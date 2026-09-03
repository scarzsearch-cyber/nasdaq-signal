#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v76] 전환 신호 알림 — changed_today 인 날만 notify.py 로 폰에 알린다.

이 전략에서 놓치면 안 되는 날은 1년에 두어 번뿐인 전환일이다. 그날 아침
신호 갱신 직후 이 스크립트가 돌고, secret(notify.py 참조)이 있으면 알림이 간다.
전환이 없으면 아무것도 하지 않는다.
"""
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def already_logged(as_of):
    """이 as_of 의 전환이 OOS 장부에 이미 기록됐는가 — 즉 앞선 슬롯이 이미 알렸는가."""
    p = os.path.join('data', 'oos_log.csv')
    if not os.path.exists(p):
        return False
    try:
        import csv
        with open(p, encoding='utf-8') as f:
            return any(r.get('as_of') == as_of and r.get('changed') == '1'
                       for r in csv.DictReader(f))
    except Exception as e:                       # 못 읽으면 보내는 쪽 — 누락보다 중복이 낫다
        print(f'[경고] 장부를 읽지 못했다({e}) — 중복 위험을 감수하고 보낸다', file=sys.stderr)
        return False

def main():
    sig = os.path.join('data', 'signal.json')
    if not os.path.exists(sig):
        return
    j = json.load(open(sig, encoding='utf-8'))
    b = (j.get('strategies') or {}).get('B') or {}
    # [2026-09-04 코드리뷰] 최상위 changed_today·state 는 **A(−16/−11) 미러**다(v192 적발).
    # B 가 없을 때 그리로 물러서면 **A 가 전환한 날 카톡이 가고 B 의 전환일엔 안 간다.**
    # 그건 「알림이 없는 것」보다 나쁘다 — 틀린 날에 팔게 만든다. 없으면 말하고 멈춘다.
    if not b:
        print('[경고] signal.json 에 strategies.B 가 없다 — 알림을 보내지 않는다', file=sys.stderr)
        return
    if not b.get('changed_today'):
        print('전환 없음 — 알림 생략')
        return
    # [2026-09-04 코드리뷰] ★ daily-signal 슬롯이 하루 여러 번 돈다(실측 4~7회) —
    #   전환일에는 **매 슬롯이 같은 카톡을 보낸다.** changed_today 는 그날 내내 참이고
    #   이 스크립트는 모든 슬롯에서 무조건 돌기 때문이다. 동결 후 전환이 0회라 아직
    #   안 드러났을 뿐 반드시 일어난다. 하필 **1년에 두어 번뿐인 가장 중요한 알림**이
    #   도배로 오면, 이 저장소가 내내 경계해 온 알림 피로가 최악의 순간에 터진다.
    #   → 장부(data/oos_log.csv)를 표시로 쓴다. 그 파일은 같은 잡의 **뒤 스텝**이 쓰고
    #   커밋하므로, 이번 슬롯에는 아직 없고 다음 슬롯에는 있다 — 딱 한 번 보낸다.
    #   커밋이 실패하면 다음 슬롯이 다시 보낸다(중복이지 누락이 아니다 — 안전한 방향).
    #   장부는 읽기만 한다(§2). 08:40 파수꾼 재알림(v192)은 별개 경로라 영향 없다.
    if already_logged(j['as_of']):
        print('이 전환은 이미 장부에 있다(다른 슬롯이 알렸다) — 중복 발송 생략')
        return
    st = b.get('state', '?')
    if st == 'QLD':
        act = '방어 바스켓 전량 매도 → TIGER 나스닥100레버리지(418660) 매수'
    else:
        act = 'QLD 전량 매도 → 방어 바스켓 매수 (배당40 458730 / 국채40 305080 / 금20 411060)'
    msg = (f"낙폭 {j.get('dd')}% (종가 {j.get('close')}, {j.get('as_of')})\n"
           f"오늘 한국장 09:05~15:20 에: {act}")
    subprocess.call([sys.executable, os.path.join('deploy', 'notify.py'),
                     '전환 신호 발생', 'signal', msg])


if __name__ == '__main__':
    main()
