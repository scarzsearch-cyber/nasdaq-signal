"""
연속상태 Walk-Forward.  파라미터는 Train에서만 고르고, 상태(w)는 전 구간 연속.
비교: (1) 히스테리시스 계열(복귀선 그리드)  (2) 쿨다운 계열 CD(N)  (3) 고정 -16/-11  (4) 고정 CD(10)
출력: reentry_wfa.csv
"""
import numpy as np, pandas as pd, sys
import reentry_lib as L

D = L.build(); QLD, QQQ = L.bench(D)
IDX, ddv, qldr, schdr = D['idx'], D['ddv'], D['qldr'], D['schdr']
N = len(IDX)
EMBARGO = 20

EXIT_GRID = [round(-0.04 - 0.005 * i, 3) for i in range(25)]   # -4% ~ -16%
CD_GRID = list(range(0, 26))


def path(kind, param_per_day, lo, hi, w0=1.0, days0=0, cost=L.COST):
    """param_per_day: 길이 N 배열. kind='hyst'면 복귀 낙폭선, 'cd'면 쿨다운일수."""
    w = np.empty(hi - lo); cur, days = w0, days0
    for j, i in enumerate(range(lo, hi)):
        d = ddv[i]
        if cur >= 1.0:
            if d <= L.ENTER:
                cur, days = 0.0, 0
        else:
            days += 1
            if d <= L.ENTER:
                cur = 0.0
            elif (d > param_per_day[i]) if kind == 'hyst' else (days >= param_per_day[i]):
                cur = 1.0
        w[j] = cur
    pos = np.empty_like(w); pos[0] = w0; pos[1:] = w[:-1]
    r = pos * qldr[lo:hi] + (1 - pos) * schdr[lo:hi]
    r = np.nan_to_num(r); r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=w0))
    g = (1 + r) * (1 - cost * turn)
    return np.cumprod(g), w, cur, days


def train_pick(kind, grid, lo, hi):
    best, bp = -1, None
    for p in grid:
        arr = np.full(N, p, dtype=float)
        c, _, _, _ = path(kind, arr, lo, hi)
        if c[-1] > best:
            best, bp = c[-1], p
    return bp, best


def wfa(kind, grid, train_y=5, test_y=1):
    tr, te = train_y * 252, test_y * 252
    start = tr
    rows, w0, days0, eq = [], 1.0, 0, 1.0
    curve_idx, curve_val = [], []
    while start + te <= N:
        lo_tr, hi_tr = max(0, start - tr), start - EMBARGO
        p, _ = train_pick(kind, grid, lo_tr, hi_tr)
        arr = np.full(N, p, dtype=float)
        c, w, w0n, d0n = path(kind, arr, start, start + te, w0=w0, days0=days0)
        rows.append(dict(kind=kind, test_start=str(IDX[start].date()), test_end=str(IDX[start+te-1].date()),
                         param=p, test_ret=(c[-1] - 1) * 100))
        curve_idx.extend(IDX[start:start+te]); curve_val.extend(list(eq * c))
        eq *= c[-1]; w0, days0 = w0n, d0n
        start += te
    return pd.DataFrame(rows), pd.Series(curve_val, index=pd.DatetimeIndex(curve_idx))


def fixed_curve(kind, p, lo, hi):
    arr = np.full(N, p, dtype=float)
    c, _, _, _ = path(kind, arr, lo, hi)
    return pd.Series(c, index=IDX[lo:hi])


out = []
for test_y in (1, 2):
    print(f'\n===== Train 5년 -> Test {test_y}년 (연속상태, embargo {EMBARGO}일) =====')
    dfh, ch = wfa('hyst', EXIT_GRID, 5, test_y)
    dfc, cc = wfa('cd', CD_GRID, 5, test_y)
    lo = IDX.searchsorted(ch.index[0]); hi = lo + len(ch)
    fb = fixed_curve('hyst', L.EXIT, lo, hi)          # 고정 -16/-11
    f10 = fixed_curve('cd', 10, lo, hi)               # 고정 CD(10)
    f13 = fixed_curve('cd', 13, lo, hi)
    ql = QLD.iloc[lo:hi] / QLD.iloc[lo]
    print(f'  OOS 구간 {ch.index[0].date()} ~ {ch.index[-1].date()}  ({len(ch)}일)')
    for nm, c in (('WFA 히스테리시스', ch), ('WFA 쿨다운', cc), ('고정 -16/-11', fb),
                  ('고정 CD(10)', f10), ('고정 CD(13)', f13), ('QLD 계속보유', ql)):
        m = L.met(c)
        print('  %-16s 배수 %7.2f  CAGR %6.2f%%  MDD %7.2f%%' % (nm, c.iloc[-1], m['cagr']*100, m['mdd']*100))
    dfh['test_y'] = test_y; dfc['test_y'] = test_y
    out += [dfh, dfc]
    # Test별 승패
    j = dfh.merge(dfc, on='test_start', suffixes=('_h', '_c'))
    print('\n  %-12s %8s %8s %8s %8s' % ('Test시작', 'H파라미터', 'H수익', 'C쿨다운', 'C수익'))
    for _, r in j.iterrows():
        print('  %-12s %8.3f %7.1f%% %8d %7.1f%%' % (r.test_start, r.param_h, r.test_ret_h, r.param_c, r.test_ret_c))
    print('  쿨다운계열이 Test에서 이긴 횟수: %d / %d' % ((j.test_ret_c > j.test_ret_h).sum(), len(j)))

pd.concat(out).to_csv('reentry_wfa.csv', index=False, encoding='utf-8-sig')
print('\n-> reentry_wfa.csv')
