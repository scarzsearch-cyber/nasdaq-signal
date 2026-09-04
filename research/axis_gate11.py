# -*- coding: utf-8 -*-
"""
[v53-b] Gate 11 정식 적용 — v53 RV 후보의 성과 집중도

v53 은 관문 10개를 **전부** 통과했다. 그런데 우위가 몇 사건에 몰려 있었다.
그 검사를 research_kit 에 박고(concentration / leave_one_crisis_out)
여기서 정식으로 돌린다.

  · 갈린 구간을 일별 로그차로 분해하고 **합이 전체 로그차와 같은지 먼저 검산**한다
    (첫 시도는 체결 지연 한 칸을 빠뜨려 0.831 vs 1.240 이었다)
  · 독립 위기 수를 252일 간격으로 센다
  · 상위 1/3/5 사건을 빼고 **재시뮬**한다
  · 위기를 하나씩 빼고 재시뮬한다 (leave-one-crisis-out)

실행:  python research/axis_gate11.py
"""
import os, sys
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _ROOT); sys.path.insert(0, _os.path.join(_ROOT, 'research'))
_os.chdir(_ROOT)
import numpy as np, pandas as pd
import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from axis_rvstate import rule
from research_kit import concentration as _concentration, leave_one_crisis_out, verdict
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass

D=DF.build('chain'); idx=D['idx']; N=len(idx)
comp=materials(D)
dfr=mix_monthly_from({k:comp[k] for k in ('div','ust5','gold')},{'div':.4,'ust5':.4,'gold':.2},idx)
rk=lev_r(D,2); ddv=np.asarray(D['ddv'],float)
S=pd.Series(np.asarray(D['px'],float))
rv=S.pct_change().rolling(21,min_periods=21).std().values
rvz=((rv-pd.Series(rv).rolling(756,min_periods=252).mean().values)
     /pd.Series(rv).rolling(756,min_periods=252).std().values)
base=rule_w(ddv,-0.16,-0.16); W=rule(ddv,rvz,0.25)
months=pd.Series(idx).dt.to_period('M').values
mstart=np.where(np.r_[False,months[1:]!=months[:-1]])[0]
L=20*252; st=list(range(0,N-L,63))


def independent_rows(rows, gap=252):
    """직전 모든 사건과 `gap` 거래행을 초과해 떨어진 사건만 독립으로 센다."""
    out=[]; last=-10**9
    for row in rows:
        row=int(row)
        if row-last > gap:
            out.append(row)
        last=row
    return out


def concentration_rows(contrib, rows, refit=None, base=None,
                       min_episodes=19, top=(1,3,5), gap_rows=252):
    """공용 집중도 검사의 독립 간격만 달력일이 아닌 거래행으로 공급한다."""
    rows=list(rows)
    if len(rows) != len(contrib):
        raise ValueError('event rows 와 contrib 길이가 다르다')
    r=_concentration(contrib, refit=refit, base=base, dates=None,
                     min_episodes=min_episodes, top=top)
    indep=independent_rows(rows, gap_rows)
    for k,(label,_,_) in enumerate(r['checks']):
        if label.startswith('독립 위기가'):
            r['checks'][k]=(label, len(indep) >= min_episodes,
                            '%d개 (%d거래행 초과 간격)'%(len(indep),gap_rows))
            break
    else:
        raise AssertionError('독립 위기 관문이 없다')
    r['n_indep']=len(indep)
    r['independent_rows']=indep
    return r


assert independent_rows([0,252,253,506]) == [0,506]

def dlog(w):
    pos=np.r_[w[0],w[:-1]]
    r=np.nan_to_num(pos*rk+(1-pos)*dfr); r[0]=0
    t=np.abs(np.diff(pos,prepend=pos[0]))
    return np.log((1+r)*(1-COST*t)), pos
def stats(w):
    l,_=dlog(w); c=np.exp(np.cumsum(l))
    a=np.array([np.mean(c[s+L-1]/c[mstart[(mstart>s)&(mstart<s+L)][:60]]) for s in st])
    return dict(median=float(np.median(a)),p20=float(np.percentile(a,20)),p5=float(np.percentile(a,5)))

lb,pb=dlog(base); lw,pw=dlog(W); d=lw-lb
diff=(pw!=pb); runs=[]; i=0
while i<N:
    if diff[i]:
        j=i
        while j<N and diff[j]: j+=1
        runs.append((i,j)); i=j
    else: i+=1
contrib=[]
for k,(i,j) in enumerate(runs):
    hi = runs[k+1][0] if k+1<len(runs) else N
    contrib.append(d[i:hi].sum())
contrib=np.array(contrib)
print("  검산: 기여합 %+.4f  vs  전체 로그차 %+.4f"%(contrib.sum(), d.sum()))
assert abs(contrib.sum()-d.sum())<1e-9, "분해 불일치"

def refit(drop):
    W2=W.copy()
    for k in drop:
        i,j=runs[k]; W2[max(0,i-1):j]=base[max(0,i-1):j]
    return stats(W2)
B=stats(base)
print("\n"+"="*92); print("Gate 11 — 성과 집중도 (research_kit.concentration)"); print("="*92)
r=concentration_rows(contrib, refit=refit, base=B,
                     rows=[i for i,_ in runs], min_episodes=19, gap_rows=252)
assert r['n_indep'] == 9, '현재 독립 사건 수는 9여야 한다: %r' % r['independent_rows']
print(verdict('v53 RV 상태변수 — 집중도', r['checks'])['text'])

print("\n"+"="*92); print("Gate 11-b — leave-one-crisis-out"); print("="*92)
dates_of={k: idx[i] for k,(i,_) in enumerate(runs)}
CR=[('1973-74 오일','1973-01-01','1975-12-31'),('1980-82 인플레','1980-01-01','1982-12-31'),
    ('1983-84 조정','1983-01-01','1984-12-31'),('1987 블랙먼데이','1987-01-01','1988-12-31'),
    ('1990 걸프','1989-06-01','1990-12-31'),('1992 조정','1992-01-01','1992-12-31'),
    ('2000-02 닷컴','2000-01-01','2003-12-31'),('2008 GFC','2007-06-01','2009-12-31'),
    ('2020 코로나','2020-01-01','2020-12-31'),('2022 베어','2021-11-01','2023-12-31')]
lo=leave_one_crisis_out(refit,B,CR,dates_of)
print("  %-16s%8s  %s"%('제외한 위기','유지','재시뮬 결과'))
for nm,ok,ev in lo['rows']:
    print("  %-16s%8s  %s"%(nm,'-' if ok is None else ('O' if ok else 'X'),ev))
print()
print(verdict('v53 RV 상태변수 — 위기별 의존', lo['checks'])['text'])
