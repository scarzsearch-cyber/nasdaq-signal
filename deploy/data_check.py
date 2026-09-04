# -*- coding: utf-8 -*-
"""[v73] 데이터 검증 게이트 — 갱신 파이프라인이 이상 데이터로 정상 데이터를
덮어쓰는 것을 막는다. refresh_hist.py 가 **파일에 쓰기 전에** 호출한다.

검사 항목 (요구 사양 그대로):
  결측치 / 중복 날짜 / 날짜 순서 이상 / 0 이하 가격 / 전일 대비 ±30% 초과 변동 /
  비정상 데이터 공백 / 핵심 열 누락

반환: 문제 목록(list[str]). 비어 있으면 통과.
실패 처리 방침은 호출자(refresh_hist)가 갖는다: 해당 파일 갱신 중단 + 기존 유지 +
로그 + 종료코드 1 (workflow 가 build_stats 를 아예 안 돌리므로 downstream 도 보호).
"""
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

MAX_DAILY_MOVE = 0.30          # 전일 대비 ±30%
# [코드리뷰 2026-09-04] 종전 12일 + 주석 '추석+주말도 7일 안쪽' 은 둘 다 틀렸다.
#   실측: kr__5EKS11.csv 의 최대 공백은 **11일**(2017-09-29 -> 2017-10-10,
#   추석+임시공휴일 10/2+개천절+한글날). 즉 여유가 1일뿐이라 임시공휴일이 하나만
#   더 끼면 게이트가 오경보로 월간 갱신을 통째로 멈춘다. 진짜 잡아야 할 것은
#   '한 달이 통째로 빈 구멍'(30일+)이므로 16 이면 오경보 없이 그것을 잡는다.
MAX_GAP_DAYS = 16              # 달력일 기준 최대 공백 (실측 최대 11일 + 여유)


