# -*- coding: utf-8 -*-
"""
[v58] Meta-Strategy — 시대마다 규칙을 갈아타면 고정 -16/-16 을 이기는가

핵심 질문(§29):
  **"시대마다 최적 규칙이 달랐다는 사실을 이용해, 그 시대가 시작될 당시
    알 수 있었던 정보만으로 실제로 더 좋은 규칙을 고를 수 있는가?"**

===========================================================================
[설계 동결 — §4. 결과를 보기 **전에** 정했고, 본 뒤 바꾸지 않는다]
===========================================================================
  후보 풀        기존 문서에 등장한 12개만. 새로 만들지 않는다.
                 -10/-10 -11/-11 -12/-12 -15/-15 -16/-16 -16/-11
                 -19/-11 -19/-18 -23/-7 -23/-18 -24/-22 -24/-24
  선택창          과거 10년 (2520 거래일)
  워밍업          10년. 1982-01 부터 메타 시작. 그 이전은 -16/-16 고정
  선택빈도        분기 1회 (63 거래일). 매일 교체 금지(§12)
  평가            **비중첩 10년 창** 우선(§15) + ISA/영구 DCA 관문
  동점처리        후보 풀 **순서상 앞선 것**. 결정론적
  비용            편도 0.1%. 규칙 교체로 생기는 포지션 점프도 그대로 비용을 문다
  상태이월        규칙을 갈아탈 때 새 규칙의 **그 시점 상태**를 그대로 받는다
                 (각 후보 경로를 1972 부터 독립적으로 굴려 둔다)

  이 설정을 결과를 보고 고치면 v58.1 로 **분리**한다. 합치지 않는다.
===========================================================================

[메타 전략 7종 — §5~§11]
  A 최근성과      과거 10년 최종배수 1등
  B 위기성과      과거 10년 MDD 가 가장 얕은 것
  C 멀티지표      순위합 (최종배수 + 하위20% + MDD)
  D 강건성       자기 점수 + **인접 규칙** 점수의 평균 (고립 첨탑에 벌점)
  E 미니맥스      과거 10년을 4등분해 **최악 순위**가 가장 좋은 것
  F 국면         지금 국면(변동성·낙폭)과 닮은 과거 구간에서 잘한 것
  G 앙상블       12개 후보의 현재 신호 **다수결** (이진 유지)

[Oracle]  각 평가창이 끝난 뒤 그 창의 1등을 사후 선택. **실전 전략이 아니다.**
          시대별 규칙 전환의 이론적 상한선을 잰다.

[미래참조] 모든 점수는 선택시점 **이전** 자료로만. Oracle 만 예외이고 그렇게 표시한다.
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ====================== 설계 상수 (동결) ======================
POOL = [(-0.10, -0.10), (-0.11, -0.11), (-0.12, -0.12), (-0.15, -0.15),
        (-0.16, -0.16), (-0.16, -0.11), (-0.19, -0.11), (-0.19, -0.18),
        (-0.23, -0.07), (-0.23, -0.18), (-0.24, -0.22), (-0.24, -0.24)]
CUR = (-0.16, -0.16)
LOOK = 10 * 252          # 선택창 10년
FREQ = 63                # 분기 1회
WARM = '1982-01-01'      # 워밍업 종료
L = 20 * 252
BLOCKS = [('1982-91', '1982-01-01', '1991-12-31'),
          ('1992-01', '1992-01-01', '2001-12-31'),
          ('2002-11', '2002-01-01', '2011-12-31'),
          ('2012-21', '2012-01-01', '2021-12-31'),
          ('2022-26', '2022-01-01', '2026-08-26')]
# =============================================================


def main():
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, 2)
    ddv = np.asarray(D['ddv'], float)
    S = pd.Series(np.asarray(D['px'], float))
    rv = S.pct_change().rolling(21, min_periods=21).std().values
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]

    W = {c: rule_w(ddv, c[0], c[1]) for c in POOL}       # 각 후보 경로 (1972~ 독립)
    LG = {}                                              # 일별 로그수익 (비용 포함)
    for c in POOL:
        pos = np.r_[W[c][0], W[c][:-1]]
        r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
        t = np.abs(np.diff(pos, prepend=pos[0]))
        LG[c] = np.log((1 + r) * (1 - COST * t))

    def mult(c, lo, hi):
        return float(np.exp(LG[c][lo:hi].sum()))

    def mdd_of(c, lo, hi):
        cc = np.exp(np.cumsum(LG[c][lo:hi]))
        return float((cc / np.maximum.accumulate(cc) - 1).min())

    def p20_of(c, lo, hi):
        """선택창 안의 1년 창 하위 20% (짧은 창이면 nan)."""
        n = hi - lo
        if n < 504:
            return np.nan
        v = [float(np.exp(LG[c][s:s + 252].sum()))
             for s in range(lo, hi - 252, 63)]
        return float(np.percentile(v, 20)) if len(v) >= 5 else np.nan

    # ---------------------------------------------------- 메타 점수 함수들
    def sc_A(lo, hi, i):
        return {c: mult(c, lo, hi) for c in POOL}

    def sc_B(lo, hi, i):
        return {c: mdd_of(c, lo, hi) for c in POOL}          # 클수록(얕을수록) 좋다

    def sc_C(lo, hi, i):
        m = {c: mult(c, lo, hi) for c in POOL}
        p = {c: p20_of(c, lo, hi) for c in POOL}
        d = {c: mdd_of(c, lo, hi) for c in POOL}
        rk_ = lambda dd: {c: i2 for i2, c in enumerate(sorted(POOL, key=lambda k: -np.nan_to_num(dd[k], nan=-1e9)))}
        ra, rb, rc = rk_(m), rk_(p), rk_(d)
        return {c: -(ra[c] + rb[c] + rc[c]) for c in POOL}    # 순위합이 작을수록 좋다

    def _neighbors(c):
        out = [k for k in POOL
               if abs(k[0] - c[0]) <= 0.011 and abs(k[1] - c[1]) <= 0.011 and k != c]
        return out

    def sc_D(lo, hi, i):
        base = {c: mult(c, lo, hi) for c in POOL}
        out = {}
        for c in POOL:
            nb = _neighbors(c)
            out[c] = np.mean([base[c]] + [base[k] for k in nb]) if nb else base[c] * 0.9
        return out

    def sc_E(lo, hi, i):
        """과거 10년을 4등분해 각 구간 순위를 매기고 **최악 순위**로 고른다."""
        q = (hi - lo) // 4
        if q < 126:
            return {c: mult(c, lo, hi) for c in POOL}
        worst = {c: 0 for c in POOL}
        for k in range(4):
            a, b = lo + k * q, lo + (k + 1) * q
            order = sorted(POOL, key=lambda c: -mult(c, a, b))
            for r_, c in enumerate(order, 1):
                worst[c] = max(worst[c], r_)
        return {c: -worst[c] for c in POOL}

    def sc_F(lo, hi, i):
        """지금 국면(변동성 z, 낙폭)과 닮은 과거 날들에서 잘한 후보."""
        z = np.nan_to_num(rv[i], nan=0.0)
        seg_rv = rv[lo:hi]
        m = np.isfinite(seg_rv) & (np.abs(seg_rv - z) <= 0.5 * np.nanstd(seg_rv))
        if m.sum() < 252:
            return {c: mult(c, lo, hi) for c in POOL}
        return {c: float(np.nansum(np.where(m, LG[c][lo:hi], 0.0))) for c in POOL}

    METAS = {'A 최근성과': sc_A, 'B 위기(MDD)': sc_B, 'C 멀티지표': sc_C,
             'D 강건성': sc_D, 'E 미니맥스': sc_E, 'F 국면': sc_F}

    lo0 = int(idx.searchsorted(pd.Timestamp(WARM)))
    picks_at = list(range(lo0, N, FREQ))

    def build_meta(scorer):
        """분기마다 후보를 골라 그 규칙의 비중경로를 따른다."""
        w = W[CUR].copy()
        chosen = []
        for k, i in enumerate(picks_at):
            lo = max(0, i - LOOK)
            s = scorer(lo, i, i)                     # **i 이전 자료만**
            best = max(POOL, key=lambda c: (np.nan_to_num(s[c], nan=-1e18),
                                            -POOL.index(c)))
            j = picks_at[k + 1] if k + 1 < len(picks_at) else N
            w[i:j] = W[best][i:j]
            chosen.append((idx[i], best))
        return w, chosen

    def build_ensemble():
        """12개 후보의 현재 신호 다수결. 이진 유지."""
        M = np.vstack([W[c] for c in POOL])
        w = (M.mean(axis=0) >= 0.5).astype(float)
        w[:lo0] = W[CUR][:lo0]
        return w, []

    def build_oracle():
        """**미래를 안다.** 각 분기 구간의 사후 1등. 실전 전략 아님."""
        w = W[CUR].copy()
        for k, i in enumerate(picks_at):
            j = picks_at[k + 1] if k + 1 < len(picks_at) else N
            best = max(POOL, key=lambda c: mult(c, i, j))
            w[i:j] = W[best][i:j]
        return w, []

    cands = {'현행 -16/-16 고정': (W[CUR], [])}
    for nm, f in METAS.items():
        cands['메타 ' + nm] = build_meta(f)
    cands['메타 G 앙상블'] = build_ensemble()
    cands['Oracle (미래참조)'] = build_oracle()

    # ---------------------------------------------------- 평가
    def curve(w):
        pos = np.r_[w[0], w[:-1]]
        r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
        t = np.abs(np.diff(pos, prepend=pos[0]))
        return np.cumprod((1 + r) * (1 - COST * t)), pos

    def dca(c, lo, hi, pay=10 ** 9):
        m = mstart[(mstart > lo) & (mstart < hi)][:pay]
        return float(np.mean(c[hi - 1] / c[m])) if len(m) else np.nan

    print("=" * 118)
    print("v58 Meta-Strategy — 설계는 §4 대로 **결과 보기 전에** 고정했다")
    print("      후보 12개 · 선택창 10년 · 분기 1회 · 워밍업 %s · 비중첩 10년창 우선"
          % WARM[:4])
    print("=" * 118)

    R = {}
    for nm, (w, ch) in cands.items():
        c, pos = curve(w)
        st = [s for s in range(lo0, N - L, 63)]
        isa = np.array([dca(c, s, s + L, 60) for s in st])
        per = np.array([dca(c, s, s + L) for s in st])
        seg = c[lo0:]
        R[nm] = dict(c=c, isa=isa, per=per, chosen=ch,
                     mdd=float((seg / np.maximum.accumulate(seg) - 1).min()),
                     sw=int((np.abs(np.diff(pos[lo0:])) > 1e-9).sum()),
                     blk=[float(c[int(idx.searchsorted(pd.Timestamp(b), side='right')) - 1]
                                / c[int(idx.searchsorted(pd.Timestamp(a)))])
                          for _, a, b in BLOCKS])
    B = R['현행 -16/-16 고정']
    O = R['Oracle (미래참조)']

    print()
    print("  %-22s%9s%8s%8s%10s%9s%7s   %s"
          % ('전략', 'ISA중앙', 'P20', 'P5', '영구중앙', 'MDD', '전환', '비중첩 10년창 (현행=100)'))
    for nm in cands:
        r = R[nm]
        rel = ' '.join('%5.0f' % (100 * v / b) for v, b in zip(r['blk'], B['blk']))
        mk = '  <- 기준' if nm.startswith('현행') else ('  <- 상한' if 'Oracle' in nm else '')
        print("  %-22s%9.1f%8.1f%8.1f%10.1f%8.1f%%%7d   %s%s"
              % (nm, np.median(r['isa']), np.percentile(r['isa'], 20),
                 np.percentile(r['isa'], 5), np.median(r['per']),
                 r['mdd'] * 100, r['sw'], rel, mk))
    print()
    print("  비중첩 10년창: %s" % ' '.join('%-5s' % b[0] for b in BLOCKS))
    print()

    # ---------------------------------------------------- Oracle Gap (§18)
    print("=" * 118)
    print("Oracle Gap (§18) — 시대별 최적의 잠재이익이 실제로 포착되는가")
    print("=" * 118)
    ob = np.median(O['isa']) / np.median(B['isa']) - 1
    print("  Oracle - 고정 : %+.0f%%   <- 시대별 규칙 전환의 **이론적 상한**" % (ob * 100))
    print()
    print("  %-22s%12s%14s%14s" % ('메타', '고정 대비', 'Oracle 대비', '상한의 몇 %를 포착'))
    for nm in cands:
        if nm.startswith('현행') or 'Oracle' in nm:
            continue
        r = R[nm]
        mb = np.median(r['isa']) / np.median(B['isa']) - 1
        mo = np.median(r['isa']) / np.median(O['isa']) - 1
        cap = (mb / ob * 100) if abs(ob) > 1e-9 else np.nan
        print("  %-22s%11.0f%%%13.0f%%%13.0f%%" % (nm, mb * 100, mo * 100, cap))
    print()

    # ---------------------------------------------------- G13 선택 안정성
    print("=" * 118)
    print("G13 선택 안정성 (§21)")
    print("=" * 118)
    print("  %-22s%10s%12s   %s" % ('메타', '규칙변경', '평균유지', '가장 많이 고른 규칙'))
    for nm in cands:
        ch = R[nm]['chosen']
        if not ch:
            continue
        rules = [c for _, c in ch]
        chg = sum(1 for a, b in zip(rules, rules[1:]) if a != b)
        from collections import Counter
        top = Counter(rules).most_common(2)
        print("  %-22s%10d%10.1f분기   %s"
              % (nm, chg, len(rules) / max(chg, 1),
                 ' · '.join('%.0f/%.0f(%d%%)' % (c[0] * 100, c[1] * 100,
                                                 100 * n // len(rules)) for c, n in top)))
    print()

    # ---------------------------------------------------- 판정
    win = []
    for nm in cands:
        if nm.startswith('현행') or 'Oracle' in nm:
            continue
        r = R[nm]
        if (np.median(r['isa']) > np.median(B['isa'])
                and np.percentile(r['isa'], 20) > np.percentile(B['isa'], 20)
                and np.percentile(r['isa'], 5) > np.percentile(B['isa'], 5)
                and np.median(r['per']) > np.median(B['per'])
                and sum(1 for v, b in zip(r['blk'], B['blk']) if v > b) >= 3
                and r['mdd'] >= B['mdd']):
            win.append(nm)
    print("=" * 118)
    print(verdict('동적 규칙 선택이 고정 -16/-16 을 이기는가 (§29)', [
        ('G1~G6 를 전부 통과한 메타가 있다', len(win) > 0,
         ', '.join(win) if win else '없음 / 메타 7종'),
        ('Oracle 이 고정을 유의하게 앞선다 (전환 가치가 애초에 있는가)',
         ob > 0.10, 'Oracle-고정 %+.0f%%' % (ob * 100)),
    ], adopt_if=['G1~G6 를 전부 통과한 메타가 있다'])['text'])
    return R, B, O, cands, idx, N, lo0


if __name__ == '__main__':
    main()
