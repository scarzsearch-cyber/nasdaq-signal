#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v73/v203] 배치 실패 알림 — Kakao / Telegram / Discord Webhook.

GitHub Actions 의 `if: failure()` 스텝에서 호출된다. secret 은 코드에 두지 않고
GitHub Secrets 로 받는다 (환경변수):
  KAKAO_REST_API_KEY + KAKAO_REFRESH_TOKEN     — 카카오톡 "나에게 보내기" (v77, 권장)
  KAKAO_CLIENT_SECRET                          — Client Secret이 ON일 때 추가(신규 앱 기본)
  DISCORD_WEBHOOK_URL                          — 디스코드 웹훅이면 이것 하나
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID        — 텔레그램이면 이 둘
사용:  python3 deploy/notify.py "<워크플로 이름>" "<상태>" "<상세/오류요약>"

종료코드 [2026-09-04 코드리뷰로 신설] — 종전에는 항상 0 이라 「채널이 전부 실패」와
「채널이 아예 없음」이 같은 초록불이었다:
  0  한 곳이라도 도착
  2  설정된 채널이 있는데 전부 전송 실패 (토큰 만료 등 — 사람이 손볼 것)
  3  채널 미설정 (알림은 부가 기능이므로 여기서 멈추는 것이 목적은 아니다)
호출처 확인 — daily-signal·monthly-stats 는 `if: failure()` 안이라 이미 빨간불이고,
notify-test.yml 은 「도착했나」를 재는 워크플로라 도착하지 않으면 빨간불이 옳다.
watchdog·signal_alert 도 종료코드를 읽어 실패 시 이슈 fallback 또는 다음 슬롯 재시도로 넘긴다.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

from kakao_keepalive import (activate_refresh_token, json_object, message_ok,
                             rotation_warning, set_github_secret, token_values)

SITE = 'https://scarzsearch-cyber.github.io/nasdaq-signal/'

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
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
        return r.status, r.read()


def telegram_ok(raw):
    """Telegram Bot API의 HTTP 본문 성공 계약(``ok: true``)을 확인한다."""
    result = json_object(raw or b'{}', 'Telegram')
    if type(result.get('ok')) is not bool:
        raise ValueError('Telegram 응답의 ok 형식이 잘못됐다')
    if not result['ok']:
        # description 원문에는 사용자 입력이 섞일 수 있어 로그에 되풀이하지 않는다.
        raise RuntimeError('Telegram API가 실패(ok=false)를 반환했다')


def kakao_token_body(key, refresh_token, client_secret=''):
    """기존 Secret-OFF 앱은 그대로 두고, 값이 있을 때만 client_secret을 보낸다."""
    fields = {'grant_type': 'refresh_token', 'client_id': key,
              'refresh_token': refresh_token}
    if client_secret:
        fields['client_secret'] = client_secret
    return urllib.parse.urlencode(fields).encode()


def kakao_send(access_token, template):
    """카카오 메시지 한 건을 보내고 HTTP 200 내부의 실패 코드까지 확인한다."""
    body = urllib.parse.urlencode({
        'template_object': json.dumps(template, ensure_ascii=False)}).encode()
    req = urllib.request.Request(
        'https://kapi.kakao.com/v2/api/talk/memo/default/send', data=body,
        headers={'Authorization': f'Bearer {access_token}'})
    with urllib.request.urlopen(req, timeout=30) as r:
        message_ok(r.read())


