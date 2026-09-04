# -*- coding: utf-8 -*-
"""
[v58-b] 메타가 왜 못 고르는가 — 위기 사례 + 시대 이월성 (§23

v58 본문: Oracle 은 고정을 +288% 앞서는데 메타 7종은 상한의 0% 이하를 포착했다.
여기서 그 기전을 본다.

  · 각 위기 직전에 메타A(직전 10년 1등)가 무엇을 들고 들어갔나
  · Oracle 이 그 위기에서 고른 것과 얼마나 다른가
  · **"직전 10년 1등"이 "다음 10년 1등"과 같은 빈도**

실행:  python research/axis_meta_crisis.py
"""
import os, sys
import os as _os
_ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0,_ROOT); sys.path.insert(0,_os.path.join(_ROOT,'research')); _os.chdir(_ROOT)
import numpy as np, pandas as pd
import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from axis_meta import POOL, CUR, LOOK
sys.stdout.reconfigure(encoding='utf-8')
D=DF.build('chain'); idx=D['idx']; N=len(idx)
comp=materials(D)
dfr=mix_monthly_from({k:comp[k] for k in ('div','ust5','gold')},{'div':.4,'ust5':.4,'gold':.2},idx)
rk=lev_r(D,2); ddv=np.asarray(D['ddv'],float)
W={c:rule_w(ddv,c[0],c[1]) for c in POOL}
LG={}
for c in POOL:
    pos=np.r_[W[c][0],W[c][:-1]]
    r=np.nan_to_num(pos*rk+(1-pos)*dfr); r[0]=0
    t=np.abs(np.diff(pos,prepend=pos[0])); LG[c]=np.log((1+r)*(1-COST*t))
def mult(c,lo,hi): return float(np.exp(LG[c][lo:hi].sum()))
CR=[('1987 블랙먼데이','1987-08-01','1988-12-31'),('1990 걸프','1990-06-01','1991-06-30'),
    ('2000-02 닷컴','2000-03-01','2002-12-31'),('2008 GFC','2007-10-01','2009-06-30'),
    ('2020 코로나','2020-02-01','2020-12-31'),('2022 베어','2021-11-01','2023-06-30')]
print("  %-16s%-14s%-14s%12s%12s%11s"%('위기','메타A가 고른 것','Oracle 1등','메타A 수익','Oracle','현행'))
gapA=[]
for nm,a,b in CR:
    lo=int(idx.searchsorted(pd.Timestamp(a))); hi=int(idx.searchsorted(pd.Timestamp(b),side='right'))
    # 메타 A: 위기 직전까지 과거 10년 최종배수 1등
    pa=max(POOL,key=lambda c:(mult(c,max(0,lo-LOOK),lo),-POOL.index(c)))
    po=max(POOL,key=lambda c:(mult(c,lo,hi),-POOL.index(c)))
    va,vo,vc=mult(pa,lo,hi)-1,mult(po,lo,hi)-1,mult(CUR,lo,hi)-1
    gapA.append(va-vc)
    print("  %-16s%-14s%-14s%11.1f%%%11.1f%%%10.1f%%"
          %(nm,'%.0f/%.0f'%(pa[0]*100,pa[1]*100),'%.0f/%.0f'%(po[0]*100,po[1]*100),
            va*100,vo*100,vc*100))
print("\n  메타A 가 위기에서 현행을 이긴 횟수: %d/%d  (중앙 %+.1f%%p)"
      %(sum(1 for g in gapA if g>0),len(gapA),np.median(gapA)*100))
# 직전 10년 1등이 다음 **완료된** 10년에도 1등인가
print("\n  '직전 10년 1등'이 '다음 10년 1등'과 같은가")
print("  %-12s%-14s%-14s%10s"%('구간','직전10년 1등','그 10년 1등','같은가'))
same=0; tot=0
def completed_decades(index, candidates):
    """끝난 달력연도만 채택한다. 마지막 해가 진행 중이면 보수적으로 제외한다."""
    if len(index) == 0:
        return []
    last_year = int(index[-1].year)
    return [y for y in candidates if last_year > y + 9]


# 2026-08 표본에서는 2022~2031을 빼고, 2032년 관측이 생긴 뒤에만 넣는다.
assert completed_decades(pd.DatetimeIndex(['2026-08-28']), (2012, 2022)) == [2012]
assert completed_decades(pd.DatetimeIndex(['2032-01-02']), (2022,)) == [2022]
all_starts = (1992, 2002, 2012, 2022)
starts = completed_decades(idx, all_starts)
for y in starts:
    a='%d-01-01'%y; b='%d-12-31'%(y+9)
    lo=int(idx.searchsorted(pd.Timestamp(a))); hi=min(N,int(idx.searchsorted(pd.Timestamp(b),side='right')))
    prev=max(POOL,key=lambda c:(mult(c,max(0,lo-LOOK),lo),-POOL.index(c)))
    now=max(POOL,key=lambda c:(mult(c,lo,hi),-POOL.index(c)))
    tot+=1; same+=(prev==now)
    print("  %-12s%-14s%-14s%10s"%('%d-%d'%(y,y+9),'%.0f/%.0f'%(prev[0]*100,prev[1]*100),
          '%.0f/%.0f'%(now[0]*100,now[1]*100),'O' if prev==now else 'X'))
print("\n  일치 %d/%d"%(same,tot))
omitted = [y for y in all_starts if y not in starts]
if omitted:
    print("  미완성 창 제외: %s (자료 마지막 %s)" %
          (', '.join('%d-%d' % (y, y + 9) for y in omitted), idx[-1].date()))
