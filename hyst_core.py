# -*- coding: utf-8 -*-
"""A(-16/-11) vs B(-16/-16) : 역사 확장 핵심 비교"""
import numpy as np, pandas as pd
from reentry_lib import run, met, rolling_stats
import hist_data as H

A = dict(name='A  -16/-11', enter=-0.16, ladder=[(('dd', -0.11), 1.0, 0)])
B = dict(name='B  -16/-16', enter=-0.16, ladder=[(('dd', -0.16), 1.0, 0)])


def curves(D, cost=0.001, start=None, end=None):
    out = {}
    for S in (A, B):
        c, w, t = run(D, S['ladder'], enter=S['enter'], cost=cost, start=start, end=end)
        out[S['name']] = (c, w, t)
    return out


def switches(w):
    """비중 시리즈 -> [(날짜, from, to)]"""
    v = w.values; idx = w.index; out = []
    for i in range(1, len(v)):
        if v[i] != v[i - 1]:
            out.append((idx[i], v[i - 1], v[i]))
    return out


def summarize(D, cost=0.001, start=None, end=None, label=''):
    cs = curves(D, cost, start, end)
    idx = D['idx']
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = len(idx) if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    sl = slice(lo, hi)
    # [코드리뷰 2026-09-04] 전략 곡선은 run() 이 r[0]=0.0 으로 눌러 정확히 1.0 에서
    # 시작한다. 벤치마크도 같은 규약을 써야 한 표에서 비교가 성립한다 — 종전에는
    # 구간 첫날 수익이 그대로 곱해져 start= 를 준 표에서 벤치마크만 부풀었다
    # (2000-01-03 기준 최종배수 +7.4% · CAGR +0.285%p).
    qr = np.array(D['qldr'][sl], dtype=float); qr[0] = 0.0
    pr = np.nan_to_num(D['px'].pct_change().values)[sl].astype(float).copy(); pr[0] = 0.0
    qld = pd.Series(np.cumprod(1 + qr), index=idx[sl])
    qqq = pd.Series(np.cumprod(1 + pr), index=idx[sl])
    rows = []
    for nm, (c, w, t) in cs.items():
        m = met(c); sw = len(switches(w))
        rs = rolling_stats(c, qld)
        rows.append(dict(전략=nm, 최종배수=m['final'], CAGR=m['cagr'] * 100, MDD=m['mdd'] * 100,
                         Calmar=m['calmar'], Sharpe=m['sharpe'], 전환=sw,
                         연전환=sw / m['years'],
                         **{f'{k}Y승률': rs[k]['win'] for k in (1, 3, 5, 10, 15) if k in rs}))
    for nm, c in [('QLD 보유', qld), ('QQQ 보유', qqq)]:
        m = met(c); rs = rolling_stats(c, qld)
        rows.append(dict(전략=nm, 최종배수=m['final'], CAGR=m['cagr'] * 100, MDD=m['mdd'] * 100,
                         Calmar=m['calmar'], Sharpe=m['sharpe'], 전환=0, 연전환=0,
                         **{f'{k}Y승률': rs[k]['win'] for k in (1, 3, 5, 10, 15) if k in rs}))
    df = pd.DataFrame(rows)
    if label:
        print('\n===== %s =====' % label)
    print(df.to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
    return cs, df


if __name__ == '__main__':
    D = H.build_ext()
    summarize(D, label='전구간 1972-02 ~ 2026-08  (54.5년)')
    summarize(D, start='2000-01-03', label='v19 비교구간 2000-01 ~ 2026-08')
    summarize(D, end='1999-12-31', label='신규구간만 1972-02 ~ 1999-12  (27.9년)')
