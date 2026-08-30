# -*- coding: utf-8 -*-
"""
[번외 후속, 소유자 질문 2026-08-31] 배율이 오르면 문턱(−16/−16)도 바뀌어야 하나?
T4 를 고배율에 얹으면 MDD 만 줄이고 수익은 지키나?

축 1: k ∈ {2.0, 2.5, 3.0} × 대칭 문턱 {−10~−22} (+비대칭 −16/−11 참고)
  — 신호는 항상 QQQ 1배 지수 낙폭(현행 구조), 엔진만 lev_r(D,k).
축 2: T4 정본 공식을 k 배 엔진에 일반화 — rv_k = k·std20·√252 (정본의 「2×」가
  자산 배율이므로 충실한 일반화), VT=0.40·투표 ≥2/4 불변, 대기 T-bill.
  퇴화 검산: k=2 가 hypo_t4_real.t4_w 와 오차 0 이어야 함.

⚠ 표본 내 격자 — PBO 0.5 교훈(04 §5-4)대로 「1등 선택」이 아니라 경사 방향만
읽는다. 판정·채택 아님, 동결 무변경. 실행: python research/lev_th.py
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
import hypo_t4_real as R                                # noqa: E402
from axis_lib import lev_r                              # noqa: E402

G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
tb = G.tb
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
px = pd.Series(G.D['px'], index=idx)
r1 = np.nan_to_num(px.pct_change().values)


def p05(a, w=5040):
    return float(np.quantile(a[w:] / a[:-w], 0.05))


def brow(k, ti, to, half=None):
    w = EC.rule_dd(px, ti, to)
    a = EC.sim2(w, np.asarray(lev_r(G.D, k), float), MIXR)
    if half == 1:
        a = a[:n // 2] / a[0]
        return EC.fullmet(a, idx=idx[:n // 2])
    if half == 2:
        a = a[n // 2:] / a[n // 2]
        return EC.fullmet(a, idx=idx[n // 2:])
    m = EC.fullmet(a, tb, idx)
    m['p05'] = p05(a)
    return m


def t4w_k(k):
    """T4 정본(hypo_t4_real.t4_w)의 k 배 일반화 — 「2.0×」만 k 로. k=2 검산 동치."""
    pxs = pd.Series(np.cumprod(1 + r1), index=idx)
    votes = sum((pxs / pxs.shift(L) > 1.0).astype(int) for L in R.LOOKS)
    sd = pd.Series(r1, index=idx).rolling(R.WIN).std(ddof=1)
    rv = k * sd * np.sqrt(252)
    w = np.clip(R.VT / rv.replace(0, np.nan), 0, 1).fillna(0)
    w[votes < R.TH] = 0.0
    w.iloc[:max(R.LOOKS)] = 0.0
    return w.values


def main():
    # 검산: k=2 일반화 == 정본 t4_w
    ref = np.asarray(R.t4_w(G.r_eq1), float)
    mine = t4w_k(2.0)
    err = float(np.max(np.abs(mine - ref)))
    assert err < 1e-12, f'T4 일반화 검산 실패 {err}'
    print(f'[검산] T4 k=2 일반화 == 정본 오차 {err:.1e}  OK')

    # ---- 축 1: k × 문턱 격자 ----
    for k in (2.0, 2.5, 3.0):
        print(f'\n=== k={k} — 문턱 격자 (신호는 1배 지수 · 방어 mix · 대칭, 게이트 도달 시 '
              f'엔진 손실 ≈ {k*16:.0f}%) ===')
        print(f"{'문턱':>9} {'최종배수':>12} {'CAGR':>6} {'MDD':>7} {'Calmar':>7} {'p05':>6}")
        for ti in (-0.10, -0.12, -0.14, -0.16, -0.18, -0.20, -0.22):
            m = brow(k, ti, ti)
            tag = ' ← 현행 문턱' if abs(ti + 0.16) < 1e-9 else ''
            print(f'{ti*100:>4.0f}/{ti*100:>4.0f} {m["final"]:>12.0f} {m["cagr"]:>6.2f} '
                  f'{m["mdd"]:>7.1f} {m["calmar"]:>7.3f} {m["p05"]:>6.1f}{tag}')
        m = brow(k, -0.16, -0.11)
        print(f"{'-16/ -11':>9} {m['final']:>12.0f} {m['cagr']:>6.2f} {m['mdd']:>7.1f} "
              f"{m['calmar']:>7.3f} {m['p05']:>6.1f}  (참고 — v41 기각 계열)")

    # ---- 반쪽 안정성: k=3 에서 얕은 문턱이 이기는 게 시대 산물인지 ----
    print('\n[반쪽 검사] k=3 — 전반(1972~99)/후반(1999~26) Calmar')
    for ti in (-0.10, -0.12, -0.16, -0.20):
        m1, m2 = brow(3.0, ti, ti, half=1), brow(3.0, ti, ti, half=2)
        print(f'  {ti*100:>4.0f}/{ti*100:>4.0f}: 전반 {m1["calmar"]:.3f} · 후반 {m2["calmar"]:.3f}')

    # ---- 축 2: T4 를 k 배에 ----
    print('\n=== T4 정본 일반화 — 엔진 k 배 · 대기 T-bill (정본 규약) ===')
    print(f"{'k':>5} {'최종배수':>12} {'CAGR':>6} {'MDD':>7} {'Calmar':>7} {'p05':>6} {'평균노출':>7}")
    for k in (2.0, 2.5, 3.0):
        wt = t4w_k(k)
        a = EC.sim2(wt, np.asarray(lev_r(G.D, k), float), tb)
        m = EC.fullmet(a, tb, idx)
        print(f'{k:>5.1f} {m["final"]:>12.0f} {m["cagr"]:>6.2f} {m["mdd"]:>7.1f} '
              f'{m["calmar"]:>7.3f} {p05(a):>6.1f} {np.mean(wt):>7.1%}')
    print('  (rv_k = k·std20·√252 → k 가 오르면 VT40 이 노출을 자동 축소 — 실효 배율이'
          '\n   수렴해 「3배의 수익」은 애초에 못 가져간다. 정본 규약의 구조적 귀결)')

    # ---- 축 3 (소유자 후속): 「배수별 최적점 공식」은 가능한가 ----
    yr = pd.Series(idx).dt.year.values
    print('\n=== 켈리 최적 배수 k*=초과수익/분산 — 「공식」의 입력이 시대마다 요동한다 ===')
    for a_, b_ in ((1972, 1980), (1980, 1990), (1990, 2000),
                   (2000, 2010), (2010, 2020), (2020, 2027)):
        m = (yr >= a_) & (yr < b_)
        ex = r1[m] - tb[m]
        mu, var = ex.mean() * 252, np.var(r1[m], ddof=1) * 252
        print(f'  {a_}~{b_-1}: 초과수익 {mu:+.1%} · 변동성 {np.sqrt(var):.0%} → k* = {mu/var:+.1f}')
    ex = r1 - tb
    print(f'  전체 54년: k* = {ex.mean()*252/(np.var(r1,ddof=1)*252):+.1f}  ← 동결 배수 2.0 과 일치')

    print('\n=== T4@k3 의 VT 를 반쪽에 맞추면 (후반 개량 시도의 실측) ===')
    print(f"{'VT':>5} {'전반 Calmar':>10} {'전반배수':>9} {'후반 Calmar':>10} {'후반배수':>9}")
    h = n // 2
    for VTx in (0.30, 0.40, 0.50, 0.60, 0.80):
        pxs = pd.Series(np.cumprod(1 + r1), index=idx)
        votes = sum((pxs / pxs.shift(L) > 1.0).astype(int) for L in R.LOOKS)
        sd = pd.Series(r1, index=idx).rolling(R.WIN).std(ddof=1)
        wv = np.clip(VTx / (3.0 * sd * np.sqrt(252)).replace(0, np.nan), 0, 1).fillna(0)
        wv[votes < R.TH] = 0.0
        wv.iloc[:max(R.LOOKS)] = 0.0
        a = EC.sim2(wv.values, np.asarray(lev_r(G.D, 3.0), float), tb)
        m1 = EC.fullmet(a[:h] / a[0], idx=idx[:h])
        m2 = EC.fullmet(a[h:] / a[h], idx=idx[h:])
        print(f'{VTx*100:>4.0f}% {m1["calmar"]:>10.3f} {m1["final"]:>9.0f} '
              f'{m2["calmar"]:>10.3f} {m2["final"]:>9.0f}')
    print('  (후반 최적이 지표마다 다르고(30% by Calmar · 60% by 부) 어느 VT 도 후반에서'
          '\n   B@2(Calmar 0.499·445배)를 지배하지 못한다 — 다이얼의 문제가 아니라 시대의 문제)')


if __name__ == '__main__':
    main()
