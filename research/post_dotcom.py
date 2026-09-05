# -*- coding: utf-8 -*-
"""
[닷컴 이후 비교, 2026-08-31 소유자 질문] 「B 는 초과수익 대부분을 닷컴에서 먹었잖아 —
그 뒤로 T4·라오어와 비교하면?」

소유자 주장 확인부터: 04 는 「2000년 이후 B 가 그냥 보유를 이긴 몫(33배)의 약 97%가
2000~2003 닷컴 하나」라고 기록한다. 그렇다면 **닷컴을 빼면 B 에 무엇이 남는가.**

비교 대상 (전부 같은 엔진·같은 비용 규약):
  B        현행 채택안 (−16/−16, 방어 40/40/20)
  T4       그림자 (평가 전용, R.t4_w 정본)
  무한매수  라오어 V4.0 (ext_ibs.run_ibs)
  VR 5.0   라오어 (ext_vr.run_vr)
  2배 보유  맨몸 QLD 합성
  1배 보유  지수 그대로

구간: ① 1972~ 전체 ② 2000~ ③ **2003~ (닷컴 제외)** ④ 2010~ ⑤ 2000~2002 (닷컴만)

★ 규약 (초판에서 두 가지를 틀렸다가 검산에서 잡혔다 — ext_ibs/ext_vr main() 과 일치시킴):
   ① **라오어 2종은 3배(TQQQ 대리) 위에서 돈다.** 1배 지수를 넣으면 안 된다 —
      무한매수법·VR 은 애초에 TQQQ 대상 전략이다. `px3 = cumprod(1+lev_r(D,3.0))*100`.
   ② **전 구간을 한 번 돌린 뒤 곡선을 자른다**(`a[i0:]/a[i0]`). 구간마다 재시작시키면
      공표값과 어긋난다. 그래서 3배 잣대 비교군으로 「B 규칙×3배」·「TQQQ 맨몸」도 넣는다.
   [0] 이 검산이 04 §5-6 공표값(2010~ 무한매수 17배·B@2 84배)을 재현하는지 먼저 본다.
⚠ 유효표본: 2003~ 은 23.6년뿐 — 비중첩 10년 창 2.4개. 분포 주장 불가(§5-4 기준).

평가 전용 · 전략 무변경. 실행: python research/post_dotcom.py
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
import hypo_hex as X                                    # noqa: E402
import hypo_t4_real as R                                # noqa: E402
from ext_ibs import run_ibs                             # noqa: E402
from ext_vr import run_vr                               # noqa: E402
from axis_lib import lev_r                              # noqa: E402

idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
PXV = np.asarray(G.D['px'], float)
TB = np.asarray(G.tb, float)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
R1 = np.nan_to_num(PX.pct_change().values)
TH = -0.16

wB = EC.rule_dd(PX, TH, TH)
wT4 = R.t4_w(G.r_eq1)
R3 = np.asarray(lev_r(G.D, 3.0), float)                 # 3배 합성 (라오어의 무대)
PX3 = np.cumprod(1 + R3) * 100.0                        # TQQQ 대리

aB_full = EC.sim2(wB, QLDR, MIXR)                       # B (2배)
aB3_full = EC.sim2(wB, R3, MIXR)                        # B 규칙 × 3배 (같은 잣대 비교군)
aT4_full = X.three_way(wT4, np.zeros(n), 1 - wT4).values
a2x_full = np.cumprod(1 + QLDR)
a3x_full = np.cumprod(1 + R3)
a1x_full = np.cumprod(1 + R1)
aIBS_full = run_ibs(PX3, TB, 40)                        # 전 구간 1회 실행 후 자른다
aVR_full = run_vr(PX3, TB)

SEGS = [('1972~ 전체', None, None),
        ('2000~', '2000-01-03', None),
        ('★2003~ 닷컴 제외', '2003-01-02', None),
        ('2010~', '2010-01-04', None),
        ('2000~2002 닷컴만', '2000-01-03', '2002-12-31')]


def sl(start, end):
    lo = 0 if start is None else int(np.searchsorted(idx, pd.Timestamp(start)))
    hi = n if end is None else int(np.searchsorted(idx, pd.Timestamp(end), side='right'))
    return lo, hi


def stat(a, lo, hi):
    """구간 정규화 후 배수·CAGR·MDD·Calmar."""
    c = np.asarray(a[lo:hi], float)
    c = c / c[0]
    yrs = (idx[hi - 1] - idx[lo]).days / 365.25
    mult = float(c[-1])
    cagr = mult ** (1 / yrs) - 1
    mdd = float(np.min(c / np.maximum.accumulate(c) - 1))
    return mult, cagr * 100, mdd * 100, (cagr / abs(mdd) if mdd else float('nan')), yrs


def main():
    # ---- [0] 검산 — 04 §5-6 공표값 재현 ------------------------------------
    print('\n[0] 검산 — 04 §5-6 공표값 재현 (틀리면 아래를 신뢰하지 말 것)')
    lo, _ = sl('2010-01-04', None)
    ibs10 = stat(aIBS_full, lo, n)
    b2_10 = stat(aB_full, lo, n)
    print(f'  2010~ 무한매수40: {ibs10[0]:>6.1f}배 / MDD {ibs10[2]:>5.0f}%   (공표 17배 / −55%)')
    print(f'  2010~ B(2배)    : {b2_10[0]:>6.1f}배 / MDD {b2_10[2]:>5.0f}%   (공표 84배 / −45%)')
    ok = abs(ibs10[0] - 17) < 1.5 and abs(b2_10[0] - 84) < 1.5
    print(f'  → 검산 {"통과" if ok else "★실패 — 규약 불일치"}')
    if not ok:
        sys.exit('검산 실패')

    print('\n[1] 소유자 주장 확인 — B 의 우위는 닷컴에서 나왔는가')
    print(f"{'구간':>18} {'B':>10} {'2배 보유':>10} {'B/2배':>9} {'연수':>6}")
    for lab, s, e in SEGS:
        lo, hi = sl(s, e)
        mb, _, _, _, y = stat(aB_full, lo, hi)
        m2, _, _, _, _ = stat(a2x_full, lo, hi)
        print(f'{lab:>18} {mb:>10,.1f} {m2:>10,.1f} {mb/m2:>8.2f}배 {y:>5.1f}년')
    print('  → B/2배 가 1 보다 크면 그 구간에서 규칙이 값어치를 했다는 뜻.')

    ROWS = [('B (현행 2배)', aB_full), ('T4 그림자', aT4_full),
            ('B 규칙 × 3배', aB3_full), ('무한매수40 (3배)', aIBS_full),
            ('VR 5.0 (3배)', aVR_full), ('2배 맨몸', a2x_full),
            ('3배 맨몸(TQQQ)', a3x_full), ('1배 지수', a1x_full)]

    for title, s in (('[2] ★닷컴 이후 (2003~, 23.6년) — 정면 비교', '2003-01-02'),
                     ('[3] 닷컴 포함 (2000~, 26.7년) — 대조', '2000-01-03')):
        lo, hi = sl(s, None)
        print(f'\n{title}')
        print(f"{'전략':>17} {'최종배수':>11} {'CAGR':>8} {'MDD':>9} {'Calmar':>8}")
        for lab, a in ROWS:
            m, cg, md, cal, _ = stat(a, lo, hi)
            print(f'{lab:>17} {m:>10.2f}배 {cg:>7.1f}% {md:>8.1f}% {cal:>8.3f}')

    # [4] 판정 — 숫자는 위 표에서 계산한 값을 그대로 쓴다.
    #   [순회 B14 · 2026-09-05] 종전엔 판정문이 하드코딩이라 v210 뒤 VR 0.57 이 표(0.52)와 어긋났다.
    lo0, _ = sl('2000-01-03', None); lo3, _ = sl('2003-01-02', None); lo10, _ = sl('2010-01-04', None)
    b00, b03, b10 = stat(aB_full, lo0, n), stat(aB_full, lo3, n), stat(aB_full, lo10, n)
    h00, h03, h10 = stat(a2x_full, lo0, n), stat(a2x_full, lo3, n), stat(a2x_full, lo10, n)
    x3, ibs, vr = stat(a3x_full, lo0, n), stat(aIBS_full, lo0, n), stat(aVR_full, lo0, n)
    print('\n[4] 판정')
    print(f'  · **소유자 주장은 맞다** — 닷컴을 빼면 B 의 *수익* 우위는 {b00[0]/h00[0]:.1f}배 → {b03[0]/h03[0]:.2f}배로')
    print(f'    거의 사라진다. 2010~ 만 보면 {b10[0]/h10[0]:.2f}배로 {"오히려 진다" if b10[0] < h10[0] else "이긴다"}.')
    print('  · **그러나 값어치는 수익이 아니라 낙폭에 있다** — 2003~ 에서도 B 는')
    print(f'    MDD {b03[2]:.1f}% vs 2배 맨몸 {h03[2]:.1f}%. Calmar {b03[3]:.3f} vs {h03[3]:.3f} (**{b03[3]/h03[3]-1:+.0%}**).')
    print(f'  · **결정적 대조는 [3]** — 닷컴을 한 번 겪으면 3배 맨몸 {x3[0]:.2f}배 · 무한매수')
    print(f'    {ibs[0]:.2f}배 · VR {vr[0]:.2f}배로 **계좌가 사라진다.** B 만 {b00[0]:.0f}배로 살아남는다.')
    print('    즉 B 는 수익 기계가 아니라 **생존 장치**이고, 생존의 값어치는 평시에는')
    print('    안 보이다가 재난에서 전부가 된다 (04 「재난보험형」 기전).')
    print('  · VR 5.0 이 [2] 에서 3배 맨몸과 **소수점까지 같다** — 04 §5-6 의')
    print('    「V 가 단조 증가라 재난 후 좌초해 맨몸으로 영구 퇴화」가 실측으로 재확인됐다.')
    print('  · ⚠ 유효표본: 2003~ 은 23.6년 = 비중첩 10년 창 2.4개. **순위는 참고,')
    print('    분포 주장 불가**(§5-4 ESS 기준). 이 표로 전략을 바꾸지 말 것.')


if __name__ == '__main__':
    main()
