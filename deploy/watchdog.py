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

  ⑤ [v171] **성과 스냅샷이 안 갱신되는** 경우 (monthly-stats.yml 이 건너뜀)
     → ① 과 같은 구멍인데 **훨씬 안 보인다**: 신호는 매일이라 며칠만 밀려도
     화면 신선도 도트가 티를 내지만, 성과표는 월 1회라 두 달이 밀려도 화면이
     똑같아 보인다. 매매와 무관하지만 「지금 내 전략이 어떤 성적인가」의
     근거가 조용히 낡는다.

사용:
    python3 deploy/watchdog.py stale      # 신호가 며칠째 그대로인가
    python3 deploy/watchdog.py rebalance  # 오늘이 방어 재조정일인가 (30일 주기)
    python3 deploy/watchdog.py channel    # 알림 채널이 살아 있는가 (메시지 안 보냄)
    python3 deploy/watchdog.py stats      # 성과 스냅샷이 갱신되고 있는가 (월 1회)
    python3 deploy/watchdog.py check      # 점검.py 자동 실행 → data/ops_check.json

각 모드는 **항상 0 으로 끝난다**(감시가 파이프라인을 죽이면 안 된다).
사람이 개입해야 하는 상황이면 GITHUB_OUTPUT 에 `alert=1` 을 남긴다 —
워크플로가 그걸 보고 이슈를 연다.
"""
import json
import os
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
# ③ 점검 자동 실행 — 사람이 기억해서 파이썬을 돌릴 의무를 없앤다
# --------------------------------------------------------------------------
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

    with open(OPSCHK, 'w', encoding='utf-8') as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(f"Level {cur.get('level')} · {cur.get('level_msg')} · 할 일 {len(cur.get('todo') or [])}건")
    out('written', 1)

    # 알림 규칙: **나빠졌을 때만** 말한다. 같은 상태가 계속되면 조용하다
    # (분기 규약의 대응은 「지켜본다」이므로 매주 같은 말을 반복할 이유가 없다).
    lv0, lv1 = int(prev.get('level', 0) or 0), int(cur.get('level', 0) or 0)
    bad0 = {a['code'] for a in (prev.get('aum') or []) if a.get('state') != '정상'}
    bad1 = {a['code'] for a in (cur.get('aum') or []) if a.get('state') != '정상'}
    worse = (lv1 > lv0) or bool(bad1 - bad0) or (not cur.get('ok', True) and prev.get('ok', True))
    if not (cur.get('todo') and worse):
        print('상태 악화 없음 — 알림 생략')
        return
    out('alert', 1)
    notify('자동 점검에서 확인할 것', 'failure',
           '\n'.join(f'· {t}' for t in cur['todo'])
           + '\n(전략을 바꾸는 일이 아닙니다 — 기본 대응은 「지켜본다」입니다.)')


MODES = {'stale': mode_stale, 'rebalance': mode_rebalance,
         'channel': mode_channel, 'stats': mode_stats, 'check': mode_check}


def main():
    m = sys.argv[1] if len(sys.argv) > 1 else ''
    if m not in MODES:
        raise SystemExit('사용: python3 deploy/watchdog.py '
                 '{stale|rebalance|channel|stats|check}')
    try:
        MODES[m]()
    except Exception as e:                        # 감시가 파이프라인을 죽이지 않는다
        print(f'[경고] 파수꾼 {m} 실패: {type(e).__name__}: {e}', file=sys.stderr)
        out('alert', 1)


if __name__ == '__main__':
    main()
