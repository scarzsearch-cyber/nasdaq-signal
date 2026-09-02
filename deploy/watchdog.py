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
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

try:
    sys.stdout.reconfigure(encoding='utf-8')
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


def kst_today():
    return datetime.now(timezone(timedelta(hours=9))).date()


def biz_days_since(iso, today=None):
    """signal.html 의 bizDaysSince 와 같은 정의 — [as_of, 오늘) 의 평일 수."""
    d0 = date.fromisoformat(iso)
    d1 = today or kst_today()
    n = 0
    t = d0
    while t < d1:
        if t.weekday() < 5:
            n += 1
        t += timedelta(days=1)
    return n


def notify(title, status, detail):
    """폰 알림. secret 이 없으면 notify.py 가 조용히 넘어간다."""
    subprocess.call([sys.executable, os.path.join('deploy', 'notify.py'),
                     title, status, detail])


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
    n = biz_days_since(as_of)
    print(f'마지막 종가 {as_of} · {n}영업일 경과 (문턱 {STALE_N})')
    if n < STALE_N:
        print('정상 — 알림 없음')
        return
    # 매일 같은 알림을 보내면 정작 전환일 알림을 무시하게 된다 — 3영업일마다만.
    # 이슈 댓글도 같은 주기를 따른다(alert 를 여기서 켠다 — 매일 댓글이 붙지 않게).
    if n % STALE_N:
        print(f'{n}영업일째 — 이미 알렸으므로 이번엔 발송 생략(3영업일 간격)')
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


def kr_holidays():
    """한국 휴장일 집합(ISO). 파일이 없으면 빈 집합 — 주말만 민다(화면과 같은 후퇴)."""
    try:
        j = json.load(open(KRHOL, encoding='utf-8'))
        return set((j.get('holidays') or {}).keys())
    except Exception:
        return set()


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
                if r.get('changed') == '1' and r.get('as_of'):
                    best = (r['as_of'], r.get('state') or '?')
    if os.path.exists(SIGNAL):
        try:
            j = json.load(open(SIGNAL, encoding='utf-8'))
            b = (j.get('strategies') or {}).get('B') or {}
            if b.get('changed_today', j.get('changed_today')):
                cand = (j['as_of'], b.get('state', j.get('state', '?')))
                if best is None or cand[0] > best[0]:
                    best = cand
        except Exception:
            pass
    return best


def switch_exec_day(as_of_iso, hol):
    """미국 종가일 D → 신호는 D+1 KST 새벽에 뜬다 → 그날부터 첫 한국 거래일."""
    return kr_next_trading_day(date.fromisoformat(as_of_iso) + timedelta(days=1), hol)


def switch_action(state):
    # signal_alert.py 와 같은 문장 — 두 알림이 다른 말을 하면 안 된다
    if state == 'QLD':
        return '방어 바스켓 전량 매도 → TIGER 나스닥100레버리지(418660) 매수'
    return 'QLD 전량 매도 → 방어 바스켓 매수 (배당40 458730 / 국채40 305080 / 금20 411060)'


