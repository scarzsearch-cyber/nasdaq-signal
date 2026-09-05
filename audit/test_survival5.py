# -*- coding: utf-8 -*-
"""자동화 생존·감시 실패 경로 회귀 (2026-09-06 · 격리 환경 · 실제 발송·secrets·토큰 회전 없음).

묻는 것: 토큰 만료 · 권한 부족(GH_PAT 없음/secret 저장 실패) · 예약 누락 · 채널 부재일 때 **경고가 실제로 나가는 경로**가 있는가.
감시 대상과 감시 도구가 같은 이유(예약 실행 정지)로 동시에 멈추는 경우는 코드로 못 재고 구조로만 적는다(audit/SURVIVAL_2026-09-06.md).
"""
import io
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'audit'))
from test_watchdog_chain4 import load, Sandbox   # noqa: E402  (같은 로더·대역 재사용)


def _env(**kv):
    """환경변수를 잠시 바꾼다(None 이면 제거)."""
    class _Ctx:
        def __enter__(self):
            self.saved = {k: os.environ.get(k) for k in kv}
            for k, v in kv.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            return self

        def __exit__(self, *a):
            for k, v in self.saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    return _Ctx()


CLEAR = dict(KAKAO_REST_API_KEY=None, KAKAO_REFRESH_TOKEN=None, KAKAO_CLIENT_SECRET=None,
             TELEGRAM_BOT_TOKEN=None, TELEGRAM_CHAT_ID=None, DISCORD_WEBHOOK_URL=None, WEEKLY=None, GH_PAT=None)


class S1_ChannelLiveness(unittest.TestCase):
    """watchdog channel 모드 — 토큰이 죽었을 때 alert 출력(→ 이슈) + 살아 있는 채널로 알림."""

    def _run(self, keepalive_rc=None, keepalive_exc=None, env=None):
        WD = load('watchdog')
        with Sandbox(WD) as sb:
            saved = WD.kakao_keepalive_main
            def fake_keepalive():
                if keepalive_exc:
                    raise keepalive_exc
                return keepalive_rc
            WD.kakao_keepalive_main = fake_keepalive
            try:
                with _env(**{**CLEAR, **(env or {})}):
                    WD.mode_channel()
            finally:
                WD.kakao_keepalive_main = saved
            return sb.outputs(), list(sb.sent)

    def test_expired_kakao_token_alerts(self):
        out, sent = self._run(keepalive_rc=2, env=dict(KAKAO_REST_API_KEY='k', KAKAO_REFRESH_TOKEN='r'))
        self.assertIn('alert=1', out, '토큰 갱신 실패(rc 2)면 이슈 조건 alert=1')
        self.assertTrue(any('알림 채널 이상' in s[0] for s in sent), sent)

    def test_kakao_exception_alerts(self):
        out, sent = self._run(keepalive_exc=RuntimeError('boom'), env=dict(KAKAO_REST_API_KEY='k', KAKAO_REFRESH_TOKEN='r'))
        self.assertIn('alert=1', out)
        self.assertTrue(any('카카오톡(RuntimeError)' in s[2] for s in sent), sent)

    def test_incomplete_secret_alerts(self):
        out, sent = self._run(env=dict(KAKAO_REST_API_KEY='k'))     # refresh 토큰만 빠짐
        self.assertIn('alert=1', out)
        self.assertTrue(any('설정 불완전' in s[2] for s in sent), sent)

    def test_no_channel_at_all_is_issue_on_weekly_only(self):
        out, sent = self._run(env=dict(WEEKLY='true'))
        self.assertIn('alert=1', out, '채널이 하나도 없으면 주간 슬롯이 이슈(메일)로 알린다(v200)')
        self.assertEqual(sent, [], '보낼 채널이 없으니 notify 는 안 부른다')
        out2, sent2 = self._run(env={})
        self.assertNotIn('alert=1', out2, '평일 슬롯은 침묵(설계 · 주 1회만)')

    def test_alive_kakao_is_silent(self):
        out, sent = self._run(keepalive_rc=0, env=dict(KAKAO_REST_API_KEY='k', KAKAO_REFRESH_TOKEN='r'))
        self.assertNotIn('alert=1', out)
        self.assertEqual(sent, [])


