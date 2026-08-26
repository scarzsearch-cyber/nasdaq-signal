# -*- coding: utf-8 -*-
"""
[v22 공용 엔진] 지금까지 변수로 놓지 않았던 '축'을 재기 위한 확장 유틸

v18~v21 은 전부 **전환 타이밍 축** 하나만 변수로 놓았다(문턱·히스테리시스·룩백·
확인일·복귀지표·방어자산·신호 기준자산). 이 모듈은 그 축을 고정한 채 다음 세 축을 연다.

  축1  riskon leverage k   — 지금까지 항상 2배 고정.        lev_r()
  축2  파라미터 앙상블      — 문턱을 고르지 않고 평균낸다.   rule_w() 여러 개를 평균
  축3  적립식 목적함수      — 지금까지 항상 거치식.          accumulate()

[규약] reentry_lib.run() 과 완전히 동일하게 맞췄다. 바꾼 것이 없다.
  - 체결: 전일 종가 신호 -> 당일 체결 (pos = w.shift(1))
  - 비용: 편도 0.1%, 회전율 |Δpos| 에 비례
  - 방어자산: hist_defensive.build(kind) 가 준 schdr 그대로
  check() 가 reentry_lib.run() 대비 오차 0 을 매번 검산한다.
"""
import sys
import numpy as np
import pandas as pd

try:                                   # 윈도우 콘솔 cp949 대비
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

COST = 0.001


# ------------------------------------------------------------------ 신호
def rule_w(ddv, enter, exit_, w0=1.0):
    """낙폭 규칙 -> QLD 비중 경로. reentry_lib.run() 의 ladder 와 동치.

    enter 이하로 내려가면 0, exit_ 를 초과 회복하면 1. 그 사이는 직전 상태 유지.
    """
    n = len(ddv)
    w = np.empty(n)
    cur = w0
    for i in range(n):
        if cur >= 1.0:
            if ddv[i] <= enter:
                cur = 0.0
        else:
            if ddv[i] <= enter:
                cur = 0.0
            elif ddv[i] > exit_:
                cur = 1.0
        w[i] = cur
    return w


def dd_from(px, lb):
    """룩백 lb 일 낙폭. hist_data.build_ext() 와 같은 min_periods 규약."""
    return (px / px.rolling(lb, min_periods=lb).max() - 1).fillna(0).values


# ------------------------------------------------------------------ 배수
def lev_r(D, k):
    """기초지수 일간수익 -> k 배 상품의 일간수익.

    합성비용은 2배 실물(QQQ/QLD 겹침)에서 역산한 c_daily 를 차입분에 비례해 늘린다:
        cost(k) = (k - 1) * c_daily          # c_daily = cost(2) = 1x차입 + 운용보수
    k=2 에서 기존 규약과 정확히 일치하고, k>2 에서는 **실제보다 비싸게** 잡힌다
    (운용보수는 k 에 비례하지 않으므로). 즉 고배수에 불리한 방향의 보수적 모형이다.
    """
    pxr = np.nan_to_num(D['px'].pct_change().values)
    return k * pxr - (k - 1) * D['c_daily']


# ------------------------------------------------------------------ 거치식
def sim(D, w, riskon_r=None, cost=COST, lag=1, start=None, end=None):
    """임의의 비중경로 w 로 거치식 곡선을 만든다. reentry_lib.run() 과 동일 규약."""
    idx = D['idx']
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    sl = slice(lo, hi)
    rr = D['qldr'] if riskon_r is None else riskon_r
    wv = w[sl]
    pos = np.empty_like(wv)
    pos[:lag] = wv[0]
    pos[lag:] = wv[:-lag]
    r = np.nan_to_num(pos * rr[sl] + (1 - pos) * D['schdr'][sl])
    r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    curve = pd.Series(np.cumprod((1 + r) * (1 - cost * turn)), index=idx[sl])
    return curve, int((np.abs(np.diff(wv)) > 1e-9).sum())


# ------------------------------------------------------------------ 적립식
def accumulate(D, k, w, lo, hi, park=None, dip=None, cost=COST):
    """월초 1단위 적립. 반환 (총납입, 최종평가액, 경로MDD).

    park : 대기자금 수익률. None 이면 방어자산(schdr), 배열이면 그것(예: T-bill)
    dip  : None 이면 납입금을 전략이 지시하는 쪽에 바로 넣는다.
           숫자면 'QLD Dip Alert' 형 — 납입금을 전부 대기시켰다가
           낙폭이 dip 이하로 내려간 날 일괄 투입한다.

    납입 배치와 dip 판정 모두 **전일 신호**만 쓴다(미래 참조 없음).
    """
    idx = D['idx']
    rk = lev_r(D, k)
    dfr = D['schdr'] if park is None else park
    ddv = D['ddv']
    months = pd.Series(idx).dt.to_period('M').values

    R = C = paid = 0.0
    prev = w[lo]
    vals = []
    for i in range(lo, hi):
        R *= (1 + rk[i])
        C *= (1 + dfr[i])
        pos = w[i - 1] if i > lo else w[lo]

        if pos != prev:                                    # 전략 전환
            if pos >= 1:
                R += C * (1 - cost); C = 0.0
            else:
                C += R * (1 - cost); R = 0.0
            prev = pos

        if i > lo and months[i] != months[i - 1]:           # 월초 납입
            paid += 1.0
            if dip is not None or pos < 1:
                C += 1.0
            else:
                R += 1.0

        if dip is not None and C > 0 and pos >= 1 and ddv[i - 1] <= dip:
            R += C * (1 - cost); C = 0.0                    # dip 일괄 투입

        vals.append(R + C)

    v = pd.Series(vals, index=idx[lo:hi])
    return paid, float(v.iloc[-1]), float((v / v.cummax() - 1).min())


