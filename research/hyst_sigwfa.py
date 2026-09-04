# -*- coding: utf-8 -*-
"""제미나이.md §3: QQQ 신호 계열 vs QLD 신호 계열 OOS 재현성 (연속상태 WFA)"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np, pandas as pd
import hist_data as H
pd.set_option('display.width', 240)

D = H.build_ext(); idx = D['idx']
qldr, schdr = D['qldr'], D['schdr']
qld_lv = np.cumprod(1 + qldr)
s = pd.Series(qld_lv, index=idx)
DDQ = D['ddv']
DDL = (s / s.rolling(252, min_periods=252).max() - 1).fillna(0).values
N = len(idx); COST, EMB = 0.001, 20

# 사전 지정 후보 (대규모 Grid 금지 규약 준수)
FAM = {'QQQ신호': [(-0.16, -0.11), (-0.16, -0.15), (-0.16, -0.16)],
       'QLD신호': [(-0.25, -0.25), (-0.25, -0.15), (-0.30, -0.30),
                  (-0.30, -0.20), (-0.35, -0.35), (-0.35, -0.25)]}


def path(dd, en, ex, lo, hi, w0=1.0):
    w = np.empty(hi - lo); cur = w0
    for j, i in enumerate(range(lo, hi)):
        d = dd[i]
        if cur >= 1.0:
            if d <= en: cur = 0.0
        else:
            cur = 0.0 if d <= en else (1.0 if d > ex else cur)
        w[j] = cur
    pos = np.empty_like(w); pos[0] = w0; pos[1:] = w[:-1]
    # w0 는 구간 첫날 장 시작 전에 이미 보유한 상태이므로 첫날 수익도 포함한다.
    r = np.nan_to_num(pos * qldr[lo:hi] + (1 - pos) * schdr[lo:hi])
    t = np.abs(np.diff(pos, prepend=w0))
    return np.cumprod((1 + r) * (1 - COST * t)), cur


def wfa(fam, dd, start_i, test_y=1, train_y=5):
    tr, te = train_y * 252, test_y * 252
    st = max(tr, start_i); eq = 1.0; w0 = 1.0; rets = []; picks = []
    while st + te <= N:
        lo, hi = max(0, st - tr), st - EMB
        best, bp = -1, None
        for p in fam:
            c, _ = path(dd, p[0], p[1], lo, hi)
            if c[-1] > best: best, bp = c[-1], p
        c, w0 = path(dd, bp[0], bp[1], st, st + te, w0=w0)
        eq *= c[-1]; rets.append(c[-1] - 1); picks.append(bp); st += te
    a = np.array(rets)
    return dict(구간수=len(a), OOS누적=eq, OOS_CAGR=(eq ** (1 / (len(a) * test_y)) - 1) * 100,
                중앙수익=np.median(a) * 100, 최악구간=a.min() * 100,
                양수구간=f'{(a>0).sum()}/{len(a)}',
                선택다양성=len(set(picks)), 최빈선택=max(set(picks), key=picks.count))


for lab, si in [('전구간 1972-2026 (합성 QLD 63% 포함)', 0),
                ('실물 QLD 구간 2006-06-22~', int(idx.searchsorted(pd.Timestamp('2006-06-22'))))]:
    rows = []
    for nm, fam in FAM.items():
        dd = DDQ if nm == 'QQQ신호' else DDL
        r = wfa(fam, dd, si); r = dict(계열=nm, **r); rows.append(r)
    # 고정 현행안 대조
    lo = max(1260, si)
    c, _ = path(DDQ, -0.16, -0.11, lo, N)
    rows.append(dict(계열='고정 QQQ -16/-11', 구간수='-', OOS누적=c[-1],
                     OOS_CAGR=(c[-1] ** (252 / (N - lo)) - 1) * 100, 중앙수익=np.nan,
                     최악구간=np.nan, 양수구간='-', 선택다양성=0, 최빈선택='-'))
    print('\n===== %s  (Train 5y -> Test 1y) =====' % lab)
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
