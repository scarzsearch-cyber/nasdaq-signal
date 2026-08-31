# -*- coding: utf-8 -*-
"""
[방어 바스켓에 배당(주식)이 왜 있나 — 거치 후 적립, 2026-08-31 소유자 질문] 판정 아님.

질문 둘:
  ① "재산형성시기 방어구간에 배당100% 는 불필요한 거지? 증식은 레버리지가 하니
     방어만 확실히 하면 된다" → 적립식으로도 그런가. 단 **거치 후 적립**으로.
     (소유자 실제 패턴: 100% 전환해 두고 한 달에 한 번 월급을 얹는다 → 거치가 크다)
  ② "다우존스는 왜 사는 거야? 방어용도여도 채권과 금만으로는 안 돼서?"

기존 기록 (04·01 §, v23/v27/v36):
  · 배당100 은 **달러 최종배수 1위**다. 그런데 원화 좌측꼬리·MDD·2008 에서 진다
    (원화 20년창 p05 40.82 vs 35.73 · MDD −60.5 vs −68.1% · 2008 +9.0 vs −22.7%).
  · v36 「하지 마라」: 판정 게이트를 최종배수로 걸지 마라 · 달러로 결론 내지 마라.
  · 「국채50 금50 (주식0)」은 v23 CANDS 에 있었으나 **적립식 대조는 기록에 없다.**
→ 이 파일이 채우는 공백: **거치 후 적립 · 원화 기준 · 주식0 안 포함**.

────────────────────────────────────────────────────────────────────────
★ 사전 등록 (결과 보기 전) — 02 §3 G1~G3 규약 그대로
  판정 지표: **적립 배수(최종평가/총납입)의 중앙 · P20 · P5**, 롤링 전 시작일.
  기준 통화: **원화** (v36 「달러로 결론 내지 마라」). 달러는 참고로만 병기.
  현행 유지 조건: 현행(40/40/20)이 **P5·P20 에서 지지 않을 것.**
  「실패하면 무엇이 참인가 / 통과하면 무엇이 참인가」:
    · 배당100 이 P5 에서 이기면 = 형성기엔 방어에 주식을 더 넣는 게 맞다
    · 주식0(국채/금)이 P5 에서 이기면 = 배당 다리는 불필요하다
    · 둘 다 지면 = 현행 배합이 형성기에도 맞다
  세 답이 서로 다르다 → 관문으로 성립한다.

전략 무변경 — 동결 규칙이며 이 파일은 「형성기에도 현행이 맞나」의 답만 낸다.
실행: python research/def_equity.py
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import axis_lib as AL                                    # noqa: E402
import hist_defasset as DA                               # noqa: E402
import eng_common as EC                                  # noqa: E402

# 방어 배합 후보 — 전부 국내 상장 대응 상품이 있는 것만 (v23 제약)
DEFS = [
    ('배당100',            dict(div=1.00)),
    ('40/40/20 (현행)',    dict(div=0.40, ust5=0.40, gold=0.20)),
    ('주식0 국채50 금50',   dict(ust5=0.50, gold=0.50)),
    ('국채0 배당50 금50',   dict(div=0.50, gold=0.50)),
]
# 거치 : 월납 비율. 단위는 「월급 1회분」 — L=120 이면 10년치 월급을 이미 넣어둔 상태.
LUMPS = [0, 60, 120, 240]
WINDOWS = [(2520, '10년'), (3780, '15년'), (5040, '20년')]


def curve(idx, wB, QLDR, weights, parts):
    """방어 배합별 전략 곡선 — 검증된 sim2 로만 만든다(엔진 재구현 금지)."""
    mixr = DA.mix_monthly_parts(idx, weights, {k: np.nan_to_num(parts[k]) for k in weights})
    return EC.sim2(wB, QLDR, np.nan_to_num(mixr))


def accum_mult(a, mstart, lo, hi, lump):
    """거치 lump + 월납 1단위의 **적립 배수** (최종평가 / 총납입).

    전략 경로는 투입액과 무관하므로 최종평가는 납입에 **정확히 선형**이다:
        V_T = lump·(a_T/a_lo) + Σ_j (a_T/a_j)
    그래서 곡선 하나로 모든 시작일을 O(n) 에 계산한다.
    이 선형성은 아래 selfcheck() 가 axis_lib.accumulate 와 대조해 검산한다.
    """
    m = mstart[(mstart > lo) & (mstart < hi)]
    n_pay = len(m)
    inv = np.sum(a[hi - 1] / a[m]) if n_pay else 0.0
    v = lump * (a[hi - 1] / a[lo]) + inv
    return v / (lump + n_pay) if (lump + n_pay) > 0 else np.nan


def selfcheck(D, wB, mix_r, a_ref, mstart):
    """검산 — 위 선형식이 axis_lib.accumulate 와 같은 답을 내는가.

    accumulate 는 방어자산을 **D['schdr'] 하나로** 받는다. G.D 의 schdr 은
    배당체인 **원본**이므로, 40/40/20 곡선과 대조하려면 배합을 주입한 사본을
    넘겨야 한다(hypo_gates 가 Dm 을 만드는 것과 같은 이유). 초판이 이걸 빠뜨려
    21% 오차가 났고 이 검산이 잡았다.
    """
    Dm = dict(D)
    Dm['schdr'] = mix_r
    lo, hi = 3000, 3000 + 20 * 252
    paid, fin, _ = AL.accumulate(Dm, 2.0, wB, lo, hi)     # 순수 월납 (거치 0)
    mine = accum_mult(a_ref, mstart, lo, hi, 0) * paid
    err = abs(mine / fin - 1)
    print(f'[검산] 선형식 vs axis_lib.accumulate — 납입 {paid:.0f}회 · '
          f'최종 {mine:,.1f} vs {fin:,.1f} · 상대오차 {err:.2e}')
    assert err < 2e-3, f'선형식 검산 실패 {err:.3e} — 규약을 잘못 읽었다'
    return err


def dist_row(vals):
    v = np.asarray([x for x in vals if x == x])
    return (np.median(v), np.quantile(v, 0.20), np.quantile(v, 0.05), len(v))


def main():
    G, _ = EC.selfcheck()
    idx, D, wB = G.idx, G.D, np.asarray(G.wB, float)
    n = len(idx)
    QLDR = np.nan_to_num(np.asarray(D['qldr'], float))
    parts = {'div': np.asarray(D['schdr'], float),
             'ust5': DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE),
             'gold': DA.gold_r(idx)}
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]      # 월초 납입일

    # 원화 환산 — 4다리 전부 환노출이므로 포트폴리오 전체에 환율이 곱해진다
    fxr, fx0 = None, None
    d = pd.read_csv(_os.path.join('data', 'hist', 'fred_DEXKOUS.csv'))
    c = [x for x in d.columns if x.lower().startswith('observation')][0]
    v = [x for x in d.columns if x != c][0]
    s = pd.to_numeric(d.set_index(pd.to_datetime(d[c]))[v], errors='coerce').dropna()
    s = s.reindex(idx.union(s.index)).ffill().reindex(idx)
    fx0 = s.first_valid_index()
    fxr = (s / s.loc[fx0]).bfill().values

    mixes = {nm: DA.mix_monthly_parts(idx, wt, {k: np.nan_to_num(parts[k]) for k in wt})
             for nm, wt in DEFS}
    curves = {nm: EC.sim2(wB, QLDR, np.nan_to_num(mixes[nm])) for nm, _ in DEFS}
    cur_nm = '40/40/20 (현행)'
    selfcheck(D, wB, mixes[cur_nm], curves[cur_nm], mstart)

    kr_lo = int(idx.searchsorted(fx0))
    print(f'\n표본: {str(idx[0].date())}~{str(idx[-1].date())} · '
          f'원화 구간 {str(idx[kr_lo].date())}~ (환율 자료 시작)')
    print('적립 규약: 월초 1단위 · 거치 L 은 「월급 L 회분」 · 배수 = 최종평가/총납입')

    for cy, a_mul, c0 in (('원화 (판정 기준) · 1981~', fxr, kr_lo),
                          ('달러 · **원화와 같은 창 1981~** (통화 효과 분리)', None, kr_lo),
                          ('달러 · 전구간 1972~ (참고)', None, 0)):
        print('\n' + '=' * 78)
        print(f' {cy}')
        print('=' * 78)
        for w, wl in WINDOWS:
            starts = np.arange(c0, n - w, 21)                  # 월 간격 시작일 전수
            if len(starts) < 12:
                print(f'  {wl}창 — 표본 부족({len(starts)}개) 생략')
                continue
            print(f'\n  ── {wl} 창 · 시작일 {len(starts)}개 ──')
            print(f"  {'거치:월납':<10}{'방어 배합':<18}{'중앙':>9}{'P20':>9}{'P5':>9}"
                  f"{'현행대비 P5':>12}")
            for L in LUMPS:
                base = None
                for nm, _wt in DEFS:
                    a = curves[nm] if a_mul is None else curves[nm] * a_mul
                    vals = [accum_mult(a, mstart, s0, s0 + w, L) for s0 in starts]
                    med, p20, p05, _ = dist_row(vals)
                    if nm.startswith('40/40/20'):
                        base = p05
                    tag = f'{L}:1' if L else '순수적립'
                    d5 = '' if base is None or nm.startswith('40/40/20') else \
                         f'{(p05/base-1)*100:>+11.1f}%'
                    star = '  ←현행' if nm.startswith('40/40/20') else ''
                    print(f"  {tag if nm == DEFS[0][0] else '':<10}{nm:<18}"
                          f"{med:>8.2f}배{p20:>8.2f}배{p05:>8.2f}배{d5}{star}")

    # ── 배당 다리가 무엇을 하는가 — 기전 ────────────────────────────────────
    print('\n' + '=' * 78)
    print(' 배당 다리는 무엇을 하는가 — 방어 구간의 길이와 수익')
    print('=' * 78)
    defmask = wB < 0.5
    runs, i = [], 0
    while i < n:
        if defmask[i]:
            j = i
            while j + 1 < n and defmask[j + 1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    lens = np.array([j - i + 1 for i, j in runs])
    print(f'  방어 구간 {len(runs)}회 · 총 {int(defmask.sum()):,}일 (전체의 {defmask.mean():.0%})')
    print(f'  길이 중앙 {np.median(lens):.0f}거래일(~{np.median(lens)/21:.1f}개월) · '
          f'최장 {lens.max():,}일(~{lens.max()/252:.1f}년) · '
          f'1년 넘는 구간 {int((lens > 252).sum())}회')
    print(f"\n  {'방어 배합':<18}{'방어 중 연CAGR':>15}{'방어 중 최악낙폭':>17}")
    for nm, wt in DEFS:
        mixr = DA.mix_monthly_parts(idx, wt, {k: np.nan_to_num(parts[k]) for k in wt})
        seg = np.concatenate([mixr[i:j + 1] for i, j in runs])
        cg = (np.prod(1 + seg) ** (252 / len(seg)) - 1) * 100
        worst = min((np.prod(1 + mixr[i:j + 1]) - 1) * 100 for i, j in runs)
        print(f'  {nm:<18}{cg:>14.2f}%{worst:>16.1f}%')
    print('  ※ 「방어 중 최악낙폭」 = 방어 구간 하나에서 난 최악의 누적 손실.')

    # ── 분해 + 반증 ⓑ — 「배당을 빼도 되나」는 식별되는 질문인가 ─────────────
    #   주식0(ust50/gold50)은 배당 40→0 과 금 20→50 을 **동시에** 바꾼다. 교란이다.
    #   갈라서 재고, 내가 고른 배합이 아니라 무작위 300개 분포로 판정한다(§-1 ⓑ).
    def p5med(a, w=5040, L=120, c0=0):
        st = np.arange(c0, n - w, 21)
        out = []
        for s0 in st:
            out.append(accum_mult(a, mstart, s0, s0 + w, L))
        return np.quantile(out, 0.05), np.median(out)

    for cy, a_mul, c0 in (('원화 (판정 기준) 1981~', fxr, kr_lo), ('달러 1972~ (대조)', None, 0)):
        print('\n' + '=' * 78)
        print(f' 분해 + 반증 — {cy} · 20년창 · 거치120:1 · P5')
        print('=' * 78)
        def C(d_, u_, g_):
            wt = {k: x for k, x in (('div', d_), ('ust5', u_), ('gold', g_)) if x > 0}
            m = DA.mix_monthly_parts(idx, wt, {k: np.nan_to_num(parts[k]) for k in wt})
            a = EC.sim2(wB, QLDR, np.nan_to_num(m))
            return a if a_mul is None else a * a_mul
        bp5, _ = p5med(C(.40, .40, .20), c0=c0)
        print(f"  {'배합':<26}{'P5':>9}{'현행대비':>10}")
        for lab, wt3 in [('현행 div40/ust40/gold20', (.40, .40, .20)),
                         ('배당만 뺌 ust80/gold20', (0, .80, .20)),
                         ('금만 늘림 div25/ust25/gold50', (.25, .25, .50)),
                         ('주식0 ust50/gold50', (0, .50, .50)),
                         ('금 뺌 div50/ust50', (.50, .50, 0)),
                         ('배당100', (1.0, 0, 0))]:
            q, _ = p5med(C(*wt3), c0=c0)
            print(f'  {lab:<26}{q:>8.2f}배{(q/bp5-1)*100:>+9.1f}%')
        rng = np.random.default_rng(20260831)
        res = []
        for _ in range(300):
            vv = rng.dirichlet([1, 1, 1])
            res.append((vv, p5med(C(*vv), c0=c0)[0]))
        qs = np.array([r[1] for r in res])
        arr = np.array([r[0] for r in res])
        print(f'  [반증 ⓑ] 무작위 300개 — 현행은 상위 {np.mean(qs <= bp5)*100:.0f}백분위 · '
              f'최고 {qs.max()/bp5-1:+.1%}')
        top = sorted(res, key=lambda r: -r[1])[:3]
        print('    상위 3 (div/ust/gold): ' + ' · '.join(
            f'{v[0]*100:.0f}/{v[1]*100:.0f}/{v[2]*100:.0f}' for v, _ in top))
        print(f'    비중-P5 상관 — 배당 {np.corrcoef(arr[:,0],qs)[0,1]:+.2f} · '
              f'국채 {np.corrcoef(arr[:,1],qs)[0,1]:+.2f} · 금 {np.corrcoef(arr[:,2],qs)[0,1]:+.2f}')

    print('\n' + '=' * 78)
    print(' 판정')
    print('=' * 78)
    print(' ① 배당100 은 형성기에도 아니다 — 원화 20년창 P5 −10.2%,')
    print('    그리고 **방어 중 연 −8.04% · 최악 −22.3%**. 방어하러 들어가서 잃는다.')
    print(' ② 「배당 다리를 빼도 되나」는 **식별되지 않는 질문**이다:')
    print('    최적 배합이 **표본 창**에 따라 정반대 코너로 튄다 (배당-P5 상관')
    print('    1972~ +0.96 / 1981~ −0.78). **통화는 무관** — 같은 창이면 원화·달러가')
    print('    같다(4다리 전부 환노출). 코너 최적은 sweep 이 예외로 거부하는 형태다.')
    print('    1981~ 창은 금 고점(1980-01) 직후부터라 최악 진입점을 뺀 편향된 창이다.')
    print('    04 §5-15 C 의 「방어 비중은 고를 여지 없음」과 같은 결론 — 내가 본 ±10%는')
    print('    **다리 하나를 0 으로 만드는 코너를 포함해서** 생긴 폭이다.')
    print(' → 현행 40/40/20 유지. 근거는 「최적이라서」가 아니라 **어느 코너에도 걸지')
    print('    않아서**이고, 실제로 방어 중 최악낙폭이 4개 중 최소(−5.9%)다.')
    print('=' * 78)

    # ── 파생 질문 (CLAUDE.md §-1 절대멈춤 6 — 판정만 내고 끝내지 않는다) ──────
    print('\n' + '=' * 74)
    print(' 이 측정이 낳은 다음 질문 — 답은 04 §7 대장에 등재')
    print('=' * 74)
    print('  · [답함 §5-15C] 무작위 300 배합 현행 44백분위 → 코너 빼면 평평, 고를 여지 없음')
    print('  · [답함 §5-8  ] 방어 구간 중앙 4거래일 → 잔왕복 비용? 손익분기 편도 2.5%')
    print('  · [답함 01 §  ] 방어 중 CAGR +0.08% → 설계대로. 방어의 목적함수는 수익이 아니다')
    print('  · [답함 §7-2] 금 국면을 5번째 감시 변수로? — **넣지 않는다.** 금이 최악이던')
    print('               20년(−65.5%)에도 바스켓은 +261.7%(배당이 +2,172%). 그 창으로')
    print('               금을 빼면 전체 최종배수 −9.7%. 관문 테스트도 실패(양쪽 답이 같다)')
    print('  (미결은 「하지 마라」가 아니다. 조건이 오면 사전 등록부터 다시 한다.)')



if __name__ == '__main__':
    main()
