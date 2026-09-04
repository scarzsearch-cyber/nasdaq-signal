#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v75] 종가 확정 대기 루프 — "새벽 5시(미 종가) ~ 아침 9시(한국 개장) 안 반영" 보장 강화.
[v190] 마감 **전**에 떠서 마감 순간을 잡는다 — 「마감 뒤 5분 안 반영」.

문제: GitHub 예약 실행은 슬롯을 통째로 건너뛴다 (실측: 8/26 3슬롯 전부, 8/29 06:17·06:47).
     슬롯을 늘려도 '떠야 도는' 구조는 그대로다.
해법: **슬롯 하나만 떠도** 이 루프가 예상 종가가 반영될 때까지 몇 분 간격으로 재시도한다.
     트리거(05:17/06:17/07:47/09:17 KST + [v190] 04:35·04:45·05:35·05:45) 중 하나라도
     뜨면 창 전체가 커버된다.

[v190] 왜 마감 전에 뜨나 (2026-09-02 소유자: 「미국 종가가 05:25 에 반영된다 — 정시 5분 안에 안 되나」):
  첫 슬롯이 05:17 KST 라 마감(05:00, 서머타임) 뒤 17분은 구조적으로 늦고, 거기에 예약 지연
  4~9분(실측 09-01 05:20 · 09-02 05:25)이 얹혔다. 예약 지연은 우리가 못 줄인다 — 그래서
  마감 25분 **전** 슬롯(04:35·04:45 KST)에 떠서 마감까지 자고, 마감 뒤엔 20초 간격으로
  종가가 굳는 순간(regularMarketTime ≥ 마감 시각)을 잡는다. 겨울(마감 06:00)엔 같은 슬롯이
  85분 기다린다(상한 100분 안). 마감 뒤 8분이 지나도 안 굳으면 휴장일이거나 소스 지연이므로
  조용히 끝내고 다음 슬롯에 맡긴다 — 이 파일이 새로 실패를 만들지는 않는다.
  ★ 종가를 **쓰기 전**에 30초 뒤 한 번 더 읽어 같은 값인지 본다(마감 직후 정정 대비).
  ★ 큰 움직임(|등락| > update_signal.BIG_MOVE)이면 대조 소스(네이버)가 CLOSE 가 될 때까지
    최대 15분 기다린다 — v137 가드의 교차 대조가 「아직 안 닫힘」으로 헛돌지 않게.
    15분 뒤에도 안 닫히면 가드 자신의 규약대로 통과시킨다(fail open).

동작:
  1. 예상 종가 날짜 = Yahoo meta 의 regularMarketTime (마지막 세션 마감 시각) 의 날짜.
     마감 후에는 이 값이 마감 시각으로 굳으므로 주말·휴장에도 자동으로 맞다
     (휴장일: 예상 = 직전 거래일 = 이미 반영됨 → 즉시 종료. 헛돌지 않는다).
  2. signal.json 의 as_of = 예상이면 **아무것도 안 하고** 종료 — 신선한 날엔
     signal.json 을 다시 쓰지 않으므로 의미 없는 커밋도 안 생긴다.
  3. 아니면 update_signal.py 실행 → 재확인 → 될 때까지 240초 간격, 최대 170분.
  4. 시한 초과 시 종료코드 1 (workflow 실패 → notify 알림).

로컬 확인:  python3 deploy/wait_close.py             (실제 조회)
            python3 deploy/wait_close.py --selftest   (가짜 시계·가짜 시세로 대기 논리 검산, 네트워크 0)
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
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

SIG = os.path.join('data', 'signal.json')
MAX_MIN = 170          # 다음 트리거와 겹치기 직전까지
SLEEP = 240
# [v190] 마감 전 대기 규약
WAIT_CAP = 100 * 60    # 마감까지 이보다 멀면 기다리지 않는다 (겨울 04:35 슬롯 = 85분이 최장)
FAST_SLEEP = 20        # 마감 직후 폴링 간격
FAST_MAX = 8 * 60      # 마감 뒤 이만큼 지나도 안 굳으면 종료 (휴장일·소스 지연 — 다음 슬롯이 맡는다)
SETTLE = 30            # 굳은 종가를 30초 뒤 한 번 더 읽어 같은 값인지 (최대 5회)
XSRC_WAIT = 15 * 60    # 큰 움직임일 때 대조 소스(네이버)가 닫힐 때까지 기다리는 상한
META_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/QQQ?range=1d&interval=1d'


