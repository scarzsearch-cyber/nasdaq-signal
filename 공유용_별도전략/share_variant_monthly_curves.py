# -*- coding: utf-8 -*-
"""
[공유용 변형 — 적립 계산기용 월별 곡선 추출, 2026-09-01] share_variant_ratio_scan.py 후속.
소유자가 "CAGR로 편 결정론적 투사 말고, 실제 과거 경로로 적립 시뮬레이션(분포)까지
바로 해달라"고 요청 — 이 파일은 그 재료(월초 스냅샷 곡선)만 뽑는다. 판정 아님·
전략 B 무변경. 데이터·엔진은 이전 두 스크립트와 동일(54년 체인).

왜 "월초 값 하나"만 뽑나: 적립은 매달 초 넣는다고 가정하므로, 임의의 시작월 s와
투자기간 h개월에 대해
    거치(원금 1) 최종배수      = curve[s+h] / curve[s]
    적립(매달 1) 최종배수      = sum_{i=0..h-1} curve[s+h] / curve[s+i]
로 전부 계산할 수 있다(선형이라 P0·PMT 각각의 배수만 있으면 됨). 그래서
일별 곡선 전체를 내보낼 필요 없이 "월초 스냅샷"만 있으면 프론트에서 임의의
시작월·기간 조합을 즉시 계산할 수 있다.

실행: python research/share_variant_monthly_curves.py
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
    """각 달의 첫 거래일 값만 뽑는다."""
    s = pd.Series(np.arange(n), index=idx)
    per = idx.to_period('M')
    first_pos = s.groupby(per).first()
    dates = [str(p) for p in first_pos.index]
    return dates, curve[first_pos.values]


def main():
    EC.selfcheck()
    out = {'ratios': {}}
    dates_ref = None
    for s, q in RATIOS:
        r_atk = DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10), dict(div=r_div, qqq=r_qqq1x))
        c_static = np.cumprod(1 + r_atk)
        c_switch = EC.sim2(w, r_atk, r_def)
        dates, ms = month_snapshot(c_static)
        _, mw = month_snapshot(c_switch)
        if dates_ref is None:
            dates_ref = dates
        label = f'S{s}Q{q}'
        out['ratios'][label] = {
            'static': [round(float(v), 5) for v in ms],
            'switched': [round(float(v), 5) for v in mw],
        }
        print(f'{label}: {len(ms)}개월 · static[0]={ms[0]:.4f} static[-1]={ms[-1]:.2f} · '
              f'switched[0]={mw[0]:.4f} switched[-1]={mw[-1]:.2f}')
    out['dates'] = dates_ref
    path = '공유용_별도전략/_monthly_curves_out.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    size_kb = _os.path.getsize(path) / 1024
    print(f'\n[저장] {path} ({size_kb:.1f} KB) · {len(dates_ref)}개월 · {dates_ref[0]}~{dates_ref[-1]}')


if __name__ == '__main__':
    main()
