# -*- coding: utf-8 -*-
"""
[번외 최종장, 소유자 제안 2026-08-31] 「5년 투자자에게 합리적인 배율」 —
최적화가 아니라 한계 분석: 어느 k 부터 위험 증가가 수익 증가를 압도하는가.

방법 (임의 가중치 배제):
  A. 5년(1260일) 창 전수 분포의 확실성등가 CE(γ) — γ=1(log)·2·3.
     CE(1)=기하평균, CE(2)=조화평균, CE(3)=(E[m^-2])^(-1/2).
     γ별 argmax k = 「위험회피도 γ 인 5년 투자자의 합리적 배율」.
  B. 한계표: k +0.1 당 Δ(5y 중앙) vs Δ(5y p05)·Δ(5y 최악)·ΔMDD·Δ(00-09)·Δ(지연 잔존)
     — 수익 한계가 위험 한계에 먹히기 시작하는 칸.
  C. 강건성: 반쪽(1972-99 / 1999-26) CE argmax 이동 · 10년 창 CE (지평 연장 효과).
소유자 직관 검증 대상: 「2.0~2.3 과 2.5+ 사이 경계 존재?」
판정 아님 · 국내 실전은 2배 상한(동결) — 미국 진출 k 결정용 연구.
실행: python research/lev_5y.py
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

import eng_common as EC                                 # noqa: E402
from axis_lib import lev_r                              # noqa: E402

G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
wB = np.asarray(G.wB, float)
KS = [round(2.0 + 0.1 * i, 1) for i in range(11)]


def bcurve(k, lag=1):
    r = np.asarray(lev_r(G.D, k), float)
    if lag == 1:
        return EC.sim2(wB, r, MIXR)
    w2 = np.empty(n)
    w2[0] = wB[0]
    w2[1:] = wB[:-1]
    return EC.sim2(w2, r, MIXR)


def ce(m, g):
    if g == 1:
        return float(np.exp(np.mean(np.log(m))))
    return float(np.mean(m ** (1 - g)) ** (1.0 / (1 - g)))


def main():
    W = 1260
    curves = {k: bcurve(k) for k in KS}
    mult = {k: curves[k][W:] / curves[k][:-W] for k in KS}
    i0, i1 = pd.Series(idx).searchsorted([pd.Timestamp('2000-01-01'), pd.Timestamp('2010-01-01')])
    half = (n - W) // 2

    # ---- A. CE 표 ----
    print(f'\n[A] 5년 창 {len(mult[2.0])}개 — 확실성등가 CE(γ) (5년 배수 단위)')
    print(f"{'k':>4} {'중앙':>6} {'p05':>6} {'최악':>6} {'CE(γ=1)':>8} {'CE(γ=2)':>8} {'CE(γ=3)':>8} {'MDD':>7} {'지연잔존':>7}")
    lagret = {}
    for k in KS:
        m = mult[k]
        lagret[k] = bcurve(k, lag=2)[-1] / curves[k][-1]
        print(f'{k:>4.1f} {np.median(m):>6.2f} {np.quantile(m,0.05):>6.2f} {m.min():>6.2f} '
              f'{ce(m,1):>8.3f} {ce(m,2):>8.3f} {ce(m,3):>8.3f} '
              f'{EC.fullmet(curves[k],idx=idx)["mdd"]:>7.1f} {lagret[k]:>7.2f}')
    print('\n  위험회피도 γ → 5년 지평 합리적 k (CE argmax · 괄호는 CE 고원 ±0.005 범위)')
    for g in (1, 1.5, 2, 2.5, 3, 3.5, 4, 5):
        ces = {k: ce(mult[k], g) for k in KS}
        best = max(KS, key=lambda k: ces[k])
        plat = [k for k in KS if ces[k] >= ces[best] - 0.005]
        print(f'  γ={g:<4}: k* = {best:.1f}  (고원 {min(plat):.1f}~{max(plat):.1f})')

    # ---- B. 한계표 ----
    print(f'\n[B] 한계 분석 — k +0.1 당 변화 (수익 한계 vs 위험 한계)')
    print(f"{'구간':>9} {'Δ중앙5y':>8} {'Δp05_5y':>8} {'Δ최악5y':>8} {'ΔMDD':>6} {'Δ00-09':>7} {'Δ지연':>6}")
    for a, b in zip(KS[:-1], KS[1:]):
        dmed = np.median(mult[b]) - np.median(mult[a])
        dp05 = np.quantile(mult[b], 0.05) - np.quantile(mult[a], 0.05)
        dwor = mult[b].min() - mult[a].min()
        dmdd = EC.fullmet(curves[b], idx=idx)['mdd'] - EC.fullmet(curves[a], idx=idx)['mdd']
        e_b = (curves[b][i1] / curves[b][i0]) / (curves[2.0][i1] / curves[2.0][i0])
        e_a = (curves[a][i1] / curves[a][i0]) / (curves[2.0][i1] / curves[2.0][i0])
        print(f'{a:>4.1f}→{b:<4.1f} {dmed:>+8.2f} {dp05:>+8.3f} {dwor:>+8.3f} '
              f'{dmdd:>+6.1f} {e_b-e_a:>+7.2f} {lagret[b]-lagret[a]:>+6.2f}')

    # ---- C. 강건성 ----
    print(f'\n[C] 반쪽 CE(γ=2) — 전반(1972~99) / 후반(1999~26) 5년 창')
    for k in (2.0, 2.2, 2.4, 2.6, 3.0):
        m = mult[k]
        print(f'  k={k:.1f}: 전반 {ce(m[:half],2):.3f} · 후반 {ce(m[half:],2):.3f}')
    for g in (2, 3):
        b1 = max(KS, key=lambda k: ce(mult[k][:half], g))
        b2 = max(KS, key=lambda k: ce(mult[k][half:], g))
        print(f'  γ={g} argmax: 전반 {b1:.1f} · 후반 {b2:.1f}')
    print(f'\n[C2] 지평 연장 — 10년(2520일) 창 CE argmax')
    m10 = {k: curves[k][2520:] / curves[k][:-2520] for k in KS}
    for g in (1, 2, 3):
        best = max(KS, key=lambda k: ce(m10[k], g))
        print(f'  γ={g}: 최적 k = {best:.1f} (CE {ce(m10[best],g):.2f})')


if __name__ == '__main__':
    main()