def mode_switchday(today=None):
    sw = last_switch()
    if not sw:
        print('전환 기록 없음 — 할 일 없음')
        return
    as_of, st = sw
    today = today or kst_today()
    ex = switch_exec_day(as_of, kr_holidays())
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
        return row.get('B', row.get('s'))

    def line(row):
        v = b.get('exit', j.get('exit')) if bstate(row) == 'SCHD' else b.get('enter', j.get('enter'))
        v = float(v if v is not None else -16)
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
    if b.get('changed_today', j.get('changed_today')):
        print('전환일 — 새벽 알림이 이미 갔다(근접 알림 생략)')
        return
    today = today or kst_today()
    n = biz_days_since(j['as_of'], today)
    g = near_gaps(j)
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
    is_atk = st != 'SCHD'
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
            body = urllib.parse.urlencode({'grant_type': 'refresh_token',
                                           'client_id': kk, 'refresh_token': kr}).encode()
            req = urllib.request.Request('https://kauth.kakao.com/oauth/token', data=body)
            with urllib.request.urlopen(req, timeout=30) as r:
                json.loads(r.read())
            alive.append('카카오톡')
        except Exception as e:
            dead.append(f'카카오톡({type(e).__name__})')

    tk = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    if tk:
        try:
            with urllib.request.urlopen(f'https://api.telegram.org/bot{tk}/getMe', timeout=30) as r:
                json.loads(r.read())
            alive.append('Telegram')
        except Exception as e:
            dead.append(f'Telegram({type(e).__name__})')

    if os.environ.get('DISCORD_WEBHOOK_URL', '').strip():
        alive.append('Discord(등록됨 · 무발송 확인 불가)')

    print('살아 있음: ' + (', '.join(alive) if alive else '없음'))
    if not alive and not dead:
        print('알림 채널 secret 미설정 — 확인할 것 없음')
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
        gen = str(j['generated_at'])[:10]
        d = date.fromisoformat(gen)
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
    if (n - STATS_STALE) % 7:
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
def mode_price():
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
        # 브랜치가 아직 없을 수도 있다(첫 도입 직후) — 그건 사고가 아니다.
        print(f'[정보] price-data 를 읽지 못했다: {type(e).__name__} — 첫 도입 직후면 정상')
        return
    n = biz_days_since(as_of)
    print(f'시세 스냅샷 {as_of} · {n}영업일 경과 (문턱 {PRICE_STALE})')
    if n < PRICE_STALE:
        print('정상 — 알림 없음')
        return
    if n % PRICE_STALE:
        print(f'{n}영업일째 — 이미 알렸으므로 이번엔 발송 생략')
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
    elif rc == 0 and events is not None and '판정: 재검토 사유 없음' in txt:
        v, line, todo = 'ok', '사건 %d건 — 재검토 사유 없음' % events, None
    else:
        v, line, todo = 'error', '평가기 출력을 읽지 못했다', 'B 판정 규약 평가기 출력을 읽지 못했다 — AI 에게 확인 요청'
        print((p.stderr or '')[-600:])
    if drift and todo is None:
        todo = 'B 판정 규약 기저율이 등록값과 다르다(원자료 갱신?) — 판정 전에 원인 확인'
    return {'verdict': v, 'events': events, 'line': line, 'drift': drift, 'todo': todo, 'exit': rc}


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

    with open(OPSCHK, 'w', encoding='utf-8') as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(f"Level {cur.get('level')} · {cur.get('level_msg')} · 할 일 {len(cur.get('todo') or [])}건"
          + (f" · 판정 규약 {pb['line']}" if pb else ''))
    out('written', 1)

    # 알림 규칙: **나빠졌을 때만** 말한다. 같은 상태가 계속되면 조용하다
    # (분기 규약의 대응은 「지켜본다」이므로 매주 같은 말을 반복할 이유가 없다).
    lv0, lv1 = int(prev.get('level', 0) or 0), int(cur.get('level', 0) or 0)
    bad0 = {a['code'] for a in (prev.get('aum') or []) if a.get('state') != '정상'}
    bad1 = {a['code'] for a in (cur.get('aum') or []) if a.get('state') != '정상'}
    pb0, pb1 = (prev.get('protocol_b') or {}), (cur.get('protocol_b') or {})
    worse = ((lv1 > lv0) or bool(bad1 - bad0) or (not cur.get('ok', True) and prev.get('ok', True))
             # [v188] 판정 규약이 나빠진 것(정상→주의→역사 밖)·기저율 표류가 새로 생긴 것도 「악화」다
             or PB_RANK.get(pb1.get('verdict'), 0) > PB_RANK.get(pb0.get('verdict'), 0)
             or (bool(pb1.get('drift')) and not pb0.get('drift')))
    if not (cur.get('todo') and worse):
        print('상태 악화 없음 — 알림 생략')
        return
    out('alert', 1)
    notify('자동 점검에서 확인할 것', 'failure',
           '\n'.join(f'· {t}' for t in cur['todo'])
           + '\n(전략을 바꾸는 일이 아닙니다 — 기본 대응은 「지켜본다」입니다.)')


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

    notify('자동화 정상 작동 중', 'signal',
           '한 달에 한 번 보내는 생존 확인입니다.\n' + '\n'.join(lines) + '\n\n'
           '★ 이 알림이 **다음 달에 안 오면** 자동화가 멈춘 것입니다 — 그때만 손보시면 됩니다.\n'
           '(이상이 있으면 이 알림과 별개로 즉시 따로 갑니다.)')

    j['heartbeat'] = ym
    with open(OPSCHK, 'w', encoding='utf-8') as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
        f.write('\n')
    out('written', 1)
    print(f'{ym} 살아 있음 알림 발송 · ops_check.json 에 기록')


MODES = {'stale': mode_stale, 'rebalance': mode_rebalance,
         'channel': mode_channel, 'stats': mode_stats, 'price': mode_price,
         'check': mode_check, 'heartbeat': mode_heartbeat,
         'switchday': mode_switchday, 'near': mode_near}


def main():
    m = sys.argv[1] if len(sys.argv) > 1 else ''
    if m not in MODES:
        raise SystemExit('사용: python3 deploy/watchdog.py '
                 '{stale|rebalance|switchday|near|channel|stats|price|check|heartbeat}')
    try:
        MODES[m]()
    except Exception as e:                        # 감시가 파이프라인을 죽이지 않는다
        print(f'[경고] 파수꾼 {m} 실패: {type(e).__name__}: {e}', file=sys.stderr)
        out('alert', 1)


if __name__ == '__main__':
    main()
