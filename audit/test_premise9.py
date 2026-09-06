# -*- coding: utf-8 -*-
"""전제 감시(research/surv_map.py) 4변수 · 점검 파서(내가_보는_것/점검.py) · AUM · Level 회귀 (2026-09-06 · 장부 audit/PREMISE_2026-09-06.md).

정의(surv_map 판독 · 이 파일이 고정하는 계약):
  창 = 거래일 수 3년 756 · 5년 1260 · 10년 2520 · 20년 5040 · 현재값 = 엔진 마지막 날(i = n−1) 기준 뒤로 w 일수익
  지수 CAGR = (끝/시작)^(252/w) − 1 · 변동성 = 일수익 모집단 표준편차(ddof 0) × √252 · 2배 드래그 = 2×지수CAGR − 2배CAGR(2배 = qldr 누적)
  역사 백분위 = 창 종료일을 w−1 부터 5일 보폭으로 옮긴 값들 중 현재값 이하 비율 · 입력 = eng_common/hypo_gates 의 54년 체인(1972-02-07~)
A  독립 재계산(가격 비율·표준편차 직접 · 누적 로그/제곱합 트릭 미사용) vs 실제 surv_map 출력 — 표시 반올림(0.1%p · 1%) 안
B  실제 생산자 출력 ↔ 점검.py 파서 연결 · 누락/서식 변화/중복/AUM 결측·중복·판정불가/exec 누락이 정상으로 오인되지 않는다
C  AUM: 합성 장부 — 정상·결측 다리·비수치·최신 행 선택(파일 순서가 아니라 as_of) · 밴드 경계(300/100억)
D  Level 산정 — BANDS 경계에서 SURVIVAL §F 규약(경계값 = 안쪽 · 1개 주의 = 1 · 2개 = 2 · 범위 밖 = 3 · 못 읽음 ≥ 2)
BANDS·AUM 임계·알림 정책은 바꾸지 않는다.
"""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, '내가_보는_것', '점검.py')
SURV = os.path.join(ROOT, 'research', 'surv_map.py')
EXEC = os.path.join(ROOT, 'research', 'exec_cost.py')
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')
_CACHE = {}


def producer(script):
    """실제 생산자 출력(한 번만 돈다 · 읽기 전용 스크립트)."""
    if script not in _CACHE:
        p = subprocess.run([sys.executable, script], capture_output=True, text=True, encoding='utf-8', errors='replace',
                           env=ENV, cwd=ROOT, timeout=600)
        assert p.returncode == 0, p.stderr[-800:]
        _CACHE[script] = p.stdout
    return _CACHE[script]


def parse5(out):
    blk = out.split('[5]')[1].split('[6]')[0]
    got = {}
    for ln in blk.splitlines():
        m = re.match(r'\s{2}(\S.*?)\s{2,}([+-]?[\d.]+)%(?:/yr)?\s+· 역사 백분위 (\d+)%', ln)
        if m:
            got[m.group(1).strip()] = (float(m.group(2)), int(m.group(3)))
    return got


class A_IndependentVariables(unittest.TestCase):
    def test_four_variables_and_percentiles(self):
        import numpy as np
        import pandas as pd
        sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'research'))
        cwd = os.getcwd(); os.chdir(ROOT)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                import hypo_gates as G                     # 엔진 입력만(surv_map 함수 미호출)
            px = np.asarray(G.D['px'], float); qldr = np.nan_to_num(np.asarray(G.D['qldr'], float))
        finally:
            os.chdir(cwd)
        n = len(px)
        r = pd.Series(px).pct_change().fillna(0.0).values
        lev = np.cumprod(1 + qldr)
        cagr = lambda L, i, w: (L[i] / L[max(i - w, 0)]) ** (252.0 / w) - 1.0
        vol = lambda i, w: float(np.std(r[i + 1 - w:i + 1], ddof=0) * np.sqrt(252))
        W = {'3년': 756, '5년': 1260, '10년': 2520, '20년': 5040}
        i = n - 1
        cur, pct = {}, {}
        rank = lambda vals, v: float(np.mean(np.asarray(vals) <= v)) * 100
        for lab, w in W.items():
            k = '지수 %s CAGR' % lab
            cur[k] = cagr(px, i, w) * 100
            pct[k] = rank([cagr(px, j, w) for j in range(w - 1, n, 5)], cur[k] / 100)
            if w <= 2520:
                k2 = '지수 %s 변동성' % lab
                cur[k2] = vol(i, w) * 100
                pct[k2] = rank([vol(j, w) for j in range(w - 1, n, 5)], cur[k2] / 100)
        cur['2배 드래그 3년'] = (2 * cagr(px, i, 756) - cagr(lev, i, 756)) * 100
        pct['2배 드래그 3년'] = rank([2 * cagr(px, j, 756) - cagr(lev, j, 756) for j in range(755, n, 5)], cur['2배 드래그 3년'] / 100)
        prod = parse5(producer(SURV))
        self.assertEqual(set(cur), set(prod) - {'B 5년 CAGR'} - {k for k in prod if k not in cur}, prod.keys())
        for k, v in cur.items():
            pv, pp = prod[k]
            self.assertLessEqual(abs(v - pv), 0.051, (k, v, pv))           # 표시는 0.1 반올림
            self.assertLessEqual(abs(pct[k] - pp), 1.0, (k, pct[k], pp))  # 백분위는 1% 반올림
        self.assertEqual(n, 13749)


