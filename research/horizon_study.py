# -*- coding: utf-8 -*-
"""
[지평 연구, 소유자 지시 2026-08-31] 「내 수명은 유한하다 — 3~20년만 연구하라」.

  A. 현행 B(2배, 실물 체인) — 지평 3/5/7/10/15/20년 창 전수:
     손실 창 비중 · p05 · 중앙 · 최악 · B가 맨몸2배/헤지6/4를 이긴 창 비중
     (헤지6/4 근사 = 공격다리 0.6·QLD+0.4·배당 일일 리밸런스, 같은 −16 규칙 —
      실전은 월 1회 재조정이라 근사임을 명시)
  B. 지평 × 위험회피 γ → 합리적 배율 k* (CE argmax, 합성 잣대 k=1.5~3.0):
     lev_5y 의 5년 지도를 3~20년 전 지평으로 확장.
판정 아님 · 국내 실전 2배 동결 — 지평 설계·미국 진출 결정용.
실행: python research/horizon_study.py
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
DIVR = np.nan_to_num(np.asarray(G.D['schdr'], float))
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
wB = np.asarray(G.wB, float)
HS = [(756, '3년'), (1260, '5년'), (1764, '7년'), (2520, '10년'),
      (3780, '15년'), (5040, '20년')]


def ce(m, g):
    if g == 1:
        return float(np.exp(np.mean(np.log(m))))
    return float(np.mean(m ** (1 - g)) ** (1.0 / (1 - g)))


def main():
    aB = EC.sim2(wB, QLDR, MIXR)
    aH = np.cumprod(1 + QLDR)
    r_hed = 0.6 * QLDR + 0.4 * DIVR
    aHd = EC.sim2(wB, r_hed, MIXR)

    print('\n[A] 현행 B(2배·실물 체인) — 지평별 겹친 창 전수 (54년 검증 표본)')
    print(f"{'지평':>5} {'창수':>6} {'비중첩':>7} {'손실창':>8} {'p05':>6} {'중앙':>7} {'최악':>6} "
          f"{'B>맨몸창':>9} {'B>헤지창':>9}")
    span_years = (idx[-1] - idx[0]).days / 365.25
    for w, lab in HS:
        mb = aB[w:] / aB[:-w]
        mh = aH[w:] / aH[:-w]
        md = aHd[w:] / aHd[:-w]
        print(f'{lab:>5} {len(mb):>6} {span_years/(w/252):>6.1f}개 {np.mean(mb < 1):>8.1%} {np.quantile(mb, 0.05):>5.2f}배 '
              f'{np.median(mb):>6.2f}배 {mb.min():>5.2f}배 {np.mean(mb > mh):>9.1%} '
              f'{np.mean(mb > md):>9.1%}')
    print('  ※ 겹친 창의 비율은 이 한 역사경로에서 관측된 몫이지 미래 확률이 아니다. 비중첩은 독립 표본 수의 상한이다.')

    # 최악 창의 정체 (지평별 최악 시작 시점)
    print('\n  지평별 최악 창의 시작 시점:')
    for w, lab in HS:
        mb = aB[w:] / aB[:-w]
        i = int(np.argmin(mb))
        print(f'  {lab}: {str(idx[i].date())} 시작 → {mb[i]:.2f}배')

    # ---- B. 지평 × γ → k* (합성 잣대) ----
    KS = [round(1.5 + 0.1 * i, 1) for i in range(16)]
    curves = {k: EC.sim2(wB, np.asarray(lev_r(G.D, k), float), MIXR) for k in KS}
    print('\n[B] 지평 × 위험회피 γ → 합리적 배율 k* (CE argmax · 합성 잣대 1.5~3.0)')
    print(f"{'지평':>5} {'γ=2 (덜 보수)':>14} {'γ=3 (보수 표준)':>15} {'γ=4 (매우 보수)':>15}")
    for w, lab in HS:
        mult = {k: curves[k][w:] / curves[k][:-w] for k in KS}
        row = f'{lab:>5}'
        for g in (2, 3, 4):
            ces = {k: ce(mult[k], g) for k in KS}
            best = max(KS, key=lambda k: ces[k])
            plat = [k for k in KS if ces[k] >= ces[best] - 0.005]
            row += f'   {best:.1f} ({min(plat):.1f}~{max(plat):.1f})'
        print(row)
    print('  (γ=3 열이 「보수적 개인」의 표준 답 — 지평이 길수록 합리적 배율이 오른다)')


if __name__ == '__main__':
    main()
