# -*- coding: utf-8 -*-
"""[공유용 변형 — 확정안 재계산] 방어를 국채60/금40 -> 국채70/금30으로 교체해
switched 지표·월별곡선을 다시 뽑는다(static은 방어 무관이라 그대로).
share_variant_threshold_scan.py 의 고원검증 결과로 확정된 안:
  공격 S6Q4(배당다우존스60/나스닥100비레버리지40) · 방어 국채70/금30 · 신호 -16/-16
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
import sys
import json
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_defensive as DF
import hist_defasset as DA
import eng_common as EC

D = dict(DF.build('chain'))
idx = D['idx']
px = pd.Series(D['px'], index=idx)
n = len(idx)
r_qqq1x = np.nan_to_num(px.pct_change().values)
r_div = np.asarray(D['schdr'], float)
r_ust5 = np.nan_to_num(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE))
r_gold = np.nan_to_num(DA.gold_r(idx))
r_def = DA.mix_monthly_parts(idx, dict(ust5=0.70, gold=0.30), dict(ust5=r_ust5, gold=r_gold))
w = EC.rule_dd(px, -0.16, -0.16)

RATIOS = [(9, 1), (8, 2), (7, 3), (6, 4), (5, 5), (4, 6), (3, 7), (2, 8), (1, 9)]


def month_snapshot(curve):
    s = pd.Series(np.arange(n), index=idx)
    per = idx.to_period('M')
    first_pos = s.groupby(per).first()
    return curve[first_pos.values]


def main():
    EC.selfcheck()
    print('\nSWITCHED (방어 국채70/금30, 신호 -16/-16):')
    out_monthly = {}
    for s, q in RATIOS:
        r_atk = DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10), dict(div=r_div, qqq=r_qqq1x))
        c_switch = EC.sim2(w, r_atk, r_def)
        m = EC.fullmet(c_switch, idx=idx)
        turns = int(np.sum(np.abs(np.diff(w))))
        label = f'S{s}Q{q}'
        print(f"{{label:\"{label}\", s:{s}, q:{q}, final:{m['final']:.2f}, cagr:{m['cagr']:.2f}, "
              f"mdd:{m['mdd']:.2f}, calmar:{m['calmar']:.3f}, turns:{turns}}},")
        ms = month_snapshot(c_switch)
        out_monthly[label] = [round(float(v), 5) for v in ms]

    with open('공유용_별도전략/_switched_monthly_70_30.json', 'w', encoding='utf-8') as f:
        json.dump(out_monthly, f, ensure_ascii=False, separators=(',', ':'))
    print('\n[저장] 공유용_별도전략/_switched_monthly_70_30.json')


if __name__ == '__main__':
    main()
