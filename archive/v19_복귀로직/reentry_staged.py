"""
후보 S(X,q): 저점대비 X%p 회복하면 QLD를 q만큼만 되사고, 낙폭이 -11%를 회복하면 전량.
부분노출이 '휩쏘 손실 <-> V자 반등 포착'의 상충을 깰 수 있는지 본다.
"""
import numpy as np, pandas as pd
import reentry_lib as L
D = L.build(); QLD, QQQ = L.bench(D)
IDX, ddv, qldr, schdr = D['idx'], D['ddv'], D['qldr'], D['schdr']
N = len(IDX)

def run_s(x=None, q=0.5, exit_=L.EXIT, enter=L.ENTER, cost=L.COST, lag=1,
          ddv=ddv, qldr=qldr, schdr=schdr, n=None):
    n = n or len(ddv)
    w = np.empty(n); cur, ddmin = 1.0, 0.0
    for i in range(n):
        d = ddv[i]
        if cur >= 1.0:
            if d <= enter: cur, ddmin = 0.0, d
        else:
            ddmin = min(ddmin, d)
            if d <= enter: cur = 0.0
            elif d > exit_: cur = 1.0
            elif x is not None and (d - ddmin) >= x: cur = max(cur, q)
        w[i] = cur
    pos = np.empty(n); pos[:lag] = 1.0; pos[lag:] = w[:-lag]
    r = pos*qldr + (1-pos)*schdr; r = np.nan_to_num(r); r[0] = 0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1+r)*(1-cost*turn)), w, turn

print('%-18s %8s %6s %7s %6s %6s %6s %6s %6s %8s' %
      ('rule','final','CAGR','MDD','회전/년','3y','5y','10y','15y','닷컴'))
def rep(nm, x=None, q=0.5):
    eq, w, turn = run_s(x, q); c = pd.Series(eq, index=IDX); m = L.met(c)
    rq = L.rolling_stats(c, QLD)
    print('%-18s %8.1f %6.2f %7.2f %6.2f %6.1f %6.1f %6.1f %6.1f %8.1f' %
          (nm, m['final'], m['cagr']*100, m['mdd']*100, turn.sum()/m['years'],
           rq[3]['win'], rq[5]['win'], rq[10]['win'], rq[15]['win'],
           L.seg_ret(c, *L.CRISES['닷컴 2000-2002'])))
    return m['final']
rep('BASE -16/-11')
fs = {}
for q in (0.25, 0.5, 0.75):
    for x in (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10):
        fs[(q, x)] = rep('S(%.0f%%p, %d%%)' % (x*100, q*100), x, q)
print('\n각 q별 X방향 3점이동평균:')
for q in (0.25, 0.5, 0.75):
    xs = [0.02,0.03,0.04,0.05,0.06,0.08,0.10]; v = [fs[(q,x)] for x in xs]
    print('  q=%d%%: '%(q*100) + ' '.join('%.0f'%np.mean(v[max(0,i-1):i+2]) for i in range(len(v))))

print('\n=== 톱니 스트레스 ===')
rng = np.random.default_rng(7); n = 750; scen = []
for amp, drift in [(0.018,-0.0004),(0.025,-0.0006),(0.012,-0.0002),(0.030,-0.0008),(0.022,-0.0005)]:
    t = np.arange(n); b = np.cumsum(np.full(n,drift))+amp*np.sin(2*np.pi*t/45)+rng.normal(0,0.006,n)
    s = pd.Series(100*np.exp(b), index=pd.bdate_range('2000-01-03',periods=n))
    dds = (s/s.rolling(252,min_periods=60).max()-1).fillna(0).values
    scen.append((dds, np.nan_to_num(s.pct_change().values)*2-0.033/252, np.full(n,0.02/252)))
hdr = '%-16s'%'rule'
for i in range(len(scen)): hdr += ' %13s'%('시나리오%d'%(i+1))
print(hdr)
for nm, x, q in [('BASE',None,0.5), ('S(3%p,50%)',0.03,0.5), ('S(5%p,50%)',0.05,0.5),
                 ('S(3%p,25%)',0.03,0.25), ('S(5%p,25%)',0.05,0.25), ('S(8%p,50%)',0.08,0.5)]:
    line = '%-16s'%nm
    for dds, qr, sr in scen:
        eq, w, turn = run_s(x, q, ddv=dds, qldr=qr, schdr=sr, n=n)
        mdd = (eq/np.maximum.accumulate(eq)-1).min()
        line += ' %5.2f/%4.1f/%3.0f%%'%(eq[-1], turn.sum(), mdd*100)
    print(line)
print('  (표기: 최종배수 / 총회전율 / MDD)')
