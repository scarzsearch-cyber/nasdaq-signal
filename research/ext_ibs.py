# -*- coding: utf-8 -*-
"""
[외부 전략 비교, 소유자 요청 2026-08-31] 라오어 무한매수법 V4.0 (quantstack.app
문서 기준) vs 현행 B — 같은 54년 잣대.

구현 사양 (quantstack.app/infinite/v4-0-normal · v4-0-reverse, 2026-08-26 판):
  대상 TQQQ(=lev_r(D,3) 합성, 실물 2010~ 이전은 합성 — 금지5 표기) · N=40/20분할.
  일반모드: 별% = 15 − (30/N)·T, 별지점 = 평단×(1+별%/100).
    1회매수금 = 잔금/(N−T). 첫 매수(보유 0)는 사실상 MOC — 종가 전액 체결.
    전반전(T<N/2): 절반은 별지점 LOC(종가≤별지점 시 체결), 절반은 평단 LOC.
    후반전: 전액 별지점 LOC. 매수 체결 → T+1 (반체결 +0.5).
    매도: 보유 1/4 별지점 LOC매도(종가≥별지점 → 종가 체결, T×0.75),
          나머지 3/4 평단+15% 지정가(종가≥한계 → 한계가 체결. 1/4도 같은 날
          별지점 충족이므로 전량 청산 = 사이클 종료 → 익일 전액 재시작(즉시 복리)).
    T > N−1 → 리버스모드.
  리버스모드: 첫날 보유×(2/N) MOC 매도(T×=1−2/N). 이후 별지점R=직전 5종가 평균.
    종가≥별지점R → 보유×(2/N) 매도(T×=1−2/N) · 종가<별지점R → 잔금/4 매수
    (T += (N−T)/4). 종료: 종가 > 평단×0.85 → 익일 일반모드 (T 승계).
근사 (종가 데이터 한계 — 전부 문서화):
  일중 고저 없음 → 지정가 +15%는 종가≥한계일 때 한계가 체결(보수적),
  「큰수·아래 단계 LOC 사다리」는 당일 1회 체결로 근사, 주식 소수점 허용,
  대기 현금은 T-bill 이자(실무 RP — IBS 에 관대), 편도 비용 0.1%.
검산: 단조 상승 가상 경로에서 「매집→+15% 청산」 반복, 보유 0 미만/현금 음수 불가.
판정 아님 · 전략 무변경. 실행: python research/ext_ibs.py
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

COST = 0.001


def run_ibs(px, tb, N=40):
    """무한매수법 V4.0 — 종가 배열 px 위 시뮬. 반환: 계좌가치 곡선(np.ndarray)."""
    n = len(px)
    star_hi, slope = 15.0, 30.0 / N                     # 별% = 15 − (30/N)·T
    qsell_fr = 2.0 / N                                  # 리버스 등비 매도율
    cash, sh, avg, T = 1.0, 0.0, 0.0, 0.0
    mode = 'n'
    rv_first = False
    vals = np.empty(n)
    for i in range(n):
        c = px[i]
        cash *= (1 + tb[i])                             # 대기 현금 이자 (관대)
        if mode == 'n':
            if sh <= 1e-15:                             # 사이클 시작 — 사실상 MOC
                amt = cash / (N - T) if T < N - 1 else cash
                amt = min(amt, cash)
                if amt > 0:
                    f = amt / c
                    sh, avg = f, c
                    cash -= amt * (1 + COST)
                    T += 1.0
            else:
                star = avg * (1 + (star_hi - slope * T) / 100.0)
                lim = avg * 1.15
                if c >= lim:                            # 전량 청산 (3/4 한계가 + 1/4 종가)
                    cash += sh * 0.75 * lim * (1 - COST) + sh * 0.25 * max(c, star) * (1 - COST)
                    sh, avg, T = 0.0, 0.0, 0.0
                elif c >= star:                         # 쿼터매도
                    cash += sh * 0.25 * c * (1 - COST)
                    sh *= 0.75
                    T *= 0.75
                else:                                   # 매수 구간
                    one = cash / max(N - T, 1.0)
                    buy = 0.0
                    half = T < N / 2.0
                    if half:
                        if c <= star:
                            buy += one * 0.5
                        if c <= avg:
                            buy += one * 0.5
                    else:
                        if c <= star:
                            buy = one
                    buy = min(buy, cash / (1 + COST))
                    if buy > 1e-15:
                        f = buy / c
                        avg = (avg * sh + buy) / (sh + f)
                        sh += f
                        cash -= buy * (1 + COST)
                        T += 1.0 if (not half or buy >= one * 0.999) else 0.5
                if T > N - 1:
                    mode, rv_first = 'r', True
        else:                                           # 리버스모드
            if rv_first:
                q = sh * qsell_fr
                cash += q * c * (1 - COST)
                sh -= q
                T *= (1 - qsell_fr)
                rv_first = False
            else:
                starR = np.mean(px[max(0, i - 5):i]) if i >= 1 else c
                if c >= starR:
                    q = sh * qsell_fr
                    cash += q * c * (1 - COST)
                    sh -= q
                    T *= (1 - qsell_fr)
                else:
                    buy = min(cash / 4.0, cash / (1 + COST))
                    if buy > 1e-15:
                        f = buy / c
                        avg = (avg * sh + buy) / (sh + f) if sh > 0 else c
                        sh += f
                        cash -= buy * (1 + COST)
                        T += (N - T) * 0.25
            if avg > 0 and c > avg * 0.85:
                mode = 'n'                              # 익일 일반모드 (T 승계)
        vals[i] = cash + sh * c
        assert cash > -1e-9 and sh > -1e-12
    return vals


def _check():
    # 단조 상승 경로: 매집 후 +15% 청산 반복 — 현금·보유 건전성
    px = np.cumprod(np.full(600, 1.004)) * 100
    tb0 = np.zeros(600)
    v = run_ibs(px, tb0)
    assert v[-1] > 1.0, v[-1]
    # 급락 경로: −0.5%/일 600일 — 소진→리버스 진입 후에도 파산 없음
    px2 = np.cumprod(np.full(600, 0.995)) * 100
    v2 = run_ibs(px2, tb0)
    assert 0 < v2[-1] < 1.0
    print(f'[검산] 상승 경로 최종 {v[-1]:.3f}(>1) · 급락 경로 최종 {v2[-1]:.3f}(파산 없음)  OK')


def main():
    G, X = EC.selfcheck()
    _check()
    idx = G.idx
    n = len(idx)
    tb = G.tb
    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    r3 = np.asarray(lev_r(G.D, 3.0), float)
    px3 = np.cumprod(1 + r3) * 100.0                    # TQQQ 대리 (합성 잣대)
    aI40 = run_ibs(px3, tb, 40)
    aI20 = run_ibs(px3, tb, 20)
    aB2 = EC.sim2(np.asarray(G.wB, float), np.nan_to_num(np.asarray(G.D['qldr'], float)), MIXR)
    aB3 = EC.sim2(np.asarray(G.wB, float), r3, MIXR)
    aH3 = np.cumprod(1 + r3)

    rows = [('무한매수 40분할', aI40), ('무한매수 20분할', aI20),
            ('현행 B (2배)', aB2), ('B 규칙 × 3배', aB3), ('TQQQ 맨몸', aH3)]

    for s, lab in (('1972-02-07', '전창 54년 (합성 잣대 — 재난 3회 포함)'),
                   ('2000-01-01', '2000~ (닷컴부터)'),
                   ('2010-01-01', '2010~ (실물 TQQQ 시대 = 사이트 백테스트 구간)')):
        i0 = int(pd.Series(idx).searchsorted(pd.Timestamp(s)))
        print(f'\n=== {lab} ===')
        print(f"{'전략':<14} {'최종배수':>12} {'CAGR':>7} {'MDD':>7} {'Calmar':>7} {'물속(년)':>7}")
        for nm, a in rows:
            seg = a[i0:] / a[i0]
            m = EC.fullmet(seg, idx=idx[i0:])
            print(f'{nm:<14} {m["final"]:>12.2f} {m["cagr"]:>7.2f} {m["mdd"]:>7.1f} '
                  f'{m["calmar"]:>7.3f} {m["rec"]/252:>7.1f}')

    # 위기 해부 — 닷컴·GFC·2022 에서 무한매수 40분할에 무슨 일이
    print('\n[위기 구간 계좌 배수 — 무한매수40 / B(2배) / TQQQ 맨몸]')
    for nm, s, e in (('닷컴 00-02', '2000-03-10', '2002-10-09'),
                     ('GFC 07-09', '2007-10-31', '2009-03-09'),
                     ('2022 베어', '2022-01-03', '2022-10-12')):
        i0, i1 = pd.Series(idx).searchsorted([pd.Timestamp(s), pd.Timestamp(e)])
        print(f'  {nm}: IBS {aI40[i1]/aI40[i0]:>6.3f} · B2 {aB2[i1]/aB2[i0]:>6.3f} · '
              f'맨몸 {aH3[i1]/aH3[i0]:>7.4f}')


if __name__ == '__main__':
    main()
