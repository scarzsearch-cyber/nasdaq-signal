"""자동 파수꾼(deploy/watchdog.py + watchdog.yml) 연결 검사 (2026-09-05 · 4차).

모드 하나가 아니라 **모드끼리 이어 돌릴 때**의 파일 상태·출력·알림·커밋을 본다.
네트워크 0 · 실제 알림 0 · 토큰 회전 0 · 실측 장부 무접촉. 하위 스크립트(점검.py · 판정 규약 평가기)는
실제 출력 문자열을 고정 응답으로 준다. 커밋 스텝은 워크플로 셸을 그대로 뽑아 로컬 bare 원격에서 돌린다.

W1 평가기 출력 계약 · W2 주간 check 연쇄(점검→평가기→병합→쓰기→악화 알림) · W3 주간 커밋 스텝 셸 ·
W4 워크플로 계약(id·if·이슈 조건) · W5 토큰 회전 연속성 · W6 heartbeat 커밋 유실 시 동작.

실행:  python -m unittest audit.test_watchdog_chain4  (저장소 루트에서)
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEPLOY = os.environ.get('WATCHDOG4_OLD') or os.path.join(ROOT, 'deploy')
if DEPLOY not in sys.path:
    sys.path.insert(0, DEPLOY)

# research/oos_protocol_b.py --oos 의 실제 출력(2026-09-05 실행 · 사건 0건). 파서 계약의 기준 문자열.
EVAL_OK = (
    '==============================================================================\n'
    '등록 규약 data/oos_protocol_b.json · 등록일 2026-09-02 · 지문 74387a5c73c0fc06\n'
    '==============================================================================\n'
    '  기저율 자기검산: A 독립 8/8 (등록 8/8) · B 전체 69건 P05 -29.3% (등록 -29.3%)\n'
    '\n'
    '  동결 이후 도피 사건 0건 (엔진 자료 마지막 날 2026-08-28)\n'
    '  → **판정 불가 — 정상.** 사건이 없다. (독립 사건은 역사상 2.6년에 1건)\n'
    '\n'
    '  R 계산 불가 — 동결 뒤 0거래일 (756 필요)\n'
    '\n'
    '  판정: 재검토 사유 없음 (판정 사건 0건)\n'
    '  이 출력은 자동으로 아무것도 바꾸지 않는다 — 규약 response 항목대로.\n')
EVAL_DRIFT = (EVAL_OK.split('\n  동결 이후')[0] +
              '\n  ⚠ 역사 기저율이 등록값과 다르다 — 원자료 갱신(수정주가 재조정 등) 때문일 수 있다. '
              '판정 전에 원인을 적고 지문을 의도적으로 갱신하라.\n'
              '  → **판정 중단.** 등록 당시 저울이 달라졌으므로 OOS 정상/주의/역사 밖 판정을 내리지 않는다.\n')
EVAL_FP = EVAL_OK.split('\n  기저율')[0] + '\n  ⛔ 지문 불일치 (재계산 deadbeef00000000) — 규약이 수정됐다. 판정을 내지 않는다.\n'
EVAL_WARN = EVAL_OK.replace('판정: 재검토 사유 없음 (판정 사건 0건)', '판정: 주의 (사건 1건 · 2026-10-01 B)')
EVAL_OUT = EVAL_OK.replace('판정: 재검토 사유 없음 (판정 사건 0건)', '판정: **역사 밖 — 재검토 연구 개시** (2026-10-01 A)')
EVAL_CRASH = 'Traceback (most recent call last):\n  File "x", line 1\nKeyError: \'gates\'\n'


def load(name):
    path = os.path.join(DEPLOY, name + '.py')
    spec = importlib.util.spec_from_file_location('watchdog4_' + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # watchdog 은 import 시 ROOT 로 chdir 한다 — 그 뒤에 임시 디렉터리로 옮긴다
    return mod


class CP:
    def __init__(self, stdout='', stderr='', returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


class Sandbox:
    """임시 디렉터리 + GITHUB_OUTPUT + 알림 대역."""

    def __init__(self, WD):
        self.WD = WD
        self.sent = []

    def __enter__(self):
        self.old = os.getcwd()
        self.td = tempfile.mkdtemp(prefix='wd4_')
        os.chdir(self.td)
        os.makedirs('data')
        os.makedirs('research')
        with open(os.path.join('research', 'oos_protocol_b.py'), 'w', encoding='utf-8') as f:
            f.write('# 존재 검사용 대역 — 실행은 subprocess 대역이 가로챈다\n')
        self.output = os.path.join(self.td, 'gh_output')
        self.env_saved = os.environ.get('GITHUB_OUTPUT')
        os.environ['GITHUB_OUTPUT'] = self.output
        WD = self.WD

        def fake_notify(title, status, detail):
            self.sent.append((title, status, detail))
            return 0
        self.real_notify = WD.notify
        WD.notify = fake_notify
        return self

    def outputs(self):
        return open(self.output, encoding='utf-8').read() if os.path.exists(self.output) else ''

    def reset_output(self):
        if os.path.exists(self.output):
            os.unlink(self.output)

    def __exit__(self, *exc):
        self.WD.notify = self.real_notify
        os.chdir(self.old)
        if self.env_saved is None:
            os.environ.pop('GITHUB_OUTPUT', None)
        else:
            os.environ['GITHUB_OUTPUT'] = self.env_saved
        shutil.rmtree(self.td, ignore_errors=True)
        return False


class W1_EvaluatorContract(unittest.TestCase):
    """protocol_status 가 평가기의 **실제 출력 문자열**을 verdict 로 옮기는 계약."""

    def _status(self, text, rc):
        WD = load('watchdog')
        with Sandbox(WD):                          # 평가기 파일 존재 검사만 통과시킨다(실행은 대역)
            WD.subprocess = types.SimpleNamespace(run=lambda *a, **k: CP(stdout=text, returncode=rc))
            return WD.protocol_status({})

    def test_real_zero_event_output_is_ok(self):
        s = self._status(EVAL_OK, 0)
        self.assertEqual((s['verdict'], s['events'], s['drift'], s['todo']), ('ok', 0, False, None))

    def test_warn_outside_fingerprint(self):
        self.assertEqual(self._status(EVAL_WARN, 0)['verdict'], 'warn')
        self.assertEqual(self._status(EVAL_OUT, 0)['verdict'], 'outside')
        s = self._status(EVAL_FP, 2)
        self.assertEqual(s['verdict'], 'invalid')
        self.assertIn('지문', s['todo'])

    def test_baseline_drift_is_reported_as_drift_not_parse_failure(self):
        s = self._status(EVAL_DRIFT, 2)
        self.assertTrue(s['drift'])
        self.assertEqual(s['verdict'], 'drift', '[v225] 표류는 전용 verdict — 화면 PBV 가 「재등록 필요」로 읽는다')
        self.assertIn('기저율', s['todo'], '기저율 표류를 「출력을 읽지 못했다」로 보고한다')
        self.assertNotIn('읽지 못했다', s['line'])

    def test_crash_is_error_with_todo(self):
        s = self._status(EVAL_CRASH, 1)
        self.assertEqual(s['verdict'], 'error')
        self.assertTrue(s['todo'])


class W2_WeeklyCheckChain(unittest.TestCase):
    """mode_check: 점검.py --json → 평가기 --oos → merge_ops → 원자 쓰기 → 악화 판정 → 알림.

    불변조건: (i) 첫 주간 실행에서 protocol_b·health_errors 가 새로 생겨도 「악화」가 아니다.
    (ii) heartbeat 키는 이월된다. (iii) 같은 상태 반복은 조용하고 새로 나빠질 때만 한 번 알린다.
    (iv) 평가기 크래시는 error 로 파일에 남고 악화로 알린다 — 조용히 사라지지 않는다."""

    def _stub(self, WD, check_json, eval_text, eval_rc=0):
        def run(args, **kw):
            script = str(args[1])
            if script.endswith('점검.py'):
                return CP(stdout='사람용 줄\n' + json.dumps(check_json, ensure_ascii=False) + '\n')
            if script.endswith('oos_protocol_b.py'):
                return CP(stdout=eval_text, returncode=eval_rc)
            raise AssertionError(f'예상 밖 하위 실행: {args}')
        WD.subprocess = types.SimpleNamespace(run=run, call=lambda *a, **k: 0, check_output=lambda *a, **k: b'')

    def _base(self):
        return {'as_of': '2026-09-07', 'level': 0, 'level_msg': '정상 — 유지', 'todo': [], 'vars': [],
                'aum': [{'code': '418660', 'name': 'x', 'eok': 6488, 'state': '정상'}],
                'exec': {}, 'health_errors': [], 'ok': True}

    def test_first_run_with_new_keys_is_not_worse_and_carries_heartbeat(self):
        WD = load('watchdog')
        with Sandbox(WD) as sb:
            json.dump({'as_of': '2026-09-01', 'level': 0, 'level_msg': '정상 — 유지', 'todo': [],
                       'vars': [], 'aum': [], 'exec': {}, 'ok': True, 'heartbeat': '2026-09'},
                      open('data/ops_check.json', 'w', encoding='utf-8'), ensure_ascii=False)
            self._stub(WD, self._base(), EVAL_OK)
            WD.mode_check()
            j = json.load(open('data/ops_check.json', encoding='utf-8'))
            self.assertEqual(j['protocol_b']['verdict'], 'ok')
            self.assertEqual(j['heartbeat'], '2026-09', 'heartbeat 표시가 지워졌다(v177 월 1회 → 주 1회)')
            self.assertEqual(j['todo'], [])
            self.assertEqual(sb.sent, [])
            self.assertIn('written=1', sb.outputs())
            self.assertNotIn('alert=1', sb.outputs())

    def test_worsening_alerts_once_then_silent(self):
        WD = load('watchdog')
        with Sandbox(WD) as sb:
            json.dump(self._base(), open('data/ops_check.json', 'w', encoding='utf-8'), ensure_ascii=False)
            worse = dict(self._base(), level=1, level_msg='주의 — 지켜본다',
                         todo=['전제 감시 Level 1 · 주의 — 지수 10년 CAGR'])
            self._stub(WD, worse, EVAL_OK)
            WD.mode_check()
            self.assertEqual(len(sb.sent), 1)
            self.assertIn('alert=1', sb.outputs())
            sb.reset_output()
            WD.mode_check()                                   # 같은 상태 반복
            self.assertEqual(len(sb.sent), 1, '같은 상태를 매주 다시 알린다')
            self.assertNotIn('alert=1', sb.outputs())

    def test_evaluator_crash_is_recorded_and_alerted(self):
        WD = load('watchdog')
        with Sandbox(WD) as sb:
            base = dict(self._base(), protocol_b={'verdict': 'ok', 'events': 0, 'drift': False})
            json.dump(base, open('data/ops_check.json', 'w', encoding='utf-8'), ensure_ascii=False)
            self._stub(WD, self._base(), EVAL_CRASH, eval_rc=1)
            WD.mode_check()
            j = json.load(open('data/ops_check.json', encoding='utf-8'))
            self.assertEqual(j['protocol_b']['verdict'], 'error')
            self.assertTrue(any('평가기' in t for t in j['todo']))
            self.assertEqual(len(sb.sent), 1)

    def test_check_script_failure_keeps_previous_file(self):
        WD = load('watchdog')
        with Sandbox(WD) as sb:
            prev = dict(self._base(), heartbeat='2026-09')
            json.dump(prev, open('data/ops_check.json', 'w', encoding='utf-8'), ensure_ascii=False)
            before = open('data/ops_check.json', 'rb').read()
            WD.subprocess = types.SimpleNamespace(run=lambda *a, **k: CP(stdout='깨진 출력\n', stderr='Traceback', returncode=1))
            WD.mode_check()
            self.assertEqual(open('data/ops_check.json', 'rb').read(), before, '점검 실패가 기존 파일을 덮었다')
            self.assertEqual(len(sb.sent), 1)
            self.assertIn('alert=1', sb.outputs())


def git(*args, cwd, check=True):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args], cwd=cwd,
                          check=check, capture_output=True, encoding='utf-8', errors='replace')


def bash_exe():
    for cand in (r'C:\Program Files\Git\bin\bash.exe', r'C:\Program Files\Git\usr\bin\bash.exe'):
        if os.path.exists(cand):
            return cand
    return shutil.which('bash')


class W3_WeeklyCommitStep(unittest.TestCase):
    """watchdog.yml 「점검 결과 커밋」 셸을 로컬 bare 원격에서 그대로 실행.

    불변조건: 변경 없으면 커밋 없음 · 원격 그대로면 push · 원격이 움직였으면 실패(옛 점검 산출물을
    새 코드 위에 얹지 않음 — 다음 주간 슬롯이 새 HEAD 로 다시 계산)."""

    @classmethod
    def setUpClass(cls):
        cls.bash = bash_exe()
        with open(os.path.join(ROOT, '.github', 'workflows', 'watchdog.yml'), encoding='utf-8') as f:
            lines = f.read().replace('\r\n', '\n').split('\n')
        start = next(i for i, l in enumerate(lines) if l.strip() == '- name: 점검 결과 커밋')
        run_i = next(i for i in range(start, len(lines)) if lines[i].strip() == 'run: |')
        key_indent = len(lines[run_i]) - len(lines[run_i].lstrip())
        body = []
        for l in lines[run_i + 1:]:
            if l.strip() and (len(l) - len(l.lstrip())) <= key_indent:
                break
            body.append(l)
        indent = min(len(l) - len(l.lstrip()) for l in body if l.strip())
        cls.snippet = '\n'.join(l[indent:] if l.strip() else '' for l in body) + '\n'

    def setUp(self):
        if not self.bash:
            self.skipTest('bash 없음')

    def _seed(self, td):
        bare = os.path.join(td, 'origin.git')
        git('init', '-q', '--bare', '-b', 'main', bare, cwd=td)
        seed = os.path.join(td, 'seed')
        git('clone', '-q', bare, seed, cwd=td)
        os.makedirs(os.path.join(seed, 'data'))
        for p, t in {'data/ops_check.json': json.dumps({'level': 0, 'as_of': '2026-08-31'}),
                     'data/kr_holidays.json': '{"range": [2025, 2032], "holidays": {}}',
                     'data/signal.json': '{"as_of": "2026-09-04"}', 'README.md': 'seed\n'}.items():
            with open(os.path.join(seed, p), 'w', encoding='utf-8') as f:
                f.write(t)
        git('add', '-A', cwd=seed); git('commit', '-q', '-m', 'seed', cwd=seed)
        git('push', '-q', 'origin', 'HEAD:main', cwd=seed)
        return bare

    def _run(self, repo):
        shim = os.path.join(repo, '.shim')
        os.makedirs(shim)
        with open(os.path.join(shim, 'python3'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('#!/bin/sh\nexec "%s" "$@"\n' % sys.executable.replace('\\', '/'))
        os.chmod(os.path.join(shim, 'python3'), 0o755)
        script = os.path.join(shim, 'commit_step.sh')
        with open(script, 'w', encoding='utf-8', newline='\n') as f:
            f.write(self.snippet)
        with open(os.path.join(repo, '.git', 'info', 'exclude'), 'a', encoding='utf-8') as f:
            f.write('.shim/\n')
        env = dict(os.environ, PATH=shim + os.pathsep + os.environ.get('PATH', ''), GIT_TERMINAL_PROMPT='0')
        r = subprocess.run([self.bash, '-e', script], cwd=repo, env=env, capture_output=True,
                           encoding='utf-8', errors='replace', timeout=120)
        return r.returncode, (r.stdout or '') + (r.stderr or '')

    def _remote_level(self, bare):
        return json.loads(git('show', 'main:data/ops_check.json', cwd=bare).stdout)['level']

    def test_no_change_no_commit(self):
        with tempfile.TemporaryDirectory(prefix='wd4_race_') as td:
            bare = self._seed(td)
            c = os.path.join(td, 'run'); git('clone', '-q', bare, c, cwd=td)
            rc, out = self._run(c)
            self.assertEqual(rc, 0, out)
            self.assertIn('변경 없음', out)

    def test_changed_check_is_pushed(self):
        with tempfile.TemporaryDirectory(prefix='wd4_race_') as td:
            bare = self._seed(td)
            c = os.path.join(td, 'run'); git('clone', '-q', bare, c, cwd=td)
            with open(os.path.join(c, 'data', 'ops_check.json'), 'w', encoding='utf-8') as f:
                f.write(json.dumps({'level': 1, 'as_of': '2026-09-07', 'heartbeat': '2026-09'}))
            rc, out = self._run(c)
            self.assertEqual(rc, 0, out)
            self.assertEqual(self._remote_level(bare), 1)

    def test_remote_moved_fails_closed_without_rebase(self):
        with tempfile.TemporaryDirectory(prefix='wd4_race_') as td:
            bare = self._seed(td)
            a = os.path.join(td, 'daily'); git('clone', '-q', bare, a, cwd=td)
            c = os.path.join(td, 'run'); git('clone', '-q', bare, c, cwd=td)
            with open(os.path.join(a, 'data', 'signal.json'), 'w', encoding='utf-8') as f:
                f.write('{"as_of": "2026-09-08"}')                  # 일일 신호 슬롯이 먼저 밀었다
            git('add', '-A', cwd=a); git('commit', '-q', '-m', 'signal', cwd=a); git('push', '-q', cwd=a)
            with open(os.path.join(c, 'data', 'ops_check.json'), 'w', encoding='utf-8') as f:
                f.write(json.dumps({'level': 1, 'as_of': '2026-09-07'}))
            rc, out = self._run(c)
            self.assertNotEqual(rc, 0, '원격이 움직였는데 push 가 성공했다')
            self.assertEqual(self._remote_level(bare), 0, '옛 체크아웃의 점검 결과가 원격을 덮었다')


class W4_WorkflowContracts(unittest.TestCase):
    """watchdog.yml ↔ watchdog.py: 모드·id·if·이슈 조건이 서로를 전부 가리키는가."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, '.github', 'workflows', 'watchdog.yml'), encoding='utf-8') as f:
            cls.y = f.read().replace('\r\n', '\n')
        cls.WD = load('watchdog')

    def _steps(self):
        out = []
        for m in re.finditer(r'- name: (.+)\n((?:\s{8}.*\n)+)', self.y):
            body = m.group(2)
            sid = re.search(r'^\s*id: (\w+)', body, re.M)
            mode = re.search(r'deploy/watchdog\.py (\w+)', body)
            cond = re.search(r'^\s*if: (.+)', body, re.M)
            coe = 'continue-on-error: true' in body
            out.append({'name': m.group(1).strip(), 'id': sid.group(1) if sid else None,
                        'mode': mode.group(1) if mode else None,
                        'if': cond.group(1).strip() if cond else None, 'coe': coe})
        return out

    def test_every_mode_step_has_id_referenced_by_issue_condition(self):
        steps = self._steps()
        issue = next(s for s in steps if s['name'].startswith('이상이면 이슈'))
        issue_if = re.search(r'if: >-\n((?:\s+.*\n)+?)\s*uses:', self.y).group(1)
        modes = {s['mode']: s for s in steps if s['mode']}
        self.assertEqual(set(modes), set(self.WD.MODES), '워크플로 모드와 MODES 가 다르다')
        for mode, s in modes.items():
            self.assertIsNotNone(s['id'], f'{mode} 스텝에 id 가 없다')
            self.assertIn(f"steps.{s['id']}.outputs.alert == '1'", issue_if, f'{mode} 의 alert 를 이슈 조건이 안 읽는다')
        self.assertIn('always()', issue_if)
        self.assertIn('failure()', issue_if)

    def test_daily_steps_skip_the_weekly_slot_and_weekly_steps_gate_on_env(self):
        steps = self._steps()
        daily = {'stale', 'rebalance', 'switchday', 'near', 'stats', 'price'}
        weekly = {'check', 'heartbeat'}
        for s in steps:
            if s['mode'] in daily:
                self.assertEqual(s['if'], "github.event.schedule != '10 0 * * 1'", s['mode'])
            if s['mode'] in weekly:
                self.assertEqual(s['if'], "env.WEEKLY == 'true'", s['mode'])
            if s['mode'] == 'channel':
                self.assertIsNone(s['if'])
        commit = next(s for s in steps if s['name'] == '점검 결과 커밋')
        self.assertEqual(commit['if'], "env.WEEKLY == 'true'")

    def test_holiday_table_step_cannot_block_the_check_commit(self):
        steps = self._steps()
        hol = next(s for s in steps if s['name'] == '휴장일 표 연장')
        commit = next(s for s in steps if s['name'] == '점검 결과 커밋')
        self.assertLess(steps.index(hol), steps.index(commit))
        self.assertTrue(hol['coe'], '휴장일 표 연장이 실패하면 점검 결과 커밋까지 막힌다')
        self.assertIsNotNone(hol['id'])
        issue_if = re.search(r'if: >-\n((?:\s+.*\n)+?)\s*uses:', self.y).group(1)
        self.assertIn(f"steps.{hol['id']}.outcome == 'failure'", issue_if, '휴장일 표 실패가 이슈로 드러나지 않는다')


