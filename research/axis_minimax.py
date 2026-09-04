# -*- coding: utf-8 -*-
"""
[v56-b] 미니맥스 순위 — 현행이 과적합의 산물인가

과적합의 지문은 **"고른 표본에서 1등, 나머지에서 붕괴"** 다.
겹치지 않는 6구간에서 각 규칙의 순위를 매기고 **최악 순위**로 줄세운다.

  · 현행이 어느 구간에서도 1등이 아닌데 최악 순위가 좋다면 -> 미니맥스(강건)
  · 현행이 특정 구간에서만 1등이고 나머지에서 무너진다면 -> 과적합

실행:  python research/axis_minimax.py
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


def median_rank(values):
    """짝수 개 구간의 중앙순위를 반정수까지 보존한다."""
    return float(np.median(np.asarray(values, dtype=float)))


def _selfcheck_median_rank():
    assert median_rank([19, 126, 94, 37, 84, 11]) == 60.5
    tied = [('later', 126, 134.5), ('earlier', 126, 134.0)]
    tied.sort(key=lambda t: (t[1], t[2]))
    assert tied[0][0] == 'earlier'


_selfcheck_median_rank()
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
# 겹치지 않는 6구간 (v18 표본을 통째로 쓰지 않는다)
WIN=[('1972-81','1972-01-01','1981-12-31'),('1982-90','1982-01-01','1990-12-31'),
     ('1991-99','1991-01-01','1999-12-31'),('2000-08','2000-01-01','2008-12-31'),
     ('2009-17','2009-01-01','2017-12-31'),('2018-26','2018-01-01','2026-08-26')]
R={}
for nm,a,b in WIN:
    order=sorted(combos,key=lambda c:-seg(c,a,b))
    for i,c in enumerate(order,1): R.setdefault(c,[]).append(i)
rows=[]
for c in combos:
    v=np.array(R[c]); rows.append((c,v.max(),median_rank(v),v.min()))
rows.sort(key=lambda t:(t[1],t[2]))
CUR=(-0.16,-0.16)
print("  겹치지 않는 6구간에서의 순위 (격자 210개, 최종배수)")
print("  **최악 순위**가 좋은 순으로 정렬 = 미니맥스")
print("  %-12s%10s%10s%10s   %s"%('규칙','최악순위','중앙순위','최고순위','구간별'))
for c,mx,md,mn in rows[:8]:
    mk='  <- 현행' if c==CUR else ''
    print("  %-12s%10d%10.1f%10d   %s%s"%('%.0f/%.0f'%(c[0]*100,c[1]*100),mx,md,mn,
          ' '.join('%3d'%x for x in R[c]),mk))
i=[j for j,(c,_,_,_) in enumerate(rows,1) if c==CUR][0]
if i>8:
    c,mx,md,mn=[r for r in rows if r[0]==CUR][0]
    print("  ...")
    print("  %-12s%10d%10.1f%10d   %s  <- 현행"%('-16/-16',mx,md,mn,' '.join('%3d'%x for x in R[CUR])))
print()
print("  현행의 미니맥스 순위: **%d위 / %d**"%(i,len(rows)))
# 각 구간 1등들의 최악 순위
print()
print("  각 구간 1등이 다른 구간에서는?")
print("  %-12s%10s%10s   %s"%('구간 1등','최악순위','중앙순위','구간별'))
seen=set()
for nm,a,b in WIN:
    top=max(combos,key=lambda c:seg(c,a,b))
    if top in seen: continue
    seen.add(top)
    v=np.array(R[top])
    print("  %-12s%10d%10.1f   %s"%('%.0f/%.0f'%(top[0]*100,top[1]*100),v.max(),median_rank(v),
          ' '.join('%3d'%x for x in v)))
