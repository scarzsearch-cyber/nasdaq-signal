#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v73] 배치 실패 알림 — Telegram / Discord Webhook.

GitHub Actions 의 `if: failure()` 스텝에서 호출된다. secret 은 코드에 두지 않고
GitHub Secrets 로 받는다 (환경변수):
  KAKAO_REST_API_KEY + KAKAO_REFRESH_TOKEN     — 카카오톡 "나에게 보내기" (v77, 권장)
  DISCORD_WEBHOOK_URL                          — 디스코드 웹훅이면 이것 하나
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID        — 텔레그램이면 이 둘
사용:  python3 deploy/notify.py "<워크플로 이름>" "<상태>" "<상세/오류요약>"

종료코드 [2026-09-04 코드리뷰로 신설] — 종전에는 항상 0 이라 「채널이 전부 실패」와
「채널이 아예 없음」이 같은 초록불이었다:
  0  한 곳이라도 도착
  2  설정된 채널이 있는데 전부 전송 실패 (토큰 만료 등 — 사람이 손볼 것)
  3  채널 미설정 (알림은 부가 기능이므로 여기서 멈추는 것이 목적은 아니다)
호출처 3곳 확인 — daily-signal·monthly-stats 는 `if: failure()` 안이라 이미 빨간불이고,
notify-test.yml 은 「도착했나」를 재는 워크플로라 도착하지 않으면 빨간불이 옳다.
watchdog·signal_alert 는 subprocess.call 이라 코드를 읽지 않는다(종전 동작 유지).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

SITE = 'https://scarzsearch-cyber.github.io/nasdaq-signal/'

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


KAKAO_TEXT_MAX = 180     # 카카오 텍스트 템플릿 한도(200)에 여유를 둔 값 — 종전과 동일


def kakao_chunks(text, limit=KAKAO_TEXT_MAX):
    """카카오 한 건에 안 들어가는 글을 **자르지 않고** 나눈다.
    (1/2) 머리표가 붙으므로 그만큼(8자) 빼고 담는다. 줄 단위로 끊고,
    한 줄이 통째로 넘치면 그 줄만 글자 단위로 쪼갠다."""
    room = limit - 8
    if len(text) <= limit:
        return [text]
    out, cur = [], ''
    for ln in text.split('\n'):
        while len(ln) > room:                      # 한 줄이 혼자 넘칠 때
            if cur:
                out.append(cur); cur = ''
            out.append(ln[:room]); ln = ln[room:]
        if not cur:
            cur = ln
        elif len(cur) + 1 + len(ln) <= room:
            cur += '\n' + ln
        else:
            out.append(cur); cur = ln
    if cur:
        out.append(cur)
    return out


