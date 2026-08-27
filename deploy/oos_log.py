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
OUT = os.path.join('data', 'oos_log.csv')
COLS = ['as_of', 'close', 'high_252', 'dd', 'state', 'changed', 'rule', 'fingerprint']


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

    b = (j.get('strategies') or {}).get(f['rule']['name'].replace('-16/-16', 'B')) or {}
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

    rows = []
    if os.path.exists(OUT):
        with io.open(OUT, encoding='utf-8', newline='') as fh:
            rows = list(csv.DictReader(fh))
    if any(r['as_of'] == as_of for r in rows):
        print('%s 는 이미 기록됨 — 변경하지 않는다 (append-only)' % as_of)
        return

    rows.append(row)
    rows.sort(key=lambda r: r['as_of'])
    with io.open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print('OOS 장부 %d행 (동결 %s 이후 %d영업일 기록)'
          % (len(rows), f['frozen_at'], len(rows)))


if __name__ == '__main__':
    main()
