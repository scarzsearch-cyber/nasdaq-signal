# -*- coding: utf-8 -*-
"""
[v88] 최종 검증 — B 동결 상태의 실전 안정성 · 비용 스트레스 · T4 그림자 채점 템플릿

소유자 지시 (2026-08-30): "새 전략을 채굴하지 말고, 현재 전략이 실제로 신뢰할 수
있는지 검증하라. 성공 조건은 더 높은 CAGR 이 아니라 «B 를 유지해도 되는 충분한
근거가 있는가»를 편향 없이 확인하는 것이다."

[룰 준수 선언] 파라미터 재최적화 없음 · 신규 후보 없음 · 관문 사후 신설 없음.
  채택안·freeze.json·oos_log.csv·nav_history.csv 무수정. B 는 이미 동결돼 있다
  (2026-08-27, I11 이 매 push 감시). 성숙 전 그림자 장부는 판단에 쓰지 않는다 —
  아래 T4 분석은 전부 동결 이전 54.5년 체인이며, **미래 그림자 기록을 같은 방식으로
  채점하기 위한 사전 등록 템플릿**이다.

[★ 판정 기준 — 실행 전 고정]
  J1 (B 비용 견고성)   비용 ×3(편도 0.6%)에서도 최종 ≥ 2×보유(같은 비용) AND
                       MDD 가 보유보다 얕으면 "생존". 극단(1.0%)은 참고.
  J2 (T4 승격)         실시간 그림자 ≥ 3년 + 완료된 독립 사건 ≥ 1 (v69/v80)일 때만
                       판정 시점 도달. 그 전에는 채점 템플릿의 작동만 확인한다.
  J3 (비용 가정 실측)  유효 nav_history ≥ 60세션 (v80 부속서 2) — 미달이면 "대기".
  갭 위험              전환 신호일의 QQQ 익일 시가 갭 분포(1999~, 시가 존재 구간).
                       참고 해석: 한국 체결은 미국 다음 개장 전이라 이 갭의 일부만
                       노출되며, v43 의 갭 스트레스(전환마다 2.58% 분산 부과)에서도
                       B 우위 유지가 이미 판정돼 있다.
  국면 정의(사전 고정)  달력연도 QQQ 대리지수 수익 > +15% 상승장 / < 0% 하락장 /
                       그 외 횡보장. T4·B 연환산 수익을 국면별 집계.
  감속 회피/기회 분해   경고일(B=공격 ∧ T4<0.7) 이후 63거래일 내 그날 대비 최대
                       낙폭 ≤ −10% 면 "회피 정당", 아니면 "기회비용" (사전 고정 문턱).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ---------------------------------------------------------------------------
import json
import numpy as np
import pandas as pd

import hist_data as H
import hist_defasset as DA
import hist_defensive as DF
from axis_lib import rule_w, sim
from axis_t4_shadow import build, met

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

KCOST = 0.002
FROZEN_B = dict(enter=-0.16, exit=-0.16, lookback=252,
                defense=dict(div=0.40, ust5=0.40, gold=0.20))
OOS_REQUIRED = ('as_of', 'close', 'high_252', 'dd', 'state', 'changed',
                'rule', 'fingerprint', 't4_votes', 't4_rv', 't4_w')
NAV_REQUIRED = ('as_of', 'code', 'name', 'close', 'nav', 'dev_pct', 'volume',
                'mktcap_eok', 'univ_n', 'univ_med_pct', 'univ_sd_pct')
CORE_CODES = frozenset(('458730', '305080', '411060', '418660'))
J2_ROWS = 756
J3_SESSIONS = 60
with open(_os.path.join(_ROOT, 'data', 'freeze.json'), encoding='utf-8') as _fh:
    _FREEZE = json.load(_fh)
FREEZE_FINGERPRINT = _FREEZE['fingerprint']
OOS_START = pd.Timestamp(_FREEZE['oos_start'])


def runs(mask, idx):
    """True 연속 구간들의 (시작i, 끝i, 일수)."""
    out = []
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j, j - i + 1))
            i = j + 1
        else:
            i += 1
    return out


def dstat(x, pct=False):
    x = np.asarray(x, float)
    if not len(x):
        return '표본 없음 (n=0)'
    f = (lambda v: '%+.2f%%' % (v * 100)) if pct else (lambda v: '%.0f' % v)
    return '중앙 %s · 평균 %s · P95 %s · 최악 %s (n=%d)' % (
        f(np.median(x)), f(np.mean(x)), f(np.percentile(x, 95)),
        f(np.max(x) if not pct else np.min(x)), len(x))


def build_inputs():
    """T4의 T-bill 보완자산과 B의 40/40/20 방어 바스켓을 분리한다."""
    D_t4, wT, wB_old, votes, rv = build('tbill')
    t4_defense = np.asarray(D_t4['schdr'], float).copy()

    if DA.MIX_V23 != FROZEN_B['defense']:
        raise AssertionError('MIX_V23 이 동결 40/40/20과 다르다')
    D_b = dict(DF.build('chain'))
    if not D_b['idx'].equals(D_t4['idx']):
        raise AssertionError('B와 T4의 거래일 격자가 다르다')
    for key in ('ddv', 'qldr'):
        if not np.allclose(D_b[key], D_t4[key], equal_nan=True):
            raise AssertionError('B와 T4의 %s 입력이 다르다' % key)
    D_b['schdr'] = DA.mix_monthly(D_b['idx'], DA.MIX_V23, D_b['schdr'])
    wB = rule_w(D_b['ddv'], FROZEN_B['enter'], FROZEN_B['exit'])
    if not np.array_equal(wB, wB_old):
        raise AssertionError('B 동결 신호가 T4 입력과 갈렸다')
    if not np.array_equal(np.asarray(D_t4['schdr'], float), t4_defense):
        raise AssertionError('B 방어 바스켓 생성이 T4의 T-bill 보완자산을 바꿨다')
    return D_b, D_t4, wB, wT, votes, rv


def transition_gaps(idx, w, op, cl):
    """신호가 바뀐 idx[i] 종가부터 다음 미국 개장까지의 갭."""
    gaps_o, gaps_c, worst = [], [], (0.0, None)
    tdays = np.flatnonzero(np.asarray(w[1:]) != np.asarray(w[:-1])) + 1
    for i in tdays:
        d0 = idx[i]
        if d0 not in cl.index:
            continue
        pos = cl.index.get_loc(d0)
        if not isinstance(pos, (int, np.integer)) or pos + 1 >= len(cl.index):
            continue
        d1 = cl.index[pos + 1]
        go = float(op.loc[d1] / cl.loc[d0] - 1)
        gc = float(cl.loc[d1] / cl.loc[d0] - 1)
        gaps_o.append(go); gaps_c.append(gc)
        if abs(go) > abs(worst[0]):
            worst = (go, d1.date())
    return np.asarray(gaps_o), np.asarray(gaps_c), worst


def complete_forward(pxv, events, horizon):
    """horizon 뒤 종가가 실제로 있는 사건만 (사건행, 종가수익)으로 반환."""
    events = np.asarray(events, dtype=int)
    valid = events[events + horizon < len(pxv)]
    return valid, np.asarray(pxv)[valid + horizon] / np.asarray(pxv)[valid] - 1


def following_drawdown(pxv, events, horizon):
    """사건 다음 행부터 정확히 horizon개 행(i+1:i+h+1)의 최대낙폭."""
    pxv = np.asarray(pxv, float)
    events = np.asarray(events, dtype=int)
    if np.any(events + horizon >= len(pxv)):
        raise ValueError('완성되지 않은 forward 사건이 들어왔다')
    return np.asarray([pxv[i + 1:i + horizon + 1].min() / pxv[i] - 1
                       for i in events])


def calendar_year_returns(level):
    """전체 대리지수의 전년 말 대비 달력연도 수익; 첫 부분연도는 NaN."""
    year_end = level.groupby(level.index.year).last()
    out = year_end.pct_change(fill_method=None)
    if len(out):
        out.iloc[0] = np.nan
    return out


def independent_completed_escapes(states, gap=252, post=252):
    """직전 원시 도피와 gap 초과인 사건 중 +post 관측이 끝난 사건."""
    states = np.asarray(states, dtype=object)
    raw = np.flatnonzero((states[1:] == 'SCHD') & (states[:-1] == 'QLD')) + 1
    keep, last = [], None
    for e in raw:
        if last is None or e - last > gap:
            keep.append(int(e))
        last = int(e)
    complete = [e for e in keep if e + post < len(states)]
    return raw.tolist(), keep, complete


def _missing(frame, required):
    return [c for c in required if c not in frame.columns]


def audit_oos(led, today=None, trading_dates=None):
    """동결 장부의 스키마·기본 값 불변식과 완료 사건 수를 실제로 검사."""
    missing = _missing(led, OOS_REQUIRED)
    errors = []
    if missing:
        return dict(ok=False, missing=missing, errors=['필수 열 누락'],
                    raw_events=0, independent_events=0, completed_events=0,
                    t4_rows=0)
    if led.empty:
        errors.append('행 없음')

    raw_dates = led['as_of'].astype(str)
    dates = pd.to_datetime(raw_dates, errors='coerce')
    if dates.isna().any():
        errors.append('날짜 파싱 실패 %d행' % dates.isna().sum())
    elif not raw_dates.eq(dates.dt.strftime('%Y-%m-%d')).all():
        errors.append('날짜가 YYYY-MM-DD 정규형이 아님')
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        errors.append('날짜 중복 또는 역순')
    if not dates.isna().any():
        today_day = pd.Timestamp.today().normalize() if today is None else pd.Timestamp(today).normalize()
        if (dates < OOS_START).any():
            errors.append('동결 OOS 시작일 이전 행')
        if (dates > today_day).any():
            errors.append('미래 날짜 행')

    nums = {c: pd.to_numeric(led[c], errors='coerce')
            for c in ('close', 'high_252', 'dd', 'changed')}
    numeric_ok = all(not v.isna().any() and np.isfinite(v.to_numpy(dtype=float)).all()
                     for v in nums.values())
    if not numeric_ok:
        errors.append('필수 수치 비정상(NaN/inf 포함)')
    else:
        if ((nums['close'] <= 0) | (nums['high_252'] <= 0) |
                (nums['high_252'] + 1e-9 < nums['close'])).any():
            errors.append('종가·252일 고점 범위 위반')
        dd_calc = (nums['close'] / nums['high_252'] - 1) * 100
        if (np.abs(dd_calc - nums['dd']) > 0.02).any():
            errors.append('낙폭과 종가/고점 불일치')
        if (~nums['changed'].isin([0, 1])).any():
            errors.append('changed가 0/1 밖')

    state = led['state'].astype(str)
    if (~state.isin(['QLD', 'SCHD'])).any():
        errors.append('B 상태 값 비정상')
    elif len(state) > 1 and not nums['changed'].isna().any():
        expected = (state.values[1:] != state.values[:-1]).astype(int)
        adjacent = np.ones(len(expected), dtype=bool)
        if trading_dates is not None:
            try:
                sessions = pd.DatetimeIndex(pd.to_datetime(trading_dates, errors='raise')).normalize()
                if len(sessions) < 2 or sessions.has_duplicates or not sessions.is_monotonic_increasing:
                    raise ValueError('거래일이 부족하거나 중복·역순임')
                if dates.isna().any() or not set(dates).issubset(set(sessions)):
                    raise ValueError('OOS 날짜가 QQQ 거래일에 없음')
                previous = {sessions[i]: sessions[i - 1] for i in range(1, len(sessions))}
                adjacent = np.array(
                    [previous.get(dates.iloc[i]) == dates.iloc[i - 1]
                     for i in range(1, len(dates))], dtype=bool)
            except Exception as e:
                errors.append('QQQ 거래일 계약을 해석할 수 없음: %s' % e)
                adjacent[:] = False
        actual = nums['changed'].values[1:].astype(int)
        if adjacent.any() and not np.array_equal(actual[adjacent], expected[adjacent]):
            errors.append('changed와 실제 상태 전환 불일치')
    if numeric_ok and state.isin(['QLD', 'SCHD']).all():
        expected_state = pd.Series(
            np.where(nums['dd'].values <= -16.0, 'SCHD', 'QLD'), index=led.index)
        if not state.eq(expected_state).all():
            errors.append('B 상태와 -16% 낙폭 규칙 불일치')
    if not led['rule'].astype(str).eq('-16/-16').all():
        errors.append('동결 규칙 이름 불일치')
    fingerprints = led['fingerprint'].astype(str)
    if not fingerprints.str.fullmatch(r'[0-9a-f]{16}').all():
        errors.append('fingerprint 형식 비정상')
    elif not fingerprints.eq(FREEZE_FINGERPRINT).all():
        errors.append('fingerprint가 현행 freeze.json과 다름')

    t4 = led.loc[:, ['t4_votes', 't4_rv', 't4_w']]
    present = t4.notna()
    if (present.any(axis=1) & ~present.all(axis=1)).any():
        errors.append('T4 세 필드 일부만 기록')
    full = present.all(axis=1)
    if (~full).any():
        errors.append('T4 세 필드가 비어 있는 행 %d개' % int((~full).sum()))
    if full.any():
        tv = pd.to_numeric(t4.loc[full, 't4_votes'], errors='coerce')
        tr = pd.to_numeric(t4.loc[full, 't4_rv'], errors='coerce')
        tw = pd.to_numeric(t4.loc[full, 't4_w'], errors='coerce')
        expected_w = np.where(tv < 2, 0.0,
                              np.where(tr == 0, 1.0, np.minimum(1.0, 40.0 / tr)))
        bad = (tv.isna() | tr.isna() | tw.isna() |
               ~np.isfinite(tv) | ~np.isfinite(tr) | ~np.isfinite(tw) | (tv % 1 != 0) |
               ~tv.between(0, 4) | (tr < 0) | ~tw.between(0, 1) |
               (np.abs(tw - expected_w) > 0.003))
        if bad.any():
            errors.append('T4 값 범위·40%% 변동성 목표 정의 위반 %d행' % bad.sum())

    raw, independent, complete = independent_completed_escapes(state.values)
    return dict(ok=not errors, missing=[], errors=errors,
                raw_events=len(raw), independent_events=len(independent),
                completed_events=len(complete), t4_rows=int(full.sum()))


def _kr_holiday_contract():
    """J3 세션 수에 쓸 추적 휴장일 표. 모르면 세션을 세지 않는다."""
    path = _os.path.join(_ROOT, 'data', 'kr_holidays.json')
    with open(path, encoding='utf-8') as fh:
        payload = json.load(fh)
    holidays, years = payload.get('holidays'), payload.get('range')
    if not isinstance(holidays, dict) or not isinstance(years, list) or len(years) != 2:
        raise ValueError('kr_holidays.json 구조가 잘못됨')
    lo, hi = int(years[0]), int(years[1])
    parsed = {pd.Timestamp(day).normalize() for day in holidays}
    if lo > hi or any(not lo <= day.year <= hi for day in parsed):
        raise ValueError('kr_holidays.json 날짜가 선언 범위 밖임')
    return parsed, (lo, hi)


def audit_nav(nav, today=None, holidays=None):
    """NAV 행 값과 전략 4종목이 모두 있는 유효 세션 수를 검사."""
    missing = _missing(nav, NAV_REQUIRED)
    errors = []
    warnings = []
    if missing:
        return dict(ok=False, missing=missing, errors=['필수 열 누락'],
                    warnings=[], sessions=0, valid_sessions=0, core=pd.DataFrame())
    if nav.empty:
        errors.append('행 없음')
    raw_dates = nav['as_of'].astype(str)
    dates = pd.to_datetime(raw_dates, errors='coerce')
    if dates.isna().any():
        errors.append('날짜 파싱 실패 %d행' % dates.isna().sum())
    elif not raw_dates.eq(dates.dt.strftime('%Y-%m-%d')).all():
        errors.append('NAV 날짜가 YYYY-MM-DD 정규형이 아님')
    elif not dates.is_monotonic_increasing:
        errors.append('NAV 날짜 역순')
    else:
        today_day = pd.Timestamp.today().normalize() if today is None else pd.Timestamp(today).normalize()
        if (dates > today_day).any():
            errors.append('NAV 미래 날짜 행')
    codes = nav['code'].astype(str).str.replace(r'\.0$', '', regex=True)
    if pd.DataFrame({'date': dates, 'code': codes}).duplicated().any():
        errors.append('날짜·종목 중복')
    numcols = ('close', 'nav', 'dev_pct', 'volume', 'mktcap_eok', 'univ_n',
               'univ_med_pct', 'univ_sd_pct')
    nums = {c: pd.to_numeric(nav[c], errors='coerce') for c in numcols}
    numeric_ok = all(not v.isna().any() and np.isfinite(v.to_numpy(dtype=float)).all()
                     for v in nums.values())
    if not numeric_ok:
        errors.append('NAV 필수 수치 비정상(NaN/inf 포함)')
    else:
        if ((nums['close'] <= 0) | (nums['nav'] <= 0) | (nums['volume'] < 0) |
                (nums['mktcap_eok'] < 0) | (nums['univ_n'] < 10) |
                (nums['univ_n'] % 1 != 0) |
                (nums['dev_pct'].abs() >= 20)).any():
            errors.append('NAV 값 범위 위반')
        dev_calc = (nums['close'] / nums['nav'] - 1) * 100
        if (np.abs(dev_calc - nums['dev_pct']) > 0.02).any():
            errors.append('괴리율과 종가/NAV 불일치')

    # 2026-08-29(토)처럼 과거에 이미 봉인된 오기 행은 삭제하지 않는다. 다만 J3의
    # 60세션을 앞당기지 못하게 주말·추적 휴장일을 유효 세션에서 제외한다.
    calendar_ok = dates.notna() & (dates.dt.weekday < 5)
    try:
        if holidays is None:
            holiday_days, (lo, hi) = _kr_holiday_contract()
            if dates.notna().any() and ((dates.dropna().dt.year < lo).any()
                                         or (dates.dropna().dt.year > hi).any()):
                raise ValueError('NAV 날짜가 kr_holidays.json 범위 밖임')
        else:
            holiday_days = {pd.Timestamp(day).normalize() for day in holidays}
        calendar_ok &= ~dates.dt.normalize().isin(holiday_days)
    except Exception as e:
        errors.append('한국 휴장일 표 검증 실패: %s' % e)
        calendar_ok &= False
    bad_calendar = sorted(set(nav.loc[dates.notna() & ~calendar_ok, 'as_of'].astype(str)))
    if bad_calendar:
        warnings.append('비거래일 NAV %d일 제외(%s)' %
                        (len(bad_calendar), ', '.join(bad_calendar[:3])))

    core_mask = codes.isin(CORE_CODES) & calendar_ok
    core = nav.loc[core_mask].copy().astype({'code': 'string'})
    core.loc[:, '_date'] = dates[core_mask].values
    valid_sessions = 0
    if not core.empty:
        valid_sessions = int(sum(set(g['code']) == CORE_CODES
                                 for _, g in core.groupby('_date')))
    return dict(ok=not errors, missing=[], errors=errors,
                warnings=warnings,
                sessions=int(dates.dropna().nunique()), valid_sessions=valid_sessions,
                core=core)


def j2_ready(rows, completed_events, audit_ok=True):
    return bool(audit_ok and rows >= J2_ROWS and completed_events >= 1)


def j3_ready(valid_sessions, audit_ok=True):
    return bool(audit_ok and valid_sessions >= J3_SESSIONS)


def selfcheck_contracts():
    """이번 코드리뷰에서 고친 다섯 계약의 최소 반례."""
    # 전환일 i가 신호 확정일이다. i-1을 쓰면 아래 50% 갭을 놓친다.
    ix = pd.DatetimeIndex(['2020-01-02', '2020-01-03', '2020-01-06'])
    qi = pd.DatetimeIndex(['2020-01-02', '2020-01-03', '2020-01-06', '2020-01-07'])
    cl = pd.Series([100., 200., 300., 330.], index=qi)
    op = pd.Series([100., 200., 300., 330.], index=qi)
    go, gc, worst = transition_gaps(ix, np.array([1., 0., 0.]), op, cl)
    assert np.allclose(go, [0.5]) and np.allclose(gc, [0.5]) and str(worst[1]) == '2020-01-06'

    # 마지막 horizon이 없는 사건은 제외하고, +63번째 행은 낙폭 창에 포함한다.
    path = np.full(65, 100.0); path[63] = 50.0
    valid, _ = complete_forward(path, np.array([0, 1, 2]), 63)
    assert valid.tolist() == [0, 1]
    assert np.allclose(following_drawdown(path, np.array([0]), 63), [-0.5])

    # 첫 부분연도는 분류하지 않고 다음 해는 반드시 전년 말과 비교한다.
    lv = pd.Series([100., 110., 121.], index=pd.to_datetime(
        ['2019-06-03', '2019-12-31', '2020-12-31']))
    yr = calendar_year_returns(lv)
    assert np.isnan(yr.loc[2019]) and np.isclose(yr.loc[2020], 0.10)

    # 중간 원시 사건을 건너뛰어도 last는 갱신한다. +252 완료 여부도 별도다.
    states = np.full(908, 'QLD', dtype=object)
    for e in (1, 201, 401, 654):
        states[e] = 'SCHD'
    raw, independent, complete = independent_completed_escapes(states)
    assert raw == [1, 201, 401, 654] and independent == [1, 654] and complete == [1, 654]
    assert not j2_ready(755, 1) and not j2_ready(756, 0) and j2_ready(756, 1)
    assert not j3_ready(59) and j3_ready(60)

    # 열 하나가 사라진 장부는 충족으로 오판하면 안 된다.
    assert not audit_oos(pd.DataFrame(columns=OOS_REQUIRED[:-1]))['ok']
    assert not audit_nav(pd.DataFrame(columns=NAV_REQUIRED[:-1]))['ok']

    # 16자리 hex라는 형식만 맞는 가짜 지문도 장부 성숙도로 인정하지 않는다.
    row = dict(as_of='2026-08-28', close=100.0, high_252=100.0, dd=0.0,
               state='QLD', changed=0, rule='-16/-16',
               fingerprint=FREEZE_FINGERPRINT,
               t4_votes=2, t4_rv=80.0, t4_w=0.5)
    assert audit_oos(pd.DataFrame([row]))['ok']
    row['fingerprint'] = '0000000000000000'
    assert not audit_oos(pd.DataFrame([row]))['ok']
    row['fingerprint'] = FREEZE_FINGERPRINT
    row['close'], row['dd'], row['state'] = 80.0, -20.0, 'QLD'
    assert not audit_oos(pd.DataFrame([row]))['ok']
    row['state'] = 'SCHD'
    row['t4_votes'] = row['t4_rv'] = row['t4_w'] = np.nan
    assert not audit_oos(pd.DataFrame([row]))['ok']
    row.update(t4_votes=4, t4_rv=80.0, t4_w=1.0)
    assert not audit_oos(pd.DataFrame([row]))['ok']
    row.update(t4_votes=4, t4_rv=0.0, t4_w=1.0)
    assert audit_oos(pd.DataFrame([row]))['ok']
    infrow = dict(row, close=np.inf, high_252=np.inf, dd=0.0)
    assert not audit_oos(pd.DataFrame([infrow]))['ok']
    noncanonical = dict(row, as_of='2026-8-28')
    assert not audit_oos(pd.DataFrame([noncanonical]))['ok']
    row['as_of'] = '2026-08-27'
    assert not audit_oos(pd.DataFrame([row]), today='2026-09-04')['ok']

    # 중간 QQQ 거래일의 장부가 빠졌다면 다음 행 changed=False는 정상 복구다. 반대로
    # 두 행이 실제 연속 거래일이면 같은 상태차에 changed=False를 허용하지 않는다.
    gap_a = dict(row, as_of='2026-08-28', close=100.0, high_252=100.0, dd=0.0,
                 state='QLD', changed=0, t4_votes=2, t4_rv=80.0, t4_w=0.5)
    gap_b = dict(gap_a, as_of='2026-09-01', close=80.0, dd=-20.0,
                 state='SCHD', changed=0)
    gap_ledger = pd.DataFrame([gap_a, gap_b])
    assert audit_oos(gap_ledger, today='2026-09-04',
                     trading_dates=['2026-08-28', '2026-08-31', '2026-09-01'])['ok']
    assert not audit_oos(gap_ledger, today='2026-09-04',
                         trading_dates=['2026-08-28', '2026-09-01'])['ok']

    navrow = dict(as_of='2026-09-05', code='418660', name='TIGER', close=100.0,
                  nav=100.0, dev_pct=0.0, volume=1, mktcap_eok=1,
                  univ_n=10, univ_med_pct=0.0, univ_sd_pct=1.0)
    assert not audit_nav(pd.DataFrame([navrow]), today='2026-09-04')['ok']
    navinf = dict(navrow, as_of='2026-09-04', close=np.inf, nav=np.inf)
    assert not audit_nav(pd.DataFrame([navinf]), today='2026-09-04', holidays=set())['ok']

    # 토요일에 핵심 4종이 모두 있어도 J3의 유효 세션은 늘지 않는다(실제 2026-08-29 반례).
    weekend = pd.DataFrame([dict(navrow, as_of='2026-08-29', code=code)
                            for code in CORE_CODES])
    weekend_audit = audit_nav(weekend, today='2026-09-04', holidays=set())
    assert weekend_audit['ok'] and weekend_audit['valid_sessions'] == 0
    assert weekend_audit['warnings']


def main():
    selfcheck_contracts()
    D_b, D_t4, wB, wT, votes, rv = build_inputs()
    idx = D_b['idx']; n = len(idx)
    yrs = (idx[-1] - idx[0]).days / 365.25
    r_full, _ = H.qqq_proxy()
    px_full = (1 + r_full).cumprod()
    px = px_full.reindex(idx)

    # ============================================================ 1. B 실전 안정성
    print('=' * 104)
    print('1. B 실전 안정성 — 동결 파라미터 그대로 (54.5년)')
    print('=' * 104)
    flips = int((wB[1:] != wB[:-1]).sum())
    att = runs(wB == 1, idx); dfn = runs(wB == 0, idx)
    print('  전환 %d회 (연 %.2f) · 공격 구간 %d개 · 방어 구간 %d개' % (flips, flips / yrs, len(att), len(dfn)))
    print('  공격 보유기간(거래일): %s' % dstat([d for _, _, d in att]))
    print('  방어 기간(=복귀 대기): %s' % dstat([d for _, _, d in dfn]))
    a, b, d = max(dfn, key=lambda t: t[2])
    print('  최장 방어: %s ~ %s (%d거래일 ≈ %.1f년)' % (idx[a].date(), idx[b].date(), d, d / 252))
    cB2, _ = sim(D_b, wB, cost=KCOST)
    uw = (cB2 / cB2.cummax() - 1)
    uw_runs = runs((uw < 0).values, idx)
    a2, b2, d2 = max(uw_runs, key=lambda t: t[2])
    print('  최장 언더워터(0.2%%): %d거래일 ≈ %.1f년 (%s~%s)' % (d2, d2 / 252, idx[a2].date(), idx[b2].date()))

    # 신호 지연 (휴장·실기 위험의 값)
    for lag in (1, 2, 3):
        c, _ = sim(D_b, wB, cost=KCOST, lag=lag)
        print('  체결 지연 lag=%d: 최종 %s · MDD %.1f%%' % (lag, format(float(c.iloc[-1]), ',.0f'), met(c)['mdd'] * 100))

    # 전환 신호일 갭 (QQQ 시가 존재 구간 1999-03~)
    s = H._stooq('qqq_us_d.csv')
    raw = pd.read_csv('qqq_us_d.csv', parse_dates=['Date']).set_index('Date')
    op, cl = raw['Open'], raw['Close']
    gaps_o, gaps_c, worst = transition_gaps(idx, wB, op, cl)
    print('  전환 신호일 익일 갭 (1999~, %d회 관측):' % len(gaps_o))
    print('    종가→익일시가: %s' % dstat(gaps_o, pct=True))
    print('    종가→익일종가: %s' % dstat(gaps_c, pct=True))
    print('    최대 단일 시가 갭: %+.2f%% (%s) · 참고: v43 갭 스트레스(2.58%% 분산)에서도 B 우위' % (worst[0] * 100, worst[1]))
    print('    해석: 한국 체결(09:05~15:20 KST)은 미국 다음 개장 전 — 시가 갭의 일부만 노출 + 환율 변동 별도')

    # ============================================================ 2. 비용 스트레스
    print()
    print('=' * 104)
    print('2. 비용 스트레스 — B 파라미터 불변, 편도 비용만 충격 (J1)')
    print('=' * 104)
    hold = np.ones(n)
    print('  %-14s %10s %8s %8s %12s %8s' % ('시나리오', '최종배수', 'CAGR', 'MDD', '2배보유(동일비용)', '생존'))
    j1 = None
    for lab, c in (('기본가정 0.2%', 0.002), ('x1.5 = 0.3%', 0.003), ('x2 = 0.4%', 0.004),
                   ('x3 = 0.6%', 0.006), ('극단 1.0%', 0.010), ('(참고 0.1%)', 0.001)):
        cb, _ = sim(D_b, wB, cost=c)
        ch, _ = sim(D_b, hold, cost=c)
        m, mh = met(cb), met(ch)
        alive = m['final'] >= 2 * mh['final'] and m['mdd'] > mh['mdd']
        if lab.startswith('x3'):
            j1 = alive
        print('  %-14s %10s %7.1f%% %7.1f%% %12s %8s' %
              (lab, format(m['final'], ',.0f'), m['cagr'] * 100, m['mdd'] * 100,
               format(mh['final'], ',.0f'), '생존' if alive else '탈락'))

    # ============================================================ 3. T4 vs B 최종 비교
    print()
    print('=' * 104)
    print('3. T4 vs B — 사전 정의 그대로, 재최적화 없음 (B 방어 40/40/20 · T4 보완 T-bill · lag=1)')
    print('=' * 104)
    cT2, _ = sim(D_t4, wT, cost=KCOST)
    retB = cB2.pct_change().fillna(0).values
    retT = cT2.pct_change().fillna(0).values

    def full_metrics(curve, w):
        m = met(curve)
        r = curve.pct_change().dropna().values
        dn = r[r < 0]
        m['sortino'] = ((1 + np.mean(r)) ** 252 - 1) / (np.std(dn, ddof=1) * np.sqrt(252)) if len(dn) > 5 else np.nan
        m['switch'] = int((np.abs(np.diff(w)) > 1e-9).sum())
        off = runs(w < 0.5, idx)
        m['def_med'] = np.median([d for _, _, d in off]) if off else 0
        m['def_n'] = len(off)
        return m
    mB, mT = full_metrics(cB2, wB), full_metrics(cT2, wT)
    rows = [('최종배수', '%s' % format(mB['final'], ',.0f'), '%s' % format(mT['final'], ',.0f')),
            ('CAGR', '%.2f%%' % (mB['cagr'] * 100), '%.2f%%' % (mT['cagr'] * 100)),
            ('MDD', '%.1f%%' % (mB['mdd'] * 100), '%.1f%%' % (mT['mdd'] * 100)),
            ('Calmar', '%.3f' % mB['calmar'], '%.3f' % mT['calmar']),
            ('Sortino(일간)', '%.3f' % mB['sortino'], '%.3f' % mT['sortino']),
            ('조정 횟수(54.5y)', '%d' % mB['switch'], '%d' % mT['switch']),
            ('저노출 구간 수·중앙일수', '%d개 · %.0f일' % (mB['def_n'], mB['def_med']),
             '%d개 · %.0f일' % (mT['def_n'], mT['def_med']))]
    print('  %-22s %16s %16s' % ('지표', 'B', 'T4'))
    for nm, a_, b_ in rows:
        print('  %-22s %16s %16s' % (nm, a_, b_))

    # 최악 곰랠리(B 방어 중 T4 재진입 손실) · 최대 기회비용(252일 상대열세)
    rel = np.log(cT2.values) - np.log(cB2.values)
    worst_bear = 0.0
    for a3, b3, _ in dfn:
        seg = cT2.iloc[a3:b3 + 1]
        worst_bear = min(worst_bear, float((seg / seg.cummax() - 1).min()))
    rel252 = pd.Series(rel, index=idx).diff(252).dropna()
    print('  B 방어 구간 중 T4 최악 낙폭(곰랠리 비용): %.1f%%' % (worst_bear * 100))
    print('  T4 최대 기회비용(252일 상대열세): %.1f%% (%s)'
          % ((np.exp(rel252.min()) - 1) * 100, rel252.idxmin().date()))
    print('  B 최대 기회비용(T4 대비 252일):   %.1f%% (%s)'
          % ((np.exp(-rel252.max()) - 1) * 100, rel252.idxmax().date()))

    # 5년 롤링 + 국면별 (사전 고정 정의)
    L = 1260
    starts = np.arange(1, n - L, 21)
    lgB, lgT = np.log(cB2.values), np.log(cT2.values)
    fB = np.exp(lgB[starts + L - 1] - lgB[starts - 1])
    fT = np.exp(lgT[starts + L - 1] - lgT[starts - 1])
    print('  5년 롤링 %d개: T4 승 %.0f%% · 중앙 상대성적 %+.1f%%'
          % (len(starts), (fT > fB).mean() * 100, (np.median(fT / fB) - 1) * 100))
    yr_ret = calendar_year_returns(px_full)
    def regime_of(y):
        r = yr_ret.get(y, np.nan)
        if pd.isna(r):
            return '미분류'
        return '상승' if r > 0.15 else ('하락' if r < 0 else '횡보')
    reg = np.array([regime_of(y) for y in idx.year])
    print('  국면별 연환산 수익 (달력연도 QQQ: >+15% 상승 / <0% 하락 / 그 외 횡보):')
    print('    첫 부분연도 %d년은 전년 말이 없어 분류에서 제외' % int(yr_ret.index[0]))
    for g in ('상승', '하락', '횡보'):
        m_ = reg == g
        aB = (1 + pd.Series(retB[m_])).prod() ** (252 / m_.sum()) - 1
        aT = (1 + pd.Series(retT[m_])).prod() ** (252 / m_.sum()) - 1
        print('    %-4s (%4.0f일/yr 평균 %4.1f년치)  B %+7.1f%%  T4 %+7.1f%%'
              % (g, m_.sum() / yrs * 1.0, m_.sum() / 252, aB * 100, aT * 100))

    # ============================================================ 4. 감속 신호 조건부 성과
    print()
    print('=' * 104)
    print('4. T4 감속 신호의 조건부 성과 — 그림자 채점 템플릿 (사전 등록)')
    print('=' * 104)
    warn = (wB == 1) & (wT < 0.7)
    wi = np.where(warn)[0]
    pxv = px.values
    fwd = {}
    for h in (5, 21, 63):
        wh, v = complete_forward(pxv, wi, h)
        fwd[h] = (wh, v)
        print('  경고일(B공격∧T4<0.7, %d일) 이후 %2d일 시장수익: %s'
              % (len(wh), h, dstat(v, pct=True)))
    # 회피 정당 vs 기회비용 (사전 고정: 63일 내 최대낙폭 ≤ −10%)
    wi63, fwd63 = fwd[63]
    mdd63 = following_drawdown(pxv, wi63, 63)
    just = mdd63 <= -0.10
    dT_win = retT[wi63 + 1]   # lag=1 체결 반영 다음날 수익부터는 근사 — 상대비교용
    dB_win = retB[wi63 + 1]
    print('  분해: 회피 정당(63일 내 −10%% 이상 하락) %d일 (%.0f%%) · 기회비용 %d일 (%.0f%%)'
          % (just.sum(), just.mean() * 100, (~just).sum(), (~just).mean() * 100))
    print('    회피 정당일의 63일 내 최대낙폭: %s' % dstat(mdd63[just], pct=True))
    print('    기회비용일의 63일 시장수익: %s' % dstat(fwd63[~just], pct=True))
    print('    경고일 평균 상대수익(T4−B, 익일): %+.4f%%p/일 · 전체일 평균 %+.4f%%p/일'
          % ((dT_win - dB_win).mean() * 100, (retT - retB).mean() * 100))
    print('  → 실시간 그림자도 같은 식으로 채점한다: 장부의 close·state·t4_w 만으로 재구성 가능')

    # ============================================================ 5. 장부·실측 수집 감사
    print()
    print('=' * 104)
    print('5. 그림자 장부 · 한국 실측 수집 감사 (J2·J3)')
    print('=' * 104)
    led = pd.read_csv('data/oos_log.csv') if _os.path.exists('data/oos_log.csv') else pd.DataFrame()
    qqq_days = (pd.read_csv('data/qqq.csv', usecols=['Date'])['Date']
                if _os.path.exists('data/qqq.csv') else [])
    la = audit_oos(led, trading_dates=qqq_days)
    span = ('%s ~ %s' % (led['as_of'].iloc[0], led['as_of'].iloc[-1])
            if len(led) and 'as_of' in led else '날짜 없음')
    print('  oos_log.csv: %d행 (%s) · 열 %d개' % (len(led), span, led.shape[1]))
    print('    스키마 감사: %s%s' %
          ('통과' if not la['missing'] else '실패',
           '' if not la['missing'] else ' — 누락 ' + ','.join(la['missing'])))
    print('    값 감사: %s%s' %
          ('통과' if la['ok'] else '실패',
           '' if la['ok'] else ' — ' + '; '.join(la['errors'])))
    print('    도피 사건: 원시 %d · 독립 %d · +252일 완료 %d'
          % (la['raw_events'], la['independent_events'], la['completed_events']))
    j2 = j2_ready(la['t4_rows'], la['completed_events'], la['ok'])
    if not la['ok']:
        j2_text = '장부 감사 실패 — 판정 중단'
    elif j2:
        j2_text = '판정 시점 도달 — v80 판정식 실행 가능'
    else:
        j2_text = '대기 — T4 유효 %d/756행 · 완료 독립 사건 %d/1' % (
            la['t4_rows'], la['completed_events'])
    print('  J2 성숙도: %s' % j2_text)

    nav = (pd.read_csv('data/nav_history.csv', encoding='utf-8-sig')
           if _os.path.exists('data/nav_history.csv') else pd.DataFrame())
    na = audit_nav(nav)
    nav_span = ('%s ~ %s' % (nav['as_of'].min(), nav['as_of'].max())
                if len(nav) and 'as_of' in nav else '날짜 없음')
    print('  nav_history.csv: 전체 %d세션 · 4종목 유효 %d세션 (%s) · 60세션 기준 %d 남음'
          % (na['sessions'], na['valid_sessions'], nav_span,
             max(0, J3_SESSIONS - na['valid_sessions'])))
    print('    스키마 감사: %s%s' %
          ('통과' if not na['missing'] else '실패',
           '' if not na['missing'] else ' — 누락 ' + ','.join(na['missing'])))
    print('    값 감사: %s%s' %
          ('통과' if na['ok'] else '실패',
           '' if na['ok'] else ' — ' + '; '.join(na['errors'])))
    if na.get('warnings'):
        print('    세션 제외: ' + '; '.join(na['warnings']))
    if not na['core'].empty and na['ok']:
        dev = na['core'].groupby('code')['dev_pct'].agg(['median', 'std', 'max'])
        print('  괴리율 잠정 관측(전략 4종목, %%): \n%s' % dev.round(3).to_string())
    print('  주의: 호가 스프레드는 미수집 — 괴리율+거래대금으로 하한만 잰다. 60 유효세션 후 재측정(v80 부속서 2).')
    j3 = j3_ready(na['valid_sessions'], na['ok'])
    if not na['ok']:
        j3_text = '장부 감사 실패 — 재측정 중단'
    elif j3:
        j3_text = '%d/60 유효세션 — 재측정 시점 도달' % na['valid_sessions']
    else:
        j3_text = '%d/60 유효세션 — 대기' % na['valid_sessions']

    print()
    print('=' * 104)
    print('[J1] 비용 x3 생존: %s' % ('통과' if j1 else '탈락'))
    print('[J2] T4 승격 성숙도: %s' % j2_text)
    print('[J3] 비용 실측 성숙도: %s. 잠정 괴리율은 0.2%% 가정 대비 방향 참고만.' % j3_text)


if __name__ == '__main__':
    if '--selftest' in _sys.argv:
        selfcheck_contracts()
        print('axis_finalverify selftest: PASS (갭/완료창/연도 · 사건 간격 · 장부 스키마/동결 지문)')
    else:
        main()
