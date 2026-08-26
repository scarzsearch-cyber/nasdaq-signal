# -*- coding: utf-8 -*-
"""B의 우위가 몇 개 사건에 몰려 있는가? log(B/A) 누적 분해 + 집중도"""
import numpy as np, pandas as pd
from reentry_lib import run, met
import hist_data as H
from hyst_core import A, B, switches
pd.set_option('display.width', 250)
F = lambda x: f'{x:,.2f}'

D = H.build_ext(); idx = D['idx']
cA, wA, _ = run(D, A['ladder'], enter=A['enter'])
cB, wB, _ = run(D, B['ladder'], enter=B['enter'])

lr = np.log(cB / cA).diff().fillna(0)
tot = float(np.log(cB.iloc[-1] / cA.iloc[-1]))
print('총 log(B/A) = %.4f  (배수비 %.2f)' % (tot, np.exp(tot)))

print('\n--- 두 전략의 비중이 다른 날 ---')
diff = (wA != wB)
print('다른 날 %d일 / 전체 %d일 = %.1f%%' % (diff.sum(), len(idx), diff.mean() * 100))

print('\n--- 연도별 log(B/A) 기여 (상위/하위 10) ---')
yr = lr.groupby(lr.index.year).sum()
z = pd.DataFrame({'연도': yr.index, 'logBA': yr.values, '배수비': np.exp(yr.values)})
z = z[z['logBA'].abs() > 1e-9]
print('상위:'); print(z.nlargest(10, 'logBA').to_string(index=False, float_format=F))
print('하위:'); print(z.nsmallest(10, 'logBA').to_string(index=False, float_format=F))
print('\n기여가 0이 아닌 해: %d개 / 55년' % len(z))

s = z['logBA'].sort_values(ascending=False)
for k in (1, 3, 5, 10):
    print('상위 %2d개 해가 총우위에서 차지하는 비중: %6.1f%%' % (k, s.head(k).sum() / tot * 100))
print('상위 3개 해를 제외하면 B/A 배수비 = %.2f' % np.exp(tot - s.head(3).sum()))
print('상위 5개 해를 제외하면 B/A 배수비 = %.2f' % np.exp(tot - s.head(5).sum()))

print('\n--- 일별 기여 상위 15일 ---')
d15 = lr.reindex(lr.abs().nlargest(15).index).sort_index()
print(pd.DataFrame({'날짜': [str(x.date()) for x in d15.index], 'logBA': d15.values,
                    'A비중': wA.reindex(d15.index).values, 'B비중': wB.reindex(d15.index).values,
                    'dd%': D['dd'].reindex(d15.index).values * 100}).to_string(index=False, float_format=F))
print('상위 15일 합 = %.4f  (총우위의 %.0f%%)' % (d15.sum(), d15.sum() / tot * 100))

print('\n--- 확장구간(1972-99) / 실물QQQ구간(2000-) 분리 ---')
for lab, s_, e_ in [('1972-1999 (대체지수)', None, '1999-12-31'), ('2000-2026 (QQQ 실물)', '2000-01-03', None)]:
    a, _, _ = run(D, A['ladder'], enter=A['enter'], start=s_, end=e_)
    b, _, _ = run(D, B['ladder'], enter=B['enter'], start=s_, end=e_)
    print('%-22s A %10.2f배  B %10.2f배  B/A %.2f' % (lab, met(a)['final'], met(b)['final'],
                                                     met(b)['final'] / met(a)['final']))
