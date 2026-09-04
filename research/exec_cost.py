# -*- coding: utf-8 -*-
"""
[체결 비용 실측 하네스, 2026-08-31 소유자 지시] 0.2% 가정을 언젠가 실측으로 검증한다.

배경: 03_System_Params 는 매매비용을 **편도 0.1% + 슬리피지 0.1%** 로 가정한다.
  04 §5-8 이 손익분기가 편도 ≈2.5%(25배 여유)임을 보였으므로 **결론이 뒤집힐 위험은
  낮다.** 그러나 가정은 여전히 가정이고, 동결(2026-08-27) 이후 순수 OOS 가 쌓이면
  실측으로 대체할 수 있다.

이 스크립트는 **지금 답을 내지 않는다.** 표본이 모이면 자동으로 답이 나오도록
경로를 미리 깔아둔다. **[v140] 사람이 돌리지 않는다** — 자동 파수꾼이 매주
`surv_map` 과 함께 돌려 `data/ops_check.json` 에 진행률을 남기고 화면이 읽는다.

무엇을 재는가 — 체결 비용은 세 층이다:
  ① 수수료      : 증권사 고정, 실측 불필요
  ② 체결 손실   : 체결가 vs 그날 기준가 (b_trades_v1 → 백업 json)
  ③ NAV 괴리   : 시장가 vs NAV (data/nav_history.csv — 이미 매일 적립 중)
모형의 0.1% 슬리피지는 ②+③, 즉 **체결가 vs 같은 날 NAV**를
매수/매도 방향으로 보정한 편도 실행손실을 덮어야 한다.

관측 단위는 체결 행 수가 아니라 **서로 다른 체결일**이다. 한 번의 전환에서
공격 1종·방어 3종이 같은 날 체결되므로 행 4개를 독립 표본 4개로 세면 안 된다.
OOS 전환 수는 체결 **기회**일 뿐 실측 표본이 아니다. 백업을 주지 않은 자동
점검은 NAV 수집 일수만 감시하고 체결 진행률은 0으로 남긴다.

평가 전용 · 전략 무변경. 실행: python research/exec_cost.py [백업.json]
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import csv
import datetime
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

MODEL_FEE, MODEL_SLIP = 0.001, 0.001        # 03_System_Params 가정
LEGS = {'418660': '공격 레버리지', '458730': '방어 배당',
        '305080': '방어 국채', '411060': '방어 금'}


def oos_state():
    """동결 이후 장부에 전환이 몇 번 기록됐나 — 실측 가능성의 상한."""
    p = os.path.join('data', 'oos_log.csv')
    if not os.path.exists(p):
        return 0, 0, None, None
    with open(p, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 0, 0, None, None
    key = 'state_B' if 'state_B' in rows[0] else ('state' if 'state' in rows[0] else None)
    sw = 0
    if key:
        for a, b in zip(rows, rows[1:]):
            if a[key] and b[key] and a[key] != b[key]:
                sw += 1
    return len(rows), sw, rows[0].get('as_of'), rows[-1].get('as_of')


def nav_stats(path=None):
    """NAV 일간 통계와 (날짜, 종목) 별 NAV 조회표를 한 번에 읽는다."""
    p = path or os.path.join('data', 'nav_history.csv')
    if not os.path.exists(p):
        return {}, [], {}
    with open(p, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    out = {}
    lookup = {}
    valid_by_day = {}
    for c in LEGS:
        v = []
        for r in rows:
            if r.get('code') != c:
                continue
            day = _weekday(r.get('as_of'))
            nav, dev = _number(r.get('nav')), _number(r.get('dev_pct'))
            if day is None or nav is None or nav <= 0 or dev is None:
                continue
            v.append(dev)
            lookup[(day, c)] = nav
            valid_by_day.setdefault(day, []).append(c)
        if v:
            m = sum(v) / len(v)
            sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5 if len(v) > 1 else 0.0
            out[c] = (len(v), m, sd, min(v), max(v))
    # 네 다리의 유효 NAV/괴리가 각각 한 번 있는 평일만 수집일로 센다.
    # 주말·NaN·부분 기록은 60일 관문을 채우지 못한다.
    days = sorted(d for d, codes in valid_by_day.items()
                  if len(codes) == len(LEGS) and set(codes) == set(LEGS))
    return out, days, lookup


def _number(v):
    try:
        x = float(v)
        return x if x == x and abs(x) != float('inf') else None
    except (TypeError, ValueError):
        return None


def _weekday(value):
    try:
        d = datetime.date.fromisoformat(str(value))
        return d.isoformat() if d.weekday() < 5 and str(value) == d.isoformat() else None
    except (ValueError, TypeError):
        return None


def analyse_trades(trades, nav_lookup):
    """체결행을 매매 방향으로 보정하고, 같은 체결일은 한 사건으로 묶는다.

    매수는 싸게, 매도는 비싸게 체결될수록 손실이 음수다. NAV 행이 하나라도
    빠진 날은 ①+② 합산이 완성되지 않으므로 판정 표본에서 전체 제외한다.
    """
    by_date = {}
    ref_costs = []
    valid = 0
    invalid = 0
    for t in trades if isinstance(trades, list) else []:
        if not isinstance(t, dict):
            invalid += 1
            continue
        d, code, side = str(t.get('d') or ''), str(t.get('code') or ''), t.get('side')
        qty, px, ref = _number(t.get('qty')), _number(t.get('px')), _number(t.get('ref'))
        if (_weekday(d) is None or code not in LEGS
                or side not in ('buy', 'sell') or not qty or qty <= 0 or not px or px <= 0):
            invalid += 1
            if _weekday(d) is not None and code in LEGS:
                by_date.setdefault(d, []).append({'matched': False})
            continue
        valid += 1
        sign = 1.0 if side == 'buy' else -1.0
        if ref and ref > 0:
            ref_costs.append(sign * (px / ref - 1))
        nav = _number(nav_lookup.get((d, code)))
        row = {'matched': bool(nav and nav > 0)}
        if row['matched']:
            row['cost'] = sign * (px / nav - 1)
            row['notional'] = qty * nav
        by_date.setdefault(d, []).append(row)

    event_costs = []
    incomplete_dates = []
    for d, rows in sorted(by_date.items()):
        if not rows or not all(r['matched'] for r in rows):
            incomplete_dates.append(d)
            continue
        den = sum(r['notional'] for r in rows)
        if den > 0:
            event_costs.append((d, sum(r['cost'] * r['notional'] for r in rows) / den))
    return {'raw': len(trades) if isinstance(trades, list) else 0,
            'valid': valid, 'invalid': invalid, 'dates': len(by_date),
            'ref_costs': ref_costs, 'event_costs': event_costs,
            'incomplete_dates': incomplete_dates}


def trade_stats(path, nav_lookup):
    """백업 json 체결 기록을 분석한다(선택 인자)."""
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        j = json.load(f)
    tr = j.get('trades') or j.get('b_trades_v1') or []
    return analyse_trades(tr, nav_lookup)


def selfcheck():
    """매수/매도 부호와 같은 날 묶기·NAV 누락 제외를 작은 예제로 고정한다."""
    nav = {('2026-01-02', '418660'): 100.0, ('2026-01-02', '458730'): 100.0,
           ('2026-01-05', '418660'): 100.0}
    tr = [
        {'d': '2026-01-02', 'code': '418660', 'side': 'buy', 'qty': 1, 'px': 101, 'ref': 100},
        {'d': '2026-01-02', 'code': '458730', 'side': 'sell', 'qty': 1, 'px': 101, 'ref': 100},
        {'d': '2026-01-05', 'code': '418660', 'side': 'sell', 'qty': 1, 'px': 99, 'ref': 100},
        {'d': '2026-01-05', 'code': '411060', 'side': 'buy', 'qty': 1, 'px': 100, 'ref': 100},
    ]
    got = analyse_trades(tr, nav)
    assert abs(got['ref_costs'][0] - 0.01) < 1e-12
    assert abs(got['ref_costs'][1] + 0.01) < 1e-12
    assert len(got['event_costs']) == 1 and abs(got['event_costs'][0][1]) < 1e-12
    assert got['incomplete_dates'] == ['2026-01-05']


def main():
    selfcheck()
    need = 20
    print('\n[1] 동결 이후 OOS 전환 기회 — 체결 표본이 아님')
    n, sw, d0, d1 = oos_state()
    print(f'  기록 {n} 영업일 ({d0} ~ {d1}) · 전환 {sw}회')
    print('  ※ 전환 신호가 나왔다고 사용자가 체결했거나 체결가를 기록했다고 볼 수 없다.')

    print('\n[2] NAV 괴리 일간 모니터링 (nav_history)')
    ds, days, nav_lookup = nav_stats()
    if not days:
        print('  수집 0 영업일 · 수집분 없음')
    else:
        print(f'  수집 {len(days)} 영업일 ({days[0]} ~ {days[-1]})')
        print(f"{'종목':>8} {'이름':>12} {'n':>4} {'평균':>8} {'표준편차':>9} {'최대|dev|':>10}")
        for c, lab in LEGS.items():
            if c not in ds:
                continue
            k, m, sd, lo, hi = ds[c]
            mx = max(abs(lo), abs(hi))
            print(f'{c:>8} {lab:>12} {k:>4} {m:>7.3f}% {sd:>8.3f}% {mx:>9.3f}%')
        print('  ※ 매일의 최대 괴리는 체결 방향·시각이 없어 비용 판정에 쓰지 않는다.')
        if len(days) < 60:
            print(f'  ※ {len(days)}일뿐이라 분포를 논하기 이르다 (60 영업일 이상 권장)')

    print('\n[3] 체결 기록 (선택 — 백업 json 경로를 인자로 주면 읽는다)')
    got = trade_stats(sys.argv[1] if len(sys.argv) > 1 else None, nav_lookup)
    event_costs = [] if got is None else got['event_costs']
    if got is None:
        print('  실제 체결 자료 없음 — 화면의 「체결 기록·백업」에서 json 을 저장해 인자로 넘겨라:')
        print('    python research/exec_cost.py C:/경로/백업.json')
    else:
        print(f'  원본 {got["raw"]}행 · 유효 체결 {got["valid"]}행 / {got["dates"]}일 '
              f'· 형식·종목 오류 {got["invalid"]}행')
        if got['ref_costs']:
            mref = sum(got['ref_costs']) / len(got['ref_costs'])
            print(f'  기준가 대비 방향 보정 손실 {len(got["ref_costs"])}행: 평균 {mref:.3%} '
                  f'(+: 비용, −: 가격 개선)')
        else:
            print('  기준가가 있는 유효 체결이 없음')
        if got['incomplete_dates']:
            print(f'  NAV 행이 빠져 판정에서 제외한 체결일 {len(got["incomplete_dates"])}일')
        if event_costs:
            vals = [v for _, v in event_costs]
            print(f'  체결가↔NAV 합산 {len(vals)}일: 평균 {sum(vals)/len(vals):.3%} '
                  f'· 최악 {max(vals):.3%} (+: 비용, −: 가격 개선)')
        else:
            print('  같은 날·같은 종목 NAV 가 전부 맞는 체결일이 없음')

    ready = len(event_costs) >= need and len(days) >= 60
    print(f'  진행률 {len(event_costs)}/{need} — '
          f'{"판정 가능" if ready else "표본 부족, 아직 판정 불가"}')

    print('\n[4] 판정 규약 (미리 고정 — 표본이 차면 이 기준으로 읽는다)')
    print(f'  · NAV 가 전부 맞는 서로 다른 체결일 {need}일 이상 + NAV 60 영업일 이상이면 판정한다.')
    print('  · 같은 날 여러 종목은 NAV 금액으로 가중해 한 사건으로 묶고, 사건별 평균을 쓴다.')
    print(f'  · 매수(+)·매도(−) 방향 보정 「체결가 vs NAV」 평균이 모형 {MODEL_SLIP:.1%} 를')
    print('    넘으면 03_System_Params 의 슬리피지 가정을 실측으로 교체한다.')
    print('  · 04 §5-8 실측: 손익분기 편도 ≈2.5%(모형의 25배). 따라서 이 검증은')
    print('    **결론을 바꾸기 위해서가 아니라 가정을 사실로 바꾸기 위해** 한다.')
    if ready:
        mean_cost = sum(v for _, v in event_costs) / len(event_costs)
        print(f'  ▶ 실측 판정: 평균 {mean_cost:.3%} — '
              f'{"★모형 초과" if mean_cost > MODEL_SLIP else "모형 안"}')


if __name__ == '__main__':
    main()
