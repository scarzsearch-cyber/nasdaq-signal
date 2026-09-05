#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v72] 월 1회 원자료 연장 — 성과 스냅샷(전략 곡선·지평표)을 최신으로 유지한다.

원칙:
  · **기존 행은 절대 고치지 않는다** (동결된 연구 스냅샷 보존). 마지막 날짜 뒤만 붙인다.
  · 수정주가는 **비율 이음(ratio-splice)**: 붙이는 구간 = 야후 수정주가 × k,
    k = 저장된 마지막 종가 / 야후 수정주가(같은 날). 수정주가의 정보는 레벨이 아니라
    **수익률**이므로, 이음새 이후 수익률이 야후의 조정 수익률과 정확히 일치하면 된다.
    배당이 지나 야후가 과거를 재조정해도 k 가 그걸 흡수한다 (자가 치유).
  · 장중 가드: 정규장 진행 중이면 마지막 봉 제외 (update_signal.py 와 같은 판별).
  · 미국·한국 장이 모두 닫힌 시각(매월 1일 07:17 UTC)에 돌도록 예약돼 있다.

대상 (build_stats.py 4개 시나리오의 전방 의존성 전부):
  qqq/qld/schd_us_d.csv   미국 3종 (Close=수정주가, OHLCV)
  yahoo_TNX.csv           10년 금리 (국채 다리)
  lbma_gold_pm.csv        금 — LBMA 는 야후에 없어 GLD 수익률로 이음 (연 0.4% 보수만큼
                          현물보다 불리 — 방어 다리 20% 에 묻히는 크기, 문서화됨)
  kr_*.csv 5종            TIGER 실물 + KOSPI 달력 (Open 원시가 + AdjClose 이음)
  fred_DEXKOUS.csv        원달러 — FRED 공식 CSV를 검증해 기존 마지막 날 뒤만 추가

