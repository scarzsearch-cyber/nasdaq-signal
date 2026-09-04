#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v77] 카카오 refresh 토큰 연명 — 매일 신호 갱신 뒤에 돈다.

왜 필요한가: 카카오 refresh 토큰은 약 2개월 시한부다. 알림은 1년에 몇 번만
발송되므로 그냥 두면 정작 전환일에 토큰이 죽어 있다. 그래서 매일 한 번
토큰을 갱신(재발급)해서 시한을 계속 민다.

토큰 교체: 만료 1개월 안쪽으로 들어가면 카카오가 응답에 **새 refresh 토큰**을
준다. GH_PAT(secrets 쓰기 권한의 fine-grained PAT) secret 이 있으면 gh CLI 로
저장소 secret 을 자동 교체한다. 없거나 교체에 실패하면 카카오톡으로
"저장된 기존 토큰은 이미 무효 — 지금 재설정" 경고를 보낸다
(아직 살아 있는 새 access 토큰으로).

토큰 값은 로그에 절대 출력하지 않는다.
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


def json_object(raw, what):
    """외부 API 응답을 객체로 제한한다. 토큰 자체는 오류문에 넣지 않는다."""
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f'{what} 응답이 JSON 객체가 아니다')
    return value


def token_values(tok):
    """카카오 갱신 응답의 필수/선택 토큰을 검증한다."""
    if not isinstance(tok, dict):
        raise ValueError('토큰 응답이 JSON 객체가 아니다')
    access = tok.get('access_token')
    refresh = tok.get('refresh_token')
    if not isinstance(access, str) or not access.strip():
        raise ValueError('토큰 응답에 access_token 이 없다')
    if refresh is not None and (not isinstance(refresh, str) or not refresh.strip()):
        raise ValueError('토큰 응답의 refresh_token 형식이 잘못됐다')
    return access.strip(), refresh.strip() if refresh else None


def refresh_body(key, refresh_token, client_secret=''):
    """Client Secret OFF 기존 앱과 ON 신규 앱의 갱신 본문을 함께 만든다."""
    params = {'grant_type': 'refresh_token', 'client_id': key,
              'refresh_token': refresh_token}
    if client_secret:
        params['client_secret'] = client_secret
    return urllib.parse.urlencode(params).encode()


def message_ok(raw):
    """카카오 메시지는 HTTP 200 안에도 실패 코드를 담을 수 있다."""
    result = json_object(raw or b'{}', '메시지')
    code = result.get('result_code')
    if type(code) is not int:
        raise ValueError('메시지 응답의 result_code 형식이 잘못됐다')
    if code != 0:
        raise RuntimeError(f'카카오 메시지 result_code={code}')


def set_github_secret(new_rt, pat, repo, runner=subprocess.run):
    """새 refresh token 을 GitHub Actions secret 으로 저장한다."""
    env = dict(os.environ, GH_TOKEN=pat, GH_PROMPT_DISABLED='1',
               GH_NO_UPDATE_NOTIFIER='1')
    try:
        p = runner(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--repo', repo],
                   input=new_rt.encode(), env=env, timeout=60)
        return p.returncode == 0
    except (OSError, subprocess.SubprocessError) as e:
        print(f'[경고] gh 실행 자체가 실패({type(e).__name__}) - 아래 수동 경고로 전환',
              file=sys.stderr)
        return False


def rotation_warning(repo):
    """새 토큰 저장 실패 뒤 보낼 긴급 안내 템플릿."""
    return {
        'object_type': 'text',
        'text': '[나스닥 신호] 카카오 새 refresh 토큰이 발급됐지만 GitHub secret '
                '자동 교체에 실패했습니다. 저장된 기존 토큰은 이미 무효입니다. '
                '지금 deploy/kakao_setup.py 를 다시 실행해 KAKAO_REFRESH_TOKEN secret 을 '
                '교체하세요. GH_PAT secret 을 등록하면 다음 교체부터 자동 처리됩니다.',
        'link': {'web_url': 'https://github.com/' + (repo or '')},
    }


