# -*- coding: utf-8 -*-
"""
[Deflated Sharpe — B 본체, 2026-08-31 소유자 승인] 탐색 벌점을 채택안 자신에게 겨눈다.

배경 — 이 저장소의 두 번째 일관성 구멍:
  audit_stat.py [5] 가 Deflated Sharpe 를 이미 구현했으나 **혼합 스프레드
  (mix40−B)에만** 적용했다. 정작 「500+ 후보에서 골라낸 B 자신」은 한 번도
  탐색 벌점으로 깎아 보지 않았다. PBO(0.437~0.53)는 「선택이 과적합인가」를
  묻고, DSR 은 「N 번 시도 후 남은 성과가 통계적으로 실재하는가」를 묻는다 —
  두 질문은 다르고, 후자가 비어 있었다.

방법: Bailey & López de Prado (2014), "The Deflated Sharpe Ratio",
      Journal of Portfolio Management 40(5).
  E[max SR | 참 SR=0] = σ_SR · [(1−γ)·Z⁻¹(1−1/N) + γ·Z⁻¹(1−1/(N·e))]
  DSR = Z[ (SR − SR₀)·√(T−1) / √(1 − g₃·SR + (g₄−1)/4·SR²) ]
  γ = 오일러-마스케로니 0.5772…, g₃ 왜도, g₄ 첨도(정규=3), SR 은 일간(비연율).

시행 공간: B 가 실제로 선택된 격자 = 진입·복귀 문턱 2차원.
  (k=2 는 문턱과 분리된 결정 — 04 §5-6 「문턱 최적은 배율과 분리」, 국내 상품 제약)

판정 아님 · 전략 무변경. 실행: python research/dsr_b.py
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
from math import erf, sqrt, exp
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
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
EULER = 0.5772156649015329


def ncdf(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def nppf(p):
    """Beasley-Springer-Moro (audit_stat [5] 와 같은 구현)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = sqrt(-2 * np.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = sqrt(-2 * np.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r_ = q * q
    return (((((a[0]*r_+a[1])*r_+a[2])*r_+a[3])*r_+a[4])*r_+a[5])*q / \
           (((((b[0]*r_+b[1])*r_+b[2])*r_+b[3])*r_+b[4])*r_+1)


def rets(a):
    return np.diff(a, prepend=1.0) / np.concatenate(([1.0], a[:-1]))


def sr_of(r):
    return float(np.mean(r) / np.std(r, ddof=1))


def dsr(sr, sr0, r):
    """관측 SR 을 탐색 벌점 sr0 로 깎아 실재 확률을 낸다 (일간 단위)."""
    T = len(r)
    g3 = float(pd.Series(r).skew())
    g4 = float(pd.Series(r).kurt()) + 3.0
    den = sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4.0 * sr * sr))
    return ncdf((sr - sr0) * sqrt(T - 1) / den), g3, g4


def main():
    # ---- 시행 공간: B 가 선택된 문턱 격자 --------------------------------
    ths = [round(-0.24 + 0.01 * i, 2) for i in range(17)]      # -0.24 ~ -0.08
    trials, grid = [], []
    for en in ths:
        for ex in ths:
            if ex < en:                                        # 복귀선은 진입선 이상
                continue
            w = EC.rule_dd(PX, en, ex)
            r = rets(EC.sim2(w, QLDR, MIXR))
            trials.append(sr_of(r))
            grid.append((en, ex))
    trials = np.array(trials)
    N = len(trials)

    wB = EC.rule_dd(PX, -0.16, -0.16)
    rB = rets(EC.sim2(wB, QLDR, MIXR))
    srB = sr_of(rB)
    iB = grid.index((-0.16, -0.16))

    print(f'\n[1] 시행 공간 — 진입×복귀 문턱 격자 {N}칸 (−24%~−8%, 1%p 간격)')
    order = np.argsort(-trials)
    rank = int(np.where(order == iB)[0][0]) + 1
    print(f'  B(−16/−16) 일간 SR {srB:.5f} · 격자 내 순위 {rank}/{N}')
    print(f'  격자 SR 산포 σ {trials.std(ddof=1):.5f} · 최고 {trials.max():.5f} '
          f'({grid[int(order[0])]}) · 중앙 {np.median(trials):.5f}')

    # ---- DSR — 시행 수를 바꿔 가며 -----------------------------------------
    sig = float(trials.std(ddof=1))
    print(f'\n[2] Deflated Sharpe (Bailey & López de Prado 2014)')
    print(f"{'가정 시행수 N':>13} {'E[max SR|H0]':>13} {'DSR':>9}  해석")
    for NN in (N, 210, 500, 1000):
        sr0 = sig * ((1 - EULER) * nppf(1 - 1.0 / NN) +
                     EULER * nppf(1 - 1.0 / (NN * exp(1))))
        d, g3, g4 = dsr(srB, sr0, rB)
        tag = '실재' if d > 0.95 else ('경계' if d > 0.90 else '미달')
        note = {N: '이 격자', 210: 'v48 문턱 격자', 500: '04 서두 500+',
                1000: '보수적 상한'}[NN]
        print(f'{NN:>13} {sr0:>13.5f} {d:>9.3f}  {tag} · {note}')
    _, g3, g4 = dsr(srB, 0.0, rB)
    print(f'  (B 일간수익 왜도 {g3:.3f} · 첨도 {g4:.2f} — 정규 3.0 대비 두꺼운 꼬리)')

    # ---- 참고: 연율 SR 과 문턱 민감도 --------------------------------------
    print(f'\n[3] 참고 — 문턱을 1%p 씩 흔들면 SR 이 얼마나 변하나 (고원 여부)')
    for en in (-0.18, -0.17, -0.16, -0.15, -0.14):
        j = grid.index((en, en))
        print(f'  {en:+.2f}/{en:+.2f}  일간 SR {trials[j]:.5f}  '
              f'연율 {trials[j]*sqrt(252):.3f}')
    print('  → 이웃 칸과 완만하면 첨탑이 아니라 고원 (v50 파라미터 첨탑 지문의 반대)')


if __name__ == '__main__':
    main()
