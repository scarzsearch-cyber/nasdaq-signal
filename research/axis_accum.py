# -*- coding: utf-8 -*-
"""
[축3] 목적함수를 바꾼다 — 거치식이 아니라 적립식

문제의식: v18~v21 의 모든 수치는 **1회 거치 후 방치**를 가정한다. 실제 운용은
매달 납입하는 적립식이고, 적립식은 수익률의 순서 위험(sequence risk)이 정반대다
(초기 폭락이 오히려 유리하다). 목적함수가 다르면 순위도 달라질 수 있다.

동시에 이 축은 'QLD Dip Alert' 류 모바일 앱이 파는 것을 정면으로 검증한다.
그 앱은 전환전략이 아니라 **매수 타이밍 도구**다 — "낙폭이 X% 오면 알림, 그때 사라".
그것을 정책으로 구현한 것이 아래 dip-* 다: 납입금을 전부 대기시켰다가 낙폭이
문턱 아래로 내려간 날 일괄 투입한다.

측정: 월 1단위 납입, 롤링 창(분기 스텝), **납입액 대비 최종배수**
      (거치식 배수와 직접 비교하면 안 된다 — 평균 투자기간이 절반이다)

실행:  python axis_accum.py
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

import hist_data as H
import hist_defensive as DF
from axis_lib import COST, rule_w, accumulate, check


def policies(D):
    one = np.ones(len(D['idx']))
    wB = rule_w(D['ddv'], -0.16, -0.16)
    wA = rule_w(D['ddv'], -0.16, -0.11)
    tb = H.tbill_daily(D['idx'])                     # dip 대기자금은 현금(T-bill)
    #      이름                   k    비중경로  대기자금  dip문턱
    return [('QQQ 적립',          1.0, one, None, None),
            ('QLD2x 그냥 적립',    2.0, one, None, None),
            ('전략A x2.0',        2.0, wA,  None, None),
            ('전략B x2.0',        2.0, wB,  None, None),
            ('전략B x2.5',        2.5, wB,  None, None),
            ('전략B x3.0',        3.0, wB,  None, None),
            ('전략B x3.5',        3.5, wB,  None, None),
            ('dip -16% 현금대기',  2.0, one, tb,   -0.16),
            ('dip -25% 현금대기',  2.0, one, tb,   -0.25)]


def run_accum(D, years, step=63):
    idx = D['idx']
    span = int(years * 252)
    POL = policies(D)
    res = {n: [] for n, *_ in POL}
    mdd = {n: [] for n, *_ in POL}
    starts = list(range(0, len(idx) - span, step))
    for st in starts:
        for n, k, w, park, dip in POL:
            paid, fin, m = accumulate(D, k, w, st, st + span, park=park, dip=dip)
            res[n].append(fin / paid)
            mdd[n].append(m * 100)

    print('\n===== 적립식 %d년 롤링 (%d창, 월 1단위) — 납입액 대비 배수 ====='
          % (years, len(starts)))
    print('%-20s %9s %9s %9s %9s %11s %11s' %
          ('정책', '중앙값', '10%분위', '최악', '최고', 'B2x대비승률', '경로MDD중앙'))
    base = np.array(res['전략B x2.0'])
    for n, *_ in POL:
        a = np.array(res[n])
        print('%-20s %9.2f %9.2f %9.2f %9.1f %10.1f%% %10.1f%%' %
              (n, np.median(a), np.percentile(a, 10), a.min(), a.max(),
               (a > base).mean() * 100, np.median(mdd[n])))
    return res


if __name__ == '__main__':
    D = DF.build('chain')
    print('데이터 %s ~ %s  n=%d  방어=배당체인  편도비용 %.2f%%'
          % (D['idx'][0].date(), D['idx'][-1].date(), len(D['idx']), COST * 100))
    assert check(D), '검산 실패'
    run_accum(D, 15)
    run_accum(D, 25)
    print('\n판정 1: dip 대기 투입(= QLD Dip Alert 형)의 기여는 0 이다.')
    print('        중앙값이 그냥 적립과 같고 좌측꼬리는 오히려 나빠진다.')
    print('        -25% 까지 기다리면 확실히 손해다. 가치는 "싸게 사는 것"이 아니라')
    print('        "도피하는 것"에 있다 — v21 §11.3 의 f*=0.5 와 같은 얘기다.')
    print('판정 2: 적립식에서 전환전략의 우위는 거치식보다 오히려 크다.')
    print('        최악 창이 QLD 그냥 적립의 6~11배다(그쪽은 원금 절반을 잃는다).')
