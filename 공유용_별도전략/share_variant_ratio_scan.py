# -*- coding: utf-8 -*-
"""
[공유용 변형 — SCHD:QQQ 비율 스캔, 2026-09-01] share_variant_divqqq.py 후속.
소유자가 보여준 그래프(수익률x변동성, S9Q1~S1Q9 낙타등 곡선)를 실제 데이터로
재현 + 각 비율을 공격 다리로 넣었을 때 전환전략 성과까지 낸다. 판정 아님·
전략 B 무변경. 데이터·엔진은 share_variant_divqqq.py 와 동일(54년 체인).

두 표를 낸다:
  [A] 정적 매수보유 — 비율별 CAGR·변동성·MDD·최종배수 (그래프의 "낙타등"이
      실제 데이터에서도 나타나는지 확인용. 상관 낮으면 중간 비율이 양끝보다
      변동성 대비 유리해지는 게 마코위츠 표준 결과)
  [B] 그 비율을 공격다리로 쓰고 기존 −16/−16 신호 + 국채60/금40 방어로
      전환했을 때 성과 (지난 1차 실측과 같은 조건, 비율만 스캔)

실행: python research/share_variant_ratio_scan.py
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
r_def = DA.mix_monthly_parts(idx, dict(ust5=0.60, gold=0.40), dict(ust5=r_ust5, gold=r_gold))

RATIOS = [(9, 1), (8, 2), (7, 3), (6, 4), (5, 5), (4, 6), (3, 7), (2, 8), (1, 9)]


def blend(s, q):
    return DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10),
                                 dict(div=r_div, qqq=r_qqq1x))


def vol_ann(r):
    return float(np.std(r) * np.sqrt(252) * 100)


def main():
    EC.selfcheck()
    print(f'\n데이터 구간: {idx[0].date()} ~ {idx[-1].date()}  ({n}행)\n')

    rows = []
    print('[A] 정적 매수보유(월초 재조정) — 비율별 위험/수익')
    print(f"{'라벨':<8}{'CAGR%':>8}{'변동성%':>9}{'MDD%':>8}{'최종배수':>12}{'Calmar':>8}")
    for s, q in [(10, 0)] + RATIOS + [(0, 10)]:
        r = r_div if q == 0 else (r_qqq1x if s == 0 else blend(s, q))
        c = np.cumprod(1 + r)
        m = EC.fullmet(c, idx=idx)
        v = vol_ann(r)
        label = 'SCHD' if q == 0 else ('QQQ' if s == 0 else f'S{s}Q{q}')
        print(f"{label:<8}{m['cagr']:>8.2f}{v:>9.2f}{m['mdd']:>8.2f}{m['final']:>12.2f}{m['calmar']:>8.3f}")
        rows.append(dict(label=label, s=s, q=q, cagr=round(m['cagr'], 3), vol=round(v, 3),
                          mdd=round(m['mdd'], 3), final=round(m['final'], 2), calmar=round(m['calmar'], 4)))

    print('\n[B] 같은 비율을 공격다리로 · 기존 -16/-16 신호 + 국채60/금40 방어로 전환')
    print(f"{'라벨':<8}{'최종배수':>12}{'CAGR%':>8}{'MDD%':>8}{'Calmar':>8}{'전환수':>7}")
    rows_b = []
    for s, q in RATIOS:
        r_atk = blend(s, q)
        w = EC.rule_dd(px, -0.16, -0.16)
        c = EC.sim2(w, r_atk, r_def)
        m = EC.fullmet(c, idx=idx)
        turns = int(np.sum(np.abs(np.diff(w))))
        label = f'S{s}Q{q}'
        print(f"{label:<8}{m['final']:>12.2f}{m['cagr']:>8.2f}{m['mdd']:>8.2f}{m['calmar']:>8.3f}{turns:>7}")
        rows_b.append(dict(label=label, s=s, q=q, final=round(m['final'], 2), cagr=round(m['cagr'], 3),
                            mdd=round(m['mdd'], 3), calmar=round(m['calmar'], 4)))

    out = dict(static=rows, switched=rows_b, data_from=str(idx[0].date()), data_to=str(idx[-1].date()))
    with open('공유용_별도전략/_ratio_scan_out.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('\n[저장] 공유용_별도전략/_ratio_scan_out.json')


if __name__ == '__main__':
    main()
