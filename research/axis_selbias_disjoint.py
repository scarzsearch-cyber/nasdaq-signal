# -*- coding: utf-8 -*-
"""
[v57] v56 T3 정정 — 평가창을 겹치지 않게 잘라 독립 관측 수를 정직하게 센다

v56 T3 은 결정시점 T 마다 (T, 2026] 으로 평가했다. **7개 창이 전부 2026 에서
끝나므로 서로 포함관계**다 — 1985 창이 나머지를 전부 포함한다.
'0/7' 은 독립 관측 7개가 아니다. 겹치지 않는 창으로 다시 잰다.

실행:  python research/axis_selbias_disjoint.py
"""
import os, sys
import os as _os
_ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0,_ROOT); _os.chdir(_ROOT)
import numpy as np, pandas as pd
import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
sys.stdout.reconfigure(encoding='utf-8')
D=DF.build('chain'); idx=D['idx']
comp=materials(D)
dfr=mix_monthly_from({k:comp[k] for k in ('div','ust5','gold')},{'div':.4,'ust5':.4,'gold':.2},idx)
rk=lev_r(D,2); ddv=np.asarray(D['ddv'],float)
combos=[(round(e,2),round(x,2)) for e in np.arange(-0.24,-0.09,0.01) for x in np.arange(e,-0.03,0.01)]
C={}
for c in combos:
    w=rule_w(ddv,c[0],c[1]); pos=np.r_[w[0],w[:-1]]
    r=np.nan_to_num(pos*rk+(1-pos)*dfr); r[0]=0
    t=np.abs(np.diff(pos,prepend=pos[0])); C[c]=np.cumprod((1+r)*(1-COST*t))
def seg(c,a,b):
    lo=int(idx.searchsorted(pd.Timestamp(a))); hi=int(idx.searchsorted(pd.Timestamp(b),side='right'))
    return float(C[c][hi-1]/C[c][lo])
CUR=(-0.16,-0.16)
print("  [정정] v56 의 T3 은 평가창이 전부 2026 에서 끝나 **서로 포함관계**였다.")
print("         '7/7' 은 독립 관측 7개가 아니다. 겹치지 않게 다시 잰다.\n")
print("  겹치지 않는 평가창 (선택은 그 시점 이전 자료로만)")
print("  %-10s%-12s%12s%12s%10s"%('선택시점','뽑힌 규칙','이후 선택','이후 고정','차이'))
BL=[('1986-01-01','1995-12-31',1985),('1996-01-01','2005-12-31',1995),
    ('2006-01-01','2015-12-31',2005),('2016-01-01','2026-08-26',2015)]
w=0
for a,b,T in BL:
    best=max(combos,key=lambda c:seg(c,'1972-01-01','%d-12-31'%T))
    vs,vf=seg(best,a,b),seg(CUR,a,b)
    w+=(vs>vf)
    print("  %-10d%-12s%12.2f%12.2f%9.0f%%"%(T,'%.0f/%.0f'%(best[0]*100,best[1]*100),vs,vf,(vs/vf-1)*100))
print("\n  **겹치지 않는 4개 창에서 선택 절차가 고정을 이긴 횟수: %d/4**"%w)
print("  (v56 이 보고한 0/7 은 실질 이 4개다. 결론은 같지만 표본 수를 정확히 적는다)")