def validate_frame(df, name, price_cols, date_col='Date', prev_close=None,
                   max_move=MAX_DAILY_MOVE, max_gap=MAX_GAP_DAYS, allow_move_cols=(),
                   prev_date=None, value_bounds=None, prev_values=None,
                   ohlc_cols=None):
    """붙이려는 새 구간(df)을 검사한다.

    price_cols : 0 이하·결측을 검사할 가격 열들
    prev_close : 이음새 검사용 - 기존 파일의 마지막 종가 (첫 새 행과의 변동도 검사)
    prev_values: 열별 이음새 기준값. 예: 새 Open/High/Low도 기존 Close와 대조한다.
    prev_date  : 이음새 검사용 - 기존 파일의 마지막 날짜. [코드리뷰 2026-09-04]
                 없으면 공백 검사가 **새 구간 안**만 본다. 정작 append 가 만드는
                 유일한 이음새(기존 끝 -> 첫 새 행)를 못 봐서, 그 자리에 몇 달짜리
                 구멍이 있어도 통과했다 (splice_tnx 가 실제 경로다).
    allow_move_cols : ±30% 검사에서 제외할 열 (예: 금리처럼 수준 변동이 큰 것)
    value_bounds : 열별 절대 허용범위 ``{'Close': (하한, 상한)}``. 금리처럼
                   비율 변화 한도만 넓혀야 하는 자료의 10배 오염을 별도로 막는다.
    ohlc_cols : ``(Open, High, Low, Close)`` 열 이름. 봉 내부 고저 관계도 검사한다.
    """
    probs = []
    if df is None:
        return [f'{name}: 입력 표가 없다 — 다운로드 실패 여부 확인 필요']
    if len(df) == 0:
        # 빈 다운로드와 "필터 뒤 새 행 0개"는 호출자가 구분해야 한다. 검증기 자체는
        # 원천을 알 수 없으므로 0행 입력을 정상으로 추정하지 않고 실패-폐쇄한다.
        return [f'{name}: 행이 0개다 — 빈 다운로드 여부 확인 필요']
    for c in [date_col] + list(price_cols):
        if c not in df.columns:
            probs.append(f'{name}: 핵심 열 누락 — {c}')
    if probs:
        return probs
    # utc=True 는 입력이 naive/aware 로 섞여도 비교가 object dtype 으로 무너지는 것을
    # 막는다. 이 게이트가 재는 것은 시각이 아니라 일간 행의 순서와 간격이다.
    d = pd.to_datetime(df[date_col], errors='coerce', utc=True)
    if d.isna().any():
        probs.append(f'{name}: 날짜 결측 {int(d.isna().sum())}건')
    if d.duplicated().any():
        probs.append(f'{name}: 중복 날짜 {int(d.duplicated().sum())}건')
    valid_d = d.dropna().reset_index(drop=True)
    days = valid_d.dt.normalize()
    if not valid_d.equals(days):
        probs.append(f'{name}: 일간 날짜에 시각이 포함됨')
    if days.duplicated().any() and not d.duplicated().any():
        probs.append(f'{name}: 같은 날짜가 여러 시각으로 중복됨 '
                     f'{int(days.duplicated().sum())}건')
    if not days.is_monotonic_increasing:
        probs.append(f'{name}: 날짜 순서 역전')
    dchk = days
    if prev_date is not None:
        prev_ts = pd.to_datetime(prev_date, errors='coerce', utc=True)
        if pd.isna(prev_ts):
            probs.append(f'{name}: 기존 마지막 날짜가 잘못됨 — {prev_date}')
        elif prev_ts != prev_ts.normalize():
            probs.append(f'{name}: 기존 마지막 날짜에 시각이 포함됨 — {prev_date}')
        elif len(days):
            if days.iloc[0] <= prev_ts:
                probs.append(f'{name}: 새 구간 첫 날짜가 기존 끝보다 늦지 않음 '
                             f'({df[date_col].iloc[0]} <= {prev_date})')
            dchk = pd.concat([pd.Series([prev_ts]), days], ignore_index=True)
    gaps = dchk.diff().dt.days.dropna()
    if len(gaps) and gaps.max() > max_gap:
        probs.append(f'{name}: 데이터 공백 {int(gaps.max())}일 (허용 {max_gap}일)')
    for c in price_cols:
        v = pd.to_numeric(df[c], errors='coerce')
        bad = v.isna() | ~np.isfinite(v.astype(float))
        if bad.any():
            probs.append(f'{name}.{c}: 결측/비수치/무한대 {int(bad.sum())}건')
            continue
        if (v <= 0).any():
            probs.append(f'{name}.{c}: 0 이하 값 {int((v <= 0).sum())}건')
        if value_bounds and c in value_bounds:
            lo, hi = value_bounds[c]
            outside = (v < lo) | (v > hi)
            if outside.any():
                probs.append(f'{name}.{c}: 절대 범위 밖 {int(outside.sum())}건 '
                             f'(허용 {lo:g}~{hi:g})')
        if c in allow_move_cols:
            continue
        seq = v.values
        # [코드리뷰 2026-09-04] r[i] 는 seq[i] -> seq[i+1] 로 들어오는 변동이다.
        #   prev_close 를 앞에 붙인 열은 seq 가 한 칸 밀려 r[i] 가 df 의 i 행이 되지만,
        #   안 붙인 열(= price_cols[0] 이 아닌 전부)은 df 의 **i+1** 행이다.
        #   종전에는 둘 다 i 행을 찍어 조사자를 하루 앞 날짜로 보냈다.
        base = 1
        prior_value = None
        if prev_values is not None and c in prev_values:
            prior_value = prev_values[c]
        elif prev_close is not None and c == price_cols[0]:
            prior_value = prev_close
        if prior_value is not None:
            try:
                prior = float(prior_value)
            except (TypeError, ValueError):
                prior = float('nan')
            if not np.isfinite(prior) or prior <= 0:
                probs.append(f'{name}.{c}: 기존 마지막 값이 유효하지 않음')
                continue
            seq = np.concatenate([[prior], seq])   # 이음새 포함
            base = 0
        r = np.abs(np.diff(seq) / seq[:-1])
        if len(r) and np.nanmax(r) > max_move:
            i = int(np.nanargmax(r))
            probs.append(f'{name}.{c}: 일간 변동 {np.nanmax(r)*100:.1f}% > {max_move*100:.0f}% '
                         f'({df[date_col].iloc[i + base]})')
    if ohlc_cols is not None:
        op, hi, lo, cl = ohlc_cols
        if not all(c in df.columns for c in ohlc_cols):
            probs.append(f'{name}: OHLC 관계 검사 열 누락')
        else:
            vals = [pd.to_numeric(df[c], errors='coerce') for c in ohlc_cols]
            if not any(v.isna().any() for v in vals):
                o, h, l, c = vals
                bad = (l > pd.concat([o, c], axis=1).min(axis=1)) | \
                      (h < pd.concat([o, c], axis=1).max(axis=1)) | (l > h)
                if bad.any():
                    probs.append(f'{name}: OHLC 고저 관계 위반 {int(bad.sum())}건')
    return probs