def post(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json',
                                          **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def main():
    wf = sys.argv[1] if len(sys.argv) > 1 else '(워크플로)'
    status = sys.argv[2] if len(sys.argv) > 2 else 'failure'
    detail = sys.argv[3] if len(sys.argv) > 3 else ''
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    job = os.environ.get('GITHUB_JOB', '')
    url = f'https://github.com/{repo}/actions/runs/{run_id}' if repo and run_id else ''
    kst = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
    icon = {'failure': '❌', 'signal': '🔔'}.get(status, '✅')
    text = (f'{icon} [{wf}] {status}\n'
            f'job: {job} · {kst}\n'
            + (f'{detail}\n' if detail else '')
            + (f'{url}' if url else ''))

    sent = False
    configured = []          # 설정된 채널 이름 — 실패와 미설정을 구별하려면 필요하다
    dc = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()
    if dc:
        configured.append('Discord')
        try:
            post(dc, {'content': text})
            print('Discord 알림 전송')
            sent = True
        except Exception as e:
            print(f'[경고] Discord 전송 실패: {e}', file=sys.stderr)
    tk = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    ch = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if tk and ch:
        configured.append('Telegram')
        try:
            post(f'https://api.telegram.org/bot{tk}/sendMessage',
                 {'chat_id': ch, 'text': text, 'disable_web_page_preview': True})
            print('Telegram 알림 전송')
            sent = True
        except Exception as e:
            print(f'[경고] Telegram 전송 실패: {e}', file=sys.stderr)
    kk = os.environ.get('KAKAO_REST_API_KEY', '').strip()
    kr = os.environ.get('KAKAO_REFRESH_TOKEN', '').strip()
    if kk and kr:
        configured.append('카카오')
        try:
            import urllib.parse
            body = urllib.parse.urlencode({'grant_type': 'refresh_token',
                                           'client_id': kk, 'refresh_token': kr}).encode()
            req = urllib.request.Request('https://kauth.kakao.com/oauth/token', data=body)
            with urllib.request.urlopen(req, timeout=30) as r:
                at = json.loads(r.read()).get('access_token')
            # [2026-09-04 코드리뷰] 종전 text[:180] 은 **말없이 잘랐다**. 실측 길이 —
            # heartbeat 363 · switchday 308 · near 307 · signal_alert 251 · rebalance 224 ·
            # stale 215자로 6종 전부 초과였고, 카카오가 유일한 등록 채널이라 잘리지 않은
            # 사본이 어디에도 없었다. 잘려 나간 것이 하필 각 알림의 **사용법 문장**이다:
            # heartbeat 의 「다음 달에 안 오면 자동화가 멈춘 것입니다」(v177 의 존재 이유),
            # switchday 의 「이미 체결하셨다면 무시하세요」(v192), near 의 「45%는 되돌아갑니다」
            # (04 §7 Q5 가 0.33배로 값을 매긴 미리 팔기를 막는 문장).
            # → 자르지 않고 **여러 건으로 나눠 보낸다**. 한 건이라도 실패하면 실패로 본다.
            parts = kakao_chunks(text)
            for i, part in enumerate(parts, 1):
                head = f'({i}/{len(parts)}) ' if len(parts) > 1 else ''
                tpl = json.dumps({'object_type': 'text', 'text': head + part,
                                  'link': {'web_url': SITE, 'mobile_web_url': SITE},
                                  'button_title': '화면 열기'}, ensure_ascii=False)
                body = urllib.parse.urlencode({'template_object': tpl}).encode()
                req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                                             data=body, headers={'Authorization': f'Bearer {at}'})
                with urllib.request.urlopen(req, timeout=30) as r:
                    res = json.loads((r.read() or b'{}').decode('utf-8', 'replace') or '{}')
                # ★ 카카오는 HTTP 200 에 실패 코드를 담아 거절한다 — 본문을 봐야 안다.
                if int(res.get('result_code', 0)) != 0:
                    raise RuntimeError(f'카카오 result_code={res.get("result_code")} {res}')
            print(f'카카오톡 나에게 보내기 전송 ({len(parts)}건)')
            sent = True
        except Exception as e:
            print(f'[경고] 카카오 전송 실패: {e}', file=sys.stderr)
    # [2026-09-04 코드리뷰] 종전에는 「설정된 채널이 전부 실패」와 「채널이 없음」을
    # 같은 문장으로 보고하고 항상 종료코드 0 이었다. 전환일에 카카오 토큰이 만료돼
    # 알림이 사라져도 로그는 「설정 안 됨」이라 말하고 잡은 초록불이었다(v178·v120 계열).
    # → 둘을 갈라 **종료코드로** 알린다. 0=한 곳이라도 도착 · 2=설정됐는데 전부 실패 ·
    #   3=채널 없음. 호출자(signal_alert·watchdog)는 subprocess.call 이라 지금은 코드를
    #   안 읽지만, 워크플로 스텝이 non-zero 를 보고 if: failure() 로 이슈·메일을 낼 수 있다.
    if sent:
        return 0
    if configured:
        print(f'[실패] 설정된 알림 채널({", ".join(configured)})이 전부 전송에 실패했다 — '
              f'미설정이 아니다. 위 [경고] 줄을 보라.', file=sys.stderr)
        return 2
    print('알림 secret 미설정 (KAKAO_* / DISCORD_WEBHOOK_URL / TELEGRAM_*) — 생략')
    return 3


if __name__ == '__main__':
    sys.exit(main() or 0)
