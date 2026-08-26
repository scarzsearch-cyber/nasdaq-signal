#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[v24] 한국 증시 휴장일 생성기 — signal.html 시계에 넣을 표를 만든다

signal.html 의 시장 시계는 지금까지 **한국 공휴일을 반영하지 못했다**(설·추석이 음력이라
보류). 여기서 음력을 실제로 계산해 표를 굳히고, 화면은 그 표만 읽는다.

[음력 계산] Meeus, Astronomical Algorithms
  - 삭(new moon) 시각: 49장 (평균삭 + 주기항 보정)
  - 태양 황경:        25장 (중기 판정용)
  - 규칙: 동지가 든 달 = 11월. 이후 삭에서 삭까지를 한 달로 하고,
          중기(태양황경 30° 배수)가 없는 달을 윤달로 넣는다. 전부 KST 기준.

[증시 휴장일]
  고정   1/1, 3/1, 5/1(근로자의날), 5/5, 6/6, 8/15, 10/3, 10/9, 12/25
  음력   설 연휴(섣달그믐·1/1·1/2), 부처님오신날(4/8), 추석 연휴(8/14·15·16)
  대체공휴일  현행 규정(설·추석·어린이날·삼일절·광복절·개천절·한글날·부처님오신날·성탄절)
  연말   12월 마지막 영업일은 증시 휴장

[알고리즘이 못 맞히는 것] 임시공휴일과 선거일. 예측 불가라 SPECIAL 에 손으로 넣는다.

[검증] verify() 가 KOSPI 실거래일(data/hist/kr__5EKS11.csv)에서 역산한 실제 휴장일과
       대조한다. 알고리즘 휴장일이 실제로 휴장이었는지(거짓양성 0), 그리고 실제 휴장일
       중 임시공휴일·선거일을 뺀 나머지를 다 맞히는지(거짓음성 0)를 본다.

실행:
    python deploy/kr_holidays.py            # 검증 리포트
    python deploy/kr_holidays.py --emit     # data/kr_holidays.json 생성
