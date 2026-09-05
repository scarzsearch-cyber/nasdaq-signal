"""운영 자동화 장애·재시도·복구 통합 검사 (2026-09-05 · 3차).

함수 하나가 아니라 **호출 순서 · 파일 상태 · 종료코드 · 다음 재실행**을 함께 본다.
네트워크 0 · 알림 0 · 토큰 회전 0 · 실측 장부 무접촉. 모든 입력은 가짜 시계·고정 응답·
임시 디렉터리·로컬 bare 원격이다. 각 시나리오의 불변조건은 클래스 docstring 에 적는다.

시나리오: S1 신호 생성 도중 실패 · S2 종가 확인 실패 · S3 알림 부분 실패 · S4 가격 불변 ·
S5 원자료 일부 갱신 실패 · S6 실행 경쟁(예약 중첩·원격 변경).

실행:  python -m unittest audit.test_ops_recovery3  (저장소 루트에서)
"""
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# 수정 전 상태 재현: OPS_RECOVERY3_OLD=<옛 deploy 디렉터리> (S1·S2·S4 가 실패해야 한다).
DEPLOY = os.environ.get('OPS_RECOVERY3_OLD') or os.path.join(ROOT, 'deploy')
if DEPLOY not in sys.path:
    sys.path.insert(0, DEPLOY)
KST = timezone(timedelta(hours=9))


