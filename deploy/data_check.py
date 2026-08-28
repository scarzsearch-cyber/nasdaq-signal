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
MAX_GAP_DAYS = 12              # 달력일 기준 최대 공백 (추석+주말도 7일 안쪽)


def validate_frame(df, name, price_cols, date_col='Date', prev_close=None,
                   max_move=MAX_DAILY_MOVE, max_gap=MAX_GAP_DAYS, allow_move_cols=()):
    """붙이려는 새 구간(df)을 검사한다.

    price_cols : 0 이하·결측을 검사할 가격 열들
    prev_close : 이음새 검사용 — 기존 파일의 마지막 종가 (첫 새 행과의 변동도 검사)
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
    gaps = d.diff().dt.days.dropna()
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
        if prev_close is not None and c == price_cols[0]:
            seq = np.concatenate([[float(prev_close)], seq])   # 이음새 포함
        r = np.abs(np.diff(seq) / seq[:-1])
        if len(r) and np.nanmax(r) > max_move:
            i = int(np.nanargmax(r))
            probs.append(f'{name}.{c}: 일간 변동 {np.nanmax(r)*100:.1f}% > {max_move*100:.0f}% '
                         f'({df[date_col].iloc[min(i, len(df)-1)]})')
    return probs
