# -*- coding: utf-8 -*-
"""
[공유용 변형 — 비율×문턱×방어 3축 스캔, 2026-09-01] share_variant_*.py 시리즈 완결편.
소유자 요청: "비중 추천과 -16/-16 같은 문턱까지 합쳐서 최선의 전략을 짜달라."
판정 아님·전략 B 무변경(§2 무접촉). 데이터·엔진은 이전 스크립트들과 동일(54년 체인).

★ 이 저장소의 §-1 규약을 그대로 따른다 — 전체 구간 Calmar 봉우리 하나만 보고
「최선」이라 부르지 않는다:
  ⓐ 후보가 관문(고Calmar)을 통과했으면 반드시 반증 — 여기선 20년창 p05(하위
     5%가 아니라 최악에 가까운 시나리오)와 이웃 문턱·이웃 비율의 고원 여부로 반증한다.
  ⓑ 손으로 비율 9개·문턱 10개를 골랐다는 것 자체가 격자 스캔이라 어느 정도
     완화되지만, 「봉우리 하나(첨탑)」인지 「고원」인지는 반드시 확인한다.
  전 구간 통짜 지표(Calmar/최종배수)는 복리 높은 쪽이 자동 우승하므로 20년창
  p05를 나란히 낸다(비중첩 창수도 함께 — 54년/20년 ≈ 2.7개뿐이라는 것을 매번 명시).

실행: python research/share_variant_threshold_scan.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
import sys
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

RATIOS = [(9, 1), (8, 2), (7, 3), (6, 4), (5, 5), (4, 6), (3, 7), (2, 8), (1, 9)]
DEF_CANDS = {
    '국채100':     dict(ust5=1.00),
    '국채70/금30': dict(ust5=0.70, gold=0.30),
    '국채60/금40': dict(ust5=0.60, gold=0.40),
    '국채50/금50': dict(ust5=0.50, gold=0.50),
}
TH_GRID = list(range(-8, -27, -2))  # -8,-10,...,-26


def attack(s, q):
    return DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10), dict(div=r_div, qqq=r_qqq1x))


def defense(w0):
    return DA.mix_monthly_parts(idx, w0, dict(ust5=r_ust5, gold=r_gold))


def run_one(r_atk, r_def, th):
    w = EC.rule_dd(px, th / 100, th / 100)
    c = EC.sim2(w, r_atk, r_def)
    m = EC.fullmet(c, idx=idx)
    p05 = EC.p05_20y(c)
    turns = int(np.sum(np.abs(np.diff(w))))
    return dict(calmar=m['calmar'], final=m['final'], cagr=m['cagr'], mdd=m['mdd'], p05_20y=p05, turns=turns)


def main():
    EC.selfcheck()
    nonoverlap_20y = n / 5040
    print(f'\n데이터 {idx[0].date()}~{idx[-1].date()} · {n}거래일 · 20년창 비중첩 ≈ {nonoverlap_20y:.1f}개'
          f' (이 숫자로 p05_20y를 「확률」로 읽으면 안 된다 — 참고용 최악 근사치)\n')

    # ---- [1] 방어는 국채60/금40 고정 · 비율×문턱 90칸 격자 ----
    def_fixed = defense(DEF_CANDS['국채60/금40'])
    grid = {}
    print('[1] 비율×문턱 격자 (방어 국채60/금40 고정) — 셀 = Calmar (20년창 p05)')
    header = '문턱\\비율 ' + ''.join(f'{f"S{s}Q{q}":>13}' for s, q in RATIOS)
    print(header)
    for th in TH_GRID:
        row = f'{th:>9} '
        for s, q in RATIOS:
            r_atk = attack(s, q)
            res = run_one(r_atk, def_fixed, th)
            grid[(s, q, th)] = res
            row += f'{res["calmar"]:>7.3f}({res["p05_20y"]:>4.1f})'
        print(row)

    # ---- 최고 Calmar 후보 상위 8 ----
    ranked = sorted(grid.items(), key=lambda kv: kv[1]['calmar'], reverse=True)
    print('\n[2] Calmar 상위 8 (방어 국채60/금40 고정)')
    print(f"{'배합':<8}{'문턱':>6}{'Calmar':>8}{'p05_20y':>9}{'최종배수':>10}{'CAGR%':>7}{'MDD%':>7}{'전환수':>7}")
    for (s, q, th), res in ranked[:8]:
        print(f"S{s}Q{q:<6}{th:>6}{res['calmar']:>8.3f}{res['p05_20y']:>9.1f}{res['final']:>10.1f}"
              f"{res['cagr']:>7.2f}{res['mdd']:>7.2f}{res['turns']:>7}")

    # ---- 고원 검사: 1등 근방(비율 ±1, 문턱 ±2) 이 같이 좋은가 ----
    best_s, best_q, best_th = ranked[0][0]
    print(f'\n[3] 고원 검사 — 1등 S{best_s}Q{best_q}@{best_th} 이웃')
    print(f"{'배합':<8}{'문턱':>6}{'Calmar':>8}{'p05_20y':>9}")
    for ds in (-1, 0, 1):
        s2 = best_s + ds
        if s2 < 1 or s2 > 9:
            continue
        q2 = 10 - s2
        for dth in (-2, 0, 2):
            th2 = best_th + dth
            if th2 not in TH_GRID:
                continue
            key = (s2, q2, th2)
            res = grid.get(key)
            if res is None:
                continue
            mark = ' <-- 1등' if key == (best_s, best_q, best_th) else ''
            print(f"S{s2}Q{q2:<6}{th2:>6}{res['calmar']:>8.3f}{res['p05_20y']:>9.1f}{mark}")

    # ---- 1등 조합에서 방어자산 4종 재확인 ----
    print(f'\n[4] 1등 배합 S{best_s}Q{best_q}@{best_th} 에서 방어자산 후보 재비교')
    print(f"{'방어':<14}{'Calmar':>8}{'p05_20y':>9}{'최종배수':>10}{'MDD%':>7}")
    r_atk_best = attack(best_s, best_q)
    for name, w0 in DEF_CANDS.items():
        res = run_one(r_atk_best, defense(w0), best_th)
        print(f"{name:<14}{res['calmar']:>8.3f}{res['p05_20y']:>9.1f}{res['final']:>10.1f}{res['mdd']:>7.2f}")


if __name__ == '__main__':
    main()
