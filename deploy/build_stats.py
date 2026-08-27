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

[지표] 최종배수 / CAGR / MDD / Calmar / Sortino / Sharpe / 최장회복기간 / Ulcer / 전환횟수
  Sortino, Sharpe 는 reentry_lib.met() 정의 그대로 — 무위험수익률 0, 일간수익 연율화.
  [v60] 최장회복기간·Ulcer 는 reentry_lib.ulcer_uw(). MDD 가 못 재는 '낙폭의 넓이'다.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

try:                       # [v60] cp949 콘솔에서 '−'(U+2212) 로 죽지 않게
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import hist_data as H                 # noqa: E402
import hist_defasset as DA            # noqa: E402
import hist_defensive as DF           # noqa: E402
import hist_korea as K                # noqa: E402
import hist_krfinal as KF             # noqa: E402
import hist_krreal as KR              # noqa: E402
import reentry_lib as RL              # noqa: E402
from reentry_lib import met, run, ulcer_uw   # noqa: E402

OUT = os.path.join('data', 'strategy_stats.json')

# 방어자산 2안 — 전략_v23 에서 채택안이 바뀌었다.
DEFS = [
    ('mix', '배당40 / 국채40 / 금20', '전략_v23 채택안. 국내 상품 실측 사양(환노출·실효 5년). 월 1회 재조정.'),
    ('div', '배당100 (v21)', '2026-08 이전 채택안. 비교용으로 남겨 둔다.'),
]


def defensive_r(idx, base, kind):
    """kind='div' 면 배당체인 그대로, 'mix' 면 v23 바스켓(월간 재조정)."""
    if kind == 'div':
        return np.asarray(base, dtype=float)
    return DA.mix_monthly(idx, DA.MIX_V23, base)

STRATS = {
    'B': dict(enter=-0.16, exit=-0.16, name='−16 / −16', ladder=[(('dd', -0.16), 1.0, 0)]),
    'A': dict(enter=-0.16, exit=-0.11, name='−16 / −11', ladder=[(('dd', -0.11), 1.0, 0)]),
}


def pack(curve, turn):
    m = met(curve)
    ui, uwd, uwo = ulcer_uw(curve)
    return {
        'final': round(float(m['final']), 3),
        'cagr': round(float(m['cagr']) * 100, 2),
        'mdd': round(float(m['mdd']) * 100, 2),
        'calmar': round(float(m['calmar']), 3),
        'sortino': round(float(m['sortino']), 3) if np.isfinite(m['sortino']) else None,
        'sharpe': round(float(m['sharpe']), 3),
        'years': round(float(m['years']), 1),
        # [v60] MDD 는 최악의 한 점이라 '얼마나 오래 물속이었나'를 못 잰다.
        'ulcer': round(float(ui), 2),
        'uw_months': round(uwd / 30.4375, 1),
        'uw_open': bool(uwo),
        'switches': int(np.sum(np.asarray(turn) > 1e-9)),
        'start': curve.index[0].strftime('%Y-%m-%d'),
        'end': curve.index[-1].strftime('%Y-%m-%d'),
    }


def sc_us_2000(kind):
    D = dict(RL.build())
    D['schdr'] = defensive_r(D['idx'], D['schdr'], kind)
    out = {}
    for k, S in STRATS.items():
        c, w, t = run(D, S['ladder'], enter=S['enter'])
        out[k] = pack(c, t)
    return out


def sc_us_1972(kind):
    D = dict(DF.build('chain'))
    D['schdr'] = defensive_r(D['idx'], D['schdr'], kind)
    out = {}
    for k, S in STRATS.items():
        c, w, t = run(D, S['ladder'], enter=S['enter'])
        out[k] = pack(c, t)
    return out


