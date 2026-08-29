#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배포본에 '화면 개정 시점'을 박는다.

signal.html 은 종가와 별개로 **전략 로직 자체**가 바뀔 수 있다. 사용자가
"지금 보는 화면이 최신 전략인가"를 알려면 종가일이 아니라 이 값을 봐야 한다.

pages.yml 이 `cp signal.html _site/index.html` 직후에 부른다:

    python3 deploy/stamp_rev.py _site/index.html "v85 · 2026-08-29 21:40"

인자를 안 주면 git 에서 직접 읽는다(로컬 확인용).
치환 자리를 못 찾으면 **실패로 끝낸다** — 조용히 빈 값이 배포되면 안 된다.

[v85] 형식: "vNN · YYYY-MM-DD HH:MM" (KST). 하루에 여러 번 고치는 운용이라
날짜·해시로는 최신 여부를 알 수 없다(소유자 지적). vNN 은 signal.html 을 마지막으로
바꾼 커밋 제목에서 뽑고, 제목에 vNN 이 없으면 시각만 적는다.
"""
import io
import os
import re
import subprocess
import sys

MARK = "const HTML_REV = '__HTML' + '_REV__';"


def git_rev(src='signal.html'):
    env = dict(os.environ, TZ='Asia/Seoul')
    out = subprocess.check_output(
        ['git', 'log', '-1', '--date=format-local:%Y-%m-%d %H:%M',
         '--format=%ad%n%s', '--', src],
        text=True, encoding='utf-8', env=env).strip()
    if not out:
        raise SystemExit('git 이력에서 %s 의 커밋을 못 찾았다' % src)
    lines = out.split('\n')
    when = lines[0]
    m = re.search(r'\bv(\d+)\b', lines[1] if len(lines) > 1 else '')
    return ('v%s · %s' % (m.group(1), when)) if m else when


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else '_site/index.html'
    rev = sys.argv[2] if len(sys.argv) > 2 else git_rev()
    if not os.path.exists(path):
        raise SystemExit('%s 가 없다' % path)
    s = io.open(path, encoding='utf-8').read()
    if MARK not in s:
        raise SystemExit('치환 자리를 못 찾았다 — signal.html 의 HTML_REV 선언이 바뀌었나?\n'
                         '  찾던 것: %s' % MARK)
    s = s.replace(MARK, "const HTML_REV = %r;" % rev)
    io.open(path, 'w', encoding='utf-8').write(s)
    print('화면 개정 주입:', rev, '->', path)


if __name__ == '__main__':
    main()
