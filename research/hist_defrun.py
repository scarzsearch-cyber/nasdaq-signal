# -*- coding: utf-8 -*-
"""
과제 ① + ④ 실행 — 방어자산 대체가 A(-16/-11) vs B(-16/-16) 판정을 뒤집는가?
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np, pandas as pd
from reentry_lib import run, met, rolling_stats
import hist_data as H, hist_defensive as DF
from hyst_core import A, B, switches

KINDS = [('연2% 고정현금 (기존 규약)', 'cash2'),
         ('3M T-bill 실측    (과제④)', 'tbill'),
         ('BE/ME Hi30 가치주  (과제①)', 'value'),
         ('D/P Hi30 배당주   (과제①+자율1)', 'div')]


def one(D, S, cost=0.001, start=None, end=None):
    c, w, t = run(D, S['ladder'], enter=S['enter'], cost=cost, start=start, end=end)
    m = met(c)
    return c, w, m, len(switches(w))


def table(start, end, label, cost=0.001):
    print('\n===== %s =====' % label)
    print('%-32s %-11s %12s %7s %8s %7s %7s' %
          ('방어자산', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar', '전환'))
    res = {}
    for nm, k in KINDS:
        D = DF.build(k)
        for S in (A, B):
            c, w, m, sw = one(D, S, cost, start, end)
            res[(k, S['name'])] = m
            print('%-32s %-11s %12s %6.2f%% %7.2f%% %7.2f %7d' %
                  (nm if S is A else '', S['name'], f"{m['final']:,.1f}",
                   m['cagr'] * 100, m['mdd'] * 100, m['calmar'], sw))
        ra = res[(k, A['name'])]; rb = res[(k, B['name'])]
        print('%-32s %-11s   B/A 배수비 %.3f   CAGR차 %+.2f%%p   MDD차 %+.2f%%p' %
              ('', '', rb['final'] / ra['final'],
               (rb['cagr'] - ra['cagr']) * 100, (rb['mdd'] - ra['mdd']) * 100))
    return res


def flight_compare(start, end, label, cost=0.001):
    """과제④ 본론: '주식형 방어자산(SCHD)' vs '순수 현금 피신' 직접 비교."""
    print('\n===== %s : SCHD 피신 vs 현금 피신 =====' % label)
    print('%-34s %-11s %12s %7s %8s %7s' % ('피신처', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar'))
    for nm, k in [('순수 현금(연2%) 전구간', 'pure_cash2'),
                  ('순수 T-bill 전구간', 'pure_tbill'),
                  ('SCHD계열(D/P대리+실물) 전구간', 'div'),
                  ('SCHD실물+그이전 T-bill', 'tbill')]:
        D = DF.build(k)
        for S in (A, B):
            c, w, m, sw = one(D, S, cost, start, end)
            print('%-34s %-11s %12s %6.2f%% %7.2f%% %7.2f' %
                  (nm if S is A else '', S['name'], f"{m['final']:,.1f}",
                   m['cagr'] * 100, m['mdd'] * 100, m['calmar']))


def defense_pnl(kind, start=None, end=None):
    """방어자산에 머무는 동안 실제로 얼마를 벌었나 (위기별)."""
    D = DF.build(kind)
    idx = D['idx']
    c, w, t = run(D, A['ladder'], enter=A['enter'], cost=0.001, start=start, end=end)
    pos = w.shift(1).fillna(1.0)
    sr = pd.Series(D['schdr'], index=idx).reindex(w.index)
    qr = pd.Series(D['qldr'], index=idx).reindex(w.index)
    inD = pos < 0.5
    return dict(days=int(inD.sum()),
                defret=float(np.prod(1 + sr[inD]) - 1),
                qldret=float(np.prod(1 + qr[inD]) - 1),
                ann=float((np.prod(1 + sr[inD])) ** (252 / max(int(inD.sum()), 1)) - 1))


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    table(None, None, '전구간 1972-02 ~ 2026-08 (54.5년)')
    table('2000-01-03', None, '기준구간 2000-01 ~ 2026-08 (26.6년)')
    table(None, '1999-12-31', '신규구간 1972-02 ~ 1999-12 (27.9년)')
    flight_compare('2000-01-03', None, '2000-2026')
    flight_compare(None, None, '1972-2026')

    print('\n===== A(-16/-11)가 방어자산에 머문 기간의 실제 수익 =====')
    for nm, k in KINDS + [('순수 T-bill', 'pure_tbill')]:
        for lab, st, en in [('1972-2026', None, None), ('2000-2026', '2000-01-03', None),
                            ('2000-2003', '2000-01-03', '2003-12-31')]:
            r = defense_pnl(k, st, en)
            print('%-32s %-10s 방어일수 %5d  방어자산 %+8.1f%% (연%+6.2f%%)  같은기간 QLD %+9.1f%%'
                  % (nm if lab == '1972-2026' else '', lab, r['days'],
                     r['defret'] * 100, r['ann'] * 100, r['qldret'] * 100))
