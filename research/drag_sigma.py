# -*- coding: utf-8 -*-
"""
[변동성 드래그의 σ 의존성, 2026-08-31 소유자 승인] 상수 가정이 B 평가를 왜곡하는가.

배경: 03_System_Params 는 2배 합성 드래그를 **연 3.30% 상수**로 차감한다
  (`eng_common.synth2x` = 2r − c_daily, c_daily 는 **스칼라**).
  이론은 상수가 아니라 실현분산 비례를 말한다 — Avellaneda & Zhang (2010),
  "Path-Dependence of Leveraged ETF Returns", SIAM J. Financial Math 1, 586–603:
  배율 β 누적수익에 (β−β²)/2 · 실현분산 항. β=2 면 계수 −1 → **드래그 ≈ σ²**.

실험: 합성 백필 구간의 드래그 **총량은 고정**하고 **시점 분포만** σ² 비례로 바꾼다
  (κ·σ²_t, 실제로 상수가 쓰인 합성일 평균이 기존 상수와 일치하도록 κ 보정).
  총량을 고정하므로 「수준」이 아니라 **「타이밍」**만 본다 — 고변동일에 드래그를
  몰아주면 B 평가가 달라지는가?

평가 전용 · 전략 무변경 · 동결 규칙 무접촉. 실행: python research/drag_sigma.py
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

G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
R1 = np.nan_to_num(PX.pct_change().values)
CD = float(G.D['c_daily'])
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
TH = -0.16


def run(qldr):
    w = EC.rule_dd(PX, TH, TH)
    a = EC.sim2(w, qldr, MIXR)
    m = EC.fullmet(a, idx=idx)
    p05 = float(np.quantile(a[5040:] / a[:-5040], 0.05))
    return a, m['final'], m['mdd'], m['calmar'], p05


def main():
    # ---- [1] 사실 확인 ------------------------------------------------------
    var_ann = float(np.nanvar(R1)) * 252
    print(f'\n[1] 현행 드래그의 정체')
    print(f'  c_daily 는 시계열이 아니라 **스칼라** {CD:.8f} → 연율 {CD*252:.2%}')
    print(f'  전체 연율 분산 σ² = {var_ann:.2%} (σ = {np.sqrt(var_ann):.1%})')
    print(f'  이론(β=2) 드래그 ≈ σ² = {var_ann:.2%} vs 실측 {CD*252:.2%} '
          f'→ 비율 {CD*252/var_ann:.2f}')
    print('  → 순수 분산드래그 공식은 실제 QLD 드래그를 **과대평가**한다(0.63배).')
    print('     이산 일간 재설정·추적 상쇄 때문 — 실측 상수가 이론보다 보수적이지 않다.')

    # ---- [1-b] ★핵심 발견: qldr 은 전 구간 합성이 아니다 --------------------
    syn_all = EC.synth2x(R1, CD)
    SYN = np.abs(syn_all - QLDR) <= 1e-10          # 합성이 쓰인 날 = 상수가 적용된 날
    yr = pd.Series(~SYN, index=idx).groupby(idx.year // 10 * 10).mean() * 100
    print(f'\n[1-b] ★ qldr 은 전 구간 합성이 아니다 — 상수는 일부 구간에만 적용된다')
    print('  실물(비합성) 비율: ' + ' · '.join(f'{int(k)}s {v:.0f}%' for k, v in yr.items()))
    print(f'  합성 구간 {SYN.sum():,}일 ({idx[SYN][0].date()}~{idx[SYN][-1].date()}) · '
          f'실물 구간 {(~SYN).sum():,}일')
    print('  → QLD 상장(2006) 이후는 **실물 수익**이라 진짜 시변 드래그가 이미 내장돼 있다.')
    print('     상수 가정의 영향은 **합성 백필 구간에 한정**된다.')

    # ---- [2] 시변 드래그 구성 (총량 고정) -----------------------------------
    v20 = pd.Series(R1).rolling(20, min_periods=5).std().values
    s2 = np.nan_to_num(v20 ** 2, nan=float(np.nanmean(v20 ** 2)))
    kappa = CD / float(np.mean(s2[SYN]))                # 실제 상수가 쓰인 합성구간 총량 고정
    c_t = kappa * s2
    assert np.isclose(np.mean(c_t[SYN]), CD), '합성구간 드래그 총량 보정 실패'
    print(f'\n[2] 시변 드래그 c_t = κ·σ²_t  (κ={kappa:.3f}, 합성구간 평균 일치 '
          f'{np.mean(c_t[SYN])*252:.2%} ≡ {CD*252:.2%})')
    print(f'  분위별 연율 드래그: 최저20% {np.quantile(c_t,0.1)*252:.2%} · '
          f'중앙 {np.median(c_t)*252:.2%} · 최고10% {np.quantile(c_t,0.9)*252:.2%} · '
          f'최대 {c_t.max()*252:.1%}')

    # ---- [3] B 재평가 — 합성 구간에만 시변 드래그 적용 ----------------------
    #   실물 QLD 수익을 모형으로 덮어쓰면 실측을 버리는 것이다. 합성 구간만 바꾼다.
    q_tv = QLDR.copy()
    q_tv[SYN] = EC.synth2x(R1, c_t)[SYN]
    print('\n[3] 드래그 타이밍만 바꾸면 B 가 얼마나 움직이나 (합성 구간에만 적용)')
    print(f"{'드래그 모형':>22} {'최종배수':>13} {'MDD':>8} {'Calmar':>8} {'20년 p05':>10}")
    _, f0, m0, c0, p0 = run(QLDR)
    print(f'{"상수 3.30% (현행)":>22} {f0:>13,.1f} {m0:>7.1f}% {c0:>8.3f} {p0:>9.1f}배')
    _, f1, m1, c1, p1 = run(q_tv)
    print(f'{"κ·σ²_t (합성만 시변)":>22} {f1:>13,.1f} {m1:>7.1f}% {c1:>8.3f} {p1:>9.1f}배')
    print(f'{"차이":>22} {f1/f0-1:>12.1%} {m1-m0:>+7.1f}p {c1-c0:>+8.3f} '
          f'{p1/p0-1:>9.1%}')
    # 21세기 기준(v131 공표 프레임)에서는 실물이라 영향이 더 작다
    i0 = int(np.searchsorted(idx, pd.Timestamp('2000-01-03')))
    a0, a1 = run(QLDR)[0], run(q_tv)[0]
    print(f'  2000~ 구간만: 상수 {a0[-1]/a0[i0]:,.1f}배 vs 시변 {a1[-1]/a1[i0]:,.1f}배 '
          f'(차이 {(a1[-1]/a1[i0])/(a0[-1]/a0[i0])-1:+.1%})')

    # ---- [4] 왜 그런가 — 게이트가 고변동을 이미 걷어낸다 --------------------
    wB = EC.rule_dd(PX, TH, TH)
    att = wB > 0.5
    print('\n[4] 원인 — B 가 공격을 유지하는 동안의 변동성')
    print(f'  전체 평균 σ(20일)   {np.nanmean(v20)*np.sqrt(252):.1%}')
    print(f'  공격 구간 평균 σ    {np.nanmean(v20[att])*np.sqrt(252):.1%}  ({att.sum():,}일)')
    print(f'  방어 구간 평균 σ    {np.nanmean(v20[~att])*np.sqrt(252):.1%}  ({(~att).sum():,}일)')
    print(f'  공격 구간 시변 드래그 평균 {np.mean(c_t[att])*252:.2%} vs 상수 {CD*252:.2%}')
    print('  → 게이트가 고변동 국면을 방어로 보내므로, 시변 모형으로 바꾸면 공격 구간의')
    print('     드래그가 오히려 **낮아진다**. 상수 가정은 B 에게 불리한 쪽으로 틀려 있다.')


if __name__ == '__main__':
    main()
