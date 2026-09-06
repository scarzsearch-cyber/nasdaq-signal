# -*- coding: utf-8 -*-
"""낙폭 백분위(data/dd_percentile.json · research/emit_dd_distribution.py · signal.html ddDeeperPct) 회귀 (2026-09-06 · 장부 audit/DDPCT_2026-09-06.md).

정의(고정하는 계약):
  분포 = 엔진 chain(hist_defensive.build('chain')) 의 252거래일 고점 대비 낙폭 ddv(소수) × 100 → % · 유한값 전부(n = 엔진 거래일 수)
  경계 = 1~99 백분위(생성기: numpy 기본 선형 보간 · 소수 4자리) · 오름차순(깊은 쪽이 앞) · edges[98] = 0(고점 갱신일이 11% 라 p89~p99 가 0)
  화면 = 「오늘보다 더 깊었던 날 p%」 = 오늘 낙폭보다 **엄격히 작은** 경계의 수(정수 %) · 0 이면 「가장 깊은 축」
  운영 일봉(data/qqq.csv · 매일)과 이 분포(월간 원자료 연장 뒤 생성)의 끝 날짜 차이는 정상 시차 — 여기서 검사하지 않는다.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, 'data', 'dd_percentile.json')
_ENGINE = {}


def engine_dd():
    """엔진 입력(읽기 전용) — 생성기 함수를 부르지 않는다."""
    if 'dd' not in _ENGINE:
        sys.path.insert(0, ROOT)
        cwd = os.getcwd(); os.chdir(ROOT)
        try:
            import pandas as pd
            import hist_defensive as DF
            D = DF.build('chain')
            _ENGINE['dd'] = np.asarray(D['ddv'], float) * 100.0
            _ENGINE['idx'] = pd.DatetimeIndex(D['idx'])
        finally:
            os.chdir(cwd)
    return _ENGINE['dd'], _ENGINE['idx']


def contract(doc, dd=None, idx=None):
    """JSON 이 정의를 지키는지 — 위반 목록을 돌려준다(빈 목록 = 통과). 생성기의 보간식은 쓰지 않는다."""
    bad = []
    e = np.asarray(doc.get('edges', []), float)
    if e.size != 99: bad.append('edges 99개 아님(%d)' % e.size)
    if e.size and not np.all(np.diff(e) >= 0): bad.append('edges 비단조')
    if e.size == 99 and e[98] != 0: bad.append('edges[98] != 0 (%s)' % e[98])
    if doc.get('percentiles') != list(range(1, 100)): bad.append('percentiles 1~99 아님')
    if dd is not None:
        n = dd.size
        if doc.get('n') != n: bad.append('n %s != 엔진 %d' % (doc.get('n'), n))
        if str(doc.get('start')) != str(idx[0].date()) or str(doc.get('end')) != str(idx[-1].date()):
            bad.append('start/end %s~%s != 엔진 %s~%s' % (doc.get('start'), doc.get('end'), idx[0].date(), idx[-1].date()))
        for k, v in (('min', dd.min()), ('max', dd.max()), ('median', np.median(dd))):
            if abs(float(doc.get(k, np.nan)) - v) > 1e-4 + 1e-9: bad.append('%s %s != %.4f' % (k, doc.get(k), v))
        # 경험분포 괄호(보간식 무관): 경계 e_p 아래 비율 ≤ p ≤ 경계 이하 비율 — 순서통계 하나(1/n)와
        #   생성기의 소수 4자리 반올림(±5e-5 %p)만큼 여유
        if e.size == 99:
            tol = 1.0 / n + 1e-9; rnd = 5e-5
            for i, ep in enumerate(e):
                p = (i + 1) / 100.0
                lo = float(np.mean(dd < ep - rnd)); hi = float(np.mean(dd <= ep + rnd))
                if not (lo - tol <= p <= hi + tol):
                    bad.append('p%d 경계 %.4f 가 경험분포 밖(%.5f~%.5f)' % (i + 1, ep, lo, hi)); break
    return bad


class T1_JsonMatchesEngine(unittest.TestCase):
    def test_contract_against_engine(self):
        dd, idx = engine_dd()
        doc = json.load(io.open(JSON_PATH, encoding='utf-8'))
        self.assertEqual(contract(doc, dd, idx), [])
        self.assertGreaterEqual(float(np.mean(dd == 0)) * 100, 5.0, '고점 갱신일 동률이 분포의 큰 덩어리 — 화면은 이를 세지 말아야 한다')

    def test_screen_mapping_error_bound(self):
        """정수 % 표시의 오차: 엄격 경계 수 vs 정확한 「더 깊은 날」 분율 — 전 일자 1%p 이내(99개 경계 근사)."""
        dd, _ = engine_dd()
        e = np.asarray(json.load(io.open(JSON_PATH, encoding='utf-8'))['edges'], float)
        s = np.sort(dd)
        p_strict = np.searchsorted(e, dd, side='left')
        f_strict = np.searchsorted(s, dd, side='left') / dd.size * 100
        self.assertLessEqual(float(np.max(np.abs(p_strict - f_strict))), 1.01)
        z = dd == 0
        self.assertTrue(z.any())
        self.assertEqual(int(p_strict[z][0]), int(np.sum(e < 0)))                 # 고점일 = 음수 경계 수
        p_incl = np.searchsorted(e, dd, side='right')                              # 종전(≤) 셈은 고점일에 99 를 냈다
        self.assertEqual(int(p_incl[z][0]), 99)
        self.assertGreater(99 - f_strict[z][0], 5.0, '종전 셈의 고점일 오차가 5%p 를 넘는다(수정 근거)')

    def test_contract_catches_injected_defects(self):
        dd, idx = engine_dd()
        base = json.load(io.open(JSON_PATH, encoding='utf-8'))
        def mut(f):
            d = json.loads(json.dumps(base)); f(d); return contract(d, dd, idx)
        self.assertTrue(any('비단조' in b for b in mut(lambda d: d['edges'].__setitem__(50, d['edges'][49] - 1.0))))
        self.assertTrue(any('edges[98]' in b for b in mut(lambda d: d['edges'].__setitem__(98, -0.1))))
        self.assertTrue(any(b.startswith('n ') for b in mut(lambda d: d.__setitem__('n', d['n'] + 1))))
        self.assertTrue(any('start/end' in b for b in mut(lambda d: d.__setitem__('end', '2026-01-02'))))
        self.assertTrue(any('경험분포 밖' in b for b in mut(lambda d: d['edges'].__setitem__(18, d['edges'][18] + 3.0))))   # p19 경계를 3%p 올림
        self.assertTrue(any('median' in b for b in mut(lambda d: d.__setitem__('median', -9.0))))


class T2_ScreenFunction(unittest.TestCase):
    def test_dd_deeper_pct_is_strict(self):
        if not shutil.which('node'):
            self.skipTest('node 없음')
        src = io.open(os.path.join(ROOT, 'signal.html'), encoding='utf-8').read()
        i = src.index('function ddDeeperPct(dd){'); j = src.index('\nfunction paintDdPct(', i)
        fn = src[i:j]
        js = ("let DDPCT = {edges: [-50, -40, -30, -20, -10, 0, 0, 0]};\n" + fn + "\n"
              "const out = {zero: ddDeeperPct(0), tie20: ddDeeperPct(-20), between: ddDeeperPct(-25), below: ddDeeperPct(-60), nullish: ddDeeperPct(null), nan: ddDeeperPct(NaN)};\n"
              "DDPCT = null; out.noData = ddDeeperPct(-5);\nconsole.log(JSON.stringify(out));")
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 't.js')
            with io.open(p, 'w', encoding='utf-8') as f:
                f.write(js)
            r = subprocess.run(['node', p], capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out['zero'], 5, '고점(0)에서는 음수 경계 5개만 — 동률 0 은 세지 않는다(종전 ≤ 셈은 8)')
        self.assertEqual(out['tie20'], 3, '경계와 같은 값(-20)은 「더 깊은」 쪽에 안 들어간다 — -50·-40·-30 셋(종전 ≤ 셈은 4)')
        self.assertEqual((out['between'], out['below']), (3, 0))
        self.assertIsNone(out['nullish']); self.assertIsNone(out['nan']); self.assertIsNone(out['noData'])


if __name__ == '__main__':
    unittest.main()
