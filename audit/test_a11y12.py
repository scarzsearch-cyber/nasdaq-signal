# -*- coding: utf-8 -*-
"""리퍼러 정책·키보드/보조기술 계약 회귀 (2026-09-06 · v231 · 장부 audit/REFERRER_A11Y_2026-09-06.md).

**CI 미등재** — verify.yml 은 unittest 모듈을 명시 나열하므로 이 파일은 자동 수집되지 않는다(편입은 인계 판단).
실행: python -m unittest audit.test_a11y12

고정하는 계약(정적 · 브라우저 실측은 장부):
  R1 세 화면 <head> 에 <meta name="referrer" content="no-referrer"> — GitHub Pages 는 헤더를 못 두므로 meta 가 유일한 수단.
  R2 바깥 링크(target=_blank · http(s))는 전부 rel 에 noopener 를 가진다(정적 마크업 + JS 템플릿).
  A1 신호: #vpx(5분 시세) 는 aria-live="off"(판정 live 영역 안에서 매번 읽히지 않게) · #msg aria-live · #sysWarn role=alert · 복원 결과 undoBar role=status.
  A2 설명서: #gsearch 가 aria-label · #gsearchMsg aria-live. 노트: 필터 버튼 aria-pressed(초기 「전체」만 true) + 클릭 핸들러가 aria-pressed 를 갱신.
  A3 세 화면 setupFold 가 접기 버튼에 aria-expanded·aria-label 을 준다.
  A4 정적 <button> 은 텍스트 또는 aria-label 을 가진다 · 정적 <input>(hidden 제외)은 aria-label 또는 감싸는/for 라벨을 가진다.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENS = ('signal.html', 'guide.html', 'notes.html')


def read(name):
    with io.open(os.path.join(ROOT, name), encoding='utf-8') as f:     # CI 로그의 ResourceWarning 제거
        return f.read()


def head_of(src):
    return src.split('</head>')[0]


class R_Referrer(unittest.TestCase):
    def test_meta_no_referrer_in_every_head(self):
        for n in SCREENS:
            h = head_of(read(n))
            self.assertRegex(h, r'<meta\s+name="referrer"\s+content="no-referrer">', n)

    def test_external_blank_links_have_noopener(self):
        for n in SCREENS:
            src = read(n)
            for m in re.finditer(r'<a\b[^>]*target="_blank"[^>]*>', src):
                tag = m.group(0)
                self.assertRegex(tag, r'rel="[^"]*noopener', '%s: %s' % (n, tag[:120]))
            # JS 템플릿 안의 target=_blank(문자열 연결 포함)
            for m in re.finditer(r"target=\\?\"_blank\\?\"[^\n]{0,80}", src):
                self.assertIn('noopener', m.group(0), '%s: %s' % (n, m.group(0)[:120]))


class A_Aria(unittest.TestCase):
    def test_signal_live_regions(self):
        s = read('signal.html')
        self.assertRegex(s, r'<div class="state" aria-live="polite">')
        self.assertRegex(s, r'<a class="vpx" id="vpx"[^>]*aria-live="off"')
        self.assertRegex(s, r'<div class="msg" id="msg" aria-live="polite">')
        self.assertRegex(s, r'id="sysWarn" hidden role="alert"')
        self.assertIn("d.id = 'undoBar';", s)
        self.assertRegex(s, r"d\.setAttribute\('role', 'status'\)")
        # [v232] 되돌리기 버튼은 자기 줄을 지우므로 초점을 복원 컨트롤로 되돌린다(격리 Chrome 실측 · kb_keyboard_check S5)
        undo = s[s.index("getElementById('undoBtn').addEventListener"):s.index("getElementById('undoBtn').addEventListener") + 900]
        self.assertLess(undo.index('back.focus()'), undo.index('d.remove()'), '되돌리기: 초점 복귀가 undoBar 제거보다 앞서야 한다')

    def test_guide_search_names_and_notes_filter_state(self):
        g = read('guide.html')
        self.assertRegex(g, r'<input type="search" id="gsearch"[^>]*\n?[^>]*aria-label="[^"]+"')
        self.assertRegex(g, r'id="gsearchMsg"[^>]*aria-live="polite"')
        nts = read('notes.html')
        btns = re.findall(r'<button[^>]*data-f="(\w+)"[^>]*aria-pressed="(true|false)"', nts)
        self.assertEqual([b[0] for b in btns], ['all', 'new', 'fix', 'del'])
        self.assertEqual([b[1] for b in btns], ['true', 'false', 'false', 'false'])
        self.assertRegex(nts, r"x\.setAttribute\('aria-pressed', x === b \? 'true' : 'false'\)")

    def test_fold_buttons_expose_expanded_state(self):
        for n in SCREENS:
            src = read(n)
            self.assertIn("b.setAttribute('aria-expanded', on ? 'false' : 'true')", src, n)
            self.assertIn("b.setAttribute('aria-label', (on ? '펼치기' : '접기')", src, n)

    def test_static_controls_have_names(self):
        for n in SCREENS:
            src = read(n)
            for m in re.finditer(r'<button\b([^>]*)>(.*?)</button>', src, re.S):
                attrs, inner = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
                if '${' in inner or '${' in attrs:      # JS 템플릿 조각은 제외
                    continue
                if re.search(r'\shidden(\s|$)', attrs):   # 숨김 상태로 두고 JS 가 글자를 채우는 버튼(#tlAuto) — 이름은 브라우저 실측(장부)
                    continue
                self.assertTrue(inner or 'aria-label=' in attrs, '%s: 이름 없는 버튼 %s' % (n, m.group(0)[:100]))
            for m in re.finditer(r'<input\b([^>]*)>', src):
                attrs = m.group(1)
                if 'type="hidden"' in attrs or '${' in attrs:
                    continue
                idm = re.search(r'id="([^"]+)"', attrs)
                labeled = 'aria-label=' in attrs
                if not labeled and idm:
                    labeled = ('for="%s"' % idm.group(1)) in src
                if not labeled:
                    # 감싸는 <label> — 태그 앞 200자 안에 닫히지 않은 <label 이 있는가
                    before = src[max(0, m.start() - 200):m.start()]
                    labeled = before.rfind('<label') > before.rfind('</label>')
                self.assertTrue(labeled, '%s: 이름 없는 입력 %s' % (n, m.group(0)[:100]))


if __name__ == '__main__':
    unittest.main()