def main():
    key = os.environ.get('KAKAO_REST_API_KEY', '').strip()
    rt = os.environ.get('KAKAO_REFRESH_TOKEN', '').strip()
    client_secret = os.environ.get('KAKAO_CLIENT_SECRET', '').strip()
    if not key or not rt:
        print('카카오 secret 미설정 — 연명 생략')
        return
    body = refresh_body(key, rt, client_secret)
    req = urllib.request.Request('https://kauth.kakao.com/oauth/token', data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json_object(r.read(), '토큰 갱신')
        at, new_rt = token_values(tok)
    except Exception as e:
        print(f'[경고] 카카오 토큰 갱신 실패({type(e).__name__}: {e}) - '
              '만료됐다면 deploy/kakao_setup.py 재실행 필요',
              file=sys.stderr)
        return 2
    # refresh_token 은 만료 1개월 안쪽일 때만 온다.
    print('카카오 access 토큰 갱신 OK' + (' · refresh 토큰 교체 필요 감지' if new_rt else ''))
    if not new_rt:
        return 0

    pat = os.environ.get('GH_PAT', '').strip()
    repo = os.environ.get('GITHUB_REPOSITORY', '').strip()
    if pat and repo:
        # [코드리뷰 2026-09-04] gh 가 PATH 에 없으면 subprocess.run 이 **returncode 를 내기 전에**
        #   FileNotFoundError 를 던진다. 종전에는 그것이 main() 밖으로 튀어 아래 카톡 경고를
        #   건너뛰었고, daily-signal.yml 의 continue-on-error 가 초록불로 덮었다.
        #   그 시점엔 카카오가 이미 새 토큰을 발급해 옛 토큰을 죽인 뒤라 복구 수단이 없다.
        if set_github_secret(new_rt, pat, repo):
            print('KAKAO_REFRESH_TOKEN secret 자동 교체 완료')
            return 0
        print('[경고] secret 자동 교체 실패 - 아래 수동 경고로 전환', file=sys.stderr)
    # PAT 없음/실패 — 본인에게 카카오로 경고 (지금 access 토큰은 살아 있다)
    try:
        tpl = json.dumps(rotation_warning(repo), ensure_ascii=False)
        body = urllib.parse.urlencode({'template_object': tpl}).encode()
        req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                                     data=body, headers={'Authorization': f'Bearer {at}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            message_ok(r.read())
        print('저장 토큰 무효 긴급 경고를 카카오톡으로 발송')
        # 경고는 도착했지만 새 토큰을 저장하지 못했다. continue-on-error 호출자가
        # 다음 작업은 계속하되 이 스텝을 실패로 표시할 수 있게 한다.
        return 2
    except Exception as e:
        print(f'[경고] 만료 예고 발송 실패: {type(e).__name__}: {e}', file=sys.stderr)
        return 3


def selftest():
    assert token_values({'access_token': ' a '}) == ('a', None)
    assert token_values({'access_token': 'a', 'refresh_token': ' r '}) == ('a', 'r')
    legacy_body = urllib.parse.urlencode({
        'grant_type': 'refresh_token', 'client_id': 'key',
        'refresh_token': 'refresh'}).encode()
    assert refresh_body('key', 'refresh') == legacy_body
    with_secret = urllib.parse.parse_qs(
        refresh_body('key', 'refresh', 'client-secret').decode())
    assert with_secret['client_secret'] == ['client-secret']
    warning = rotation_warning('owner/repo')
    assert '이미 무효' in warning['text'] and '한 달 안에 만료' not in warning['text']
    assert warning['link']['web_url'] == 'https://github.com/owner/repo'
    for bad in ({}, [], {'access_token': ''}, {'access_token': 'a', 'refresh_token': 3}):
        try:
            token_values(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('잘못된 토큰 응답이 통과했다')
    message_ok(b'{"result_code": 0}')
    try:
        message_ok(b'{"result_code": -2}')
    except RuntimeError:
        pass
    else:
        raise AssertionError('카카오 실패 본문이 통과했다')
    for bad in (b'{"result_code": 0.5}', b'{"result_code": "0"}'):
        try:
            message_ok(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('정수가 아닌 result_code 가 통과했다')

    calls = []
    class Result:
        returncode = 0
    def fake_runner(args, **kwargs):
        calls.append((args, kwargs))
        return Result()
    assert set_github_secret('new-token', 'pat', 'owner/repo', fake_runner)
    assert calls[0][1]['input'] == b'new-token' and calls[0][1]['timeout'] == 60
    def timeout_runner(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs['timeout'])
    assert not set_github_secret('new-token', 'pat', 'owner/repo', timeout_runner)

    class Response:
        def __init__(self, body):
            self.body = body
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return self.body

    old_open = urllib.request.urlopen
    names = ('KAKAO_REST_API_KEY', 'KAKAO_REFRESH_TOKEN', 'KAKAO_CLIENT_SECRET',
             'GH_PAT', 'GITHUB_REPOSITORY')
    old_env = {k: os.environ.get(k) for k in names}
    try:
        for k in names:
            os.environ.pop(k, None)
        os.environ.update(KAKAO_REST_API_KEY='key', KAKAO_REFRESH_TOKEN='refresh')

        replies = iter([Response(b'{"access_token":"access"}')])
        urllib.request.urlopen = lambda *a, **k: next(replies)
        assert main() == 0

        replies = iter([Response(b'{"access_token":"access","refresh_token":"new"}'),
                        Response(b'{"result_code":0}')])
        urllib.request.urlopen = lambda *a, **k: next(replies)
        assert main() == 2              # 경고는 갔지만 새 secret 은 아직 저장되지 않았다
    finally:
        urllib.request.urlopen = old_open
        for k, value in old_env.items():
            if value is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = value
    print('kakao_keepalive selftest: PASS (Client Secret 선택 · 응답 계약 · secret 저장 · 폴백)')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        sys.exit(main() or 0)
