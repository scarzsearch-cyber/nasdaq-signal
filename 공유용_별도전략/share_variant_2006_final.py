# -*- coding: utf-8 -*-
"""
[공유용 변형 — 2006~2026 · 5비율(S8Q2~S4Q6) 확정판, 2026-09-01]
소유자 지시: ① SCHD/QQQ 사이 후보를 S8Q2·S7Q3·S6Q4·S5Q5·S4Q6 5개로만 제한
             ② 데이터 구간을 1972~2026(54년 체인) 대신 2006~2026(20년)으로.
신호 전환은 이미 제거됨(순수 매수보유 배합 탐색기) — 이 스크립트도 static만 낸다.

실행: python research/share_variant_2006_final.py
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

import hist_defensive as DF                                # noqa: E402
import hist_defasset as DA                                 # noqa: E402
import eng_common as EC                                     # noqa: E402

START = '2006-01-01'
D = dict(DF.build('chain', start=START))
idx = D['idx']
px = pd.Series(D['px'], index=idx)
n = len(idx)
print(f'데이터 구간 실측: {idx[0].date()} ~ {idx[-1].date()}  ({n}거래일)')

r_qqq1x = np.nan_to_num(px.pct_change().values)
r_div = np.asarray(D['schdr'], float)

RATIOS = [(8, 2), (7, 3), (6, 4), (5, 5), (4, 6)]


def blend(s, q):
    return DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10), dict(div=r_div, qqq=r_qqq1x))


def vol_ann(r):
    return float(np.std(r) * np.sqrt(252) * 100)


def month_snapshot(curve):
    s = pd.Series(np.arange(n), index=idx)
    per = idx.to_period('M')
    first_pos = s.groupby(per).first()
    dates = [str(p) for p in first_pos.index]
    return dates, curve[first_pos.values]


def main():
    EC.selfcheck()
    rows = []
    print('\n[정적 매수보유] 2006~2026')
    print(f"{'라벨':<8}{'CAGR%':>8}{'변동성%':>9}{'MDD%':>8}{'최종배수':>12}{'Calmar':>8}")
    monthly = {}
    dates_ref = None
    for s, q in [(10, 0)] + RATIOS + [(0, 10)]:
        r = r_div if q == 0 else (r_qqq1x if s == 0 else blend(s, q))
        c = np.cumprod(1 + r)
        m = EC.fullmet(c, idx=idx)
        v = vol_ann(r)
        label = 'SCHD' if q == 0 else ('QQQ' if s == 0 else f'S{s}Q{q}')
        print(f"{label:<8}{m['cagr']:>8.2f}{v:>9.2f}{m['mdd']:>8.2f}{m['final']:>12.2f}{m['calmar']:>8.3f}")
        rows.append(dict(label=label, s=s, q=q, cagr=round(m['cagr'], 3), vol=round(v, 3),
                          mdd=round(m['mdd'], 3), final=round(m['final'], 2), calmar=round(m['calmar'], 4)))
        if label not in ('SCHD', 'QQQ'):
            dates, ms = month_snapshot(c)
            if dates_ref is None:
                dates_ref = dates
            monthly[label] = [round(float(x), 5) for x in ms]

    out = dict(static=rows, monthly=dict(dates=dates_ref, ratios=monthly),
               data_from=str(idx[0].date()), data_to=str(idx[-1].date()))
    with open('공유용_별도전략/_2006_final_out.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('\n[저장] 공유용_별도전략/_2006_final_out.json')


if __name__ == '__main__':
    main()