def selftest():
    clean = pd.DataFrame({'Date': ['2026-09-01', '2026-09-02'],
                          'Close': [100.0, 101.0], 'Open': [99.0, 100.0]})
    assert validate_frame(clean, 'clean', ['Close', 'Open'],
                          prev_close=99.0, prev_date='2026-08-31') == []

    empty = pd.DataFrame(columns=['Date', 'Close'])
    assert any('행이 0개' in p for p in validate_frame(empty, 'empty', ['Close']))

    overlap = validate_frame(clean.iloc[:1], 'overlap', ['Close'],
                             prev_close=100.0, prev_date='2026-09-01')
    assert any('늦지 않음' in p for p in overlap)

    nonfinite = clean.iloc[:1].copy()
    nonfinite.loc[nonfinite.index[0], 'Close'] = np.inf
    assert any('무한대' in p for p in validate_frame(nonfinite, 'inf', ['Close']))

    bad_date = clean.iloc[:1].copy()
    bad_date.loc[bad_date.index[0], 'Date'] = 'not-a-date'
    assert any('날짜 결측' in p for p in validate_frame(bad_date, 'date', ['Close']))

    intraday = pd.DataFrame({'Date': ['2026-09-01 10:00', '2026-09-01 11:00'],
                             'Close': [100.0, 101.0]})
    intraday_probs = validate_frame(intraday, 'intraday', ['Close'])
    assert any('시각이 포함됨' in p for p in intraday_probs)
    assert any('여러 시각으로 중복' in p for p in intraday_probs)

    seam = validate_frame(clean.iloc[:1], 'gap', ['Close'], prev_close=100.0,
                          prev_date='2026-07-01', max_gap=16)
    assert any('데이터 공백' in p for p in seam)
    bounded = validate_frame(clean.iloc[:1], 'bounded', ['Close'],
                             value_bounds={'Close': (0.01, 30.0)})
    assert any('절대 범위 밖' in p for p in bounded)
    one_row_seam = validate_frame(
        pd.DataFrame({'Date': ['2026-09-01'], 'Close': [101.0], 'Open': [1000.0]}),
        'per-column', ['Close', 'Open'], prev_date='2026-08-31',
        prev_values={'Close': 100.0, 'Open': 100.0})
    assert any('.Open: 일간 변동' in p for p in one_row_seam)
    bad_bar = pd.DataFrame({'Date': ['2026-09-01'], 'Open': [100.0],
                            'High': [99.0], 'Low': [98.0], 'Close': [101.0]})
    assert any('OHLC 고저 관계' in p for p in validate_frame(
        bad_bar, 'ohlc', ['Open', 'High', 'Low', 'Close'],
        ohlc_cols=('Open', 'High', 'Low', 'Close')))
    print('data_check selftest: PASS (이음새·열별 기준 · 비유한 값 · 날짜 · 절대범위·OHLC)')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        raise SystemExit('직접 실행은 --selftest 만 지원한다')
