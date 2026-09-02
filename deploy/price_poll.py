#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[v190] 장중 시세 폴러 — 「5분마다」를 예약 슬롯이 아니라 **한 실행 안에서** 지킨다.

발단(2026-09-02 소유자): 「한국 장시작이 09:22 에 반영된다 — 정시에서 5분 안에 안 되나」.
실측(gh run list, 2026-09-01): price.yml 의 `*/5` 예약은 하루 84슬롯 중 **17개만** 떴고
간격 중앙 31.6분·최장 108분. 첫 스냅샷 09:06(09-01)·09:22(09-02).
→ v176 의 「5분마다」는 GitHub 이 슬롯을 대부분 버려서 **한 번도 실현된 적이 없다.**
  예약 실행은 부하가 높으면 지연·드롭되며 정시(00:00 UTC = 09:00 KST)가 가장 심하다
  (공식 문서). 슬롯을 더 넣어도 「떠야 도는」 구조는 그대로다.

해법: 개장 **전에** 뜬 실행 하나가 개장까지 기다렸다가 장 끝까지 5분마다 찍는다.
  · 예약 지연(실측 2~18분)은 개장 전 여유로 흡수 — 08:30·08:40·08:50 세 슬롯.
  · 스냅샷마다 price-data 브랜치를 덮어쓰고(v176 규약: 항상 커밋 1개) pages.yml 을
    workflow_dispatch 로 깨운다. 실행이 안 끝나므로 workflow_run(완료 구독)은 못 쓴다.
    GITHUB_TOKEN 이 만드는 이벤트 중 workflow_dispatch·repository_dispatch 만
    예외적으로 새 실행을 만든다(공식 문서).
  · 한 실행은 6시간 상한 — 12:26 에 오후 실행으로 넘긴다(자기 자신을 dispatch).
  · 동시성 그룹(price)이 하나만 돌게 한다. 예비 슬롯(매시 :20·:50)은 대기했다가
    폴러가 죽었을 때만 이어받고, 이어받은 실행은 자기 구간 끝까지 폴링한다.
  · 배포 깨우기가 실패하면 **즉시 종료**한다 — 실행이 끝나면 workflow_run 배포가
    대신 뜨고, 다음 슬롯이 새로 시작한다. 즉 종전(슬롯당 1회) 방식으로 저절로 물러선다.

★ 전략 무접촉: price_now.py 와 같다 — 표시 전용, 판정은 QQQ 미국 종가만(동결).
  실패는 사고가 아니다 — 항상 exit 0, 파일을 지어내지 않는다.

실행: python deploy/price_poll.py --mode poll|once [--dry-run] [--cycles N] [--selftest]
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone, time as dtime

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import price_now  # noqa: E402 — 같은 수집·같은 파일 규약을 그대로 쓴다

KST = timezone(timedelta(hours=9))
OPEN = dtime(9, 0, 20)       # 첫 스냅샷: 개장 20초 뒤 (동시호가 체결이 시세에 실린 뒤)
SPLIT = dtime(12, 26, 0)     # 오전 실행이 오후 실행에 넘기는 시각 (6시간 상한 대비)
DAY_END = dtime(15, 56, 0)   # 마지막 스냅샷 15:55 — 종전 예약(~15:55)과 같은 끝
STEP = 300                   # 5분
OFFSET = 20                  # 매 5분 경계 + 20초
HOLI = os.path.join(ROOT, 'data', 'kr_holidays.json')
PRICE = price_now.OUT        # data/price.json
BRANCH = 'price-data'


def log(msg):
    print(f'[{datetime.now(KST):%H:%M:%S}] {msg}', flush=True)


def at(d, t):
    return datetime.combine(d, t, tzinfo=KST)


def load_holidays():
    try:
        return set(json.load(io.open(HOLI, encoding='utf-8'))['holidays'])
    except Exception:
        return set()


def is_trading_day(d, holidays=None):
    if d.weekday() >= 5:
        return False
    if holidays is None:
        holidays = load_holidays()
    return d.isoformat() not in holidays


def phase_end(now):
    """이 실행이 폴링을 멈출 시각. 오전 실행은 SPLIT, 오후 실행은 DAY_END."""
    d = now.date()
    return at(d, SPLIT) if now < at(d, SPLIT) else at(d, DAY_END)


def next_slot(now):
    """now 뒤에 오는 첫 「5분 경계 + OFFSET」."""
    base = now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)
    cand = base + timedelta(seconds=OFFSET)
    while cand <= now:
        cand += timedelta(seconds=STEP)
    return cand


