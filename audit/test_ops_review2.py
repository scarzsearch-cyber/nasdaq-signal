"""2차 심층 코드리뷰(2026-09-05 · 운영·화면 20파일) 회귀 검사.

네트워크 0 · 실측 장부(data/*.csv) 무접촉 · 알림 전송 없음. 모든 입력은 고정 응답과 가짜 시계다.
결함 반례와 정상 동작 보존 검사를 함께 포함한다. v220 근거는
audit/DEEP_REVIEW_OPS_UI_2026-09-05.md §F 에 있다. 수정 전 상태를 다시 재현하려면
``OPS_REVIEW2_OLD=<옛 deploy 디렉터리>`` 로 옛 사본을 가리키면 된다.
이 옵션은 deploy만 바꾼다. HTML 검사는 ROOT의 현재 화면을 읽는다.
v221 추가6검사 및 실패 재현은 audit/OPS_UI_CROSSCHECK_2026-09-05.md 참조.

실행:  python -m unittest audit.test_ops_review2  (저장소 루트에서)
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
from unittest.mock import patch

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEPLOY = os.environ.get('OPS_REVIEW2_OLD') or os.path.join(ROOT, 'deploy')
if DEPLOY not in sys.path:
    sys.path.insert(0, DEPLOY)


def load(name):
    """deploy 모듈을 경로로 적재한다 (옛 사본 대조용 OPS_REVIEW2_OLD 지원)."""
    path = os.path.join(DEPLOY, name + '.py')
    spec = importlib.util.spec_from_file_location('ops_review2_' + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ts(text):
    return int(pd.Timestamp(text, tz='UTC').timestamp())


class FakeResponse:
    def __init__(self, body):
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def yahoo_payload(stamps, closes, meta, adj=None):
    quote = {'open': list(closes), 'high': list(closes), 'low': list(closes),
             'close': list(closes), 'volume': [1000] * len(stamps)}
    res = {'timestamp': list(stamps), 'indicators': {'quote': [quote]}, 'meta': meta}
    if adj is not None:
        res['indicators']['adjclose'] = [{'adjclose': list(adj)}]
    return {'chart': {'result': [res]}}


def fx_session_stamps(first_session_start_utc, n):
    """런던 서머타임 규약 - 각 세션은 전날 23:00 UTC 에 시작한다(야후 실측 2026-09-05)."""
    out, t = [], pd.Timestamp(first_session_start_utc, tz='UTC')
    while len(out) < n:
        if t.weekday() in (6, 0, 1, 2, 3):   # 일~목 23:00 시작 = 월~금 세션 (금·토 시작 세션은 없다)
            out.append(int(t.timestamp()))
        t += pd.Timedelta(days=1)
    return out


class RefreshHistIntradayGuard(unittest.TestCase):
    """R2-11 · ^TNX 는 마지막 체결이 마감 1분 전(18:59)이라 마감 뒤에도 장중으로 오인돼
    확정봉이 매달 지워졌다(yahoo_TNX.csv 가 다른 미국 자료보다 늘 하루 짧았다)."""

    def setUp(self):
        self.RH = load('refresh_hist')
        self.RH.FAILURES.clear()

    def _tnx_meta(self):
        start, end = ts('2026-09-04 12:20'), ts('2026-09-04 19:00')
        return start, end, {'regularMarketTime': end - 60,
                            'currentTradingPeriod': {'regular': {'start': start, 'end': end}},
                            'exchangeTimezoneName': 'America/Chicago'}

    def test_closed_session_bar_survives_late_last_print(self):
        RH = self.RH
        start, end, meta = self._tnx_meta()
        df = pd.DataFrame({'close': [4.762, 4.784]},
                          index=pd.to_datetime(['2026-09-03', '2026-09-04']))
        RH.time = types.SimpleNamespace(time=lambda: end + 12 * 3600)   # 월간 슬롯(07:17 UTC) 상당
        kept = RH._drop_intraday_bar(df, meta)
        self.assertEqual(len(kept), 2, '마감 12시간 뒤인데 regularMarketTime<end 라는 이유로 확정봉을 지웠다')

    def test_live_session_bar_is_still_dropped(self):
        RH = self.RH
        start, end, meta = self._tnx_meta()
        meta = dict(meta, regularMarketTime=start + 3600)
        df = pd.DataFrame({'close': [4.762, 4.784]},
                          index=pd.to_datetime(['2026-09-03', '2026-09-04']))
        RH.time = types.SimpleNamespace(time=lambda: start + 3600)
        self.assertEqual(len(RH._drop_intraday_bar(df, meta)), 1)


class RefreshHistFxLabels(unittest.TestCase):
    """R2-12 · 환율(KRW=X) 봉은 런던 서머타임에 전날 23:00 UTC 에 시작한다. UTC 로 자르면
    라벨이 하루 이르고(금요일 세션 -> 목요일), FRED 꼬리(금요일)를 이음날로 못 찾아 예비 경로가 죽었다."""

    def setUp(self):
        self.RH = load('refresh_hist')
        self.RH.FAILURES.clear()
        self.real_urlopen = self.RH.urllib.request.urlopen

    def tearDown(self):
        self.RH.urllib.request.urlopen = self.real_urlopen

    def test_live_fx_duplicate_calendar_labels_removed_before_duplicate_check(self):
        start, end = ts('2026-09-03 23:00'), ts('2026-09-04 22:59')
        meta = {'regularMarketTime': ts('2026-09-04 12:00'), 'exchangeTimezoneName': 'Europe/London',
                'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
        # One complete historical bar plus two timestamps in the unfinished session.
        payload = yahoo_payload([ts('2026-09-02 23:00'), start, meta['regularMarketTime']],
                                [1380., 1381., 1382.], meta)
        self.RH.urllib.request.urlopen = lambda *a, **k: FakeResponse(payload)
        df = self.RH.chart('KRW=X', now=meta['regularMarketTime'])
        self.assertEqual(list(df.index), [pd.Timestamp('2026-09-03')])

    def test_closed_duplicate_dates_and_raw_duplicate_timestamps_rejected(self):
        start, end = ts('2026-09-03 23:00'), ts('2026-09-04 22:59')
        meta = {'regularMarketTime': end, 'exchangeTimezoneName': 'Europe/London',
                'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
        for stamps in ([start, start], [start, start+3600]):
            self.RH.urllib.request.urlopen = lambda *a, **k: FakeResponse(yahoo_payload(stamps,[1.,1.],meta))
            with self.assertRaises(RuntimeError):
                self.RH.chart('KRW=X', now=end+1)

    def test_invalid_timezone_does_not_silently_shift_fx_dates(self):
        with self.assertRaises(RuntimeError):
            self.RH._bar_index([ts('2026-09-03 23:00')], {'exchangeTimezoneName':'invalid/timezone'})

    def test_bar_dates_follow_exchange_timezone(self):
        RH = self.RH
        stamps = fx_session_stamps('2026-08-23 23:00', 5)          # 월~금 세션(08-24~08-28)
        start, end = ts('2026-08-27 23:00'), ts('2026-08-28 22:59')
        meta = {'regularMarketTime': ts('2026-08-28 12:00'), 'exchangeTimezoneName': 'Europe/London',
                'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
        RH.urllib.request.urlopen = lambda *a, **k: FakeResponse(
            yahoo_payload(stamps, [1380.0, 1381.0, 1382.0, 1383.0, 1384.0], meta))
        RH.time = types.SimpleNamespace(time=lambda: ts('2026-08-29 08:00'))   # 토요일 - 세션 종료
        df = RH.chart('KRW=X', years=1)
        self.assertEqual([d.isoformat() for d in df.index.date],
                         ['2026-08-24', '2026-08-25', '2026-08-26', '2026-08-27', '2026-08-28'])

    def test_fallback_appends_after_friday_fred_anchor(self):
        RH = self.RH
        with tempfile.TemporaryDirectory() as td:
            fx = os.path.join(td, 'fred.csv')
            RH._atomic_write_text(fx, 'observation_date,DEXKOUS\n'
                                      '2026-08-20,1393.35\n'
                                      '2026-08-21,1385.01\n')
            stamps = fx_session_stamps('2026-08-20 23:00', 11)     # 금 08-21 + 두 주(08-24~09-04)
            closes = [1385.0 + i for i in range(11)]
            start, end = ts('2026-09-03 23:00'), ts('2026-09-04 22:59')
            meta = {'regularMarketTime': end, 'exchangeTimezoneName': 'Europe/London',
                    'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}

            def urlopen(req, *a, **k):
                url = getattr(req, 'full_url', str(req))
                if 'fred.stlouisfed.org' in url:
                    raise OSError('FRED 타임아웃 모의')
                return FakeResponse(yahoo_payload(stamps, closes, meta))
            RH.urllib.request.urlopen = urlopen
            RH.time = types.SimpleNamespace(time=lambda: ts('2026-09-05 08:00'))
            n = RH.refresh_fx(fx, today='2026-09-05')
            self.assertEqual(RH.FAILURES, [], '금요일 FRED 꼬리 뒤에 야후 보강이 실패-폐쇄됐다')
            self.assertEqual(n, 10)
            written = pd.read_csv(fx)
            self.assertEqual(written.iloc[:, 0].tolist()[2:4], ['2026-08-24', '2026-08-25'])
            self.assertEqual(written.iloc[-1, 0], '2026-09-04')


class NavCollectNonCoreRows(unittest.TestCase):
    """R2-07 · 비핵심 감시 종목 한 줄의 거래량 결측이 핵심 4종 장부까지 통째로 막았다."""

    def setUp(self):
        self.NC = load('nav_collect')

    def test_universe_uses_only_valid_prices_and_keeps_minimum_sample_gate(self):
        valid = [dict(nowVal=100.,nav=100.) for _ in range(10)]
        bad = [None,{},dict(nav=100.),dict(nowVal=True,nav=1),dict(nowVal=100.,nav='bad')]
        self.assertEqual(self.NC.universe_stats(valid+bad),(10,0.,0.))
        self.assertEqual(self.NC.universe_stats(valid[:9]+bad),(0,0.,0.))

    def _run(self, break_code):
        NC = self.NC
        with tempfile.TemporaryDirectory() as td:
            NC.HOL = os.path.join(td, 'holidays.json')
            with open(NC.HOL, 'w', encoding='utf-8') as f:
                json.dump({'range': [2025, 2032], 'holidays': {}}, f)
            NC.OUT = os.path.join(td, 'nav.csv')

            def items():
                rows = []
                for k, code in enumerate(NC.WATCH):
                    row = {'itemcode': code, 'nowVal': 100 + k, 'nav': 100 + k,
                           'quant': 0, 'marketSum': 1}
                    if code == break_code:
                        row.pop('quant')              # 네이버 응답에 거래량 필드가 빠진 종목
                    rows.append(row)
                for extra in ('000000', '000001'):
                    rows.append({'itemcode': extra, 'nowVal': 100, 'nav': 100, 'quant': 0, 'marketSum': 1})
                return rows
            NC.fetch = items
            rows = NC.collect('2026-09-04')
            written = pd.read_csv(NC.OUT, dtype=str) if os.path.exists(NC.OUT) else None
            return rows, written

    def test_noncore_missing_volume_does_not_block_core_ledger(self):
        NC = self.NC
        bad = next(c for c in NC.WATCH if c not in NC.CORE_CODES)
        rows, written = self._run(bad)
        codes = {r['code'] for r in rows}
        self.assertTrue(set(NC.CORE_CODES) <= codes, '핵심 4종이 기록되지 않았다')
        self.assertNotIn(bad, codes)
        self.assertEqual(sorted(written['code']), sorted(codes))

    def test_core_missing_volume_still_fails_closed(self):
        NC = self.NC
        with self.assertRaises(RuntimeError):
            self._run(NC.CORE_CODES[0])

    def test_malformed_prices_are_isolated_before_universe_arithmetic(self):
        NC = self.NC
        for core in (False, True):
            for bad_key, bad_value in (('nowVal',None),('nowVal','bad'),('nav','bad'),
                                       ('nav',0),('nowVal',True),('nav',float('inf'))):
                with self.subTest(core=core,key=bad_key,value=bad_value), tempfile.TemporaryDirectory() as td:
                    code = NC.CORE_CODES[0] if core else next(c for c in NC.WATCH if c not in NC.CORE_CODES)
                    items = [dict(itemcode=c,nowVal=100.,nav=100.,quant=1,marketSum=1) for c in NC.WATCH]
                    items += [dict(itemcode=f'X{i}',nowVal=100.,nav=100.) for i in range(12)]
                    # A malformed unrelated market-comparison entry must not block core collection either.
                    items += [None, {'itemcode':'unrelated','nav':100.}]
                    next(r for r in items if isinstance(r,dict) and r['itemcode']==code)[bad_key] = bad_value
                    out = os.path.join(td,'nav.csv')
                    with patch.object(NC,'OUT',out), patch.object(NC,'fetch',return_value=items):
                        if core:
                            with self.assertRaises(RuntimeError):
                                NC.collect('2026-09-04')
                            self.assertFalse(os.path.exists(out))
                        else:
                            rows = NC.collect('2026-09-04')
                            self.assertTrue(set(NC.CORE_CODES) <= {r['code'] for r in rows})
                            self.assertNotIn(code,{r['code'] for r in rows})


class TnxFailureIsolation(unittest.TestCase):
    def test_tnx_failure_preserves_file_and_main_stays_failed_after_other_attempts(self):
        rh = load('refresh_hist')
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td,'tnx.csv')
            old = b'Date,Open,Close\n2026-09-03,4.0,4.1\n'
            with open(path,'wb') as f:
                f.write(old)
            with patch.object(rh,'chart',side_effect=OSError('offline fixture')):
                self.assertEqual(rh.splice_tnx(path),0)
            with open(path,'rb') as f:
                self.assertEqual(f.read(),old)
            self.assertEqual(rh.FAILURES,['tnx.csv'])
        # Same failure inside orchestration: no real sources, no real output writes.
        rh.FAILURES.clear()
        def fail_tnx(path):
            return rh._abort_update(path,['offline fixture'])
        with patch.object(rh,'splice_us',return_value=0), patch.object(rh,'splice_tnx',side_effect=fail_tnx), \
             patch.object(rh,'splice_gold',return_value=0) as gold, \
             patch.object(rh,'refresh_fx',return_value=0) as fx, patch.object(rh,'splice_kr',return_value=0) as kr:
            self.assertEqual(rh.main(),1)
            self.assertEqual((gold.call_count,fx.call_count,kr.call_count),(1,1,6))


def node_available():
    return shutil.which('node') is not None


def extract_js(src, start_pat, end_pat):
    i = src.index(start_pat)
    j = src.index(end_pat, i)
    return src[i:j]


class SignalHtmlDayCounts(unittest.TestCase):
    """R2-21/R2-20 · 화면의 날짜 셈이 UTC 자정(09:00 KST)·달력일 기준이라 파수꾼(08:40 KST)과
    어긋났다. signal.html 의 실제 함수 본문을 꺼내 node 로 가짜 시계에서 잰다."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, 'signal.html'), encoding='utf-8') as f:
            cls.src = f.read()

    def _run_js(self, body):
        if not node_available():
            self.skipTest('node 없음')
        src = self.src
        helpers = extract_js(src, "const NY='America/New_York'", 'function krIso(')
        # [v225] 서명이 (iso, now) 로 바뀌었다 — now 는 검사용 주입(기본 지금). 휴장 표(usHolidays)는 helpers 블록 안에 있다.
        biz = extract_js(src, 'function bizDaysSince(iso, now){', '\nfunction showStale(')
        days = re.search(r'function daysSince\(d\)\{.*?\n(?=/\*|function )', src, re.S).group(0)
        fake_clock = (
            'const RealDate = Date; let FIXED = 0;\n'
            'class FakeDate extends RealDate {\n'
            '  constructor(...a){ super(...(a.length ? a : [FIXED])); }\n'
            '  static now(){ return FIXED; }\n'
            '  static UTC(...a){ return RealDate.UTC(...a); }\n'
            '  static parse(s){ return RealDate.parse(s); }\n'
            '}\n'
            'globalThis.Date = FakeDate;\n')
        script = fake_clock + helpers + '\n' + biz + '\n' + days + '\n' + body
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 't.js')
            with open(p, 'w', encoding='utf-8') as f:
                f.write(script)
            out = subprocess.run(['node', p], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout.strip().splitlines()[-1])

    def test_days_since_uses_kst_calendar(self):
        r = self._run_js(
            'FIXED = Date.UTC(2026, 8, 14, 23, 40);'         # 2026-09-15(화) 08:40 KST (파수꾼 슬롯)
            'const a = daysSince("2026-08-16");'              # 진입 30일째 아침
            'FIXED = Date.UTC(2026, 8, 15, 0, 30);'           # 같은 날 09:30 KST
            'const b = daysSince("2026-08-16");'
            'console.log(JSON.stringify({a, b}));')
        self.assertEqual(r, {'a': 30, 'b': 30}, '재조정 확인일 아침 08:40 에 화면이 D-1 을 보인다')

    def test_biz_days_since_ignores_the_unfinished_us_session(self):
        # 2026-09-07(월)은 미국 노동절 휴장이라 그 다음 주로 잰다 - 휴장일은 파수꾼과 같이 세지 않는다.
        r = self._run_js(
            'FIXED = Date.UTC(2026, 8, 14, 16, 0);'           # 2026-09-15(화) 01:00 KST · 미국 월요일 장중
            'const live = bizDaysSince("2026-09-11");'        # 금요일 종가가 최신 -> 1
            'FIXED = Date.UTC(2026, 8, 14, 23, 40);'          # 08:40 KST · 마감 후 -> 파수꾼과 같은 2
            'const morning = bizDaysSince("2026-09-11");'
            'console.log(JSON.stringify({live, morning}));')
        self.assertEqual(r, {'live': 1, 'morning': 2})

    def test_biz_days_since_skips_us_holidays(self):
        # [v225] 노동절(2026-09-07) 주 — 종전(평일 셈)은 화요일 아침에 2(노란 점)·목요일에 4 였다.
        #   파수꾼 biz_days_since 와 같은 미국 거래일 셈: 화 1 · 수 2 · 목 3. 독립기념일 관측일(07-03 금)도 뺀다.
        r = self._run_js(
            'FIXED = Date.UTC(2026, 8, 7, 23, 40);'           # 09-08(화) 08:40 KST
            'const tue = bizDaysSince("2026-09-04");'
            'FIXED = Date.UTC(2026, 8, 8, 23, 40);'           # 09-09(수)
            'const wed = bizDaysSince("2026-09-04");'
            'FIXED = Date.UTC(2026, 8, 9, 23, 40);'           # 09-10(목)
            'const thu = bizDaysSince("2026-09-04");'
            'const j4 = bizDaysSince("2026-07-02", new Date(Date.UTC(2026, 6, 7, 1, 0)));'   # now 주입 · 07-07(화) 10:00 KST
            'console.log(JSON.stringify({tue, wed, thu, j4}));')
        self.assertEqual(r, {'tue': 1, 'wed': 2, 'thu': 3, 'j4': 2})


