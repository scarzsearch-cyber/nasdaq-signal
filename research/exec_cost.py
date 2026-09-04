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
  ② 스프레드/슬리피지: 체결가 vs 그날 기준가 차이 (b_trades_v1 → 백업 json)
  ③ 괴리율      : 시장가 vs NAV (data/nav_history.csv — 이미 매일 적립 중)
모형의 0.1% 슬리피지는 ②+③ 을 덮어야 한다.

평가 전용 · 전략 무변경. 실행: python research/exec_cost.py [백업.json]
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import csv
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


def dev_stats():
    """괴리율 실측 — nav_collect 가 매일 쌓는다."""
    p = os.path.join('data', 'nav_history.csv')
    if not os.path.exists(p):
        return {}, []
    with open(p, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    out = {}
    for c in LEGS:
        v = [float(r['dev_pct']) for r in rows if r['code'] == c and r['dev_pct']]
        if v:
            m = sum(v) / len(v)
            sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5 if len(v) > 1 else 0.0
            out[c] = (len(v), m, sd, min(v), max(v))
    days = sorted({r['as_of'] for r in rows})
    return out, days


def trade_stats(path):
    """백업 json 의 체결 기록에서 기준가 대비 차이를 뽑는다 (선택 인자)."""
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        j = json.load(f)
    tr = j.get('trades') or j.get('b_trades_v1') or []
    got = []
    for t in tr:
        px, ref = t.get('px'), t.get('ref')
        if px and ref:
            got.append(abs(float(px) / float(ref) - 1))
    return got


def main():
    print('\n[1] 실측 진행 상황 — 동결 이후 OOS 장부')
    n, sw, d0, d1 = oos_state()
    print(f'  기록 {n} 영업일 ({d0} ~ {d1}) · 전환 {sw}회')
    need = 20
    print(f'  슬리피지를 논하려면 최소 {need}회 전환이 필요하다 (연 2~3회 → 약 {need/2.5:.0f}년)')
    print(f'  진행률 {sw}/{need} — {"표본 부족, 아직 판정 불가" if sw < need else "판정 가능"}')

    print('\n[2] 괴리율 실측 (nav_history — 이미 매일 적립 중)')
    ds, days = dev_stats()
    if not ds:
        print('  수집분 없음')
    else:
        print(f'  수집 {len(days)} 영업일 ({days[0]} ~ {days[-1]})')
        print(f"{'종목':>8} {'이름':>12} {'n':>4} {'평균':>8} {'표준편차':>9} {'최대|dev|':>10}")
        worst = 0.0
        for c, lab in LEGS.items():
            if c not in ds:
                continue
            k, m, sd, lo, hi = ds[c]
            mx = max(abs(lo), abs(hi))
            worst = max(worst, mx)
            print(f'{c:>8} {lab:>12} {k:>4} {m:>7.3f}% {sd:>8.3f}% {mx:>9.3f}%')
        print(f'  모형 슬리피지 {MODEL_SLIP:.1%} 대비 최대 괴리 {worst/100:.2%} — '
              f'{"모형 안" if worst/100 <= MODEL_SLIP else "★모형 초과"}')
        if len(days) < 60:
            print(f'  ※ {len(days)}일뿐이라 분포를 논하기 이르다 (60 영업일 이상 권장)')

    print('\n[3] 체결 기록 (선택 — 백업 json 경로를 인자로 주면 읽는다)')
    got = trade_stats(sys.argv[1] if len(sys.argv) > 1 else None)
    if got is None:
        print('  경로 미지정 — 화면의 「체결 기록·백업」에서 json 을 저장해 인자로 넘겨라:')
        print('    python research/exec_cost.py C:/경로/백업.json')
    elif not got:
        print('  체결 기록에 기준가가 입력된 건이 없다 (기준가를 넣어야 실측이 된다)')
    else:
        m = sum(got) / len(got)
        print(f'  기준가 대비 차이 {len(got)}건: 평균 {m:.3%} · 최대 {max(got):.3%}')
        print(f'  모형 슬리피지 {MODEL_SLIP:.1%} 대비 — '
              f'{"모형 안" if m <= MODEL_SLIP else "★모형 초과"}')

    print('\n[4] 판정 규약 (미리 고정 — 표본이 차면 이 기준으로 읽는다)')
    print(f'  · 전환 {need}회 이상 + 괴리율 60 영업일 이상이 모이면 판정한다.')
    print(f'  · ②+③ 실측 합이 모형 {MODEL_SLIP:.1%} 를 넘으면 03_System_Params 의 비용')
    print('    가정을 실측으로 교체한다(전략 규칙 변경 아님 — 평가 기준 갱신).')
    print('  · 04 §5-8 실측: 손익분기 편도 ≈2.5%(모형의 25배). 따라서 이 검증은')
    print('    **결론을 바꾸기 위해서가 아니라 가정을 사실로 바꾸기 위해** 한다.')


if __name__ == '__main__':
    main()
