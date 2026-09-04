#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v77] 카카오톡 알림 최초 1회 설정 도우미 — **본인 PC에서 직접** 실행하세요.

mobi-market 에서 쓰던 카카오 개발자 앱을 그대로 재활용합니다.
(developers.kakao.com > 내 애플리케이션 — "카카오톡 메시지 전송" 동의항목이
이미 켜져 있는 그 앱. REST API 키를 사용합니다. JavaScript 키 아님!)

실행:  python deploy/kakao_setup.py
절차:  ① REST API 키 입력 → ② 그 앱에 등록된 Redirect URI 아무거나 입력
      → ②-1 Client Secret 이 ON 이면 값 입력(OFF 면 Enter)
      → ③ 출력된 주소를 브라우저에서 열고 동의 → ④ 이동된 주소창의 code= 값 붙여넣기
      → ⑤ 출력된 refresh_token 을 GitHub Secrets 에 등록

토큰은 이 화면에만 출력되고 어디에도 저장·전송되지 않습니다.
"""
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


def auth_url(key, uri):
    query = urllib.parse.urlencode({
        'response_type': 'code', 'client_id': key,
        'redirect_uri': uri, 'scope': 'talk_message',
    })
    return 'https://kauth.kakao.com/oauth/authorize?' + query


def token_body(key, uri, code, client_secret=''):
    """Client Secret OFF 기존 앱과 ON 신규 앱의 토큰 발급 본문을 만든다."""
    params = {'grant_type': 'authorization_code', 'client_id': key,
              'redirect_uri': uri, 'code': code}
    if client_secret:
        params['client_secret'] = client_secret
    return urllib.parse.urlencode(params).encode()


def token_values(tok):
    """성공 응답의 필수 토큰을 확인하되 오류에 토큰 값을 노출하지 않는다."""
    if not isinstance(tok, dict):
        raise ValueError('응답이 JSON 객체가 아니다')
    access, refresh = tok.get('access_token'), tok.get('refresh_token')
    if not isinstance(access, str) or not access.strip():
        raise ValueError('응답에 access_token 이 없다')
    if not isinstance(refresh, str) or not refresh.strip():
        raise ValueError('응답에 refresh_token 이 없다')
    if '\r' in access or '\n' in access or '\r' in refresh or '\n' in refresh:
        raise ValueError('토큰 응답에 줄바꿈이 섞여 있다')
    return access.strip(), refresh.strip()


def oauth_error(raw):
    """HTTP 오류 본문에서 비밀값 없이 사람이 고칠 수 있는 필드만 꺼낸다."""
    try:
        value = json.loads(raw.decode('utf-8', 'replace'))
    except Exception:
        return '응답 본문은 JSON 이 아님'
    if not isinstance(value, dict):
        return '응답 본문 형식이 잘못됨'
    parts = [str(value[k]) for k in ('error', 'error_description', 'error_code')
             if value.get(k) is not None]
    return ' / '.join(parts) if parts else '오류 설명 없음'


def message_ok(raw):
    try:
        result = json.loads(raw or b'{}')
    except (TypeError, ValueError, json.JSONDecodeError):
        raise ValueError('시험 발송 응답 형식이 잘못됐다')
    if not isinstance(result, dict) or type(result.get('result_code')) is not int:
        raise ValueError('시험 발송 응답 형식이 잘못됐다')
    code = result['result_code']
    if code != 0:
        raise RuntimeError(f'카카오 메시지 result_code={code}')


def main():
    print(__doc__)
    key = input('① REST API 키: ').strip()
    uri = input('② 앱에 등록된 Redirect URI (mobi-market 페이지 주소 등): ').strip()
    if not key or not uri:
        raise SystemExit('REST API 키와 Redirect URI 는 비울 수 없습니다.')
    client_secret = os.environ.get('KAKAO_CLIENT_SECRET', '').strip()
    if not client_secret:
        client_secret = getpass.getpass(
            '②-1 Client Secret (REST API 키 설정이 OFF 면 Enter): ').strip()
    auth = auth_url(key, uri)
    print('\n③ 아래 주소를 브라우저에서 열고 [동의하고 계속하기]:\n\n   ' + auth)
    print('\n   동의하면 Redirect URI 로 이동합니다. 그 페이지가 뭐든 상관없고,')
    print('   주소창에 붙은  ?code=XXXX  의 XXXX 만 필요합니다.')
    code = input('\n④ code 값: ').strip()
    if not code:
        raise SystemExit('code 값은 비울 수 없습니다.')
    body = token_body(key, uri, code, client_secret)
    req = urllib.request.Request('https://kauth.kakao.com/oauth/token', data=body)
    # [코드리뷰 2026-09-04] 카카오는 code 가 만료-재사용이면 **HTTP 400 + JSON 본문**을 준다
    #   (RFC 6749 5.2). urlopen 은 그때 예외를 던지므로 종전 코드에서는 아래 '실패:' 안내가
    #   영영 못 돌고 생짜 traceback 이 떴다. 정작 이유가 적힌 error_description 은 그 예외
    #   안에 있다 - 꺼내서 보여준다. code 는 1회용이고 10분쯤 지나면 죽는다.
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = oauth_error(e.read())
        sys.exit(f'실패: HTTP {e.code} {detail}\n'
                 '  code 는 1회용이고 10분쯤 뒤 만료됩니다. ③ 주소를 다시 열어 새 code 를 받으세요.\n'
                 '  Client Secret 이 ON 이면 같은 REST API 키의 값을 정확히 입력해야 합니다.')
    except Exception as e:
        sys.exit(f'실패: 토큰 요청을 보내지 못했습니다 - {e}')
    try:
        access_token, refresh_token = token_values(tok)
    except ValueError as e:
        # 종전 f'{tok}' 는 access_token 이 든 성공 비슷한 응답을 콘솔에 통째로 노출했다.
        sys.exit(f'실패: 토큰 응답 형식 오류 - {e}')
    # [코드리뷰 2026-09-04] 시험 발송을 **성공 안내보다 먼저** 한다. 종전에는 토큰 모양만
    #   보고 '성공!' 과 등록할 secret 을 먼저 찍었고, 정작 유일한 실기능 검증인 발송 실패는
    #   그 아래 경고로 붙었다 - 동의항목이 꺼져 있어도 사용자는 성공으로 읽고 secret 을
    #   등록했다. keepalive 는 토큰 엔드포인트만 두드리므로 전환일까지 안 드러난다.
    sent = False
    try:
        tpl = json.dumps({'object_type': 'text',
                          'text': '나스닥 신호 알림 연결 시험 — 이 메시지가 보이면 성공',
                          'link': {'web_url': 'https://scarzsearch-cyber.github.io/nasdaq-signal/'}},
                         ensure_ascii=False)
        body = urllib.parse.urlencode({'template_object': tpl}).encode()
        req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                                     data=body,
                                     headers={'Authorization': f'Bearer {access_token}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            message_ok(r.read())
        print('\n지금 카카오톡(나와의 채팅)으로 시험 메시지를 보냈습니다 — 확인해 보세요.')
        sent = True
    except Exception as e:
        print(f'\n[경고] 시험 발송 실패: {e} — 동의항목(카카오톡 메시지 전송)이 켜져 있는지 확인.')

    if sent:
        print('\n⑤ 성공! GitHub 저장소 → Settings → Secrets and variables → Actions 에 등록:')
    else:
        print('⑤ 토큰은 받았지만 **발송이 안 됐습니다.** 위 경고를 먼저 해결하세요.')
        print('   (그대로 등록하면 평소엔 조용하다가 정작 전환일에 알림이 안 옵니다.)')
        print('   해결 뒤 등록할 값:')
    print(f'   KAKAO_REST_API_KEY  = {key}')
    print(f'   KAKAO_REFRESH_TOKEN = {refresh_token}')
    if client_secret:
        print('   KAKAO_CLIENT_SECRET = (②-1에서 입력한 값을 별도 secret 으로 등록)')
    print('\n등록 후 Actions 탭 → "알림 테스트" → Run workflow 로 확인하세요.')
    print('(선택) 토큰 자동 연명·교체까지 원하면 GH_PAT secret 도 등록 — 03 문서 참조.')
    return 0 if sent else 2


def selftest():
    url = auth_url('key&x', 'https://example.com/a?b=1')
    parsed = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert parsed['client_id'] == ['key&x']
    assert parsed['redirect_uri'] == ['https://example.com/a?b=1']
    legacy_body = urllib.parse.urlencode({
        'grant_type': 'authorization_code', 'client_id': 'key',
        'redirect_uri': 'https://example.com/cb', 'code': 'code'}).encode()
    assert token_body('key', 'https://example.com/cb', 'code') == legacy_body
    with_secret = urllib.parse.parse_qs(
        token_body('key', 'https://example.com/cb', 'code', 'client-secret').decode())
    assert with_secret['client_secret'] == ['client-secret']
    assert token_values({'access_token': ' a ', 'refresh_token': ' r '}) == ('a', 'r')
    try:
        token_values({'access_token': 'secret-access'})
    except ValueError as e:
        assert 'secret-access' not in str(e)
    else:
        raise AssertionError('refresh_token 없는 응답이 통과했다')
    for bad in (
            {'access_token': 'access\nFAKE=value', 'refresh_token': 'refresh'},
            {'access_token': 'access', 'refresh_token': 'refresh\r\nFAKE=value'}):
        try:
            token_values(bad)
        except ValueError as e:
            assert 'FAKE' not in str(e)
        else:
            raise AssertionError('줄바꿈이 섞인 토큰이 통과했다')
    assert 'sensitive' not in oauth_error(
        b'{"error":"bad","access_token":"sensitive"}')
    message_ok(b'{"result_code":0}')
    try:
        message_ok(b'{"result_code":-2}')
    except RuntimeError:
        pass
    else:
        raise AssertionError('실패 result_code 가 통과했다')
    for bad in (b'{"result_code":0.5}', b'{"result_code":"0"}'):
        try:
            message_ok(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('정수가 아닌 result_code 가 통과했다')
    print('kakao_setup selftest: PASS (Client Secret 선택 · URL 인코딩 · 토큰 비노출/줄바꿈 거부 · 발송 응답)')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        sys.exit(main() or 0)
