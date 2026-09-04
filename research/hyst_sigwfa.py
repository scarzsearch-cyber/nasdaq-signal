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
try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
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


def path(dd, en, ex, lo, hi, w0=1.0, prev_pos=None, return_position=False):
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
    t = np.abs(np.diff(pos, prepend=w0 if prev_pos is None else prev_pos))
    result = (np.cumprod((1 + r) * (1 - COST * t)), cur)
    return (*result, pos[-1]) if return_position else result


def state_before(dd, en, ex, lo):
    """학습창 전까지의 신호 상태를 유지한다. 각 창을 공격 상태로 재설정하지 않는다."""
    cur = 1.0
    for d in dd[:lo]:
        if cur >= 1.0:
            if d <= en: cur = 0.0
        else:
            cur = 0.0 if d <= en else (1.0 if d > ex else cur)
    return cur


def calmar(c):
    # HANDOFF §2: 학습 목적함수는 최종금액이 아니라 Calmar다.
    c = np.asarray(c, float)
    initial = np.r_[1.0, c]
    mdd = np.min(initial / np.maximum.accumulate(initial) - 1)
    cagr = c[-1] ** (252 / len(c)) - 1
    return cagr / abs(mdd) if mdd < -1e-12 else float('inf')


def wfa(fam, dd, start_i, test_y=1, train_y=5):
    tr, te = train_y * 252, test_y * 252
    st = max(tr, start_i); eq = 1.0; w0 = 1.0; rets = []; picks = []
    held = w0
    test_lo = st
    while st + te <= N:
        lo, hi = max(0, st - tr), st - EMB
        best, bp = -np.inf, None
        for p in fam:
            c, _ = path(dd, p[0], p[1], lo, hi,
                        w0=state_before(dd, *p, lo),
                        prev_pos=state_before(dd, *p, max(0, lo - 1)))
            score = calmar(c)
            if score > best: best, bp = score, p
        c, w0, held = path(dd, bp[0], bp[1], st, st + te, w0=w0,
                           prev_pos=held, return_position=True)
        eq *= c[-1]; rets.append(c[-1] - 1); picks.append(bp); st += te
    a = np.array(rets)
    return dict(구간수=len(a), OOS누적=eq, OOS_CAGR=(eq ** (1 / (len(a) * test_y)) - 1) * 100,
                중앙수익=np.median(a) * 100, 최악구간=a.min() * 100,
                양수구간=f'{(a>0).sum()}/{len(a)}',
                선택다양성=len(set(picks)), 최빈선택=max(set(picks), key=picks.count),
                _lo=test_lo, _hi=st)


for lab, si in [('전구간 1972-2026 (합성 QLD 63% 포함)', 0),
                ('실물 QLD 구간 2006-06-22~', int(idx.searchsorted(pd.Timestamp('2006-06-22'))))]:
    rows = []
    for nm, fam in FAM.items():
        dd = DDQ if nm == 'QQQ신호' else DDL
        r = wfa(fam, dd, si); r = dict(계열=nm, **r); rows.append(r)
    # 고정 현행 B를 WFA가 실제로 시험한 동일 시작·종료점에 맞춰 대조한다.
    lo, hi = rows[0]['_lo'], rows[0]['_hi']
    c, _ = path(DDQ, -0.16, -0.16, lo, hi)
    endpoints = np.r_[1.0, c[251::252]]
    fixed_rets = endpoints[1:] / endpoints[:-1] - 1
    rows.append(dict(계열='고정 전략 B QQQ -16/-16', 구간수=len(fixed_rets), OOS누적=c[-1],
                     OOS_CAGR=(c[-1] ** (252 / (hi - lo)) - 1) * 100,
                     중앙수익=np.median(fixed_rets) * 100, 최악구간=fixed_rets.min() * 100,
                     양수구간=f'{(fixed_rets > 0).sum()}/{len(fixed_rets)}',
                     선택다양성=1, 최빈선택=(-0.16, -0.16)))
    for r in rows:
        r.pop('_lo', None); r.pop('_hi', None)
    print('\n===== %s  (Train 5y Calmar -> Test 1y) =====' % lab)
    print('실제 평가: %s ~ %s' % (idx[lo].date(), idx[hi - 1].date()))
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
