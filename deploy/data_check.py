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
import numpy as np
import pandas as pd

MAX_DAILY_MOVE = 0.30          # 전일 대비 ±30%
# [코드리뷰 2026-09-04] 종전 12일 + 주석 '추석+주말도 7일 안쪽' 은 둘 다 틀렸다.
#   실측: kr__5EKS11.csv 의 최대 공백은 **11일**(2017-09-29 -> 2017-10-10,
#   추석+임시공휴일 10/2+개천절+한글날). 즉 여유가 1일뿐이라 임시공휴일이 하나만
#   더 끼면 게이트가 오경보로 월간 갱신을 통째로 멈춘다. 진짜 잡아야 할 것은
#   '한 달이 통째로 빈 구멍'(30일+)이므로 16 이면 오경보 없이 그것을 잡는다.
MAX_GAP_DAYS = 16              # 달력일 기준 최대 공백 (실측 최대 11일 + 여유)


def validate_frame(df, name, price_cols, date_col='Date', prev_close=None,
                   max_move=MAX_DAILY_MOVE, max_gap=MAX_GAP_DAYS, allow_move_cols=(),
                   prev_date=None):
    """붙이려는 새 구간(df)을 검사한다.

    price_cols : 0 이하·결측을 검사할 가격 열들
    prev_close : 이음새 검사용 - 기존 파일의 마지막 종가 (첫 새 행과의 변동도 검사)
    prev_date  : 이음새 검사용 - 기존 파일의 마지막 날짜. [코드리뷰 2026-09-04]
                 없으면 공백 검사가 **새 구간 안**만 본다. 정작 append 가 만드는
                 유일한 이음새(기존 끝 -> 첫 새 행)를 못 봐서, 그 자리에 몇 달짜리
                 구멍이 있어도 통과했다 (splice_tnx 가 실제 경로다).
    allow_move_cols : ±30% 검사에서 제외할 열 (예: 금리처럼 수준 변동이 큰 것)
    """
    probs = []
    if df is None or len(df) == 0:
        return probs                       # 붙일 게 없으면 통과 (갱신 0행)
    for c in [date_col] + list(price_cols):
        if c not in df.columns:
            probs.append(f'{name}: 핵심 열 누락 — {c}')
    if probs:
        return probs
    d = pd.to_datetime(df[date_col])
    if d.isna().any():
        probs.append(f'{name}: 날짜 결측 {int(d.isna().sum())}건')
    if d.duplicated().any():
        probs.append(f'{name}: 중복 날짜 {int(d.duplicated().sum())}건')
    if not d.is_monotonic_increasing:
        probs.append(f'{name}: 날짜 순서 역전')
    dchk = d if prev_date is None else pd.concat(
        [pd.Series([pd.Timestamp(prev_date)]), d], ignore_index=True)
    gaps = dchk.diff().dt.days.dropna()
    if len(gaps) and gaps.max() > max_gap:
        probs.append(f'{name}: 데이터 공백 {int(gaps.max())}일 (허용 {max_gap}일)')
    for c in price_cols:
        v = pd.to_numeric(df[c], errors='coerce')
        if v.isna().any():
            probs.append(f'{name}.{c}: 결측/비수치 {int(v.isna().sum())}건')
            continue
        if (v <= 0).any():
            probs.append(f'{name}.{c}: 0 이하 값 {int((v <= 0).sum())}건')
        if c in allow_move_cols:
            continue
        seq = v.values
        # [코드리뷰 2026-09-04] r[i] 는 seq[i] -> seq[i+1] 로 들어오는 변동이다.
        #   prev_close 를 앞에 붙인 열은 seq 가 한 칸 밀려 r[i] 가 df 의 i 행이 되지만,
        #   안 붙인 열(= price_cols[0] 이 아닌 전부)은 df 의 **i+1** 행이다.
        #   종전에는 둘 다 i 행을 찍어 조사자를 하루 앞 날짜로 보냈다.
        base = 1
        if prev_close is not None and c == price_cols[0]:
            seq = np.concatenate([[float(prev_close)], seq])   # 이음새 포함
            base = 0
        r = np.abs(np.diff(seq) / seq[:-1])
        if len(r) and np.nanmax(r) > max_move:
            i = int(np.nanargmax(r))
            probs.append(f'{name}.{c}: 일간 변동 {np.nanmax(r)*100:.1f}% > {max_move*100:.0f}% '
                         f'({df[date_col].iloc[i + base]})')
    return probs
