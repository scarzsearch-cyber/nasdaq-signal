# -*- coding: utf-8 -*-
"""[공유용 변형 — 최종 후보 확정 점검] share_variant_threshold_scan.py 부속.
-16 문턱이 고원임을 확인한 뒤, S6Q4·S5Q5@-16 두 후보에서 방어자산만 재비교."""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
import numpy as np
import pandas as pd
import hist_defensive as DF
import hist_defasset as DA
import eng_common as EC

D = dict(DF.build('chain'))
idx = D['idx']
px = pd.Series(D['px'], index=idx)
r_qqq1x = np.nan_to_num(px.pct_change().values)
r_div = np.asarray(D['schdr'], float)
r_ust5 = np.nan_to_num(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE))
r_gold = np.nan_to_num(DA.gold_r(idx))

DEF_CANDS = {'국채100': dict(ust5=1.0), '국채70/금30': dict(ust5=.7, gold=.3),
             '국채60/금40': dict(ust5=.6, gold=.4), '국채50/금50': dict(ust5=.5, gold=.5)}

for s, q in [(6, 4), (5, 5)]:
    r_atk = DA.mix_monthly_parts(idx, dict(div=s/10, qqq=q/10), dict(div=r_div, qqq=r_qqq1x))
    w = EC.rule_dd(px, -0.16, -0.16)
    print(f'\nS{s}Q{q}@-16 방어자산 비교')
    print(f"{'방어':<14}{'Calmar':>8}{'p05_20y':>9}{'최종배수':>10}{'CAGR%':>7}{'MDD%':>7}")
    for name, w0 in DEF_CANDS.items():
        r_def = DA.mix_monthly_parts(idx, w0, dict(ust5=r_ust5, gold=r_gold))
        c = EC.sim2(w, r_atk, r_def)
        m = EC.fullmet(c, idx=idx)
        p05 = EC.p05_20y(c)
        print(f"{name:<14}{m['calmar']:>8.3f}{p05:>9.1f}{m['final']:>10.1f}{m['cagr']:>7.2f}{m['mdd']:>7.2f}")
