"""
복귀(SCHD -> QLD) 로직 후보 그리드.  출력: reentry_results.csv / reentry_plateau.csv
진입선 -16%는 고정. 복귀 규칙만 바꾼다.
"""
import numpy as np, pandas as pd, itertools, sys
import reentry_lib as L

D = L.build(); F = L.features(D)
QLD, QQQ = L.bench(D)
COSTS = [0.0005, 0.001, 0.002, 0.003, 0.005]


def evaluate(name, family, ladder, params=''):
    c, w, turn = L.run(D, ladder)
    m = L.met(c)
    rq = L.rolling_stats(c, QLD)
    rn = L.rolling_stats(c, QQQ)
    chg = int((np.abs(np.diff(w.values, prepend=w.values[0])) > 1e-9).sum())
    row = dict(family=family, name=name, params=params,
               final=m['final'], cagr=m['cagr'] * 100, mdd=m['mdd'] * 100,
               calmar=m['calmar'], sharpe=m['sharpe'], sortino=m['sortino'],
               chg=chg, turn_yr=float(turn.sum()) / m['years'],
               schd_share=float((1 - w.values).mean()) * 100)
    for W in (1, 3, 5, 10, 15):
        row[f'qld{W}'] = rq[W]['win'] if W in rq else np.nan
        row[f'qqq{W}'] = rn[W]['win'] if W in rn else np.nan
        row[f'ex{W}'] = rq[W]['ex_med'] if W in rq else np.nan
    for k, (s, e) in L.CRISES.items():
        row['c_' + k] = L.seg_ret(c, s, e)
    for cs in COSTS:
        cc, _, _ = L.run(D, ladder, cost=cs)
        row[f'cost{int(cs*10000)}'] = float(cc.iloc[-1])
    return row


rows = [evaluate('기존 -16/-11', 'BASE', L.BASE_LADDER, 'exit=-0.11')]

# ---------------- A. 단순 낙폭 복귀선
for x in [round(-0.04 - 0.005 * i, 3) for i in range(24)]:
    rows.append(evaluate(f'A exit {x*100:.1f}%', 'A', [(('dd', x), 1.0, 0)], f'exit={x}'))

# ---------------- B. 낙폭 회복 속도 (ddrec = dd_t - dd_{t-k})
for k, x in itertools.product((5, 10, 20, 60), (0.02, 0.03, 0.04, 0.05, 0.07, 0.10, 0.13)):
    cond = F[f'ddrec{k}'] >= x
    rows.append(evaluate(f'B ddrec{k}>={x*100:.0f}pp OR', 'B_or',
                         [(('dd', L.EXIT), 1.0, 0), (cond, 1.0, 0)], f'k={k},x={x}'))
    rows.append(evaluate(f'B ddrec{k}>={x*100:.0f}pp ONLY', 'B_only', [(cond, 1.0, 0)], f'k={k},x={x}'))

# ---------------- C. 최근 저점 대비 반등률
for k, x in itertools.product((5, 10, 20, 30, 60),
                              (0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15, 0.20)):
    cond = F[f'reb{k}'] >= x
    rows.append(evaluate(f'C reb{k}>=+{x*100:.0f}% OR', 'C_or',
                         [(('dd', L.EXIT), 1.0, 0), (cond, 1.0, 0)], f'k={k},x={x}'))
    rows.append(evaluate(f'C reb{k}>=+{x*100:.0f}% ONLY', 'C_only', [(cond, 1.0, 0)], f'k={k},x={x}'))

# ---------------- D. 단기 수익률 급반등
for k, x in itertools.product((3, 5, 10, 20), (0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.20)):
    cond = F[f'ret{k}'] >= x
    rows.append(evaluate(f'D ret{k}>=+{x*100:.0f}% OR', 'D_or',
                         [(('dd', L.EXIT), 1.0, 0), (cond, 1.0, 0)], f'k={k},x={x}'))
    rows.append(evaluate(f'D ret{k}>=+{x*100:.0f}% ONLY', 'D_only', [(cond, 1.0, 0)], f'k={k},x={x}'))

# ---------------- F. 이동평균 기울기/방향 (복귀 확인용, 단독)
for tag, cond in (('ma20up', F['ma20up']), ('ma20slope', F['ma20slope']),
                  ('ma50slope', F['ma50slope'])):
    rows.append(evaluate(f'F {tag} OR', 'F_or', [(('dd', L.EXIT), 1.0, 0), (cond, 1.0, 0)], tag))