def selftest():
    plain = urllib.parse.parse_qs(kakao_token_body('key', 'refresh').decode())
    sealed = urllib.parse.parse_qs(kakao_token_body('key', 'refresh', 'secret').decode())
    assert 'client_secret' not in plain
    assert sealed.get('client_secret') == ['secret']
    parts = kakao_chunks('첫 줄\n' + '가' * 400)
    assert ''.join(part.replace('\n', '') for part in parts) == ('첫 줄' + '가' * 400)
    assert all(len(part) <= KAKAO_TEXT_MAX for part in parts)
    telegram_ok(b'{"ok":true,"result":{}}')
    for bad in (b'{"ok":false,"description":"secret"}', b'{"ok":1}'):
        try:
            telegram_ok(bad)
        except (RuntimeError, ValueError) as e:
            assert 'secret' not in str(e)
        else:
            raise AssertionError('Telegram 실패/잘못된 응답이 통과했다')
    class Response:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return self.body

    names = ('KAKAO_REST_API_KEY', 'KAKAO_REFRESH_TOKEN', 'KAKAO_CLIENT_SECRET',
             'GH_PAT', 'GITHUB_REPOSITORY', 'GITHUB_ENV', 'DISCORD_WEBHOOK_URL',
             'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID')
    old_env = {k: os.environ.get(k) for k in names}
    old_open = urllib.request.urlopen
    old_set = globals()['set_github_secret']
    try:
        for name in names:
            os.environ.pop(name, None)
        os.environ.update(KAKAO_REST_API_KEY='key', KAKAO_REFRESH_TOKEN='old-refresh',
                          GH_PAT='pat', GITHUB_REPOSITORY='owner/repo')

        # 회전 토큰 저장 성공: 의도한 메시지를 보내고 새 토큰을 현재 잡에도 반영한다.
        replies = iter([Response(b'{"access_token":"access","refresh_token":"new-refresh"}'),
                        Response(b'{"result_code":0}')])
        urllib.request.urlopen = lambda *a, **k: next(replies)
        globals()['set_github_secret'] = lambda *a, **k: True
        assert main() == 0
        assert os.environ['KAKAO_REFRESH_TOKEN'] == 'new-refresh'

        # 저장 실패: 긴급 경고와 원래 메시지가 가도 미래 인증은 깨졌으므로 non-zero다.
        os.environ['KAKAO_REFRESH_TOKEN'] = 'old-refresh'
        replies = iter([Response(b'{"access_token":"access","refresh_token":"newer-refresh"}'),
                        Response(b'{"result_code":0}'), Response(b'{"result_code":0}')])
        urllib.request.urlopen = lambda *a, **k: next(replies)
        globals()['set_github_secret'] = lambda *a, **k: False
        assert main() == 2
    finally:
        urllib.request.urlopen = old_open
        globals()['set_github_secret'] = old_set
        for name, value in old_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    print('notify selftest: PASS (Client Secret · 긴 메시지 · refresh 회전 저장/실패)')


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
            # webhook 비밀값은 URL 경로에 있다. 예외 문자열이 URL을 포함해도 로그로
            # 새지 않도록 종류만 남긴다.
            print(f'[경고] Discord 전송 실패: {type(e).__name__}', file=sys.stderr)
    tk = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    ch = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if tk and ch:
        configured.append('Telegram')
        try:
            _, raw = post(f'https://api.telegram.org/bot{tk}/sendMessage',
                          {'chat_id': ch, 'text': text, 'disable_web_page_preview': True})
            telegram_ok(raw)
            print('Telegram 알림 전송')
            sent = True
        except Exception as e:
            # Bot token도 URL 경로에 있으므로 예외 원문은 출력하지 않는다.
            print(f'[경고] Telegram 전송 실패: {type(e).__name__}', file=sys.stderr)
    elif tk or ch:
        configured.append('Telegram')
        print('[경고] Telegram token/chat ID 중 하나만 설정돼 전송할 수 없다', file=sys.stderr)
    kk = os.environ.get('KAKAO_REST_API_KEY', '').strip()
    kr = os.environ.get('KAKAO_REFRESH_TOKEN', '').strip()
    ks = os.environ.get('KAKAO_CLIENT_SECRET', '').strip()
    rotation_unstored = False
    if kk and kr:
        configured.append('카카오')
        try:
            body = kakao_token_body(kk, kr, ks)
            req = urllib.request.Request('https://kauth.kakao.com/oauth/token', data=body)
            with urllib.request.urlopen(req, timeout=30) as r:
                tok = json_object(r.read(), '토큰 갱신')
            at, new_rt = token_values(tok)
            if new_rt:
                try:
                    activate_refresh_token(new_rt)
                except Exception as e:
                    rotation_unstored = True
                    print(f'[경고] 현재 잡에 새 refresh 토큰 반영 실패: '
                          f'{type(e).__name__}: {e}', file=sys.stderr)
                pat = os.environ.get('GH_PAT', '').strip()
                repo_name = os.environ.get('GITHUB_REPOSITORY', '').strip()
                if pat and repo_name and set_github_secret(new_rt, pat, repo_name):
                    print('KAKAO_REFRESH_TOKEN secret 자동 교체 완료')
                else:
                    rotation_unstored = True
                    print('[경고] 새 refresh 토큰 저장 실패 — 기존 secret 은 이미 무효',
                          file=sys.stderr)
                    try:
                        kakao_send(at, rotation_warning(repo_name))
                        print('저장 토큰 무효 긴급 경고를 카카오톡으로 발송')
                    except Exception as e:
                        print(f'[경고] 저장 실패 긴급 경고도 보내지 못함: '
                              f'{type(e).__name__}: {e}', file=sys.stderr)
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
                kakao_send(at, {'object_type': 'text', 'text': head + part,
                                'link': {'web_url': SITE, 'mobile_web_url': SITE},
                                'button_title': '화면 열기'})
            print(f'카카오톡 나에게 보내기 전송 ({len(parts)}건)')
            sent = True
        except Exception as e:
            print(f'[경고] 카카오 전송 실패: {e}', file=sys.stderr)
    elif kk or kr:
        configured.append('카카오')
        print('[경고] 카카오 REST key/refresh token 중 하나만 설정돼 전송할 수 없다',
              file=sys.stderr)
    # [2026-09-04 코드리뷰] 종전에는 「설정된 채널이 전부 실패」와 「채널이 없음」을
    # 같은 문장으로 보고하고 항상 종료코드 0 이었다. 전환일에 카카오 토큰이 만료돼
    # 알림이 사라져도 로그는 「설정 안 됨」이라 말하고 잡은 초록불이었다(v178·v120 계열).
    # → 둘을 갈라 **종료코드로** 알린다. 0=한 곳이라도 도착 · 2=설정됐는데 전부 실패 ·
    #   3=채널 없음. 호출자(signal_alert·watchdog)는 subprocess.call 의 반환값을 읽어
    #   실패를 alert=1 또는 non-zero 로 올리고, 워크플로가 이슈·메일 통로로 이어 간다.
    if rotation_unstored:
        print('[실패] 카카오 새 refresh 토큰을 미래 실행용 secret 에 저장하지 못했다',
              file=sys.stderr)
        return 2
    if sent:
        return 0
    if configured:
        print(f'[실패] 설정된 알림 채널({", ".join(configured)})이 전부 전송에 실패했다 — '
              f'미설정이 아니다. 위 [경고] 줄을 보라.', file=sys.stderr)
        return 2
    print('알림 secret 미설정 (KAKAO_* / DISCORD_WEBHOOK_URL / TELEGRAM_*) — 생략')
    return 3


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        sys.exit(main() or 0)
