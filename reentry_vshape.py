"""
후보 V(X): 기존 -11% 복귀선은 그대로 두고, "이번 피신 구간의 낙폭 저점 대비 X%p 회복"이면
조기 복귀하는 경로를 추가한다.  (경로의존 = 고정창 반등률과 다름)
   복귀 조건 = dd > -11%  OR  (dd - min_dd_since_entry >= X  AND  dd > -16%)
톱니 약세장에서는 dd 회복폭이 작아 발동하지 않고, V자 반등에서만 발동하는 것이 가설.
"""
import numpy as np, pandas as pd
import reentry_lib as L
D = L.build(); QLD, QQQ = L.bench(D)
IDX, ddv, qldr, schdr = D['idx'], D['ddv'], D['qldr'], D['schdr']
N = len(IDX)

def run_v(x=None, mind=0, exit_=L.EXIT, enter=L.ENTER, cost=L.COST, lag=1,
          ddv=ddv, qldr=qldr, schdr=schdr, n=None):
    n = n or len(ddv)
    w = np.empty(n); cur, ddmin, days = 1.0, 0.0, 0
    for i in range(n):
        d = ddv[i]
        if cur >= 1.0:
            if d <= enter:
                cur, ddmin, days = 0.0, d, 0
        else:
            days += 1
            ddmin = min(ddmin, d)
            if d <= enter:
                cur = 0.0
            elif d > exit_ or (x is not None and (d - ddmin) >= x and days >= mind):
                cur = 1.0
        w[i] = cur
    pos = np.empty(n); pos[0] = 1.0; pos[lag:] = w[:-lag]; pos[:lag] = 1.0
    r = pos*qldr + (1-pos)*schdr; r = np.nan_to_num(r); r[0] = 0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1+r)*(1-cost*turn)), w

def rep(nm, eq, w):
    c = pd.Series(eq, index=IDX); m = L.met(c); rq = L.rolling_stats(c, QLD)
    chg = int((np.abs(np.diff(w, prepend=w[0]))>1e-9).sum())
    print('%-16s %8.1f %6.2f %7.2f %5d %6.1f %6.1f %6.1f %6.1f %8.1f %8.1f' %
          (nm, m['final'], m['cagr']*100, m['mdd']*100, chg, rq[3]['win'], rq[5]['win'],
           rq[10]['win'], rq[15]['win'], L.seg_ret(c,*L.CRISES['닷컴 2000-2002']),
           L.seg_ret(c,*L.CRISES['2022 베어'])))
    return c

print('%-16s %8s %6s %7s %5s %6s %6s %6s %6s %8s %8s' %
      ('rule','final','CAGR','MDD','sw','3y','5y','10y','15y','닷컴','2022'))
eq,w = run_v(None); base_c = rep('BASE -16/-11', eq, w)
curves={}
for x in [0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.10,0.11,0.12,0.13,0.14,0.16,0.18,0.20,0.25]:
    eq,w = run_v(x); curves[x]=rep('V(%.0f%%p)'%(x*100), eq, w)
print('\n--- V(X) + 최소경과일 (노이즈 반등 억제) ---')
for x in (0.08,0.10,0.12):
    for m_ in (5,10,20):
        eq,w = run_v(x, mind=m_); rep('V(%.0f%%p)+%d일'%(x*100,m_), eq, w)

fs=[curves[x].iloc[-1] for x in sorted(curves)]
xs=sorted(curves)
print('\n5점이동평균:', ' '.join('%.0f'%np.mean(fs[max(0,i-2):i+3]) for i in range(len(fs))))
print('        (X=', ' '.join('%.0f'%(x*100) for x in xs), ')')

print('\n=== 인공 그라인딩 톱니 스트레스 ===')
rng = np.random.default_rng(7); n=750
print('%-12s %10s %10s %10s %10s' % ('시나리오','BASE','exit-16%','V(10%p)','V(12%p)'))
for trial,(amp,drift) in enumerate([(0.018,-0.0004),(0.025,-0.0006),(0.012,-0.0002),(0.030,-0.0008),(0.022,-0.0005)]):
    t=np.arange(n)
    b=np.cumsum(np.full(n,drift))+amp*np.sin(2*np.pi*t/45)+rng.normal(0,0.006,n)
    s=pd.Series(100*np.exp(b), index=pd.bdate_range('2000-01-03',periods=n))
    dds=(s/s.rolling(252,min_periods=60).max()-1).fillna(0).values
    qr=np.nan_to_num(s.pct_change().values)*2-0.033/252; sr=np.full(n,0.02/252)
    def f(x=None, exit_=L.EXIT):
        eq,w=run_v(x, exit_=exit_, ddv=dds, qldr=qr, schdr=sr, n=n)
        mdd=(eq/np.maximum.accumulate(eq)-1).min()
        return '%.2f배/%d회/%.0f%%'%(eq[-1], int((np.abs(np.diff(w,prepend=w[0]))>1e-9).sum()), mdd*100)
    print('%-12s %10s %10s %10s %10s' % ('시나리오%d(%.0f%%)'%(trial+1,dds.min()*100),
          f(), f(None,-0.16), f(0.10), f(0.12)))

