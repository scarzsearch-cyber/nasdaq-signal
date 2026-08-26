"""
후보 CD(N): 진입 dd <= -16% -> SCHD.  복귀: SCHD 진입 후 N거래일 경과 & dd > -16% -> QLD
(= 히스테리시스(-11%)를 없애고 쿨다운으로 대체)
쿨다운 스윕 + 구간분해 + 지연/진입선 민감도.
"""
import numpy as np, pandas as pd
import reentry_lib as L

D = L.build(); QLD, QQQ = L.bench(D)
ALWAYS = np.ones(len(D['idx']), dtype=bool)


def cd(n, enter=L.ENTER):
    """쿨다운 n일 후보의 ladder"""
    return [(ALWAYS, 1.0, n)], enter


def stats(ladder, enter=L.ENTER, cost=L.COST, lag=1):
    c, w, t = L.run(D, ladder, enter=enter, cost=cost, lag=lag)
    m = L.met(c); rq = L.rolling_stats(c, QLD); rn = L.rolling_stats(c, QQQ)
    chg = int((np.abs(np.diff(w.values, prepend=w.values[0])) > 1e-9).sum())
    return c, w, m, rq, rn, chg


print('%-22s %8s %6s %7s %5s %6s %6s %6s %6s %6s' %
      ('rule', 'final', 'CAGR', 'MDD', 'sw', '1y', '3y', '5y', '10y', '15y'))
def line(nm, ladder, enter=L.ENTER):
    c, w, m, rq, rn, chg = stats(ladder, enter)
    print('%-22s %8.1f %6.2f %7.2f %5d %6.1f %6.1f %6.1f %6.1f %6.1f' %
          (nm, m['final'], m['cagr']*100, m['mdd']*100, chg,
           rq[1]['win'], rq[3]['win'], rq[5]['win'], rq[10]['win'], rq[15]['win']))
    return c, w, m, chg

base_c, base_w, base_m, base_chg = line('BASE -16/-11', L.BASE_LADDER)
res = {}
for n in range(0, 31):
    c, w, m, chg = line(f'CD({n})', [(ALWAYS, 1.0, n)])
    res[n] = (c, w, m, chg)

print('\n=== 10년 단위 구간 수익 (%) : 특정 사건 의존 확인 ===')
segs = [('2000-2003', '2000-01-01', '2003-12-31'), ('2004-2007', '2004-01-01', '2007-12-31'),
        ('2008-2012', '2008-01-01', '2012-12-31'), ('2013-2019', '2013-01-01', '2019-12-31'),
        ('2020-2022', '2020-01-01', '2022-12-31'), ('2023-2026', '2023-01-01', '2026-08-24')]
print('%-12s %10s %10s %10s %10s' % ('구간', 'BASE', 'CD(8)', 'CD(10)', 'CD(13)'))
for nm, s, e in segs:
    print('%-12s %9.1f%% %9.1f%% %9.1f%% %9.1f%%' % (nm, L.seg_ret(base_c, s, e),
          L.seg_ret(res[8][0], s, e), L.seg_ret(res[10][0], s, e), L.seg_ret(res[13][0], s, e)))

print('\n=== 위기 구간 (%) ===')
print('%-20s %10s %10s %10s' % ('구간', 'BASE', 'CD(10)', 'QLD보유'))
qldc = QLD
for k, (s, e) in L.CRISES.items():
    print('%-20s %9.1f%% %9.1f%% %9.1f%%' % (k, L.seg_ret(base_c, s, e), L.seg_ret(res[10][0], s, e), L.seg_ret(qldc, s, e)))

print('\n=== 체결지연 민감도 (최종배수) ===')
print('%-8s %10s %10s' % ('지연', 'BASE', 'CD(10)'))
for lag in (1, 2, 3, 5):
    a = stats(L.BASE_LADDER, lag=lag)[2]['final']; b = stats([(ALWAYS, 1.0, 10)], lag=lag)[2]['final']
    print('%-8s %10.1f %10.1f' % (f'{lag}일', a, b))

print('\n=== 거래비용 민감도 (최종배수) ===')
print('%-8s %10s %10s %10s' % ('편도', 'BASE', 'CD(10)', 'CD(13)'))
for cs in (0.0005, 0.001, 0.002, 0.003, 0.005, 0.01):
    a = stats(L.BASE_LADDER, cost=cs)[2]['final']
    b = stats([(ALWAYS, 1.0, 10)], cost=cs)[2]['final']
    d = stats([(ALWAYS, 1.0, 13)], cost=cs)[2]['final']
    print('%-8s %10.1f %10.1f %10.1f' % (f'{cs*100:.2f}%', a, b, d))

print('\n=== 진입선 이동에 대한 견고성 (CD(10) vs 해당 진입선의 -5%p 히스테리시스) ===')
print('%-8s %12s %12s' % ('진입선', 'CD(10)', 'hyst +5%p'))
for en in (-0.13, -0.14, -0.15, -0.16, -0.17, -0.18, -0.20):
    a = stats([(ALWAYS, 1.0, 10)], enter=en)[2]['final']
    b = stats([(('dd', round(en+0.05, 3)), 1.0, 0)], enter=en)[2]['final']
    print('%-8s %12.1f %12.1f' % (f'{en*100:.0f}%', a, b))

# 전환 이력 비교
def events(w):
    v = w.values; out = []
    for i in range(1, len(v)):
        if abs(v[i]-v[i-1]) > 1e-9:
            out.append((w.index[i].date(), 'QLD' if v[i] > 0.5 else 'SCHD'))
    return out
print('\n=== CD(10) 전환 이력 (%d회) ===' % len(events(res[10][1])))
ev = events(res[10][1])
for i in range(0, len(ev), 2):
    a = ev[i]; b = ev[i+1] if i+1 < len(ev) else None
    print('  %s -> SCHD   %s' % (a[0], ('%s -> QLD (%d일)' % (b[0], (pd.Timestamp(b[0])-pd.Timestamp(a[0])).days)) if b else ''))
