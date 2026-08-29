#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v77] 카카오 refresh 토큰 연명 — 매일 신호 갱신 뒤에 돈다.

왜 필요한가: 카카오 refresh 토큰은 약 2개월 시한부다. 알림은 1년에 몇 번만
발송되므로 그냥 두면 정작 전환일에 토큰이 죽어 있다. 그래서 매일 한 번
토큰을 갱신(재발급)해서 시한을 계속 민다.

토큰 교체: 만료 1개월 안쪽으로 들어가면 카카오가 응답에 **새 refresh 토큰**을
준다. GH_PAT(secrets 쓰기 권한의 fine-grained PAT) secret 이 있으면 gh CLI 로
저장소 secret 을 자동 교체한다. 없으면 카카오톡으로 "토큰 곧 만료 — 재설정
필요" 경고를 보낸다 (아직 살아 있는 새 access 토큰으로).

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
except Exception:
    pass


def main():
    key = os.environ.get('KAKAO_REST_API_KEY', '').strip()
    rt = os.environ.get('KAKAO_REFRESH_TOKEN', '').strip()
    if not key or not rt:
        print('카카오 secret 미설정 — 연명 생략')
        return
    body = urllib.parse.urlencode({'grant_type': 'refresh_token',
                                   'client_id': key, 'refresh_token': rt}).encode()
    req = urllib.request.Request('https://kauth.kakao.com/oauth/token', data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read())
    except Exception as e:
        print(f'[경고] 카카오 토큰 갱신 실패({e}) — 만료됐다면 deploy/kakao_setup.py 재실행 필요',
              file=sys.stderr)
        return
    at = tok.get('access_token')
    new_rt = tok.get('refresh_token')          # 만료 1개월 안쪽일 때만 옴
    print('카카오 access 토큰 갱신 OK' + (' · refresh 토큰 교체 필요 감지' if new_rt else ''))
    if not new_rt:
        return

    pat = os.environ.get('GH_PAT', '').strip()
    repo = os.environ.get('GITHUB_REPOSITORY', '').strip()
    if pat and repo:
        env = dict(os.environ, GH_TOKEN=pat)
        p = subprocess.run(['gh', 'secret', 'set', 'KAKAO_REFRESH_TOKEN', '--repo', repo],
                           input=new_rt.encode(), env=env)
        if p.returncode == 0:
            print('KAKAO_REFRESH_TOKEN secret 자동 교체 완료')
            return
        print('[경고] secret 자동 교체 실패 — 아래 수동 경고로 전환', file=sys.stderr)
    # PAT 없음/실패 — 본인에게 카카오로 경고 (지금 access 토큰은 살아 있다)
    try:
        tpl = json.dumps({'object_type': 'text',
                          'text': '[나스닥 신호] 카카오 알림 토큰이 한 달 안에 만료됩니다. '
                                  'deploy/kakao_setup.py 를 다시 실행해 KAKAO_REFRESH_TOKEN '
                                  'secret 을 갱신하거나, GH_PAT secret 을 등록하면 자동 교체됩니다.',
                          'link': {'web_url': 'https://github.com/' + (repo or '')}},
                         ensure_ascii=False)
        body = urllib.parse.urlencode({'template_object': tpl}).encode()
        req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                                     data=body, headers={'Authorization': f'Bearer {at}'})
        urllib.request.urlopen(req, timeout=30).read()
        print('만료 예고를 카카오톡으로 발송')
    except Exception as e:
        print(f'[경고] 만료 예고 발송 실패: {e}', file=sys.stderr)


if __name__ == '__main__':
    main()
