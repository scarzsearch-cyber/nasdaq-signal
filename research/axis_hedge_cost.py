# -*- coding: utf-8 -*-
"""[v73] 헤지 60/40 (방어 40/40/20) 거래비용 민감도 — 구조적 견고성 확인.

목적: 특정 숫자 맞추기가 아니라, 편도 비용이 0 → 1.0% 로 올라도 전략의 성격
(낙폭 축소·Calmar 우위)이 유지되는지 본다. 성과 정의는 기존 함수(reentry_lib.met,
build_stats 의 헤지 구성)를 그대로 재사용한다 — 새 정의 없음.

실행:  python research/axis_hedge_cost.py        # 저장소 루트에서
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'deploy')))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_defasset as DA                    # noqa: E402
import hist_defensive as DF                   # noqa: E402
from reentry_lib import met, run              # noqa: E402
from build_stats import HEDGE_W, STRATS          # noqa: E402

COSTS = (0.0, 0.001, 0.003, 0.005, 0.010)     # 편도 0 / 0.1 / 0.3 / 0.5 / 1.0%


def costed_baskets(D, cost):
    """공격·방어 월간 바스켓 모두 같은 비용 가정으로 다시 만든다."""
    att = DA.mix_monthly_parts(
        D['idx'], HEDGE_W,
        {'lev': np.asarray(D['qldr']), 'div': np.asarray(D['schdr'])},
        cost=cost,
    )
    dfr = DA.mix_monthly(D['idx'], DA.MIX_V23, D['schdr'], cost=cost)
    return np.asarray(att, float), np.asarray(dfr, float)


def _assert_all_leg_costs_vary(leg_wealth):
    """비용 스윕에서 공격·방어 중 한쪽이라도 고정되는 회귀를 막는다."""
    for name, col in (('공격', 1), ('방어', 2)):
        values = [row[col] for row in leg_wealth]
        assert all(a > b for a, b in zip(values, values[1:])), \
            '%s 월간 바스켓 비용이 모든 스윕 행에서 함께 증가하지 않았다' % name


def main():
    D = dict(DF.build('chain'))               # 54년 확장 — 가장 긴 표본

    hdr = f'{"편도비용":>8s} {"최종배수":>12s} {"CAGR":>7s} {"MDD":>8s} {"Calmar":>7s} {"Sharpe":>7s} {"전환":>5s}'
    print('헤지 60/40 · 방어 40/40/20 · 54년 (1972-02~) 비용 민감도')
    print(hdr); print('-' * len(hdr))
    rows = []
    leg_wealth = []
    for c in COSTS:
        att, dfr = costed_baskets(D, c)
        Dx = dict(D); Dx['qldr'] = att; Dx['schdr'] = dfr
        cv, w, t = run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'], cost=c)
        m = met(cv)
        sw = int(np.sum(np.asarray(t) > 1e-9))
        rows.append((c, m))
        leg_wealth.append((c, float(np.prod(1 + att)), float(np.prod(1 + dfr))))
        print(f'{c*100:7.2f}% {m["final"]:>12,.0f} {m["cagr"]*100:6.2f}% {m["mdd"]*100:7.2f}% '
              f'{m["calmar"]:7.3f} {m["sharpe"]:7.3f} {sw:5d}')
    _assert_all_leg_costs_vary(leg_wealth)
    base, worst = rows[0][1], rows[-1][1]
    print(f'\n0% → 1.0% 에서: CAGR {base["cagr"]*100:.2f}% → {worst["cagr"]*100:.2f}% '
          f'(−{(base["cagr"]-worst["cagr"])*100:.2f}%p), MDD {base["mdd"]*100:.1f}% → {worst["mdd"]*100:.1f}%')
    print('판정 기준: 비용 증가로 성격(낙폭 축소·Calmar)이 붕괴하면 구조 취약. 선형 감쇠면 견고.')


if __name__ == '__main__':
    main()
