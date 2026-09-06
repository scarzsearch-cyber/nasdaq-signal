# -*- coding: utf-8 -*-
"""위기 타임머신(data/crisis_paths.json · research/build_crisis_paths.py · signal.html initTimeMachine) 회귀 (2026-09-06 · 장부 audit/CRISIS_2026-09-06.md).

정의(고정하는 계약):
  경로 = deploy/build_stats sc_us_2000 과 같은 재료·규약(reentry_lib.build → 방어 40/40/20 월간 재조정(MIX_V23) → run(B −16/−16) · 달러 · 세전 · 편도 비용 동일)
  구간 = update_signal.CRISES 의 (이름, 고점일) — 고점일 이후 첫 거래일부터 400거래일 · 각 경로를 그 첫 값으로 나눠 시작 1.0(전략·2배 보유 각각)
  2배 보유 = qldr 누적(첫날 수익 0) · 화면 = 1,000만원 × 값 · (값−1)% 소수 1자리 · 슬라이더 0~399 · 재생 = 100ms/일, 끝(399)에서 정지
  공표 대조 = _meta.engine_check 의 전체 곡선 final vs strategy_stats us_2000 B.final — 같은 기간(2000-01-03~)·통화·전략·비용·정규화(시작 1.0)라 비교 가능
  수동 생성 정책 유지: 이 검사는 재생성하지 않고 「낡았는가」만 알린다.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, 'data', 'crisis_paths.json')
STATS = os.path.join(ROOT, 'data', 'strategy_stats.json')
_E = {}


def load_doc():
    return json.load(io.open(JSON_PATH, encoding='utf-8'))


def crises():
    sys.path.insert(0, os.path.join(ROOT, 'deploy'))
    from update_signal import CRISES
    return list(CRISES)


def engine_paths():
    """엔진 경로(입력) — 생성기 함수는 부르지 않고 같은 재료로 곡선을 만든 뒤 **독립적으로** 자른다."""
    if not _E:
        sys.path.insert(0, ROOT)
        cwd = os.getcwd(); os.chdir(ROOT)
        try:
            import pandas as pd
            import hist_defasset as DA
            import reentry_lib as RL
            D = dict(RL.build())
            D['schdr'] = DA.mix_monthly(D['idx'], DA.MIX_V23, D['schdr'])
            curve, w, turn = RL.run(D, [(('dd', -0.16), 1.0, 0)], enter=-0.16)
            lo = int(D['idx'].searchsorted(curve.index[0]))
            rr = np.nan_to_num(np.asarray(D['qldr'][lo:lo + len(curve)], float)).copy(); rr[0] = 0.0
            _E['curve'] = curve; _E['hold'] = pd.Series(np.cumprod(1 + rr), index=curve.index)
            _E['ddv'] = pd.Series(np.asarray(D['ddv'], float), index=D['idx'])
        finally:
            os.chdir(cwd)
    return _E


def contract(doc, names):
    bad = []
    meta = doc.get('_meta', {})
    m = re.search(r'final ([\d.]+) == strategy_stats us_2000 B\.final ([\d.]+)', meta.get('engine_check', ''))
    if not m: bad.append('engine_check 문구 없음')
    else:
        got, pub_then = float(m.group(1)), float(m.group(2))
        stats = json.load(io.open(STATS, encoding='utf-8'))
        pub_now = float(next(s for s in stats['scenarios'] if s['key'] == 'us_2000')['strategies']['B']['final'])
        if abs(got - pub_now) > 0.005 + 1e-9:
            bad.append('낡음: 생성 당시 final %.3f vs 현재 공표 %.3f — research/build_crisis_paths.py 수동 재실행 필요' % (got, pub_now))
    keys = [k for k in doc if k != '_meta']
    if keys != [n for n, _ in names]: bad.append('구간 이름/순서 %s != CRISES %s' % (keys, [n for n, _ in names]))
    for n_, peak in names:
        c = doc.get(n_)
        if not c: continue
        if c.get('peak') != peak: bad.append('%s 고점일 %s != %s' % (n_, c.get('peak'), peak))
        s, h = c.get('strategy', []), c.get('leveraged_hold', [])
        if len(s) != meta.get('days', 400) or len(h) != len(s): bad.append('%s 길이 %d/%d' % (n_, len(s), len(h)))
        if s and (abs(s[0] - 1.0) > 1e-9 or abs(h[0] - 1.0) > 1e-9): bad.append('%s 시작값 %s/%s' % (n_, s[:1], h[:1]))
        if not (np.isfinite(s).all() and np.isfinite(h).all() and min(s + h) > 0): bad.append('%s 비유한/비양수' % n_)
    return bad


class T1_ContractAndFreshness(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(contract(load_doc(), crises()), [])

    def test_contract_catches_defects(self):
        base = load_doc(); names = crises()
        def mut(f):
            d = json.loads(json.dumps(base)); f(d); return contract(d, names)
        self.assertTrue(any('낡음' in b for b in mut(lambda d: d['_meta'].__setitem__('engine_check', 'final 150.000 == strategy_stats us_2000 B.final 150.000'))))
        self.assertTrue(any('고점일' in b for b in mut(lambda d: d[names[0][0]].__setitem__('peak', '2000-03-28'))))
        self.assertTrue(any('길이' in b for b in mut(lambda d: d[names[1][0]]['strategy'].pop())))
        self.assertTrue(any('시작값' in b for b in mut(lambda d: d[names[2][0]]['strategy'].__setitem__(0, 0.99))))
        self.assertTrue(any('구간 이름' in b for b in mut(lambda d: d.pop(names[3][0]))))


class T2_EngineSlice(unittest.TestCase):
    def test_slices_match_independent_cut(self):
        E = engine_paths(); doc = load_doc()
        import pandas as pd
        for name, peak in crises():
            c = doc[name]
            i0 = int(np.searchsorted(E['curve'].index.values, np.datetime64(peak)))      # 고점일 이후 첫 거래일
            self.assertEqual(str(E['curve'].index[i0].date()), peak, '고점일은 거래일이어야 한다(%s)' % name)
            s = E['curve'].values[i0:i0 + 400]; h = E['hold'].values[i0:i0 + 400]
            s = s / s[0]; h = h / h[0]
            self.assertEqual(len(s), 400)
            self.assertLessEqual(float(np.max(np.abs(s - np.asarray(c['strategy'])))), 5e-5, name)       # JSON 은 4자리 반올림
            self.assertLessEqual(float(np.max(np.abs(h - np.asarray(c['leveraged_hold'])))), 5e-5, name)
            # 고점일 = 252일 고점(엔진 낙폭 0) — 「고점 이후」라는 화면 문구의 근거
            self.assertEqual(float(E['ddv'].loc[pd.Timestamp(peak)]), 0.0, '%s 고점일에 엔진 낙폭이 0 이 아니다' % name)

    def test_full_curve_final_equals_published_now(self):
        E = engine_paths()
        pub = float(next(s for s in json.load(io.open(STATS, encoding='utf-8'))['scenarios'] if s['key'] == 'us_2000')['strategies']['B']['final'])
        self.assertLessEqual(abs(float(E['curve'].iloc[-1]) - pub), 0.005 + 1e-9)


class T3_ScreenPaint(unittest.TestCase):
    def test_tm_paint_amounts_and_labels(self):
        if not shutil.which('node'):
            self.skipTest('node 없음')
        src = io.open(os.path.join(ROOT, 'signal.html'), encoding='utf-8').read()
        def extract(a, b):
            i = src.index(a); return src[i:src.index(b, i)]
        fmtA = extract('function fmtA(v){', '\n/* [v146]') if '\n/* [v146]' in src[src.index('function fmtA(v){'):] else extract('function fmtA(v){', '\nfunction ')
        tm = extract('let TM = null, TM_KEY = null, TM_TIMER = null;', '\nfunction tmToggle(){')
        stop = extract('function tmStop(){', '\n}\n') + '\n}'
        js = (r"""
