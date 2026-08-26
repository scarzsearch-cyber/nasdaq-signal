# -*- coding: utf-8 -*-
"""
[축1] 리스크온 상태의 레버리지 배수 k — v18~v21 이 한 번도 변수로 놓지 않은 축

문제의식: v21 §11.3 의 상태별 조건부 Kelly 는 이렇게 나왔다.
    DD > -11% (평상시)        f* = 5.00
    -16% < DD <= -11% (회색)  f* = 4.25
    DD <= -16% (도피)         f* = 0.50
도피 쪽(0.5)은 SCHD 전환으로 이미 구현돼 있다. 그런데 리스크온 쪽은 f* 가 4~5 인데
54년 내내 2배만 태웠다. -16/-11 vs -16/-16 은 561일짜리 회색지대 논쟁이지만
배수는 13,859일 전부에 걸린다.

출력 순서
  1) 배수 격자           k = 1.0 ~ 4.0, 규칙 A/B/단순보유
  2) 검증관문 체결지연    lag 1/2/3/5
  3) 검증관문 거래비용    편도 0.05 ~ 0.5%
  4) 구간 안정성         5개 하위구간 (한 시대의 산물인지)
  5) 위기별 손실
  6) 꼬리위험            최악 1일/5일, 최장 수중기간
  7) 롤링 시작시점 의존성 거치식 10년/20년
  8) 계좌 상쇄           ISA 과세이연 x2  vs  해외주식 22% 통산 x2.5/x3/x3.5

실행:  python axis_lev.py
"""
import numpy as np
import pandas as pd

import hist_defensive as DF
from reentry_lib import met
from axis_lib import (COST, rule_w, lev_r, sim, after_tax, after_tax_annual,
                      check, row, show, qqq_curve)

KS = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)
KS_GATE = (2.0, 2.5, 3.0, 3.5)

SEGS = [('1972-1985', '1972-02-07', '1985-12-31'),
        ('1986-1999', '1986-01-01', '1999-12-31'),
        ('2000-2009', '2000-01-03', '2009-12-31'),
        ('2010-2026', '2010-01-01', '2026-08-24'),
        ('2000-2026', '2000-01-03', None),
        ('1972-2026', None, None)]

CRISES = {'닷컴 00-02': ('2000-03-10', '2002-10-09'),
          'GFC 07-09': ('2007-10-31', '2009-03-09'),
          '87블랙먼데이': ('1987-08-25', '1988-12-31'),
          '73-74오일': ('1973-01-11', '1974-10-03'),
          '코로나20': ('2020-02-19', '2020-03-23'),
          '2022베어': ('2022-01-03', '2022-12-31')}


# --------------------------------------------------------------- 1) 격자
def grid(D, start, label):
    ref = qqq_curve(D, start)
    rows = []
    for k in KS:
        rk = lev_r(D, k)
        for nm, en, ex in (('-16/-11', -0.16, -0.11), ('-16/-16', -0.16, -0.16)):
            c, sw = sim(D, rule_w(D['ddv'], en, ex), riskon_r=rk, start=start)
            rows.append(row('%s  x%.1f' % (nm, k), c, sw, ref=ref))
        c, sw = sim(D, np.ones(len(D['ddv'])), riskon_r=rk, start=start)
        rows.append(row('단순보유  x%.1f' % k, c, sw, ref=ref))
    return show(rows, '1) 배수 격자 — %s' % label)


# --------------------------------------------------------------- 2~3) 관문
def gate_lag(D):
    print('\n===== 2) 검증관문 : 체결지연 (2000-2026, -16/-16) =====')
    print('%-8s %12s %12s %12s %12s %10s' % ('k', 'lag1', 'lag2', 'lag3', 'lag5', 'lag2/lag1'))
    w = rule_w(D['ddv'], -0.16, -0.16)
    for k in KS_GATE:
        rk = lev_r(D, k)
        v = [sim(D, w, rk, lag=L, start='2000-01-03')[0].iloc[-1] for L in (1, 2, 3, 5)]
        print('x%-7.1f %12s %12s %12s %12s %9.2f' %
              (k, *[format(x, ',.1f') for x in v], v[1] / v[0]))


def gate_cost(D):
    print('\n===== 3) 검증관문 : 편도 거래비용 (2000-2026, -16/-16) =====')
    print('%-8s %12s %12s %12s %12s %12s' % ('k', '0.05%', '0.10%', '0.20%', '0.50%', 'x2대비(0.5%)'))
    w = rule_w(D['ddv'], -0.16, -0.16)
    base = None
    for k in KS_GATE:
        rk = lev_r(D, k)
        v = [sim(D, w, rk, cost=c, start='2000-01-03')[0].iloc[-1]
             for c in (0.0005, 0.001, 0.002, 0.005)]
        if base is None:
            base = v[3]
        print('x%-7.1f %12s %12s %12s %12s %11.2f배' %
              (k, *[format(x, ',.1f') for x in v], v[3] / base))


# --------------------------------------------------------------- 4) 구간
def segments(D):
    w = rule_w(D['ddv'], -0.16, -0.16)
    print('\n===== 4) 구간 안정성 (-16/-16, 최종배수 / CAGR) =====')
    print('%-11s' % '구간' + ''.join('%20s' % ('x%.1f' % k) for k in KS_GATE))
    for nm, s, e in SEGS:
        cells = []
        for k in KS_GATE:
            c, _ = sim(D, w, lev_r(D, k), start=s, end=e)
            m = met(c)
            cells.append('%11s /%5.1f%%' % (format(m['final'], ',.1f'), m['cagr'] * 100))
        print('%-11s' % nm + ''.join('%20s' % x for x in cells))
    print('  ※ 2000-2009 만 역전한다 — 고배수의 대가는 "최악의 10년"에서 나온다')


