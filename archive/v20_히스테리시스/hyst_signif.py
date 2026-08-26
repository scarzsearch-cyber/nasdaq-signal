# -*- coding: utf-8 -*-
"""B-A 우위가 54년 실제 역사에서 통계적으로 구분 가능한가 + 대체지수 구간 제외 검증"""
import numpy as np, pandas as pd
from reentry_lib import run, met
import hist_data as H
from hyst_core import A, B, switches
pd.set_option('display.width', 250)
F = lambda x: f'{x:,.2f}'
rng = np.random.default_rng(20260826)

D = H.build_ext(); idx = D['idx']
cA, _, _ = run(D, A['ladder'], enter=A['enter'])
cB, _, _ = run(D, B['ladder'], enter=B['enter'])
lr = np.log(cB / cA).diff().fillna(0)

yr = lr.groupby(lr.index.year).sum()
nz = yr[yr.abs() > 1e-9]
print('===== 연간 log(B/A) 분포 (기여 있는 %d개 해) =====' % len(nz))
print('평균 %+.4f  표준편차 %.4f  중앙값 %+.4f' % (nz.mean(), nz.std(ddof=1), nz.median()))
print('양(+) %d해 / 음(-) %d해' % ((nz > 0).sum(), (nz < 0).sum()))
print('최대 %+.3f (%d)  최소 %+.3f (%d)' % (nz.max(), nz.idxmax(), nz.min(), nz.idxmin()))
print('왜도 %.2f  (음수면 「잦은 소액이익 + 드문 큰손실」)' % float(pd.Series(nz).skew()))
t = nz.mean() / (nz.std(ddof=1) / np.sqrt(len(nz)))
print('t통계량 = %.2f  (|t|<2 면 54년 표본으로도 A와 구분 불가)' % t)

# 연도 블록 부트스트랩
boot = np.array([rng.choice(nz.values, len(nz), replace=True).sum() for _ in range(20000)])
print('연도 부트스트랩 20,000회: B가 A를 이길 확률 %.1f%%   / 5%%분위 배수비 %.2f  95%%분위 %.2f'
      % ((boot > 0).mean() * 100, np.exp(np.percentile(boot, 5)), np.exp(np.percentile(boot, 95))))

print('\n===== 하위구간 안정성 =====')
segs = [('전구간 1972-2026', None, None), ('Composite 제외 1986-2026', '1986-01-02', None),
        ('QQQ 실물만 2000-2026', '2000-01-03', None), ('2011-2026 (SCHD 실물)', '2011-10-27', None),
        ('1972-1999', None, '1999-12-31'), ('1986-1999', '1986-01-02', '1999-12-31')]
rows = []
for lab, s, e in segs:
    a, wa, _ = run(D, A['ladder'], enter=A['enter'], start=s, end=e)
    b, wb, _ = run(D, B['ladder'], enter=B['enter'], start=s, end=e)
    ma, mb = met(a), met(b)
    rows.append(dict(구간=lab, 년=ma['years'], A배수=ma['final'], B배수=mb['final'],
                     B슬래시A=mb['final'] / ma['final'], A_MDD=ma['mdd'] * 100, B_MDD=mb['mdd'] * 100,
                     A연전환=len(switches(wa)) / ma['years'], B연전환=len(switches(wb)) / mb['years']))
print(pd.DataFrame(rows).to_string(index=False, float_format=F))

print('\n===== 상위 N개 해 제거 후 B/A =====')
s = nz.sort_values(ascending=False); tot = nz.sum()
print(' '.join('상위%d제거 %.2f' % (k, np.exp(tot - s.head(k).sum())) for k in (0, 1, 2, 3, 5, 7)))
print(' '.join('하위%d제거 %.2f' % (k, np.exp(tot - s.tail(k).sum())) for k in (1, 2, 3)))
