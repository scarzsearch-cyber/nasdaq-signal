#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[v25] 국내 ETF 실측 NAV 수집기 — 진짜 괴리율을 쌓는다

v21 부터 미결이던 과제다. v24 는 iNAV 를 못 구해 **상한**(이론가 대비 잔차)만 쟀다.
이제 실측 NAV 를 얻는 경로를 찾았으므로, 매일 받아서 시계열로 쌓는다.

[왜 과거는 못 쌓는가]
  · KRX 정보데이터시스템(data.krx.co.kr) — 2026-08 현재 **로그인 필수**로 바뀌었다.
    getJsonData.cmd 가 세션 없이 부르면 본문 "LOGOUT" 과 함께 400 을 준다.
  · 발행사(미래에셋 TIGER / 한국투자 ACE) 상세 페이지의 기준가격 ajax 는
    내부 파라미터가 있어야 하고 외부 호출로는 빈 결과를 준다.
  · ETF체크 등 3자 사이트는 API 경로가 공개돼 있지 않다.
  -> **과거 NAV 는 공개 경로가 없다.** 대신 오늘부터 쌓으면 시간이 해결한다.

[출처] 네이버 금융 ETF 전종목 목록 (로그인 불필요, 약 1,160 종목)
    https://finance.naver.com/api/sise/etfItemList.nhn
  nowVal(현재가) 과 nav(순자산가치) 를 함께 준다. 괴리율 = nowVal/nav − 1.

[실행 시각 주의]
  daily-signal.yml 슬롯은 04:35~09:17 KST 다(v190 이후). 09:00 전 슬롯에서는 한국장이
  아직 안 열렸으므로 받는 값이 **직전 거래일 종가·공식 NAV** 다. 09:17 슬롯은 한국장이
  열린 뒤(실측 09:3x)라 **개장 직후 값**을 준다 - 그 값을 그날 행으로 적으면 행은 다시
  고쳐지지 않으므로 close 열이 **영구히** 종가가 아니게 된다(실측 2026-09-01~04 4행:
  09-04 38,680·거래량 47,392 vs 공식 종가 38,585·178,498 - 2026-09-05 전수 감사).
  -> [v206] **한국장이 열려 있으면 적립하지 않는다**(kr_market_open). 그날 행은 다음
  장 밖 슬롯(대개 다음날 04:35)이 「직전 거래일」로 적는다. as_of 는 trading_as_of().

실행:
    python deploy/nav_collect.py            # 1회 수집 -> data/nav_history.csv 에 append
    python deploy/nav_collect.py --report   # 쌓인 것으로 괴리율 리포트
