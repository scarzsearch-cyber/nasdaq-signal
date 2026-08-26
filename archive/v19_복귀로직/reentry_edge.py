"""복귀선을 진입선(-16%) 아래까지 밀어보고, 개선이 '레버리지 노출 증가'의 부산물인지 검사."""
import numpy as np, pandas as pd
import reentry_lib as L
D = L.build(); QLD, QQQ = L.bench(D)
ALWAYS = np.ones(len(D['idx']), dtype=bool)

def show(nm, ladder, enter=L.ENTER):
    c, w, t = L.run(D, ladder, enter=enter)
    m = L.met(c); rq = L.rolling_stats(c, QLD)
    chg = int((np.abs(np.diff(w.values, prepend=w.values[0])) > 1e-9).sum())
    print('%-24s %8.1f %6.2f %7.2f %5d %6.1f%% %6.1f %6.1f %6.1f' %
          (nm, m['final'], m['cagr']*100, m['mdd']*100, chg,
           (1-w.values).mean()*100, rq[3]['win'], rq[5]['win'], rq[10]['win']))
    return m

print('%-24s %8s %6s %7s %5s %7s %6s %6s %6s' % ('rule','final','CAGR','MDD','sw','SCHD비중','3y','5y','10y'))
show('BASE -16/-11', L.BASE_LADDER)
print('--- 복귀선을 진입선 밑으로 (음의 히스테리시스) ---')
for x in [-0.16, -0.17, -0.18, -0.20, -0.25, -0.30, -0.40, -0.60]:
    show(f'exit {x*100:.0f}%', [(('dd', x), 1.0, 0)])
print('--- 쿨다운 계열 ---')
for n in (0, 5, 10, 13, 20):
    show(f'CD({n})', [(ALWAYS, 1.0, n)])
print('--- 대조 ---')
m = L.met(QLD); print('%-24s %8.1f %6.2f %7.2f' % ('QLD 계속보유', m['final'], m['cagr']*100, m['mdd']*100))

print('\n=== 위기별: 복귀선을 밀수록 무엇이 무너지나 (%) ===')
print('%-14s %8s %8s %8s %8s %8s %8s' % ('구간','BASE','exit-16','exit-18','exit-25','CD(10)','QLD'))
curves = {'BASE': L.run(D, L.BASE_LADDER)[0]}
for x in (-0.16, -0.18, -0.25):
    curves[f'exit{x}'] = L.run(D, [(('dd', x), 1.0, 0)])[0]
curves['CD10'] = L.run(D, [(ALWAYS, 1.0, 10)])[0]
for k,(s,e) in L.CRISES.items():
    print('%-14s %7.1f%% %7.1f%% %7.1f%% %7.1f%% %7.1f%% %7.1f%%' % (k[:12],
        L.seg_ret(curves['BASE'],s,e), L.seg_ret(curves['exit-0.16'],s,e),
        L.seg_ret(curves['exit-0.18'],s,e), L.seg_ret(curves['exit-0.25'],s,e),
        L.seg_ret(curves['CD10'],s,e), L.seg_ret(QLD,s,e)))

print('\n=== 인공 그라인딩 약세장 스트레스 (닷컴형 장기하락 + -16% 근처 톱니) ===')
# QQQ 실제 경로를 쓰되, 2000-2002 구간의 낙폭을 -11~-18% 사이에서 진동시키는 합성 경로
rng = np.random.default_rng(7)
n = 750
for trial, (amp, drift) in enumerate([(0.018, -0.0004), (0.025, -0.0006), (0.012, -0.0002)]):
    # 톱니: 낙폭이 -11%~-18%를 왕복하며 서서히 하락
    t = np.arange(n)
    base = np.cumsum(np.full(n, drift)) + amp*np.sin(2*np.pi*t/45) + rng.normal(0, 0.006, n)
    px = 100*np.exp(base)
    s = pd.Series(px, index=pd.bdate_range('2000-01-03', periods=n))
    dd = (s/s.rolling(252, min_periods=60).max()-1).fillna(0).values
    qr = np.nan_to_num(s.pct_change().values)*2 - 0.033/252
    sr = np.full(n, 0.02/252)
    def sim(mode, p):
        w=np.empty(n); cur=1.0; days=0
        for i in range(n):
            d=dd[i]
            if cur>=1.0:
                if d<=-0.16: cur, days = 0.0, 0
            else:
                days+=1
                if d<=-0.16: cur=0.0
                elif (d>p) if mode=='h' else (days>=p): cur=1.0
            w[i]=cur
        pos=np.empty(n); pos[0]=1.0; pos[1:]=w[:-1]
        r=pos*qr+(1-pos)*sr; r[0]=0
        turn=np.abs(np.diff(pos,prepend=1.0))
        eq=np.cumprod((1+r)*(1-0.001*turn))
        return eq[-1], int((np.abs(np.diff(w,prepend=w[0]))>1e-9).sum()), (eq/np.maximum.accumulate(eq)-1).min()
    a=sim('h',-0.11); b=sim('h',-0.16); c=sim('c',10)
    print(' 시나리오%d 최저낙폭 %.1f%%  BASE %.2f배(%d회, MDD%.0f%%) | exit-16%% %.2f배(%d회, MDD%.0f%%) | CD(10) %.2f배(%d회, MDD%.0f%%)'
          % (trial+1, dd.min()*100, a[0],a[1],a[2]*100, b[0],b[1],b[2]*100, c[0],c[1],c[2]*100))
