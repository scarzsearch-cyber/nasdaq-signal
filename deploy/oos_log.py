#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전향적 OOS 장부 — 규칙 동결(2026-08-27) 이후를 하루 한 줄씩 **덧붙인다**.

`data/signal.json` 은 매일 덮어쓰므로 과거가 남지 않는다. 순수 out-of-sample
표본을 만들려면 **append-only 기록**이 필요하다. 이 스크립트가 그 일을 한다.

  · 하루 한 줄. 이미 있는 날짜는 건드리지 않는다(재실행해도 안전).
  · 기록만 한다. **어떤 판단도 하지 않는다.**
  · 이 장부를 보고 규칙을 바꾸면 순수 OOS 가 사라진다 — `data/freeze.json` 참조.

GitHub Actions 의 일일 신호 갱신 뒤에 호출된다.
로컬 확인:  python3 deploy/oos_log.py
"""
import csv
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SIG = os.path.join('data', 'signal.json')
FRZ = os.path.join('data', 'freeze.json')
QQQ = os.path.join('data', 'qqq.csv')
OUT = os.path.join('data', 'oos_log.csv')
COLS = ['as_of', 'close', 'high_252', 'dd', 'state', 'changed', 'rule', 'fingerprint',
        't4_votes', 't4_rv', 't4_w']

# [v69] T4 그림자 — 평가 전용. 채택안이 아니다. 어떤 판단·매매에도 쓰지 않는다.
# 정의와 사전 고정 파라미터는 docs/history/전략_v68_추세추종.md:
#   투표 = #{k ∈ {21,63,126,252} : 종가/종가[k일 전] > 1}
#   w    = clip(40% / 실현변동성, 0, 1) × 1[투표 ≥ 2]
#   실현변동성 = 2배 자산 근사 = 2 × (QQQ 일간수익 20일 표본표준편차) × √252
# 종가 원천은 이 장부의 close 와 같은 data/qqq.csv — 장부 안에서 일관되게.
# ([v80 정정] 이 캐시는 Yahoo **수정주가**다. 네이버 예비 소스는 최신 봉만 원시로
#  붙이는데 최신 봉은 두 값이 같다 — update_signal.py [v71] 참조. 구판 주석의
#  "(비수정)"은 오기였다. 신호 계산엔 영향 없음: 원천 이원화 실측 게이트 불일치
#  0.04% — research/axis_t4_shadow.py A-3.)
# 이 파라미터를 나중에 바꾸면 그때까지의 그림자 기록은 무효다(사전 고정이 전부다).
T4_LOOKS = (21, 63, 126, 252)
T4_TH = 2
T4_VT = 0.40
T4_WIN = 20


def t4_shadow(as_of):
    """as_of 종가까지의 데이터로 T4 목표비중을 계산한다. (votes, rv%, w) 또는 None."""
    if not os.path.exists(QQQ):
        return None
    px, last = [], None
    with io.open(QQQ, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if r['Date'][:10] <= as_of:
                px.append(float(r['Close']))
                last = r['Date'][:10]
    if last != as_of:
        # [v80] 가격 파일이 as_of 까지 안 왔다 — 전일 값을 오늘 날짜로 그럴듯하게
        # 기록하는 것보다 빈 칸이 낫다 (그림자 실패는 본 기록을 해치지 않는다).
        print('[경고] qqq.csv 마지막 날짜(%s) != as_of(%s) — T4 그림자 빈 칸'
              % (last, as_of), file=sys.stderr)
        return None
    if len(px) < max(T4_LOOKS) + 1:
        return None
    votes = sum(1 for k in T4_LOOKS if px[-1] / px[-1 - k] > 1.0)
    rets = [px[i] / px[i - 1] - 1.0 for i in range(len(px) - T4_WIN, len(px))]
    mu = sum(rets) / len(rets)
    var = sum((x - mu) ** 2 for x in rets) / (len(rets) - 1)          # 표본(ddof=1)
    rv = 2.0 * (var ** 0.5) * (252 ** 0.5)                            # 2배 자산 연율화
    w = min(1.0, T4_VT / rv) if rv > 0 else 1.0
    if votes < T4_TH:
        w = 0.0
    return votes, round(rv * 100, 1), round(w, 3)


def main():
    if not os.path.exists(SIG) or not os.path.exists(FRZ):
        print('signal.json 또는 freeze.json 이 없다 — 건너뜀', file=sys.stderr)
        return
    j = json.load(io.open(SIG, encoding='utf-8'))
    f = json.load(io.open(FRZ, encoding='utf-8'))

    as_of = j['as_of']
    if as_of < f['oos_start']:
        print('%s 는 동결일 이전 — 기록하지 않는다' % as_of)
        return

    # 동결 규칙은 signal.json 의 'B' 항목이다. freeze.json 과 문턱이 일치하는지
    # 확인하고 쓴다 — 이름 문자열을 파싱하지 않는다(몇 년을 무인으로 돌 코드다).
    b = (j.get('strategies') or {}).get('B') or {}
    if b and 'enter' in b and abs(float(b.get('enter', 0)) / 100 - f['rule']['enter']) > 1e-9:
        print('[경고] signal.json 의 B 진입선이 동결값과 다르다 — 기록을 멈춘다',
              file=sys.stderr)
        return
    row = {
        'as_of': as_of,
        'close': j.get('close'),
        'high_252': j.get('high_252'),
        'dd': j.get('dd'),
        'state': b.get('state', j.get('state')),
        'changed': int(bool(b.get('changed_today', j.get('changed_today')))),
        'rule': f['rule']['name'],
        'fingerprint': f['fingerprint'],
    }
    # T4 그림자 (실패해도 본 기록은 살린다 — 빈 칸으로 남는다)
    row.update({'t4_votes': '', 't4_rv': '', 't4_w': ''})
    try:
        t4 = t4_shadow(as_of)
        if t4:
            row.update({'t4_votes': t4[0], 't4_rv': t4[1], 't4_w': t4[2]})
    except Exception as e:
        print('[경고] T4 그림자 계산 실패(%s) — 빈 칸으로 기록' % e, file=sys.stderr)

    rows = []
    if os.path.exists(OUT):
        with io.open(OUT, encoding='utf-8', newline='') as fh:
            rows = list(csv.DictReader(fh))
    if any(r['as_of'] == as_of for r in rows):
        print('%s 는 이미 기록됨 — 변경하지 않는다 (append-only)' % as_of)
        return

    for r in rows:                      # 구판 행에 새 열이 없으면 빈 칸으로
        for c in COLS:
            r.setdefault(c, '')
    rows.append(row)
    rows.sort(key=lambda r: r['as_of'])
    with io.open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print('OOS 장부 %d행 (동결 %s 이후 %d영업일 기록)'
          % (len(rows), f['frozen_at'], len(rows)))


if __name__ == '__main__':
    main()
