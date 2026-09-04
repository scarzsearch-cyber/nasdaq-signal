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


def load_holidays(for_date=None):
    """검증된 한국장 휴장일만 반환한다.

    달력을 못 읽었는데 평일로 간주하면 휴장일의 전일 종가를 새 시각으로 계속
    발행해 화면에 거짓 신선도를 만든다. 모르면 폴링하지 않는 쪽이 안전하다.
    """
    if not os.path.exists(HOLI):
        raise RuntimeError('kr_holidays.json 이 없다 — 시세 날짜를 판정할 수 없음')
    try:
        doc = json.load(io.open(HOLI, encoding='utf-8'))
    except Exception as e:
        raise RuntimeError('kr_holidays.json 파싱 실패') from e
    if (not isinstance(doc, dict) or not isinstance(doc.get('range'), list)
            or len(doc['range']) != 2 or not isinstance(doc.get('holidays'), dict)):
        raise RuntimeError('kr_holidays.json 구조가 잘못됨')
    try:
        y0, y1 = (int(doc['range'][0]), int(doc['range'][1]))
        if y0 > y1:
            raise ValueError
        dates = list(doc['holidays'])
        parsed = [datetime.strptime(s, '%Y-%m-%d').date() for s in dates]
        if any(d.isoformat() != s or not (y0 <= d.year <= y1)
               for s, d in zip(dates, parsed)):
            raise ValueError
    except Exception as e:
        raise RuntimeError('kr_holidays.json 날짜·범위를 해석할 수 없음') from e
    if for_date is not None and not (y0 <= for_date.year <= y1):
        raise RuntimeError('kr_holidays.json 범위 밖 날짜 — 시세 폴링 중단')
    return set(dates)