# --------------------------------------------------------------- 5) 위기
def crises(D):
    w = rule_w(D['ddv'], -0.16, -0.16)
    print('\n===== 5) 위기 구간별 손실 (-16/-16) =====')
    print('%-8s' % 'k' + ''.join('%13s' % c for c in CRISES))
    for k in (1.0,) + KS_GATE:
        c, _ = sim(D, w, lev_r(D, k))
        cells = []
        for s, e in CRISES.values():
            z = c.loc[s:e]
            cells.append('%12.1f%%' % ((z.iloc[-1] / z.iloc[0] - 1) * 100) if len(z) > 1 else '%13s' % '-')
        print('x%-7.1f' % k + ''.join(cells))


# --------------------------------------------------------------- 6) 꼬리
def _longest_underwater(c):
    best = cur = 0
    for v in (c < c.cummax()).values:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best / 252


def tails(D):
    w = rule_w(D['ddv'], -0.16, -0.16)
    print('\n===== 6) 꼬리위험 (-16/-16, 1972-2026) =====')
    print('%-6s %10s %-13s %10s %10s %10s' %
          ('k', '최악1일', '(날짜)', '최악5일', 'MDD', '최장수중'))
    for k in KS_GATE + (4.0,):
        c, _ = sim(D, w, lev_r(D, k))
        dr = c.pct_change().dropna()
        print('x%-5.1f %9.2f%% %-13s %9.2f%% %9.2f%% %8.1f년' %
              (k, dr.min() * 100, str(dr.idxmin().date()),
               (c / c.shift(5) - 1).min() * 100,
               (c / c.cummax() - 1).min() * 100, _longest_underwater(c)))
    print('  ※ 기초지수가 하루 -1/k 이상 빠지면 k배 상품은 전액소각된다.')
    print('    1987-10-19 나스닥 종합은 -11.35% 였다. x3 이면 -34%, x4 면 -45% 다.')


# --------------------------------------------------------------- 7) 롤링
def rolling(D, years):
    span = int(years * 252)
    step = 63
    w = rule_w(D['ddv'], -0.16, -0.16)
    print('\n===== 7) 거치식 %d년 롤링 시작시점 의존성 (-16/-16) =====' % years)
    print('%-8s %11s %11s %11s %12s %11s' %
          ('k', '중앙배수', '10%분위', '최악', 'x2대비승률', '최악CAGR'))
    base = None
    for k in KS_GATE:
        c, _ = sim(D, w, lev_r(D, k))
        v = c.values
        a = np.array([v[s + span - 1] / v[s] for s in range(0, len(v) - span, step)])
        if base is None:
            base = a
        print('x%-7.1f %11.2f %11.2f %11.2f %11.1f%% %10.2f%%' %
              (k, np.median(a), np.percentile(a, 10), a.min(),
               (a > base).mean() * 100, (a ** (252 / span) - 1).min() * 100))


# --------------------------------------------------------------- 8) 계좌
def accounts(D, start, label):
    """국내 상장 레버리지 ETF 는 2배가 상한이고 ISA 는 해외 상장 종목을 담을 수 없다.
    따라서 x2 초과는 해외주식계좌(양도세 22%, 연간 손익통산)로만 가능하다."""
    w = rule_w(D['ddv'], -0.16, -0.16)
    print('\n===== 8) 계좌 상쇄 — %s =====' % label)
    print('%-38s %14s %10s %14s' % ('시나리오', '세후 최종배수', '세전대비', 'ISA x2 대비'))
    base = None
    for nm, k, kind in [('x2.0  ISA 과세이연 (최종 9.9%)', 2.0, 'isa'),
                        ('x2.0  해외주식 22% 통산', 2.0, 'ovs'),
                        ('x2.5  해외주식 22% 통산', 2.5, 'ovs'),
                        ('x3.0  해외주식 22% 통산', 3.0, 'ovs'),
                        ('x3.5  해외주식 22% 통산', 3.5, 'ovs')]:
        pre, _ = sim(D, w, lev_r(D, k), start=start)
        if kind == 'isa':
            v, _ = after_tax(D, k, w, 0.099, False, start=start)
        else:
            v, _ = after_tax_annual(D, k, w, 0.22, start=start)
        if base is None:
            base = v
        print('%-38s %14s %9.1f%% %12.2f배' %
              (nm, format(v, ',.1f'), v / pre.iloc[-1] * 100, v / base))


if __name__ == '__main__':
    D = DF.build('chain')
    print('데이터 %s ~ %s  n=%d  방어=배당체인  편도비용 %.2f%%'
          % (D['idx'][0].date(), D['idx'][-1].date(), len(D['idx']), COST * 100))
    print('2배 합성비용 c_daily = %.2f%%/yr  ->  cost(k) = (k-1) x %.2f%%/yr'
          % (D['c_daily'] * 252 * 100, D['c_daily'] * 252 * 100))
    assert check(D), '검산 실패'

    grid(D, None, '1972-2026 (54.5년)')
    grid(D, '2000-01-03', '2000-2026 (26.6년)')
    gate_lag(D)
    gate_cost(D)
    segments(D)
    crises(D)
    tails(D)
    rolling(D, 10)
    rolling(D, 20)
    accounts(D, '2000-01-03', '2000-2026')
    accounts(D, None, '1972-2026')
