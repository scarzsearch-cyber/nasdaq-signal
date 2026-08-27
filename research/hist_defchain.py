# -*- coding: utf-8 -*-
"""자율규약2 체인 적용 후 A vs B 재판정 + 과제④ 최종 비교"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np, pandas as pd
from reentry_lib import run, met
import hist_data as H, hist_defensive as DF
from hyst_core import A, B, switches

KINDS = [('연2% 고정현금 (기존 규약)', 'cash2'),
         ('3M T-bill 실측 (과제④)', 'tbill'),
         ('배당체인 D/P→DVY→SCHD (자율2)', 'chain'),
         ('배당체인 mix (DVY/VYM/SDY)', 'chainmix')]


def mdd_trace(c):
    dd = c / c.cummax() - 1; t = dd.idxmin(); p = c.loc[:t].idxmax()
    return p, t, float(dd.min())


def table(start, end, label, cost=0.001):
    print('\n===== %s =====' % label)
    print('%-30s %-11s %12s %7s %8s %7s %6s  %s' %
          ('방어자산', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar', '전환', 'MDD 시점'))
    out = {}
    for nm, k in KINDS:
        D = DF.build(k)
        for S in (A, B):
            c, w, t = run(D, S['ladder'], enter=S['enter'], cost=cost, start=start, end=end)
            m = met(c); p, tr, d = mdd_trace(c); out[(k, S['name'])] = m
            print('%-30s %-11s %12s %6.2f%% %7.2f%% %7.2f %6d  %s->%s' %
                  (nm if S is A else '', S['name'], f"{m['final']:,.1f}", m['cagr'] * 100,
                   m['mdd'] * 100, m['calmar'], len(switches(w)), p.date(), tr.date()))
        ra, rb = out[(k, A['name'])], out[(k, B['name'])]
        print('%-30s %-11s   B/A %.3f   CAGR차 %+.2f%%p   MDD차 %+.2f%%p'
              % ('', '', rb['final'] / ra['final'], (rb['cagr'] - ra['cagr']) * 100,
                 (rb['mdd'] - ra['mdd']) * 100))
    return out


if __name__ == '__main__':
    import hist_divetf as DE
    ch = DE.defensive_chain()
    print('방어자산 체인 CAGR 1972-2026 = %.2f%%   MDD = %.2f%%'
          % (((1 + ch).prod() ** (252 / len(ch)) - 1) * 100,
             ((1 + ch).cumprod() / (1 + ch).cumprod().cummax() - 1).min() * 100))
    table(None, None, '전구간 1972-02 ~ 2026-08')
    table('2000-01-03', None, '기준구간 2000-01 ~ 2026-08')
    table('2003-11-10', None, '방어자산 100% 실물 구간 2003-11 ~ 2026-08')
