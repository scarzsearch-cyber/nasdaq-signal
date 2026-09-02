# -*- coding: utf-8 -*-
"""
[새 길 탐구 · 가상] 무덤에 없는 세 차원 — 병렬 슬리브 · 안전자산 단위 낙폭 · 고점 이후 시간 (2026-09-03, 소유자 「개선이 아닌 새로운
탐구도 좋다 — 알파고처럼 너만의 길」)

04 §1~§5-26 · EXPLORATION.md §A 에 없는 것만 골랐다(grep 확인: 슬리브·비율 낙폭·기간 신호 선행 0건. 인버스 슬리브(§5-24 X2)는 방어 안의 혼합이라 다른 것).
  A 병렬 슬리브(CTA 식): −16/−16 규칙을 **한 엔진에 거는 대신 여러 자산에 각각** 건다. 슬리브 = 자기 지수의 252일 고점 낙폭이 −16% 위면
    그 자산(주식 지수는 2배 합성 · 금·채권은 1배), 아래면 T-bill. 슬리브 균등 배분(일 단위 재조정 근사 · 회전 비용은 스위치 때만).
      A1 {NDX·SPX}  A2 {NDX·SPX·금·30년국채}  A3 {NDX·SPX·RUT} (1987~)  A4 NDX 50% + 나머지 50%  A5 A2 인데 슬리브 방어를 40/40/20 로
  C 안전자산 단위 낙폭: 신호를 나스닥 가격이 아니라 **나스닥÷금**·**나스닥÷30년국채**·**나스닥÷T-bill(초과수익)** 의 252일 고점 낙폭에 건다.
    위험 회피 때 금·채권이 오르면 비율이 먼저 떨어져 더 일찍 나간다(가설). 보유는 B 와 같다(나스닥 2배 ↔ 40/40/20).
      C1 ÷금  C2 ÷30년국채(1977~)  C3 ÷T-bill  C4 「둘 중 하나」: 나스닥 낙폭 ≤ −16 또는 ÷금 낙폭 ≤ −16 이면 방어, 둘 다 > −16 이면 복귀
  D 고점 이후 시간: 깊이 대신 **252일 고점을 못 넘긴 날수**로 나간다.
      D1/D2/D3 순수 시간: 고점 이후 60/120/250일 넘으면 방어, 새 고점이면 복귀   D4/D5 「깊이 또는 시간」: dd ≤ −16 또는 120/250일 → 방어, dd > −16 복귀
기준 B(나스닥 2배 · −16/−16 · 40/40/20) · 같은 창 · 편도 0.1% · 관문 ① Calmar +10.2% ② 20년창 p05 ≥ B ③ 4블록 중 3 이상(Calmar).

★ 사전 등록 예측:
  P1 슬리브 A1~A5: MDD 는 B 보다 5~15%p 얕고 최종은 0.2~0.5×, Calmar 는 0.8~1.1× — 여기가 진짜 열린 질문이다.
  P2 슬리브 어느 것도 ①②③ 동시 통과 없음(최종·p05 가 희석된다).
  P3 비율 낙폭 C1~C3 은 B 의 0.7~0.95× Calmar(금·채권의 자체 움직임이 채찍질을 만든다). C4 는 B 의 ±10%.
  P4 순수 시간 D1~D3 은 최종 0.1~0.4×(V 자를 놓친다). D4·D5 는 B 의 ±10%.
  「틀리면 무엇이 참인가」: 어느 후보가 ①②③ 을 넘으면 그림자 후보로 소유자에게(반영은 소유자). 전부 실패면 「새 차원도 낙폭 스위치를 못 넘는다」.

실행: python research/new_paths.py
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

import liquid_design as LD                               # noqa: E402  (자산·시뮬 재사용)
import eng_common as EC                                  # noqa: E402

IDX, R, NAMES, col, MIX = LD.IDX, LD.R, LD.NAMES, LD.col, LD.MIX
N, K = len(IDX), len(NAMES)
L = '=' * 100
PX = pd.Series(LD.G.D['px'], index=IDX).astype(float)
QLDR = np.nan_to_num(np.asarray(LD.G.D['qldr'], float))
TB = np.nan_to_num(R[:, col['TBILL']])


def dd_series(r, win=252):
    return LD.dd_of(r, win)


def rule_state(dd, th=-0.16):
    w = np.ones(N); s = 1
    for t in range(N):
        d = dd[t]
        if not np.isnan(d):
            s = 0 if (s == 1 and d <= th) else (1 if (s == 0 and d > th) else s)
        w[t] = s
    return w


def sim_curve(W2, RM2, lo):
    return LD.sim_multi(W2[lo:], RM2[lo:])


def metrics(c, ix):
    m = EC.fullmet(c, idx=ix); m['p05_20'] = EC.p05_20y(c); return m


def blocks_calmar(c, ix, nb=4):
    e = np.linspace(0, len(c), nb + 1).astype(int); out = []
    for a, b in zip(e[:-1], e[1:]):
        out.append(EC.fullmet(c[a:b] / c[a], idx=ix[a:b])['calmar'])
    return out


def curve_B(lo):
    wB = np.asarray(EC.rule_dd(PX, -0.16, -0.16), float)
    return np.asarray(EC.sim2(wB[lo:], QLDR[lo:], MIX[lo:]), float)


def report(title, curves, lo):
    ix = IDX[lo:]
    B = curve_B(lo); mB = metrics(B, ix); bB = blocks_calmar(B, ix)
    print('\n' + L); print(f'{title}  창 {ix[0].date()} ~ {ix[-1].date()} ({(ix[-1]-ix[0]).days/365.25:.1f}년)'); print(L)
    print(f"  {'후보':<46}{'최종':>10}{'vsB':>7}{'CAGR':>8}{'MDD':>8}{'Calmar':>8}{'ΔCal':>8}{'20y p05':>9}{'Δp05':>8}{'블록':>6}  관문")
    res = {}
    for nm, c in curves.items():
        m = metrics(c, ix); bl = blocks_calmar(c, ix); wins = sum(1 for x, y in zip(bl, bB) if x > y)
        d1 = m['calmar'] / mB['calmar'] - 1; dp = m['p05_20'] / mB['p05_20'] - 1 if not np.isnan(m['p05_20']) else np.nan
        g = (d1 > 0.102, (not np.isnan(dp)) and dp >= 0, wins >= 3)
        res[nm] = (m, g)
        tag = '★①②③' if all(g) else ('①' if g[0] else '-') + ('②' if g[1] else '-') + ('③' if g[2] else '-')
        print(f"  {nm:<46}{m['final']:>10,.1f}{m['final']/mB['final']:>6.2f}x{m['cagr']:>7.2f}%{m['mdd']:>7.1f}%{m['calmar']:>8.3f}"
              f"{d1*100:>+7.1f}%{m['p05_20']:>8.2f}배{dp*100:>+7.1f}%{wins:>4d}/4  {tag}")
    print(f"  {'B 소유자 전략':<46}{mB['final']:>10,.1f}{1:>6.2f}x{mB['cagr']:>7.2f}%{mB['mdd']:>7.1f}%{mB['calmar']:>8.3f}{'':>8}{mB['p05_20']:>8.2f}배")
    return res, mB


# ── A 병렬 슬리브 ────────────────────────────────────────────────────────────────
def sleeves(members, weights=None, defense='tbill'):
    """members: [(자산, 배율)]. 각 슬리브 자기 낙폭 규칙. 꺼지면 T-bill(또는 40/40/20)."""
    W = np.zeros((N, K)); Wm = np.zeros(N); Wtb = np.zeros(N)
    RM = R.copy()
    wts = weights or [1.0 / len(members)] * len(members)
    first = 0
    for (k, lev), wt in zip(members, wts):
        r = R[:, col[k]]
        first = max(first, int(np.argmax(~np.isnan(r))))
        dd = dd_series(np.nan_to_num(r))
        st = rule_state(dd)
        if lev == 2:
            RM[:, col[k]] = LD.lev2(r)
        for t in range(N):
            if st[t] == 1:
                W[t, col[k]] += wt
            elif defense == 'mix':
                Wm[t] += wt
            else:
                W[t, col['TBILL']] += wt
    W2 = np.column_stack([W, Wm]); RM2 = np.column_stack([RM, MIX])
    return W2, RM2, first + 252


# ── C 안전자산 단위 낙폭 ─────────────────────────────────────────────────────────
def ratio_rule(denom_r, either=False):
    """신호 = (나스닥 ÷ 분모자산) 의 252일 낙폭. 보유는 B 와 같다."""
    ratio_r = (1 + np.nan_to_num(PX.pct_change().values)) / (1 + np.nan_to_num(denom_r)) - 1
    dd_ratio = dd_series(ratio_r)
    dd_px = dd_series(np.nan_to_num(PX.pct_change().values))
    w = np.ones(N); s = 1
    for t in range(N):
        if either:
            a, b = dd_px[t], dd_ratio[t]
            if np.isnan(a) or np.isnan(b):
                w[t] = s; continue
            s = 0 if (s == 1 and (a <= -0.16 or b <= -0.16)) else (1 if (s == 0 and a > -0.16 and b > -0.16) else s)
        else:
            d = dd_ratio[t]
            if not np.isnan(d):
                s = 0 if (s == 1 and d <= -0.16) else (1 if (s == 0 and d > -0.16) else s)
        w[t] = s
    first = int(np.argmax(~np.isnan(denom_r))) + 252
    return w, first


# ── D 고점 이후 시간 ─────────────────────────────────────────────────────────────
def duration_rule(D, combo=False):
    hi = PX.rolling(252, min_periods=252).max()
    is_high = (PX >= hi).values
    days = np.zeros(N); c = 0
    for t in range(N):
        c = 0 if is_high[t] else c + 1
        days[t] = c
    dd = dd_series(np.nan_to_num(PX.pct_change().values))
    w = np.ones(N); s = 1
    for t in range(N):
        if combo:
            d = dd[t]
            if np.isnan(d):
                w[t] = s; continue
            s = 0 if (s == 1 and (d <= -0.16 or days[t] > D)) else (1 if (s == 0 and d > -0.16 and days[t] <= D) else s)
        else:
            s = 0 if (s == 1 and days[t] > D) else (1 if (s == 0 and days[t] == 0) else s)
        w[t] = s
    return w


def main():
    print(L); print('새 길 탐구 — 병렬 슬리브 · 안전자산 단위 낙폭 · 고점 이후 시간 (규칙 무변경 · 모의 실험)'); print(L)
    allres = {}
    # A
    lo = 252
    cur = {}
    for nm, mem, wts, dfn in [
        ('A1 슬리브 {NDX·SPX} 2배', [('NDX', 2), ('SPX', 2)], None, 'tbill'),
        ('A2 슬리브 {NDX·SPX·금·30년국채}', [('NDX', 2), ('SPX', 2), ('GOLD', 1), ('UST30c', 1)], None, 'tbill'),
        ('A4 NDX 50% + {SPX·금·30년국채} 50%', [('NDX', 2), ('SPX', 2), ('GOLD', 1), ('UST30c', 1)], [0.5, 1 / 6, 1 / 6, 1 / 6], 'tbill'),
        ('A5 A2 + 슬리브 방어 40/40/20', [('NDX', 2), ('SPX', 2), ('GOLD', 1), ('UST30c', 1)], None, 'mix'),
    ]:
        W2, RM2, first = sleeves(mem, wts, dfn); lo = max(lo, first); cur[nm] = (W2, RM2)
    curves = {nm: sim_curve(W2, RM2, lo) for nm, (W2, RM2) in cur.items()}
    resA, _ = report('A 병렬 슬리브 (30년 금리 고시 이후 공통창)', curves, lo)
    W2, RM2, first = sleeves([('NDX', 2), ('SPX', 2), ('RUT', 2)])
    resA3, _ = report('A3 슬리브 {NDX·SPX·RUT} 2배', {'A3 슬리브 {NDX·SPX·RUT} 2배': sim_curve(W2, RM2, first)}, first)
    allres.update(resA); allres.update(resA3)
    # C
    cur = {}; lo = 252
    for nm, den, either in [('C1 ÷금 낙폭', R[:, col['GOLD']], False), ('C3 ÷T-bill 낙폭(초과수익)', TB, False),
                            ('C4 나스닥 또는 ÷금 낙폭 (둘 중 하나)', R[:, col['GOLD']], True)]:
        w, first = ratio_rule(den, either); lo = max(lo, first)
        cur[nm] = np.asarray(EC.sim2(w[lo:], QLDR[lo:], MIX[lo:]), float) if False else w
    curves = {nm: np.asarray(EC.sim2(w[lo:], QLDR[lo:], MIX[lo:]), float) for nm, w in cur.items()}
    resC, _ = report('C 안전자산 단위 낙폭 (1973~)', curves, lo)
    w, first = ratio_rule(R[:, col['UST30c']])
    resC2, _ = report('C2 ÷30년국채 낙폭 (1978~)', {'C2 ÷30년국채 낙폭': np.asarray(EC.sim2(w[first:], QLDR[first:], MIX[first:]), float)}, first)
    allres.update(resC); allres.update(resC2)
    # D
    lo = 252; curves = {}
    for nm, D, combo in [('D1 시간 60일', 60, False), ('D2 시간 120일', 120, False), ('D3 시간 250일', 250, False),
                         ('D4 깊이 −16 또는 시간 120일', 120, True), ('D5 깊이 −16 또는 시간 250일', 250, True)]:
        w = duration_rule(D, combo); curves[nm] = np.asarray(EC.sim2(w[lo:], QLDR[lo:], MIX[lo:]), float)
    resD, _ = report('D 고점 이후 시간 (1973~)', curves, lo)
    allres.update(resD)

    print('\n' + L); print('사전 등록 대조'); print(L)
    def ratio(nm, key):
        return allres[nm][0][key]
    # 창별 B 가 달라 예측은 표의 vsB·ΔCal 로 대조한다
    a_names = [k for k in allres if k.startswith('A')]
    print('  P1 (슬리브 MDD 5~15%p 얕고 · 최종 0.2~0.5× · Calmar 0.8~1.1×): 표의 A 행 참조 — 판정은 아래 요약')
    passed = [k for k, (m, g) in allres.items() if all(g)]
    print(f"  P2·마지막 (①②③ 동시 통과): {passed or '없음'} → {'맞음(없음)' if not passed else '틀림 — 그림자 후보'}")
    print('\n이 측정이 낳은 다음 질문 (§-1 절대멈춤 6):')
    print('  · 슬리브가 Calmar 를 올렸다면 그것은 「분산」의 값이지 「규칙」의 값이 아니다 — 소유자가 감내선을 바꿀 때의 선택지(§7 Q6)와 같은 서랍.')
    print('  · 비율 낙폭·시간 낙폭이 B 와 갈린 전환일이 몇 건인지(사건 단위)가 다음 질문 — 갈린 건수가 적으면 같은 규칙의 다른 표기일 뿐이다.')


if __name__ == '__main__':
    main()
