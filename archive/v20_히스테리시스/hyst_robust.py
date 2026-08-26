# -*- coding: utf-8 -*-
"""v19에서 B를 탈락시킨 관문들을 확장 데이터로 재검증 + 현금규약 민감도"""
import numpy as np, pandas as pd
from reentry_lib import run, met, rolling_stats
import hist_data as H
from hyst_core import A, B, switches

pd.set_option('display.width', 260)
F = lambda x: f'{x:,.2f}'


def pair(D, enter, band, cost=0.001, lag=1, start=None, end=None):
    a, wa, _ = run(D, [(('dd', enter + band), 1.0, 0)], enter=enter, cost=cost, lag=lag, start=start, end=end)
    b, wb, _ = run(D, [(('dd', enter), 1.0, 0)], enter=enter, cost=cost, lag=lag, start=start, end=end)
    return (a, wa), (b, wb)


def main():
    D = H.build_ext()
    DT = H.build_ext(cash='tbill')

    print('===== 현금 규약 민감도 (SCHD 이전 구간) =====')
    rows = []
    for lab, DD in [('연2% 고정(기존 규약)', D), ('실제 3M T-bill', DT)]:
        for nm, S in [('A -16/-11', A), ('B -16/-16', B)]:
            c, w, _ = run(DD, S['ladder'], enter=S['enter'])
            m = met(c)
            rows.append(dict(현금규약=lab, 전략=nm, 최종배수=m['final'], CAGR=m['cagr'] * 100,
                             MDD=m['mdd'] * 100, Calmar=m['calmar']))
    t = pd.DataFrame(rows); print(t.to_string(index=False, float_format=F))
    r = t.set_index(['현금규약', '전략'])['최종배수']
    print('B/A 배수비 : 연2%% %.2f  /  T-bill %.2f'
          % (r[('연2% 고정(기존 규약)', 'B -16/-16')] / r[('연2% 고정(기존 규약)', 'A -16/-11')],
             r[('실제 3M T-bill', 'B -16/-16')] / r[('실제 3M T-bill', 'A -16/-11')]))

    print('\n===== 관문(d) 진입선 이동 견고성  [A는 5%p 밴드 유지] =====')
    for lab, s in [('전구간 1972-2026', None), ('2000-2026', '2000-01-03')]:
        rows = []
        for e in (-0.12, -0.14, -0.16, -0.18, -0.20, -0.25):
            (a, wa), (b, wb) = pair(D, e, 0.05, start=s)
            ma, mb = met(a), met(b)
            rows.append(dict(진입선=f'{e*100:.0f}%', A배수=ma['final'], B배수=mb['final'],
                             비=mb['final'] / ma['final'], A_MDD=ma['mdd'] * 100, B_MDD=mb['mdd'] * 100,
                             A전환=len(switches(wa)), B전환=len(switches(wb))))
        print('[%s]' % lab)
        print(pd.DataFrame(rows).to_string(index=False, float_format=F))

    print('\n===== 히스테리시스 폭 평탄성  (진입 -16% 고정, 복귀선을 -16%→-6% 로) =====')
    rows = []
    for x in np.arange(0.0, 0.105, 0.01):
        c, w, _ = run(D, [(('dd', -0.16 + x), 1.0, 0)], enter=-0.16)
        m = met(c)
        c2, _, _ = run(D, [(('dd', -0.16 + x), 1.0, 0)], enter=-0.16, start='2000-01-03')
        rows.append(dict(복귀선=f'{(-0.16+x)*100:.0f}%', 밴드=f'{x*100:.0f}%p', 전구간배수=m['final'],
                         CAGR=m['cagr'] * 100, MDD=m['mdd'] * 100, 전환=len(switches(w)),
                         구간2000=met(c2)['final']))
    print(pd.DataFrame(rows).to_string(index=False, float_format=F))

    print('\n===== 체결 지연 민감도 (전구간) =====')
    rows = []
    for lag in (1, 2, 3, 5):
        (a, _), (b, _) = pair(D, -0.16, 0.05, lag=lag)
        rows.append(dict(지연=f'{lag}일', A배수=met(a)['final'], B배수=met(b)['final'],
                         비=met(b)['final'] / met(a)['final']))
    print(pd.DataFrame(rows).to_string(index=False, float_format=F))

    print('\n===== 10년 단위 분해 =====')
    rows = []
    for s, e in [('1972-02-07', '1979-12-31'), ('1980-01-01', '1989-12-31'),
                 ('1990-01-01', '1999-12-31'), ('2000-01-01', '2009-12-31'),
                 ('2010-01-01', '2019-12-31'), ('2020-01-01', '2026-08-24')]:
        (a, wa), (b, wb) = pair(D, -0.16, 0.05, start=s, end=e)
        qs = D['idx'].searchsorted(pd.Timestamp(s)); qe = D['idx'].searchsorted(pd.Timestamp(e), side='right')
        q = np.prod(1 + D['qldr'][qs:qe])
        rows.append(dict(구간=s[:4] + '-' + e[:4], A배수=met(a)['final'], B배수=met(b)['final'],
                         QLD배수=q, A_MDD=met(a)['mdd'] * 100, B_MDD=met(b)['mdd'] * 100,
                         A전환=len(switches(wa)), B전환=len(switches(wb)),
                         승자='B' if met(b)['final'] > met(a)['final'] else 'A'))
    print(pd.DataFrame(rows).to_string(index=False, float_format=F))


if __name__ == '__main__':
    main()
