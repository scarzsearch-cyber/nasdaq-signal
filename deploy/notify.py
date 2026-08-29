#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v73] 배치 실패 알림 — Telegram / Discord Webhook.

GitHub Actions 의 `if: failure()` 스텝에서 호출된다. secret 은 코드에 두지 않고
GitHub Secrets 로 받는다 (환경변수):
  KAKAO_REST_API_KEY + KAKAO_REFRESH_TOKEN     — 카카오톡 "나에게 보내기" (v77, 권장)
  DISCORD_WEBHOOK_URL                          — 디스코드 웹훅이면 이것 하나
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID        — 텔레그램이면 이 둘
둘 다 없으면 "secret 없음" 만 출력하고 성공 종료한다 (알림은 부가 기능 — 알림
실패가 파이프라인을 또 실패시키면 안 된다).

사용:  python3 deploy/notify.py "<워크플로 이름>" "<상태>" "<상세/오류요약>"
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
    dc = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()
    if dc:
        try:
            post(dc, {'content': text})
            print('Discord 알림 전송')
            sent = True
        except Exception as e:
            print(f'[경고] Discord 전송 실패: {e}', file=sys.stderr)
    tk = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    ch = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if tk and ch:
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
        try:
            import urllib.parse
            body = urllib.parse.urlencode({'grant_type': 'refresh_token',
                                           'client_id': kk, 'refresh_token': kr}).encode()
            req = urllib.request.Request('https://kauth.kakao.com/oauth/token', data=body)
            with urllib.request.urlopen(req, timeout=30) as r:
                at = json.loads(r.read()).get('access_token')
            tpl = json.dumps({'object_type': 'text', 'text': text[:180],
                              'link': {'web_url': SITE, 'mobile_web_url': SITE},
                              'button_title': '화면 열기'}, ensure_ascii=False)
            body = urllib.parse.urlencode({'template_object': tpl}).encode()
            req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                                         data=body, headers={'Authorization': f'Bearer {at}'})
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
            print('카카오톡 나에게 보내기 전송')
            sent = True
        except Exception as e:
            print(f'[경고] 카카오 전송 실패: {e}', file=sys.stderr)
    if not sent:
        print('알림 secret 미설정 (KAKAO_* / DISCORD_WEBHOOK_URL / TELEGRAM_*) — 생략')


if __name__ == '__main__':
    main()
