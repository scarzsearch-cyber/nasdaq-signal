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
