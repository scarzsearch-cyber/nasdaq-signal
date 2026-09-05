# -*- coding: utf-8 -*-
"""설치·실행 재현성 + 워크플로 권한 계약 회귀 (2026-09-06 · audit/REPRO_2026-09-06.md · audit/SECURITY_INPUT_2026-09-06.md).

R1  verify_all.py 는 어느 작업 디렉터리에서 불러도 저장소 루트를 찾는다 — 종전엔 다른 cwd 에서
    'data/…' 가 전부 「없음」으로 읽혀 경고 12건·종료 1(격리 클론 실측).
S1  워크플로 8종 전부 permissions 블록을 선언한다 — notify-test.yml 만 없어서 저장소 기본 권한(write)을 물려받았다.
"""
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, '.github', 'workflows')


class R1_VerifyAllCwdIndependent(unittest.TestCase):
    def test_fast_mode_from_foreign_cwd(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, PYTHONIOENCODING='utf-8')
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'verify_all.py'), '--fast'],
                               cwd=td, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
        self.assertEqual(r.returncode, 0, (r.stdout[-1500:], r.stderr[-800:]))
        self.assertNotIn('freeze.json 존재', r.stdout.split('결과')[-1],
                         '다른 cwd 에서 파일 「없음」 경고가 나면 경로 보정이 죽은 것')


class S1_WorkflowPermissions(unittest.TestCase):
    def test_every_workflow_declares_permissions(self):
        names = sorted(n for n in os.listdir(WF) if n.endswith('.yml'))
        self.assertGreaterEqual(len(names), 8, names)
        for n in names:
            y = io.open(os.path.join(WF, n), encoding='utf-8').read()
            self.assertRegex(y, r'(?m)^permissions:', '%s 에 permissions 블록이 없다 — 저장소 기본 권한(write)을 물려받는다' % n)

    def test_notify_test_is_read_only(self):
        y = io.open(os.path.join(WF, 'notify-test.yml'), encoding='utf-8').read()
        m = re.search(r'(?m)^permissions:\n((?:  .*\n)+)', y)
        self.assertIsNotNone(m)
        self.assertIn('contents: read', m.group(1))
        self.assertNotIn('write', m.group(1))


if __name__ == '__main__':
    unittest.main()