def load_check(argv):
    """점검.py 를 파일 경로로 불러온다(JSON_MODE 는 import 시점 argv 로 정해진다)."""
    old = sys.argv
    sys.argv = ['점검.py'] + list(argv)
    try:
        spec = importlib.util.spec_from_file_location('gumjeom', CHECK)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old
    return mod


def run_check(mod, surv_out, exec_out):
    def fake_run(script, *args):
        if script.endswith('surv_map.py'):
            return True, surv_out
        if script.endswith('exec_cost.py'):
            return True, exec_out
        raise AssertionError(script)
    mod.run = fake_run
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.main()
    return json.loads(buf.getvalue().strip().splitlines()[-1])


class B_ParserCoupling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.surv = producer(SURV)
        cls.exec_ = producer(EXEC)
        cls.mod = load_check(['--json'])

    def test_real_outputs_parse_completely(self):
        R = run_check(self.mod, self.surv, self.exec_)
        self.assertEqual(R['health_errors'], [])
        self.assertTrue(R['ok'])
        self.assertEqual([v['name'] for v in R['vars']], ['지수 10년 CAGR', '지수 20년 CAGR', '지수 3년 변동성', '2배 드래그 3년'])
        self.assertTrue(all(v['value'] is not None for v in R['vars']))
        prod = parse5(self.surv)
        for v in R['vars']:
            self.assertEqual(v['value'], prod[v['name']][0], v)           # 파서가 읽은 값 = 생산자가 찍은 값
        self.assertEqual(sorted(a['code'] for a in R['aum']), ['305080', '411060', '418660', '458730'])
        self.assertEqual(set(R['exec']), {'events', 'need', 'nav_days'})
        self.assertIn(R['level'], (0, 1, 2, 3))

    def _mut(self, surv):
        return run_check(self.mod, surv, self.exec_)

    def test_missing_variable_is_not_normal(self):
        surv = '\n'.join(l for l in self.surv.splitlines() if not l.startswith('  지수 20년 CAGR'))
        R = self._mut(surv)
        self.assertIn('var_missing:지수 20년 CAGR', R['health_errors'])
        self.assertGreaterEqual(R['level'], 2)
        self.assertTrue(any('서식' in t for t in R['todo']))

    def test_format_drift_is_not_normal(self):
        surv = re.sub(r'^  지수 10년 CAGR\s{2,}', '  지수 10년 CAGR ', self.surv, flags=re.M)   # 두 칸 → 한 칸
        R = self._mut(surv)
        self.assertIn('var_missing:지수 10년 CAGR', R['health_errors'])
        self.assertGreaterEqual(R['level'], 2)

    def test_duplicate_variable_with_conflicting_value_is_flagged(self):
        lines = self.surv.splitlines()
        i = next(k for k, l in enumerate(lines) if l.startswith('  지수 10년 CAGR'))
        lines.insert(i + 1, '  지수 10년 CAGR        -9.9%                   · 역사 백분위 1%')
        R = self._mut('\n'.join(lines))
        self.assertTrue(any(e.startswith('var_duplicate:지수 10년 CAGR') for e in R['health_errors']), R['health_errors'])
        self.assertIsNone(next(v for v in R['vars'] if v['name'] == '지수 10년 CAGR')['value'], '둘 중 하나를 골라 쓰지 않는다')
        self.assertGreaterEqual(R['level'], 2, '값이 둘이면 어느 쪽도 믿을 수 없다 — 정상으로 발행하지 않는다')

    def test_aum_gaps_are_flagged(self):
        s = self.surv
        s1 = re.sub(r'^  305080 방어 국채 .*$', '  305080 방어 국채        시총 자료 오류  [판정 불가]  (2026-09-04 기준)', s, flags=re.M)
        R = self._mut(s1); self.assertIn('aum_missing:305080', R['health_errors']); self.assertFalse(R['ok'])
        dup = next(l for l in s.splitlines() if l.startswith('  411060'))
        s2 = s.replace(dup, dup + '\n' + dup)
        R = self._mut(s2); self.assertIn('aum_duplicate:411060', R['health_errors'])
        s3 = s.replace(dup, dup + '\n' + dup.replace('411060', '999999'))
        R = self._mut(s3); self.assertIn('aum_unexpected:999999', R['health_errors'])
        s4 = s.replace(dup, dup.replace('[정상]', '[★경보]').replace('40,871', '99'))
        R = self._mut(s4); self.assertTrue(any('상품 AUM 경보' in t and '411060' in t for t in R['todo']))

    def test_exec_parse_gap_is_flagged(self):
        ex = '\n'.join(l for l in self.exec_.splitlines() if '진행률' not in l)
        R = run_check(self.mod, self.surv, ex)
        self.assertIn('exec_parse:events', R['health_errors']); self.assertIn('exec_parse:need', R['health_errors'])
        self.assertFalse(R['ok'])


