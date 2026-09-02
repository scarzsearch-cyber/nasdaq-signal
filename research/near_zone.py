# -*- coding: utf-8 -*-
"""
[운영 측정] 낙폭 게이지 「근접」 구간의 빈도 — 근접 알림(v192)의 근거 (2026-09-02)

질문: 화면 게이지가 「근접」(전환선까지 3%p 미만)에 들어서는 일이 얼마나 잦고,
      그중 얼마가 실제 전환으로 이어지나? → 알림을 「근접 진입」에 걸면 연 몇 번 오고
      몇 번이 헛걸음인가.

전략 변경 0. 규칙·문턱·룩백 무접촉 — 이미 있는 판정(w)의 **위치**만 센다.

정의 (signal.html paintProx 와 같은 값 — 화면과 다른 기준을 만들지 않는다):
  gap  = |dd − 전환선| × 100  [%p]   (진입선=복귀선=−16% 라 양 상태에서 같은 식)
  여유 gap ≥ 8 · 접근 3 ≤ gap < 8 · 근접 gap < 3
  「진입」 = 전날은 그 구간이 아니었는데 오늘 그 구간인 날.
  「전환으로 이어짐」 = 근접 에피소드 시작 ~ 종료 + 20거래일 안에 상태 전환 1회 이상.

엔진: eng_common.selfcheck() 의 QQQ 체인(1972~ 54년) — 검산 통과 못 하면 즉시 중단.
실행: python research/near_zone.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                 # noqa: E402

TH = -0.16
NEAR, APPROACH = 3.0, 8.0          # signal.html paintProx: gap>=8 여유 · >=3 접근 · <3 근접
FOLLOW = 20                        # 「전환으로 이어짐」 창(거래일)
PRE = 5                            # 「전환 직전 근접이 있었나」 창(거래일)


def zones(px):
    hi = px.rolling(252, min_periods=252).max()
    dd = (px / hi - 1).dropna()
    w = pd.Series(np.asarray(EC.rule_dd(px, TH, TH), int), index=px.index).reindex(dd.index)
    gap = (dd - TH).abs() * 100
    z = np.where(gap < NEAR, 'near', np.where(gap < APPROACH, 'approach', 'far'))
    return dd, w, gap, pd.Series(z, index=dd.index)


def stats(px, label):
    dd, w, gap, z = zones(px)
    yrs = (dd.index[-1] - dd.index[0]).days / 365.25
    sw = (w != w.shift(1)).astype(int); sw.iloc[0] = 0
    n_sw = int(sw.sum())
    print(f'\n[{label}] {dd.index[0].date()} ~ {dd.index[-1].date()} · {yrs:.1f}년 · {len(dd):,}일 · 전환 {n_sw}회 (연 {n_sw/yrs:.2f})')
    print(f'  {"구간":6s} {"일수":>7s} {"비율":>6s} {"연 일수":>7s} {"진입":>5s} {"연 진입":>7s}')
    for k, nm in (('near', '근접'), ('approach', '접근')):
        days = int((z == k).sum()); ent = int(((z == k) & (z.shift(1) != k)).sum())
        print(f'  {nm:6s} {days:7,d} {days/len(dd)*100:5.1f}% {days/yrs:7.1f} {ent:5d} {ent/yrs:7.2f}')
    near = (z == 'near')
    starts = np.where((near & ~near.shift(1, fill_value=False)).values)[0]
    lens, led = [], 0
    for i in starts:
        j = i
        while j < len(dd) and near.iloc[j]:
            j += 1
        lens.append(j - i)
        if sw.iloc[i:min(j + FOLLOW, len(dd))].sum() > 0:
            led += 1
    idx = np.where(sw.values == 1)[0]
    pre = sum(1 for i in idx if near.iloc[max(0, i - PRE):i].any())
    jump = sum(1 for i in idx if (z.iloc[max(0, i - PRE):i] == 'far').all())
    print(f'  근접 에피소드 {len(starts)}회 · {FOLLOW}일 안 전환으로 이어짐 {led} ({led/len(starts)*100:.0f}%) '
          f'· 길이 중앙 {np.median(lens):.0f}일 · p90 {np.percentile(lens, 90):.0f}일')
    print(f'  전환 {n_sw}회 중 직전 {PRE}일 안에 근접이 있었던 것 {pre} ({pre/max(n_sw,1)*100:.0f}%) '
          f'· 직전 {PRE}일 내내 「여유」였다가 곧바로 전환 {jump}회')
    return dict(years=yrs, near_entries=len(starts), near_per_year=len(starts) / yrs,
                led=led, led_pct=led / len(starts) * 100, pre_pct=pre / max(n_sw, 1) * 100,
                jump=jump, len_med=float(np.median(lens)), len_p90=float(np.percentile(lens, 90)))


def main():
    G, X = EC.selfcheck()
    px = pd.Series(G.D['px'], index=G.idx).astype(float)
    print('=' * 92)
    print('근접 구간 빈도 — 근접 알림(watchdog near)의 근거 · 전략 무접촉 (research/near_zone.py)')
    print('=' * 92)
    r = stats(px, 'QQQ 체인(엔진 표본)')
    # 교차 확인: 실물 NDX 지수(FRED, 1986~) — 체인 접합의 산물이 아닌지
    p2 = _os.path.join('data', 'hist', 'fred_NASDAQ100.csv')
    if _os.path.exists(p2):
        d = pd.read_csv(p2)
        d.columns = [c.lower() for c in d.columns]
        dc = [c for c in d.columns if 'date' in c][0]; vc = [c for c in d.columns if c != dc][0]
        d[dc] = pd.to_datetime(d[dc]); d[vc] = pd.to_numeric(d[vc], errors='coerce')
        s2 = d.dropna(subset=[vc]).set_index(dc)[vc].sort_index()
        stats(s2, 'NDX 실물 지수 (FRED 1986~) — 교차 확인')

    print('\n판정(사전 등록 · 알림 설계 기준):')
    print(f'  근접 진입 연 {r["near_per_year"]:.1f}회 · 그중 {r["led_pct"]:.0f}% 가 {FOLLOW}일 안 전환 · '
          f'전환의 {r["pre_pct"]:.0f}% 는 직전 {PRE}일 안에 근접을 거침 · 「여유」에서 곧바로 전환 {r["jump"]}회')
    print('  → 근접 진입에 알림을 걸면 실제 전환은 거의 전부 그 알림 뒤에 오고, 헛걸음은 연 '
          f'{r["near_per_year"]*(1-r["led_pct"]/100):.1f}회 수준. 「접근」까지 넓히면 알림 피로(연 9회↑).')
    print('\n이 측정이 낳은 다음 질문 (CLAUDE.md §-1 절대멈춤 6):')
    print('  · 근접 알림이 「미리 팔기」(재량 개입)를 실제로 유발하는가 — 동결 이후 체결 기록의 D+n 이 음수(신호 전 체결)로')
    print('    나타나는지로 잰다. 답이 없으면 04 §7 대장(미결) — 사건이 쌓여야 잴 수 있다.')
    print('  · 근접 에피소드의 44% 가 되돌아간다 — 그 되돌림에서 규칙은 아무것도 하지 않는다(맞다). 알림 문구가 「아직 할 일')
    print('    없음」을 먼저 말해야 하는 이유. 문구 규약은 deploy/watchdog.py mode_near 참조.')


if __name__ == '__main__':
    main()