class W5_TokenRotationContinuity(unittest.TestCase):
    """channel 모드가 회전한 refresh 토큰을 같은 잡의 뒤 모드(알림)가 쓰는가."""

    def test_rotated_token_reaches_later_notify(self):
        WD = load('watchdog')
        KK = load('kakao_keepalive')
        with Sandbox(WD) as sb:
            gh_env = os.path.join(sb.td, 'gh_env')
            names = ('KAKAO_REST_API_KEY', 'KAKAO_REFRESH_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
                     'DISCORD_WEBHOOK_URL', 'WEEKLY', 'GITHUB_ENV')
            saved = {k: os.environ.get(k) for k in names}
            try:
                for k in names:
                    os.environ.pop(k, None)
                os.environ.update(KAKAO_REST_API_KEY='key', KAKAO_REFRESH_TOKEN='old', GITHUB_ENV=gh_env)

                def keepalive():
                    KK.activate_refresh_token('rotated', github_env=gh_env)
                    return 0
                WD.kakao_keepalive_main = keepalive
                WD.mode_channel()
                self.assertNotIn('alert=1', sb.outputs())
                seen = []
                WD.subprocess = types.SimpleNamespace(call=lambda args: seen.append(os.environ.get('KAKAO_REFRESH_TOKEN')) or 0)
                sb.real_notify('t', 'signal', 'd')          # 실제 notify (subprocess.call 만 대역)
                self.assertEqual(seen, ['rotated'], '회전된 토큰이 뒤 알림에 전달되지 않는다')
                self.assertIn('KAKAO_REFRESH_TOKEN=rotated', open(gh_env, encoding='utf-8').read())
            finally:
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v