"""
import csv
import datetime as dt
import io
import json
import math
import os
import sys
import tempfile
import urllib.request

try:                       # [코드리뷰 2026-09-04] 이 파일은 콘솔에 표를 찍는다.
    sys.stdout.reconfigure(encoding='utf-8')   # cp949 콘솔에서 em-dash 로 죽지 않게
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

SRC = 'https://finance.naver.com/api/sise/etfItemList.nhn'
OUT = os.path.join('data', 'nav_history.csv')
HOL = os.path.join('data', 'kr_holidays.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      'Accept': 'application/json',
      'Referer': 'https://finance.naver.com/sise/etf.naver'}

# 전략이 실제로 쓰는 종목 + 대안 + 대조군
# [2026-08-31] 이름 2건이 운용사에서 바뀌어 있었다 — 308620 「미국채10년선물」→
# 「미국10년국채선물」, 148070 「KOSEF」→「KIWOOM」(브랜드 변경). 매칭은 itemcode 로
# 하므로 기능 영향은 0 이고, nav_history.csv 의 과거 행에는 옛 이름이 남아 있다.
WATCH = {
    '458730': 'TIGER 미국배당다우존스',
    '305080': 'TIGER 미국채10년선물',
    '411060': 'ACE KRX금현물',
    '308620': 'KODEX 미국10년국채선물',
    '132030': 'KODEX 골드선물(H)',
    '453850': 'ACE 미국30년국채액티브(H)',
    '148070': 'KIWOOM 국고채10년',
    '418660': 'TIGER 미국나스닥100레버리지',
    '133690': 'TIGER 미국나스닥100',
}

# 실제 전략의 공격 1종 + 방어 3종. 이 네 종목 중 하나라도 빠진 날은 완전한
# 운용 장부가 아니다. 부분 성공으로 봉인하지 않고 다음 슬롯이 다시 받게 한다.
CORE_CODES = ('418660', '458730', '305080', '411060')

COLS = ['as_of', 'code', 'name', 'close', 'nav', 'dev_pct', 'volume', 'mktcap_eok',
        'univ_n', 'univ_med_pct', 'univ_sd_pct']


def fetch():
    """네이버 ETF 목록. NAV 없는 가격 예비 소스는 성공으로 가장하지 않는다.

    이 파일의 목적은 가격 표시가 아니라 **실측 NAV 장부**다. 예비 가격만 받아 빈 행으로
    정상 종료하면 그 슬롯은 재시도되지 않고 해당 거래일이 영구 누락된다. 네이버 NAV가
    없으면 예외를 그대로 올려 워크플로의 다음 슬롯과 실패 이슈가 작동하게 한다.
    """
    try:
        raw = urllib.request.urlopen(urllib.request.Request(SRC, headers=UA), timeout=40).read()
        items = json.loads(raw.decode('utf-8', 'replace'))['result']['etfItemList']
        if not isinstance(items, list):
            raise ValueError('etfItemList가 배열이 아님')
        return items
    except Exception as e:
        raise RuntimeError(f'네이버 ETF NAV 목록 수집 실패({type(e).__name__})') from e


def universe_stats(lst):
    """전 종목 괴리율 분포 — 우리 종목이 정상 범위인지 보는 대조군."""
    d = sorted((i['nowVal'] / i['nav'] - 1) * 100
               for i in lst if i.get('nav') and abs(i['nowVal'] / i['nav'] - 1) < 0.2)
    n = len(d)
    if n < 10:
        return 0, 0.0, 0.0
    med = d[n // 2]
    mean = sum(d) / n
    sd = (sum((x - mean) ** 2 for x in d) / n) ** 0.5
    return n, med, sd


KST = dt.timezone(dt.timedelta(hours=9))
KR_OPEN = dt.time(9, 0)
KR_CLOSE = dt.time(15, 30)   # [v206] 정규장 마감 - 장중 적립 금지의 끝


def kr_market_open(now=None):
    """[v206] 한국 정규장이 열려 있는가(거래일 09:00~15:30 KST).

    열려 있으면 collect() 는 적립하지 않는다. 09:17 슬롯이 적던 개장 직후 값은
    되돌릴 수 없는 영구 행이 됐다(모듈 docstring 실측). 장 밖 슬롯만 적립하면
    close 열은 항상 직전 거래일의 공식 종가·NAV 다.
    """
    now = now or dt.datetime.now(KST)
    d = now.date()
    if d.weekday() >= 5 or d.isoformat() in _kr_holidays(d):
        return False
    return KR_OPEN <= now.time() < KR_CLOSE


def trading_as_of(now=None):
    """[2026-09-04 코드리뷰] 이 스냅샷의 값이 **속한 거래일**.

    종전에는 `dt.date.today()` 였다 — 러너의 **UTC 날짜**다. KST 새벽 슬롯에서는 UTC 가
    전날이라 우연히 「직전 거래일」과 맞아떨어졌지만, 그건 규약이 아니라 시차의 우연이다.
    실제로 어긋난 자리가 장부에 남아 있다: cron 이 UTC 1-5 라 **KST 로는 화~토**에 도는데,
    토요일 09:17 슬롯은 금요일 종가를 받아 놓고 **as_of=토요일**로 적었다
    (data/nav_history.csv 의 2026-08-29 행이 그것이다 — 장부는 §2 라 그대로 둔다).
    한국 임시공휴일에도 같은 일이 난다.

    규약: 한국장이 **오늘 열렸고 09:00 을 지났으면** 오늘, 아니면 **직전 거래일**.
    (네이버가 주는 nowVal 이 정확히 그 값이다 — 장중이면 오늘 값, 장 밖이면 마지막 종가.)
    """
    now = now or dt.datetime.now(KST)
    hol = _kr_holidays(now.date())
    d = now.date()
    if d.weekday() < 5 and d.isoformat() not in hol and now.time() >= KR_OPEN:
        return d.isoformat()
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5 or d.isoformat() in hol:
        d -= dt.timedelta(days=1)
    return d.isoformat()


def _kr_holidays(for_date=None):
    """추적된 휴장일 표를 검증해 돌려준다. 장부 날짜는 달력 없이 추정하지 않는다."""
    if not os.path.exists(HOL):
        raise RuntimeError('kr_holidays.json 이 없다 — NAV 장부 날짜를 정할 수 없음')
    try:
        with open(HOL, encoding='utf-8') as f:
            payload = json.load(f)
    except Exception as e:
        raise RuntimeError('kr_holidays.json 파싱 실패') from e
    holidays = payload.get('holidays')
    years = payload.get('range')
    if not isinstance(holidays, dict) or not isinstance(years, list) or len(years) != 2:
        raise RuntimeError('kr_holidays.json 구조가 잘못됨')
    try:
        lo, hi = int(years[0]), int(years[1])
        parsed = {dt.date.fromisoformat(str(day)) for day in holidays}
    except (TypeError, ValueError) as e:
        raise RuntimeError('kr_holidays.json 날짜·범위를 해석할 수 없음') from e
    if lo > hi or any(not lo <= day.year <= hi for day in parsed):
        raise RuntimeError('kr_holidays.json 날짜가 선언 범위 밖임')
    if for_date is not None and not lo <= for_date.year <= hi:
        raise RuntimeError(
            f'NAV 기준일 {for_date.isoformat()}이 휴장일 표 범위 {lo}~{hi} 밖임')
    return {day.isoformat() for day in parsed}


def _iso_day(value, label='날짜'):
    """YYYY-MM-DD만 허용한다(문자열 정렬을 날짜 정렬로 써도 안전하게)."""
    if not isinstance(value, str):
        raise RuntimeError(f'{label}가 문자열이 아님')
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as e:
        raise RuntimeError(f'{label}가 ISO 날짜가 아님: {value!r}') from e
    if parsed.isoformat() != value:
        raise RuntimeError(f'{label}가 YYYY-MM-DD 형식이 아님: {value!r}')
    return parsed


def _number(row, key, *, positive=False, nonnegative=False):
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f'NAV 행 {row.get("code", "?")}의 {key}가 수치가 아님') from e
    if not math.isfinite(value):
        raise RuntimeError(f'NAV 행 {row.get("code", "?")}의 {key}가 비유한 값임')
    if positive and value <= 0:
        raise RuntimeError(f'NAV 행 {row.get("code", "?")}의 {key}가 0 이하임')
    if nonnegative and value < 0:
        raise RuntimeError(f'NAV 행 {row.get("code", "?")}의 {key}가 음수임')
    return value


def _validate_nav_rows(rows):
    """원자 교체 전에 새 행의 수치 계약과 자체 일관성을 전부 확인한다."""
    seen = set()
    batch_date = None
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(COLS):
            raise RuntimeError('NAV 새 행의 열 계약이 불완전함')
        day = _iso_day(row['as_of'], 'NAV as_of')
        batch_date = day if batch_date is None else batch_date
        if day != batch_date:
            raise RuntimeError('한 번의 NAV append에 날짜가 둘 이상 섞임')
        code = str(row.get('code') or '')
        if code not in WATCH or code in seen:
            raise RuntimeError(f'NAV 새 행 종목 코드가 알 수 없거나 중복됨: {code!r}')
        seen.add(code)
        if not str(row.get('name') or '').strip():
            raise RuntimeError(f'NAV 행 {code}의 이름이 비었음')
        close = _number(row, 'close', positive=True)
        nav = _number(row, 'nav', positive=True)
        dev = _number(row, 'dev_pct')
        if abs(dev) >= 20:
            raise RuntimeError(f'NAV 행 {code}의 괴리율이 허용 범위(절대 20% 미만) 밖임')
        _number(row, 'volume', nonnegative=True)
        _number(row, 'mktcap_eok', nonnegative=True)
        univ_n = _number(row, 'univ_n', nonnegative=True)
        if not univ_n.is_integer() or univ_n < 10:
            raise RuntimeError(f'NAV 행 {code}의 univ_n이 정수가 아니거나 10 미만임')
        _number(row, 'univ_med_pct')
        _number(row, 'univ_sd_pct', nonnegative=True)
        expected = round((close / nav - 1) * 100, 4)
        if abs(dev - expected) > 0.00011:
            raise RuntimeError(
                f'NAV 행 {code}의 dev_pct가 close/nav 계산과 다름({dev} != {expected})')


def _atomic_append_rows(path, rows, replace_func=os.replace):
    """한 날짜의 여러 종목을 한 번에 기록하고 실패하면 원본을 바꾸지 않는다."""
    if not rows:
        return
    _validate_nav_rows(rows)
    original = ''
    if os.path.exists(path):
        with open(path, encoding='utf-8', newline='') as f:
            original = f.read()
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n')
    if not original:
        writer.writeheader()
    writer.writerows(rows)
    suffix = '' if not original or original.endswith(('\n', '\r')) else '\n'
    text = original + suffix + buf.getvalue()
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.nav_history.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        replace_func(tmp, path)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

def collect(as_of=None, now=None):
    now = now or dt.datetime.now(KST)
    if as_of is None and kr_market_open(now):
        # [v206] 장중 값은 적립하지 않는다 - 다음 장 밖 슬롯이 종가로 적는다.
        print(f'{now:%H:%M} KST 한국장 개장 중 - 장중 값은 적립하지 않는다(다음 장 밖 슬롯이 종가로 적는다)')
        return []
    as_of = as_of or trading_as_of(now)   # ★ UTC 날짜가 아니라 「값이 속한 거래일」
    as_day = _iso_day(as_of, '새 NAV as_of')
    if as_day > dt.datetime.now(KST).date():
        raise RuntimeError('새 NAV as_of가 KST 현재 날짜보다 미래임')
    os.makedirs('data', exist_ok=True)
    have = set()
    existing = []
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != COLS:
                raise RuntimeError('기존 nav_history.csv 헤더가 현행 계약과 다름')
            existing = list(reader)
            keys = [(r.get('as_of', ''), r.get('code', '')) for r in existing]
            if any(not a or not c for a, c in keys) or len(set(keys)) != len(keys):
                raise RuntimeError('기존 nav_history.csv 날짜·종목 키가 비었거나 중복됨')
            dates = [a for a, _ in keys]
            for day in dates:
                _iso_day(day, '기존 NAV as_of')
            if dates != sorted(dates):
                raise RuntimeError('기존 nav_history.csv 날짜 순서가 뒤집힘')
            batches = {}
            for row in existing:
                batches.setdefault(row['as_of'], []).append(row)
            for day, batch in batches.items():
                _validate_nav_rows(batch)
                covered = {r['code'] for r in batch if r['code'] in CORE_CODES}
                if covered != set(CORE_CODES):
                    raise RuntimeError(
                        f'기존 nav_history.csv {day} 핵심 4종이 불완전함')
            for r in existing:
                have.add((r['as_of'], r['code']))

    # 이미 핵심 네 종목이 모두 봉인된 재실행은 외부 API·T4와 무관한 완전한 no-op이다.
    existing_core = {code for day, code in have if day == as_of and code in CORE_CODES}
    if existing_core == set(CORE_CODES):
        print(f'{as_of} 핵심 4종은 이미 기록됨 — 변경하지 않는다')
        return []
    if existing and as_of < existing[-1]['as_of']:
        raise RuntimeError('새 NAV 날짜가 기존 장부 끝보다 과거임 — 중간 삽입을 거부한다')

    lst = fetch()
    itemcodes = [str(i.get('itemcode') or '') for i in lst if isinstance(i, dict)]
    watched = [code for code in itemcodes if code in WATCH]
    if len(watched) != len(set(watched)):
        raise RuntimeError('네이버 NAV 응답에 감시 종목 코드가 중복됨')
    by = {str(i.get('itemcode') or ''): i for i in lst if isinstance(i, dict)}
    n, med, sd = universe_stats(lst)

    rows = []
    for code, nm in WATCH.items():
        it = by.get(code)
        if not it or not it.get('nav'):
            continue
        if (as_of, code) in have:
            continue
        rows.append({'as_of': as_of, 'code': code, 'name': nm,
                     'close': it['nowVal'], 'nav': it['nav'],
                     'dev_pct': round((it['nowVal'] / it['nav'] - 1) * 100, 4),
                     'volume': it.get('quant', ''), 'mktcap_eok': it.get('marketSum', ''),
                      'univ_n': n, 'univ_med_pct': round(med, 4), 'univ_sd_pct': round(sd, 4)})

    covered_core = existing_core | {r['code'] for r in rows if r['code'] in CORE_CODES}
    missing = sorted(set(CORE_CODES) - covered_core)
    if missing:
        raise RuntimeError('핵심 4종 NAV가 모두 오지 않아 장부를 쓰지 않음: ' + ', '.join(missing))
    _validate_nav_rows(rows)

    _atomic_append_rows(OUT, rows)
    print('%s  신규 %d행 기록 (전체 %d종목, 시장 중앙 %.3f%% / 표준편차 %.3f%%)'
          % (as_of, len(rows), n, med, sd))
    return rows


def selftest():
    """휴장일 fail-close, 완전 수집 계약, 다종목 원자 append의 최소 반례."""
    global HOL, OUT, fetch
    saved_hol, saved_out, saved_fetch = HOL, OUT, fetch
    try:
        with tempfile.TemporaryDirectory() as td:
            HOL = os.path.join(td, 'holidays.json')
            payload = {'range': [2025, 2032],
                       'holidays': {'2026-10-05': '개천절 대체'}}
            with open(HOL, 'w', encoding='utf-8') as f:
                json.dump(payload, f)
            monday = dt.datetime(2026, 10, 5, 10, 0, tzinfo=KST)
            assert trading_as_of(monday) == '2026-10-02'

            # [v206] 장중 적립 금지 - 개장 중엔 fetch 조차 부르지 않고 빈 손으로 돌아온다.
            tue_open = dt.datetime(2026, 10, 6, 9, 35, tzinfo=KST)
            assert kr_market_open(tue_open)
            assert not kr_market_open(dt.datetime(2026, 10, 6, 4, 40, tzinfo=KST))   # 마감 전 슬롯
            assert not kr_market_open(dt.datetime(2026, 10, 6, 15, 30, tzinfo=KST))  # 정규장 마감
            assert not kr_market_open(monday)                                          # 휴장일
            assert not kr_market_open(dt.datetime(2026, 10, 10, 10, 0, tzinfo=KST))  # 토요일

            def _boom():
                raise AssertionError('장중 적립 금지인데 fetch 를 불렀다')
            fetch = _boom
            assert collect(now=tue_open) == []

            os.unlink(HOL)
            try:
                trading_as_of(monday)
                raise AssertionError('휴장일 표 누락을 정상 영업일로 처리했다')
            except RuntimeError:
                pass
            with open(HOL, 'w', encoding='utf-8') as f:
                f.write('{broken')
            try:
                trading_as_of(monday)
                raise AssertionError('깨진 휴장일 표를 정상 영업일로 처리했다')
            except RuntimeError:
                pass
            with open(HOL, 'w', encoding='utf-8') as f:
                json.dump({'range': [2025, 2025], 'holidays': {}}, f)
            try:
                trading_as_of(monday)
                raise AssertionError('휴장일 표 범위 밖 날짜를 허용했다')
            except RuntimeError:
                pass

            out = os.path.join(td, 'nav.csv')
            first = dict(as_of='2026-09-01', code='418660', name='TIGER',
                         close=100, nav=100, dev_pct=0, volume=0, mktcap_eok=0,
                         univ_n=10, univ_med_pct=0, univ_sd_pct=1)
            _atomic_append_rows(out, [first])
            with open(out, 'rb') as f:
                original = f.read()

            def fail_replace(src, dst):
                raise OSError('교체 실패 모의')
            second = dict(first, as_of='2026-09-02')
            try:
                _atomic_append_rows(out, [second], replace_func=fail_replace)
                raise AssertionError('NAV 원자 교체 실패를 성공으로 처리했다')
            except OSError:
                pass
            with open(out, 'rb') as f:
                assert f.read() == original

            # 실제 collect 경계: 핵심 4종 완전성, 값 검증, 날짜 비후퇴, 성공 재실행 no-op.
            OUT = os.path.join(td, 'collected.csv')
            with open(HOL, 'w', encoding='utf-8') as f:
                json.dump(payload, f)

            def items():
                rows = []
                for k, code in enumerate(WATCH):
                    rows.append({'itemcode': code, 'nowVal': 100 + k, 'nav': 100 + k,
                                 'quant': 0, 'marketSum': 1})
                rows.append({'itemcode': '000000', 'nowVal': 100, 'nav': 100,
                             'quant': 0, 'marketSum': 1})
                rows.append({'itemcode': '000001', 'nowVal': 100, 'nav': 100,
                             'quant': 0, 'marketSum': 1})
                return rows

            fetch = items
            assert len(collect('2026-09-01')) == len(WATCH)
            with open(OUT, 'rb') as f:
                collected = f.read()

            fetch = lambda: (_ for _ in ()).throw(RuntimeError('재실행은 외부 호출 금지'))
            assert collect('2026-09-01') == []
            with open(OUT, 'rb') as f:
                assert f.read() == collected

            # 같은 날 no-op도 기존 장부 검증보다 먼저 빠져나가면 오염을 영구 은닉한다.
            lines = collected.decode('utf-8').splitlines()
            fields = lines[1].split(',')
            fields[3] = 'nan'
            corrupted = ('\n'.join([lines[0], ','.join(fields), *lines[2:]]) + '\n').encode()
            with open(OUT, 'wb') as f:
                f.write(corrupted)
            try:
                collect('2026-09-01')
                raise AssertionError('오염된 기존 NAV 장부를 no-op으로 숨겼다')
            except RuntimeError:
                pass
            with open(OUT, 'wb') as f:
                f.write(collected)

            partial = items()
            partial = [r for r in partial if r.get('itemcode') != CORE_CODES[0]]
            fetch = lambda: partial
            try:
                collect('2026-09-02')
                raise AssertionError('핵심 종목 누락을 부분 성공으로 기록했다')
            except RuntimeError:
                pass
            with open(OUT, 'rb') as f:
                assert f.read() == collected

            core_only = [r for r in items() if r.get('itemcode') in CORE_CODES]
            fetch = lambda: core_only
            try:
                collect('2026-09-02')
                raise AssertionError('절단된 소수 종목 응답을 정상 시장 표본으로 기록했다')
            except RuntimeError:
                pass
            with open(OUT, 'rb') as f:
                assert f.read() == collected

            invalid = items()
            next(r for r in invalid if r.get('itemcode') == CORE_CODES[0])['nowVal'] = float('nan')
            fetch = lambda: invalid
            try:
                collect('2026-09-02')
                raise AssertionError('비유한 NAV 응답을 장부에 기록했다')
            except RuntimeError:
                pass
            with open(OUT, 'rb') as f:
                assert f.read() == collected

            extreme = items()
            bad = next(r for r in extreme if r.get('itemcode') == CORE_CODES[0])
            bad['nowVal'], bad['nav'] = 100.0, 1.0
            fetch = lambda: extreme
            try:
                collect('2026-09-02')
                raise AssertionError('절대 20% 밖 괴리율을 장부에 기록했다')
            except RuntimeError:
                pass
            with open(OUT, 'rb') as f:
                assert f.read() == collected

            fetch = items
            try:
                collect('2026-08-31')
                raise AssertionError('기존 끝보다 과거인 날짜를 append했다')
            except RuntimeError:
                pass
            with open(OUT, 'rb') as f:
                assert f.read() == collected
    finally:
        HOL, OUT, fetch = saved_hol, saved_out, saved_fetch
    print('nav_collect selftest: PASS (휴장일 · 장중 적립 금지 · 핵심 4종 완전성 · 값/날짜 · 원자 append/no-op)')


def report():
    if not os.path.exists(OUT):
        sys.exit('아직 수집분이 없다. 먼저 python deploy/nav_collect.py 를 돌려라.')
    with open(OUT, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    days = sorted({r['as_of'] for r in rows})
    print('===== 실측 괴리율 (시장가 / NAV − 1) =====')
    print('수집 구간 %s ~ %s  (%d 영업일)' % (days[0], days[-1], len(days)))
    print()
    print('%-8s %-28s %8s %8s %8s %8s %6s' %
          ('코드', '이름', '평균', '표준편차', '최소', '최대', 'n'))
    for code, nm in WATCH.items():
        v = [float(r['dev_pct']) for r in rows if r['code'] == code]
        if not v:
            continue
        m = sum(v) / len(v)
        sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5 if len(v) > 1 else 0.0
        print('%-8s %-28s %7.3f%% %7.3f%% %7.3f%% %7.3f%% %6d'
              % (code, nm, m, sd, min(v), max(v), len(v)))
    u = [float(r['univ_sd_pct']) for r in rows if r['univ_sd_pct']]
    if u:
        print('\n  대조군: 국내 전체 ETF 괴리율 표준편차 평균 %.3f%%' % (sum(u) / len(u)))
    if len(days) < 20:
        print('\n  ※ %d 영업일뿐이라 아직 분포를 논하기 이르다.' % len(days))
        print('    daily-signal.yml 이 매일 한 줄씩 쌓으므로 시간이 해결한다.')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    elif '--report' in sys.argv:
        report()
    else:
        collect()
