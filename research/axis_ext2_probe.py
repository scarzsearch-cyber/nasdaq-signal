# -*- coding: utf-8 -*-
"""
[v54-b] 최선 후보 G1(단기/장기 RV 비율) 정밀검증

v54 의 26후보 중 G1~G6 을 5/6 통과한 유일한 **4블록 전구간 후보**.
막힌 곳은 4블록(2/4)이다. G7 파라미터 이웃 · 4블록 상세 · G11 집중도를 본다.

실행:  python research/axis_ext2_probe.py
"""
import os, sys
import os as _os
_ROOT=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0,_ROOT); sys.path.insert(0,_os.path.join(_ROOT,'research')); _os.chdir(_ROOT)
import numpy as np, pandas as pd
import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from axis_ext2 import state_latch, zsc, curve, SEGS, ENTER
from research_kit import concentration, leave_one_crisis_out, verdict
sys.stdout.reconfigure(encoding='utf-8')

D=DF.build('chain'); idx=D['idx']; N=len(idx)
comp=materials(D)
dfr=mix_monthly_from({k:comp[k] for k in ('div','ust5','gold')},{'div':.4,'ust5':.4,'gold':.2},idx)
rk=lev_r(D,2); ddv=np.asarray(D['ddv'],float)
S=pd.Series(np.asarray(D['px'],float))
rv21=S.pct_change().rolling(21,min_periods=21).std().values
rv126=S.pct_change().rolling(126,min_periods=126).std().values
ratio=np.where(rv126>0, rv21/rv126, np.nan)
rz=zsc(np.nan_to_num(ratio,nan=1.))
base=rule_w(ddv,ENTER,ENTER)
months=pd.Series(idx).dt.to_period('M').values
mstart=np.where(np.r_[False,months[1:]!=months[:-1]])[0]
L=20*252; st=list(range(0,N-L,63))
def dca(c,lo,hi,pay=10**9):
    m=mstart[(mstart>lo)&(mstart<hi)][:pay]
    return float(np.mean(c[hi-1]/c[m])) if len(m) else np.nan
def stats(w):
    c,_=curve(rk,dfr,w)
    a=np.array([dca(c,s,s+L,60) for s in st])
    return dict(median=float(np.median(a)),p20=float(np.percentile(a,20)),p5=float(np.percentile(a,5)))
B=stats(base); cb,_=curve(rk,dfr,base)

print("="*92); print("1. 파라미터 이웃 (G7) — 능선인가 첨탑인가"); print("="*92)
print("  %-10s%9s%9s%9s%9s%8s%7s"%('T >','중앙','P20','P5','MDD','전환','블록'))
for T in (-1.0,-0.5,0.0,0.25,0.5,0.75,1.0,1.5,3.0):
    w=state_latch(ddv,rz,None,T); c,pos=curve(rk,dfr,w)
    a=np.array([dca(c,s,s+L,60) for s in st])
    m=float((c/np.maximum.accumulate(c)-1).min())
    bw=sum(1 for _,x,y in SEGS
           if dca(c,int(idx.searchsorted(pd.Timestamp(x))),int(idx.searchsorted(pd.Timestamp(y),side='right')))
              > dca(cb,int(idx.searchsorted(pd.Timestamp(x))),int(idx.searchsorted(pd.Timestamp(y),side='right'))))
    win='O' if (np.median(a)>B['median'] and np.percentile(a,20)>B['p20'] and np.percentile(a,5)>B['p5']) else 'X'
    print("  %-10.2f%9.1f%9.1f%9.1f%8.1f%%%8d%5d/4  %s"
          %(T,np.median(a),np.percentile(a,20),np.percentile(a,5),m*100,
            int((np.abs(np.diff(pos))>1e-9).sum()),bw,win))
print("  현행:     %9.1f%9.1f%9.1f%8.1f%%%8d"%(B['median'],B['p20'],B['p5'],
      (cb/np.maximum.accumulate(cb)-1).min()*100,int((np.abs(np.diff(np.r_[base[0],base[:-1]]))>1e-9).sum())))

T0=0.5; W=state_latch(ddv,rz,None,T0); cr,_=curve(rk,dfr,W)
print("\n"+"="*92); print("2. 4블록 상세 (T=%.1f) — 어디서 지는가"%T0); print("="*92)
print("  %-10s%12s%12s%11s"%('블록','현행','G1','차이'))
for nm,a,b in SEGS:
    lo=int(idx.searchsorted(pd.Timestamp(a))); hi=int(idx.searchsorted(pd.Timestamp(b),side='right'))
    v0,v1=dca(cb,lo,hi),dca(cr,lo,hi)
    print("  %-10s%12.2f%12.2f%10.0f%%"%(nm,v0,v1,(v1/v0-1)*100))

print("\n"+"="*92); print("3. G11 집중도"); print("="*92)
def dlog(w):
    pos=np.r_[w[0],w[:-1]]; r=np.nan_to_num(pos*rk+(1-pos)*dfr); r[0]=0
    t=np.abs(np.diff(pos,prepend=pos[0])); return np.log((1+r)*(1-COST*t)),pos
lb,pb=dlog(base); lw,pw=dlog(W); d=lw-lb
diff=(pw!=pb); runs=[];i=0
while i<N:
    if diff[i]:
        j=i
        while j<N and diff[j]: j+=1
        runs.append((i,j)); i=j
    else: i+=1
contrib=[]
for k,(i,j) in enumerate(runs):
    hi=runs[k+1][0] if k+1<len(runs) else N
    contrib.append(d[i:hi].sum())
contrib=np.array(contrib)
print("  검산 기여합 %+.4f vs 전체 로그차 %+.4f"%(contrib.sum(),d.sum()))
def refit(drop):
    W2=W.copy()
    for k in drop:
        i,j=runs[k]; W2[max(0,i-1):j]=base[max(0,i-1):j]
    return stats(W2)
r=concentration(contrib,refit=refit,base=B,dates=[idx[i] for i,_ in runs],min_episodes=19)
print(verdict('G1 단기/장기 RV비율 — 집중도',r['checks'])['text'])
