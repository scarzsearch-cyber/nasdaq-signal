#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signal.html 의 전략 선택 카드에 띄울 성과지표를 미리 계산해 data/strategy_stats.json 에 굳힌다.

매일 도는 스크립트가 아니다. 원자료(data/hist/**, *_us_d.csv)가 있는 로컬에서 수동으로 돌리고
결과 JSON 만 커밋한다. GitHub Actions 러너에는 확장 원자료가 없으므로 여기서 돌리지 않는다.

    python deploy/build_stats.py          # 반드시 저장소 루트에서

[시나리오]
  us_2000  달러 · 2000-01~ · QQQ/QLD 실물, SCHD 상장 이전은 연 2% 현금   (verify.py 규약)
  us_1972  달러 · 1972-02~ · 나스닥 3구간 체인, 방어자산은 배당 실측 체인 (전략_v21 §2·§3)
  kr_1997  원화 · 1997-01~ · 환노출 2배 + 한국 거래일 체결 + 슬리피지 0.1% (전략_v21 §4)
  kr_real  원화 · 2023-06~ · 실물 TIGER 3종 시가 체결                     (전략_v21 §4.5)

[지표] 최종배수 / CAGR / MDD / Calmar / Sortino / Sharpe / 전환횟수
  Sortino, Sharpe 는 reentry_lib.met() 정의 그대로 — 무위험수익률 0, 일간수익 연율화.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import hist_data as H                 # noqa: E402
import hist_defensive as DF           # noqa: E402
import hist_korea as K                # noqa: E402
import hist_krfinal as KF             # noqa: E402
import hist_krreal as KR              # noqa: E402
import reentry_lib as RL              # noqa: E402
from reentry_lib import met, run      # noqa: E402

OUT = os.path.join('data', 'strategy_stats.json')

STRATS = {
    'B': dict(enter=-0.16, exit=-0.16, name='−16 / −16', ladder=[(('dd', -0.16), 1.0, 0)]),
    'A': dict(enter=-0.16, exit=-0.11, name='−16 / −11', ladder=[(('dd', -0.11), 1.0, 0)]),
}


def pack(curve, turn):
    m = met(curve)
    return {
        'final': round(float(m['final']), 3),
        'cagr': round(float(m['cagr']) * 100, 2),
        'mdd': round(float(m['mdd']) * 100, 2),
        'calmar': round(float(m['calmar']), 3),
        'sortino': round(float(m['sortino']), 3) if np.isfinite(m['sortino']) else None,
        'sharpe': round(float(m['sharpe']), 3),
        'years': round(float(m['years']), 1),
        'switches': int(np.sum(np.asarray(turn) > 1e-9)),
        'start': curve.index[0].strftime('%Y-%m-%d'),
        'end': curve.index[-1].strftime('%Y-%m-%d'),
    }


def sc_us_2000():
    D = RL.build()
    out = {}
    for k, S in STRATS.items():
        c, w, t = run(D, S['ladder'], enter=S['enter'])
        out[k] = pack(c, t)
    return out


def sc_us_1972():
    D = DF.build('chain')
    out = {}
    for k, S in STRATS.items():
        c, w, t = run(D, S['ladder'], enter=S['enter'])
        out[k] = pack(c, t)
    return out


def sc_kr_1997():
    D, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    krd = K.kr_caldays()
    Dx = dict(D); Dx['qldr'] = lev2; Dx['schdr'] = dfk
    out = {}
    for k, S in STRATS.items():
        c, w, t = K.run_kr(Dx, S, cost=0.001, slip=0.001, start=KF.ST, krdays=krd)
        out[k] = pack(c, t)
    return out


def sc_kr_real():
    out = {}
    for k, S in STRATS.items():
        c, hold, dd = KR.run_real(S['exit'])
        turn = hold.shift(1).fillna(1.0).diff().abs().fillna(0).values
        out[k] = pack(c, turn)
    return out


SCENARIOS = [
    ('us_2000', '미국 달러 기준', 'QQQ 실물 · SCHD 상장 이전은 연 2% 현금. verify.py 와 같은 규약.', sc_us_2000),
    ('us_1972', '달러 · 54년 확장', '나스닥 3구간 체인 + 배당 실측 방어자산. 가장 긴 표본.', sc_us_1972),
    ('kr_1997', '원화 · 한국 체결', '환노출 2배 + 한국 거래일 체결 + 슬리피지 0.1%. 국내 ETF 상장 이전은 원화 환산 시뮬레이션.', sc_kr_1997),
    ('kr_real', '원화 · 실물 TIGER', 'TIGER 3종이 모두 상장된 이후만. 실제 시가 체결.', sc_kr_real),
]


def main():
    if not os.path.exists('qqq_us_d.csv'):
        sys.exit('저장소 루트에서 실행해야 한다: python deploy/build_stats.py')
    scen = []
    for key, label, note, fn in SCENARIOS:
        print('  계산 중 …', key, flush=True)
        s = fn()
        scen.append(dict(key=key, label=label, note=note, strategies=s))
    payload = dict(
        generated_at=pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M UTC'),
        strategies={k: dict(name=v['name'], enter=round(v['enter'] * 100),
                            exit=round(v['exit'] * 100)) for k, v in STRATS.items()},
        scenarios=scen,
    )
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    hdr = '%-16s %-9s %10s %7s %8s %8s %8s %6s' % (
        '시나리오', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar', 'Sortino', '전환')
    print('\n' + hdr); print('-' * len(hdr))
    for s in scen:
        for k in ('B', 'A'):
            m = s['strategies'][k]
            print('%-16s %-9s %10s %6.2f%% %7.2f%% %8.3f %8s %6d' % (
                s['label'] if k == 'B' else '', STRATS[k]['name'], f"{m['final']:,.1f}",
                m['cagr'], m['mdd'], m['calmar'],
                '—' if m['sortino'] is None else f"{m['sortino']:.3f}", m['switches']))
    print('\n→', OUT)


if __name__ == '__main__':
    main()