class W6_HeartbeatCommitLoss(unittest.TestCase):
    """heartbeat 상태는 ops_check.json 커밋에 실린다 — 커밋이 유실되면 다음 주에 한 번 더 간다(설계).
    발송이 실패하면 표시를 남기지 않아 다음 주 재시도한다."""

    def test_lost_commit_resends_and_failed_send_leaves_no_mark(self):
        WD = load('watchdog')
        with Sandbox(WD) as sb:
            prev = {'level': 0, 'level_msg': '정상'}
            json.dump(prev, open('data/ops_check.json', 'w', encoding='utf-8'))
            json.dump({'as_of': '2026-09-04', 'dd': -3.5,
                       'strategies': {'B': {'state': 'QLD', 'gap_pp': 12.5}}},
                      open('data/signal.json', 'w', encoding='utf-8'))
            WD.subprocess = types.SimpleNamespace(run=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('git 생략')),
                                                  check_output=lambda *a, **k: b'', call=lambda *a, **k: 0)
            WD.mode_heartbeat()
            self.assertEqual(len(sb.sent), 1)
            ym = WD.kst_today().strftime('%Y-%m')
            self.assertEqual(json.load(open('data/ops_check.json', encoding='utf-8'))['heartbeat'], ym)
            WD.mode_heartbeat()
            self.assertEqual(len(sb.sent), 1, '같은 달에 두 번 보냈다')
            json.dump(prev, open('data/ops_check.json', 'w', encoding='utf-8'))   # 커밋 유실 = 다음 주 체크아웃에 표시 없음
            WD.mode_heartbeat()
            self.assertEqual(len(sb.sent), 2, '커밋 유실 뒤 재발송(설계) 이 아니다')
            json.dump(prev, open('data/ops_check.json', 'w', encoding='utf-8'))
            WD.notify = lambda *a: 2                          # 발송 실패
            WD.mode_heartbeat()
            self.assertNotIn('heartbeat', json.load(open('data/ops_check.json', encoding='utf-8')),
                             '발송 실패인데 이번 달 표시를 남겼다')


