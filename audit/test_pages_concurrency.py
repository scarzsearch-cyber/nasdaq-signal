# -*- coding: utf-8 -*-
"""pages.yml 취소 연쇄 회귀 (2026-09-06).

실측(09-04): price 예비 슬롯(:20/:50)이 다음 예약에 밀려 취소됨 → workflow_run(cancelled) 이벤트 → pages 새 실행 생성
→ **워크플로 수준** concurrency(cancel-in-progress) 가 진행 중인 5분 dispatch 배포를 취소 → 그 실행 자신은 skipped(0 스텝).
:25/:55 스냅샷 3건이 다음 스냅샷까지 341~349s 늦게 반영됐다.

두 갈래로 지킨다.
  ① 정적: pages.yml 이 워크플로 수준 concurrency 를 갖지 않고, deploy 잡이 잡 수준 concurrency + 「취소된 선행 실행이면 건너뜀」 조건을 갖는다.
     v203 의 「success 만 허용 금지」(실패한 선행 실행도 재배포)는 그대로다.
  ② 모형: 이벤트 순서 4경우(정상 완료 · 선행 실행 취소 · 연속 갱신 · 수동 dispatch)를 두 정책으로 돌려, 옛 정책이 실측 손실을 재현하고
     새 정책이 마지막 배포에 최신 유효 데이터를 싣는지 본다. 모형의 concurrency 규칙: 같은 그룹에 진행 중인 것이 있으면 새 것이 그것을 취소한다.
     워크플로 수준이면 실행이 생기는 순간 그룹에 들어가고, 잡 수준이면 잡이 실제로 큐에 들어갈 때(if 로 건너뛰면 안 들어간다)만 그룹에 들어간다.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, '.github', 'workflows', 'pages.yml')


def _yml():
    return io.open(PAGES, encoding='utf-8').read()


class StaticContract(unittest.TestCase):
    def test_no_workflow_level_concurrency(self):
        y = _yml()
        self.assertIsNone(re.search(r'^concurrency:', y, re.M), '워크플로 수준 concurrency 가 다시 생겼다 — 취소 연쇄 재발')

    def test_job_level_concurrency_and_skip_condition(self):
        y = _yml()
        job = y[y.index('  deploy:'):]
        self.assertIsNotNone(re.search(r'^    concurrency:
      group: pages
      cancel-in-progress: true', job, re.M), '잡 수준 concurrency')
        m = re.search(r'^    if: (.+)$', job, re.M)
        self.assertIsNotNone(m, 'deploy 잡의 if 가 없다')
        cond = m.group(1)
        self.assertIn("github.event_name != 'workflow_run'", cond)
        self.assertIn("github.event.workflow_run.conclusion != 'cancelled'", cond)
        self.assertNotIn("== 'success'", y, 'v203: 실패한 선행 실행도 재배포해야 한다')
        # if 가 concurrency 보다 앞에 있어도 뒤에 있어도 의미는 같지만, 둘 다 잡 안에 있어야 한다
        self.assertLess(job.index('    concurrency:'), job.index('    steps:'))

    def test_triggers_unchanged(self):
        y = _yml()
        self.assertIn('workflow_run:', y)
        self.assertIn('workflows: ["일일 신호 갱신", "price", "월간 성과 스냅샷 갱신"]', y)
        self.assertIn('types: [completed]', y)
        self.assertIn('workflow_dispatch:', y)


# ------------------------------------------------------------------ 모형
DEPLOY_S = 25            # 배포 잡 소요(실측 중앙 22s)


def simulate(events, policy, cond=None):
    """events: (t, kind, payload) — kind ∈ dispatch(payload=data_version) · push(version) · workflow_run(conclusion).
    policy: 'workflow' | 'job'. 반환: (완료 순서대로의 배포 데이터 버전 목록, 취소된 run 수, 건너뛴 run 수)."""
    cond = cond or (lambda kind, payload: True)
    inflight = None           # (start, end, version)
    done, cancelled, skipped = [], 0, 0
    for t, kind, payload in sorted(events):
        if inflight and inflight[1] <= t:       # 앞선 배포가 끝났다
            done.append(inflight[2]); inflight = None
        if kind == 'workflow_run':
            enters = (policy == 'workflow') or cond(kind, payload)
            if not enters:
                skipped += 1; continue
            if inflight:
                cancelled += 1; inflight = None
            if not cond(kind, payload):         # 워크플로 수준: 그룹엔 들어갔지만 잡은 건너뛴다(실측 skipped)
                skipped += 1; continue
            version = payload.get('version')
        else:
            version = payload
            if inflight:
                cancelled += 1; inflight = None
        inflight = (t, t + DEPLOY_S, version)
    if inflight:
        done.append(inflight[2])
    return done, cancelled, skipped


def _cond(kind, payload):
    return not (kind == 'workflow_run' and payload.get('conclusion') == 'cancelled')


class Model(unittest.TestCase):
    def test_normal_completion(self):
        for pol in ('workflow', 'job'):
            done, c, s = simulate([(0, 'dispatch', 'v1')], pol, _cond)
            self.assertEqual((done, c, s), (['v1'], 0, 0), pol)

    def test_cancelled_predecessor_during_inflight(self):
        ev = [(0, 'dispatch', 'v1'), (8, 'workflow_run', {'conclusion': 'cancelled', 'version': 'v1'})]
        done_old, c_old, s_old = simulate(ev, 'workflow', _cond)
        self.assertEqual((done_old, c_old, s_old), ([], 1, 1), '옛 정책: 진행 중 배포 취소 + skipped — 09-04 실측')
        done_new, c_new, s_new = simulate(ev, 'job', _cond)
        self.assertEqual((done_new, c_new, s_new), (['v1'], 0, 1), '새 정책: 건너뛴 잡은 그룹에 안 들어가 v1 배포가 산다')

    def test_successive_updates_last_wins(self):
        ev = [(0, 'dispatch', 'v1'), (3, 'dispatch', 'v2')]
        for pol in ('workflow', 'job'):
            done, c, s = simulate(ev, pol, _cond)
            self.assertEqual(done, ['v2'], pol)
            self.assertEqual(c, 1)

    def test_manual_dispatch_during_pending_workflow_run(self):
        ev = [(0, 'workflow_run', {'conclusion': 'success', 'version': 'v1'}), (2, 'dispatch', 'v2')]
        for pol in ('workflow', 'job'):
            done, c, s = simulate(ev, pol, _cond)
            self.assertEqual(done, ['v2'], pol)

    def test_failed_predecessor_still_deploys(self):
        ev = [(0, 'workflow_run', {'conclusion': 'failure', 'version': 'v1'})]
        done, c, s = simulate(ev, 'job', _cond)
        self.assertEqual((done, s), (['v1'], 0), 'v203: 실패한 선행 실행도 재배포')


if __name__ == '__main__':
    unittest.main()