def sc_kr_1997(kind):
    D, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    krd = K.kr_caldays()
    if kind == 'div':
        sr = dfk
    else:
        # 채택안 3종은 전부 환노출이다 — axis_krspec.py 의 실측(b2≈0.8~1.0).
        #   TIGER 미국배당다우존스 / TIGER 미국채10년선물(실효 5년) / ACE KRX금현물
        # [v36] ust5 는 **선물형**이다(305080). 현물 총수익에서 단기금리·보수를 뺀다.
        raw = {'div': np.asarray(dfk, dtype=float),
               'ust5': DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE),
               'gold': DA.gold_r(idx)}
        parts = {k: (raw[k] if k == 'div' else (1 + raw[k]) * (1 + fr) - 1)
                 for k in DA.MIX_V23}
        sr = DA.mix_monthly_parts(idx, DA.MIX_V23, parts)
    Dx = dict(D); Dx['qldr'] = lev2; Dx['schdr'] = sr
    out = {}
    for k, S in STRATS.items():
        c, w, t = K.run_kr(Dx, S, cost=0.001, slip=0.001, start=KF.ST, krdays=krd)
        out[k] = pack(c, t)
    return out


def sc_kr_real(kind):
    out = {}
    for k, S in STRATS.items():
        c, hold, dd = KR.run_real(S['exit'], defmix=(kind == 'mix'))
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
        row = dict(key=key, label=label, note=note)
        for dk, dlabel, dnote in DEFS:
            print('  계산 중 …', key, dk, flush=True)
            row['strategies' if dk == 'mix' else 'strategies_' + dk] = fn(dk)
        scen.append(row)
    payload = dict(
        generated_at=pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M UTC'),
        strategies={k: dict(name=v['name'], enter=round(v['enter'] * 100),
                            exit=round(v['exit'] * 100)) for k, v in STRATS.items()},
        defensives=[dict(key=k, label=l, note=n) for k, l, n in DEFS],
        defensive_legs=DA.MIX_LEGS,
        scenarios=scen,
    )
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # [v45·v60] signal.json 은 이 파일의 **사본**을 안에 들고 있고, 화면은 그 사본을
    # 우선한다(signal.html: if(AUTO && AUTO.stats) STATS = AUTO.stats).
    # 그래서 여기서 새로 굳히면 사본도 같이 갱신해야 한다. 안 하면 다음 일일
    # 실행 때까지 라이브가 옛 수치를 보여준다 — v36 정정 때 실제로 그랬다.
    sig = os.path.join('data', 'signal.json')
    if os.path.exists(sig):
        with open(sig, encoding='utf-8') as f:
            j = json.load(f)
        if j.get('stats', {}).get('generated_at') != payload['generated_at']:
            j['stats'] = payload
            with open(sig, 'w', encoding='utf-8') as f:
                json.dump(j, f, ensure_ascii=False, indent=1)
            print('→', sig, '(내장 사본 갱신)')
    # [v60] 사본 갱신은 아래 요약 출력보다 **먼저** 한다 — 출력이 죽어도
    #       사본이 옛 판으로 남지 않도록.

    hdr = '%-16s %-9s %10s %7s %8s %8s %8s %9s %7s %6s' % (
        '시나리오', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar', 'Sortino',
        '회복기간', 'Ulcer', '전환')
    print('\n' + hdr); print('-' * len(hdr))
    for s in scen:
        for k in ('B', 'A'):
            m = s['strategies'][k]
            o = s['strategies_div'][k]
            def uw(x):
                return '%.1f개월%s' % (x['uw_months'], '+' if x['uw_open'] else '')
            print('%-16s %-9s %10s %6.2f%% %7.2f%% %8.3f %8s %9s %7.2f %6d' % (
                s['label'] if k == 'B' else '', STRATS[k]['name'], f"{m['final']:,.1f}",
                m['cagr'], m['mdd'], m['calmar'],
                '—' if m['sortino'] is None else f"{m['sortino']:.3f}",
                uw(m), m['ulcer'], m['switches']))
            print('%-16s %-9s %10s %6.2f%% %7.2f%% %8.3f %8s %9s %7.2f %6d   <- 배당100' % (
                '', '', f"{o['final']:,.1f}", o['cagr'], o['mdd'], o['calmar'],
                '—' if o['sortino'] is None else f"{o['sortino']:.3f}",
                uw(o), o['ulcer'], o['switches']))
    print('\n→', OUT)



if __name__ == '__main__':
    main()
