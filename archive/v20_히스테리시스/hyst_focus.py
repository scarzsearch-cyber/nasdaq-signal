# -*- coding: utf-8 -*-
"""§4 위기별 전환일지, §6 1973-74, §7 1987, §8 비용민감도"""
import numpy as np, pandas as pd
from reentry_lib import run, met
import hist_data as H
from hyst_core import A, B, switches

pd.set_option('display.width', 260)
F = lambda x: f'{x:,.2f}'

CR = {'1973-74 대약세': ('1973-01-01', '1975-12-31'),
      '1978-82 스태그': ('1978-01-01', '1982-12-31'),
      '1983-84 조정': ('1983-06-01', '1984-12-31'),
      '1987 블랙먼데이': ('1987-08-01', '1988-12-31'),
      '1990 걸프': ('1990-01-01', '1991-06-30'),
      '1992 톱니': ('1992-04-01', '1992-12-31'),
      '1998 LTCM': ('1998-07-01', '1998-12-31'),
      '2000-02 닷컴': ('2000-01-01', '2002-12-31'),
      '2007-09 GFC': ('2007-10-01', '2009-03-31'),
      '2020 코로나': ('2020-02-01', '2020-04-30'),
      '2022 베어': ('2022-01-01', '2022-12-31'),
      '2025 관세': ('2025-01-01', '2025-12-31')}


def log(w, s, e):
    sw = switches(w.loc[s:e])
    return ' '.join('%s%s' % (str(d.date())[2:], '→QLD' if t >= 1 else '→SCHD') for d, f_, t in sw)


def main():
    D = H.build_ext(); idx = D['idx']
    cA, wA, _ = run(D, A['ladder'], enter=A['enter'])
    cB, wB, _ = run(D, B['ladder'], enter=B['enter'])
    qld = pd.Series(np.cumprod(1 + D['qldr']), index=idx)
    sr = lambda c, s, e: (c.loc[s:e].iloc[-1] / c.loc[s:e].iloc[0] - 1) * 100
    mdd = lambda c, s, e: ((c.loc[s:e] / c.loc[s:e].cummax() - 1).min()) * 100

    rows = []
    for nm, (s, e) in CR.items():
        if pd.Timestamp(s) < idx[0]: continue
        rows.append(dict(위기=nm, A수익=sr(cA, s, e), B수익=sr(cB, s, e), QLD수익=sr(qld, s, e),
                         A_MDD=mdd(cA, s, e), B_MDD=mdd(cB, s, e),
                         A전환=len(switches(wA.loc[s:e])), B전환=len(switches(wB.loc[s:e]))))
    t = pd.DataFrame(rows)
    print('===== §4 위기 구간 손익 =====')
    print(t.to_string(index=False, float_format=F))
    t.to_csv('hyst_crisis.csv', index=False, encoding='utf-8-sig')

    print('\n===== §4 전환 일지 =====')
    for nm, (s, e) in CR.items():
        if pd.Timestamp(s) < idx[0]: continue
        print('\n[%s]' % nm)
        print('  A: %s' % (log(wA, s, e) or '(전환없음)'))
        print('  B: %s' % (log(wB, s, e) or '(전환없음)'))

    for nm, s, e in [('§6  1973-01 ~ 1975-12', '1973-01-01', '1975-12-31'),
                     ('§7  1987-08 ~ 1988-12', '1987-08-01', '1988-12-31')]:
        print('\n===== %s =====' % nm)
        z = D['dd'].loc[s:e]
        print('낙폭 경로: 최저 %.1f%%  /  -16%% 이하 체류 %d일 / 전체 %d일  /  -16%% 하향돌파 %d회'
              % (z.min() * 100, (z <= -0.16).sum(), len(z),
                 int(((z <= -0.16).values[1:] & ~(z <= -0.16).values[:-1]).sum())))
        # 월별 낙폭 저점
        m = z.groupby([z.index.year, z.index.month]).min() * 100
        print('월별 최저낙폭:', ' '.join('%02d/%02d %.0f' % (y % 100, mo, v) for (y, mo), v in m.items()))
        sub = []
        for lab, c, w in [('A -16/-11', cA, wA), ('B -16/-16', cB, wB), ('QLD 보유', qld, None)]:
            d = dict(전략=lab, 수익률=sr(c, s, e), MDD=mdd(c, s, e))
            if w is not None:
                ww = w.loc[s:e]
                d['전환'] = len(switches(ww)); d['QLD노출일'] = int((ww >= 1).sum())
                d['QLD노출%'] = (ww >= 1).mean() * 100
            sub.append(d)
        print(pd.DataFrame(sub).to_string(index=False, float_format=F))

    print('\n===== §8 편도 거래비용 민감도 (전구간 1972-2026) =====')
    rows = []
    for c in (0.0005, 0.001, 0.002, 0.003, 0.005):
        r = dict(비용=f'{c*100:.2f}%')
        for lab, S in [('A', A), ('B', B)]:
            cc, ww, _ = run(D, S['ladder'], enter=S['enter'], cost=c)
            m = met(cc); r[lab + '_배수'] = m['final']; r[lab + '_CAGR'] = m['cagr'] * 100
        r['B/A'] = r['B_배수'] / r['A_배수']
        rows.append(r)
    tc = pd.DataFrame(rows); print(tc.to_string(index=False, float_format=F))
    tc.to_csv('hyst_cost.csv', index=False, encoding='utf-8-sig')

    print('\n===== §8b 2000-2026 구간 비용 민감도 =====')
    rows = []
    for c in (0.0005, 0.001, 0.002, 0.003, 0.005):
        r = dict(비용=f'{c*100:.2f}%')
        for lab, S in [('A', A), ('B', B)]:
            cc, _, _ = run(D, S['ladder'], enter=S['enter'], cost=c, start='2000-01-03')
            m = met(cc); r[lab + '_배수'] = m['final']; r[lab + '_CAGR'] = m['cagr'] * 100
        r['B/A'] = r['B_배수'] / r['A_배수']
        rows.append(r)
    print(pd.DataFrame(rows).to_string(index=False, float_format=F))


if __name__ == '__main__':
    main()
