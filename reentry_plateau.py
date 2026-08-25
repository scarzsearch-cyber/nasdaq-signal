"""G계열(반등확인 + 최소경과일) 2차원 평탄성 표면. 출력: reentry_plateau.csv"""
import numpy as np, pandas as pd
import reentry_lib as L

D = L.build(); F = L.features(D); QLD, _ = L.bench(D)
MINS = list(range(0, 31, 2)) + [1, 3, 5, 7, 9, 11, 13, 15]
MINS = sorted(set(MINS))
XS = [0.0, 0.01, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]

rows = []
for k in (10, 20):
    for x in XS:
        cond = F[f'reb{k}'] >= x
        for m in MINS:
            c, w, t = L.run(D, [(('dd', L.EXIT), 1.0, 0), (cond, 1.0, m)])
            mm = L.met(c)
            rq = L.rolling_stats(c, QLD, windows=(3, 5))
            rows.append(dict(k=k, x=x * 100, mind=m, final=mm['final'], cagr=mm['cagr'] * 100,
                             mdd=mm['mdd'] * 100, qld3=rq[3]['win'], qld5=rq[5]['win'],
                             dotcom=L.seg_ret(c, *L.CRISES['닷컴 2000-2002'])))
df = pd.DataFrame(rows)
df.to_csv('reentry_plateau.csv', index=False, encoding='utf-8-sig')

for k in (10, 20):
    p = df[df.k == k].pivot(index='mind', columns='x', values='final')
    print(f'\n=== reb{k}: 최종배수 표면 (행=최소경과일, 열=반등%) ===')
    print(p.to_string(float_format=lambda v: '%6.1f' % v))
    sm = p.rolling(3, center=True, min_periods=2).mean().T.rolling(3, center=True, min_periods=2).mean().T
    print(f'--- 3x3 이웃평균 ---')
    print(sm.to_string(float_format=lambda v: '%6.1f' % v))
print('\n기준선 138.5x')