print('\n=== V(X) 톱니 스트레스 전수 (X=3~10%p) ===')
rng = np.random.default_rng(7); n=750
scen=[]
for amp,drift in [(0.018,-0.0004),(0.025,-0.0006),(0.012,-0.0002),(0.030,-0.0008),(0.022,-0.0005)]:
    t=np.arange(n); b=np.cumsum(np.full(n,drift))+amp*np.sin(2*np.pi*t/45)+rng.normal(0,0.006,n)
    s=pd.Series(100*np.exp(b), index=pd.bdate_range('2000-01-03',periods=n))
    dds=(s/s.rolling(252,min_periods=60).max()-1).fillna(0).values
    scen.append((dds, np.nan_to_num(s.pct_change().values)*2-0.033/252, np.full(n,0.02/252)))
hdr='%-10s'%'X'
for i in range(len(scen)): hdr+=' %14s'%('시나리오%d'%(i+1))
print(hdr)
for x in [None,0.03,0.04,0.05,0.06,0.07,0.08,0.10]:
    line='%-10s'%('BASE' if x is None else '%.0f%%p'%(x*100))
    for dds,qr,sr in scen:
        eq,w=run_v(x, ddv=dds,qldr=qr,schdr=sr,n=n)
        mdd=(eq/np.maximum.accumulate(eq)-1).min()
        line+=' %6.2f/%2d/%3.0f%%'%(eq[-1], int((np.abs(np.diff(w,prepend=w[0]))>1e-9).sum()), mdd*100)
    print(line)

print('\n=== V 계열 연속상태 WFA (5년 Train -> 1년 Test, embargo 20일) ===')
GRID=[None]+[round(0.02+0.01*i,2) for i in range(24)]
EMB=20
def wfa_v(test_y=1):
    tr, te = 5*252, test_y*252
    start=tr; w0=1.0; ddmin0=0.0; days0=0; eq_acc=1.0; rows=[]; ci=[]; cv=[]
    while start+te<=N:
        lo,hi=max(0,start-tr), start-EMB
        best,bp=-1,None
        for x in GRID:
            e,_=run_v(x, ddv=ddv[lo:hi], qldr=qldr[lo:hi], schdr=schdr[lo:hi], n=hi-lo)
            if e[-1]>best: best,bp=e[-1],x
        # test 구간을 이전 상태 이어받아 실행
        n2=te; w=np.empty(n2); cur,ddmin,days=w0,ddmin0,days0
        for j in range(n2):
            i=start+j; d=ddv[i]
            if cur>=1.0:
                if d<=L.ENTER: cur,ddmin,days=0.0,d,0
            else:
                days+=1; ddmin=min(ddmin,d)
                if d<=L.ENTER: cur=0.0
                elif d>L.EXIT or (bp is not None and (d-ddmin)>=bp): cur=1.0
            w[j]=cur
        pos=np.empty(n2); pos[0]=w0; pos[1:]=w[:-1]
        r=pos*qldr[start:start+te]+(1-pos)*schdr[start:start+te]; r=np.nan_to_num(r); r[0]=0
        turn=np.abs(np.diff(pos,prepend=w0))
        e=np.cumprod((1+r)*(1-L.COST*turn))
        rows.append((str(IDX[start].date()), bp, (e[-1]-1)*100))
        ci.extend(IDX[start:start+te]); cv.extend(eq_acc*e)
        eq_acc*=e[-1]; w0,ddmin0,days0=cur,ddmin,days
        start+=te
    return rows, pd.Series(cv,index=pd.DatetimeIndex(ci))
rows,cv=wfa_v(1)
print('  %-12s %10s %10s'%('Test시작','선택X','Test수익'))
for d,x,r_ in rows: print('  %-12s %10s %9.1f%%'%(d, 'BASE' if x is None else '%.0f%%p'%(x*100), r_))
lo=IDX.searchsorted(cv.index[0]); hi=lo+len(cv)
eqb,_=run_v(None, ddv=ddv[lo:hi],qldr=qldr[lo:hi],schdr=schdr[lo:hi],n=hi-lo)
eq5,_=run_v(0.05, ddv=ddv[lo:hi],qldr=qldr[lo:hi],schdr=schdr[lo:hi],n=hi-lo)
print('  OOS %s ~ %s'%(cv.index[0].date(), cv.index[-1].date()))
print('  WFA(V계열)   %.2f배   고정 BASE %.2f배   고정 V(5%%p) %.2f배'%(cv.iloc[-1], eqb[-1], eq5[-1]))
print('  BASE 선택 횟수: %d / %d'%(sum(1 for _,x,_ in rows if x is None), len(rows)))