const els = {tmSlider:{value:'0', max:'399'}, tmNums:{innerHTML:''}, tmDay:{innerHTML:''}, tmPlay:{textContent:''}, tmWrap:{hidden:true}, tmTabs:{innerHTML:''}};
const document = {getElementById:(id)=>els[id]||null, querySelectorAll:()=>[]};
""" + fmtA + "\n" + tm + "\n" + stop + r"""
TM = {'닷컴 2000': {peak:'2000-03-27', strategy:[1.0, 0.9, 0.516, 0.5416], leveraged_hold:[1.0, 0.8, 0.0331, 0.0449]}};
TM_KEY = '닷컴 2000';
const out = {};
els.tmSlider.value = '0'; tmPaint(); out.i0 = [els.tmNums.innerHTML, els.tmDay.innerHTML];
els.tmSlider.value = '3'; tmPaint(); out.iEnd = [els.tmNums.innerHTML, els.tmDay.innerHTML];
els.tmSlider.value = '99'; tmPaint(); out.iOver = els.tmDay.innerHTML;
console.log(JSON.stringify(out));
""")
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 't.js')
            with io.open(p, 'w', encoding='utf-8') as f:
                f.write(js)
            r = subprocess.run(['node', p], capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertIn('1000.0만원', out['i0'][0]); self.assertIn('+0.0%', out['i0'][0]); self.assertIn('<b>0거래일</b> / 3일', out['i0'][1])
        self.assertIn('541.6만원', out['iEnd'][0]); self.assertIn('-45.8%', out['iEnd'][0]); self.assertIn('44.9만원', out['iEnd'][0]); self.assertIn('-95.5%', out['iEnd'][0])
        self.assertIn('<b>3거래일</b> / 3일', out['iOver'], '슬라이더가 끝을 넘어도 마지막 날로 고정')


if __name__ == '__main__':
    unittest.main()