class ScreenContracts(unittest.TestCase):
    """화면이 생성 자료·재실행값과 같은 숫자를 말하는지 - 정적 대조."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, 'signal.html'), encoding='utf-8') as f:
            cls.signal = f.read()
        with open(os.path.join(ROOT, 'guide.html'), encoding='utf-8') as f:
            cls.guide = f.read()

    def test_calmar_null_is_guarded_like_build_stats_emits(self):
        # build_stats.pack 은 calmar 비유한이면 None 을 낸다 - 화면이 toFixed 를 그대로 부르면 redraw 전체가 죽는다.
        total = self.signal.count('m.calmar.toFixed(3)')
        guarded = len(re.findall(r"m\.calmar\s*==\s*null\s*\?\s*'[^']*'\s*:\s*m\.calmar\.toFixed\(3\)", self.signal))
        self.assertGreaterEqual(total, 3, '성과표·심사·CSV 의 Calmar 출력이 줄었다')
        self.assertEqual(guarded, total, f'calmar null 가드 없는 toFixed 가 {total - guarded}곳 있다')

    def test_switch_statistics_match_rerun_and_each_other(self):
        # research/ops_risk.py 2026-09-05 재실행(v210 자료): 전환 137회 · 손실 70(51%) · 놓쳐도 이득 103 · 10% 초과 손실 21
        g = re.search(r'전환 (\d+)번 중 <b class="key">(\d+)번\((\d+)%\)', self.guide)
        s = re.search(r'과거 (\d+)번의 전환 중 <b>(\d+)번\((\d+)%\)', self.signal)
        f = re.search(r"과거 전환 (\d+)번 중 <b>(\d+)번\((\d+)%\)", self.signal)
        self.assertTrue(g and s and f, '전환 통계 문장을 찾지 못했다')
        self.assertEqual(g.groups(), ('137', '70', '51'))
        self.assertEqual(s.groups(), g.groups())
        self.assertEqual(f.groups(), g.groups())
        self.assertTrue('103번은 놓쳐도' in self.guide, '놓친 전환 이득 횟수가 재실행값(103)이 아니다')
        self.assertFalse('139번' in (self.guide + self.signal), 'v210 이전 전환 횟수(139)가 화면에 남아 있다')

    def test_withdrawal_income_figure_is_the_reexecuted_one(self):
        # research/withdraw.py [5]·[6] 2026-09-05 재실행: 연 5% 비율 인출 최악 소득 -55.9%
        self.assertTrue('−55.9%' in self.guide, '인출 소득 최악값이 재실행값(−55.9%)이 아니다')
        self.assertFalse('−51.3%' in self.guide, '옛 인출 소득값(−51.3%)이 설명서에 남아 있다')


if __name__ == '__main__':
    unittest.main()