def is_trading_day(d, holidays=None):
    if d.weekday() >= 5:
        return False
    if holidays is None:
        holidays = load_holidays(d)
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
    """price_now와 같은 규약으로 수집한다. 실패는 폴러의 연속 실패 계수로 올린다."""
    try:
        doc = price_now.build(price_now.fetch())
    except Exception as e:
        raise RuntimeError(f'수집 실패({type(e).__name__}: {e})') from e
    if not doc['items']:
        raise RuntimeError('대상 종목 0건')
    price_now.atomic_json_write(PRICE, doc)
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

        # [2026-09-04 코드리뷰] GIT_TERMINAL_PROMPT=0 — 자격증명이 거부되면 git 이
        # 프롬프트를 띄우고 timeout 까지 매달린다. 러너엔 터미널이 없으니 즉시 실패가 옳다.
        genv = dict(os.environ, GIT_TERMINAL_PROMPT='0')

        def g(*a):
            return subprocess.run(['git', *a], cwd=d, check=True, capture_output=True,
                                  timeout=120, env=genv)
        g('init', '-q')
        g('config', 'user.name', 'github-actions[bot]')
        g('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
        g('add', '-A')
        g('commit', '-q', '-m', f'price: {datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ} 스냅샷 (항상 커밋 1개)')
        g('push', '-qf', f'https://x-access-token:{token}@github.com/{repo}.git', f'HEAD:refs/heads/{BRANCH}')
        return True
    # [2026-09-04 코드리뷰] ★ 종전엔 CalledProcessError 만 잡았다. push 가 120초를 넘기면
    #   subprocess.TimeoutExpired 가 나는데 그 예외의 문자열에는 **실행한 명령줄 전체**가
    #   들어간다 — 즉 push URL 의 `x-access-token:<토큰>` 이 그대로 Actions 로그에 찍힌다.
    #   (GitHub 의 secret 마스킹은 이 토큰을 모른다: GITHUB_TOKEN 은 러너가 주입한 값이라
    #   ***로 가려지지만 GH_TOKEN 으로 넣은 PAT 는 등록 secret 이름과 값이 다를 수 있고,
    #   무엇보다 마스킹에 기대는 것이 방어가 아니다.) 5분마다 도는 경로라 노출 기회도 많다.
    #   → 예외 종류를 가리지 않고 잡고, 토큰 문자열을 지운 뒤에만 찍는다.
    except Exception as e:
        raw = (getattr(e, 'stderr', None) or b'')
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', 'replace')
        err = (raw or f'{type(e).__name__}: {e}').replace(token, '***')
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
    # UTC 일~목 23시가 KST 월~금 08시가 되는지 확인한다. 월요일 슬롯 누락 방지.
    assert datetime(2026, 8, 30, 23, 30, tzinfo=timezone.utc).astimezone(KST).weekday() == 0
    assert datetime(2026, 9, 3, 23, 50, tzinfo=timezone.utc).astimezone(KST).weekday() == 4
    # 달력을 모르면 휴장일을 거래일로 지어내지 않는다.
    real_holi = globals()['HOLI']
    with tempfile.TemporaryDirectory(prefix='price_holiday_') as td:
        test_holi = os.path.join(td, 'kr_holidays.json')
        globals()['HOLI'] = test_holi
        try:
            for label, payload in (
                    ('missing', None), ('broken', '{broken'),
                    ('range', json.dumps({'range': [2025, 2025], 'holidays': {}}))):
                if payload is None:
                    if os.path.exists(test_holi):
                        os.unlink(test_holi)
                else:
                    with io.open(test_holi, 'w', encoding='utf-8') as f:
                        f.write(payload)
                try:
                    is_trading_day(date(2026, 9, 2))
                    raise AssertionError(f'{label} 휴장 달력을 거래일로 허용했다')
                except RuntimeError:
                    pass
        finally:
            globals()['HOLI'] = real_holi
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

    # 실제 snapshot 실패가 cycle 바깥으로 전파돼 main의 연속 실패 계수에 닿아야 한다.
    real_fetch = price_now.fetch
    try:
        price_now.fetch = lambda: (_ for _ in ()).throw(OSError('HTTP 실패 모의'))
        try:
            cycle(None, True)
            raise AssertionError('수집 실패를 성공 슬롯으로 삼켰다')
        except RuntimeError:
            pass
    finally:
        price_now.fetch = real_fetch

    # 외부 JSON 이 bool·NaN·Infinity 를 숫자로 돌려도 표시 파일에 실리지 않아야 한다.
    # Python json.dumps 기본값은 NaN 토큰을 허용하지만 브라우저 JSON.parse 는 거부한다.
    malformed = [
        {'itemcode': '418660', 'itemname': 'NaN 가격', 'nowVal': float('nan')},
        {'itemcode': '458730', 'itemname': float('nan'), 'nowVal': 10000,
         'nav': float('inf'), 'changeVal': float('nan'), 'changeRate': True,
         'quant': -1},
        {'itemcode': '305080', 'itemname': '불리언 가격', 'nowVal': True},
    ]
    clean = price_now.build(malformed)
    assert set(clean['items']) == {'458730'}
    clean_row = clean['items']['458730']
    assert clean_row['name'] == ''
    assert clean_row['chg'] is None and clean_row['chg_pct'] is None
    assert clean_row['volume'] is None and 'nav' not in clean_row
    json.dumps(clean, allow_nan=False)
    assert price_now._plausible({'itemcode': '418660', 'nowVal': True}) is False
    import kr_sources
    assert kr_sources._num(True) is None
    assert kr_sources._num(float('nan')) is None
    assert kr_sources._num(float('inf')) is None
    try:
        kr_sources._item('418660', float('nan'))
        raise AssertionError('NaN 가격을 예비 시세로 허용했다')
    except ValueError:
        pass

    # 직렬화나 쓰기가 실패해도 마지막 정상 스냅샷은 바이트 단위로 보존한다.
    with tempfile.TemporaryDirectory(prefix='price_atomic_') as td:
        target = os.path.join(td, 'price.json')
        with open(target, 'wb') as f:
            f.write(b'SENTINEL')
        try:
            price_now.atomic_json_write(target, {'bad': float('nan')})
            raise AssertionError('비표준 JSON 값이 저장됐다')
        except ValueError:
            pass
        with open(target, 'rb') as f:
            assert f.read() == b'SENTINEL'

    # workflow_dispatch 기본 once도 거래일 달력과 장중 경계를 우회하지 않는다.
    # 누락·손상·범위 밖 달력, 휴일, 개장 전·마감 뒤에는 cycle이 한 번도 불리지 않는다.
    real_holi = globals()['HOLI']
    real_cycle = globals()['cycle']
    real_branch_items = globals()['branch_items']
    calls = []
    with tempfile.TemporaryDirectory(prefix='price_once_') as td:
        once_holi = os.path.join(td, 'kr_holidays.json')
        globals()['HOLI'] = once_holi
        globals()['cycle'] = lambda *args, **kwargs: calls.append((args, kwargs)) or (None, True)
        globals()['branch_items'] = lambda: {'before': True}
        try:
            # 파일 없음·파싱 실패·범위 밖은 모두 발행 없이 종료한다.
            assert main(['--mode', 'once', '--dry-run'], now=T(10, 0)) == 0
            with io.open(once_holi, 'w', encoding='utf-8') as f:
                f.write('{broken')
            assert main(['--mode', 'once', '--dry-run'], now=T(10, 0)) == 0
            with io.open(once_holi, 'w', encoding='utf-8') as f:
                json.dump({'range': [2025, 2025], 'holidays': {}}, f)
            assert main(['--mode', 'once', '--dry-run'], now=T(10, 0)) == 0

            with io.open(once_holi, 'w', encoding='utf-8') as f:
                json.dump({'range': [2026, 2026],
                           'holidays': {'2026-09-02': '합성 휴장일'}}, f)
            assert main(['--mode', 'once', '--dry-run'], now=T(10, 0)) == 0
            with io.open(once_holi, 'w', encoding='utf-8') as f:
                json.dump({'range': [2026, 2026], 'holidays': {}}, f)
            assert main(['--mode', 'once', '--dry-run'], now=T(8, 59)) == 0
            assert main(['--mode', 'once', '--dry-run'], now=T(15, 56)) == 0
            assert calls == []
            assert main(['--mode', 'once', '--dry-run'], now=T(10, 0)) == 0
            assert len(calls) == 1

            # 수집 예외를 snapshot/cycle이 삼켜 성공으로 바꾸면 이 3회 종료 계약은
            # 도달 불가다. 진입점에서 연속 실패는 3회 뒤 종료하고, 1~2회 뒤 성공은 회복한다.
            failed = []
            def always_fail(*args, **kwargs):
                failed.append(1)
                raise RuntimeError('수집 실패 모의')
            globals()['cycle'] = always_fail
            assert main(['--mode', 'poll', '--dry-run'], now=T(10, 0),
                        clock=lambda: T(10, 0), sleeper=lambda target: None) == 0
            assert len(failed) == 3

            attempts = []
            def recover_third(*args, **kwargs):
                attempts.append(1)
                if len(attempts) < 3:
                    raise RuntimeError('일시 실패 모의')
                return {'after': True}, True
            globals()['cycle'] = recover_third
            assert main(['--mode', 'poll', '--dry-run', '--cycles', '3'], now=T(10, 0),
                        clock=lambda: T(10, 0), sleeper=lambda target: None) == 0
            assert len(attempts) == 3
        finally:
            globals()['HOLI'] = real_holi
            globals()['cycle'] = real_cycle
            globals()['branch_items'] = real_branch_items
    print('selftest OK — 구간·정렬·휴장·once 관문·유한 시세·원자 저장·수집 3회 실패·하루 85스냅샷 검산 통과')
    return 0


def main(argv=None, now=None, clock=None, sleeper=sleep_until):
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['poll', 'once'], default='once')
    ap.add_argument('--dry-run', action='store_true', help='수집·파일 쓰기만 — push·배포·인계 없음')
    ap.add_argument('--cycles', type=int, default=0, help='(시험용) 이 횟수만 찍고 멈춤')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    clock = clock or (lambda: datetime.now(KST))
    now = clock() if now is None else now
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    else:
        now = now.astimezone(KST)
    try:
        trading_day = is_trading_day(now.date())
    except RuntimeError as e:
        log(f'휴장일 표 검증 실패({e}) — 시세 발행 없이 종료')
        return 0
    if not trading_day:
        log(f'{now:%Y-%m-%d} 휴장 — 종료')
        return 0
    if now >= at(now.date(), DAY_END):
        log('장 마감 후 — 종료')
        return 0
    start = at(now.date(), OPEN)
    if a.mode == 'once':
        # 수동 기본값도 검증된 거래일의 장중에만 현재 시각을 붙인다. 장외 quote는
        # 전일 종가일 수 있어 새 as_of_kst로 발행하면 화면에 거짓 신선도를 만든다.
        if now < start:
            log('개장 전 — 수동 1회 시세 발행 없이 종료')
            return 0
        try:
            cycle(branch_items(), a.dry_run)
        except Exception as e:
            log(f'수동 스냅샷 실패: {type(e).__name__}: {str(e)[:200]}')
        return 0

    end = phase_end(now)
    if now < start:
        log(f'개장 전 — {start:%H:%M:%S} 까지 {(start - now).total_seconds():.0f}초 대기')
        sleeper(start)
    log(f'폴링 시작 — {end:%H:%M} 까지 5분마다')
    last = branch_items()
    n = 0
    # [2026-09-04 코드리뷰] cycle() 안에서 예외가 하나만 나도 6시간짜리 폴러가 통째로
    # 죽었다(수집 HTTP 오류·git 타임아웃 등). 예비 슬롯(매시 :20·:50)이 이어받으므로
    # 사고까지는 아니지만 **일시적 오류 하나에 최대 30분치 시세가 빈다.**
    # → 한 번의 실패로는 안 죽고 다음 슬롯에서 다시 해 본다. 연속 3회면 그때 종료해
    #   예비 슬롯에 넘긴다(계속 붙들고 헛돌면 예비가 못 들어온다 — 동시성 그룹이 하나다).
    consec = 0
    while True:
        try:
            last, ok = cycle(last, a.dry_run)
            consec = 0
        except Exception as e:
            consec += 1
            log(f'스냅샷 실패({consec}/3): {type(e).__name__}: {str(e)[:200]}')
            if consec >= 3:
                log('연속 3회 실패 — 종료하고 예비 슬롯에 넘긴다')
                return 0
            ok = True                      # 배포 경로가 막힌 것은 아니다 — 다음 슬롯에서 재시도
        n += 1
        if not ok:
            log('배포 경로가 막혀 종료 — 실행이 끝나면 workflow_run 배포가 대신 뜨고, 다음 슬롯이 다시 시작한다')
            return 0
        if a.cycles and n >= a.cycles:
            log('시험 횟수 도달 — 종료')
            return 0
        nxt = next_slot(clock())
        if nxt >= end:
            break
        sleeper(nxt)
    if end < at(now.date(), DAY_END):
        handover(a.dry_run)
    log('구간 끝 — 종료')
    return 0


if __name__ == '__main__':
    sys.exit(main())