def load(name):
    """deploy 모듈을 새 이름으로 적재한다(전역 상태를 검사마다 새로)."""
    path = os.path.join(DEPLOY, name + '.py')
    spec = importlib.util.spec_from_file_location('ops_recovery3_' + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ts(text):
    """'YYYY-MM-DD HH:MM' (UTC) → epoch 초."""
    return int(pd.Timestamp(text, tz='UTC').timestamp())


def synth_series(end, start='1999-01-04', seed=7):
    """QQQ 수정종가를 흉내 낸 결정론적 랜덤워크(영업일)."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(seed)
    px = 100.0 * np.cumprod(1 + rng.normal(0.0004, 0.012, len(idx)))
    return pd.Series(px, index=idx, name='Close')


def closed_meta(day):
    """미국 세션이 그날 마감된 뒤의 Yahoo meta (wait_close.fetch_meta 모양)."""
    start = int(pd.Timestamp(f'{day} 13:30', tz='UTC').timestamp())
    end = int(pd.Timestamp(f'{day} 20:00', tz='UTC').timestamp())
    return {'qt': end, 'start': start, 'end': end, 'price': 100.0, 'prev': 99.0}


class FakeClock:
    """time.time()/time.sleep() 대역 — sleep 이 시계를 밀고 실제로는 기다리지 않는다."""

    def __init__(self, t0=1_700_000_000.0):
        self.t = float(t0)
        self.slept = []

    def time(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += float(s)


class TempRepoDir:
    """임시 디렉터리로 chdir 하고 data/ 를 만든다."""

    def __enter__(self):
        self.old = os.getcwd()
        self.td = tempfile.mkdtemp(prefix='ops_recovery3_')
        os.chdir(self.td)
        os.makedirs('data', exist_ok=True)
        return self.td

    def __exit__(self, *exc):
        os.chdir(self.old)
        shutil.rmtree(self.td, ignore_errors=True)
        return False


class BrokenJson:
    """json.dump/dumps 만 실패하는 대역 — 디스크·직렬화 오류를 신호 JSON 쓰기 단계에 주입한다."""
    load = staticmethod(json.load)
    loads = staticmethod(json.loads)

    @staticmethod
    def dump(*a, **k):
        raise OSError('signal.json 쓰기 실패 모의')

    @staticmethod
    def dumps(*a, **k):
        raise OSError('signal.json 직렬화 실패 모의')


def run_update(US, series):
    """update_signal.main 을 고정 응답으로 돌린다(야후 1차 소스만 살아 있음)."""
    US.fetch = lambda host='query1': series
    US.fetch_naver = lambda: (_ for _ in ()).throw(RuntimeError('naver 미사용'))
    US.main()


def read_signal(path='data/signal.json'):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


class S1_SignalGenerationCrash(unittest.TestCase):
    """S1 · 신호 생성 도중 실패.

    불변조건: (i) 어떤 시점에 죽어도 data/signal.json 은 **마지막 성공 판정**으로 파싱된다.
    (ii) CSV 만 앞서 있으면 OOS 장부는 쓰지 않고(원천 대조 실패) 다음 갱신이 JSON 을 따라잡는다.
    (iii) wait_close 는 그 사이 「손상된 신호」로 즉시 종료하지 않고 다음 재시도로 회복한다."""

    D0, D1 = '2026-09-03', '2026-09-04'

    def _seed(self, US):
        run_update(US, synth_series(self.D0))
        self.assertEqual(read_signal()['as_of'], self.D0)

    def test_json_write_failure_keeps_last_good_signal_and_next_run_recovers(self):
        with TempRepoDir():
            US = load('update_signal')
            self._seed(US)
            before = open('data/signal.json', 'rb').read()
            US.json = BrokenJson
            with self.assertRaises(OSError):
                run_update(US, synth_series(self.D1))
            US.json = json
            # CSV 는 앞서 갔지만 JSON 은 마지막 성공 판정 그대로여야 한다.
            csv_last = pd.read_csv('data/qqq.csv')['Date'].iloc[-1]
            self.assertEqual(csv_last, self.D1)
            self.assertEqual(open('data/signal.json', 'rb').read(), before,
                             'signal.json 이 반쪽/빈 파일이 됐다 — 소비자가 판정을 잃는다')
            # 소비자 1: OOS 장부는 CSV(D1)·signal(D0) 불일치를 원천 대조로 거부한다.
            OL = load('oos_log')
            shutil.copy(os.path.join(ROOT, 'data', 'freeze.json'), 'data/freeze.json')
            self.assertNotEqual(OL.main(), 0)
            self.assertFalse(os.path.exists('data/oos_log.csv'))
            # 소비자 2: wait_close 는 손상이 아니라 「아직 옛 종가」로 읽는다.
            WC = load('wait_close')
            self.assertEqual(WC.current_as_of(), self.D0)
            self.assertIsNotNone(WC.validate_signal_as_of(self.D0))
            # 다음 갱신이 성공하면 JSON 이 CSV 를 따라잡고 장부도 한 줄 쓴다.
            run_update(US, synth_series(self.D1))
            self.assertEqual(read_signal()['as_of'], self.D1)
            self.assertEqual(OL.main(), 0)
            rows = pd.read_csv('data/oos_log.csv')
            self.assertEqual(rows['as_of'].tolist(), [self.D1])
            self.assertEqual(OL.main(), 0)          # 재실행은 append-only no-op
            self.assertEqual(len(pd.read_csv('data/oos_log.csv')), 1)

    def test_replace_failure_during_json_write_keeps_last_good_signal(self):
        with TempRepoDir():
            US = load('update_signal')
            self._seed(US)
            before = open('data/signal.json', 'rb').read()
            real_replace = US.os.replace

            def fail_replace(src, dst):
                if dst.endswith('signal.json'):
                    raise OSError('교체 실패 모의')
                return real_replace(src, dst)
            US.os.replace = fail_replace
            try:
                with self.assertRaises(OSError):
                    run_update(US, synth_series(self.D1))
            finally:
                US.os.replace = real_replace
            self.assertEqual(open('data/signal.json', 'rb').read(), before)
            leftovers = [n for n in os.listdir('data') if n.endswith('.tmp')]
            self.assertEqual(leftovers, [], '임시파일이 남아 허용 목록 밖 변경으로 커밋을 막는다')

    def test_wait_close_retries_after_mid_run_crash_instead_of_exiting(self):
        # 보존 검사: 수정 전에도 빈 as_of 는 「없음」으로 읽혀 재시도됐다(loop 의 as_of_is_current('')=False).
        # 수정 뒤에는 첫 시도가 JSON 을 비우지 않으므로 그 사이 소비자도 옛 판정을 유지한다.
        with TempRepoDir():
            US = load('update_signal')
            self._seed(US)
            WC = load('wait_close')
            clock = FakeClock()
            WC.time = types.SimpleNamespace(time=clock.time, sleep=clock.sleep)
            WC.fetch_meta = lambda: closed_meta(self.D1)
            WC.wait_for_close = lambda meta: (meta, '마감 확인(대역)')
            calls = []

            def fake_call(args):
                calls.append(args)
                if len(calls) == 1:                 # 첫 시도: JSON 쓰기 단계에서 죽는다
                    US.json = BrokenJson
                    try:
                        run_update(US, synth_series(self.D1))
                    except OSError:
                        return 1
                    finally:
                        US.json = json
                    return 1
                run_update(US, synth_series(self.D1))
                return 0
            WC.subprocess = types.SimpleNamespace(call=fake_call)
            self.assertIsNone(WC.main(), '재시도 대신 종료했다')
            self.assertEqual(len(calls), 2)
            self.assertEqual(read_signal()['as_of'], self.D1)


class S2_CloseConfirmationFailure(unittest.TestCase):
    """S2 · 종가 확인(예상일 조회) 실패.

    불변조건: (i) 갱신이 원천 meta 로 마감을 확정(source yahoo/yahoo2/naver)했으면 예상일 조회가
    죽어도 성공이다 — 170분 헛돌고 거짓 실패 알림을 내지 않는다. (ii) 갱신이 실패했거나
    캐시로 물러선(확정 없음) 신호는 예상일 없이 정상으로 인정하지 않는다."""

    D0, D1 = '2026-09-03', '2026-09-04'

    def _setup(self, WC):
        clock = FakeClock()
        WC.time = types.SimpleNamespace(time=clock.time, sleep=clock.sleep)
        WC.fetch_meta = lambda: (_ for _ in ()).throw(OSError('meta 조회 실패 모의'))
        with open('data/signal.json', 'w', encoding='utf-8') as f:
            json.dump({'as_of': self.D0, 'source': 'yahoo'}, f)
        return clock

    def _writer(self, as_of, source, rc=0):
        calls = []

        def call(args):
            calls.append(args)
            with open('data/signal.json', 'w', encoding='utf-8') as f:
                json.dump({'as_of': as_of, 'source': source}, f)
            return rc
        return call, calls

    def test_certified_update_ends_run_without_expected_date(self):
        with TempRepoDir():
            WC = load('wait_close')
            clock = self._setup(WC)
            call, calls = self._writer(self.D1, 'yahoo')
            WC.subprocess = types.SimpleNamespace(call=call)
            self.assertIsNone(WC.main(), '갱신이 확정됐는데 예상일 조회 실패로 실패 종료했다')
            self.assertEqual(len(calls), 1)
            self.assertLess(clock.t - 1_700_000_000.0, WC.MAX_MIN * 60)

    def test_already_current_signal_is_not_reported_as_failure(self):
        with TempRepoDir():
            WC = load('wait_close')
            self._setup(WC)
            call, calls = self._writer(self.D0, 'yahoo')      # 재조회 결과가 같은 종가일
            WC.subprocess = types.SimpleNamespace(call=call)
            self.assertIsNone(WC.main())
            self.assertEqual(len(calls), 1)

    def test_failed_update_without_expected_date_still_fails_closed(self):
        with TempRepoDir():
            WC = load('wait_close')
            clock = self._setup(WC)
            call, calls = self._writer(self.D0, 'yahoo', rc=1)
            WC.subprocess = types.SimpleNamespace(call=call)
            with self.assertRaises(SystemExit) as cm:
                WC.main()
            self.assertEqual(cm.exception.code, 1)
            self.assertGreater(len(calls), 1)

    def test_cache_fallback_is_not_certified(self):
        with TempRepoDir():
            WC = load('wait_close')
            self._setup(WC)
            call, calls = self._writer(self.D0, 'cache')
            WC.subprocess = types.SimpleNamespace(call=call)
            with self.assertRaises(SystemExit) as cm:
                WC.main()
            self.assertEqual(cm.exception.code, 1)

    def test_stale_signal_with_known_expected_date_is_rejected(self):
        with TempRepoDir():
            WC = load('wait_close')
            clock = FakeClock()
            WC.time = types.SimpleNamespace(time=clock.time, sleep=clock.sleep)
            WC.fetch_meta = lambda: closed_meta(self.D1)
            WC.wait_for_close = lambda meta: (meta, '마감 확인(대역)')
            with open('data/signal.json', 'w', encoding='utf-8') as f:
                json.dump({'as_of': self.D0, 'source': 'yahoo'}, f)
            WC.subprocess = types.SimpleNamespace(call=lambda args: 1)   # 갱신이 안 됨
            with self.assertRaises(SystemExit) as cm:
                WC.main()
            self.assertEqual(cm.exception.code, 1)


def yahoo_chart_payload(series, closed_day):
    """update_signal.fetch() 가 읽는 실제 Yahoo chart JSON 모양 — 마지막 봉·meta 가 closed_day 마감."""
    stamps = [int(pd.Timestamp(d).tz_localize('UTC').timestamp()) + 13 * 3600 + 1800 for d in series.index]
    start, end = ts(f'{closed_day} 13:30'), ts(f'{closed_day} 20:00')
    meta = {'regularMarketTime': end,
            'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
    return {'chart': {'result': [{'timestamp': stamps,
                                  'indicators': {'adjclose': [{'adjclose': [float(v) for v in series.values]}]},
                                  'meta': meta}]}}


class FakeHttp:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.body


class S2b_FreshnessAgainstCalendar(unittest.TestCase):
    """S2 보완(통합 담당 지적) · 원천이 통째로 뒤처진 경우.

    불변조건: source·비미래 날짜만으로는 최신성을 증명하지 못한다. NYSE 달력(주말·휴장·장 시작 전)으로
    「마지막으로 마감된 세션」을 독립 계산해, 원천(chart meta·별도 meta)이 그보다 뒤처지면 성공으로
    인정하지 않는다 — 갱신을 재시도하고 시한이 지나면 「최신성 확인 불가」로 실패한다.
    생산자 파서(`update_signal.fetch → _parse_yahoo_result`)부터 대기 루프(`wait_close.main`)까지 연결한다."""

    def _run_chain(self, series, closed_day, now_utc, meta_mode, initial_as_of=None):
        """meta_mode: 'fail' = 예상일 조회 실패 · 'stale' = 원천 meta 도 closed_day · 'live'(qt 장중)."""
        US = load('update_signal')
        WC = load('wait_close')
        clock = FakeClock(t0=ts(now_utc))
        WC.time = types.SimpleNamespace(time=clock.time, sleep=clock.sleep)
        if meta_mode == 'fail':
            WC.fetch_meta = lambda: (_ for _ in ()).throw(OSError('meta 조회 실패 모의'))
        elif meta_mode == 'stale':
            WC.fetch_meta = lambda: closed_meta(closed_day)
        else:
            day = pd.Timestamp(now_utc).strftime('%Y-%m-%d')
            live = closed_meta(day)
            live['qt'] = live['start'] + 3600          # 장중
            WC.fetch_meta = lambda: live
        WC.wait_for_close = lambda meta: (meta, '대역')
        if initial_as_of:
            with open('data/signal.json', 'w', encoding='utf-8') as f:
                json.dump({'as_of': initial_as_of, 'source': 'yahoo'}, f)
        payload = yahoo_chart_payload(series, closed_day)
        US.urllib.request.urlopen = lambda *a, **k: FakeHttp(payload)      # 실제 fetch → _parse_yahoo_result
        US.fetch_naver = lambda: (_ for _ in ()).throw(RuntimeError('naver 미사용'))
        calls = []

        def call(args):
            calls.append(1)
            if len(calls) == 1:
                US.main()
            return 0
        WC.subprocess = types.SimpleNamespace(call=call)
        return WC, calls

    def test_source_two_sessions_behind_is_not_certified_without_expected_date(self):
        # 통합 담당 반례: 지금 2026-09-05(토) · Yahoo 일봉·meta 모두 09-02 마감 → 09-03·09-04 종가가 빠졌다.
        with TempRepoDir():
            WC, calls = self._run_chain(synth_series('2026-09-02'), '2026-09-02',
                                        '2026-09-05 08:00', 'fail')
            with self.assertRaises(SystemExit) as cm:
                WC.main()
            self.assertEqual(cm.exception.code, 1, '뒤처진 원천을 최신으로 인정했다')
            self.assertEqual(read_signal()['as_of'], '2026-09-02')    # 갱신은 됐지만 성공은 아니다

    def test_fresh_source_is_certified_on_weekend(self):
        with TempRepoDir():
            WC, calls = self._run_chain(synth_series('2026-09-04'), '2026-09-04',
                                        '2026-09-05 08:00', 'fail')
            self.assertIsNone(WC.main())
            self.assertEqual(len(calls), 1)
            self.assertEqual(read_signal()['as_of'], '2026-09-04')

    def test_holiday_monday_does_not_look_stale(self):
        # 2026-09-07 노동절 휴장 · 화요일 장 시작 전(07:00Z) → 마지막 마감 세션은 금요일 09-04.
        with TempRepoDir():
            WC, calls = self._run_chain(synth_series('2026-09-04'), '2026-09-04',
                                        '2026-09-08 07:00', 'fail')
            self.assertIsNone(WC.main())
            self.assertEqual(read_signal()['as_of'], '2026-09-04')

    def test_stale_expected_date_from_source_is_loud_not_silent_success(self):
        # 별도 meta 도 09-02 를 「예상」이라고 말하는 날(원천 전체 지연) — 종전엔 「이미 최신」으로 조용히 성공.
        with TempRepoDir():
            WC, calls = self._run_chain(synth_series('2026-09-02'), '2026-09-02',
                                        '2026-09-05 08:00', 'stale', initial_as_of='2026-09-02')
            with self.assertRaises(SystemExit) as cm:
                WC.main()
            self.assertEqual(cm.exception.code, 1)
            self.assertGreaterEqual(len(calls), 1, '원천 지연 의심인데 갱신을 시도하지 않았다')

    def test_in_session_with_missing_previous_close_attempts_update(self):
        # 화요일 장중(15:00Z · 월요일 휴장)인데 signal 이 09-02 — 직전 마감(09-04)이 빠져 있다.
        with TempRepoDir():
            WC, calls = self._run_chain(synth_series('2026-09-04'), '2026-09-04',
                                        '2026-09-08 15:00', 'live', initial_as_of='2026-09-02')
            self.assertIsNone(WC.main())
            self.assertEqual(len(calls), 1, '장중이라는 이유로 빠진 직전 종가를 갱신하지 않았다')
            self.assertEqual(read_signal()['as_of'], '2026-09-04')

    def test_in_session_with_current_previous_close_exits_without_update(self):
        with TempRepoDir():
            WC, calls = self._run_chain(synth_series('2026-09-04'), '2026-09-04',
                                        '2026-09-08 15:00', 'live', initial_as_of='2026-09-04')
            self.assertIsNone(WC.main())
            self.assertEqual(calls, [])

    def test_nyse_calendar_and_latest_closed_session(self):
        WC = load('wait_close')
        from datetime import date
        h = WC.nyse_holidays(2026)
        for d in ('2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25', '2026-06-19',
                  '2026-07-03', '2026-09-07', '2026-11-26', '2026-12-25'):
            self.assertIn(date.fromisoformat(d), h, d)
        self.assertNotIn(date(2026, 7, 4), h)          # 토요일 → 금요일 관측
        self.assertIn(date(2027, 1, 1), WC.nyse_holidays(2027))
        self.assertNotIn(date(2022, 1, 1), WC.nyse_holidays(2022))   # 토요일 신정은 미관측(NYSE 규칙)
        L = lambda s: WC.latest_closed_session(ts(s)).isoformat()   # noqa: E731
        self.assertEqual(L('2026-09-05 08:00'), '2026-09-04')       # 토
        self.assertEqual(L('2026-09-04 19:59'), '2026-09-03')       # 마감 1분 전(EDT 20:00Z)
        self.assertEqual(L('2026-09-04 20:00'), '2026-09-04')       # 마감
        self.assertEqual(L('2026-09-07 22:00'), '2026-09-04')       # 노동절
        self.assertEqual(L('2026-09-08 13:00'), '2026-09-04')       # 화 장 시작 전
        self.assertEqual(L('2026-12-02 20:30'), '2026-12-01')       # 겨울(EST 21:00Z 마감) 전
        self.assertEqual(L('2026-12-02 21:00'), '2026-12-02')
        self.assertEqual(L('2026-11-27 18:30'), '2026-11-25')       # 추수감사절 다음날 13:00 ET 조기마감은 보수적으로 16:00 까지 미마감


class S3_NotificationPartialFailure(unittest.TestCase):
    """S3 · 알림 부분 실패.

    설계 선택(누락보다 중복)이 실제 동작과 일치하는지 본다: 조각 일부 실패 → 전체 실패(rc 2) →
    성공 표시 없음 → 다음 슬롯이 **모든 조각**을 다시 보낸다(앞 조각 중복 1회). 성공 뒤에는 생략."""

    def _notify_env(self, NT):
        names = ('KAKAO_REST_API_KEY', 'KAKAO_REFRESH_TOKEN', 'KAKAO_CLIENT_SECRET', 'GH_PAT',
                 'GITHUB_REPOSITORY', 'GITHUB_ENV', 'DISCORD_WEBHOOK_URL',
                 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'GITHUB_RUN_ID', 'GITHUB_JOB')
        saved = {k: os.environ.get(k) for k in names}
        for k in names:
            os.environ.pop(k, None)
        os.environ.update(KAKAO_REST_API_KEY='key', KAKAO_REFRESH_TOKEN='refresh')

        class Tok:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"access_token":"access"}'
        NT.urllib.request.urlopen = lambda *a, **k: Tok()
        return saved

    def _restore(self, saved):
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_partial_chunk_failure_retries_all_chunks_next_slot(self):
        NT = load('notify')
        saved = self._notify_env(NT)
        sent = []
        try:
            def sender(fail_at):
                def send(token, template):
                    sent.append(template['text'][:5])
                    if len(sent) == fail_at:
                        raise RuntimeError('두 번째 조각 전송 실패 모의')
                return send
            long_detail = '\n'.join('줄 %02d ' % i + '가' * 40 for i in range(8))
            sys.argv = ['notify.py', '전환 신호 발생', 'signal', long_detail]
            n_chunks = len(NT.kakao_chunks('🔔 [전환 신호 발생] signal\njob:  · x\n' + long_detail + '\n'))
            self.assertGreaterEqual(n_chunks, 2)
            NT.kakao_send = sender(fail_at=2)
            self.assertEqual(NT.main(), 2, '조각 하나가 실패했는데 성공으로 보고했다')
            self.assertEqual(len(sent), 2)                    # 1 도착 · 2 실패 · 나머지 미전송
            NT.kakao_send = sender(fail_at=0)
            self.assertEqual(NT.main(), 0)
            self.assertEqual(len(sent), 2 + n_chunks, '재시도는 모든 조각을 다시 보낸다(앞 조각 중복 1회 = 설계)')
            self.assertEqual(sent[0], sent[2])
        finally:
            self._restore(saved)

    def test_signal_alert_state_only_after_full_success_and_state_write_failure_retries(self):
        with TempRepoDir():
            SA = load('signal_alert')
            sig = {'as_of': '2026-09-04', 'close': 600, 'dd': -16.2,
                   'strategies': {'B': {'state': 'SCHD', 'changed_today': True,
                                        'enter': -16, 'exit': -16}}}
            json.dump(sig, open('data/signal.json', 'w', encoding='utf-8'))
            json.dump({'rule': {'enter': -0.16, 'exit': -0.16}},
                      open('data/freeze.json', 'w', encoding='utf-8'))
            rcs = iter([2, 0, 0, 0])
            calls = []

            def sender(args):
                calls.append(args)
                return next(rcs)
            self.assertEqual(SA.main(sender), 2)            # 부분 실패(rc 2) → 표시 없음
            self.assertFalse(os.path.exists(SA.STATE))
            real_replace = SA.os.replace
            SA.os.replace = lambda s, d: (_ for _ in ()).throw(OSError('상태 저장 실패 모의'))
            try:
                self.assertEqual(SA.main(sender), 2)        # 전송은 됐지만 표시 저장 실패
            finally:
                SA.os.replace = real_replace
            self.assertFalse(os.path.exists(SA.STATE))
            self.assertEqual(len(calls), 2)
            self.assertEqual(SA.main(sender), 0)            # 다음 슬롯: 다시 보내고 표시 저장
            self.assertEqual(len(calls), 3)
            self.assertTrue(SA.already_alerted('2026-09-04'))
            self.assertEqual(SA.main(sender), 0)            # 이후 슬롯: 생략
            self.assertEqual(len(calls), 3)


class S4_PriceQuietPeriod(unittest.TestCase):
    """S4 · 가격 불변.

    불변조건: 값이 그대로여도 폴러가 살아 있으면 발행 시각(as_of)이 REPUBLISH_S 안에서 전진한다 —
    화면의 「N분 전」이 마지막 **확인** 시각(최대 30분 양자화)이 되어, 조용한 장과 멈춘 폴러가 갈린다.
    값이 바뀌면 즉시 발행한다."""

    def _doc(self, now, items):
        return {'as_of_kst': now.strftime('%Y-%m-%d %H:%M'),
                'as_of_iso': now.isoformat(timespec='seconds'), 'source': 'x', 'items': items}

    def test_unchanged_prices_republish_after_quiet_interval(self):
        PP = load('price_poll')
        items = {'418660': {'px': 38585, 'chg_pct': 0.1}}
        t0 = datetime(2026, 9, 4, 10, 0, tzinfo=KST)
        published = []
        PP.publish = lambda dry: published.append(1) or True
        PP.wake_pages = lambda dry: True
        state = {'items': items, 'published': t0}
        PP.snapshot = lambda: self._doc(t0 + timedelta(minutes=5), items)
        state, ok = PP.cycle(state, False, now=t0 + timedelta(minutes=5))
        self.assertTrue(ok)
        self.assertEqual(published, [], '값이 같고 조용한 간격 안이면 발행하지 않는다')
        PP.snapshot = lambda: self._doc(t0 + timedelta(minutes=31), items)
        state, ok = PP.cycle(state, False, now=t0 + timedelta(minutes=31))
        self.assertTrue(ok)
        self.assertEqual(published, [1], '값이 같아도 조용한 간격이 지나면 다시 발행해 살아 있음을 드러낸다')
        self.assertEqual(state['published'], t0 + timedelta(minutes=31))
        changed = {'418660': {'px': 38600, 'chg_pct': 0.2}}
        PP.snapshot = lambda: self._doc(t0 + timedelta(minutes=36), changed)
        state, ok = PP.cycle(state, False, now=t0 + timedelta(minutes=36))
        self.assertEqual(published, [1, 1], '값이 바뀌면 즉시 발행한다')
        self.assertEqual(state['items'], changed)

    def test_branch_state_without_timestamp_publishes_first_cycle(self):
        PP = load('price_poll')
        items = {'418660': {'px': 1}}
        published = []
        PP.publish = lambda dry: published.append(1) or True
        PP.wake_pages = lambda dry: True
        now = datetime(2026, 9, 4, 10, 0, tzinfo=KST)
        PP.snapshot = lambda: self._doc(now, items)
        state, ok = PP.cycle({'items': items, 'published': None}, False, now=now)
        self.assertEqual(published, [1])
        state, ok = PP.cycle(None, False, now=now)
        self.assertEqual(published, [1, 1])


class S5_MonthlyPartialRefresh(unittest.TestCase):
    """S5 · 원자료 일부 갱신 실패.

    불변조건: 한 파일이라도 실패하면 main 은 1 을 돌려주고(성공한 파일은 자기 파일 안에서만 갱신)
    실패 파일은 바이트 그대로다. 워크플로는 그 종료코드로 build_stats·커밋을 막는다 —
    성공·실패가 섞인 원자료로 새 성과표가 발행되지 않는다."""

    def _write(self, path, text):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def test_mixed_success_returns_failure_and_preserves_failed_file(self):
        today = pd.Timestamp.now('UTC').normalize().tz_localize(None)
        anchor = (today - pd.Timedelta(days=6)).strftime('%Y-%m-%d')
        prev = (today - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
        new = (today - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        with TempRepoDir():
            os.makedirs('data/hist')
            for name in ('qqq_us_d.csv', 'qld_us_d.csv', 'schd_us_d.csv'):
                self._write(name, 'Date,Open,High,Low,Close,Volume\n'
                                  f'{prev},100,101,99,100,1000\n{anchor},101,102,100,101,1000\n')
            self._write('data/hist/yahoo_TNX.csv', f'Date,Open,Close\n{prev},4.1,4.2\n{anchor},4.2,4.3\n')
            self._write('data/hist/lbma_gold_pm.csv', f'Date,Close\n{prev},3000\n{anchor},3010\n')
            self._write('data/hist/fred_DEXKOUS.csv',
                        f'observation_date,DEXKOUS\n{prev},1380.0\n{anchor},1381.0\n')
            for name in ('kr__5EKS11.csv', 'kr_133690_KS.csv', 'kr_418660_KS.csv', 'kr_458730_KS.csv'):
                self._write(f'data/hist/{name}', f'Date,Open,Close,AdjClose\n{prev},100,100,100\n{anchor},101,101,101\n')
            for name in ('kr_305080_KS.csv', 'kr_411060_KS.csv'):
                self._write(f'data/hist/{name}', f'Date,Open,Close,Volume,Raw\n{prev},100,100,10,100\n{anchor},101,101,10,101\n')
            RH = load('refresh_hist')
            RH.FAILURES.clear()
            tnx_before = open('data/hist/yahoo_TNX.csv', 'rb').read()

            def fake_chart(symbol, years=3, require_adj=False, now=None):
                if symbol == '^TNX':
                    raise OSError('Yahoo ^TNX 조회 실패 모의')
                idx = pd.to_datetime([anchor, new])
                v = [101.0, 102.0] if symbol != 'KRW=X' else [1381.0, 1382.0]
                return pd.DataFrame({'open': v, 'high': v, 'low': v, 'close': v, 'adj': v,
                                     'volume': [1000, 1000]}, index=idx)
            RH.chart = fake_chart
            RH.urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(OSError('FRED 타임아웃 모의'))
            rc = RH.main()
            self.assertEqual(rc, 1, '한 파일이 실패했는데 성공으로 끝났다')
            self.assertEqual(RH.FAILURES, ['yahoo_TNX.csv'])
            self.assertEqual(open('data/hist/yahoo_TNX.csv', 'rb').read(), tnx_before)
            for name in ('qqq_us_d.csv', 'data/hist/lbma_gold_pm.csv', 'data/hist/fred_DEXKOUS.csv',
                         'data/hist/kr_418660_KS.csv', 'data/hist/kr_305080_KS.csv'):
                self.assertEqual(pd.read_csv(name).iloc[-1, 0], new, name)

    def test_monthly_workflow_gates_build_and_commit_on_refresh_exit_code(self):
        with open(os.path.join(ROOT, '.github', 'workflows', 'monthly-stats.yml'), encoding='utf-8') as f:
            y = f.read()
        steps = re.split(r'\n\s*- name: ', y)
        by = {s.split('\n', 1)[0].strip(): s for s in steps[1:]}
        for name in ('원자료 연장', '성과 스냅샷 재계산', '불변식 검증', '변경분 커밋'):
            self.assertIn(name, by)
            self.assertNotIn('continue-on-error', by[name], name)
            self.assertNotRegex(by[name], r'\n\s*if:\s*always\(\)', name)
        order = [s.split('\n', 1)[0].strip() for s in steps[1:]]
        self.assertLess(order.index('원자료 연장'), order.index('성과 스냅샷 재계산'))
        self.assertLess(order.index('불변식 검증'), order.index('변경분 커밋'))


def git(*args, cwd, check=True):
    # [2026-09-06] 러너에서 로컬 bare 클론이 한 번 exit 128 로 죽었는데(재실행은 통과) 예외에 stderr 가 없어 원인을 못 봤다
    #   — 실패하면 git 의 stderr 를 메시지에 붙인다. 재시도로 가리지 않는다(간헐 실패는 보여야 한다).
    r = subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args], cwd=cwd,
                       check=False, capture_output=True, encoding='utf-8', errors='replace')
    if check and r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, r.args, output=r.stdout,
                                            stderr='%s\n[git stderr] %s' % (r.stderr, (r.stderr or '').strip()[-400:]))
    return r


def bash_exe():
    for cand in (r'C:\Program Files\Git\bin\bash.exe', r'C:\Program Files\Git\usr\bin\bash.exe'):
        if os.path.exists(cand):
            return cand
    return shutil.which('bash')


class S6_PushRaceGate(unittest.TestCase):
    """S6 · 실행 경쟁 — daily-signal.yml 「변경분 커밋」 스텝의 실제 셸을 로컬 bare 원격에서 돌린다.

    불변조건: (i) 원격이 같거나 더 새 종가를 이미 반영했으면 이 실행의 커밋은 버리고 정상 종료(0) —
    오래된 결과가 최신을 덮지 않는다. (ii) 원격이 다른 이유로 움직였으면 실패(1) — rebase 로 옛 코드의
    산출물을 새 코드 위에 얹지 않는다. (iii) 원격이 그대로면 push 된다."""

    @classmethod
    def setUpClass(cls):
        cls.bash = bash_exe()
        with open(os.path.join(ROOT, '.github', 'workflows', 'daily-signal.yml'), encoding='utf-8') as f:
            y = f.read().replace('\r\n', '\n')
        m = re.search(r'- name: 변경분 커밋\n\s*run: \|\n(.*?)\n\s*- name: ', y, re.S)
        assert m, '변경분 커밋 스텝을 찾지 못했다'
        body = m.group(1)
        indent = min(len(l) - len(l.lstrip()) for l in body.split('\n') if l.strip())
        cls.snippet = '\n'.join(l[indent:] for l in body.split('\n'))

    def _seed(self, td):
        bare = os.path.join(td, 'origin.git')
        git('init', '-q', '--bare', '-b', 'main', bare, cwd=td)
        seed = os.path.join(td, 'seed')
        git('clone', '-q', bare, seed, cwd=td)
        os.makedirs(os.path.join(seed, 'data'))
        files = {'data/qqq.csv': 'Date,Close\n2026-09-03,100\n',
                 'data/signal.json': json.dumps({'as_of': '2026-09-03'}),
                 'data/signal_alert_state.json': '{}',
                 'data/nav_history.csv': 'as_of,code\n',
                 'data/oos_log.csv': 'as_of,changed\n',
                 'README.md': 'seed\n'}
        for p, t in files.items():
            with open(os.path.join(seed, p), 'w', encoding='utf-8') as f:
                f.write(t)
        git('add', '-A', cwd=seed)
        git('commit', '-q', '-m', 'seed', cwd=seed)
        git('push', '-q', 'origin', 'HEAD:main', cwd=seed)
        return bare

    def _clone(self, td, bare, name):
        path = os.path.join(td, name)
        git('clone', '-q', bare, path, cwd=td)
        return path

    def _set_asof(self, repo, as_of, extra=None):
        with open(os.path.join(repo, 'data', 'signal.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps({'as_of': as_of}))
        if extra:
            with open(os.path.join(repo, extra[0]), 'w', encoding='utf-8') as f:
                f.write(extra[1])

    def _run_snippet(self, repo):
        shim = os.path.join(repo, '.shim')
        os.makedirs(shim)
        with open(os.path.join(shim, 'python3'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('#!/bin/sh\nexec "%s" "$@"\n' % sys.executable.replace('\\', '/'))
        os.chmod(os.path.join(shim, 'python3'), 0o755)
        script = os.path.join(repo, '.shim', 'commit_step.sh')
        with open(script, 'w', encoding='utf-8', newline='\n') as f:
            f.write(self.snippet)
        with open(os.path.join(repo, '.git', 'info', 'exclude'), 'a', encoding='utf-8') as f:
            f.write('.shim/\n')
        env = dict(os.environ, PATH=shim + os.pathsep + os.environ.get('PATH', ''),
                   GIT_TERMINAL_PROMPT='0')
        r = subprocess.run([self.bash, '-e', script], cwd=repo, env=env, capture_output=True,
                           encoding='utf-8', errors='replace', timeout=120)
        return r.returncode, (r.stdout or '') + (r.stderr or '')

    def _remote_asof(self, bare):
        return json.loads(git('show', 'main:data/signal.json', cwd=bare).stdout)['as_of']

    def setUp(self):
        if not self.bash:
            self.skipTest('bash 없음')

    def test_unchanged_remote_pushes(self):
        with tempfile.TemporaryDirectory(prefix='race_') as td:
            bare = self._seed(td)
            c = self._clone(td, bare, 'run_c')
            self._set_asof(c, '2026-09-04')
            rc, out = self._run_snippet(c)
            self.assertEqual(rc, 0, out)
            self.assertEqual(self._remote_asof(bare), '2026-09-04')

    def test_remote_already_has_same_close_discards_duplicate_as_success(self):
        with tempfile.TemporaryDirectory(prefix='race_') as td:
            bare = self._seed(td)
            a = self._clone(td, bare, 'run_a')
            c = self._clone(td, bare, 'run_c')          # 같은 base 에서 시작한 둘째 실행
            self._set_asof(a, '2026-09-04')
            git('add', '-A', cwd=a); git('commit', '-q', '-m', 'A', cwd=a); git('push', '-q', cwd=a)
            a_head = git('rev-parse', 'HEAD', cwd=a).stdout.strip()
            self._set_asof(c, '2026-09-04')
            rc, out = self._run_snippet(c)
            self.assertEqual(rc, 0, out)
            self.assertIn('중복 커밋은 버린다', out)
            self.assertEqual(git('rev-parse', 'main', cwd=bare).stdout.strip(), a_head,
                             '둘째 실행의 커밋이 원격을 덮었다')
            # 다음 슬롯의 첫 스텝(reset --hard origin/main)이 이 작업트리를 원격과 같게 만든다.
            git('fetch', '-q', 'origin', 'main', cwd=c); git('reset', '-q', '--hard', 'origin/main', cwd=c)
            self.assertEqual(json.load(open(os.path.join(c, 'data', 'signal.json')))['as_of'], '2026-09-04')

    def test_remote_newer_close_wins_over_stale_result(self):
        with tempfile.TemporaryDirectory(prefix='race_') as td:
            bare = self._seed(td)
            a = self._clone(td, bare, 'run_a')
            c = self._clone(td, bare, 'run_c')
            self._set_asof(a, '2026-09-08')
            git('add', '-A', cwd=a); git('commit', '-q', '-m', 'A', cwd=a); git('push', '-q', cwd=a)
            self._set_asof(c, '2026-09-04')             # 오래된 결과를 든 실행
            rc, out = self._run_snippet(c)
            self.assertEqual(rc, 0, out)
            self.assertEqual(self._remote_asof(bare), '2026-09-08', '오래된 결과가 최신을 덮었다')

    def test_remote_moved_for_other_reason_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix='race_') as td:
            bare = self._seed(td)
            a = self._clone(td, bare, 'run_a')
            c = self._clone(td, bare, 'run_c')
            with open(os.path.join(a, 'README.md'), 'w', encoding='utf-8') as f:
                f.write('code change\n')
            git('add', '-A', cwd=a); git('commit', '-q', '-m', 'code', cwd=a); git('push', '-q', cwd=a)
            self._set_asof(c, '2026-09-04')
            rc, out = self._run_snippet(c)
            self.assertEqual(rc, 1, out)
            self.assertEqual(self._remote_asof(bare), '2026-09-03', '옛 체크아웃의 산출물이 새 코드 위에 밀렸다')

    def test_disallowed_file_change_blocks_commit(self):
        with tempfile.TemporaryDirectory(prefix='race_') as td:
            bare = self._seed(td)
            c = self._clone(td, bare, 'run_c')
            self._set_asof(c, '2026-09-04', extra=('data/strategy_stats.json', '{}'))
            rc, out = self._run_snippet(c)
            self.assertEqual(rc, 1, out)
            self.assertEqual(self._remote_asof(bare), '2026-09-03')


class S6_SchedulingContracts(unittest.TestCase):
    """예약 중첩을 막는 워크플로 계약 — 텍스트 검사(값이 바뀌면 위 시나리오의 전제가 깨진다)."""

    def test_daily_signal_serializes_and_resets_before_computing(self):
        with open(os.path.join(ROOT, '.github', 'workflows', 'daily-signal.yml'), encoding='utf-8') as f:
            y = f.read()
        self.assertRegex(y, r'concurrency:\s*\n\s*group: daily-signal\s*\n\s*cancel-in-progress: false')
        self.assertLess(y.index('git reset --hard origin/main'), y.index('deploy/wait_close.py'))
        self.assertLess(y.index('deploy/signal_alert.py'), y.index('deploy/nav_collect.py'))
        self.assertLess(y.index('deploy/nav_collect.py'), y.index('deploy/oos_log.py'))

    def test_price_and_monthly_do_not_cancel_in_progress(self):
        for name in ('price.yml', 'monthly-stats.yml'):
            with open(os.path.join(ROOT, '.github', 'workflows', name), encoding='utf-8') as f:
                self.assertIn('cancel-in-progress: false', f.read(), name)


if __name__ == '__main__':
    unittest.main()