실행:  python deploy/refresh_hist.py          # 저장소 루트에서
"""
import csv
import io
import json
import os
import sys
import tempfile
import time
import urllib.request

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_check import validate_frame            # noqa: E402  [v73] 검증 게이트

FAILURES = []                                    # 검증 실패 파일 목록
MAX_GLOBAL_GAP_DAYS = 8                          # 미국·금리·금·환율: 실측 최대 7일 + 1일
MAX_KR_GAP_DAYS = 16                             # 한국: 2017 추석 실측 11일 + 임시공휴일 여유
TNX_MAX_DAILY_MOVE = 0.75                        # 저장 이력 최대 49.9% + 넓은 안전 여유
TNX_VALUE_BOUNDS = {'Close': (0.01, 30.0), 'Open': (0.01, 30.0)}

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


def _bar_index(timestamps, meta):
    """봉의 날짜 라벨 = **거래소 시간대의 달력일** (야후 화면과 같은 날짜).

    [2026-09-05 2차 리뷰 R2-12] UTC 로 자르면 FX(KRW=X)가 어긋난다. 런던 서머타임엔 세션이
    전날 23:00 UTC 에 시작해 금요일 세션이 목요일 라벨을 받았고, FRED 꼬리(금요일)를 이음날로
    못 찾아 야후 예비 경로가 여름 내내 실패-폐쇄했다(겨울엔 00:00 UTC 시작이라 우연히 맞았다).
    미국(13:30 UTC)·한국(00:00 UTC)·시카고(12:20 UTC) 봉은 어느 쪽으로 잘라도 같은 날이다.
    시간대 이름을 모르면 UTC(종전 동작)."""
    idx = pd.to_datetime(timestamps, unit='s', utc=True)
    tz = (meta or {}).get('exchangeTimezoneName')
    if tz:
        try:
            idx = idx.tz_convert(tz)
        except Exception:
            pass
    return idx.tz_localize(None).normalize()


def _drop_intraday_bar(df, meta, now=None):
    """정규장 **진행 중**인 오늘 봉만 제거한다. 판정 메타가 없으면 실패-폐쇄한다.

    [2026-09-05 2차 리뷰 R2-11] regularMarketTime 만으로는 장중을 판정할 수 없다. ^TNX 같은
    지수는 마지막 체결이 마감 1분 전(18:59, 마감 19:00 UTC)이라 마감 뒤에도 start<=qt<end 가
    참이었고, 매달 1일 07:17 UTC 슬롯이 확정봉을 지워 yahoo_TNX.csv 가 다른 미국 자료보다
    늘 하루 짧았다(실측 08-27 vs 08-28, 9704ac0 과 그 부모 커밋에서도 같은 간격).
    벽시계(now)가 마감을 지났으면 확정봉이다. now 는 검산용 주입 인자다."""
    regular = (meta or {}).get('currentTradingPeriod', {}).get('regular', {})
    qt = (meta or {}).get('regularMarketTime')
    start, end = regular.get('start'), regular.get('end')
    if not all(isinstance(v, (int, float)) for v in (qt, start, end)):
        raise RuntimeError('Yahoo 응답에 장중 판정 메타가 없다')
    if len(df) == 0 or not (start <= qt < end):
        return df
    now_ts = time.time() if now is None else float(now)
    if now_ts >= end:
        return df
    # FX처럼 현재 세션을 시작 timestamp와 현재 quote timestamp 두 행으로 주는 응답도
    # 있다. 마지막 한 행만 자르면 close=None인 시작 행이 남으므로 세션 시작일부터 뺀다.
    live_start = _bar_index([start], meta)[0]
    return df.loc[df.index < live_start]


def _drop_kr_intraday_bar(df, now=None):
    """네이버 일봉 fallback에서 한국 정규장 진행 중인 오늘 행을 제거한다."""
    ts = pd.Timestamp.now(tz='Asia/Seoul') if now is None else pd.Timestamp(now)
    if ts.tzinfo is None:
        ts = ts.tz_localize('Asia/Seoul')
    else:
        ts = ts.tz_convert('Asia/Seoul')
    minute = ts.hour * 60 + ts.minute
    if ts.weekday() < 5 and 9 * 60 <= minute < 15 * 60 + 30 and len(df):
        today = ts.tz_localize(None).normalize()
        if pd.Timestamp(df.index[-1]).tz_localize(None).normalize() == today:
            return df.iloc[:-1]
    return df


def chart(symbol, years=3, require_adj=False, now=None):
    """야후 v8 chart — 수정주가 필수 경로는 raw close 대체를 금지한다. now 는 검산용 벽시계."""
    import datetime
    p2 = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    p1 = p2 - years * 366 * 86400
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
           f'?period1={p1}&period2={p2}&interval=1d')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read().decode('utf-8', 'replace'))['chart']['result'][0]
    meta = res.get('meta', {})
    idx = _bar_index(res['timestamp'], meta)
    if idx.has_duplicates or not idx.is_monotonic_increasing:
        raise RuntimeError(f'{symbol}: Yahoo 원본 날짜가 중복되거나 역순임')
    q = res['indicators']['quote'][0]
    for name in ('open', 'high', 'low', 'close', 'volume'):
        values = q.get(name)
        if not isinstance(values, list) or len(values) != len(idx):
            raise RuntimeError(f'{symbol}: Yahoo {name} 배열이 없거나 길이가 다름')
    adj_blocks = res['indicators'].get('adjclose') or []
    adj = adj_blocks[0].get('adjclose') if adj_blocks else None
    close_values = q.get('close')
    adj_ok = isinstance(adj, list) and len(adj) == len(idx)
    if require_adj:
        if not adj_ok:
            raise RuntimeError(f'{symbol}: Yahoo 수정주가 배열이 없거나 길이가 다름')
    elif not adj_ok:
        # 금리·환율·무배당 지수처럼 호출자가 raw를 허용한 경로만 명시적으로 대체한다.
        adj = close_values
    df = pd.DataFrame({'open': q['open'], 'high': q.get('high'), 'low': q.get('low'),
                       'close': q['close'], 'adj': adj, 'volume': q['volume']}, index=idx)
    # Yahoo는 휴장일 timestamp에 OHLC·수정주가·거래량이 전부 null인 placeholder를
    # 종목 종류와 무관하게 섞는다. 전부 빈 행만 날짜째 제거하고, 일부만 빈 봉은 남겨
    # 아래 strict 검증에서 거부한다.
    value_cols = ['open', 'high', 'low', 'close', 'adj', 'volume']
    # errors='coerce' 뒤 판정하면 문자열 오염도 빈 휴장행처럼 사라진다. 원본의 실제
    # None/NaN만 placeholder로 인정하고, 비수치는 아래 strict 검증에 남긴다.
    placeholders = df[value_cols].isna().all(axis=1)
    df = df.loc[~placeholders]
    if df.empty:
        raise RuntimeError(f'{symbol}: Yahoo 원본이 빈 placeholder뿐임')
    # 장중 행은 아직 close가 없을 수 있으므로 결측 검증보다 먼저 메타로 제거한다.
    df = _drop_intraday_bar(df, meta, now=now)
    if df.empty:
        raise RuntimeError(f'{symbol}: 확정된 Yahoo 봉이 없음')
    numeric = df[value_cols].apply(pd.to_numeric, errors='coerce')
    if require_adj:
        if numeric.loc[numeric['close'].notna(), 'adj'].isna().any():
            raise RuntimeError(f'{symbol}: Yahoo 수정주가에 비어 있는 값이 있음')
    else:
        partial = numeric['close'].isna()
        if partial.any():
            raise RuntimeError(f'{symbol}: Yahoo 원본 종가만 비어 있는 불완전 봉이 있음')
    if df['close'].isna().any():
        raise RuntimeError(f'{symbol}: Yahoo 원본 종가에 결측이 있음')
    return df


def read_csv(path):
    return pd.read_csv(path, parse_dates=['Date'])


def _abort_update(path, problems):
    """한 파일의 갱신을 실패-폐쇄하고 main 의 비정상 종료까지 전달한다."""
    name = os.path.basename(path)
    for msg in problems:
        print(f'  [검증실패] {msg}', file=sys.stderr)
    print(f'  {name:22s} 갱신 중단 — 기존 데이터 유지, 수동 검증 필요',
          file=sys.stderr)
    if name not in FAILURES:
        FAILURES.append(name)
    return 0


def _normalise_utc_day(value=None):
    """시간대 유무와 무관하게 UTC 기준의 tz-naive 날짜로 정규화한다."""
    ts = pd.Timestamp.now(tz='UTC') if value is None else pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert('UTC').tz_localize(None)
    return ts.normalize()


def _validate_download(path, df, required_cols, anchor=None,
                       max_age_days=None, today=None):
    """chart 계열 원본이 실제 자료이고 기존 끝과 이어지는지 쓴 뒤 판단한다.

    append 후보가 0행이라는 사실만으로는 "이미 최신"과 "빈 다운로드"를 구별할 수
    없다. 따라서 모든 chart 소비자는 필터링 전에 이 검사를 통과해야 한다. 비율 이음이
    필요 없는 TNX 도 기존 마지막 날을 원본에서 확인해, 빈/절단 응답을 최신으로 오인하지
    않는다.
    """
    name = os.path.basename(path)
    if df is None or len(df) == 0:
        _abort_update(path, [f'{name}: 내려받은 원본이 0행이다'])
        return False

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        _abort_update(
            path, [f'{name}: 내려받은 원본의 핵심 열 누락 — {", ".join(missing)}'])
        return False

    try:
        idx = pd.DatetimeIndex(pd.to_datetime(df.index, errors='coerce', utc=True))
    except Exception:
        idx = pd.DatetimeIndex([])
    problems = []
    if len(idx) != len(df) or idx.isna().any():
        problems.append(f'{name}: 내려받은 원본의 날짜를 해석할 수 없다')
    elif idx.has_duplicates:
        problems.append(f'{name}: 내려받은 원본에 중복 날짜가 있다')
    elif not idx.is_monotonic_increasing:
        problems.append(f'{name}: 내려받은 원본의 날짜 순서가 뒤집혔다')

    if anchor is not None and not problems:
        anchor_ts = pd.to_datetime(anchor, errors='coerce', utc=True)
        if pd.isna(anchor_ts):
            problems.append(f'{name}: 기존 마지막 날짜를 해석할 수 없다 — {anchor}')
        else:
            idx_days = idx.tz_convert(None).normalize()
            anchor_day = anchor_ts.tz_convert(None).normalize()
            if anchor_day not in idx_days:
                problems.append(
                    f'{name}: 이음날 {anchor_day.date()} 이 내려받은 원본에 없다')

    if max_age_days is not None and not problems:
        latest = idx.tz_convert(None).normalize().max()
        today_day = _normalise_utc_day(today)
        cutoff = today_day - pd.Timedelta(days=max_age_days)
        if latest > today_day:
            problems.append(
                f'{name}: 내려받은 원본에 미래 날짜가 있음 — {latest.date()} > {today_day.date()}')
        if latest < cutoff:
            problems.append(
                f'{name}: 내려받은 원본이 오래됨 — 마지막 {latest.date()}, '
                f'허용 최저 {cutoff.date()}')

    if problems:
        _abort_update(path, problems)
        return False
    return True


def _already_current(path):
    """정상 원본과 이음날을 확인한 호출자만 사용할 수 있는 0행 성공 경로."""
    print(f'  {os.path.basename(path):22s} 추가 0행 (이미 최신)')
    return 0


def _atomic_write_bytes(path, data, replace_func=os.replace):
    """같은 디렉터리 임시파일을 완전히 기록한 뒤 한 번에 교체한다.

    네트워크 원문을 기존 파일에 바로 쓰면 프로세스 중단·디스크 오류 때 원본까지
    잃는다. 임시파일의 flush/fsync가 끝난 뒤에만 교체하며, 교체 실패 시 임시파일만
    치우고 기존 파일은 그대로 둔다. ``replace_func``는 실패 경계 selftest용이다.
    """
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.',
                               suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        replace_func(tmp, path)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def _atomic_write_text(path, text, replace_func=os.replace):
    """UTF-8 텍스트를 원자적으로 교체한다."""
    _atomic_write_bytes(path, text.encode('utf-8'), replace_func=replace_func)


def _csv_header(original):
    """UTF-8 CSV 원본의 첫 줄을 열 목록으로 읽는다."""
    if not original:
        raise RuntimeError('기존 CSV가 비어 있음')
    try:
        first_line = original.splitlines()[0].decode('utf-8-sig')
        return next(csv.reader([first_line]))
    except (UnicodeDecodeError, csv.Error, StopIteration) as e:
        raise RuntimeError(f'기존 CSV 헤더를 해석할 수 없음 — {e}') from e


def _atomic_append_values(path, rows, cols=None, replace_func=os.replace):
    """기존 CSV 바이트를 건드리지 않고 날짜·값 행만 원자적으로 덧붙인다."""
    with open(path, 'rb') as f:
        original = f.read()
    if cols is not None and _csv_header(original) != list(cols):
        raise RuntimeError(
            f'기존 CSV 열이 다름 — {_csv_header(original)} != {list(cols)}')
    suffix = b'' if not original or original.endswith((b'\n', b'\r')) else b'\n'
    suffix += ''.join(f'{d},{v}\n' for d, v in rows).encode('utf-8')
    _atomic_write_bytes(path, original + suffix, replace_func=replace_func)


def _atomic_append_frame(path, new_df, cols, replace_func=os.replace):
    """기존 CSV prefix를 바이트 단위로 보존하고 새 행만 원자적으로 덧붙인다."""
    with open(path, 'rb') as f:
        original = f.read()
    header = _csv_header(original)
    expected = list(cols)
    if header != expected:
        raise RuntimeError(f'기존 CSV 열이 다름 — {header} != {expected}')

    rows = new_df.loc[:, expected].copy()
    if 'Date' in rows.columns:
        dates = pd.to_datetime(rows['Date'], errors='raise')
        rows['Date'] = dates.dt.strftime('%Y-%m-%d')
    payload = rows.to_csv(index=False, header=False, lineterminator='\n').encode('utf-8')
    separator = b'' if original.endswith((b'\n', b'\r')) else b'\n'
    _atomic_write_bytes(path, original + separator + payload, replace_func=replace_func)


def _fred_last_valid(old):
    """기존 FRED/Yahoo 혼합 파일에서 마지막 유효 환율 날짜를 찾는다."""
    if len(old.columns) < 2:
        raise RuntimeError('기존 FRED 파일 열이 부족함')
    dates = pd.to_datetime(old.iloc[:, 0], errors='coerce')
    if dates.isna().any():
        raise RuntimeError('기존 FRED 파일 날짜를 해석할 수 없음')
    values = pd.to_numeric(old.iloc[:, 1], errors='coerce')
    valid = values.notna()
    if not valid.any():
        raise RuntimeError('기존 FRED 파일에 유효한 환율이 없음')
    return dates[valid].max()


def _fred_last_date(old):
    """기존 파일의 마지막 *물리 행* 날짜를 돌려준다.

    FRED는 마지막 며칠을 ``.``으로 먼저 싣고 나중에 값을 채울 수 있다. 추가 기준을
    마지막 유효값으로 잡으면 그 결측 날짜를 다시 붙여 중복 행을 만든다. 기존 prefix를
    불변으로 두는 계약상 append floor는 값 유무와 무관한 마지막 날짜여야 한다.
    """
    if len(old.columns) < 2 or old.empty:
        raise RuntimeError('기존 FRED 파일 열 또는 행이 부족함')
    dates = pd.to_datetime(old.iloc[:, 0], errors='coerce')
    if dates.isna().any():
        raise RuntimeError('기존 FRED 파일 날짜를 해석할 수 없음')
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise RuntimeError('기존 FRED 파일 날짜가 중복되거나 역순임')
    return dates.iloc[-1]


def _validate_fred_payload(path, txt, old, today=None):
    """FRED 원문을 날짜 1열·수치 1열 시계열로 검증해 메타데이터를 돌려준다.

    FRED는 휴장일을 ``.``(pandas에서는 NaN)로 싣는다. 그 행은 원문 보존을 위해
    파일에는 남기되, 값 검증과 최신일 판정에서는 제외한다. 그 밖의 비수치 토큰,
    중복·역순 날짜, 비양수/비유한 환율, 비정상 공백은 교체 전에 막는다.
    """
    if not isinstance(txt, str) or not txt.strip():
        raise RuntimeError('FRED 응답이 비어 있음')
    new = pd.read_csv(io.StringIO(txt))
    if list(new.columns) != ['observation_date', 'DEXKOUS']:
        raise RuntimeError(f'FRED 응답 열이 다름 — {list(new.columns)}')
    if len(new) == 0:
        raise RuntimeError('FRED 응답이 0행')

    dates = pd.to_datetime(new['observation_date'], errors='coerce')
    if dates.isna().any():
        raise RuntimeError('FRED 날짜를 해석할 수 없음')
    if dates.duplicated().any():
        raise RuntimeError('FRED 날짜가 중복됨')
    if not dates.is_monotonic_increasing:
        raise RuntimeError('FRED 날짜 순서가 뒤집힘')

    raw = new['DEXKOUS']
    values = pd.to_numeric(raw, errors='coerce')
    missing = raw.isna() | raw.astype(str).str.strip().isin(('', '.'))
    invalid = ~missing & values.isna()
    if invalid.any():
        bad = raw[invalid].iloc[0]
        raise RuntimeError(f'FRED 환율에 비수치 값이 있음 — {bad!r}')
    keep = ~missing
    candidate = pd.DataFrame({'Date': dates[keep].to_numpy(),
                              'Close': values[keep].to_numpy()})
    problems = validate_frame(candidate, os.path.basename(path), ['Close'],
                              max_gap=MAX_GLOBAL_GAP_DAYS)
    if problems:
        raise RuntimeError('; '.join(problems))

    n_old = len(old)
    old_last = _fred_last_valid(old)
    old_end = _fred_last_date(old)
    new_last = candidate['Date'].max()
    if len(new) < n_old * 0.9:
        raise RuntimeError(f'FRED 새 파일이 비정상적으로 짧음 — {len(new)} < {n_old}×0.9')
    if new_last < old_end:
        raise RuntimeError(
            f'FRED 최신 값이 기존 끝보다 뒤처짐 — {new_last.date()} < {old_end.date()}')
    cutoff = _normalise_utc_day(today) - pd.Timedelta(days=MAX_GLOBAL_GAP_DAYS)
    today_day = _normalise_utc_day(today)
    newest_observation = dates.max()
    if newest_observation > today_day:
        raise RuntimeError(
            f'FRED 응답에 미래 날짜가 있음 — {newest_observation.date()} > {today_day.date()}')
    if new_last < cutoff:
        raise RuntimeError(
            f'FRED 최신 값이 오래됨 — 마지막 {new_last.date()}, 허용 최저 {cutoff.date()}')
    return new, new_last


def append_rows(path, new_df, cols, price_cols=('Close',), prev=None, allow_move=(),
                 prev_date=None, max_gap=MAX_GLOBAL_GAP_DAYS, max_move=0.30,
                 value_bounds=None, prev_values=None, ohlc_cols=None):
    """new_df 를 검증 게이트에 통과시킨 뒤에만 파일 끝에 붙인다.

    0행은 빈 다운로드일 수 있으므로 이 함수에서는 실패다. 정상적인 "이미 최신"은
    각 splicer가 원본과 anchor를 검증한 뒤 _already_current()로만 판정한다.
    [v73] 검증 실패 시: 쓰지 않고(기존 데이터 유지) FAILURES 에 기록 — main 이
    종료코드 1 로 끝나 workflow 가 build_stats 를 돌리지 않는다 (downstream 보호)."""
    probs = validate_frame(new_df, os.path.basename(path), list(price_cols),
                           prev_close=prev, allow_move_cols=allow_move,
                           prev_date=prev_date, max_gap=max_gap, max_move=max_move,
                           value_bounds=value_bounds, prev_values=prev_values,
                           ohlc_cols=ohlc_cols)
    if probs:
        return _abort_update(path, probs)
    try:
        _atomic_append_frame(path, new_df, cols)
    except Exception as e:
        return _abort_update(
            path, [f'{os.path.basename(path)}: 기존 prefix 보존 append 실패 — '
                   f'{type(e).__name__}: {e}'])
    print(f'  {os.path.basename(path):22s} 추가 {len(new_df)}행 '
          f'(~{new_df["Date"].iloc[-1].date()})')
    return len(new_df)


def splice_us(path, symbol, today=None):
    """미국 3종: Close=수정주가 비율 이음. OHL 도 같은 비율로 조정해 붙인다."""
    old = read_csv(path)
    last_d, last_c = old['Date'].iloc[-1], float(old['Close'].iloc[-1])
    try:
        df = chart(symbol, require_adj=True)
    except Exception as e:
        return _abort_update(
            path, [f'{os.path.basename(path)}: Yahoo 수정주가 실패 — {type(e).__name__}: {e}'])
    if not _validate_download(path, df,
                              ('open', 'high', 'low', 'close', 'adj', 'volume'),
                              anchor=last_d, max_age_days=MAX_GLOBAL_GAP_DAYS,
                              today=today):
        return 0
    k = last_c / float(df.loc[last_d, 'adj'])
    new = df[df.index > last_d].copy()
    if new.empty:
        return _already_current(path)
    f = (new['adj'] * k / new['close'])              # 원시 → 이 파일의 수정 기준
    out = pd.DataFrame({'Date': new.index,
                        'Open': new['open'] * f, 'High': new['high'] * f,
                        'Low': new['low'] * f, 'Close': new['adj'] * k,
                        'Volume': new['volume'].fillna(0).astype('int64')})
    seam = {c: last_c for c in ('Close', 'Open', 'High', 'Low')}
    return append_rows(path, out, ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
                       price_cols=('Close', 'Open', 'High', 'Low'), prev_date=last_d,
                       prev_values=seam,
                       ohlc_cols=('Open', 'High', 'Low', 'Close'))


def splice_kr(path, symbol, today=None, now=None):
    """한국 종목 — 파일 형식이 둘이다 (hist_defasset.kr 의 주석과 동일):
      A) Date,Open,Close,AdjClose        : Open/Close 원시가 + AdjClose 만 비율 이음
      B) Date,Open,Close,Volume,Raw      : Close 가 이미 조정본 → Close 를 비율 이음,
                                           Raw 에 원시 종가, Open 은 원시가 그대로
    """
    old = read_csv(path)
    has_adj = 'AdjClose' in old.columns
    adj_col = 'AdjClose' if has_adj else 'Close'
    last_d, last_a = old['Date'].iloc[-1], float(old[adj_col].iloc[-1])
    try:
        df = chart(symbol, require_adj=(symbol != '^KS11'))
    except Exception as e:
        # ETF의 네이버 일봉은 수정주가가 아니다. 배당락을 손실로 굳힌 행은 Yahoo가
        # 돌아와도 anchor 뒤만 붙이는 구조상 영구 복구되지 않으므로 ETF는 실패-폐쇄한다.
        if symbol != '^KS11':
            return _abort_update(
                path, [f'{os.path.basename(path)}: Yahoo 수정주가 실패({type(e).__name__}) — '
                       '비수정 네이버 ETF 일봉으로 대체하지 않음'])
        print(f'  {os.path.basename(path):22s} [경고] 야후 실패({type(e).__name__}) — '
              '배당이 없는 KOSPI 지수만 네이버 일봉으로 보강', file=sys.stderr)
        import kr_sources
        df = kr_sources.history_df(symbol, count=90)
        df = _drop_kr_intraday_bar(df, now=now)
    if not _validate_download(path, df, ('open', 'close', 'adj', 'volume'),
                              anchor=last_d, max_age_days=MAX_KR_GAP_DAYS,
                              today=today):
        return 0
    k = last_a / float(df.loc[last_d, 'adj'])
    new = df[df.index > last_d]
    if new.empty:
        return _already_current(path)
    if has_adj:
        out = pd.DataFrame({'Date': new.index, 'Open': new['open'],
                            'Close': new['close'], 'AdjClose': new['adj'] * k})
        cols = ['Date', 'Open', 'Close', 'AdjClose']
        pcols = ('AdjClose', 'Close', 'Open')
        raw_last = float(old['Close'].iloc[-1])
        seam = {'AdjClose': last_a, 'Close': raw_last, 'Open': raw_last}
    else:
        out = pd.DataFrame({'Date': new.index, 'Open': new['open'],
                            'Close': new['adj'] * k,
                            'Volume': new['volume'].fillna(0), 'Raw': new['close']})
        cols = ['Date', 'Open', 'Close', 'Volume', 'Raw']
        pcols = ('Close', 'Open', 'Raw')
        raw_last = float(old['Raw'].iloc[-1])
        seam = {'Close': last_a, 'Open': raw_last, 'Raw': raw_last}
    return append_rows(path, out, cols, price_cols=pcols, prev_date=last_d,
                       max_gap=MAX_KR_GAP_DAYS, prev_values=seam)


def splice_tnx(path, today=None):
    """금리(^TNX)는 수익률이 아니라 **수준**이라 이음 없이 원시 종가를 붙인다."""
    old = read_csv(path)
    last_d = old['Date'].iloc[-1]
    df = chart('^TNX')
    if not _validate_download(path, df, ('open', 'close'), anchor=last_d,
                              max_age_days=MAX_GLOBAL_GAP_DAYS, today=today):
        return 0
    new = df[df.index > last_d]
    if new.empty:
        return _already_current(path)
    out = pd.DataFrame({'Date': new.index, 'Open': new['open'], 'Close': new['close']})
    # 금리는 수준이라 공통 ±30%보다 넓게 보되 무제한 허용하지 않는다.
    # 저장 이력 최대 49.9%에 25%p 여유, 지수 수준 자체는 0.01~30 범위로 이중 방어한다.
    last_close = float(old['Close'].iloc[-1])
    return append_rows(path, out, ['Date', 'Open', 'Close'],
                       price_cols=('Close', 'Open'),
                       prev_values={'Close': last_close, 'Open': last_close},
                       prev_date=last_d, max_move=TNX_MAX_DAILY_MOVE,
                       value_bounds=TNX_VALUE_BOUNDS)


def splice_gold(path, today=None):
    """LBMA 오후 고시는 야후에 없다. GLD 수정주가 **수익률**로 잇는다 (비율 이음과 동일)."""
    old = read_csv(path)
    last_d, last_c = old['Date'].iloc[-1], float(old['Close'].iloc[-1])
    try:
        df = chart('GLD', require_adj=True)
    except Exception as e:
        return _abort_update(
            path, [f'{os.path.basename(path)}: GLD 수정주가 실패 — {type(e).__name__}: {e}'])
    if not _validate_download(path, df, ('adj',), anchor=last_d,
                              max_age_days=MAX_GLOBAL_GAP_DAYS, today=today):
        return 0
    k = last_c / float(df.loc[last_d, 'adj'])
    new = df[df.index > last_d]
    if new.empty:
        return _already_current(path)
    out = pd.DataFrame({'Date': new.index, 'Close': new['adj'] * k})
    return append_rows(path, out, ['Date', 'Close'], price_cols=('Close',), prev=last_c,
                       prev_date=last_d)


def refresh_fx(path, today=None):
    """FRED 공식 CSV에서 **기존 마지막 날 뒤만** 붙인다. 실패 시 Yahoo를 쓴다.

    [보험을 든 이유] 2026-09-02~03 FRED 가 이틀째 타임아웃이었다(urllib·curl 모두). 종전엔 예외 → main 의
    「기존 유지」로만 물러섰는데, 달을 넘겨 계속 죽어 있으면 원화 시나리오의 환율이 조용히 낡는다.
    야후 KRW=X 종가는 DEXKOUS(뉴욕 정오 매입환율)와 고시 시점이 달라 0.1~0.3% 차이가 있으나 ffill 로
    버티는 것보다 낫다. FRED 가 돌아와도 **기존 유효 꼬리와 같은 날까지 따라온 뒤에만**
    새 행을 붙인다. 기존 prefix는 절대 다시 쓰지 않으므로 공식 원본의 수정·누락·오염이
    보관 연구 이력을 바꿀 수 없고, 뒤처진 응답이 Yahoo 보강분을 되감지도 않는다.
    ★ 행 수는 손상 탐지용 10% 여유만 두고, 마지막 유효 날짜는 후퇴를 한 날도 허용하지
      않는다. 두 원본 모두 실행일 기준 신선도 관문(미국계 8일)을 통과해야 한다."""
    try:
        old = pd.read_csv(path)
        if list(old.columns) != ['observation_date', 'DEXKOUS']:
            raise RuntimeError(f'기존 FRED 열이 다름 — {list(old.columns)}')
        n_old = len(old)
        old_last = _fred_last_valid(old)
        old_end = _fred_last_date(old)
    except Exception as e:
        return _abort_update(
            path, [f'{os.path.basename(path)}: 기존 환율 CSV 검증 실패 — '
                   f'{type(e).__name__}: {e}'])
    try:
        # FRED 공식 CSV 경로는 graph(단수)다. graphs는 404라 주경로가 매번 죽고
        # Yahoo 보강만 쓰게 된다 — URL 자체를 회귀검사에서 봉인한다.
        url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode('utf-8', 'replace')
        new, new_last = _validate_fred_payload(path, txt, old, today=today)
        dates = pd.to_datetime(new['observation_date'], errors='coerce')
        values = pd.to_numeric(new['DEXKOUS'], errors='coerce')
        # 값이 비어 있더라도 이미 존재하는 날짜는 기존 prefix의 일부다. 마지막 유효값
        # 뒤가 아니라 마지막 물리 행 뒤만 붙여, FRED가 결측을 사후 보충해도 중복이 없다.
        keep = (dates > old_end) & values.notna()
        add = pd.DataFrame({'Date': dates[keep].to_numpy(),
                            'Close': values[keep].to_numpy()})
        if add.empty:
            cutoff = _normalise_utc_day(today) - pd.Timedelta(days=MAX_GLOBAL_GAP_DAYS)
            if old_last < cutoff:
                # FRED가 기존 trailing 결측을 사후 보충했더라도 prefix 불변 계약상 그
                # 날짜를 덮어쓸 수 없다. 저장 파일의 실제 유효 꼬리가 낡은 채라면
                # "최신"으로 성공시키지 말고 Yahoo의 strict append를 시도한다.
                raise RuntimeError(
                    f'저장 환율의 마지막 유효값이 오래됨 — {old_last.date()} < {cutoff.date()}')
            return _already_current(path)
        old_values = pd.to_numeric(old.iloc[:, 1], errors='coerce').dropna()
        probs = validate_frame(add, os.path.basename(path), ['Close'],
                               # 중복 방지 cutoff는 old_end지만, 값의 실제 공백은 마지막
                               # 유효값부터 센다. trailing 결측 뒤 한 행만 와도 긴 공백을 숨길 수 없다.
                               prev_close=float(old_values.iloc[-1]), prev_date=old_last,
                               max_gap=MAX_GLOBAL_GAP_DAYS)
        if probs:
            return _abort_update(path, probs)
        rows = [(d.date().isoformat(), f'{v:.4f}')
                for d, v in zip(add['Date'], add['Close'])]
        _atomic_append_values(path, rows, ['observation_date', 'DEXKOUS'])
        print(f'  fred_DEXKOUS.csv       FRED로 {len(add)}행 추가 '
              f'({n_old} → {n_old + len(add)}행, ~{new_last.date()})')
        return len(add)
    except Exception as e:
        print(f'  fred_DEXKOUS.csv       [경고] FRED 실패({type(e).__name__}: {e}) — 야후 KRW=X 로 최근 구간 보강',
              file=sys.stderr)
    # ── 보험: 야후 KRW=X (chart() 는 장중 봉을 이미 잘라 준다) ──
    try:
        df = chart('KRW=X', years=1)
    except Exception as e:
        return _abort_update(
            path, [f'{os.path.basename(path)}: FRED와 야후 환율 원본이 모두 실패 — '
                   f'{type(e).__name__}: {e}'])
    if not _validate_download(path, df, ('close',), anchor=old_last,
                               max_age_days=MAX_GLOBAL_GAP_DAYS, today=today):
        return 0
    add = df.loc[df.index > old_end, 'close'].dropna()
    if add.empty:
        cutoff = _normalise_utc_day(today) - pd.Timedelta(days=MAX_GLOBAL_GAP_DAYS)
        if old_last < cutoff:
            return _abort_update(
                path, [f'{os.path.basename(path)}: 저장 환율의 마지막 유효값이 오래됐고 '
                       f'두 원본에도 {old_end.date()} 뒤 새 행이 없다'])
        return _already_current(path)
    candidate = pd.DataFrame({'Date': add.index, 'Close': add.values})
    old_values = pd.to_numeric(old.iloc[:, 1], errors='coerce').dropna()
    prev_close = float(old_values.iloc[-1]) if len(old_values) else None
    probs = validate_frame(candidate, os.path.basename(path), ['Close'],
                           prev_close=prev_close, prev_date=old_last,
                           max_gap=MAX_GLOBAL_GAP_DAYS)
    if probs:
        return _abort_update(path, probs)
    rows = [(d.date().isoformat(), f'{v:.4f}') for d, v in add.items()]
    _atomic_append_values(path, rows, ['observation_date', 'DEXKOUS'])
    print(f'  fred_DEXKOUS.csv       야후 KRW=X 로 {len(add)}행 보강 '
          f'(~{add.index[-1].date()}) — FRED가 이 날짜를 따라오면 그 뒤부터 다시 사용')
    return len(add)


def main():
    if not os.path.exists('qqq_us_d.csv'):
        sys.exit('저장소 루트에서 실행해야 한다: python deploy/refresh_hist.py')
    total = 0
    print('== 미국 3종 (수정주가 비율 이음) ==')
    for p, s in [('qqq_us_d.csv', 'QQQ'), ('qld_us_d.csv', 'QLD'), ('schd_us_d.csv', 'SCHD')]:
        total += splice_us(p, s)
    print('== 보조 시계열 ==')
    total += splice_tnx('data/hist/yahoo_TNX.csv')
    total += splice_gold('data/hist/lbma_gold_pm.csv')
    try:
        total += refresh_fx('data/hist/fred_DEXKOUS.csv')
    except Exception as e:
        _abort_update('data/hist/fred_DEXKOUS.csv',
                      [f'fred_DEXKOUS.csv: 예상 밖 갱신 실패 — {type(e).__name__}: {e}'])
    print('== 한국 실물 + 달력 ==')
    for p, s in [('data/hist/kr__5EKS11.csv', '^KS11'),
                 ('data/hist/kr_133690_KS.csv', '133690.KS'),
                 ('data/hist/kr_418660_KS.csv', '418660.KS'),
                 ('data/hist/kr_458730_KS.csv', '458730.KS'),
                 ('data/hist/kr_305080_KS.csv', '305080.KS'),
                 ('data/hist/kr_411060_KS.csv', '411060.KS')]:
        total += splice_kr(p, s)
    print(f'\n총 추가 {total}행')
    # [2026-09-04 코드리뷰] ★ append_rows 의 docstring 이 「main 이 종료코드 1 로 끝나
    #   workflow 가 build_stats 를 돌리지 않는다(downstream 보호)」고 **약속하는데 그 코드가
    #   없었다.** FAILURES 에 쌓기만 하고 아무도 읽지 않았고, main 은 행 수를 돌려주며
    #   __main__ 은 그 값을 버려 언제나 0 으로 끝났다.
    #   결과: 원자료가 검증에 막혀 옛날 그대로인데 monthly-stats 는 다음 스텝으로 넘어가
    #   build_stats 가 **낡은 입력으로 계산해 새 generated_at 을 찍고 커밋한다.**
    #   그러면 파수꾼 stats 모드(45일 문턱)도 「방금 갱신됨」으로 보므로 **낡음이 보이지
    #   않게 된다** — 조용히 틀린 값을 오래 믿게 되는, 이 저장소가 가장 싫어하는 실패다.
    if FAILURES:
        for ln in ['', f'[실패] 검증에 막혀 갱신하지 못한 파일 {len(FAILURES)}개:',
                   *[f'  · {f}' for f in FAILURES],
                   '기존 데이터는 그대로 있다. 위 [검증실패] 줄을 보고 손으로 확인할 것.',
                   '(이 스텝이 실패하므로 build_stats 는 돌지 않는다 — 낡은 입력으로',
                   ' 새 성과표를 찍어 낡음을 감추는 것을 막는다.)']:
            print(ln, file=sys.stderr)
        return 1
    return 0


def selftest():
    """장중·신선도·이음새·FRED strict append 실패를 파일 경계에서 구별한다."""
    global chart
    real_chart = chart
    real_urlopen = urllib.request.urlopen
    saved_failures = FAILURES[:]

    def tnx_frame(dates):
        idx = pd.to_datetime(dates)
        n = len(idx)
        return pd.DataFrame({'open': [4.0 + i * .1 for i in range(n)],
                             'close': [4.1 + i * .1 for i in range(n)]}, index=idx)

    def file_bytes(path):
        with open(path, 'rb') as f:
            return f.read()

    def fail_replace(src, dst):
        raise OSError('교체 실패 모의')

    try:
        with tempfile.TemporaryDirectory() as td:
            # 장중 가드는 개장 전 전일 확정봉을 지우지 않고, 실제 정규장 진행 중 봉만 뺀다.
            prev_day = pd.Timestamp('2026-09-02')
            live_day = pd.Timestamp('2026-09-03')
            start = int(pd.Timestamp('2026-09-03 13:30', tz='UTC').timestamp())
            end = int(pd.Timestamp('2026-09-03 20:00', tz='UTC').timestamp())
            pre = {'regularMarketTime': int(pd.Timestamp(
                       '2026-09-02 20:00', tz='UTC').timestamp()),
                   'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
            intra = {'regularMarketTime': start + 3600,
                     'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
            post = {'regularMarketTime': end + 60,
                    'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
            one = pd.DataFrame({'close': [1.0]}, index=[prev_day])
            two = pd.DataFrame({'close': [1.0, 1.1]}, index=[prev_day, live_day])
            assert len(_drop_intraday_bar(one, pre)) == 1
            assert len(_drop_intraday_bar(two, intra, now=start + 3600)) == 1
            assert len(_drop_intraday_bar(two, post)) == 2
            # [R2-11] 마감이 지났으면 마지막 체결이 마감 직전(^TNX 18:59)이어도 확정봉이다.
            late = {'regularMarketTime': end - 60,
                    'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
            assert len(_drop_intraday_bar(two, late, now=end + 12 * 3600)) == 2
            assert len(_drop_intraday_bar(two, late, now=end - 30)) == 1
            # FX는 한 현재 세션을 start placeholder와 실시간 quote 두 행으로 줄 수 있다.
            fx_start = int(pd.Timestamp('2026-09-03 23:00', tz='UTC').timestamp())
            fx_qt = int(pd.Timestamp('2026-09-04 12:00', tz='UTC').timestamp())
            fx_end = int(pd.Timestamp('2026-09-04 22:59', tz='UTC').timestamp())
            fx_rows = pd.DataFrame({'close': [1.0, float('nan'), 1.1]}, index=pd.to_datetime(
                ['2026-09-02', '2026-09-03', '2026-09-04']))
            fx_meta = {'regularMarketTime': fx_qt,
                       'currentTradingPeriod': {'regular': {'start': fx_start, 'end': fx_end}}}
            assert len(_drop_intraday_bar(fx_rows, fx_meta, now=fx_qt)) == 1
            try:
                _drop_intraday_bar(two, {})
                raise AssertionError('장중 판정 메타 없는 응답을 허용했다')
            except RuntimeError:
                pass

            path = os.path.join(td, 'tnx.csv')
            base = pd.DataFrame({'Date': ['2026-09-01'], 'Open': [4.0], 'Close': [4.1]})
            base.to_csv(path, index=False)
            original = file_bytes(path)

            # append_rows 자체도 0행을 "최신"으로 우회하지 않고 실패-폐쇄한다.
            FAILURES.clear()
            empty_candidate = pd.DataFrame(columns=['Date', 'Open', 'Close'])
            assert append_rows(path, empty_candidate, ['Date', 'Open', 'Close'],
                               price_cols=('Close', 'Open'), prev_date='2026-09-01') == 0
            assert FAILURES == ['tnx.csv']
            assert file_bytes(path) == original

            # 빈 Yahoo 응답은 실패이며 기존 파일을 그대로 둔다.
            FAILURES.clear()
            chart = lambda symbol, *args, **kwargs: tnx_frame([])
            assert splice_tnx(path, today='2026-09-04') == 0
            assert FAILURES == ['tnx.csv']
            assert file_bytes(path) == original

            # 새 날짜가 있어도 기존 마지막 날(anchor)이 없으면 이어 붙이지 않는다.
            FAILURES.clear()
            chart = lambda symbol, *args, **kwargs: tnx_frame(['2026-09-02', '2026-09-03'])
            assert splice_tnx(path, today='2026-09-04') == 0
            assert FAILURES == ['tnx.csv']
            assert file_bytes(path) == original

            # 정상 원본에 anchor만 있고 뒤 행이 없을 때만 "이미 최신" 성공이다.
            FAILURES.clear()
            chart = lambda symbol, *args, **kwargs: tnx_frame(['2026-09-01'])
            assert splice_tnx(path, today='2026-09-04') == 0
            assert FAILURES == []
            assert file_bytes(path) == original

            # 원본이 anchor까지만 정상 응답해도 그 꼬리 자체가 오래됐으면 성공이 아니다.
            FAILURES.clear()
            chart = lambda symbol, *args, **kwargs: tnx_frame(['2026-09-01'])
            assert splice_tnx(path, today='2026-09-20') == 0
            assert FAILURES == ['tnx.csv']
            assert file_bytes(path) == original

            # 소스가 실행일 뒤의 봉을 주면 신선해 보이더라도 미래 자료라서 막는다.
            FAILURES.clear()
            chart = lambda symbol, *args, **kwargs: tnx_frame(['2026-09-01', '2026-09-05'])
            assert splice_tnx(path, today='2026-09-04') == 0
            assert FAILURES == ['tnx.csv']
            assert file_bytes(path) == original

            # 미국 계열은 한국 장기 연휴용 16일을 공유하지 않는다. 실측 최대 7일을
            # 한 칸 넘긴 8일까지만 허용하고, 9일 이음새는 누락으로 막는다.
            FAILURES.clear()
            chart = lambda symbol, *args, **kwargs: tnx_frame(['2026-09-01', '2026-09-10'])
            assert splice_tnx(path, today='2026-09-10') == 0
            assert FAILURES == ['tnx.csv']
            assert file_bytes(path) == original

            # 정상 anchor와 새 행은 기존 행을 건드리지 않고 한 행만 붙인다.
            FAILURES.clear()
            chart = lambda symbol, *args, **kwargs: tnx_frame(['2026-09-01', '2026-09-02'])
            assert splice_tnx(path, today='2026-09-04') == 1
            assert FAILURES == []
            written = pd.read_csv(path)
            assert len(written) == 2
            assert file_bytes(path).startswith(original)
            assert written.iloc[0].to_dict() == pd.read_csv(io.BytesIO(original)).iloc[0].to_dict()
            assert written['Date'].iloc[-1] == '2026-09-02'

            # 일반 시계열도 기존 행을 pandas로 왕복시키지 않는다. CRLF·숫자 표기와
            # 마지막 개행 유무까지 원본 prefix가 정확히 남고, 새 행만 LF로 붙어야 한다.
            prefix_path = os.path.join(td, 'prefix.csv')
            prefix = b'Date,Open,Close\r\n2026-09-01,4.0000,4.100000'
            _atomic_write_bytes(prefix_path, prefix)
            add_one = pd.DataFrame({'Date': pd.to_datetime(['2026-09-02']),
                                    'Open': [4.2], 'Close': [4.3]})
            _atomic_append_frame(prefix_path, add_one, ['Date', 'Open', 'Close'])
            assert file_bytes(prefix_path) == prefix + b'\n2026-09-02,4.2,4.3\n'

            # 헤더가 다르거나 마지막 교체가 실패하면 성공으로 가장하지 않고 원본 그대로다.
            bad_header = os.path.join(td, 'bad_header.csv')
            bad_header_bytes = b'Date,Close,Open\n2026-09-01,4.1,4.0\n'
            _atomic_write_bytes(bad_header, bad_header_bytes)
            try:
                _atomic_append_frame(bad_header, add_one, ['Date', 'Open', 'Close'])
                raise AssertionError('열 순서가 다른 기존 CSV에 행을 붙였다')
            except RuntimeError:
                pass
            assert file_bytes(bad_header) == bad_header_bytes
            prefix_after = file_bytes(prefix_path)
            try:
                _atomic_append_frame(prefix_path, add_one, ['Date', 'Open', 'Close'],
                                     replace_func=fail_replace)
                raise AssertionError('append 교체 실패를 성공으로 처리했다')
            except OSError:
                pass
            assert file_bytes(prefix_path) == prefix_after

            # TNX의 실제 최대 일변동은 49.9%다. 10배 오염은 금리 예외로도 통과하지 않는다.
            tnx_written = file_bytes(path)
            chart = lambda symbol, *args, **kwargs: pd.DataFrame(
                {'open': [4.1, 40.0], 'close': [4.2, 40.0]},
                index=pd.to_datetime(['2026-09-02', '2026-09-03']))
            FAILURES.clear()
            assert splice_tnx(path, today='2026-09-04') == 0
            assert FAILURES == ['tnx.csv']
            assert file_bytes(path) == tnx_written

            # 수정주가를 못 받은 ETF는 비수정 네이버 일봉으로 영구 오염시키지 않는다.
            etf = os.path.join(td, 'etf.csv')
            pd.DataFrame({'Date': ['2026-09-01'], 'Open': [100.0], 'Close': [100.0],
                          'AdjClose': [100.0]}).to_csv(etf, index=False)
            etf_original = file_bytes(etf)
            chart = lambda symbol, *args, **kwargs: (_ for _ in ()).throw(OSError('Yahoo 중단 모의'))
            FAILURES.clear()
            assert splice_kr(etf, '458730.KS', today='2026-09-04') == 0
            assert FAILURES == ['etf.csv']
            assert file_bytes(etf) == etf_original

            # KOSPI 네이버 fallback도 한국장 중인 오늘 행은 확정 종가로 붙이지 않는다.
            import kr_sources
            real_kr_history = kr_sources.history_df
            kospi = os.path.join(td, 'kospi.csv')
            pd.DataFrame({'Date': ['2026-09-01'], 'Open': [100.0], 'Close': [100.0],
                          'AdjClose': [100.0]}).to_csv(kospi, index=False)
            kospi_original = file_bytes(kospi)
            try:
                kr_sources.history_df = lambda *args, **kwargs: pd.DataFrame(
                    {'open': [100.0, 101.0], 'close': [100.0, 101.0],
                     'adj': [100.0, 101.0], 'volume': [1000, 1000]},
                    index=pd.to_datetime(['2026-09-01', '2026-09-02']))
                FAILURES.clear()
                assert splice_kr(kospi, '^KS11', today='2026-09-02',
                                 now='2026-09-02 10:00+09:00') == 0
                assert FAILURES == [] and file_bytes(kospi) == kospi_original
            finally:
                kr_sources.history_df = real_kr_history

            # FRED의 공식 결측(.)은 허용하지만, 날짜/비결측 값은 모두 검증한다.
            fx = os.path.join(td, 'fred.csv')
            fx_text = ('observation_date,DEXKOUS\n'
                       '2026-08-31,1380.0\n'
                       '2026-09-01,.\n'
                       '2026-09-02,1382.5\n')
            _atomic_write_text(fx, fx_text)
            fx_old = pd.read_csv(fx)
            parsed, last = _validate_fred_payload(
                fx, fx_text, fx_old, today='2026-09-04')
            assert len(parsed) == 3 and last == pd.Timestamp('2026-09-02')

            # 기존 FRED 파일의 두 열 이름·순서가 틀리면 숫자가 그럴듯해도 다른 뜻의
            # 열 끝에 날짜·환율을 붙이지 않는다. 공급원 fallback 전에 대상부터 닫는다.
            bad_fx = os.path.join(td, 'bad_fx.csv')
            bad_fx_text = 'DEXKOUS,observation_date\n1380.0,2026-09-01\n'
            _atomic_write_text(bad_fx, bad_fx_text)
            bad_fx_original = file_bytes(bad_fx)
            FAILURES.clear()
            assert refresh_fx(bad_fx, today='2026-09-04') == 0
            assert FAILURES == ['bad_fx.csv']
            assert file_bytes(bad_fx) == bad_fx_original

            # HTTP 200이어도 기존 Yahoo 보강 꼬리보다 하루라도 뒤면 교체하지 않는다.
            regressed_text = ('observation_date,DEXKOUS\n'
                              '2026-08-30,1379.0\n'
                              '2026-08-31,1380.0\n'
                              '2026-09-01,1381.0\n')
            try:
                _validate_fred_payload(
                    fx, regressed_text, fx_old, today='2026-09-04')
                raise AssertionError('기존 꼬리보다 뒤처진 FRED 응답을 허용했다')
            except RuntimeError:
                pass

            future_text = fx_text.replace('2026-09-02,1382.5', '2026-09-05,1382.5')
            try:
                _validate_fred_payload(
                    fx, future_text, fx_old, today='2026-09-04')
                raise AssertionError('미래 FRED 행을 허용했다')
            except RuntimeError:
                pass

            # 마지막 날짜가 기존과 같아도 실행일 기준으로 낡았으면 성공이 아니다.
            try:
                _validate_fred_payload(
                    fx, fx_text, fx_old, today='2026-09-20')
                raise AssertionError('절대 신선도를 넘긴 FRED 응답을 허용했다')
            except RuntimeError:
                pass

            # 형식상 CSV여도 비수치 환율이면 교체 전에 막아 원본을 보존한다.
            fx_original = file_bytes(fx)
            bad_text = fx_text.replace('1382.5', '오염')
            try:
                _validate_fred_payload(
                    fx, bad_text, fx_old, today='2026-09-04')
                raise AssertionError('오염 FRED 응답을 허용했다')
            except RuntimeError:
                pass
            assert file_bytes(fx) == fx_original

            # 임시파일 기록 뒤 교체가 실패해도 기존 파일은 바뀌지 않는다.
            try:
                _atomic_write_text(fx, fx_text.replace('1382.5', '1399.9'),
                                   replace_func=fail_replace)
                raise AssertionError('교체 실패를 성공으로 처리했다')
            except OSError:
                pass
            assert file_bytes(fx) == fx_original

            # 뒤처진 FRED는 기존 파일을 덮지 않고 Yahoo의 더 최신 행으로 보강한다.
            class FakeResponse:
                def __init__(self, body):
                    self.body = body.encode('utf-8')

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return self.body

            # 환율 raw 경로에는 휴장일 timestamp의 OHLC 전체-null placeholder가 실제로
            # 섞인다. 그 행만 제거하되 값이 일부 든 불완전 봉은 허용하지 않는다.
            ts = int(pd.Timestamp('2026-09-02 20:00', tz='UTC').timestamp())
            closed_meta = {'regularMarketTime': end + 60,
                           'currentTradingPeriod': {'regular': {'start': start, 'end': end}}}
            raw_quote = {k: [None, v] for k, v in {
                'open': 100.0, 'high': 101.0, 'low': 99.0,
                'close': 100.5, 'volume': 1000}.items()}
            raw_payload = {'chart': {'result': [{
                'timestamp': [ts - 86400, ts], 'indicators': {'quote': [raw_quote]},
                'meta': closed_meta}]}}
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(json.dumps(raw_payload))
            raw_df = real_chart('KRW=X')
            assert len(raw_df) == 1 and float(raw_df['close'].iloc[0]) == 100.5
            adj_payload = {'chart': {'result': [{
                'timestamp': [ts - 86400, ts],
                'indicators': {'quote': [raw_quote],
                               'adjclose': [{'adjclose': [None, 100.25]}]},
                'meta': closed_meta}]}}
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(json.dumps(adj_payload))
            adj_df = real_chart('418660.KS', require_adj=True)
            assert len(adj_df) == 1 and float(adj_df['adj'].iloc[0]) == 100.25
            # [R2-12] FX 봉 라벨은 거래소 시간대(런던) 달력일이다. 서머타임엔 전날 23:00 UTC
            #   시작 봉이 다음 날 세션이라, UTC 로 자르면 금요일 세션이 목요일이 되어 FRED 꼬리를 못 잇는다.
            fx_stamps = [int(pd.Timestamp(d, tz='UTC').timestamp()) for d in
                         ('2026-08-23 23:00', '2026-08-24 23:00', '2026-08-25 23:00',
                          '2026-08-26 23:00', '2026-08-27 23:00')]
            fx_quote = {k: [1380.0, 1381.0, 1382.0, 1383.0, 1384.0]
                        for k in ('open', 'high', 'low', 'close')}
            fx_quote['volume'] = [0] * 5
            fx_end = int(pd.Timestamp('2026-08-28 22:59', tz='UTC').timestamp())
            fx_payload = {'chart': {'result': [{
                'timestamp': fx_stamps, 'indicators': {'quote': [fx_quote]},
                'meta': {'regularMarketTime': fx_end, 'exchangeTimezoneName': 'Europe/London',
                         'currentTradingPeriod': {'regular': {
                             'start': int(pd.Timestamp('2026-08-27 23:00', tz='UTC').timestamp()),
                             'end': fx_end}}}}]}}
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(json.dumps(fx_payload))
            fx_df = real_chart('KRW=X')
            assert [d.isoformat() for d in fx_df.index.date] == [
                '2026-08-24', '2026-08-25', '2026-08-26', '2026-08-27', '2026-08-28']
            partial_quote = dict(raw_quote)
            partial_quote['open'] = [99.0, 100.0]
            partial_payload = {'chart': {'result': [{
                'timestamp': [ts - 86400, ts], 'indicators': {'quote': [partial_quote]},
                'meta': closed_meta}]}}
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(json.dumps(partial_payload))
            try:
                real_chart('KRW=X')
                raise AssertionError('일부 값만 든 결측 raw 봉을 허용했다')
            except RuntimeError:
                pass
            garbage_quote = {k: ['garbage', v] for k, v in {
                'open': 100.0, 'high': 101.0, 'low': 99.0,
                'close': 100.5, 'volume': 1000}.items()}
            garbage_payload = {'chart': {'result': [{
                'timestamp': [ts - 86400, ts], 'indicators': {'quote': [garbage_quote]},
                'meta': closed_meta}]}}
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(json.dumps(garbage_payload))
            try:
                real_chart('KRW=X')
                raise AssertionError('비수치 오염 행을 빈 휴장행으로 삭제했다')
            except RuntimeError:
                pass

            # 배당 자산은 adjclose가 없을 때 raw close로 조용히 대체하지 않는다.
            quote = {'open': [100.0], 'high': [101.0], 'low': [98.0],
                     'close': [99.0], 'volume': [1000]}
            quote_only = {'chart': {'result': [{'timestamp': [ts],
                           'indicators': {'quote': [quote]}, 'meta': closed_meta}]}}
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(json.dumps(quote_only))
            us = os.path.join(td, 'schd.csv')
            pd.DataFrame({'Date': ['2026-09-01'], 'Open': [100.0], 'High': [100.0],
                          'Low': [100.0], 'Close': [100.0], 'Volume': [1000]}).to_csv(us, index=False)
            us_original = file_bytes(us)
            chart = real_chart
            FAILURES.clear()
            assert splice_us(us, 'SCHD', today='2026-09-04') == 0
            assert FAILURES == ['schd.csv'] and file_bytes(us) == us_original

            # 중복/역순 날짜를 keep-last+sort로 정리한 뒤 검증하지 않는다. 원본 자체를 거부한다.
            dup_quote = {k: [v[0], v[0], v[0] if k != 'close' else 102.0]
                         for k, v in quote.items()}
            dup_quote['close'] = [100.0, 101.0, 102.0]
            dup_payload = {'chart': {'result': [{
                'timestamp': [ts - 86400, ts, ts], 'indicators': {
                    'quote': [dup_quote], 'adjclose': [{'adjclose': [100.0, 101.0, 102.0]}]},
                'meta': closed_meta}]}}
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(json.dumps(dup_payload))
            FAILURES.clear()
            assert splice_us(us, 'SCHD', today='2026-09-04') == 0
            assert FAILURES == ['schd.csv'] and file_bytes(us) == us_original

            # adjclose가 있어도 장중 판정 메타가 빠진 HTTP 200은 미완성 오늘 봉일 수 있다.
            no_meta = {'chart': {'result': [{'timestamp': [ts],
                       'indicators': {'quote': [quote],
                                      'adjclose': [{'adjclose': [99.0]}]}, 'meta': {}}]}}
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(json.dumps(no_meta))
            FAILURES.clear()
            assert splice_us(us, 'SCHD', today='2026-09-04') == 0
            assert FAILURES == ['schd.csv'] and file_bytes(us) == us_original

            # 열 이름만 있고 High/Low가 비어 있는 수정주가 응답도 root OHLCV에 못 들어간다.
            chart = lambda symbol, *args, **kwargs: pd.DataFrame(
                {'open': [100.0, 100.0], 'high': [101.0, float('nan')],
                 'low': [99.0, float('nan')], 'close': [100.0, 101.0],
                 'adj': [100.0, 101.0], 'volume': [1000, 1000]},
                index=pd.to_datetime(['2026-09-01', '2026-09-02']))
            FAILURES.clear()
            assert splice_us(us, 'SCHD', today='2026-09-04') == 0
            assert FAILURES == ['schd.csv'] and file_bytes(us) == us_original

            # 새 구간이 한 행뿐이어도 KR raw Open은 기존 raw Close와 이음 검사를 받는다.
            kr_seam = os.path.join(td, 'kr_seam.csv')
            pd.DataFrame({'Date': ['2026-09-01'], 'Open': [100.0], 'Close': [100.0],
                          'AdjClose': [100.0]}).to_csv(kr_seam, index=False)
            kr_original = file_bytes(kr_seam)
            chart = lambda symbol, *args, **kwargs: pd.DataFrame(
                {'open': [100.0, 1000.0], 'close': [100.0, 101.0],
                 'adj': [100.0, 101.0], 'volume': [1000, 1000]},
                index=pd.to_datetime(['2026-09-01', '2026-09-02']))
            FAILURES.clear()
            assert splice_kr(kr_seam, '458730.KS', today='2026-09-04') == 0
            assert FAILURES == ['kr_seam.csv'] and file_bytes(kr_seam) == kr_original

            # FRED가 과거 값을 바꾸거나 날짜를 빠뜨려도 기존 prefix는 바이트 단위로 보존하고
            # 새 날짜만 붙인다. 보관 수치가 원본 공급자의 사후 수정에 흔들리지 않는다.
            advanced_text = ('observation_date,DEXKOUS\n'
                             '2026-08-31,1600.0\n'
                             '2026-09-02,1382.5\n'
                             '2026-09-03,1384.0\n')
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(advanced_text)
            FAILURES.clear()
            assert refresh_fx(fx, today='2026-09-04') == 1
            assert FAILURES == []
            assert file_bytes(fx).startswith(fx_original)
            assert pd.read_csv(fx).iloc[-1, 0] == '2026-09-03'

            # 기존 파일 끝에 결측 날짜가 있으면 마지막 유효값이 아니라 마지막 물리 날짜
            # 뒤만 붙인다. FRED가 그 값을 나중에 채워도 기존 행을 덮거나 중복하지 않는다.
            trailing_text = ('observation_date,DEXKOUS\n'
                             '2026-08-31,1380.0\n'
                             '2026-09-01,.\n'
                             '2026-09-02,.\n')
            _atomic_write_text(fx, trailing_text)
            trailing_original = file_bytes(fx)
            fill_text = ('observation_date,DEXKOUS\n'
                         '2026-08-31,1380.0\n'
                         '2026-09-01,1381.0\n'
                         '2026-09-02,1382.0\n'
                         '2026-09-03,1383.0\n')
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(fill_text)
            FAILURES.clear()
            assert refresh_fx(fx, today='2026-09-04') == 1
            trailing_written = pd.read_csv(fx)
            assert FAILURES == []
            assert file_bytes(fx).startswith(trailing_original)
            assert not trailing_written.iloc[:, 0].duplicated().any()
            assert trailing_written.iloc[:, 0].tolist() == [
                '2026-08-31', '2026-09-01', '2026-09-02', '2026-09-03']

            # 물리 날짜만 최신이고 유효값이 오래된 파일은, FRED가 빈칸을 사후 보충해도
            # prefix 불변 때문에 그대로 쓸 수 없다. 새 날짜가 없으면 성공으로 숨기지 않는다.
            stale_tail = ('observation_date,DEXKOUS\n'
                          '2026-08-20,1380.0\n'
                          '2026-08-27,.\n'
                          '2026-09-03,.\n')
            _atomic_write_text(fx, stale_tail)
            stale_original = file_bytes(fx)
            filled_tail = ('observation_date,DEXKOUS\n'
                           '2026-08-20,1380.0\n'
                           '2026-08-27,1381.0\n'
                           '2026-09-03,1382.0\n')
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(filled_tail)
            chart = lambda *args, **kwargs: pd.DataFrame(
                {'close': [1380.0, 1382.0]},
                index=pd.to_datetime(['2026-08-20', '2026-09-03']))
            FAILURES.clear()
            assert refresh_fx(fx, today='2026-09-04') == 0
            assert FAILURES == ['fred.csv']
            assert file_bytes(fx) == stale_original

            # 새 날짜 한 행이 와도 마지막 유효값부터의 15일 공백은 old_end 기준으로
            # 축소하지 않는다. append cutoff와 유효값 공백 기준은 서로 다르다.
            filled_plus = filled_tail + '2026-09-04,1383.0\n'
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(filled_plus)
            FAILURES.clear()
            assert refresh_fx(fx, today='2026-09-04') == 0
            assert FAILURES == ['fred.csv']
            assert file_bytes(fx) == stale_original

            _atomic_write_text(fx, fx_text)
            fx_original = file_bytes(fx)

            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(regressed_text)
            chart = lambda *args, **kwargs: pd.DataFrame(
                {'close': [1382.5, 1384.0]},
                index=pd.to_datetime(['2026-09-02', '2026-09-03']))
            FAILURES.clear()
            assert refresh_fx(fx, today='2026-09-04') == 1
            assert FAILURES == []
            fallback_written = pd.read_csv(fx)
            assert fallback_written.iloc[:-1, 0].tolist() == fx_old.iloc[:, 0].tolist()
            assert fallback_written.iloc[-1, 0] == '2026-09-03'

            # 두 원본이 HTTP 200이어도 모두 낡으면 실패하고 기존 파일을 보존한다.
            _atomic_write_text(fx, fx_text)
            fx_original = file_bytes(fx)
            urllib.request.urlopen = lambda *args, **kwargs: FakeResponse(fx_text)
            chart = lambda *args, **kwargs: pd.DataFrame(
                {'close': [1382.5]}, index=pd.to_datetime(['2026-09-02']))
            FAILURES.clear()
            assert refresh_fx(fx, today='2026-09-20') == 0
            assert FAILURES == ['fred.csv']
            assert file_bytes(fx) == fx_original

            # 두 공급원이 함께 죽으면 기존 파일은 보존하되 전체 갱신은 실패로 올린다.
            def fail_urlopen(*args, **kwargs):
                raise OSError('FRED 중단 모의')
            def fail_chart(*args, **kwargs):
                raise OSError('Yahoo 중단 모의')
            urllib.request.urlopen = fail_urlopen
            chart = fail_chart
            FAILURES.clear()
            assert refresh_fx(fx, today='2026-09-04') == 0
            assert FAILURES == ['fred.csv']
            assert file_bytes(fx) == fx_original
    finally:
        chart = real_chart
        urllib.request.urlopen = real_urlopen
        FAILURES[:] = saved_failures
    print('refresh_hist selftest: PASS (장중/미래 · anchor/신선도 · TNX/ETF 경계 · FRED append-only/후퇴 방지 · 이중 원본 실패)')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        sys.exit(main())
