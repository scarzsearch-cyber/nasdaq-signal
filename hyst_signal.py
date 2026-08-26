# -*- coding: utf-8 -*-
"""
신호 기준자산 비교: QQQ 낙폭 신호  vs  QLD 낙폭 신호
- 사전에 정한 소수 후보만 비교 (대규모 Grid Search 금지 규약 준수)
- 합성 QLD 구간과 실물 QLD 구간을 반드시 분리해 보고
"""
import numpy as np, pandas as pd
from reentry_lib import run, met, rolling_stats
import hist_data as H
from hyst_core import switches
pd.set_option('display.width', 260)
F = lambda x: f'{x:,.2f}'

D = H.build_ext(); idx = D['idx']
qld_lv = pd.Series(np.cumprod(1 + D['qldr']), index=idx)
dd_qld = (qld_lv / qld_lv.rolling(252, min_periods=252).max() - 1).fillna(0)
dd_qqq = D['dd']

print('===== 0. 두 낙폭 지표의 관계 =====')
print('상관계수(레벨)          : %.4f' % np.corrcoef(dd_qqq, dd_qld)[0, 1])
print('DD_QLD / DD_QQQ 중앙값 : %.3f배' % (dd_qld[dd_qqq < -0.02] / dd_qqq[dd_qqq < -0.02]).median())
REAL = '2006-06-22'
pre = idx < pd.Timestamp(REAL)
print('합성 QLD 구간 %d일(%.0f%%) / 실물 QLD 구간 %d일'
      % (pre.sum(), pre.mean() * 100, (~pre).sum()))
print('** 합성 구간의 QLD 수익률은 2*QQQ - 상수 이므로 DD_QLD 는 QQQ 에서 결정론적으로 파생된다.')
print('   즉 1972~2006 구간의 「QLD 신호」는 QQQ 신호의 재표현일 뿐 독립 정보가 아니다.')

# 사전 지정 후보 (소수)
CAND = [('QQQ  -16/-11 (현행)', 'qqq', -0.16, -0.11),
        ('QQQ  -16/-16',        'qqq', -0.16, -0.16),
        ('QQQ  -16/-15',        'qqq', -0.16, -0.15),
        ('QLD  -25/-25',        'qld', -0.25, -0.25),
        ('QLD  -25/-15',        'qld', -0.25, -0.15),
        ('QLD  -30/-30',        'qld', -0.30, -0.30),
        ('QLD  -30/-20',        'qld', -0.30, -0.20),
        ('QLD  -35/-35',        'qld', -0.35, -0.35),
        ('QLD  -35/-25',        'qld', -0.35, -0.25)]


def go(kind, enter, exit_, start=None, end=None, cost=0.001):
    Dx = dict(D)
    Dx['ddv'] = (dd_qld if kind == 'qld' else dd_qqq).values.astype(float)
    return run(Dx, [(('dd', exit_), 1.0, 0)], enter=enter, cost=cost, start=start, end=end)


for lab, s, e in [('전구간 1972-2026 (합성 QLD 34년 포함)', None, None),
                  ('실물 QLD 구간만 2006-06-22 ~ 2026-08', REAL, None),
                  ('2000-2026 (QQQ 실물)', '2000-01-03', None)]:
    rows = []
    qs = idx.searchsorted(pd.Timestamp(s)) if s else 0
    qe = idx.searchsorted(pd.Timestamp(e), side='right') if e else len(idx)
    qref = pd.Series(np.cumprod(1 + D['qldr'][qs:qe]), index=idx[qs:qe])
    for nm, k, en, ex in CAND:
        c, w, _ = go(k, en, ex, s, e)
        m = met(c); rs = rolling_stats(c, qref)
        rows.append(dict(후보=nm, 최종배수=m['final'], CAGR=m['cagr'] * 100, MDD=m['mdd'] * 100,
                         Calmar=m['calmar'], Sharpe=m['sharpe'], 전환=len(switches(w)),
                         연전환=len(switches(w)) / m['years'],
                         **{f'{x}Y승률': rs[x]['win'] for x in (3, 5) if x in rs}))
    print('\n===== %s =====' % lab)
    print(pd.DataFrame(rows).to_string(index=False, float_format=F))

print('\n===== 평탄성: QLD 신호 진입선 주변 (히스테리시스 0, 실물구간) =====')
rows = []
for en in np.arange(-0.40, -0.145, 0.025):
    c, w, _ = go('qld', round(en, 3), round(en, 3), REAL, None)
    c2, _, _ = go('qld', round(en, 3), round(en, 3), None, None)
    rows.append(dict(진입선=f'{en*100:.1f}%', 실물구간배수=met(c)['final'], MDD=met(c)['mdd'] * 100,
                     전환=len(switches(w)), 전구간배수=met(c2)['final']))
print(pd.DataFrame(rows).to_string(index=False, float_format=F))
