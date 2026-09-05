#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v229] 배포본 HTML 에 Content-Security-Policy <meta> 를 박는다 — 인라인 스크립트는 **해시**로만 허용한다.

왜 배포 때인가: GitHub Pages 는 응답 헤더를 못 바꾼다(실측 2026-09-06: CSP·X-Frame 없음, HSTS 만). 화면은 인라인
<script> 단일 파일이고(v141 비상 수동 판정의 전제), `stamp_rev.py` 가 배포 때 스크립트 안의 HTML_REV 를 치환하므로
해시는 **치환 뒤 배포본에서** 계산해야 맞다. 소스 파일(저장소·로컬 사본 file://)에는 CSP 가 없다 — 편집이 정책을
깨뜨릴 일이 없고, 배포본만 잠근다.

무엇을 막나: 주입된 <script>·인라인 핸들러(해시 불일치) · 다른 오리진으로의 fetch/XHR/beacon(connect-src 'self') ·
외부 이미지·폰트·스타일(허용 목록 밖) · <base>·폼 제출·플러그인·프레임. 스타일은 'unsafe-inline'(style 속성 83곳 ·
위험도 낮음)이고 frame-ancestors 는 <meta> 로 못 건다(헤더 전용).

실패 규약: 이 스크립트가 죽으면 pages.yml 스텝은 continue-on-error 로 **CSP 없는 종전 배포본**을 내보낸다(fail-open ·
화면을 얼리지 않는다). 대신 여기서는 「인라인 핸들러·외부 스크립트·해시 못 만드는 스크립트」가 있으면 **정책을 넣지 않고
실패**한다 — 반쪽 정책으로 화면을 깨뜨리느니 정책 없이 나간다.

사용:  python3 deploy/csp_inject.py _site/index.html _site/guide.html _site/notes.html
       python3 deploy/csp_inject.py --selftest
"""
import base64
import hashlib
import io
import os
import re
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

SCRIPT_RE = re.compile(r'<script(\s[^>]*)?>(.*?)</script>', re.S | re.I)
HANDLER_RE = re.compile(r'<[a-zA-Z][^>]*\s(on[a-zA-Z]+)\s*=', re.S)
META_RE = re.compile(r'<meta\s+http-equiv="Content-Security-Policy"[^>]*>\n?', re.I)
CHARSET_RE = re.compile(r'<meta charset="utf-8">', re.I)

# 화면이 실제로 쓰는 외부 자원(2026-09-06 전수): Pretendard(jsdelivr CSS+폰트) · GitHub 검증 배지 SVG. 그 밖은 없다.
POLICY = ("default-src 'none'; script-src {hashes}; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
          "font-src https://cdn.jsdelivr.net; img-src 'self' data: https://github.com; connect-src 'self'; "
          "manifest-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'; frame-src 'none'")


def script_hashes(html):
    """인라인 <script> 본문의 sha256 (CSP 는 태그 사이 바이트 그대로를 UTF-8 로 해시한다). 외부 src 가 있으면 ValueError."""
    out = []
    for m in SCRIPT_RE.finditer(html):
        attrs = m.group(1) or ''
        if re.search(r'\ssrc\s*=', attrs):
            raise ValueError('외부 <script src> 는 이 정책에 없다: ' + attrs.strip()[:60])
        if re.search(r'\stype\s*=\s*"(?!(text/javascript|module)")', attrs):
            continue                                   # 실행되지 않는 데이터 블록은 해시 대상이 아니다
        digest = hashlib.sha256(m.group(2).encode('utf-8')).digest()
        out.append("'sha256-" + base64.b64encode(digest).decode('ascii') + "'")
    if not out:
        raise ValueError('인라인 <script> 가 하나도 없다')
    return out


def check_handlers(html):
    """인라인 이벤트 핸들러(onclick= 등)는 해시 정책에서 실행되지 않는다 — 있으면 정책을 넣지 않는다."""
    bad = sorted({m.group(1) for m in HANDLER_RE.finditer(html)})
    if bad:
        raise ValueError('인라인 이벤트 핸들러가 남아 있다(리스너로 옮겨라): ' + ', '.join(bad))


def inject(html):
    check_handlers(html)
    hashes = script_hashes(html)
    meta = '<meta http-equiv="Content-Security-Policy" content="%s">\n' % POLICY.format(hashes=' '.join(hashes))
    html = META_RE.sub('', html)                       # 이미 있으면 갈아 끼운다(멱등)
    if not CHARSET_RE.search(html):
        raise ValueError('<meta charset="utf-8"> 가 없다 — CSP meta 를 어디에 둘지 모른다')
    return CHARSET_RE.sub(lambda m: m.group(0) + '\n' + meta.rstrip('\n'), html, count=1), hashes


def atomic_write(path, text):
    parent = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.', suffix='.tmp', dir=parent, text=True)
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


def selftest():
    doc = ('<!doctype html><html><head>\n<meta charset="utf-8">\n<title>t</title></head>'
           '<body><script>var a = 1;</script><p>x</p>\n<script>\nconsole.log("b")\n</script></body></html>')
    out, hashes = inject(doc)
    assert out.count('Content-Security-Policy') == 1 and len(hashes) == 2
    exp = "'sha256-" + base64.b64encode(hashlib.sha256(b'var a = 1;').digest()).decode() + "'"
    assert hashes[0] == exp, hashes[0]
    out2, h2 = inject(out)                                  # 멱등 — 두 번 넣어도 하나
    assert out2.count('Content-Security-Policy') == 1 and h2 == hashes
    assert out.index('Content-Security-Policy') < out.index('<title>')     # charset 바로 뒤
    for bad, why in (('<img onerror="x()">', '핸들러'), ('<script src="a.js"></script>', 'src'), ('<p>no script</p>', '스크립트 없음')):
        try:
            inject(doc.replace('<p>x</p>', bad) if why != '스크립트 없음' else '<meta charset="utf-8">' + bad)
        except ValueError:
            pass
        else:
            raise AssertionError('막혀야 할 입력이 통과했다: ' + why)
    # stamp_rev 뒤에 계산해야 맞다 — 치환 전 해시는 치환 뒤 문서와 다르다
    before = inject(doc)[1][0]
    after = inject(doc.replace('var a = 1;', "var a = 'v9';"))[1][0]
    assert before != after
    print('csp_inject selftest: PASS (해시 2 · 멱등 · 위치 · 핸들러/외부 src/무스크립트 거부 · 치환 뒤 해시 변동)')
    return 0


def main(argv):
    if argv[1:] == ['--selftest']:
        return selftest()
    paths = argv[1:] or ['_site/index.html', '_site/guide.html', '_site/notes.html']
    for path in paths:
        if not os.path.exists(path):
            raise SystemExit('%s 가 없다' % path)
        with io.open(path, encoding='utf-8') as f:
            html = f.read()
        out, hashes = inject(html)
        atomic_write(path, out)
        print('CSP 주입: %s — 인라인 스크립트 %d개 해시' % (path, len(hashes)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
