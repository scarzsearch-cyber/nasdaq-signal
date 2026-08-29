#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v77] 카카오톡 알림 최초 1회 설정 도우미 — **본인 PC에서 직접** 실행하세요.

mobi-market 에서 쓰던 카카오 개발자 앱을 그대로 재활용합니다.
(developers.kakao.com > 내 애플리케이션 — "카카오톡 메시지 전송" 동의항목이
이미 켜져 있는 그 앱. REST API 키를 사용합니다. JavaScript 키 아님!)

실행:  python deploy/kakao_setup.py
절차:  ① REST API 키 입력 → ② 그 앱에 등록된 Redirect URI 아무거나 입력
      → ③ 출력된 주소를 브라우저에서 열고 동의 → ④ 이동된 주소창의 code= 값 붙여넣기
      → ⑤ 출력된 refresh_token 을 GitHub Secrets 에 등록

토큰은 이 화면에만 출력되고 어디에도 저장·전송되지 않습니다.
"""
import json
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def main():
    print(__doc__)
    key = input('① REST API 키: ').strip()
    uri = input('② 앱에 등록된 Redirect URI (mobi-market 페이지 주소 등): ').strip()
    auth = ('https://kauth.kakao.com/oauth/authorize?response_type=code'
            f'&client_id={key}&redirect_uri={urllib.parse.quote(uri, safe="")}'
            '&scope=talk_message')
    print('\n③ 아래 주소를 브라우저에서 열고 [동의하고 계속하기]:\n\n   ' + auth)
    print('\n   동의하면 Redirect URI 로 이동합니다. 그 페이지가 뭐든 상관없고,')
    print('   주소창에 붙은  ?code=XXXX  의 XXXX 만 필요합니다.')
    code = input('\n④ code 값: ').strip()
    body = urllib.parse.urlencode({
        'grant_type': 'authorization_code', 'client_id': key,
        'redirect_uri': uri, 'code': code}).encode()
    req = urllib.request.Request('https://kauth.kakao.com/oauth/token', data=body)
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.loads(r.read())
    if 'refresh_token' not in tok:
        sys.exit(f'실패: {tok}')
    print('\n⑤ 성공! GitHub 저장소 → Settings → Secrets and variables → Actions 에 등록:')
    print(f'   KAKAO_REST_API_KEY  = {key}')
    print(f'   KAKAO_REFRESH_TOKEN = {tok["refresh_token"]}')
    print('\n등록 후 Actions 탭 → "알림 테스트" → Run workflow 로 확인하세요.')
    print('(선택) 토큰 자동 연명·교체까지 원하면 GH_PAT secret 도 등록 — 03 문서 참조.')

    # 바로 시험 발송
    try:
        tpl = json.dumps({'object_type': 'text',
                          'text': '나스닥 신호 알림 연결 시험 — 이 메시지가 보이면 성공',
                          'link': {'web_url': 'https://scarzsearch-cyber.github.io/nasdaq-signal/'}},
                         ensure_ascii=False)
        body = urllib.parse.urlencode({'template_object': tpl}).encode()
        req = urllib.request.Request('https://kapi.kakao.com/v2/api/talk/memo/default/send',
                                     data=body,
                                     headers={'Authorization': f'Bearer {tok["access_token"]}'})
        urllib.request.urlopen(req, timeout=30).read()
        print('\n지금 카카오톡(나와의 채팅)으로 시험 메시지를 보냈습니다 — 확인해 보세요.')
    except Exception as e:
        print(f'\n[경고] 시험 발송 실패: {e} — 동의항목(카카오톡 메시지 전송)이 켜져 있는지 확인.')


if __name__ == '__main__':
    main()