"""
import datetime as dt
import json
import math
import os
import sys

RAD = math.pi / 180.0

# 알고리즘으로는 못 맞히는 것들 — 임시공휴일·선거일 (관보/KRX 공지 기준)
SPECIAL = {
    '2012-04-11': '총선', '2012-12-19': '대선',
    '2014-06-04': '지방선거', '2016-04-13': '총선',
    '2017-05-09': '대선', '2018-06-13': '지방선거',
    '2020-04-15': '총선', '2020-08-17': '임시공휴일',
    '2022-03-09': '대선', '2022-06-01': '지방선거',
    '2023-10-02': '임시공휴일', '2024-04-10': '총선',
    '2025-01-27': '임시공휴일', '2025-06-03': '대선',
    '2026-06-03': '지방선거', '2026-07-17': '임시공휴일',
    '2006-05-31': '지방선거', '2007-12-19': '대선', '2008-04-09': '총선',
    '2010-06-02': '지방선거', '2015-08-14': '임시공휴일',
    '2016-05-06': '임시공휴일', '2017-10-02': '임시공휴일',
    '2024-10-01': '임시공휴일',
}

# Yahoo 시계열의 결측 의심일 — 어떤 공휴일에도 해당하지 않고 국내 5개 시계열 전부에서 빠져 있다.
# (2011-10-04 는 ^KS11 만 빠지고 132030·133690 에는 있어 결측이 확인됐다)
KNOWN_GAPS = {'2007-03-02', '2011-10-04', '2017-09-22', '2017-12-20',
              '2022-01-03', '2022-05-09'}

# 제도 이력이 있는 고정 공휴일 (연도 범위 밖이면 휴일이 아니다)
ERA = {'한글날': (2013, 9999), '제헌절': (1900, 2007), '식목일': (1900, 2005)}

FIXED = [(1, 1, '신정'), (3, 1, '삼일절'), (4, 5, '식목일'), (5, 1, '근로자의날'),
         (5, 5, '어린이날'), (6, 6, '현충일'), (7, 17, '제헌절'), (8, 15, '광복절'),
         (10, 3, '개천절'), (10, 9, '한글날'), (12, 25, '성탄절')]

# 대체공휴일 시행 시점 (제도 변경 이력)
#   2014 설·추석·어린이날 / 2021 삼일절·광복절·개천절·한글날 / 2023 부처님오신날·성탄절
SUB_FROM = {'설날': 2014, '추석': 2014, '어린이날': 2014, '삼일절': 2021,
            '광복절': 2021, '개천절': 2021, '한글날': 2021,
            '부처님오신날': 2023, '성탄절': 2023}


# ---------------------------------------------------------------- 천문
def jd_to_date(jd):
    z = math.floor(jd + 0.5)
    f = jd + 0.5 - z
    a = z
    if z >= 2299161:
        al = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + al - math.floor(al / 4)
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day = b - d - math.floor(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    return year, month, day


def new_moon_jd(k):
    """k 번째 삭의 율리우스일 (TT). Meeus 49장, 주요 보정항까지."""
    T = k / 1236.85
    T2, T3, T4 = T * T, T ** 3, T ** 4
    jde = (2451550.09766 + 29.530588861 * k + 0.00015437 * T2
           - 0.000000150 * T3 + 0.00000000073 * T4)
    E = 1 - 0.002516 * T - 0.0000074 * T2
    M = (2.5534 + 29.10535670 * k - 0.0000014 * T2 - 0.00000011 * T3) * RAD
    Mp = (201.5643 + 385.81693528 * k + 0.0107582 * T2
          + 0.00001238 * T3 - 0.000000058 * T4) * RAD
    F = (160.7108 + 390.67050284 * k - 0.0016118 * T2
         - 0.00000227 * T3 + 0.000000011 * T4) * RAD
    O = (124.7746 - 1.56375588 * k + 0.0020672 * T2 + 0.00000215 * T3) * RAD
    c = (-0.40720 * math.sin(Mp) + 0.17241 * E * math.sin(M)
         + 0.01608 * math.sin(2 * Mp) + 0.01039 * math.sin(2 * F)
         + 0.00739 * E * math.sin(Mp - M) - 0.00514 * E * math.sin(Mp + M)
         + 0.00208 * E * E * math.sin(2 * M) - 0.00111 * math.sin(Mp - 2 * F)
         - 0.00057 * math.sin(Mp + 2 * F) + 0.00056 * E * math.sin(2 * Mp + M)
         - 0.00042 * math.sin(3 * Mp) + 0.00042 * E * math.sin(M + 2 * F)
         + 0.00038 * E * math.sin(M - 2 * F) - 0.00024 * E * math.sin(2 * Mp - M)
         - 0.00017 * math.sin(O) - 0.00007 * math.sin(Mp + 2 * M))
    a = (0.000325 * math.sin((299.77 + 0.107408 * k - 0.009173 * T2) * RAD)
         + 0.000165 * math.sin((251.88 + 0.016321 * k) * RAD)
         + 0.000164 * math.sin((251.83 + 26.651886 * k) * RAD)
         + 0.000126 * math.sin((349.42 + 36.412478 * k) * RAD)
         + 0.000110 * math.sin((84.66 + 18.206239 * k) * RAD)
         + 0.000062 * math.sin((141.74 + 53.303771 * k) * RAD)
         + 0.000060 * math.sin((207.14 + 2.453732 * k) * RAD)
         + 0.000056 * math.sin((154.84 + 7.306860 * k) * RAD)
         + 0.000047 * math.sin((34.52 + 27.261239 * k) * RAD)
         + 0.000042 * math.sin((207.19 + 0.121824 * k) * RAD)
         + 0.000040 * math.sin((291.34 + 1.844379 * k) * RAD)
         + 0.000037 * math.sin((161.72 + 24.198154 * k) * RAD)
         + 0.000035 * math.sin((239.56 + 25.513099 * k) * RAD)
         + 0.000023 * math.sin((331.55 + 3.592518 * k) * RAD))
    return jde + c + a


def delta_t_days(year):
    """TT - UT 근사 (1900~2100). 일 단위."""
    t = year - 2000
    return (63.0 + 0.4 * t) / 86400.0


def sun_longitude(jd):
    """겉보기 태양황경(도). Meeus 25장 간이형."""
    T = (jd - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = (357.52911 + 35999.05029 * T - 0.0001537 * T * T) * RAD
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M)
         + 0.000289 * math.sin(3 * M))
    true_long = L0 + C
    O = (125.04 - 1934.136 * T) * RAD
    return (true_long - 0.00569 - 0.00478 * math.sin(O)) % 360.0


# ---------------------------------------------------------------- 음력
def _kst_day(jd_tt, year):
    """TT 율리우스일 -> KST 날짜(date)"""
    jd = jd_tt - delta_t_days(year) + 9.0 / 24.0
    y, m, d = jd_to_date(jd)
    return dt.date(int(y), int(m), int(math.floor(d)))


def _kst_midnight_jd(d):
    """KST 자정의 TT 율리우스일 (근사)"""
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    jdn = (d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045)
    return jdn - 0.5 - 9.0 / 24.0 + delta_t_days(d.year)


def _winter_solstice(year):
    """그해 동지(태양황경 270°)의 KST 날짜. 12/20~12/24 를 훑어 찾는다."""
    prev = None
    for d in range(19, 25):
        day = dt.date(year, 12, d)
        lon = sun_longitude(_kst_midnight_jd(day))
        if prev is not None and prev < 270 <= lon:
            return day - dt.timedelta(days=1)
        prev = lon
    return dt.date(year, 12, 22)


def _new_moons(year):
    """year-1 년 11월 ~ year+1 년 1월을 덮는 삭(KST 날짜) 목록."""
    k0 = math.floor(((year - 1) + 10.0 / 12 - 2000) * 12.3685) - 2
    out = [_kst_day(new_moon_jd(i), year) for i in range(k0, k0 + 20)]
    return sorted(set(out))


def _has_major_term(a, b):
    """[a, b) 안에 중기(태양황경 30° 배수 통과)가 있는가"""
    la = sun_longitude(_kst_midnight_jd(a))
    lb = sun_longitude(_kst_midnight_jd(b))
    na = math.floor(la / 30.0)
    nb = math.floor(lb / 30.0)
    return na != nb


def lunar_months(year):
    """year 의 설~추석을 덮는 음력 달 목록.

    표준 규칙:
      1) 전년 동지가 든 달 = 11월,  그해 동지가 든 달 = 다음 11월
      2) 두 11월 사이가 13개 달이면 윤년 — 중기가 없는 첫 달이 윤달
      3) 윤달은 직전 달의 번호를 물려받는다
    반환 [(시작일, 번호, 윤달여부), ...]
    """
    ws0 = _winter_solstice(year - 1)
    ws1 = _winter_solstice(year)
    moons = _new_moons(year)

    def month_of(d):
        idx = None
        for i in range(len(moons) - 1):
            if moons[i] <= d < moons[i + 1]:
                idx = i
        return idx

    i0, i1 = month_of(ws0), month_of(ws1)
    if i0 is None or i1 is None:
        return []
    n = i1 - i0                                   # 두 11월 사이의 달 수
    leap_at = None
    if n == 13:
        for i in range(i0 + 1, i1):
            if not _has_major_term(moons[i], moons[i + 1]):
                leap_at = i
                break
        if leap_at is None:
            leap_at = i0 + 1

    out = []
    num = 11
    for i in range(i0, min(i1 + 1, len(moons) - 1)):
        if i == leap_at:
            out.append((moons[i], num, True))     # 윤달 — 번호 유지
            continue
        if i > i0:
            num = num % 12 + 1
        out.append((moons[i], num, False))
    return out


def lunar_to_solar(year, lm, ld):
    """음력 (lm월 ld일) 의 양력 날짜. 윤달은 쓰지 않는다."""
    for start, num, leap in lunar_months(year):
        if num == lm and not leap:
            return start + dt.timedelta(days=ld - 1)
    return None


# ---------------------------------------------------------------- 휴장일
def holidays(year):
    """그해 증시 휴장일 {date: 사유}"""
    H = {}

    def add(d, why):
        if d and d.year == year:
            H.setdefault(d, why)

    for m, d, nm in FIXED:
        lo, hi = ERA.get(nm, (1900, 9999))
        if lo <= year <= hi:
            add(dt.date(year, m, d), nm)

    seol = lunar_to_solar(year, 1, 1)
    if seol:
        for off, nm in ((-1, '설날'), (0, '설날'), (1, '설날')):
            add(seol + dt.timedelta(days=off), nm)
    chu = lunar_to_solar(year, 8, 15)
    if chu:
        for off in (-1, 0, 1):
            add(chu + dt.timedelta(days=off), '추석')
    bud = lunar_to_solar(year, 4, 8)
    add(bud, '부처님오신날')

    # 대체공휴일 — 주말과 겹칠 때, 그리고 공휴일끼리 겹칠 때
    base = []
    for m, d, nm in FIXED:
        lo, hi = ERA.get(nm, (1900, 9999))
        if lo <= year <= hi:
            base.append((dt.date(year, m, d), nm))
    if seol:
        base += [(seol + dt.timedelta(days=o), '설날') for o in (-1, 0, 1)]
    if chu:
        base += [(chu + dt.timedelta(days=o), '추석') for o in (-1, 0, 1)]
    if bud:
        base.append((bud, '부처님오신날'))

    seen = {}
    for d, why in sorted(base):
        yfrom = SUB_FROM.get(why)
        if yfrom is None or year < yfrom:
            seen.setdefault(d, why)
            continue
        overlap = d in seen and seen[d] != why      # 공휴일끼리 겹침
        weekend = (d.weekday() == 6) if why in ('설날', '추석') else (d.weekday() >= 5)
        seen.setdefault(d, why)
        if not (weekend or overlap):
            continue
        n = d + dt.timedelta(days=1)
        while n in H or n.weekday() >= 5:
            n += dt.timedelta(days=1)
        H[n] = why + ' 대체'

    # 임시공휴일·선거일
    for k, why in SPECIAL.items():
        d = dt.date.fromisoformat(k)
        if d.year == year:
            H[d] = why

    # 연말 증시 휴장 (12월 마지막 영업일)
    d = dt.date(year, 12, 31)
    while d.weekday() >= 5 or d in H:
        d -= dt.timedelta(days=1)
    H[d] = '연말 휴장'

    return {k: v for k, v in sorted(H.items()) if k.weekday() < 5}


# ---------------------------------------------------------------- 검증
def actual_holidays():
    import pandas as pd
    p = 'data/hist/kr__5EKS11.csv'
    d = pd.read_csv(p, parse_dates=['Date'])
    days = pd.DatetimeIndex(sorted(d['Date'].unique()))
    bd = pd.bdate_range(days[0], days[-1])
    return {t.date() for t in bd.difference(days)}, days[0].date(), days[-1].date()


def verify(y0=2005, y1=2026):
    act, lo, hi = actual_holidays()
    print('KOSPI 실거래일 기준 실제 휴장일 대조 (%d ~ %d)' % (y0, y1))
    print('%-6s %6s %6s %8s %8s   %s' % ('연도', '계산', '실제', '거짓양성', '거짓음성', '불일치'))
    tot_fp = tot_fn = 0
    for y in range(y0, y1 + 1):
        if dt.date(y, 12, 31) < lo or dt.date(y, 1, 1) > hi:
            continue
        calc = set(holidays(y))
        real = {d for d in act if d.year == y}
        if y == hi.year:
            calc = {d for d in calc if d <= hi}
            real = {d for d in real if d <= hi}
        fp = sorted(calc - real)
        fn = sorted(d for d in (real - calc) if d.isoformat() not in KNOWN_GAPS)
        gaps = sorted(d for d in (real - calc) if d.isoformat() in KNOWN_GAPS)
        tot_fp += len(fp); tot_fn += len(fn)
        msg = ''
        if fp:
            msg += '+' + ','.join(d.strftime('%m-%d') for d in fp) + ' '
        if fn:
            msg += '-' + ','.join(d.strftime('%m-%d') for d in fn)
        if gaps:
            msg += '  (결측의심 ' + ','.join(d.strftime('%m-%d') for d in gaps) + ')'
        print('%-6d %6d %6d %8d %8d   %s' % (y, len(calc), len(real), len(fp), len(fn), msg))
    print('\n합계  거짓양성 %d  거짓음성 %d' % (tot_fp, tot_fn))
    print('  + 는 "쉰다고 했는데 실제로는 열었다", - 는 "열린다고 했는데 실제로는 쉬었다"')
    print('  (결측의심) 은 Yahoo 국내 시계열 전부에서 빠진 날 — 어떤 공휴일에도 해당하지 않는다')
    return tot_fp, tot_fn


def emit(y0=None, y1=None, path='data/kr_holidays.json'):
    y0 = y0 or dt.date.today().year
    y1 = y1 or (y0 + 6)
    out = {}
    for y in range(y0, y1 + 1):
        for d, why in holidays(y).items():
            out[d.isoformat()] = why
    payload = dict(
        generated_at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        range=[y0, y1],
        note='deploy/kr_holidays.py 산출물. 임시공휴일·선거일은 SPECIAL 에 손으로 넣는다.',
        holidays=out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print('→ %s  (%d일, %d~%d)' % (path, len(out), y0, y1))
    return payload


if __name__ == '__main__':
    if '--emit' in sys.argv:
        emit()
    else:
        verify()