# ---------------- G. 시간 + 반등 (노이즈 반등 억제)
for k, x, mind in itertools.product((10, 20), (0.03, 0.05, 0.07), (3, 5, 10, 20)):
    cond = F[f'reb{k}'] >= x
    rows.append(evaluate(f'G reb{k}>=+{x*100:.0f}% & {mind}일경과 OR', 'G_or',
                         [(('dd', L.EXIT), 1.0, 0), (cond, 1.0, mind)], f'k={k},x={x},min={mind}'))

# ---------------- H. 단계적 복귀
def stage(nm, spec):
    rows.append(evaluate(nm, 'H', spec[0], spec[1]))

for x1, x2 in [(0.03, 0.07), (0.04, 0.08), (0.05, 0.10), (0.03, 0.10), (0.05, 0.08)]:
    stage(f'H2 reb20 +{x1*100:.0f}%->50% / +{x2*100:.0f}%->100%',
          ([(F['reb20'] >= x1, 0.5, 0), (F['reb20'] >= x2, 1.0, 0), (('dd', L.EXIT), 1.0, 0)],
           f'reb20 {x1}/{x2}'))
for x1, x2, x3 in [(0.03, 0.06, 0.10), (0.04, 0.08, 0.12), (0.02, 0.05, 0.08)]:
    stage(f'H3 reb20 +{x1*100:.0f}/{x2*100:.0f}/{x3*100:.0f}% -> 33/67/100%',
          ([(F['reb20'] >= x1, 1/3, 0), (F['reb20'] >= x2, 2/3, 0), (F['reb20'] >= x3, 1.0, 0),
            (('dd', L.EXIT), 1.0, 0)], f'reb20 {x1}/{x2}/{x3}'))
for d1, d2 in [(-0.14, -0.11), (-0.13, -0.10), (-0.15, -0.11), (-0.13, -0.08)]:
    stage(f'H2 dd {d1*100:.0f}%->50% / {d2*100:.0f}%->100%',
          ([(('dd', d1), 0.5, 0), (('dd', d2), 1.0, 0)], f'dd {d1}/{d2}'))
for d1, d2, d3 in [(-0.14, -0.12, -0.09), (-0.15, -0.13, -0.11), (-0.14, -0.11, -0.08)]:
    stage(f'H3 dd {d1*100:.0f}/{d2*100:.0f}/{d3*100:.0f}% -> 33/67/100%',
          ([(('dd', d1), 1/3, 0), (('dd', d2), 2/3, 0), (('dd', d3), 1.0, 0)], f'dd {d1}/{d2}/{d3}'))
# 혼합: 반등률로 절반, 낙폭선으로 전량
for x1 in (0.03, 0.05, 0.07):
    stage(f'H2 mix reb20+{x1*100:.0f}%->50% / dd>-11%->100%',
          ([(F['reb20'] >= x1, 0.5, 0), (('dd', L.EXIT), 1.0, 0)], f'reb20 {x1} + dd-0.11'))
for x1 in (0.03, 0.05, 0.07):
    stage(f'H2 mix ddrec20>={x1*100:.0f}pp->50% / dd>-11%->100%',
          ([(F['ddrec20'] >= x1, 0.5, 0), (('dd', L.EXIT), 1.0, 0)], f'ddrec20 {x1} + dd-0.11'))

df = pd.DataFrame(rows)
df.to_csv('reentry_results.csv', index=False, encoding='utf-8-sig')
b = df.iloc[0]
print(f"후보 {len(df)-1}개 + 기준선 1개 계산 완료 -> reentry_results.csv")
print(f"BASE: {b.final:.1f}x CAGR {b.cagr:.2f}% MDD {b.mdd:.2f}% 3y {b.qld3:.1f}% 5y {b.qld5:.1f}%")

# 1차 관문: 기준선 대비 3년/5년 QLD 승률 개선 + CAGR 훼손 없음 + MDD -60% 이내
cand = df[(df.qld3 > b.qld3) & (df.qld5 > b.qld5) & (df.cagr >= b.cagr - 0.5) & (df.mdd > -60)]
print(f"\n1차 관문(3y·5y 승률 모두 개선 & CAGR>=기준-0.5%p & MDD>-60%) 통과: {len(cand)}개")
cols = ['name', 'final', 'cagr', 'mdd', 'chg', 'qld3', 'qld5', 'qld10', 'qld15', 'cost50']
with pd.option_context('display.width', 200, 'display.max_columns', 30):
    print(cand.sort_values('final', ascending=False)[cols].head(25).to_string(index=False))