class W7_FreshnessCalendar(unittest.TestCase):
    """[v225] biz_days_since 는 미국 거래일(주말·NYSE 정기 휴장 제외)을 센다 — 노동절 주의 조기 알림 재현.
    판정(state)과 무관한 표시·운영 경고 정의다. 한국 시세는 kr_biz_days_since(한국 달력)로 따로 센다."""

    def test_us_holidays_are_not_counted(self):
        WD = load('watchdog')
        d = WD.date
        self.assertEqual(WD.biz_days_since('2026-09-04', today=d(2026, 9, 8)), 1, '노동절 다음 화요일')
        self.assertEqual(WD.biz_days_since('2026-09-04', today=d(2026, 9, 9)), 2)
        self.assertEqual(WD.biz_days_since('2026-09-04', today=d(2026, 9, 10)), 3, '목요일에야 문턱')
        self.assertEqual(WD.biz_days_since('2026-09-11', today=d(2026, 9, 15)), 2, '휴장 없는 주는 종전과 같다')
        self.assertEqual(WD.biz_days_since('2026-07-02', today=d(2026, 7, 7)), 2, '독립기념일 관측일(금)')

    def test_same_table_as_wait_close(self):
        WD = load('watchdog')
        import importlib.util
        spec = importlib.util.spec_from_file_location('wc_probe', os.path.join(DEPLOY, 'wait_close.py'))
        wc = importlib.util.module_from_spec(spec); spec.loader.exec_module(wc)
        self.assertEqual(WD.us_holidays(2026), wc.nyse_holidays(2026))


if __name__ == '__main__':
    unittest.main()
