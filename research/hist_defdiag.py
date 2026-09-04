# -*- coding: utf-8 -*-
"""방어자산 대체의 부작용 진단 — MDD 가 어디서 왜 커지는가."""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np, pandas as pd
from reentry_lib import run, met
import hist_defensive as DF
from hyst_core import A, B

def mdd_trace(c):
    pk = c.cummax(); dd = c / pk - 1
    t = dd.idxmin(); p = c.loc[:t].idxmax()
    rec = c.loc[t:][c.loc[t:] >= c.loc[p]]
    return p, t, float(dd.min()), (rec.index[0] if len(rec) else None)

print('== 전략 MDD 위치 (2000-2026) ==')
for nm, k in [('연2% 현금', 'cash2'), ('T-bill', 'tbill'), ('BE/ME 가치', 'value'), ('D/P 배당', 'div')]:
    for S in (A, B):
        c, w, t = run(DF.build(k), S['ladder'], enter=S['enter'], cost=0.001, start='2000-01-03')
        p, tr, d, r = mdd_trace(c)
        print('%-12s %-11s MDD %7.2f%%  %s -> %s  회복 %s'
              % (nm if S is A else '', S['name'], d * 100, p.date(), tr.date(),
                 r.date() if r is not None else '미회복'))

print('\n== 방어자산 자체의 위기별 성과 (자산 그 자체, 전략 무관) ==')
idx = DF.H.build_ext()['idx']
ser = {nm: pd.Series(DF.defensive(idx, k), index=idx)
       for nm, k in [('연2% 현금', 'pure_cash2'), ('T-bill', 'pure_tbill'),
                     ('BE/ME Hi30', 'pure_value'), ('D/P Hi30', 'pure_div')]}
qld = pd.Series(DF.H.build_ext()['qldr'], index=idx)
ser['QLD(참고)'] = qld
CR = [('1973-74 약세장', '1973-01-11', '1974-10-03'), ('1987 대폭락', '1987-08-25', '1987-12-04'),
      ('2000-02 닷컴', '2000-03-10', '2002-10-09'), ('2007-09 금융위기', '2007-10-31', '2009-03-09'),
      ('2020 코로나', '2020-02-19', '2020-03-23'), ('2022 인플레', '2021-11-19', '2022-12-28')]
hdr = '%-16s' % '위기' + ''.join('%13s' % n for n in ser)
print(hdr)
for nm, s0, s1 in CR:
    row = '%-16s' % nm
    for n, v in ser.items():
        # s0 종가에서 s1 종가까지의 수익이므로 s0 당일 수익(전일→s0)은 제외한다.
        seg = v.loc[s0:s1].iloc[1:]
        row += '%12.1f%%' % ((np.prod(1 + seg) - 1) * 100)
    print(row)

print('\n== 방어자산 자체의 최대낙폭 ==')
for n, v in ser.items():
    lv = (1 + v).cumprod()
    p, tr, d, r = mdd_trace(lv)
    print('%-12s MDD %7.2f%%  %s -> %s' % (n, d * 100, p.date(), tr.date()))
