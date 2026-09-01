# -*- coding: utf-8 -*-
"""
[공유용 변형 — 10/20/30년 다중 표본, 2026-09-01]
소유자 지적: 20년 단일 표본만 보여주면 "QQQ가 이겼다"는 게 확정된 결론처럼 읽혀
초보자가 오해한다(비중첩 창수 ≈1인 얇은 표본인데도). 해법: 손으로 유리한 창 하나를
고르는 대신, 10/20/30년 트레일링 3개를 전부 계산해서 화면에서 토글로 비교하게 한다
— "어느 창을 보느냐에 따라 결론이 바뀐다"는 것 자체가 메시지가 되게.

실행: python research/share_variant_multi_period.py
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

RATIOS = [(8, 2), (7, 3), (6, 4), (5, 5), (4, 6)]
PERIODS_YEARS = [10, 20, 30]


def vol_ann(r):
    return float(np.std(r) * np.sqrt(252) * 100)


def month_snapshot(idx_local, n_local, curve):
    s = pd.Series(np.arange(n_local), index=idx_local)
    per = idx_local.to_period('M')
    first_pos = s.groupby(per).first()
    dates = [str(p) for p in first_pos.index]
    return dates, curve[first_pos.values]


def build_period(years):
    end_full = pd.Timestamp('2026-08-28')
    start = (end_full - pd.DateOffset(years=years)).strftime('%Y-%m-%d')
    D = dict(DF.build('chain', start=start))
    idx = D['idx']
    px = pd.Series(D['px'], index=idx)
    n = len(idx)
    r_qqq1x = np.nan_to_num(px.pct_change().values)
    r_div = np.asarray(D['schdr'], float)

    def blend(s, q):
        return DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10), dict(div=r_div, qqq=r_qqq1x))

    rows = []
    monthly = {}
    dates_ref = None
    for s, q in [(10, 0)] + RATIOS + [(0, 10)]:
        r = r_div if q == 0 else (r_qqq1x if s == 0 else blend(s, q))
        c = np.cumprod(1 + r)
        m = EC.fullmet(c, idx=idx)
        v = vol_ann(r)
        label = 'SCHD' if q == 0 else ('QQQ' if s == 0 else f'S{s}Q{q}')
        rows.append(dict(label=label, s=s, q=q, cagr=round(m['cagr'], 3), vol=round(v, 3),
                          mdd=round(m['mdd'], 3), final=round(m['final'], 2), calmar=round(m['calmar'], 4)))
        if label not in ('SCHD', 'QQQ'):
            dates, ms = month_snapshot(idx, n, c)
            if dates_ref is None:
                dates_ref = dates
            monthly[label] = [round(float(x), 5) for x in ms]

    return dict(static=rows, monthly=dict(dates=dates_ref, ratios=monthly),
                data_from=str(idx[0].date()), data_to=str(idx[-1].date()), months=len(dates_ref))


def main():
    EC.selfcheck()
    out = {}
    for y in PERIODS_YEARS:
        p = build_period(y)
        out[str(y)] = p
        print(f'\n[{y}년] {p["data_from"]} ~ {p["data_to"]} ({p["months"]}개월)')
        print(f"{'라벨':<8}{'CAGR%':>8}{'변동성%':>9}{'MDD%':>8}{'최종배수':>12}{'Calmar':>8}")
        for r in p['static']:
            print(f"{r['label']:<8}{r['cagr']:>8.2f}{r['vol']:>9.2f}{r['mdd']:>8.2f}{r['final']:>12.2f}{r['calmar']:>8.3f}")
        # 승자 판정 (SCHD vs QQQ vs 중간배합)
        best_calmar = max(p['static'], key=lambda x: x['calmar'])
        print(f'  -> Calmar 최고: {best_calmar["label"]} ({best_calmar["calmar"]:.3f})')

    with open('공유용_별도전략/_multi_period_out.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('\n[저장] 공유용_별도전략/_multi_period_out.json')


if __name__ == '__main__':
    main()
