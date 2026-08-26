# -*- coding: utf-8 -*-
import numpy as np, pandas as pd
from reentry_lib import run
import hist_data as H
from hyst_core import A, B
D = H.build_ext()
for nm, S in [('A -16/-11', A), ('B -16/-16', B)]:
    c, _, _ = run(D, S['ladder'], enter=S['enter'])
    u = c / c.cummax() - 1
    t = u.idxmin()
    peak = c.loc[:t].idxmax()
    rec = c.loc[t:][c.loc[t:] >= c.loc[peak]]
    print('%s  MDD %.2f%%   고점 %s -> 저점 %s (%d일)  회복 %s'
          % (nm, u.min() * 100, peak.date(), t.date(), (t - peak).days,
             rec.index[0].date() if len(rec) else '미회복'))
    print('   상위 5 낙폭 국면:')
    # 국면별 최저점
    seg = u.copy(); done = []
    for _ in range(5):
        tt = seg.idxmin()
        if seg.loc[tt] > -0.15: break
        done.append((tt, seg.loc[tt]))
        lo = seg.index.searchsorted(tt) - 400; hi = seg.index.searchsorted(tt) + 400
        seg.iloc[max(0, lo):hi] = 0
    for tt, v in sorted(done):
        print('     %s  %.2f%%' % (tt.date(), v * 100))