# ------------------------------------------------------------------ 세금
def after_tax(D, k, w, rate, per_switch, cost=COST, start=None, end=None):
    """계좌 규약별 세후 최종배수.

    per_switch=False : 과세이연(ISA). 만기에 총이익을 한 번만 과세
    per_switch=True  : 전환마다 실현이익 과세(손익통산 없음, 보수적)
    """
    idx = D['idx']
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    rk = lev_r(D, k)
    dfr = D['schdr']
    V = B = 1.0
    prev = w[lo]
    paid = 0.0
    for i in range(lo + 1, hi):
        pos = w[i - 1]
        V *= (1 + (rk[i] if pos >= 1 else dfr[i]))
        if pos != prev:
            V *= (1 - cost)
            if per_switch:
                g = V - B
                if g > 0:
                    t = g * rate; V -= t; paid += t
                B = V
            prev = pos
    g = V - B
    if g > 0:
        t = g * rate; V -= t; paid += t
    return V, paid


def after_tax_annual(D, k, w, rate=0.22, cost=COST, start=None, end=None):
    """해외주식 양도소득세형 — 연간 실현손익을 통산한 뒤 과세.

    250만원 기본공제는 넣지 않았다(금액 단위가 없는 배수 모형이라 정의 불가).
    계좌가 커질수록 공제의 상대적 크기가 0 으로 가므로 큰 왜곡은 아니다.
    """
    idx = D['idx']
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    rk = lev_r(D, k)
    dfr = D['schdr']
    V = B = 1.0
    prev = w[lo]
    yr = idx[lo].year
    net = paid = 0.0
    for i in range(lo + 1, hi):
        pos = w[i - 1]
        V *= (1 + (rk[i] if pos >= 1 else dfr[i]))
        if idx[i].year != yr:                       # 연말 정산
            if net > 0:
                t = net * rate; V -= t; paid += t
            net = 0.0
            yr = idx[i].year
        if pos != prev:
            V *= (1 - cost)
            net += V - B
            B = V
            prev = pos
    net += V - B
    if net > 0:
        t = net * rate; V -= t; paid += t
    return V, paid


# ------------------------------------------------------------------ 검산·출력
def check(D):
    """reentry_lib.run() 대비 오차 0 확인. 모든 스크립트가 시작할 때 부른다."""
    from reentry_lib import run
    from hyst_core import A, B
    ok = True
    for S in (A, B):
        c0, _, _ = run(D, S['ladder'], enter=S['enter'], cost=COST)
        c1, sw = sim(D, rule_w(D['ddv'], S['enter'], S['ladder'][0][0][1]))
        err = abs(c0.iloc[-1] / c1.iloc[-1] - 1)
        ok = ok and err < 1e-12
        print('검산 %-11s  run=%.4f  sim=%.4f  오차=%.1e  전환=%d'
              % (S['name'], c0.iloc[-1], c1.iloc[-1], err, sw))
    wB = rule_w(D['ddv'], -0.16, -0.16)                 # 세율 0 이면 sim 과 같아야 한다
    v, _ = after_tax(D, 2.0, wB, 0.0, True)
    c, _ = sim(D, wB, lev_r(D, 2.0))
    err = abs(v / c.iloc[-1] - 1)
    ok = ok and err < 1e-6
    print('검산 after_tax(세율0)  %.4f  vs sim %.4f  오차=%.1e' % (v, c.iloc[-1], err))
    return ok


def row(nm, curve, sw, ref=None):
    from reentry_lib import met, rolling_stats
    m = met(curve)
    d = dict(name=nm, final=m['final'], cagr=m['cagr'] * 100, mdd=m['mdd'] * 100,
             calmar=m['calmar'], sharpe=m['sharpe'], sw=sw)
    if ref is not None:
        rs = rolling_stats(curve, ref)
        for k in (5, 10):
            if k in rs:
                d['w%dy' % k] = rs[k]['win']
    return d


def show(rows, title):
    df = pd.DataFrame(rows)
    print('\n===== %s =====' % title)
    with pd.option_context('display.width', 220):
        print(df.to_string(index=False, float_format=lambda x: format(x, ',.2f')))
    return df


def qqq_curve(D, start=None):
    c = pd.Series(np.cumprod(1 + np.nan_to_num(D['px'].pct_change().values)), index=D['idx'])
    if start:
        c = c.loc[start:]
        c = c / c.iloc[0]
    return c
