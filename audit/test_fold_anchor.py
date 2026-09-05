# -*- coding: utf-8 -*-
"""[v224] 접힌 패널 안 앵커 — 세 화면이 같은 처리를 갖는지(정적). 동작 실측은 audit/GUIDE_NOTES_MATRIX_2026-09-05.md.

깨지면: 접어 둔 절·시즌·패널 안의 앵커(#order·#manual·#opsRecovery·#portPanel)로 들어왔을 때 내용이 숨은 채
맨 위에 머문다(2026-09-05 실측). 버튼 라벨은 검색·필터·앵커가 접힘을 바꿀 때 _foldPaint 로 따라가야 한다."""
import io
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name):
    return io.open(os.path.join(ROOT, name), encoding='utf-8').read()


class FoldAnchor(unittest.TestCase):
    PAGES = ('signal.html', 'guide.html', 'notes.html')

    def test_paint_hook_and_anchor_handler_in_all_pages(self):
        for p in self.PAGES:
            t = _read(p)
            self.assertIn('p._foldPaint = paint;', t, p)
            self.assertIn("closest('[data-fold].folded')", t, p)
            self.assertIn("addEventListener('hashchange', openFoldTarget)", t, p)
            self.assertIn('function openFoldTarget', t, p)

    def test_guide_restores_fold_before_opening_anchor(self):
        t = _read('guide.html')
        iife = t[t.index('function openFoldTarget'):]
        self.assertLess(iife.index('setupFold();'), iife.index('openFoldTarget();'),
                        'setupFold 가 먼저여야 저장된 접힘을 펼칠 수 있다')
        self.assertIn("closest('details.foldsec')", iife)                      # v153 유지

    def test_search_and_filter_repaint_buttons(self):
        g = _read('guide.html')
        self.assertIn("u.classList.remove('folded'); if(u._foldPaint) u._foldPaint();", g)
        self.assertIn("u.classList.add('folded'); if(u._foldPaint) u._foldPaint();", g)
        n = _read('notes.html')
        self.assertIn("if(s._foldPaint) s._foldPaint();", n)

    def test_signal_calls_handler_after_setup(self):
        s = _read('signal.html')
        boot = s[s.index('async function boot'):]
        self.assertLess(boot.index('setupFold();'), boot.index('openFoldTarget();'))


if __name__ == '__main__':
    unittest.main()