def _upd():
    """update_signal 의 상수(BIG_MOVE·NAVER_SRC)를 그대로 쓴다 — 값을 두 곳에 두지 않는다."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import update_signal
    return update_signal


def fetch_meta():
    req = urllib.request.Request(META_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        meta = json.loads(r.read())['chart']['result'][0]['meta']
    return {'qt': meta.get('regularMarketTime'),
            # [2026-09-04 코드리뷰] start 도 싣는다 — 마감 판별이 update_signal.in_session 과
            # 같은 규칙을 쓰려면 필요하다(기간이 다음 세션으로 롤오버한 경우를 가른다).
            'start': meta.get('currentTradingPeriod', {}).get('regular', {}).get('start'),
            'end': meta.get('currentTradingPeriod', {}).get('regular', {}).get('end'),
            'price': meta.get('regularMarketPrice'),
            'prev': meta.get('chartPreviousClose')}


def closed(meta):
    """마감했는가 — **update_signal.in_session() 과 같은 규칙**을 쓴다(두 벌이면 갈린다).

    [2026-09-04 코드리뷰] 종전엔 `qt >= end` 였다. currentTradingPeriod 가 다음 세션으로
    넘어가면 qt 는 오늘 마감에 굳어 있는데 end 가 내일 마감이라 **이미 끝난 장을 「아직」으로**
    본다 — 그러면 이 스크립트는 오지 않을 마감을 기다리다 8분 시한에 걸려 조용히 끝난다.
    실측 2026-09-03 ^KS11·418660.KS 에서 그 롤오버를 확인했다.
    """
    return bool(meta.get('qt')) and bool(meta.get('end')) and not _in_session(meta)


def _in_session(meta):
    """update_signal.in_session() 을 이 파일의 meta 모양으로 부른다 — 규칙은 한 곳에만 둔다."""
    return _upd().in_session({'regularMarketTime': meta.get('qt'),
                             'currentTradingPeriod': {'regular': {
                                 'start': meta.get('start'), 'end': meta.get('end')}}})


def expected_close_date(meta):
    """마지막으로 **마감된** 미국 세션의 날짜 (UTC 날짜 = ET 날짜, 마감시각 기준)."""
    if not meta.get('qt'):
        return None
    # [2026-09-04 코드리뷰] 장중 판별을 closed() 와 **같은 규칙**으로 갈았다(종전엔 두 벌).
    # ★ 단 조건은 `not closed()` 가 아니라 `in_session()` 이다 — meta 가 불완전하면(end 없음)
    #   「장중」이라 단정하지 않고 날짜를 돌려줘 **갱신을 시도한다.** 그쪽이 v137 fail open:
    #   인프라가 부실할 때 신호 갱신을 건너뛰는 것이 가장 나쁘다.
    if _in_session(meta):
        # 장중 — 오늘 종가는 아직 없다. 예상 = 직전 세션 (as_of 가 이미 그 값이면 신선)
        return 'IN_SESSION'
    return datetime.fromtimestamp(meta['qt'], timezone.utc).strftime('%Y-%m-%d')


def naver_closed():
    req = urllib.request.Request(_upd().NAVER_SRC, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8', 'replace')).get('marketStatus') == 'CLOSE'


def wait_for_close(meta, now=time.time, sleep=time.sleep, refetch=fetch_meta,
                   xsrc_closed=naver_closed, big_move=None):
    """[v190] 장중에 떴으면 마감까지 자고, 마감 뒤엔 종가가 굳을 때까지 짧게 폴링한다.
    반환 (meta, why) — meta 가 None 이면 이번 실행은 조용히 끝낸다(why 가 이유).
    시계·수면·조회를 인자로 받는 것은 --selftest 가 가짜로 바꿔 끼우기 위해서다."""
    if closed(meta):
        return meta, '이미 마감'
    if not (meta.get('qt') and meta.get('end')):
        return meta, 'meta 불완전 — 기존 루프로'
    remaining = meta['end'] - now()
    if remaining > WAIT_CAP:
        return None, (f'미국 장중 — 마감까지 {remaining / 60:.0f}분(대기 상한 {WAIT_CAP // 60}분 밖). '
                      f'직전 종가가 최신. 종료.')
    if remaining > 0:
        print(f'마감까지 {remaining / 60:.1f}분 — 마감 3초 뒤까지 대기', flush=True)
        sleep(remaining + 3)
    t0 = now()
    k = 0
    while True:
        try:
            meta = refetch()
            k += 1
        except Exception as e:
            print(f'  폴링: 조회 실패({e})', flush=True)
        if closed(meta):
            break
        if now() - t0 > FAST_MAX:
            return None, (f'마감 뒤 {FAST_MAX // 60}분이 지나도 종가가 안 굳음(휴장일이거나 소스 지연) — '
                          f'종료. 다음 슬롯이 맡는다.')
        sleep(FAST_SLEEP)
    print(f'종가 굳음 — 폴링 {k}회, 마감 뒤 {max(0, now() - meta["end"]):.0f}초 (price {meta.get("price")})',
          flush=True)
    # 안정 확인 — 쓰기 전에 30초 뒤 같은 값인지
    for i in range(5):
        sleep(SETTLE)
        try:
            m2 = refetch()
        except Exception as e:
            print(f'  안정 확인 {i + 1}: 조회 실패({e}) — 직전 값으로 진행', flush=True)
            break
        if closed(m2) and m2.get('price') == meta.get('price'):
            meta = m2
            print(f'안정 확인 — {SETTLE}초 뒤에도 같은 값', flush=True)
            break
        print(f'  안정 확인 {i + 1}: 값이 바뀜 {meta.get("price")} → {m2.get("price")} — 다시', flush=True)
        meta = m2
    # 큰 움직임 — v137 가드가 대조할 소스가 닫힐 때까지
    if big_move is None:
        big_move = _upd().BIG_MOVE
    p, pv = meta.get('price'), meta.get('prev')
    if p and pv and abs(p / pv - 1) > big_move:
        print(f'큰 움직임 {p / pv - 1:+.2%} — 대조 소스가 닫힐 때까지 최대 {XSRC_WAIT // 60}분 대기', flush=True)
        t1 = now()
        while now() - t1 < XSRC_WAIT:
            try:
                if xsrc_closed():
                    print('대조 소스 CLOSE — 진행', flush=True)
                    break
            except Exception as e:
                print(f'  대조 소스 조회 실패({e})', flush=True)
            sleep(30)
        else:
            print('대조 소스가 안 닫힘 — 가드 규약대로 통과(fail open)', flush=True)
    return meta, '마감 확인'


def current_as_of():
    if not os.path.exists(SIG):
        return ''
    try:
        return json.load(open(SIG, encoding='utf-8')).get('as_of', '')
    except Exception:
        return ''


def as_of_is_current(cur, expected):
    """예상일과 정확히 같은 날만 최신이다. 미래 날짜는 성공이 아니라 손상이다."""
    if not cur:
        return False
    try:
        cur_day = datetime.strptime(cur, '%Y-%m-%d').date()
        exp_day = datetime.strptime(expected, '%Y-%m-%d').date()
    except (TypeError, ValueError) as e:
        raise ValueError(f'as_of/예상일이 YYYY-MM-DD가 아님: {cur!r}, {expected!r}') from e
    if cur_day.isoformat() != cur or exp_day.isoformat() != expected:
        raise ValueError(f'as_of/예상일이 YYYY-MM-DD 정규형이 아님: {cur!r}, {expected!r}')
    if cur_day > exp_day:
        raise ValueError(f'signal as_of {cur}가 예상 종가일 {expected}보다 미래임')
    return cur_day == exp_day


def validate_signal_as_of(cur, today=None):
    """장중 조기 종료 전에도 signal 날짜의 정규형·비미래 계약을 확인한다."""
    if not cur:
        return None
    try:
        parsed = datetime.strptime(cur, '%Y-%m-%d').date()
    except (TypeError, ValueError) as e:
        raise ValueError(f'signal as_of가 YYYY-MM-DD가 아님: {cur!r}') from e
    if parsed.isoformat() != cur:
        raise ValueError(f'signal as_of가 YYYY-MM-DD 정규형이 아님: {cur!r}')
    today = today or datetime.now(timezone.utc).date()
    if parsed > today:
        raise ValueError(f'signal as_of {cur}가 현재 날짜 {today}보다 미래임')
    return parsed


def main():
    # [v190] 장중에 떴으면 마감까지 기다린다 (조회 실패면 v75 루프가 그대로 맡는다)
    meta = None
    try:
        meta = fetch_meta()
    except Exception as e:
        print(f'[0] 시세 meta 조회 실패({e}) — 기존 루프로', file=sys.stderr)
    if meta is not None:
        meta, why = wait_for_close(meta)
        if meta is None:
            print(why)
            return
    t0 = time.time()       # 시한은 마감 확인 뒤부터 센다 (v75 와 같은 170분)
    n = 0
    while True:
        n += 1
        try:
            exp = expected_close_date(meta if (n == 1 and meta) else fetch_meta())
        except Exception as e:
            print(f'[{n}] 예상일 조회 실패({e}) — 재시도 대기', file=sys.stderr)
            exp = None
        cur = current_as_of()
        try:
            parsed_cur = validate_signal_as_of(cur)
        except ValueError as e:
            print(f'[{n}] 손상된 신호 날짜: {e}', file=sys.stderr)
            sys.exit(1)
        if exp == 'IN_SESSION':
            if parsed_cur is None:
                print(f'[{n}] 미국 장중인데 검증할 기존 signal as_of가 없음', file=sys.stderr)
                sys.exit(1)
            print(f'[{n}] 미국 장중 — 직전 종가({cur})가 최신. 종료.')
            return
        if exp:
            try:
                current = as_of_is_current(cur, exp)
            except ValueError as e:
                print(f'[{n}] 손상된 신호 날짜: {e}', file=sys.stderr)
                sys.exit(1)
            if current:
                print(f'[{n}] 이미 최신 (as_of {cur} = 예상 {exp}) — 갱신 없이 종료.')
                return
        print(f'[{n}] as_of {cur} < 예상 {exp or "?"} — 갱신 시도', flush=True)
        subprocess.call([sys.executable, os.path.join('deploy', 'update_signal.py')])
        cur = current_as_of()
        if exp:
            try:
                current = as_of_is_current(cur, exp)
            except ValueError as e:
                print(f'[{n}] 갱신 뒤 손상된 신호 날짜: {e}', file=sys.stderr)
                sys.exit(1)
            if current:
                print(f'[{n}] 종가 반영 완료: as_of {cur} (시도 {n}회, {int(time.time() - t0)}초)')
                return
        if (time.time() - t0) > MAX_MIN * 60:
            print(f'시한 {MAX_MIN}분 초과 — as_of {cur}, 예상 {exp}. 수동 확인 필요.',
                  file=sys.stderr)
            sys.exit(1)
        time.sleep(SLEEP)


# ── 검산 (네트워크 0) ────────────────────────────────────────────────────
def selftest():
    class Clock:
        def __init__(self, t):
            self.t = float(t)

        def now(self):
            return self.t

        def sleep(self, d):
            self.t += d

    def seq(*metas):
        it = iter(metas)
        last = [metas[-1]]

        def f():
            try:
                last[0] = next(it)
            except StopIteration:
                pass
            return last[0]
        return f

    END = 1_000_000
    live = {'qt': END - 1, 'end': END, 'price': 100.0, 'prev': 99.0}
    shut = {'qt': END, 'end': END, 'price': 100.5, 'prev': 99.0}
    shut2 = {'qt': END, 'end': END, 'price': 100.6, 'prev': 99.0}
    big = {'qt': END, 'end': END, 'price': 111.0, 'prev': 99.0}
    yes = lambda: True    # noqa: E731

    assert expected_close_date(live) == 'IN_SESSION'
    assert expected_close_date(shut) == '1970-01-12'
    assert as_of_is_current('2026-09-03', '2026-09-03')
    assert not as_of_is_current('2026-09-02', '2026-09-03')
    try:
        as_of_is_current('2026-09-04', '2026-09-03')
        raise AssertionError('미래 signal as_of를 최신으로 인정했다')
    except ValueError:
        pass
    assert validate_signal_as_of('2026-09-03', datetime(2026, 9, 4).date())
    try:
        validate_signal_as_of('2099-01-01', datetime(2026, 9, 4).date())
        raise AssertionError('장중 분기에서 미래 signal as_of를 허용했다')
    except ValueError:
        pass
    try:
        validate_signal_as_of('2026-9-3', datetime(2026, 9, 4).date())
        raise AssertionError('장중 분기에서 비정규 signal as_of를 허용했다')
    except ValueError:
        pass
    # [2026-09-04 코드리뷰] 기간 롤오버·프리마켓 — 종전 `qt < end` 는 둘 다 「장중」으로 오판했다.
    #   롤오버는 실측(2026-09-03 ^KS11·418660.KS)이고, 오판하면 이 스크립트가 이미 끝난 마감을
    #   기다리다 시한에 걸려 조용히 끝난다(= 그날 갱신 없음).
    DAY, SESS = 86400, 23400
    rolled = {'qt': END, 'start': END + DAY - SESS, 'end': END + DAY, 'price': 100.5, 'prev': 99.0}
    premkt = {'qt': END - DAY, 'start': END - SESS, 'end': END, 'price': 100.5, 'prev': 99.0}
    nostart = {'qt': END - 1, 'end': END, 'price': 100.5, 'prev': 99.0}    # 구형 meta
    assert closed(rolled) and expected_close_date(rolled) == '1970-01-12', '롤오버'
    assert closed(premkt) and expected_close_date(premkt) == '1970-01-11', '프리마켓'
    assert not closed(nostart) and expected_close_date(nostart) == 'IN_SESSION', 'start 없으면 종전 규칙'
    # meta 불완전(end 없음)은 **갱신을 시도해야 한다** — v137 fail open
    assert expected_close_date({'qt': END}) == '1970-01-12', 'end 없을 때 fail open'
    m, why = wait_for_close(rolled, now=lambda: END + 3600, sleep=None, refetch=None, xsrc_closed=yes, big_move=.1)
    assert m is rolled and why == '이미 마감', '롤오버는 즉시 마감 처리'
    # 0. 이미 마감이면 즉시
    m, why = wait_for_close(shut, now=lambda: END + 3600, sleep=None, refetch=None, xsrc_closed=yes, big_move=.1)
    assert m is shut and why == '이미 마감'
    # 1. 25분 전 시작 → 마감 3초 뒤 첫 조회에서 굳음 → 30초 안정 확인 → 총 25분 33초
    c = Clock(END - 25 * 60)
    m, why = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(shut), xsrc_closed=yes, big_move=.1)
    assert m is shut and why == '마감 확인' and c.t == END + 3 + SETTLE, c.t
    # 2. 상한 밖(3시간 전) → 기다리지 않고 None
    c = Clock(END - 3 * 3600)
    m, why = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(shut), xsrc_closed=yes, big_move=.1)
    assert m is None and '상한' in why
    # 2b. 겨울 04:35 슬롯 = 85분 전 → 기다린다
    c = Clock(END - 85 * 60)
    m, _ = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(shut), xsrc_closed=yes, big_move=.1)
    assert m is shut and c.t == END + 3 + SETTLE
    # 3. 휴장일(안 굳음) → 마감 뒤 8분에 None, 실패 없음
    c = Clock(END - 60)
    m, why = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(live), xsrc_closed=yes, big_move=.1)
    assert m is None and '안 굳음' in why and END + 8 * 60 < c.t <= END + 8 * 60 + FAST_SLEEP + 3, c.t
    # 4. 마감 10초 뒤 시작, 세 번째 조회에서 굳음 → 10 + 20 + 20 + 30
    c = Clock(END + 10)
    m, _ = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(live, live, shut), xsrc_closed=yes, big_move=.1)
    assert m is shut and c.t == END + 10 + 2 * FAST_SLEEP + SETTLE, c.t
    # 5. 안정 확인에서 값이 한 번 바뀜 → 두 번째 확인에서 굳음 (60초)
    c = Clock(END + 1)
    m, _ = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(shut, shut2, shut2), xsrc_closed=yes, big_move=.1)
    assert m is shut2 and c.t == END + 1 + 2 * SETTLE, c.t
    # 6. 조회 실패가 섞여도 진행 (폴링 1회 실패 뒤 굳음)
    calls = [0]

    def flaky():
        calls[0] += 1
        if calls[0] == 1:
            raise RuntimeError('timeout')
        return shut
    c = Clock(END + 1)
    m, _ = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=flaky, xsrc_closed=yes, big_move=.1)
    assert m is shut and c.t == END + 1 + FAST_SLEEP + SETTLE, c.t
    # 7. 큰 움직임 → 대조 소스가 닫힐 때까지 (두 번 미닫힘 → 60초 뒤 진행)
    xs = iter([False, False, True])
    c = Clock(END + 1)
    m, _ = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(big), xsrc_closed=lambda: next(xs), big_move=.1)
    assert m is big and c.t == END + 1 + SETTLE + 60, c.t
    # 8. 큰 움직임인데 끝내 안 닫힘 → 15분 뒤 fail open 으로 진행
    c = Clock(END + 1)
    m, why = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(big), xsrc_closed=lambda: False, big_move=.1)
    assert m is big and why == '마감 확인' and c.t == END + 1 + SETTLE + XSRC_WAIT, c.t
    # 9. 보통 움직임이면 대조 소스를 부르지 않는다
    def boom():
        raise AssertionError('대조 소스를 부르면 안 된다')
    c = Clock(END + 1)
    m, _ = wait_for_close(live, now=c.now, sleep=c.sleep, refetch=seq(shut), xsrc_closed=boom, big_move=.1)
    assert m is shut
    print('selftest OK — 날짜 일치·대기·폴링·안정 확인·휴장·큰 움직임 검산 통과')


if __name__ == '__main__':
    if '--selftest' in sys.argv[1:]:
        selftest()
    else:
        main()