class S2_KeepaliveRotation(unittest.TestCase):
    """kakao_keepalive — 회전된 refresh 토큰을 저장하지 못할 때(GH_PAT 없음 · secret 저장 실패) 침묵하지 않는가."""

    def _run(self, replies, env, patch_secret=None):
        KK = load('kakao_keepalive')
        old = urllib.request.urlopen
        calls = []

        class R:
            def __init__(self, raw): self.raw = raw
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return self.raw

        it = iter(replies)

        def fake_open(req, timeout=30):
            calls.append(getattr(req, 'full_url', str(req)))
            nxt = next(it)
            if isinstance(nxt, Exception):
                raise nxt
            return R(nxt)
        urllib.request.urlopen = fake_open
        if patch_secret is not None:
            KK.set_github_secret = patch_secret
        with tempfile.TemporaryDirectory() as td:
            ghenv = os.path.join(td, 'env')
            try:
                with _env(**{**CLEAR, **env, 'GITHUB_ENV': ghenv, 'GITHUB_REPOSITORY': 'o/r'}):
                    rc = KK.main()
                envtext = io.open(ghenv, encoding='utf-8').read() if os.path.exists(ghenv) else ''
            finally:
                urllib.request.urlopen = old
        return rc, calls, envtext

    ROT = json.dumps({'access_token': 'A', 'refresh_token': 'NEWRT'}).encode()

    def test_rotation_without_pat_sends_urgent_warning_and_fails(self):
        rc, calls, envtext = self._run([self.ROT, b'{"result_code": 0}'],
                                       dict(KAKAO_REST_API_KEY='k', KAKAO_REFRESH_TOKEN='r'))
        self.assertEqual(rc, 2, 'GH_PAT 없음 → 긴급 경고 발송 뒤 실패 코드(스텝이 빨개진다)')
        self.assertTrue(any('talk/memo' in c for c in calls), '긴급 경고 카톡 경로를 탔다')
        self.assertIn('KAKAO_REFRESH_TOKEN=NEWRT', envtext, '같은 잡의 뒤 스텝엔 새 토큰이 넘어간다')

    def test_rotation_with_pat_but_secret_store_fails(self):
        rc, calls, envtext = self._run([self.ROT, b'{"result_code": 0}'],
                                       dict(KAKAO_REST_API_KEY='k', KAKAO_REFRESH_TOKEN='r', GH_PAT='p'),
                                       patch_secret=lambda *a, **k: False)
        self.assertEqual(rc, 2, 'secret 저장 실패도 긴급 경고 + 실패')
        self.assertTrue(any('talk/memo' in c for c in calls))

    def test_rotation_with_pat_success_is_silent(self):
        rc, calls, envtext = self._run([self.ROT], dict(KAKAO_REST_API_KEY='k', KAKAO_REFRESH_TOKEN='r', GH_PAT='p'),
                                       patch_secret=lambda *a, **k: True)
        self.assertEqual(rc, 0)
        self.assertFalse(any('talk/memo' in c for c in calls), '정상 회전은 무발송')

    def test_expired_refresh_token_fails_loudly(self):
        rc, calls, envtext = self._run([urllib.error.HTTPError('u', 401, 'unauthorized', {}, None)],
                                       dict(KAKAO_REST_API_KEY='k', KAKAO_REFRESH_TOKEN='r'))
        self.assertEqual(rc, 2, '만료 토큰 → rc 2 → channel 모드가 죽은 채널로 잡는다')

    def test_urgent_warning_send_failure_is_distinct_code(self):
        rc, calls, envtext = self._run([self.ROT, urllib.error.URLError('down')],
                                       dict(KAKAO_REST_API_KEY='k', KAKAO_REFRESH_TOKEN='r'))
        self.assertEqual(rc, 3, '경고 발송까지 실패하면 3 — 어느 경우도 0 이 아니다')


class S3_WorkflowContracts(unittest.TestCase):
    """이슈(메일)가 마지막 통로다 — 그 통로를 여는 워크플로가 권한을 선언하는가 · 예약 누락 감시 모드가 스텝에 있는가."""

    def _yml(self, name):
        with io.open(os.path.join(ROOT, '.github', 'workflows', name), encoding='utf-8') as f:
            return f.read()

    def test_issue_openers_declare_issues_write(self):
        for name in ('verify.yml', 'watchdog.yml', 'daily-signal.yml'):
            y = self._yml(name)
            self.assertIn('github.rest.issues', y, name)
            m = re.search(r'^permissions:\n((?:  .*\n)+)', y, re.M)
            self.assertIsNotNone(m, name)
            self.assertIn('issues: write', m.group(1), name)

    def test_schedule_miss_watchers_are_wired(self):
        y = self._yml('watchdog.yml')
        for mode in ('stale', 'stats', 'price', 'heartbeat'):
            self.assertIn('watchdog.py %s' % mode, y, mode)
        self.assertIn("cron: '40 23 * * 0-4'", y)      # 08:40 KST 평일
        self.assertIn("cron: '10 0 * * 1'", y)         # 09:10 KST 월요일

    def test_heartbeat_is_the_only_positive_signal(self):
        """예약 실행이 통째로 꺼지면 파수꾼도 같이 꺼진다 — 그때 남는 신호는 「월간 생존 카톡이 안 온다」뿐이다(v177).
        코드로 잴 수 없어 구조만 고정한다: heartbeat 모드가 존재하고 주간 슬롯에 걸려 있다."""
        WD = load('watchdog')
        self.assertIn('heartbeat', WD.MODES)
        y = self._yml('watchdog.yml')
        self.assertIn('watchdog.py heartbeat', y)


if __name__ == '__main__':
    unittest.main()
