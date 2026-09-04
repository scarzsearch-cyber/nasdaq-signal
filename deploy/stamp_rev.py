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
import json
import os
import re
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

MARK = "const HTML_REV = '__HTML' + '_REV__';"


def parse_git_rev(out):
    lines = out.strip().splitlines()
    if not lines or not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', lines[0]):
        raise ValueError('git 날짜 출력 형식이 잘못됐다')
    when = lines[0]
    m = re.search(r'\bv(\d+)\b', lines[1] if len(lines) > 1 else '')
    return ('v%s · %s' % (m.group(1), when)) if m else when


def git_rev(src='signal.html'):
    env = dict(os.environ, TZ='Asia/Seoul')
    out = subprocess.check_output(
        ['git', 'log', '-1', '--date=format-local:%Y-%m-%d %H:%M',
         '--format=%ad%n%s', '--', src],
        text=True, encoding='utf-8', env=env, timeout=30).strip()
    if not out:
        raise SystemExit('git 이력에서 %s 의 커밋을 못 찾았다' % src)
    try:
        return parse_git_rev(out)
    except ValueError as e:
        raise SystemExit('git 이력에서 화면 개정값을 해석하지 못했다: %s' % e)


def stamp_text(source, rev):
    if not isinstance(rev, str) or not rev.strip() or '\n' in rev or '\r' in rev:
        raise ValueError('화면 개정값은 비어 있지 않은 한 줄이어야 한다')
    count = source.count(MARK)
    if count != 1:
        raise ValueError('치환 자리는 정확히 1개여야 한다 (현재 %d개)' % count)
    # HTML 의 script 안이므로 JS 문자열 이스케이프뿐 아니라 </script> 조기 종료도 막는다.
    literal = json.dumps(rev, ensure_ascii=False)
    literal = (literal.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
               .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))
    return source.replace(MARK, 'const HTML_REV = %s;' % literal)


def atomic_write(path, text):
    parent = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.',
                               suffix='.tmp', dir=parent, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main():
    if len(sys.argv) > 3:
        raise SystemExit('사용: python deploy/stamp_rev.py [HTML경로] [개정값]')
    path = sys.argv[1] if len(sys.argv) > 1 else '_site/index.html'
    rev = sys.argv[2] if len(sys.argv) > 2 else git_rev()
    if not os.path.exists(path):
        raise SystemExit('%s 가 없다' % path)
    with io.open(path, encoding='utf-8') as f:
        s = f.read()
    try:
        s = stamp_text(s, rev)
    except ValueError as e:
        raise SystemExit('%s — signal.html 의 HTML_REV 선언을 확인하라\n  찾던 것: %s'
                         % (e, MARK))
    atomic_write(path, s)
    print('화면 개정 주입:', rev, '->', path)


def selftest():
    assert parse_git_rev('2026-09-04 12:34\nfeat: v201 화면') == 'v201 · 2026-09-04 12:34'
    assert parse_git_rev('2026-09-04 12:34\n문구 수정') == '2026-09-04 12:34'
    stamped = stamp_text('<script>' + MARK + '</script>', 'v1 </script> & ok')
    assert '</script> & ok' not in stamped
    assert '\\u003c/script\\u003e' in stamped and stamped.count('HTML_REV') == 1
    for source in ('no marker', MARK + '\n' + MARK):
        try:
            stamp_text(source, 'v1')
        except ValueError:
            pass
        else:
            raise AssertionError('잘못된 치환 자리 수가 통과했다')
    print('stamp_rev selftest: PASS (git 파싱 · 단일 표식 · script 이스케이프)')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        main()