class C_AumSyntheticLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'research'))
        cwd = os.getcwd(); os.chdir(ROOT)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                import surv_map                           # import 시 엔진 검산이 돈다(읽기 전용)
            cls.sm = surv_map
        finally:
            os.chdir(cwd)

    def _run(self, rows):
        import pandas as pd
        df = pd.DataFrame(rows, columns=['as_of', 'code', 'name', 'mktcap_eok']).astype(str)
        real = self.sm.pd.read_csv
        self.sm.pd.read_csv = lambda p, *a, **k: df.copy() if str(p).endswith('nav_history.csv') else real(p, *a, **k)
        cwd = os.getcwd(); os.chdir(ROOT)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.sm.main()
        finally:
            self.sm.pd.read_csv = real
            os.chdir(cwd)
        return buf.getvalue().split('[6]')[1]

    def test_bands_boundaries_and_gaps(self):
        base = [('2026-09-04', '418660', 'x', '300'), ('2026-09-04', '458730', 'x', '299'),
                ('2026-09-04', '305080', 'x', '100'), ('2026-09-04', '411060', 'x', '99')]
        out = self._run(base)
        self.assertRegex(out, r'418660 .*\[정상\]'); self.assertRegex(out, r'458730 .*\[주의\]')
        self.assertRegex(out, r'305080 .*\[주의\]'); self.assertRegex(out, r'411060 .*\[★경보\]')
        out = self._run(base[:3])
        self.assertIn('411060', out); self.assertIn('수집분 없음', out)
        out = self._run(base[:3] + [('2026-09-04', '411060', 'x', 'abc')])
        self.assertRegex(out, r'411060 .*\[판정 불가\]')

    def test_latest_row_is_by_as_of_not_file_order(self):
        rows = [('2026-09-04', '418660', 'x', '6421'), ('2026-09-01', '418660', 'x', '50'),   # 옛 행이 뒤에 붙어도
                ('2026-09-04', '458730', 'x', '43239'), ('2026-09-04', '305080', 'x', '2131'), ('2026-09-04', '411060', 'x', '40871')]
        out = self._run(rows)
        self.assertRegex(out, r'418660 .*6,421억  \[정상\]  \(2026-09-04 기준\)', out)


SURV_TEMPLATE = '''[5] 현재
  지수 10년 CAGR        {c10:+.1f}%                   · 역사 백분위 50%
  지수 20년 CAGR        {c20:+.1f}%                   · 역사 백분위 50%
  지수 3년 변동성          {v3:.1f}%                    · 역사 백분위 50%
  2배 드래그 3년          {d3:.1f}%/yr                  · 역사 백분위 50%

[6] 상품 생존
  418660 공격 레버리지      시총    6,421억  [정상]  (2026-09-04 기준)
  458730 방어 배당        시총   43,239억  [정상]  (2026-09-04 기준)
  305080 방어 국채        시총    2,131억  [정상]  (2026-09-04 기준)
  411060 방어 금         시총   40,871억  [정상]  (2026-09-04 기준)
'''
EXEC_MIN = '  수집 8 영업일 (2026-08-26 ~ 2026-09-04)\n  진행률 0/20 — 표본 부족, 아직 판정 불가\n'


class D_LevelBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_check(['--json'])

    def lvl(self, **kv):
        vals = dict(c10=20.0, c20=16.0, v3=20.0, d3=8.0); vals.update(kv)
        return run_check(self.mod, SURV_TEMPLATE.format(**vals), EXEC_MIN)

    def test_boundary_values_are_inside(self):
        R = self.lvl(c10=4.1, c20=9.5, v3=35.6, d3=11.7)       # 주의선 = 안쪽(밖이 아니다)
        self.assertEqual(R['level'], 0); self.assertEqual([v['state'] for v in R['vars']], ['정상'] * 4)

    def test_one_two_and_out_of_range(self):
        self.assertEqual(self.lvl(c10=4.0)['level'], 1)
        self.assertEqual(self.lvl(c10=4.0, v3=35.7)['level'], 2)
        R = self.lvl(d3=29.4); self.assertEqual((R['level'], R['vars'][3]['state']), (1, '주의'))   # 범위밖선 경계 = 범위 안(주의선은 이미 넘었으니 주의)
        R = self.lvl(d3=29.5); self.assertEqual(R['level'], 3); self.assertEqual(R['vars'][3]['state'], '역사 범위 밖')
        R = self.lvl(c20=3.1); self.assertEqual((R['level'], R['vars'][1]['state']), (1, '주의'))
        R = self.lvl(c20=3.0); self.assertEqual(R['level'], 3)

    def test_unread_variable_raises_level(self):
        surv = SURV_TEMPLATE.format(c10=20.0, c20=16.0, v3=20.0, d3=8.0).replace('  지수 3년 변동성', '  지수 3년 변동성(구)')
        R = run_check(self.mod, surv, EXEC_MIN)
        self.assertGreaterEqual(R['level'], 2); self.assertIn('var_missing:지수 3년 변동성', R['health_errors'])


if __name__ == '__main__':
    unittest.main()
