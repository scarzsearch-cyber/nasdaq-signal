#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v75] 종가 확정 대기 루프 — "새벽 5시(미 종가) ~ 아침 9시(한국 개장) 안 반영" 보장 강화.

문제: GitHub 예약 실행은 슬롯을 통째로 건너뛴다 (실측: 8/26 3슬롯 전부, 8/29 06:17·06:47).
     슬롯을 늘려도 '떠야 도는' 구조는 그대로다.
해법: **슬롯 하나만 떠도** 이 루프가 예상 종가가 반영될 때까지 몇 분 간격으로 재시도한다.
     4개 트리거(05:17/06:17/07:47/09:17 KST) 중 하나라도 뜨면 창 전체가 커버된다.

동작:
  1. 예상 종가 날짜 = Yahoo meta 의 regularMarketTime (마지막 세션 마감 시각) 의 날짜.
     마감 후에는 이 값이 마감 시각으로 굳으므로 주말·휴장에도 자동으로 맞다
     (휴장일: 예상 = 직전 거래일 = 이미 반영됨 → 즉시 종료. 헛돌지 않는다).
  2. signal.json 의 as_of ≥ 예상이면 **아무것도 안 하고** 종료 — 신선한 날엔
     signal.json 을 다시 쓰지 않으므로 의미 없는 커밋도 안 생긴다.
  3. 아니면 update_signal.py 실행 → 재확인 → 될 때까지 240초 간격, 최대 170분.
  4. 시한 초과 시 종료코드 1 (workflow 실패 → notify 알림).

로컬 확인:  python3 deploy/wait_close.py
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SIG = os.path.join('data', 'signal.json')
MAX_MIN = 170          # 다음 트리거와 겹치기 직전까지
SLEEP = 240


def expected_close_date():
    """마지막으로 **마감된** 미국 세션의 날짜 (UTC 날짜 = ET 날짜, 마감시각 기준)."""
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/QQQ?range=1d&interval=1d'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        meta = json.loads(r.read())['chart']['result'][0]['meta']
    qt = meta.get('regularMarketTime')
    end = meta.get('currentTradingPeriod', {}).get('regular', {}).get('end')
    if not qt:
        return None
    if end and qt < end:
        # 장중 — 오늘 종가는 아직 없다. 예상 = 직전 세션 (as_of 가 이미 그 값이면 신선)
        # 직전 세션 날짜는 알 수 없으니 '지금보다 과거면 통과' 규약으로 None 반환.
        return 'IN_SESSION'
    return datetime.fromtimestamp(qt, timezone.utc).strftime('%Y-%m-%d')


def current_as_of():
    if not os.path.exists(SIG):
        return ''
    try:
        return json.load(open(SIG, encoding='utf-8')).get('as_of', '')
    except Exception:
        return ''


def main():
    t0 = time.time()
    n = 0
    while True:
        n += 1
        try:
            exp = expected_close_date()
        except Exception as e:
            print(f'[{n}] 예상일 조회 실패({e}) — 재시도 대기', file=sys.stderr)
            exp = None
        cur = current_as_of()
        if exp == 'IN_SESSION':
            print(f'[{n}] 미국 장중 — 직전 종가({cur})가 최신. 종료.')
            return
        if exp and cur >= exp:
            print(f'[{n}] 이미 최신 (as_of {cur} = 예상 {exp}) — 갱신 없이 종료.')
            return
        print(f'[{n}] as_of {cur} < 예상 {exp or "?"} — 갱신 시도', flush=True)
        rc = subprocess.call([sys.executable, os.path.join('deploy', 'update_signal.py')])
        cur = current_as_of()
        if exp and cur >= exp:
            print(f'[{n}] 종가 반영 완료: as_of {cur} (시도 {n}회, {int(time.time()-t0)}초)')
            return
        if (time.time() - t0) > MAX_MIN * 60:
            print(f'시한 {MAX_MIN}분 초과 — as_of {cur}, 예상 {exp}. 수동 확인 필요.',
                  file=sys.stderr)
            sys.exit(1)
        time.sleep(SLEEP)


if __name__ == '__main__':
    main()
