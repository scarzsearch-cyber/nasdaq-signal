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

사용:
    python3 deploy/watchdog.py stale      # 신호가 며칠째 그대로인가
    python3 deploy/watchdog.py channel    # 알림 채널이 살아 있는가 (메시지 안 보냄)
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


MODES = {'stale': mode_stale, 'channel': mode_channel, 'check': mode_check}


def main():
    m = sys.argv[1] if len(sys.argv) > 1 else ''
    if m not in MODES:
        raise SystemExit('사용: python3 deploy/watchdog.py {stale|channel|check}')
    try:
        MODES[m]()
    except Exception as e:                        # 감시가 파이프라인을 죽이지 않는다
        print(f'[경고] 파수꾼 {m} 실패: {type(e).__name__}: {e}', file=sys.stderr)
        out('alert', 1)


if __name__ == '__main__':
    main()