def sleep_until(t):
    while True:
        s = (t - datetime.now(KST)).total_seconds()
        if s <= 0:
            return
        time.sleep(min(s, 600))


# ── 스냅샷 · 브랜치 · 배포 ─────────────────────────────────────────────
def snapshot():
    """price_now 와 같은 수집·같은 파일 규약. 실패하면 None (파일은 안 건드린다)."""
    try:
        doc = price_now.build(price_now.fetch())
    except Exception as e:
        log(f'수집 실패({e}) — 이번 슬롯 건너뜀')
        return None
    if not doc['items']:
        log('대상 종목 0건 — 이번 슬롯 건너뜀')
        return None
    os.makedirs(os.path.dirname(PRICE), exist_ok=True)
    with io.open(PRICE, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    return doc


def branch_items():
    """price-data 브랜치의 현재 스냅샷 items (없으면 None).
    값이 그대로면 브랜치·배포까지 헛돌 이유가 없다 — v176 의 같은 비교."""
    try:
        subprocess.run(['git', 'fetch', '-q', '--depth=1', 'origin', BRANCH], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        raw = subprocess.run(['git', 'show', 'FETCH_HEAD:data/price.json'], cwd=ROOT, check=True,
                             capture_output=True, timeout=30).stdout
        return json.loads(raw.decode('utf-8')).get('items')
    except Exception:
        return None


def publish(dry=False):
    """price-data 브랜치를 **항상 커밋 1개**로 덮어쓴다(v176 규약).
    본 체크아웃은 건드리지 않는다 — 임시 저장소에 data/price.json 하나만 넣어 force-push."""
    if dry:
        log('(dry-run) 브랜치 갱신 생략')
        return True
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not (token and repo):
        log('토큰·저장소 환경변수 없음 — 브랜치 갱신 불가')
        return False
    d = tempfile.mkdtemp(prefix='price-data-')
    try:
        os.makedirs(os.path.join(d, 'data'))
        shutil.copy(PRICE, os.path.join(d, 'data', 'price.json'))

        def g(*a):
            return subprocess.run(['git', *a], cwd=d, check=True, capture_output=True, timeout=120)
        g('init', '-q')
        g('config', 'user.name', 'github-actions[bot]')
        g('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
        g('add', '-A')
        g('commit', '-q', '-m', f'price: {datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ} 스냅샷 (항상 커밋 1개)')
        g('push', '-qf', f'https://x-access-token:{token}@github.com/{repo}.git', f'HEAD:refs/heads/{BRANCH}')
        return True
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b'').decode('utf-8', 'replace').replace(token, '***')
        log(f'브랜치 갱신 실패: {err.strip()[:300]}')
        return False
    finally:
        shutil.rmtree(d, ignore_errors=True)


def gh(*args):
    r = subprocess.run(['gh', *args], cwd=ROOT, capture_output=True, timeout=60)
    return r.returncode == 0, (r.stderr or b'').decode('utf-8', 'replace').strip()[:300]


def wake_pages(dry=False):
    """pages.yml 을 workflow_dispatch 로 깨운다. 실패하면 False — 호출자가 종료해
    workflow_run 배포로 물러선다."""
    if dry:
        log('(dry-run) 배포 깨우기 생략')
        return True
    ok, err = gh('workflow', 'run', 'pages.yml', '--ref', 'main')
    if not ok:
        log(f'배포 깨우기 실패: {err}')
    return ok


def handover(dry=False):
    """오전 실행 → 오후 실행. 동시성 그룹이 하나만 돌게 하므로 이 실행이 끝난 뒤 시작된다."""
    if dry:
        log('(dry-run) 오후 실행 인계 생략')
        return
    ok, err = gh('workflow', 'run', 'price.yml', '--ref', 'main', '-f', 'mode=poll')
    log('오후 실행 인계 요청함' if ok else f'오후 실행 인계 실패({err}) — 예비 슬롯(매시 :20·:50)이 이어받는다')


def cycle(last_items, dry):
    """스냅샷 1회: 수집 → 값이 바뀌었으면 브랜치 덮어쓰기 → 배포 깨우기.
    반환 (items, ok). ok=False 면 배포 경로가 막힌 것 — 호출자가 종료한다."""
    doc = snapshot()
    if doc is None:
        return last_items, True
    log(f"{doc['as_of_kst']} · {len(doc['items'])}종목 · "
        + ' '.join(f"{c}={r['px']:,}" for c, r in doc['items'].items()))
    if doc['items'] == last_items:
        log('시세 변화 없음 — 브랜치·배포 생략')
        return last_items, True
    if not publish(dry):
        return last_items, False
    if not wake_pages(dry):
        return doc['items'], False
    return doc['items'], True


# ── 검산 (네트워크 0) ────────────────────────────────────────────────────
def selftest():
    from datetime import date
    d = date(2026, 9, 2)                              # 수요일 · 거래일
    T = lambda h, m, s=0: at(d, dtime(h, m, s))       # noqa: E731
    assert phase_end(T(8, 40)) == T(12, 26)
    assert phase_end(T(12, 25, 59)) == T(12, 26)
    assert phase_end(T(12, 26)) == T(15, 56)
    assert phase_end(T(15, 55, 20)) == T(15, 56)
    assert next_slot(T(9, 0, 19)) == T(9, 0, 20)
    assert next_slot(T(9, 0, 20)) == T(9, 5, 20)
    assert next_slot(T(9, 4, 59)) == T(9, 5, 20)
    assert next_slot(T(12, 25, 20)) == T(12, 30, 20)
    assert next_slot(T(10, 37, 3)) == T(10, 40, 20)
    hol = {'2026-10-09'}
    assert is_trading_day(date(2026, 9, 2), hol) is True
    assert is_trading_day(date(2026, 9, 5), hol) is False    # 토
    assert is_trading_day(date(2026, 9, 6), hol) is False    # 일
    assert is_trading_day(date(2026, 10, 9), hol) is False   # 한글날
    # 하루 시뮬레이션: 08:40 에 뜬 오전 실행 + 12:26 에 이어받는 오후 실행
    #   = 정렬 슬롯 84개(종전 `*/5` 와 같은 수) + 인계 실행이 시작 즉시 찍는 1개
    shots = []
    for start in (T(8, 40), T(12, 26, 5)):
        now = start
        end = phase_end(now)
        if now < T(9, 0, 20):
            now = T(9, 0, 20)
        while True:
            shots.append(now)
            nxt = next_slot(now)
            if nxt >= end:
                break
            now = nxt
    assert len(shots) == 85, len(shots)
    assert shots[0] == T(9, 0, 20) and shots[41] == T(12, 25, 20)
    assert shots[42] == T(12, 26, 5) and shots[43] == T(12, 30, 20) and shots[-1] == T(15, 55, 20)
    assert len(set(shots)) == 85
    # 이어받기: 10:37 에 뜬 예비 실행은 즉시 한 번 찍고 10:40:20 부터 정렬
    now = T(10, 37, 3)
    assert phase_end(now) == T(12, 26) and next_slot(now) == T(10, 40, 20)
    # 폴러가 15:56 뒤에 뜨면 아무것도 안 한다 (main 이 DAY_END 검사)
    assert T(15, 56) >= at(d, DAY_END)
    print('selftest OK — 구간·정렬·휴장·하루 85스냅샷(정렬 84 + 인계 1) 검산 통과')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['poll', 'once'], default='once')
    ap.add_argument('--dry-run', action='store_true', help='수집·파일 쓰기만 — push·배포·인계 없음')
    ap.add_argument('--cycles', type=int, default=0, help='(시험용) 이 횟수만 찍고 멈춤')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    now = datetime.now(KST)
    if a.mode == 'once':
        cycle(branch_items(), a.dry_run)
        return 0

    if not is_trading_day(now.date()):
        log(f'{now:%Y-%m-%d} 휴장 — 종료')
        return 0
    if now >= at(now.date(), DAY_END):
        log('장 마감 후 — 종료')
        return 0
    end = phase_end(now)
    start = at(now.date(), OPEN)
    if now < start:
        log(f'개장 전 — {start:%H:%M:%S} 까지 {(start - now).total_seconds():.0f}초 대기')
        sleep_until(start)
    log(f'폴링 시작 — {end:%H:%M} 까지 5분마다')
    last = branch_items()
    n = 0
    while True:
        last, ok = cycle(last, a.dry_run)
        n += 1
        if not ok:
            log('배포 경로가 막혀 종료 — 실행이 끝나면 workflow_run 배포가 대신 뜨고, 다음 슬롯이 다시 시작한다')
            return 0
        if a.cycles and n >= a.cycles:
            log('시험 횟수 도달 — 종료')
            return 0
        nxt = next_slot(datetime.now(KST))
        if nxt >= end:
            break
        sleep_until(nxt)
    if end < at(now.date(), DAY_END):
        handover(a.dry_run)
    log('구간 끝 — 종료')
    return 0


if __name__ == '__main__':
    sys.exit(main())
