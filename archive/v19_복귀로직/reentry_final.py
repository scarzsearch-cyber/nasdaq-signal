"""최종 후보군 요약표 + reentry_cost.csv / reentry_crisis.csv"""
import numpy as np, pandas as pd
import reentry_lib as L
from reentry_vshape import run_v
from reentry_staged import run_s
D = L.build(); QLD, QQQ = L.bench(D); IDX = D['idx']
A = np.ones(len(IDX), dtype=bool)

def curve_of(kind, p=None, q=0.5, cost=L.COST, lag=1):
    if kind == 'base':   eq, w = run_v(None, cost=cost, lag=lag)
    elif kind == 'nohyst': c, ws, _ = L.run(D, [(A,1.0,0)], cost=cost, lag=lag); return c, ws.values
    elif kind == 'cd':   c, ws, _ = L.run(D, [(A,1.0,p)], cost=cost, lag=lag); return c, ws.values
    elif kind == 'v':    eq, w = run_v(p, cost=cost, lag=lag)
    elif kind == 's':    eq, w, _ = run_s(p, q, cost=cost, lag=lag)
    return pd.Series(eq, index=IDX), w

CANDS = [('기존 -16/-11 (기준)', 'base', None, None),
         ('무히스테리시스 (복귀 -16%)', 'nohyst', None, None),
         ('CD(10) 쿨다운 10일', 'cd', 10, None),
         ('CD(13) 쿨다운 13일', 'cd', 13, None),
         ('V(5%p) 저점대비 5%p', 'v', 0.05, None),
         ('V(8%p) 저점대비 8%p', 'v', 0.08, None),
         ('S(3%p,50%) 부분복귀', 's', 0.03, 0.5)]

rows, crisis, cost = [], [], []
for nm, k, p, q in CANDS:
    c, w = curve_of(k, p, q or 0.5)
    m = L.met(c); rq = L.rolling_stats(c, QLD); rn = L.rolling_stats(c, QQQ)
    sw = int((np.abs(np.diff(w, prepend=w[0])) > 1e-9).sum())
    rows.append(dict(전략=nm, 최종배수=m['final'], CAGR=m['cagr']*100, MDD=m['mdd']*100,
                     Calmar=m['calmar'], Sharpe=m['sharpe'], Sortino=m['sortino'], 전환=sw,
                     연전환=sw/m['years'],
                     **{f'QLD{W}y': rq[W]['win'] for W in (1,3,5,10,15)},
                     **{f'QQQ{W}y': rn[W]['win'] for W in (1,3,5,10,15)}))
    crisis.append(dict(전략=nm, **{k2: L.seg_ret(c, *v) for k2, v in L.CRISES.items()}))
    row = dict(전략=nm)
    for cs in (0.0005, 0.001, 0.002, 0.003, 0.005):
        cc, _ = curve_of(k, p, q or 0.5, cost=cs)
        row[f'{cs*100:.2f}%'] = float(cc.iloc[-1])
    for lg in (2, 3, 5):
        cc, _ = curve_of(k, p, q or 0.5, lag=lg)
        row[f'지연{lg}일'] = float(cc.iloc[-1])
    cost.append(row)

df = pd.DataFrame(rows); pd.DataFrame(crisis).to_csv('reentry_crisis.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(cost).to_csv('reentry_cost.csv', index=False, encoding='utf-8-sig')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
print(df[['전략','최종배수','CAGR','MDD','전환','연전환','QLD3y','QLD5y','QLD10y','QLD15y']].to_string(index=False, float_format=lambda x:'%.1f'%x))
print()
print(pd.DataFrame(crisis).to_string(index=False, float_format=lambda x:'%.1f'%x))
print()
print(pd.DataFrame(cost).to_string(index=False, float_format=lambda x:'%.1f'%x))
