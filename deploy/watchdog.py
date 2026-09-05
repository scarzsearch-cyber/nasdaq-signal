#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v140] 자동 파수꾼 — 「아무 일도 안 일어난 것」을 감시한다.

기존 알림은 **워크플로가 돌다가 실패했을 때**만 온다(`if: failure()`).
그런데 실제로 무서운 것은 그 반대다:

  ① 워크플로가 **아예 안 돌아서** 신호가 며칠째 그대로인 경우
     → 실패가 아니므로 실패 알림이 안 온다. 화면을 안 열면 아무도 모른다.
     04 §5-8 실측: 큰 하락 초입의 방어 전환을 놓치면 최악 −96.5%.
  ② **알림 채널 자체가 죽은** 경우 (카카오 refresh 토큰 만료 등)
     → 지금까지 경고는 stderr 로만 나갔고 그 스텝은 continue-on-error 였다.
     정작 전환일에 카톡이 안 온다는 사실을 그날 알게 된다.
  ③ 분기 점검을 **사람이 기억해서** 돌려야 했던 것
     → 사람의 정기 의무를 0으로 만든다. 이상이 있을 때만 말한다.

전략 무접촉. 판정·파라미터·장부를 읽기만 하고 쓰지 않는다
(쓰는 것은 `data/ops_check.json` 하나 — 화면에 보여줄 점검 결과다).

  ④ 방어 재조정일을 **화면을 열어야만** 알 수 있던 것
     → 전환일엔 카톡이 가는데 30일 재조정일엔 안 갔다. 둘 다 「실제 매매」인데
     한쪽만 알림이 있으면 사람이 달력을 신경 써야 한다.

  ⑦ [v177] **전부 조용한 것이 정상인지 죽은 것인지 구별이 안 되던 것**
     → 위 알림은 전부 「이상할 때만」이다. 그래서 **침묵에 두 가지 뜻**이 있었다.
     특히 공개 저장소는 **60일간 활동이 없으면 예약 실행이 통째로 꺼지는데**(공식 문서)
     그러면 **파수꾼도 같이 꺼져** 「꺼졌다」고 말해 줄 것이 남지 않는다.
     한 달에 한 번 살아 있다고 말해 두면 **그것이 안 오는 것 자체가 신호**가 된다.

  ⑥ [v176] **시세 수집이 죽은** 경우 (price.yml / price-data 브랜치)
     → v176 부터 시세는 브랜치에만 있고, 못 읽으면 화면이 배지를 **숨긴다**
     (옛 값을 새 값인 척 안 보여주는 게 옳다). 다만 **「안 보이는 것」을 사람이
     알아챈다는 보장이 없다** — v173 에서 6시간 묵은 값을 아무도 못 본 것과 같다.

  ⑤ [v171] **성과 스냅샷이 안 갱신되는** 경우 (monthly-stats.yml 이 건너뜀)
     → ① 과 같은 구멍인데 **훨씬 안 보인다**: 신호는 매일이라 며칠만 밀려도
     화면 신선도 도트가 티를 내지만, 성과표는 월 1회라 두 달이 밀려도 화면이
     똑같아 보인다. 매매와 무관하지만 「지금 내 전략이 어떤 성적인가」의
     근거가 조용히 낡는다.

  ⑧ [v192] **전환 실행일 아침의 재알림** — 새벽(05시) 알림은 자는 동안 오고 실행은 09:05 부터다.
     그걸 보고 잠들었다가 09시에 잊는 경로가 비어 있었다. 이 슬롯(평일 08:40)은 이미 있으므로
     실행일 아침에 한 번 더 말한다. 실행일에만 나가니 거짓 알림 0 · 연 2~3건.

  ⑨ [v192] **근접 진입 알림** — 게이지가 「근접」(전환선까지 3%p 미만)에 들어선 날 아침 한 번.
     04 §5-8 「근접일 때의 전환은 절대 놓치지 마라」와 설명서 §③ 부재 규칙 「근접이면 떠나기 전
     정리」는 둘 다 **화면을 열어야** 작동했다. 54년 실측(research/near_zone.py): 진입 연 3.5회 ·
     55% 가 20일 안 전환 · 전환의 99% 가 직전 5일 안에 근접을 거침 · 헛걸음 연 1.6회.

사용:
    python3 deploy/watchdog.py stale      # 신호가 며칠째 그대로인가
    python3 deploy/watchdog.py rebalance  # 오늘이 방어 재조정일인가 (30일 주기)
    python3 deploy/watchdog.py channel    # 알림 채널이 살아 있는가 (메시지 안 보냄)
    python3 deploy/watchdog.py stats      # 성과 스냅샷이 갱신되고 있는가 (월 1회)
    python3 deploy/watchdog.py price      # 시세 수집이 살아 있는가 (price-data 브랜치)
    python3 deploy/watchdog.py check      # 점검.py 자동 실행 → data/ops_check.json
    python3 deploy/watchdog.py heartbeat  # 월 1회 「살아 있음」 (안 오면 그게 신호)
    python3 deploy/watchdog.py switchday  # [v192] 오늘이 전환 실행일이면 재알림
    python3 deploy/watchdog.py near       # [v192] 게이지가 「근접」에 들어선 날 한 번

각 모드는 **항상 0 으로 끝난다**(감시가 파이프라인을 죽이면 안 된다).
사람이 개입해야 하는 상황이면 GITHUB_OUTPUT 에 `alert=1` 을 남긴다 —
워크플로가 그걸 보고 이슈를 연다.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import date, datetime, timedelta, timezone

from kakao_keepalive import main as kakao_keepalive_main

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


SIGNAL = os.path.join('data', 'signal.json')
OPSCHK = os.path.join('data', 'ops_check.json')
CHECKPY = os.path.join('내가_보는_것', '점검.py')

# 신호가 이 영업일 수만큼 밀리면 알린다.
#   · 정기 휴장은 **연속 1영업일**뿐이다 (추수감사절 목+금 중 금요일은 단축장이라 종가가 나온다).
#   · 비상 휴장의 근대 최장 기록도 2일(2012 샌디) — 문턱 3 아래다.
#   · 4일(2001 9/11) 급의 사태라면 알림이 오는 쪽이 맞다.
# 화면 배너는 2 초과에서 노랑, 4 초과에서 빨강 — 그 사이에서 폰으로 먼저 알린다.
STALE_N = 3

# [v171] 성과 스냅샷이 이 날수만큼 묵으면 알린다.
#   · 정상 주기는 매월 1일이므로 최대 31일. 한 번 건너뛰면 다음 기회는 62일 뒤다.
#   · 45 는 **한 번 건너뛴 것을 다음 예약일이 오기 전에** 잡는 자리다
#     (31 로 조이면 월말에 정상 상태로도 울리고, 62 로 늘리면 두 달을 놓친다).
# 신호(STALE_N)와 달리 이건 **매매와 무관**하다 — 알림 문구가 그 점을 먼저 말한다.
STATS_STALE = 45

# [v176] 시세 스냅샷이 이 영업일 수만큼 밀리면 알린다.
#   파수꾼은 평일 08:40(개장 전)에 도므로, 정상이면 최신 스냅샷은 **전 거래일 15:55**
#   = 1영업일 전이다. 금→월도 1영업일, 월요일이 휴장이어도 2영업일.
#   그래서 신호와 같은 3을 쓴다 — 정상 상태에서 절대 안 울린다.
PRICE_STALE = 3


def out(key, val):
    """워크플로가 읽는 스텝 출력."""
    p = os.environ.get('GITHUB_OUTPUT')
    if p:
        with open(p, 'a', encoding='utf-8') as f:
            f.write(f'{key}={val}\n')
    print(f'[출력] {key}={val}')


