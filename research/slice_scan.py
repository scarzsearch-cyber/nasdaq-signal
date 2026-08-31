# -*- coding: utf-8 -*-
"""
[다지평 슬라이스 스캔, 2026-08-31 소유자 제안] 「CT 찍듯 여러 두께로 겹쳐 썰면?」

소유자 통찰 둘 — 둘 다 맞다:
  ① 통짜 최종배수 비교는 **복리 높은 전략이 자동 우승**이다. 경로·낙폭·바닥이 지워진다.
  ② 여러 두께로 겹쳐 썰면 **시작일 편향**이 드러난다. (실제로 오늘 T4@3 오판을 이 방법이
     잡았다 — 04 §5-11 정정: 2010-01-04 하나로 기각했는데 모든 시작일로는 85% 승리)

★ 그러나 슬라이스가 **못** 하는 것 — 이 도구가 승률 옆에 유효표본을 나란히 찍는 이유:
  겹치는 창은 **같은 사건을 공유**한다. 54년에서 7년 창 12,099개를 뽑아도 독립 관측은
  **7.9개**다(horizon_ess.py 실측). 얇게 썬다고 표본이 두꺼워지지 않는다 —
  같은 몸을 여러 각도로 볼 뿐이다. **「N창 중 x%」를 「x% 확률」로 읽으면 안 된다.**

출력: 지평별 승률 · 중앙 배수비 · p05 배수비(최악쪽) · **비중첩 창수** · AR-ESS
사용: python research/slice_scan.py            (기본 비교군)
평가 전용 · 전략 무변경.
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
import hypo_gates as G                                  # noqa: E402
import hypo_t4_real as R                                # noqa: E402
from axis_lib import lev_r                              # noqa: E402

idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
r1 = np.nan_to_num(PX.pct_change().values)
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
TB = np.asarray(G.tb, float)
wB = EC.rule_dd(PX, -0.16, -0.16)
Y = 252
HS = [3, 5, 7, 10, 13, 15, 17, 20, 25]


def t4w_k(k):
    pxs = pd.Series(np.cumprod(1 + r1), index=idx)
    votes = sum((pxs / pxs.shift(L) > 1.0).astype(int) for L in R.LOOKS)
    sd = pd.Series(r1, index=idx).rolling(R.WIN).std(ddof=1)
    w = np.clip(R.VT / (k * sd * np.sqrt(252)).replace(0, np.nan), 0, 1).fillna(0)
    w[votes < R.TH] = 0.0
    w.iloc[:max(R.LOOKS)] = 0.0
    return w.values


def sim_t4(k):
    w = t4w_k(k); r = np.asarray(lev_r(G.D, k), float)
    pos = np.empty(n); pos[:1] = w[0]; pos[1:] = w[:-1]
    rr = pos * np.nan_to_num(r) + (1 - pos) * TB; rr[0] = 0.0
    return np.cumprod((1 + rr) * (1 - EC.COST * np.abs(np.diff(pos, prepend=pos[0]))))


def ar_ess(v):
    N = len(v); x = v - v.mean()
    ac = np.correlate(x, x, 'full')[N - 1:] / (x @ x)
    k, s = 1, 0.0
    while k < N and ac[k] > 0.05:
        s += ac[k]; k += 1
    return N / (1 + 2 * s)


def scan(aA, aB, lab, start=None):
    lo = 0 if start is None else int(np.searchsorted(idx, pd.Timestamp(start)))
    A = np.asarray(aA[lo:], float); B = np.asarray(aB[lo:], float)
    m = len(A)
    span = (idx[-1] - idx[lo]).days / 365.25
    print(f'\n[{lab}]  구간 {idx[lo].date()}~{idx[-1].date()} ({span:.1f}년)')
    print(f"{'지평':>5} {'창수':>7} {'승률':>7} {'중앙':>8} {'p05':>8} {'최악':>8} "
          f"{'비중첩':>7} {'AR-ESS':>8}")
    for h in HS:
        w = h * Y
        if m - w < 60:
            continue
        ra = A[w:] / A[:-w]
        rb = B[w:] / B[:-w]
        rat = ra / rb
        print(f'{h:>4}년 {len(rat):>7} {np.mean(rat > 1):>6.0%} '
              f'{np.median(rat):>7.2f}배 {np.quantile(rat, 0.05):>7.2f}배 '
              f'{rat.min():>7.2f}배 {span/h:>6.1f}개 {ar_ess(rat):>7.1f}개')


def main():
    aB2 = EC.sim2(wB, np.asarray(lev_r(G.D, 2.0), float), MIXR)
    aT3 = sim_t4(3.0)
    a2x = np.cumprod(1 + np.asarray(lev_r(G.D, 2.0), float))

    print('=' * 78)
    print(' 다지평 슬라이스 — 승률 옆의 「비중첩」이 진짜 표본 수다')
    print(' 승률 85% 라도 비중첩이 1.3개면 「85% 확률」이 아니라 「한 경로에서 85%」다')
    print('=' * 78)

    scan(aT3, aB2, 'T4@3 ÷ B@2 · 54년 전체')
    scan(aT3, aB2, 'T4@3 ÷ B@2 · 2000~ (현대만)', '2000-01-03')
    scan(aB2, a2x, 'B@2 ÷ 2배 맨몸 · 54년 전체 (대조군)')

    print('\n[읽는 법]')
    print('  · **승률**: 그 지평의 모든 시작일 중 A 가 B 를 이긴 비율. 시작일 편향을 잡는다.')
    print('  · **p05·최악**: 나쁜 쪽 꼬리. 통짜 비교가 지우는 정보가 여기 있다.')
    print('  · **비중첩**: 구간연수 ÷ 지평. **이것이 독립 관측 수의 상한**이다.')
    print('  · **AR-ESS**: 자기상관을 반영한 유효표본. 비중첩과 이 값 사이가 실제 신뢰 구간.')
    print('\n[한계 — 반드시 같이 읽을 것]')
    print('  · 겹치는 창은 같은 사건을 공유한다. 창을 늘려도 **사건 수는 안 늘어난다.**')
    print('  · 지평이 길수록 비중첩이 급감한다(20년 = 2.7개). 장기 결론일수록 근거가 얇다.')
    print('  · 이 표로 **채택을 결정하지 말 것** — 시작일 편향 검출용이다(04 §5-11 용도).')


if __name__ == '__main__':
    main()
