# -*- coding: utf-8 -*-
"""B의 손실 메커니즘: 거짓 복귀 1회당 '체결 지연 하루'의 레버리지 손실"""
import numpy as np, pandas as pd
from reentry_lib import run
import hist_data as H
from hyst_core import A, B
pd.set_option('display.width', 250)

D = H.build_ext(); idx = D['idx']
cA, wA, _ = run(D, A['ladder'], enter=A['enter'])
cB, wB, _ = run(D, B['ladder'], enter=B['enter'])
lr = np.log(cB / cA).diff().fillna(0)
pA, pB = wA.shift(1).fillna(1.0), wB.shift(1).fillna(1.0)     # 실제 체결 포지션
d = (pA != pB)
print('체결 포지션이 다른 날: %d일 / %d일 = %.1f%%' % (d.sum(), len(idx), d.mean() * 100))
print('  그 날들의 log(B/A) 합 = %+.4f   (총 %+.4f 의 %.0f%%)'
      % (lr[d].sum(), lr.sum(), lr[d].sum() / lr.sum() * 100))
print('  포지션이 같은 날들의 합 = %+.4f  (전액 거래비용)' % lr[~d].sum())

# B가 QLD, A가 SCHD 인 연속 블록 = '거짓 복귀' 1건
blk, s = [], None
v = (pB > pA).values
for i in range(len(v)):
    if v[i] and s is None: s = i
    if (not v[i] or i == len(v) - 1) and s is not None:
        e = i - 1 if not v[i] else i
        blk.append((idx[s], idx[e], e - s + 1)); s = None
rows = []
for a, b, n in blk:
    c = lr.loc[a:b].sum()
    rows.append(dict(시작=str(a.date()), 종료=str(b.date()), 일수=n, log기여=c,
                     수익차=(np.exp(c) - 1) * 100,
                     QQQ=(D['px'].loc[b] / D['px'].loc[a] - 1) * 100 if n > 1 else
                         D['px'].pct_change().loc[b] * 100))
t = pd.DataFrame(rows)
print('\nB가 QLD·A가 SCHD 였던 블록 = %d건, 총 %d일' % (len(t), t['일수'].sum()))
print('  이익 %d건 / 손실 %d건 | 합 log %+.4f' % ((t['log기여'] > 0).sum(), (t['log기여'] < 0).sum(), t['log기여'].sum()))
print('\n손실 상위 8건:')
print(t.nsmallest(8, 'log기여').to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
print('\n이익 상위 8건:')
print(t.nlargest(8, 'log기여').to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
print('\n블록 길이별:')
t['구간'] = pd.cut(t['일수'], [0, 2, 5, 20, 10000], labels=['1-2일', '3-5일', '6-20일', '21일+'])
print(t.groupby('구간', observed=True).agg(건수=('일수', 'size'), 평균일수=('일수', 'mean'),
      log합=('log기여', 'sum'), 평균수익차=('수익차', 'mean')).to_string(float_format=lambda x: f'{x:,.2f}'))
t.to_csv('hyst_blocks.csv', index=False, encoding='utf-8-sig')
