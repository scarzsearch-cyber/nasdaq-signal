# -*- coding: utf-8 -*-
"""
관문(b) 재검증: 확장 데이터(1972-2026) 연속상태 Walk-Forward.
Train 에서 '복귀선'만 고르고(밴드 0~10%p), 상태 w 는 전 구간 연속.
비교: WFA선택  vs  고정 A(-11%)  vs  고정 B(-16%)
"""
import numpy as np, pandas as pd
import hist_data as H

D = H.build_ext()
IDX, ddv, qldr, schdr = D['idx'], D['ddv'], D['qldr'], D['schdr']
N = len(IDX); ENTER, COST, EMBARGO = -0.16, 0.001, 20
GRID = [round(-0.16 + 0.01 * i, 3) for i in range(11)]      # -16% ~ -6%


def path(exitline, lo, hi, w0=1.0, cost=COST):
    w = np.empty(hi - lo); cur = w0
    for j, i in enumerate(range(lo, hi)):
        d = ddv[i]
        if cur >= 1.0:
            if d <= ENTER: cur = 0.0
        else:
            cur = 0.0 if d <= ENTER else (1.0 if d > exitline else cur)
        w[j] = cur
    pos = np.empty_like(w); pos[0] = w0; pos[1:] = w[:-1]
    r = np.nan_to_num(pos * qldr[lo:hi] + (1 - pos) * schdr[lo:hi]); r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=w0))
    return np.cumprod((1 + r) * (1 - cost * turn)), cur


def wfa(train_y=5, test_y=1):
    tr, te = train_y * 252, test_y * 252
    s = tr; rows = []
    w0 = {'wfa': 1.0, 'A': 1.0, 'B': 1.0}
    eq = {'wfa': 1.0, 'A': 1.0, 'B': 1.0}
    while s + te <= N:
        lo, hi = max(0, s - tr), s - EMBARGO
        best, bp = -1, None
        for p in GRID:
            c, _ = path(p, lo, hi)
            if c[-1] > best: best, bp = c[-1], p
        row = dict(test시작=str(IDX[s].date()), test종료=str(IDX[s + te - 1].date()), 선택복귀선=bp * 100)
        for k, p in [('wfa', bp), ('A', -0.11), ('B', -0.16)]:
            c, wn = path(p, s, s + te, w0=w0[k])
            eq[k] *= c[-1]; w0[k] = wn
            row[k + '수익'] = (c[-1] - 1) * 100
        rows.append(row); s += te
    t = pd.DataFrame(rows)
    t['wfa>A'] = t['wfa수익'] > t['A수익']; t['B>A'] = t['B수익'] > t['A수익']
    return t, eq


for ty in (1, 2):
    t, eq = wfa(test_y=ty)
    print('\n===== Walk-Forward  Train 5y -> Test %dy   (n=%d 구간) =====' % (ty, len(t)))
    print('OOS 누적: WFA %.1f배   A(-16/-11) %.1f배   B(-16/-16) %.1f배'
          % (eq['wfa'], eq['A'], eq['B']))
    print('B가 A를 이긴 Test 구간: %d/%d (%.0f%%)' % (t['B>A'].sum(), len(t), t['B>A'].mean() * 100))
    print('WFA가 A를 이긴 Test 구간: %d/%d' % (t['wfa>A'].sum(), len(t)))
    vc = t['선택복귀선'].round(0).value_counts().sort_index()
    print('Train이 고른 복귀선 분포:', ' '.join('%.0f%%:%d' % (k, v) for k, v in vc.items()))
    print('  -16%% 선택 비율: %.0f%%' % ((t['선택복귀선'].round(0) == -16).mean() * 100))
    if ty == 1:
        t.to_csv('hyst_wfa.csv', index=False, encoding='utf-8-sig')
        print(t.to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