def atomic_write_json(path, obj, replace_func=os.replace):
    """JSON을 같은 디렉터리 임시파일에 완성한 뒤 한 번에 교체한다."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.',
                               suffix='.tmp', dir=parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        replace_func(tmp, path)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def kst_today():
    return datetime.now(timezone(timedelta(hours=9))).date()


def biz_days_since(iso, today=None):
    """signal.html 의 bizDaysSince 와 같은 정의 — [as_of, 오늘) 의 평일 수."""
    d0 = date.fromisoformat(iso)
    if d0.isoformat() != iso:
        raise ValueError(f'기준일이 YYYY-MM-DD 정규형이 아님: {iso!r}')
    d1 = today or kst_today()
    if d0 > d1:
        raise ValueError(f'기준일 {d0}이 현재일 {d1}보다 미래임')
    n = 0
    t = d0
    while t < d1:
        if t.weekday() < 5:
            n += 1
        t += timedelta(days=1)
    return n


def repeat_gate(n, threshold, period):
    """[2026-09-04 코드리뷰] 「이미 알렸으니 이번엔 생략」 규칙 — 종전에는 stale·stats·price
    **세 곳에 따로** 있었고 형태도 달랐다(n % K · (n-T) % K). 규칙을 한 번만 적는다.

    True = 이번에 보낸다.  경과 n 이 문턱을 넘은 뒤 period 마다 한 번.

    ⚠ 알려진 한계 — **슬롯이 통째로 스킵되면 그 주기를 통째로 건너뛴다.** 실측(2026 전수
      시뮬레이션): 문턱 3영업일 알림에서 세 번째 슬롯이 스킵되면 첫 발송이 03-11 → 03-16 로
      **5일 밀린다.** 무상태로는 못 고친다 — 「지난번에 보냈나」를 기억할 곳이 이 잡에는 없다
      (일간 스텝은 커밋을 안 하고, 커밋을 넣으면 v176 이 없앤 이력 소음이 되살아난다).
      실측 근거로 지금은 감수한다: watchdog.yml 의 일간 cron 은 관측 3/3 이 정확히 24.0h 간격
      (지연 5~6분)이었다. 스킵이 실제로 관측되면 그때 상태 저장을 넣는다(04 §7 후보).
      ※ 놓쳐도 **조건은 지속되므로 다음 주기에 반드시 알린다** — 잃는 것은 시점이지 알림이 아니다.
    ※ 같은 날 두 번 보내던 문제(월요일은 08:40·09:10 두 슬롯이 돌았다)는 여기가 아니라
      watchdog.yml 에서 막는다 — 일간 스텝을 월요일 09:10 슬롯에서 빼는 쪽이 옳다.
    """
    if n < threshold:
        return False
    return (n - threshold) % period == 0

def notify(title, status, detail):
    """폰 알림. 실패하면 해당 모드의 이슈(메일) fallback도 함께 켠다."""
    rc = subprocess.call([sys.executable, os.path.join('deploy', 'notify.py'),
                          title, status, detail])
    if rc != 0:
        print(f'[경고] 폰 알림 실패(returncode={rc}) — 이슈 fallback 사용',
              file=sys.stderr)
        out('alert', 1)
    return rc


# --------------------------------------------------------------------------
# ① 신호 신선도 — 워크플로가 「안 돈」 경우를 잡는다
# --------------------------------------------------------------------------
def mode_stale():
    if not os.path.exists(SIGNAL):
        print('signal.json 없음 — 첫 실행이면 정상')
        return
    try:
        as_of = json.load(open(SIGNAL, encoding='utf-8'))['as_of']
    except Exception as e:
        print(f'[경고] signal.json 을 읽지 못했다: {e}')
        out('alert', 1)
        notify('신호 파일 손상', 'failure',
               'data/signal.json 을 읽지 못했습니다 — 화면 수치를 믿지 마세요.')
        return
    try:
        n = biz_days_since(as_of)
    except Exception as e:
        print(f'[경고] signal as_of가 잘못돼 신선도를 계산하지 않는다: {e}')
        out('alert', 1)
        notify('신호 날짜 손상', 'failure',
               'data/signal.json 의 종가 날짜가 미래이거나 형식이 잘못됐습니다 — 화면 수치를 믿지 마세요.')
        return
    print(f'마지막 종가 {as_of} · {n}영업일 경과 (문턱 {STALE_N})')
    if n < STALE_N:
        print('정상 — 알림 없음')
        return
    # 매일 같은 알림을 보내면 정작 전환일 알림을 무시하게 된다 — 3영업일마다만.
    # 이슈 댓글도 같은 주기를 따른다(alert 를 여기서 켠다 — 매일 댓글이 붙지 않게).
    if not repeat_gate(n, STALE_N, STALE_N):        # 규칙은 repeat_gate 한 곳에만 있다
        print(f'{n}영업일째 — 이미 알렸으므로 이번엔 발송 생략({STALE_N}영업일 간격)')
        return
    out('alert', 1)
    notify('신호가 갱신되지 않고 있습니다', 'failure',
           f'마지막 종가 {as_of} · {n}영업일째 그대로입니다.\n'
           '자동 갱신이 멈췄을 수 있습니다. 화면의 낙폭·상태는 옛 종가 기준입니다.')


# --------------------------------------------------------------------------
# ①-b 방어 재조정일 — 전환일은 알림이 가는데 재조정일은 「화면을 열어야」 알 수 있었다
# --------------------------------------------------------------------------
def defense_entry():
    """현재 방어 연속 구간의 첫 날. signal.html getDefenseEntryDate 와 같은 규약.

    장부 맨 앞까지 같은 상태면(전환 기록이 장부 밖) **미확정**으로 본다 — 없는
    날짜를 지어내느니 알리지 않는 쪽이 옳다."""
    import csv
    p = os.path.join('data', 'oos_log.csv')
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r.get('as_of')]
    if not rows or rows[-1].get('state') != 'SCHD':
        return None
    k = len(rows) - 1
    while k > 0 and rows[k - 1].get('state') == 'SCHD':
        k -= 1
    if k == 0 and rows[0].get('changed') != '1':
        return None                                # 전환 기록이 장부 밖 — 미확정
    return rows[k]['as_of']


def rebalance_due(entry_iso, today):
    """(알릴 날인가, 경과일) — v117 규약: 진입일부터 30일마다.

    주기일이 주말이면 **그 다음 평일**로 민다 (파수꾼은 평일에만 돈다).
    한국 휴장일은 밀지 않는다 — 화면의 「휴장이면 다음 개장일에」 규약과 같게 둔다.
    상태를 저장하지 않고도 주기당 정확히 한 번만 참이 되는 계산이다."""
    e = date.fromisoformat(entry_iso)
    k = (today - e).days
    if k < 30:
        return False, k
    target = e + timedelta(days=30 * (k // 30))
    while target.weekday() >= 5:                   # 토·일 → 다음 평일
        target += timedelta(days=1)
    return today == target, k


def mode_rebalance():
    e = defense_entry()
    if not e:
        print('방어 상태가 아니거나 진입일 미확정 — 할 일 없음')
        return
    today = kst_today()
    due, k = rebalance_due(e, today)
    print(f'방어 진입 {e} · {k}일 경과 · 오늘 재조정일? {due}')
    if not due:
        return
    # 이상이 아니라 **일정**이다 — alert 를 켜지 않는다(이슈를 열 일이 아니다).
    notify('방어 비율 재조정일', 'signal',
           f'방어 전환({e}) 후 {k}일 — 비율 40/40/20 확인일입니다.\n'
           '화면의 「오늘의 행동」이 몇 주를 사고팔지 계산해 줍니다. 휴장이면 다음 개장일에.')


# --------------------------------------------------------------------------
# ①-c [v192] 전환 실행일 재알림 — 05시 알림은 자는 동안 오고, 실행은 09:05 부터다
# --------------------------------------------------------------------------
# 새벽 알림(signal_alert.py)은 종가가 굳는 순간 한 번 간다. 그걸 보고 잠들었다가 09시에
# 잊는 경로가 비어 있었다. 이 슬롯(평일 08:40)은 이미 있으므로 **실행일 아침에 한 번 더**.
# 실행일 = 종가일 다음 날부터 첫 한국 거래일(주말·휴장 반영 — 화면 krExecLabel 과 같은 규약).
# 실행일에만 나가므로 거짓 알림이 없다(연 2~3건). 서버는 체결 여부를 알 수 없으므로
# 문구는 「이미 하셨다면 무시」로 끝난다. 일정이지 이상이 아니다 — alert 를 켜지 않는다.
KRHOL = os.path.join('data', 'kr_holidays.json')
OOSLOG = os.path.join('data', 'oos_log.csv')


def kr_holidays(for_date=None):
    """검증된 한국 휴장일 집합. 실행일은 달력 없이 추정하지 않는다."""
    if not os.path.exists(KRHOL):
        raise RuntimeError('kr_holidays.json 이 없다')
    try:
        j = json.load(open(KRHOL, encoding='utf-8'))
    except Exception as e:
        raise RuntimeError('kr_holidays.json 파싱 실패') from e
    holidays, years = j.get('holidays'), j.get('range')
    if not isinstance(holidays, dict) or not isinstance(years, list) or len(years) != 2:
        raise RuntimeError('kr_holidays.json 구조가 잘못됐다')
    try:
        lo, hi = int(years[0]), int(years[1])
        parsed = {date.fromisoformat(str(d)) for d in holidays}
    except (TypeError, ValueError) as e:
        raise RuntimeError('kr_holidays.json 날짜·범위를 해석할 수 없다') from e
    if lo > hi or any(not lo <= d.year <= hi for d in parsed):
        raise RuntimeError('kr_holidays.json 날짜가 선언 범위 밖이다')
    if for_date is not None and not lo <= for_date.year <= hi:
        raise RuntimeError(f'{for_date}가 휴장일 표 범위 {lo}~{hi} 밖이다')
    return {d.isoformat() for d in parsed}


def kr_biz_days_since(iso, today=None, hol=None):
    """한국 시세용 [as_of, 오늘) 거래일 수 — 평일 중 휴장일은 빼고 센다."""
    d0 = date.fromisoformat(iso)
    if d0.isoformat() != iso:
        raise ValueError(f'기준일이 YYYY-MM-DD 정규형이 아님: {iso!r}')
    d1 = today or kst_today()
    if d0 > d1:
        raise ValueError(f'기준일 {d0}이 현재일 {d1}보다 미래임')
    hol = kr_holidays(d1) if hol is None else hol
    n, cur = 0, d0
    while cur < d1:
        if cur.weekday() < 5 and cur.isoformat() not in hol:
            n += 1
        cur += timedelta(days=1)
    return n


def kr_next_trading_day(d, hol):
    """d 이후(포함) 첫 한국 거래일."""
    for _ in range(40):
        if d.weekday() < 5 and d.isoformat() not in hol:
            return d
        d += timedelta(days=1)
    return d


def last_switch():
    """가장 최근 전환 → (미국 종가일 as_of, 전환 후 상태). 장부(oos_log.csv)의 changed=1 행이
    1차, signal.json 의 changed_today 가 2차(장부 스텝이 실패한 날의 보험). 둘 중 늦은 날짜."""
    import csv
    best = None
    if os.path.exists(OOSLOG):
        with open(OOSLOG, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                changed = r.get('changed')
                if changed not in ('0', '1'):
                    raise ValueError(f'OOS changed가 0/1이 아님: {changed!r}')
                as_of, state = r.get('as_of'), r.get('state')
                if not as_of or date.fromisoformat(as_of).isoformat() != as_of:
                    raise ValueError(f'OOS as_of가 YYYY-MM-DD가 아님: {as_of!r}')
                if state not in ('QLD', 'SCHD'):
                    raise ValueError(f'OOS state가 허용값이 아님: {state!r}')
                if changed == '1':
                    best = (as_of, state)
    if os.path.exists(SIGNAL):
        try:
            j = json.load(open(SIGNAL, encoding='utf-8'))
            # [2026-09-04 코드리뷰] 최상위 키는 A(−16/−11) 미러다 — B 가 없으면 A 의
            # 전환일을 B 의 전환일로 착각해 **틀린 날 실행 알림**이 간다. 물러서지 않는다.
            b = (j.get('strategies') or {}).get('B') or {}
            changed = b.get('changed_today')
            if b and type(changed) is not bool:
                raise ValueError('signal B changed_today가 JSON 불리언이 아님')
            if changed:
                as_of, state = j.get('as_of'), b.get('state')
                if not as_of or date.fromisoformat(as_of).isoformat() != as_of:
                    raise ValueError(f'signal as_of가 YYYY-MM-DD가 아님: {as_of!r}')
                if state not in ('QLD', 'SCHD'):
                    raise ValueError(f'signal B state가 허용값이 아님: {state!r}')
                cand = (as_of, state)
                if best is None or cand[0] > best[0]:
                    best = cand
        except Exception:
            raise
    return best


def switch_exec_day(as_of_iso, hol):
    """미국 종가일 D → 신호는 D+1 KST 새벽에 뜬다 → 그날부터 첫 한국 거래일."""
    return kr_next_trading_day(date.fromisoformat(as_of_iso) + timedelta(days=1), hol)


def switch_action(state):
    # signal_alert.py 와 같은 문장 — 두 알림이 다른 말을 하면 안 된다
    if state == 'QLD':
        return '방어 바스켓 전량 매도 → TIGER 나스닥100레버리지(418660) 매수'
    if state == 'SCHD':
        return 'QLD 전량 매도 → 방어 바스켓 매수 (배당40 458730 / 국채40 305080 / 금20 411060)'
    raise ValueError(f'알 수 없는 전환 상태로 매매 문구를 만들 수 없음: {state!r}')


def mode_switchday(today=None):
    try:
        sw = last_switch()
    except Exception as e:
        print(f'[경고] 전환 기록을 검증하지 못해 실행일을 알리지 않는다: {e}')
        out('alert', 1)
        return
    if not sw:
        print('전환 기록 없음 — 할 일 없음')
        return
    as_of, st = sw
    today = today or kst_today()
    try:
        hol = kr_holidays(today)
    except Exception as e:
        print(f'[경고] 한국 휴장일 표를 읽지 못해 실행일을 추정하지 않는다: {e}')
        out('alert', 1)
        return
    ex = switch_exec_day(as_of, hol)
    print(f'마지막 전환 {as_of} → {st} · 실행일 {ex} · 오늘 {today}')
    if today != ex:
        print('오늘은 실행일이 아니다 — 알림 없음')
        return
    head = f'{as_of} 종가로 전환 신호'
    try:
        j = json.load(open(SIGNAL, encoding='utf-8'))
        if j.get('as_of') == as_of:
            head = f"낙폭 {j.get('dd')}% (종가 {j.get('close')}, {as_of})"
    except Exception:
        pass
    notify('오늘 전환 실행일 (재알림)', 'signal',
           f'{head}\n오늘 한국장 09:05~15:20 에: {switch_action(st)}\n'
           '새벽 알림과 같은 내용입니다 — 이미 체결하셨다면 무시하세요. 체결 뒤 화면에 기록을 남기세요.')


# --------------------------------------------------------------------------
# ①-d [v192] 근접 진입 알림 — 게이지가 「근접」(전환선까지 3%p 미만)에 들어선 날 아침 한 번
# --------------------------------------------------------------------------
# 04 §5-8 「근접일 때의 전환은 절대 놓치지 마라」·설명서 §③ 「근접이면 떠나기 전 정리」는 둘 다
# **화면을 열어야** 작동했다. 들어선 날 한 번 말해 두면 화면을 안 열어도 그 주를 비우지 않는다.
# 문턱 3%p 는 화면 게이지(paintProx)의 빨강과 같은 값 — 화면과 다른 기준을 만들지 않는다.
# 빈도(research/near_zone.py, 1972~ 54년): 진입 연 3.5회 · 55% 가 20일 안 전환 · 전환의 99% 가
# 직전 5일 안에 근접을 거침 · 헛걸음 연 1.6회. 「접근」(8%p)까지 넓히면 연 9회 — 알림 피로.
# ★ 문구는 「아직 할 일 없음」을 먼저 말한다 — 근접의 45% 는 되돌아가고, 그때 규칙은 아무것도
#   하지 않는 것이 맞다. 04 「B 가 안 쓰는 숫자는 재량 개입을 유혹한다」의 경계 위에 있는 알림이다.
# ★ 같은 진입을 두 번 알리지 않는다: 오늘 종가가 최신(1영업일 안)일 때만 · 전환일엔 생략(새벽 알림).
NEAR_PP = 3.0


def near_gaps(j):
    """(오늘 gap, 전날 gap, B 상태) — recent 는 최신이 [0] (signal.json 실측, v154).
    gap = |dd − 선| [%p]. 선은 상태별 enter/exit — 동결 규칙은 둘 다 −16 이라 같은 값.
    ★ signal.json 의 **최상위** state/exit/gap_pp/next_line 과 recent[].s 는 구버전 화면 호환용
      **A 미러**다(update_signal.py 주석 「구버전 signal.html 호환용 미러 (A 기준)」 — 실측 2026-09-02:
      최상위 exit = −11). B 는 strategies.B 와 recent[].B 에 있다. 최상위를 읽으면 방어 상태의
      복귀선이 −11 로 잡혀 근접 판정이 틀린다 — signal_alert.py 도 같은 이유로 strategies.B 를 읽는다."""
    b = (j.get('strategies') or {}).get('B') or {}
    rc = j.get('recent') or []
    if len(rc) < 2:
        return None

    def bstate(row):
        state = row.get('B')
        if state not in ('QLD', 'SCHD'):
            raise ValueError(f'recent B state가 허용값이 아님: {state!r}')
        return state

    def line(row):
        # [2026-09-04 코드리뷰] 최상위 exit 는 A 의 **−11** 이다(실측). B 가 없을 때 그리로
        # 물러서면 방어 상태의 복귀선이 −11 로 잡혀 근접 판정이 통째로 틀린다 —
        # v192 가 「첫 구현이 그럴 뻔했다」고 적어 둔 바로 그 함정이 폴백으로 남아 있었다.
        v = b.get('exit') if bstate(row) == 'SCHD' else b.get('enter')
        v = float(v)
        return v * 100 if abs(v) < 1 else v            # −0.16 이든 −16 이든 %p 로

    def gap(row):
        return abs(float(row['dd']) - line(row))

    return gap(rc[0]), gap(rc[1]), bstate(rc[0])


def mode_near(today=None):
    if not os.path.exists(SIGNAL):
        print('signal.json 없음 — 첫 실행이면 정상')
        return
    j = json.load(open(SIGNAL, encoding='utf-8'))
    b = (j.get('strategies') or {}).get('B') or {}
    if not b:
        print('[경고] signal.json 에 strategies.B 가 없다 — 근접 판정 생략(A 미러를 쓰지 않는다)')
        return
    if b.get('state') not in ('QLD', 'SCHD') or type(b.get('changed_today')) is not bool:
        print('[경고] strategies.B 상태/changed_today가 잘못돼 근접 판정을 하지 않는다')
        out('alert', 1)
        return
    if b.get('changed_today'):
        print('전환일 — 새벽 알림이 이미 갔다(근접 알림 생략)')
        return
    today = today or kst_today()
    try:
        n = biz_days_since(j['as_of'], today)
        g = near_gaps(j)
    except Exception as e:
        print(f'[경고] 근접 신호 입력을 검증하지 못했다: {e}')
        out('alert', 1)
        return
    if g is None:
        print('recent 가 2일 미만 — 판정 불가')
        return
    g0, g1, st = g
    print(f"낙폭 {j.get('dd')}% · 선까지 오늘 {g0:.1f}%p / 전날 {g1:.1f}%p · 종가일 {j['as_of']} ({n}영업일 전)")
    if n > 1:
        print('오늘 종가가 아니다 — 같은 진입을 두 번 알리지 않는다')
        return
    if not (g0 < NEAR_PP <= g1):
        print('근접 진입일이 아니다 — 알림 없음')
        return
    is_atk = st == 'QLD'
    nm = '전환선' if is_atk else '복귀선'
    notify('낙폭 게이지 「근접」 진입', 'signal',
           f"낙폭 {j.get('dd')}% — {nm}(−16%)까지 {g0:.1f}%p (종가 {j.get('close')}, {j['as_of']}).\n"
           '아직 할 일 없음 — 규칙대로 기다립니다. 다만 이번 주는 ① 자리를 비우지 말 것 '
           '② 증권 앱 로그인 확인.\n'
           '과거 54년: 근접의 55%가 20일 안에 전환으로 이어졌고 45%는 되돌아갔습니다(연 3~4회).')


# --------------------------------------------------------------------------
# ② 알림 채널 생존 — 「전환일에 카톡이 안 오는」 사고를 미리 잡는다
# --------------------------------------------------------------------------
def mode_channel():
    """메시지를 **보내지 않고** 자격증명만 확인한다 (평시 소음 0).

    토큰 값은 어떤 경로로도 출력하지 않는다."""
    dead, alive = [], []

    kk = os.environ.get('KAKAO_REST_API_KEY', '').strip()
    kr = os.environ.get('KAKAO_REFRESH_TOKEN', '').strip()
    if kk and kr:
        try:
            rc = kakao_keepalive_main()
            if rc != 0:
                raise RuntimeError(f'갱신/회전 처리 returncode={rc}')
            alive.append('카카오톡')
        except Exception as e:
            dead.append(f'카카오톡({type(e).__name__})')
    elif kk or kr:
        dead.append('카카오톡(secret 설정 불완전)')

    tk = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    ch = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if tk and ch:
        try:
            with urllib.request.urlopen(f'https://api.telegram.org/bot{tk}/getMe', timeout=30) as r:
                reply = json.loads(r.read())
            if not isinstance(reply, dict) or reply.get('ok') is not True:
                raise RuntimeError('getMe 응답 ok가 true가 아님')
            alive.append('Telegram')
        except Exception as e:
            dead.append(f'Telegram({type(e).__name__})')
    elif tk or ch:
        dead.append('Telegram(token/chat ID 설정 불완전)')

    if os.environ.get('DISCORD_WEBHOOK_URL', '').strip():
        alive.append('Discord(등록됨 · 무발송 확인 불가)')

    print('살아 있음: ' + (', '.join(alive) if alive else '없음'))
    if not alive and not dead:
        # [2026-09-03] 채널이 **하나도 등록돼 있지 않은** 상태는 「확인할 것 없음」이 아니라 「전환일에 아무 알림도
        #   안 오는 상태」다 — 카톡으로는 말할 수 없으니 이슈(메일)로 한다. 주간 슬롯에서만 켜 댓글이 매일 붙지 않게.
        #   (v177 생존 알림이 「안 오는 것」으로 알려 주긴 하지만 한 달 걸린다.)
        print('알림 채널 secret 미설정 — 전환일에 알림이 안 온다')
        if os.environ.get('WEEKLY', '').lower() == 'true':
            out('alert', 1)
        return
    if not dead:
        return
    print('★ 죽은 채널: ' + ', '.join(dead))
    out('alert', 1)
    # 죽은 채널로는 못 보내므로 살아 있는 채널로 알린다. 전부 죽었으면
    # notify.py 가 조용히 넘어가고, 워크플로가 이슈를 연다(메일이 온다).
    notify('알림 채널 이상', 'failure',
           '알림 채널이 응답하지 않습니다: ' + ', '.join(dead) + '\n'
           '이대로면 전환일에 알림이 안 옵니다 — AI에게 재설정을 요청하세요.')


# --------------------------------------------------------------------------
# ②-b [v171] 성과 스냅샷 신선도 — monthly-stats.yml 이 「안 돈」 경우를 잡는다
# --------------------------------------------------------------------------
def mode_stats():
    """성과 비교표의 원천이 갱신되고 있는가.

    monthly-stats.yml 도 실패 알림이 `if: failure()` 뿐이라 **예약 슬롯이 통째로
    건너뛴 경우**를 못 잡는다 — ① 과 같은 구멍이다. 다만 훨씬 덜 보인다:
    신호는 매일이라 화면 신선도 도트가 티를 내지만 성과표는 월 1회라
    두 달이 밀려도 화면이 똑같아 보인다.

    파일을 읽기만 한다. 스냅샷을 여기서 다시 만들지 않는다 —
    그건 monthly-stats.yml 의 일이고, 그쪽은 verify_all 전체를 통과해야만 커밋한다."""
    p = os.path.join('data', 'strategy_stats.json')
    if not os.path.exists(p):
        print('strategy_stats.json 없음 — 첫 실행이면 정상')
        return
    try:
        j = json.load(open(p, encoding='utf-8'))
        raw_gen = str(j['generated_at'])
        gen = raw_gen[:10]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', gen):
            raise ValueError('generated_at 날짜 형식이 YYYY-MM-DD가 아님')
        d = date.fromisoformat(gen)
        if d.isoformat() != gen or d > kst_today():
            raise ValueError('generated_at 날짜가 비정상 또는 미래임')
    except Exception as e:
        print(f'[경고] strategy_stats.json 을 읽지 못했다: {e}')
        out('alert', 1)
        notify('성과 스냅샷 파일 손상', 'failure',
               'data/strategy_stats.json 을 읽지 못했습니다 — 성과 비교표가 비어 보일 수 있습니다.\n'
               '매매와는 무관합니다: 신호·전환 판정은 이 파일을 쓰지 않습니다.')
        return
    # 곡선 끝날짜는 알림 문구에만 쓴다(없어도 감시는 돈다).
    end = ''
    try:
        end = (j['scenarios'][0]['strategies']['B']['end'] or '')
    except Exception:
        pass
    n = (kst_today() - d).days
    print(f'성과 스냅샷 {gen} 생성 · {n}일 경과 (문턱 {STATS_STALE})'
          + (f' · 곡선 {end} 까지' if end else ''))
    if n < STATS_STALE:
        print('정상 — 알림 없음')
        return
    # 매일 같은 말을 반복하면 정작 전환일 알림을 무시하게 된다 — 7일마다 한 번만.
    if not repeat_gate(n, STATS_STALE, 7):
        print(f'{n}일째 — 이미 알렸으므로 이번엔 발송 생략(7일 간격)')
        return
    out('alert', 1)
    notify('성과표가 갱신되지 않고 있습니다', 'failure',
           f'성과 비교표가 {gen} 이후 {n}일째 그대로입니다'
           + (f' (곡선 {end} 까지).' if end else '.') + '\n'
           '월간 스냅샷(매월 1일 16:17)이 건너뛰었거나 검증에서 막혔을 수 있습니다.\n'
           '★ 매매와는 무관합니다 — 신호·전환 판정은 매일 따로 갱신됩니다.')


# --------------------------------------------------------------------------
# ②-c [v176] 시세 수집 생존 — price-data 브랜치가 갱신되고 있는가
# --------------------------------------------------------------------------
def mode_price(today=None):
    """시세는 main 에 없다(v176) — price-data 브랜치에 항상 커밋 1개로 덮인다.

    수집이 죽으면 배포가 파일을 못 싣고 화면은 배지를 숨긴다. 그게 옳은 실패지만
    **조용하다** — 여기서 폰으로 말해 준다. 전략과 무관하다(표시 전용)."""
    try:
        subprocess.run(['git', 'fetch', '-q', '--depth=1', 'origin', 'price-data'],
                       check=True, timeout=120)
        raw = subprocess.check_output(['git', 'show', 'FETCH_HEAD:data/price.json'],
                                      text=True, encoding='utf-8', timeout=60)
        as_of = str(json.loads(raw)['as_of_kst'])[:10]
        d = date.fromisoformat(as_of)
    except Exception as e:
        print(f'[경고] price-data 를 읽지 못했다: {type(e).__name__}: {e}')
        out('alert', 1)
        notify('시세 수집 상태를 확인할 수 없습니다', 'failure',
               'price-data 브랜치 또는 data/price.json 을 읽지 못했습니다.\n'
               '★ 매매 신호와는 무관하지만, 화면의 가격 배지가 갱신되지 않을 수 있습니다.')
        return
    today = today or kst_today()
    try:
        n = kr_biz_days_since(as_of, today=today)
    except Exception as e:
        print(f'[경고] 한국 휴장일 표를 읽지 못해 시세 신선도를 추정하지 않는다: {e}')
        out('alert', 1)
        return
    print(f'시세 스냅샷 {as_of} · {n}영업일 경과 (문턱 {PRICE_STALE})')
    if n < PRICE_STALE:
        print('정상 — 알림 없음')
        return
    if not repeat_gate(n, PRICE_STALE, PRICE_STALE):
        print(f'{n}영업일째 — 이미 알렸으므로 이번엔 발송 생략({PRICE_STALE}영업일 간격)')
        return
    out('alert', 1)
    notify('시세가 수집되지 않고 있습니다', 'failure',
           f'화면의 자산 시세가 {as_of} 이후 {n}영업일째 그대로입니다.\n'
           '화면에서는 가격·괴리 배지가 사라져 있을 것입니다(옛 값을 보여주지 않습니다).\n'
           '★ 매매와는 무관합니다 — 신호·전환 판정은 QQQ 종가만 보며 따로 갱신됩니다.\n'
           '주문할 땐 증권사 앱 값을 쓰시면 됩니다.')


# --------------------------------------------------------------------------
# ③ 점검 자동 실행 — 사람이 기억해서 파이썬을 돌릴 의무를 없앤다
# --------------------------------------------------------------------------
PROTO_EVAL = os.path.join('research', 'oos_protocol_b.py')
PB_RANK = {'ok': 0, 'error': 1, 'warn': 1, 'invalid': 2, 'outside': 2}


def protocol_status(env):
    """[2026-09-02 · v188] B 판정 규약(02 §5-1 · data/oos_protocol_b.json) 평가기를 돌려 **요약만** 돌려준다.

    판정은 평가기(research/oos_protocol_b.py --oos)가 하고 여기서는 읽기만 한다 — 파수꾼은
    규칙·장부·규약을 한 글자도 쓰지 않는다. 평가기가 죽어도 주간 점검을 해치지 않는다
    (빈 요약 대신 'error' 로 남겨 화면에 보이게 한다 — 조용히 사라지는 것이 가장 나쁘다).
    verdict: ok · warn(주의) · outside(역사 밖 → 재검토) · invalid(규약 지문 불일치) · error.
    """
    if not os.path.exists(PROTO_EVAL):
        return None
    try:
        p = subprocess.run([sys.executable, PROTO_EVAL, '--oos'], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', env=env, timeout=900)
        txt, rc = (p.stdout or ''), p.returncode
    except Exception as e:                                  # 시간 초과·실행 불가
        print(f'[경고] 판정 규약 평가기 실행 실패: {e}')
        return {'verdict': 'error', 'events': None, 'line': '평가기 실행 실패', 'drift': False,
                'todo': 'B 판정 규약 평가기가 돌지 않았다 — AI 에게 확인 요청', 'exit': None}
    m = re.search(r'동결 이후 도피 사건 (\d+)건', txt)
    events = int(m.group(1)) if m else None
    drift = '역사 기저율이 등록값과 다르다' in txt
    # ★ 종료코드만으로 판정하지 않는다 — 파이썬이 예외로 죽어도 exit 1 이라, rc 만 보면
    #   「평가기 크래시」가 「역사 밖」으로 둔갑한다(단위 검사에서 실제로 났다). 문구가 있어야 판정이다.
    if '지문 불일치' in txt:
        v, line = 'invalid', '규약 지문 불일치'
        todo = 'B 판정 규약 JSON 이 수정됐다(지문 불일치) — 02 §5-1 절차대로 날짜·이유를 남겨야 한다'
    elif '판정: **역사 밖' in txt:
        v, line = 'outside', '역사 밖 — 재검토 연구 개시'
        todo = 'B 판정 규약: 역사 밖 — 재검토 연구 개시 (02 §5-1). 자동 변경은 없다'
    elif '판정: 주의' in txt:
        v, line, todo = 'warn', '주의', 'B 판정 규약: 주의 (02 §5-1) — 기록·알림만'
    elif drift:
        # [2026-09-05 4차 · W1] 평가기가 「기저율 표류 → 판정 중단」(rc 2)으로 끝나면 종전엔 아래 else 로
        #   떨어져 「출력을 읽지 못했다」가 todo 가 됐다 — 표류는 읽힌 것이지 못 읽은 것이 아니다.
        #   v218 이 실제로 겪은 상황(v210 자료 정정 뒤)이며, 화면·카톡 문구가 원인을 가리켜야 한다.
        v, line = 'error', '기저율 표류 — 판정 중단'
        todo = 'B 판정 규약 기저율이 등록값과 다르다(원자료 갱신?) — 판정 전에 원인 확인 · 02 §5-1 절차대로 재등록'
    elif rc == 0 and events is not None and '판정: 재검토 사유 없음' in txt:
        v, line, todo = 'ok', '사건 %d건 — 재검토 사유 없음' % events, None
    else:
        v, line, todo = 'error', '평가기 출력을 읽지 못했다', 'B 판정 규약 평가기 출력을 읽지 못했다 — AI 에게 확인 요청'
        print((p.stderr or '')[-600:])
    if drift and todo is None:
        todo = 'B 판정 규약 기저율이 등록값과 다르다(원자료 갱신?) — 판정 전에 원인 확인'
    return {'verdict': v, 'events': events, 'line': line, 'drift': drift, 'todo': todo, 'exit': rc}


# [2026-09-04 코드리뷰] ops_check.json 은 **주인이 둘**이다 — 대부분의 키는 점검.py 가
# 내지만 `heartbeat` 는 mode_heartbeat 가 얹는다. mode_check 는 점검.py 출력으로 파일을
# 통째로 덮어써서 그 키를 지웠고, watchdog.yml 에서 check 스텝이 heartbeat 스텝보다
# **먼저** 돌기 때문에 매주 월요일 「이번 달에 보냈다」 표시가 사라진다.
# → v177 이 「월 1회」로 설계한 생존 알림이 **주 1회**가 된다. 그러면 그 알림의 존재
#   이유가 무너진다: 매주 오는 알림은 읽히지 않게 되고, 읽히지 않으면 **안 오는 것도
#   눈치채지 못한다**(v177 은 침묵이 곧 고장 신호라서 만든 유일한 예외 알림이다).
#   v177 이 09-01 에 들어갔고 다음 주간 슬롯이 첫 발현이라 아직 안 났다 — 잠복 결함.
# ★ prev 를 통째로 밑에 깔지 않는다 — 점검.py 가 이번 주에 비운 todo·aum 이 되살아난다.
#   **다른 모드가 소유한 키만** 이름으로 이월한다. 새 모드가 이 파일에 키를 얹으면
#   여기 등록해야 하고, 등록을 잊으면 selftest 의 merge 검사가 잡는다.
CARRY_KEYS = ('heartbeat',)      # mode_heartbeat 소유 — 점검.py 는 이 키를 모른다


def merge_ops(prev, cur):
    """점검.py 가 낸 새 결과(cur)에 **다른 모드가 소유한 키**만 이월한다."""
    out_ = dict(cur)
    for k in CARRY_KEYS:
        if k not in out_ and k in (prev or {}):
            out_[k] = prev[k]
    return out_


def mode_check():
    prev = {}
    if os.path.exists(OPSCHK):
        try:
            prev = json.load(open(OPSCHK, encoding='utf-8'))
        except Exception:
            prev = {}
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run([sys.executable, CHECKPY, '--json'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', env=env, timeout=1800)
    line = (p.stdout or '').strip().splitlines()
    cur = None
    for ln in reversed(line):                     # JSON 은 마지막 줄 하나
        ln = ln.strip()
        if ln.startswith('{'):
            try:
                cur = json.loads(ln)
            except Exception:
                cur = None
            break
    if cur is None:
        print('[경고] 점검.py 출력을 읽지 못했다')
        print((p.stderr or '')[-800:])
        out('alert', 1)
        notify('자동 점검 실패', 'failure',
               '주간 자동 점검이 돌지 않았습니다 — AI에게 확인을 요청하세요.')
        return

    # [v188] B 판정 규약(02 §5-1) — 평가기를 같이 돌려 요약만 얹는다. v177 heartbeat 와 같은 자리
    # (이미 쓰고 커밋하는 파일)라 새 파일·새 커밋이 없다. 이상이면 todo 한 줄 → 기존 배너·알약·카톡 경로.
    pb = protocol_status(env)
    if pb is not None:
        cur['protocol_b'] = pb
        if pb.get('todo'):
            cur['todo'] = list(cur.get('todo') or []) + [pb['todo']]

    cur = merge_ops(prev, cur)            # ★ heartbeat 등 다른 모드의 키를 지우지 않는다
    atomic_write_json(OPSCHK, cur)
    print(f"Level {cur.get('level')} · {cur.get('level_msg')} · 할 일 {len(cur.get('todo') or [])}건"
          + (f" · 판정 규약 {pb['line']}" if pb else ''))
    out('written', 1)

    # 알림 규칙: **나빠졌을 때만** 말한다. 같은 상태가 계속되면 조용하다
    # (분기 규약의 대응은 「지켜본다」이므로 매주 같은 말을 반복할 이유가 없다).
    worse = check_worsened(prev, cur)
    if not (cur.get('todo') and worse):
        print('상태 악화 없음 — 알림 생략')
        return
    out('alert', 1)
    notify('자동 점검에서 확인할 것', 'failure',
           '\n'.join(f'· {t}' for t in cur['todo'])
           + '\n(전략을 바꾸는 일이 아닙니다 — 기본 대응은 「지켜본다」입니다.)')


def check_worsened(prev, cur):
    """주간 상태가 새로 나빠졌는가. 같은 장애의 반복은 조용히 둔다.

    ok 불리언 하나만 비교하면 이미 실패 중일 때 새 감시 공백이 생겨도 false→false라
    묻힌다. 점검.py가 내는 안정적인 health_errors 코드의 새 원소까지 비교한다.
    """
    lv0, lv1 = int(prev.get('level', 0) or 0), int(cur.get('level', 0) or 0)
    bad0 = {a['code'] for a in (prev.get('aum') or []) if a.get('state') != '정상'}
    bad1 = {a['code'] for a in (cur.get('aum') or []) if a.get('state') != '정상'}
    err0 = set(prev.get('health_errors') or [])
    err1 = set(cur.get('health_errors') or [])
    pb0, pb1 = (prev.get('protocol_b') or {}), (cur.get('protocol_b') or {})
    return ((lv1 > lv0) or bool(bad1 - bad0) or bool(err1 - err0)
            or (not cur.get('ok', True) and prev.get('ok', True))
            # [v188] 판정 규약이 나빠진 것(정상→주의→역사 밖)·기저율 표류가 새로 생긴 것도 「악화」다
            or PB_RANK.get(pb1.get('verdict'), 0) > PB_RANK.get(pb0.get('verdict'), 0)
            or (bool(pb1.get('drift')) and not pb0.get('drift')))


# --------------------------------------------------------------------------
# ④ [v177] 월 1회 「살아 있음」 — 침묵이 정보가 되게 한다
# --------------------------------------------------------------------------
def mode_heartbeat():
    """한 달에 한 번 「정상 작동 중」을 보낸다. **안 오면 그게 신호다.**

    다른 알림은 전부 「이상할 때만」이라 조용한 것이 정상인지 죽은 것인지 구별이
    안 됐다. 특히 공개 저장소는 **60일간 활동이 없으면 예약 실행이 통째로 꺼지고**
    (공식 문서) 그러면 파수꾼도 같이 꺼져 알려 줄 것이 남지 않는다.

    ★ 상태는 `data/ops_check.json` 에 얹는다 — 주간 점검이 **이미 쓰고 커밋하는**
      파일이라 새 파일도 새 커밋도 안 늘어난다(v176 에서 없앤 이력 소음을 되살리지
      않는다). 「달」만 비교하므로 슬롯이 건너뛰어도 다음 주에 보낸다."""
    if not os.path.exists(OPSCHK):
        print('ops_check.json 없음 — 주간 점검이 먼저 돌아야 한다')
        return
    try:
        j = json.load(open(OPSCHK, encoding='utf-8'))
    except Exception as e:
        print(f'[경고] ops_check.json 을 읽지 못했다: {e} — 이번 달은 건너뛴다')
        return

    ym = kst_today().strftime('%Y-%m')
    if str(j.get('heartbeat') or '') == ym:
        print(f'{ym} 은 이미 보냈다 — 생략')
        return

    # 알림에 실을 사실들 (하나라도 못 읽으면 그 줄만 빠진다 — 심장박동을 막지 않는다)
    lines = []
    try:
        sj = json.load(open(SIGNAL, encoding='utf-8'))
        as_of = sj['as_of']
        lines.append(f'· 신호 {as_of} ({biz_days_since(as_of)}영업일 전)')
        # [v196] 상태 한 줄 — B 는 strategies.B (최상위 state 는 A 미러, v192 적발). 메시지 수는 안 는다.
        b = (sj.get('strategies') or {}).get('B') or {}
        if b.get('state') not in ('QLD', 'SCHD'):
            raise ValueError('B state가 허용값이 아님')
        st = '방어' if b.get('state') == 'SCHD' else '공격'
        lines.append(f"· 판정 {st} · 낙폭 {sj.get('dd')}% · {'복귀선' if st == '방어' else '전환선'}까지 {b.get('gap_pp')}%p")
    except Exception:
        lines.append('· 신호 — 읽지 못했습니다')
    try:
        import csv
        rows = [r for r in csv.DictReader(open(OOSLOG, encoding='utf-8')) if r.get('as_of')]
        lines.append(f"· 동결 후 장부 {len(rows)}일 · 전환 {sum(1 for r in rows if r.get('changed') == '1')}회")
    except Exception:
        pass                                  # 장부는 부가 정보 — 없으면 그냥 뺀다
    try:
        subprocess.run(['git', 'fetch', '-q', '--depth=1', 'origin', 'price-data'],
                       check=True, timeout=120)
        pj = json.loads(subprocess.check_output(
            ['git', 'show', 'FETCH_HEAD:data/price.json'],
            text=True, encoding='utf-8', timeout=60))
        lines.append(f"· 시세 {pj['as_of_kst']}")
    except Exception:
        pass                                  # 시세는 표시 전용 — 없으면 그냥 뺀다
    lv = j.get('level')
    if lv is not None:
        lines.append(f"· 점검 Level {lv} — {j.get('level_msg') or ''}".rstrip(' —'))

    rc = notify('자동화 정상 작동 중', 'signal',
                '한 달에 한 번 보내는 생존 확인입니다.\n' + '\n'.join(lines) + '\n\n'
                '★ 이 알림이 **다음 달에 안 오면** 자동화가 멈춘 것입니다 — 그때만 손보시면 됩니다.\n'
                '(이상이 있으면 이 알림과 별개로 즉시 따로 갑니다.)')
    if rc != 0:
        print('생존 알림이 도착하지 않아 이번 달 성공 표시를 기록하지 않는다')
        return

    j['heartbeat'] = ym
    atomic_write_json(OPSCHK, j)
    out('written', 1)
    print(f'{ym} 살아 있음 알림 발송 · ops_check.json 에 기록')


MODES = {'stale': mode_stale, 'rebalance': mode_rebalance,
         'channel': mode_channel, 'stats': mode_stats, 'price': mode_price,
         'check': mode_check, 'heartbeat': mode_heartbeat,
         'switchday': mode_switchday, 'near': mode_near}


def selftest():
    """[2026-09-03] 합성 데이터 셀프테스트 — 실제 data/ 무접촉(임시 디렉터리 · notify 는 기록만).

    v192 때 스크래치에서만 돌린 24경우 + heartbeat 상태 줄을 저장소 안으로 옮겼다 — 모드를 고치면
    verify_all 전체 모드가 이걸 돌려 잡는다(「구현했다」와 「검사가 돈다」는 다르다 — v148).
    실행: python3 deploy/watchdog.py --selftest  (종료코드 0 = 전부 통과)"""
    import csv
    import io as _io
    import shutil
    import tempfile
    import contextlib
    sent = []
    real_notify = globals()['notify']
    real_kakao = globals()['kakao_keepalive_main']
    real_urlopen = urllib.request.urlopen
    real_subprocess_run = subprocess.run
    real_check_output = subprocess.check_output
    channel_names = ('KAKAO_REST_API_KEY', 'KAKAO_REFRESH_TOKEN',
                     'KAKAO_CLIENT_SECRET', 'GH_PAT', 'GITHUB_REPOSITORY',
                     'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
                     'DISCORD_WEBHOOK_URL', 'WEEKLY', 'GITHUB_OUTPUT')
    channel_env = {k: os.environ.get(k) for k in channel_names}

    def fake_notify(t, s, d):
        sent.append((t, s, d))
        return 0

    globals()['notify'] = fake_notify
    root = os.getcwd()
    T = tempfile.mkdtemp(prefix='wd_selftest_')
    os.makedirs(os.path.join(T, 'data'))
    if os.path.exists(KRHOL):
        shutil.copy(KRHOL, os.path.join(T, KRHOL))
    os.chdir(T)
    fails, n = [], 0

    def run(fn, **kw):
        n0 = len(sent)
        with contextlib.redirect_stdout(_io.StringIO()):
            fn(**kw)
        return len(sent) > n0

    def expect(name, got, want):
        nonlocal n
        n += 1
        if got != want:
            fails.append(name)

    def oos(rows):
        with open(OOSLOG, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f); w.writerow(['as_of', 'close', 'high_252', 'dd', 'state', 'changed'])
            for r in rows:
                w.writerow(r)

    def sig(**kw):
        j = dict(as_of='2026-09-01', close=700.0, dd=-5.0, state='QLD', changed_today=False,
                 enter=-16.0, exit=-11.0,                          # 최상위 = A 미러 (실측)
                 strategies={'B': {'state': 'QLD', 'changed_today': False, 'enter': -16.0, 'exit': -16.0}},
                 recent=[])
        j.update(kw)
        json.dump(j, open(SIGNAL, 'w', encoding='utf-8'))

    def rc(d0, dd0, d1, dd1, s='QLD'):
        a = 'QLD' if s == 'SCHD' else 'SCHD'                     # s 열(A 미러)은 일부러 반대로
        return [{'d': d0, 'dd': dd0, 'B': s, 'A': a, 's': a}, {'d': d1, 'dd': dd1, 'B': s, 'A': a, 's': a}]

    B = lambda st, ch=False: {'B': {'state': st, 'changed_today': ch, 'enter': -16.0, 'exit': -16.0}}
    try:
        # 미래 기준일은 0일 경과가 아니라 손상이다. 침묵하면 영구히 '정상'으로 보인다.
        try:
            biz_days_since('2099-01-01', today=date(2026, 9, 4))
            fails.append('미래 신호 날짜를 0일 경과로 처리')
        except ValueError:
            pass
        try:
            kr_biz_days_since('2099-01-01', today=date(2026, 9, 4), hol=set())
            fails.append('미래 시세 날짜를 0일 경과로 처리')
        except ValueError:
            pass
        future_output = os.path.join(T, 'future_output')
        os.environ['GITHUB_OUTPUT'] = future_output
        sig(as_of='2099-01-01')
        expect('stale 미래 날짜는 알림', run(mode_stale), True)
        expect('stale 미래 날짜는 이슈', 'alert=1' in open(future_output, encoding='utf-8').read(), True)

        # 성과 생성일도 미래면 음수 경과일로 영구 정상 처리하지 않는다.
        stats_output = os.path.join(T, 'stats_future_output')
        os.environ['GITHUB_OUTPUT'] = stats_output
        json.dump({'generated_at': '2099-01-01T00:00:00Z', 'scenarios': []},
                  open(os.path.join('data', 'strategy_stats.json'), 'w', encoding='utf-8'))
        expect('stats 미래 생성일은 알림', run(mode_stats), True)
        expect('stats 미래 생성일은 이슈',
               'alert=1' in open(stats_output, encoding='utf-8').read(), True)

        # ── channel ──
        def channel_case(values, kakao_rc=0, telegram_reply=b'{"ok":true}'):
            for key in channel_names:
                os.environ.pop(key, None)
            os.environ.update(values)
            output = os.path.join(T, 'github_output')
            if os.path.exists(output):
                os.unlink(output)
            os.environ['GITHUB_OUTPUT'] = output
            globals()['kakao_keepalive_main'] = lambda: kakao_rc

            class Response:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def read(self):
                    return telegram_reply

            urllib.request.urlopen = lambda *a, **k: Response()
            with contextlib.redirect_stdout(_io.StringIO()):
                mode_channel()
            return open(output, encoding='utf-8').read() if os.path.exists(output) else ''

        expect('channel 무설정 일간은 매일 이슈 안 냄',
               'alert=1' in channel_case({'WEEKLY': 'false'}), False)
        expect('channel 무설정 주간은 이슈',
               'alert=1' in channel_case({'WEEKLY': 'true'}), True)
        expect('channel Telegram 반쪽 설정은 죽음',
               'alert=1' in channel_case({'TELEGRAM_BOT_TOKEN': 'token'}), True)
        expect('channel Telegram 실패 본문은 죽음',
               'alert=1' in channel_case({'TELEGRAM_BOT_TOKEN': 'token',
                                          'TELEGRAM_CHAT_ID': 'chat'},
                                         telegram_reply=b'{"ok":false}'), True)
        expect('channel Kakao 회전 저장 실패는 죽음',
               'alert=1' in channel_case({'KAKAO_REST_API_KEY': 'key',
                                          'KAKAO_REFRESH_TOKEN': 'refresh'}, kakao_rc=2), True)
        expect('channel Kakao 정상은 이슈 없음',
               'alert=1' in channel_case({'KAKAO_REST_API_KEY': 'key',
                                          'KAKAO_REFRESH_TOKEN': 'refresh'}, kakao_rc=0), False)
        # ── switchday ──
        expect('sw 파일 없음', run(mode_switchday, today=date(2026, 9, 7)), False)
        oos([['2026-09-03', 700, 745, -16.5, 'SCHD', 1], ['2026-09-04', 690, 745, -17, 'SCHD', 0]])
        expect('sw 목→금 발송', run(mode_switchday, today=date(2026, 9, 4)), True)
        expect('sw 종가일 당일 무발송', run(mode_switchday, today=date(2026, 9, 3)), False)
        expect('sw 월 무발송', run(mode_switchday, today=date(2026, 9, 7)), False)
        oos([['2026-09-04', 700, 745, -16.5, 'SCHD', 1]])
        expect('sw 금→월 발송', run(mode_switchday, today=date(2026, 9, 7)), True)
        expect('sw 토 무발송', run(mode_switchday, today=date(2026, 9, 5)), False)
        oos([['2026-09-23', 700, 745, -16.5, 'SCHD', 1]])
        expect('sw 추석 연휴→09-28', run(mode_switchday, today=date(2026, 9, 28)), True)
        expect('sw 휴장일 무발송', run(mode_switchday, today=date(2026, 9, 24)), False)
        oos([['2026-08-28', 716, 745, -3.9, 'QLD', 0]])
        sig(as_of='2026-09-10', changed_today=True, state='SCHD', strategies=B('SCHD', True), dd=-16.4, close=623.0)
        expect('sw 장부 실패 보험(signal)', run(mode_switchday, today=date(2026, 9, 11)), True)
        oos([['2026-09-04', 700, 745, -16.5, 'SCHD', 1]])
        expect('sw 늦은 쪽 기준', run(mode_switchday, today=date(2026, 9, 7)), False)
        expect('sw 09-11 발송', run(mode_switchday, today=date(2026, 9, 11)), True)
        expect('sw 낙폭 문구', '낙폭 -16.4%' in sent[-1][2], True)
        sig(as_of='2026-09-10', changed_today=True, state='QLD', strategies=B('QLD', True))
        expect('sw 공격 복귀 문구', run(mode_switchday, today=date(2026, 9, 11)) and '418660) 매수' in sent[-1][2], True)
        output = os.path.join(T, 'switch_state_output')
        os.environ['GITHUB_OUTPUT'] = output
        oos([['2026-09-04', 700, 745, -16.5, '?', 1]])
        expect('sw 손상 OOS 상태는 매매 알림 없음', run(mode_switchday, today=date(2026, 9, 7)), False)
        expect('sw 손상 OOS 상태는 이슈', 'alert=1' in open(output, encoding='utf-8').read(), True)
        os.unlink(output)
        oos([['2026-08-28', 716, 745, -3.9, 'QLD', 0]])
        sig(as_of='2026-09-04', changed_today=True, strategies=B('?', True))
        expect('sw 손상 signal 상태는 매매 알림 없음', run(mode_switchday, today=date(2026, 9, 7)), False)
        expect('sw 손상 signal 상태는 이슈', 'alert=1' in open(output, encoding='utf-8').read(), True)
        expect('price 연휴 평일을 경과일에서 제외',
               kr_biz_days_since('2026-10-02', today=date(2026, 10, 7),
                                 hol={'2026-10-05', '2026-10-06'}), 1)

        # 휴장일 표가 깨지면 휴일을 실행일로 추정하지 않고 alert 출력만 남긴다.
        holiday_bytes = open(KRHOL, 'rb').read()
        open(KRHOL, 'w', encoding='utf-8').write('{broken')
        output = os.path.join(T, 'calendar_output')
        if os.path.exists(output):
            os.unlink(output)
        os.environ['GITHUB_OUTPUT'] = output
        expect('sw 달력 손상 시 매매 알림 없음',
               run(mode_switchday, today=date(2026, 9, 11)), False)
        expect('sw 달력 손상 시 이슈 출력',
               'alert=1' in open(output, encoding='utf-8').read(), True)
        open(KRHOL, 'wb').write(holiday_bytes)

        # 이미 운용 중인 price-data를 읽지 못하는 것은 첫 도입 정상으로 숨기지 않는다.
        subprocess.run = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('fetch 실패 모의'))
        expect('price 브랜치 읽기 실패 알림', run(mode_price, today=date(2026, 9, 11)), True)
        subprocess.run = lambda *a, **k: None
        subprocess.check_output = lambda *a, **k: json.dumps({'as_of_kst': '2099-01-01 10:00 KST'})
        price_output = os.path.join(T, 'price_future_output')
        os.environ['GITHUB_OUTPUT'] = price_output
        expect('price 미래 날짜는 정상 취급 안 함', run(mode_price, today=date(2026, 9, 11)), False)
        expect('price 미래 날짜는 이슈', 'alert=1' in open(price_output, encoding='utf-8').read(), True)
        subprocess.run = real_subprocess_run
        subprocess.check_output = real_check_output
        # ── near ──
        sig(as_of='2026-09-01', dd=-13.5, recent=rc('2026-09-01', -13.5, '2026-08-31', -12.0))
        expect('near 진입 발송', run(mode_near, today=date(2026, 9, 2)), True)
        expect('near 이틀째 무발송', run(mode_near, today=date(2026, 9, 3)), False)
        sig(as_of='2026-09-01', dd=-13.5, recent=rc('2026-09-01', -13.5, '2026-08-31', -14.0))
        expect('near 이미 안', run(mode_near, today=date(2026, 9, 2)), False)
        sig(as_of='2026-09-01', dd=-12.0, recent=rc('2026-09-01', -12.0, '2026-08-31', -13.5))
        expect('near 이탈', run(mode_near, today=date(2026, 9, 2)), False)
        sig(as_of='2026-09-01', dd=-13.5, recent=rc('2026-09-01', -13.5, '2026-08-31', -12.0),
            changed_today=True, strategies=B('SCHD', True))
        expect('near 전환일 생략', run(mode_near, today=date(2026, 9, 2)), False)
        sig(as_of='2026-09-04', dd=-13.5, recent=rc('2026-09-04', -13.5, '2026-09-03', -12.0))
        expect('near 금→월 발송', run(mode_near, today=date(2026, 9, 7)), True)
        sig(as_of='2026-09-01', dd=-17.5, state='SCHD', strategies=B('SCHD'),
            recent=rc('2026-09-01', -17.5, '2026-08-31', -19.5, s='SCHD'))
        expect('near 방어 복귀선', run(mode_near, today=date(2026, 9, 2)) and '복귀선' in sent[-1][2], True)
        sig(as_of='2026-09-01', dd=-13.5, strategies={'B': {'state': 'QLD', 'changed_today': False, 'enter': -0.16, 'exit': -0.16}},
            recent=rc('2026-09-01', -13.5, '2026-08-31', -12.0))
        expect('near −0.16 표기', run(mode_near, today=date(2026, 9, 2)), True)
        sig(as_of='2026-09-01', dd=-17.5, state='QLD', exit=-11.0, strategies=B('SCHD'),
            recent=rc('2026-09-01', -17.5, '2026-08-31', -19.5, s='SCHD'))
        expect('near A 미러 무시(B 기준)', run(mode_near, today=date(2026, 9, 2)) and '1.5%p' in sent[-1][2], True)
        # [2026-09-04 코드리뷰] strategies.B 가 아예 없을 때 — 종전엔 A 미러로 물러섰다.
        #   A 는 −16/−11 이라 근접·전환일 판정이 통째로 달라진다. 이제는 멈춘다.
        sig(as_of='2026-09-01', dd=-13.5, state='QLD', changed_today=True, exit=-11.0,
            strategies={}, recent=rc('2026-09-01', -13.5, '2026-08-31', -12.0))
        expect('near B 없으면 판정 안 함', run(mode_near, today=date(2026, 9, 2)), False)
        expect('switchday B 없으면 A 로 안 물러섬', run(mode_switchday, today=date(2026, 9, 2)), False)
        near_output = os.path.join(T, 'near_state_output')
        os.environ['GITHUB_OUTPUT'] = near_output
        sig(as_of='2026-09-01', dd=-13.5, strategies=B('?', False),
            recent=rc('2026-09-01', -13.5, '2026-08-31', -12.0))
        expect('near 손상 B 상태는 알림 없음', run(mode_near, today=date(2026, 9, 2)), False)
        expect('near 손상 B 상태는 이슈', 'alert=1' in open(near_output, encoding='utf-8').read(), True)
        sig(as_of='2026-09-01', dd=-13.0, recent=rc('2026-09-01', -13.0, '2026-08-31', -12.0))
        expect('near 경계 3.0 제외', run(mode_near, today=date(2026, 9, 2)), False)
        sig(as_of='2026-09-01', dd=-13.01, recent=rc('2026-09-01', -13.01, '2026-08-31', -13.0))
        expect('near 경계 2.99 포함', run(mode_near, today=date(2026, 9, 2)), True)
        sig(as_of='2026-09-01', dd=-13.5, recent=[{'d': '2026-09-01', 'dd': -13.5, 'B': 'QLD'}])
        expect('near recent 1행', run(mode_near, today=date(2026, 9, 2)), False)
        # ── heartbeat 상태 줄 (B 기준) ──
        json.dump({'level': 0, 'level_msg': '이상 없음'}, open(OPSCHK, 'w', encoding='utf-8'))
        sig(as_of='2026-09-01', dd=-5.06, state='QLD', strategies={'B': {'state': 'SCHD', 'gap_pp': 1.5, 'changed_today': False}})
        oos([['2026-08-28', 716, 745, -3.9, 'QLD', 0], ['2026-09-01', 623, 745, -16.4, 'SCHD', 1], ['2026-09-02', 620, 745, -16.8, 'SCHD', 0]])
        # 임시 저장소에서 실제 git을 부르지 않는다. 시세 줄은 부가 정보라 실패해도 정상이다.
        subprocess.run = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('fetch 생략 모의'))
        expect('hb 발송', run(mode_heartbeat), True)
        m = sent[-1][2]
        expect('hb 상태 줄(B 기준·장부)', ('판정 방어' in m) and ('복귀선까지 1.5%p' in m) and ('장부 3일' in m) and ('전환 1회' in m), True)
        expect('hb 같은 달 재발송 없음', run(mode_heartbeat), False)
        # ── [2026-09-04 코드리뷰] merge_ops — 주간 점검이 heartbeat 표시를 지우면
        #    v177 생존 알림이 월 1회 → 주 1회가 된다(그러면 침묵이 정보가 아니게 된다).
        #    실제 파일 왕복으로 잰다 — 헬퍼만 재면 mode_check 가 안 부를 때 못 잡는다.
        j0 = json.load(open(OPSCHK, encoding='utf-8'))
        expect('hb 표시가 파일에 남았다', j0.get('heartbeat'), kst_today().strftime('%Y-%m'))
        fresh = {'as_of': '2026-09-07', 'level': 0, 'level_msg': '이상 없음', 'todo': []}
        merged = merge_ops(j0, fresh)          # 점검.py 는 heartbeat 를 모른다
        json.dump(merged, open(OPSCHK, 'w', encoding='utf-8'), ensure_ascii=False)
        expect('점검이 hb 표시를 안 지운다', run(mode_heartbeat), False)
        expect('점검이 비운 todo 는 안 되살린다', merge_ops({'todo': ['옛 항목']}, fresh)['todo'], [])
        expect('CARRY_KEYS 에 heartbeat 등재', 'heartbeat' in CARRY_KEYS, True)
        # check/heartbeat가 함께 쓰는 원자 교체가 실패해도 기존 파일은 그대로다.
        ops_before = open(OPSCHK, 'rb').read()
        try:
            atomic_write_json(OPSCHK, {'corrupt': True},
                              replace_func=lambda *_: (_ for _ in ()).throw(OSError('교체 실패 모의')))
            fails.append('ops_check 교체 실패를 성공 처리')
        except OSError:
            pass
        expect('ops_check 원자 교체 실패 시 원본 보존', open(OPSCHK, 'rb').read(), ops_before)
        expect('check/heartbeat 모두 원자 writer 사용',
               mode_check.__code__.co_names.count('atomic_write_json') == 1
               and mode_heartbeat.__code__.co_names.count('atomic_write_json') == 1, True)
        subprocess.run = real_subprocess_run
        # ── check 악화 판정: 새 오류만 한 번 알린다 ──
        healthy = {'ok': True, 'health_errors': []}
        exec_bad = {'ok': False, 'health_errors': ['exec_parse:nav_days']}
        exec_plus_aum = {'ok': False, 'health_errors':
                         ['exec_parse:nav_days', 'aum_missing:411060']}
        expect('check 정상→체결오류 알림', check_worsened(healthy, exec_bad), True)
        expect('check 같은 오류 반복 무알림', check_worsened(exec_bad, exec_bad), False)
        expect('check 실패중 새 AUM 누락 알림', check_worsened(exec_bad, exec_plus_aum), True)
    finally:
        os.chdir(root)
        shutil.rmtree(T, ignore_errors=True)
        globals()['notify'] = real_notify
        globals()['kakao_keepalive_main'] = real_kakao
        urllib.request.urlopen = real_urlopen
        subprocess.run = real_subprocess_run
        subprocess.check_output = real_check_output
        for key, value in channel_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    print(f'파수꾼 셀프테스트 {n}경우 · 실패 {len(fails)}건' + (' — ' + ', '.join(fails) if fails else ''))
    return not fails


def main():
    m = sys.argv[1] if len(sys.argv) > 1 else ''
    if m == '--selftest':
        sys.exit(0 if selftest() else 1)
    if m not in MODES:
        raise SystemExit('사용: python3 deploy/watchdog.py '
                 '{stale|rebalance|switchday|near|channel|stats|price|check|heartbeat|--selftest}')
    try:
        MODES[m]()
    except Exception as e:                        # 감시가 파이프라인을 죽이지 않는다
        print(f'[경고] 파수꾼 {m} 실패: {type(e).__name__}: {e}', file=sys.stderr)
        out('alert', 1)


if __name__ == '__main__':
    main()
