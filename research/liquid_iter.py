# -*- coding: utf-8 -*-
"""
[자유 설계 · 가상] 「흐르는 전략」 개량 라운드 — 소유자 「그걸 개선해서 개량을 거듭해봐」 (2026-09-03)

EXPLORATION.md §A의 당시 진단에서 출발한 개량 실험이다. 아래 D1~D4는 수정 전 탐색 동기이지
현재 확정된 원인 설명이 아니다. v204·v207 회계 교정 뒤 수치와 판정은 실행 출력 및 CODE_REVIEW_2026-09-05.md를 따른다.
★ 「결과를 본 뒤 고치기」를 거듭하면 반드시 이기는 곡선이 하나 나온다(CLAUDE.md §-1). 그래서 걸음을 이렇게 묶는다:
  · 설계 창 D = 1994-05 ~ 2010-12 (닷컴·2008 포함)에서만 **고른다** · 보류 창 H = 2011-01 ~ 2026-08 에서 **판정**한다.
  · 역방향(H 에서 고르고 D 에서 판정)도 같이 — 한 방향에서만 이기면 맞춤이다.
  · 라운드 1: 진단 기반 고침 9개 → 설계 창 Calmar 상위 2 만 라운드 2 로.  라운드 2: 그 둘에 각각 결합 1개·룩백 앙상블 1개 → 4개.
  · 판정(보류 창): ① Calmar > B×1.102 ② 10년창 p05 ≥ B (20년창은 16년 창에 없다) — 둘 다 넘어야 「개량 성공」.
  · 시도 수는 13개(9+4). 설계 창 최고는 13개 중 최댓값이라 부풀려 있다 — 보류 창이 그걸 깎는 크기가 곧 과적합의 크기다.

진단(EXPLORATION.md §A) → 고침:
  D1 F3 는 SOX 를 37% 시간에 골라 2배 드래그로 죽었다     → R1a SOX 제외 · R1b 변동성 역가중 레버리지(1~2배, 목표 σ 30%) · R1c 위험조정 모멘텀(수익/σ)
                                                          · R1d 엔진이 200일선 위일 때만(아니면 나스닥)
  D2 F6 는 위기 안에서 매월 갈아타 한 달 늦었다          → R1e 방어는 **방어 진입 시점에 한 번**(12개월 모멘텀 상위 2)만 고르고 고정
  D3 F5 는 잠은 오나 수익이 없다                         → R1f 자산별 200일선 필터 · R1g 상위 2 집중 · R1h 주식 다리 1.5배
  D4 하이브리드                                          → R1i B 80% + F5 20% (월 재조정)
  라운드 2: 상위 2 각각에 (i) 나머지 고침 결합 (ii) 룩백 3/6/12 순위 앙상블.

★ 사전 등록 예측:
  P1 라운드 1 설계 창 최고 Calmar 는 B 를 넘는다(13번 뽑으면 하나는 넘는다) — 그러나 보류 창에서는 넘지 못한다.
  P2 보류 창에서 ①② 를 동시에 넘는 후보 0.  P3 역방향 분할에서 순위가 바뀐다(맞춤 지문).
  P4 F5 계열(R1f·g·h)은 보류 창 MDD 가 B 보다 얕고 Calmar 는 B 의 0.5~0.8배에 머문다.
  「틀리면 무엇이 참인가」: 정방향·역방향 둘 다에서 ①② 를 넘는 후보가 있으면 그것은 맞춤이 아닐 가능성이 있고 → 그림자 후보로 소유자에게
  넘긴다(반영은 소유자). 없으면 「개량을 거듭해도 낙폭 스위치를 못 넘는다」가 답이다.

실행: python research/liquid_iter.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import liquid_design as LD                               # noqa: E402  (자산·엔진·시뮬 재사용 — 결과는 안 찍는다)
import eng_common as EC                                  # noqa: E402

IDX, R, NAMES, col, MIX, MS = LD.IDX, LD.R, LD.NAMES, LD.col, LD.MIX, LD.ME
K = len(NAMES)
N = len(IDX)
ENGS = ['NDX', 'SPX', 'SOX', 'RUT', 'DIV']
DEFS = ['GOLD', 'UST10c', 'UST30c', 'TBILL', 'DIV']
L = '=' * 100
D0, D1 = pd.Timestamp('1994-05-05'), pd.Timestamp('2010-12-31')
H0, H1 = pd.Timestamp('2011-01-03'), IDX[-1]

M = {lb: {k: LD.mom(LD.ASSETS[k], lb) for k in NAMES} for lb in (63, 126, 252)}
VOL = {k: pd.Series(np.nan_to_num(R[:, col[k]]), index=IDX).rolling(60).std().values * np.sqrt(252) for k in NAMES}
MA200 = {k: (lambda c: (c > c.rolling(200).mean()).values)(pd.Series(LD.cum(LD.ASSETS[k]), index=IDX)) for k in NAMES}
NDX_DD = LD.dd_of(LD.ENG['NDX'])
TB6 = LD.mom(LD.DEF['TBILL'], 126)


def rank_engines(t, engs, lb=126, risk_adj=False, need_ma=False):
    sc = {}
    for k in engs:
        m = M[lb][k][t]
        if np.isnan(m):
            continue
        if need_ma and not MA200[k][t]:
            continue
        v = VOL[k][t]
        sc[k] = (m / v) if (risk_adj and v and not np.isnan(v) and v > 0) else m
    return sorted(sc, key=lambda k: -sc[k])


def ens_rank(t, engs):
    """룩백 3/6/12 순위 평균 (작을수록 좋음)."""
    ranks = {k: [] for k in engs}
    for lb in (63, 126, 252):
        r = rank_engines(t, engs, lb)
        for i, k in enumerate(r):
            ranks[k].append(i)
    return sorted([k for k in engs if ranks[k]], key=lambda k: np.mean(ranks[k]))


def switch_state(t, s):
    d = NDX_DD[t]
    if np.isnan(d):
        return s
    return 0 if (s == 1 and d <= -0.16) else (1 if (s == 0 and d > -0.16) else s)


def thermo_engine(engs, lb=126, risk_adj=False, need_ma=False, vol_scale=False, ensemble=False):
    """F3 계열: 나스닥 −16% 온도계 + 유동 엔진(1등) · 2배(또는 변동성 역가중 1~2배)."""
    W = np.zeros((N, K)); Wm = np.zeros(N); cur = 'NDX'; s = 1
    for t in range(N):
        s = switch_state(t, s)
        if MS[t]:
            r = ens_rank(t, engs) if ensemble else rank_engines(t, engs, lb, risk_adj, need_ma)
            cur = r[0] if r else 'NDX'
        if s == 1:
            lev = 2.0
            if vol_scale:
                v = VOL[cur][t]
                lev = float(np.clip(0.30 / v, 1.0, 2.0)) if (v and not np.isnan(v) and v > 0) else 2.0
            W[t, col[cur]] = lev / 2.0          # 2배 자산 기준 비중 (1.0 = 2배 · 0.5 = 1배)
            Wm[t] = 0.0 if lev >= 2.0 else 0.0  # 남는 몫은 현금(0 수익) — 단순화: 1배면 절반이 현금
        else:
            Wm[t] = 1.0
    RM = R.copy()
    for k in engs:
        RM[:, col[k]] = LD.lev2(R[:, col[k]])
    W2 = np.column_stack([W, Wm]); RM2 = np.column_stack([RM, MIX])
    return W2, RM2, LD.rebalance_events(W2, True if vol_scale else MS)


def defense_once(lb=252):
    """R1e: 방어 진입 때만 상위 2를 선택한다. 선택은 유지하고 비중만 월 재조정한다."""
    W = np.zeros((N, K)); cur = None; s = 1
    for t in range(N):
        ps = s; s = switch_state(t, s)
        if s == 0 and (ps == 1 or cur is None):
            sc = {k: M[lb][k][t] for k in DEFS if not np.isnan(M[lb][k][t])}
            cur = sorted(sc, key=lambda k: -sc[k])[:2] or ['TBILL']
        if s == 1:
            W[t, col['NDX']] = 1.0
        else:
            for k in cur:
                W[t, col[k]] += 1.0 / len(cur)
    RM = R.copy(); RM[:, col['NDX']] = LD.lev2(R[:, col['NDX']])
    W2 = np.column_stack([W, np.zeros(N)])
    return W2, np.column_stack([RM, MIX]), LD.rebalance_events(W2, MS)


def allweather(top=3, ma=False, lev_eq=1.0, lb=126, ensemble=False):
    """F5 계열: 10자산 모멘텀 상위 top 균등, 양수 아니면 T-bill. ma: 자산별 200일선 필터. lev_eq: 주식 다리 배율."""
    univ = ENGS + [d for d in DEFS if d != 'DIV']
    W = np.zeros((N, K)); cur = None
    for t in range(N):
        if MS[t] or cur is None:
            r = ens_rank(t, univ) if ensemble else rank_engines(t, univ, lb)
            pick = []
            for k in r:
                if len(pick) >= top:
                    break
                ok = (M[lb][k][t] > 0) and (MA200[k][t] if ma else True)
                pick.append(k if ok else 'TBILL')
            cur = pick or ['TBILL']
        for k in cur:
            W[t, col[k]] += 1.0 / len(cur)
    RM = R.copy()
    if lev_eq != 1.0:
        for k in ENGS:
            RM[:, col[k]] = lev_eq * np.nan_to_num(R[:, col[k]]) - (lev_eq - 1.0) * LD.CD
    W2 = np.column_stack([W, np.zeros(N)])
    return W2, np.column_stack([RM, MIX]), LD.rebalance_events(W2, MS)


def curve_B():
    wB = np.asarray(EC.rule_dd(pd.Series(LD.G.D['px'], index=IDX), -0.16, -0.16), float)
    QLDR = np.nan_to_num(np.asarray(LD.G.D['qldr'], float))
    return wB, QLDR


def run(spec, a, b):
    """목표·수익·마감 재조정 일정을 같은 구간으로 잘라 실행한다."""
    W2, RM2, rebalance = spec
    lo, hi = IDX.searchsorted(a), IDX.searchsorted(b, side='right')
    c = LD.sim_multi(W2[lo:hi], RM2[lo:hi], rebalance=rebalance[lo:hi])
    return c, IDX[lo:hi]


def run_B(a, b):
    wB, QLDR = curve_B()
    lo, hi = IDX.searchsorted(a), IDX.searchsorted(b, side='right')
    return np.asarray(EC.sim2(wB[lo:hi], QLDR[lo:hi], MIX[lo:hi]), float), IDX[lo:hi]


def hybrid(W2a, RM2a, W2b, RM2b, wa=0.8):
    """R1i: B 80% + F5 20% — 두 곡선의 월별 재조정 혼합(근사: 일간 수익 가중합, 월초 재조정)."""
    return None  # 아래 blend() 로 곡선 단위 처리


def blend(c1, c2, w1=0.8, ix=None, cost=LD.COST):
    """두 슬리브를 월초에만 목표비중으로 되돌린다.

    종전 구현은 매일 `w1*r1+(1-w1)*r2`를 계산해 무비용 일일 재조정을 했다.
    설명한 월 재조정과 같은 보유 경로가 되도록 실제 슬리브 평가액을 굴린다.
    """
    if ix is None or len(ix) != len(c1) or len(c1) != len(c2):
        raise ValueError('blend에는 두 곡선과 같은 길이의 날짜 ix가 필요하다')
    r1 = np.diff(c1, prepend=1.0) / np.concatenate(([1.0], c1[:-1])); r1[0] = 0
    r2 = np.diff(c2, prepend=1.0) / np.concatenate(([1.0], c2[:-1])); r2[0] = 0
    months = pd.DatetimeIndex(ix).to_period('M')
    h1, h2 = float(w1), float(1 - w1)
    out = np.empty(len(c1))
    for i in range(len(out)):
        if i > 0 and months[i] != months[i - 1]:
            total = h1 + h2
            target1 = total * w1
            turn = abs(target1 - h1) / max(total, 1e-300)
            total *= 1 - cost * turn
            h1, h2 = total * w1, total * (1 - w1)
        h1 *= 1 + r1[i]
        h2 *= 1 + r2[i]
        out[i] = h1 + h2
    return out


def met(c, ix):
    m = EC.fullmet(c, idx=ix)
    w = 2520
    m['p05_10'] = float(np.quantile(c[w:] / c[:-w], 0.05)) if len(c) > w + 252 else np.nan
    return m


def table(title, rows, base):
    print(f'\n  {title}')
    print(f"  {'후보':<52}{'최종':>8}{'CAGR':>8}{'MDD':>8}{'Calmar':>8}{'ΔCal':>8}{'10y p05':>9}{'vs B p05':>9}")
    for nm, m in rows:
        d1 = m['calmar'] / base['calmar'] - 1
        dp = (m['p05_10'] / base['p05_10'] - 1) if (not np.isnan(m['p05_10']) and base['p05_10']) else np.nan
        flag = ' ★①②' if (d1 > 0.102 and not np.isnan(dp) and dp >= 0) else ''
        print(f"  {nm:<52}{m['final']:>8,.1f}{m['cagr']:>7.2f}%{m['mdd']:>7.1f}%{m['calmar']:>8.3f}{d1*100:>+7.1f}%"
              f"{m['p05_10']:>8.2f}배{dp*100:>+8.1f}%{flag}")


def main():
    print(L); print('흐르는 전략 개량 라운드 — 설계 창에서 고르고 보류 창에서 판정 (규칙 무변경 · 모의 실험)'); print(L)
    E4 = ['NDX', 'SPX', 'RUT', 'DIV']
    cands = {
        'R1a 온도계+유동 엔진, SOX 제외': thermo_engine(E4),
        'R1b 온도계+유동 엔진, 변동성 역가중 1~2배': thermo_engine(ENGS, vol_scale=True),
        'R1c 온도계+유동 엔진, 위험조정 모멘텀': thermo_engine(ENGS, risk_adj=True),
        'R1d 온도계+유동 엔진, 200일선 위만': thermo_engine(ENGS, need_ma=True),
        'R1e 방어를 진입 시점에 한 번만 고름(12개월)': defense_once(252),
        'R1f 전천후 1배 + 자산별 200일선 필터': allweather(3, ma=True),
        'R1g 전천후 1배, 상위 2 집중': allweather(2),
        'R1h 전천후, 주식 다리 1.5배': allweather(3, lev_eq=1.5),
    }
    splits = [('정방향', (D0, D1), (H0, H1)), ('역방향', (H0, H1), (D0, D1))]
    verdict = {}
    for tag, (a, b), (c0, c1) in splits:
        print('\n' + L); print(f'{tag}: 설계 창 {a.date()}~{b.date()} 에서 고르고 → 보류 창 {c0.date()}~{c1.date()} 에서 판정'); print(L)
        Bd, ixd = run_B(a, b); Bh, ixh = run_B(c0, c1)
        mBd, mBh = met(Bd, ixd), met(Bh, ixh)
        # 라운드 1 — 설계 창
        r1 = {}
        for nm, spec in cands.items():
            cd, _ = run(spec, a, b); r1[nm] = met(cd, ixd)
        # R1i 하이브리드 (B 80 + F5 20)
        f5 = allweather(3)
        f5d, _ = run(f5, a, b); r1['R1i B 80% + 전천후 20% 혼합'] = met(blend(Bd, f5d, 0.8, ixd), ixd)
        table(f'라운드 1 · 설계 창 (B: 최종 {mBd["final"]:,.1f} · Calmar {mBd["calmar"]:.3f} · 10y p05 {mBd["p05_10"]:.2f})',
              sorted(r1.items(), key=lambda kv: -kv[1]['calmar']), mBd)
        top2 = [nm for nm, _ in sorted(r1.items(), key=lambda kv: -kv[1]['calmar'])[:2]]
        print(f'  → 라운드 2 로: {top2}')
        # 라운드 2 — 상위 2 에 결합·앙상블
        r2 = {}
        for nm in top2:
            if nm.startswith('R1i'):
                f5_filtered = allweather(3, ma=True, ensemble=True)
                r2[f'R2 [{nm[:3]}] +200일선 필터·앙상블'] = ('blend', f5_filtered, 0.8)
                r2[f'R2 [{nm[:3]}] 혼합 70/30'] = ('blend', f5, 0.7)
            elif nm.startswith('R1e'):
                r2[f'R2 [{nm[:3]}] +6개월 모멘텀'] = ('wr', defense_once(126))
                r2[f'R2 [{nm[:3]}] +위험조정 온도계 엔진 결합'] = ('wr', thermo_engine(E4, risk_adj=True, vol_scale=True))
            elif nm.startswith(('R1f', 'R1g', 'R1h')):
                r2[f'R2 [{nm[:3]}] +200일선·상위2·1.5배 결합'] = ('wr', allweather(2, ma=True, lev_eq=1.5))
                r2[f'R2 [{nm[:3]}] +룩백 앙상블'] = ('wr', allweather(3, ma=True, ensemble=True))
            else:   # R1a~d 온도계 계열
                r2[f'R2 [{nm[:3]}] +SOX 제외·위험조정·변동성 역가중 결합'] = ('wr', thermo_engine(E4, risk_adj=True, vol_scale=True, need_ma=True))
                r2[f'R2 [{nm[:3]}] +룩백 앙상블'] = ('wr', thermo_engine(E4, ensemble=True, vol_scale=True))
        rows_d, rows_h = [], []
        for nm, spec in r2.items():
            if spec[0] == 'blend':
                _, legs, w1 = spec
                cd, _ = run(legs, a, b); ch, _ = run(legs, c0, c1)
                rows_d.append((nm, met(blend(Bd, cd, w1, ixd), ixd))); rows_h.append((nm, met(blend(Bh, ch, w1, ixh), ixh)))
            else:
                _, legs = spec
                cd, _ = run(legs, a, b); ch, _ = run(legs, c0, c1)
                rows_d.append((nm, met(cd, ixd))); rows_h.append((nm, met(ch, ixh)))
        table('라운드 2 · 설계 창', rows_d, mBd)
        # 판정 — 보류 창: 라운드 2 후보 + 그 부모(라운드 1 상위 2)
        rows_hold = []
        for nm in top2:
            if nm.startswith('R1i'):
                ch, _ = run(f5, c0, c1); rows_hold.append((nm, met(blend(Bh, ch, 0.8, ixh), ixh)))
            else:
                ch, _ = run(cands[nm], c0, c1); rows_hold.append((nm, met(ch, ixh)))
        rows_hold += rows_h
        table(f'★ 판정 · 보류 창 (B: 최종 {mBh["final"]:,.1f} · Calmar {mBh["calmar"]:.3f} · 10y p05 {mBh["p05_10"]:.2f})', rows_hold, mBh)
        # 투명성: 라운드 1 전부의 보류 창 (사후 — 선택엔 안 씀)
        rows_all = []
        for nm, spec in cands.items():
            ch, _ = run(spec, c0, c1); rows_all.append((nm, met(ch, ixh)))
        ch, _ = run(f5, c0, c1); rows_all.append(('R1i B 80% + 전천후 20% 혼합', met(blend(Bh, ch, 0.8, ixh), ixh)))
        table('참고 · 라운드 1 전부의 보류 창 (선택에 안 쓴 사후 표)', sorted(rows_all, key=lambda kv: -kv[1]['calmar']), mBh)
        best_d = max(r1.values(), key=lambda m: m['calmar'])
        passed = [nm for nm, m in rows_hold if m['calmar'] > mBh['calmar'] * 1.102 and not np.isnan(m['p05_10']) and m['p05_10'] >= mBh['p05_10']]
        verdict[tag] = dict(best_design_ratio=best_d['calmar'] / mBd['calmar'],
                            best_hold_ratio=max(m['calmar'] for _, m in rows_hold) / mBh['calmar'], passed=passed,
                            rank_d=[nm[:3] for nm, _ in sorted(r1.items(), key=lambda kv: -kv[1]['calmar'])],
                            rank_h=[nm[:3] for nm, _ in sorted(rows_all, key=lambda kv: -kv[1]['calmar'])],
                            f5_hold=[(nm, m['mdd'], m['calmar'] / mBh['calmar']) for nm, m in rows_all if nm[:3] in ('R1f', 'R1g', 'R1h')],
                            B_hold_mdd=mBh['mdd'])
    print('\n' + L); print('사전 등록 대조'); print(L)
    f = verdict['정방향']; r = verdict['역방향']
    print(f"  P1 (설계 창 최고 Calmar 는 B 를 넘고 보류 창에선 못 넘는다): 정방향 설계 {f['best_design_ratio']:.2f}×B → 보류 {f['best_hold_ratio']:.2f}×B · "
          f"역방향 설계 {r['best_design_ratio']:.2f}×B → 보류 {r['best_hold_ratio']:.2f}×B → "
          f"{'맞음' if (f['best_design_ratio'] > 1 and f['best_hold_ratio'] <= 1.102) else '부분/틀림'}")
    print(f"  P2 (보류 창 ①② 동시 통과 0): 정방향 {f['passed'] or '없음'} · 역방향 {r['passed'] or '없음'} → {'맞음' if not f['passed'] and not r['passed'] else '틀림'}")
    print(f"  P3 (역방향에서 순위가 바뀐다): 정방향 설계 순위 {f['rank_d'][:4]} · 역방향 설계 순위 {r['rank_d'][:4]} → {'맞음' if f['rank_d'][:2] != r['rank_d'][:2] else '틀림'}")
    f5 = f['f5_hold']
    print(f"  P4 (F5 계열 보류 창 MDD 얕고 Calmar 0.5~0.8×B): " + ' · '.join(f'{nm[:3]} MDD {mdd:.1f}% Cal {cr:.2f}×' for nm, mdd, cr in f5)
          + f" (B MDD {f['B_hold_mdd']:.1f}%) → {'맞음' if all(mdd > f['B_hold_mdd'] and 0.5 <= cr <= 0.8 for _, mdd, cr in f5) else '부분/틀림'}")
    print('\n이 측정이 낳은 다음 질문 (§-1 절대멈춤 6):')
    print('  · 설계 창 최고와 보류 창의 차이가 과적합의 크기다 — 그 크기를 §5-20·§5-22 의 문턱 격자 PBO 와 나란히 두면 「흐르는 층」의 과적합 성향이 보인다.')
    print('  · 보류 창에서 B 에 가장 가까웠던 후보의 기전이 무엇인지(엔진 교체인지, 변동성 역가중인지, 방어 고정인지)는 표가 말한다 — 그 하나만 남기고 나머지를 빼는 축퇴 검사가 다음 걸음이나, 시도 수가 늘수록 보류 창도 오염된다. 여기서 멈춘다.')


if __name__ == '__main__':
    main()
