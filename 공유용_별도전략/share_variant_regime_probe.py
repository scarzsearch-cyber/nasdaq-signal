# -*- coding: utf-8 -*-
"""
[공유용 변형 — SCHD 강세 구간 실측, 2026-09-02]
소유자 질문: "SCHD가 강세인 순간들이 분명 있었잖아. 당장 최근에만 해도 SCHD가 강했고."

★ 확인부터 한다 — 유리한 창을 손으로 고르는 것은 이 저장소가 금지한 짓이다
  (CLAUDE.md §-1 ⓑ: 구간을 손으로 고르면 반드시 분포로 반증).
  그래서 이 파일은 "SCHD가 이긴 구간을 찾아 넣자"가 아니라
  **"언제 이겼는지를 사실대로 뽑아본다"** 이다. 결과를 보고 판단은 그 다음.

낸다:
  [1] 최근 단기 창(1·2·3·5년) — "요즘 SCHD가 강했다" 가 참인가
  [2] 달력연도별 수익률 — 어느 해에 SCHD가 이겼나
  [3] SCHD가 QQQ를 이긴 구간을 **자동으로** 찾아낸다(연속 구간 추출)

실행: python 공유용_별도전략/share_variant_regime_probe.py
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

import hist_defensive as DF                                # noqa: E402
import hist_defasset as DA                                 # noqa: E402
import eng_common as EC                                     # noqa: E402

# 실물 SCHD 는 2011-10-25 상장. 그 이전은 대리(French 배당 포트폴리오)라
# "요즘" 질문에는 실물 구간이 정직하다. 둘 다 쓰되 구분해 표기한다.
SCHD_REAL = '2011-10-25'

D = dict(DF.build('chain', start='1990-01-01'))
idx = D['idx']
px = pd.Series(D['px'], index=idx)
r_qqq = np.nan_to_num(px.pct_change().values)
r_div = np.asarray(D['schdr'], float)

S = pd.Series(np.cumprod(1 + r_div), index=idx)     # SCHD(체인)
Q = pd.Series(np.cumprod(1 + r_qqq), index=idx)     # QQQ


def cagr(s, a, b):
    z = s.loc[a:b]
    if len(z) < 2:
        return np.nan
    yrs = (z.index[-1] - z.index[0]).days / 365.25
    return (z.iloc[-1] / z.iloc[0]) ** (1 / yrs) - 1


def main():
    EC.selfcheck()
    end = idx[-1]
    print(f'\n데이터 끝: {end.date()} · SCHD 실물 시작 {SCHD_REAL}\n')

    print('[1] 최근 단기 창 — "요즘 SCHD가 강했다" 검증')
    print(f"{'창':<8}{'구간':<26}{'SCHD%':>9}{'QQQ%':>9}{'차이%p':>9}  판정")
    for y in (1, 2, 3, 5, 7, 10):
        a = (end - pd.DateOffset(years=y))
        cs, cq = cagr(S, a, end) * 100, cagr(Q, a, end) * 100
        d = cs - cq
        print(f"{str(y)+'년':<8}{str(a.date())+'~'+str(end.date()):<26}"
              f"{cs:>9.2f}{cq:>9.2f}{d:>9.2f}  {'SCHD 승' if d > 0 else 'QQQ 승'}")

    print('\n[2] 달력연도별 수익률 (SCHD 실물 구간 2012~)')
    print(f"{'연도':<8}{'SCHD%':>9}{'QQQ%':>9}{'차이%p':>9}  판정")
    yrs = sorted(set(idx.year))
    schd_wins = []
    for y in yrs:
        if y < 2012:
            continue
        seg_s = S[S.index.year == y]
        seg_q = Q[Q.index.year == y]
        if len(seg_s) < 100:
            continue
        rs = (seg_s.iloc[-1] / seg_s.iloc[0] - 1) * 100
        rq = (seg_q.iloc[-1] / seg_q.iloc[0] - 1) * 100
        w = rs > rq
        if w:
            schd_wins.append(y)
        print(f"{y:<8}{rs:>9.2f}{rq:>9.2f}{rs-rq:>9.2f}  {'SCHD 승' if w else ''}")
    print(f'  → SCHD 가 이긴 해: {schd_wins}')

    print('\n[3] SCHD 가 QQQ 를 이긴 연속 구간 — 자동 추출 (상대강도 상승 구간)')
    # 상대강도 RS = SCHD/QQQ. RS 가 오르는 동안 SCHD 우세.
    rs = (S / Q)
    rs_m = rs.resample('ME').last()
    up = rs_m > rs_m.shift(1)
    runs, cur = [], None
    for t, v in up.items():
        if v and cur is None:
            cur = t
        elif not v and cur is not None:
            runs.append((cur, t))
            cur = None
    if cur is not None:
        runs.append((cur, rs_m.index[-1]))
    # 3개월 이상 이어진 구간만, 상대우위 큰 순
    keep = []
    for a, b in runs:
        months = (b.year - a.year) * 12 + (b.month - a.month)
        if months < 3:
            continue
        gain = (rs.loc[:b].iloc[-1] / rs.loc[:a].iloc[-1] - 1) * 100
        keep.append((a, b, months, gain))
    keep.sort(key=lambda x: -x[3])
    print(f"{'시작':<10}{'끝':<10}{'개월':>5}{'SCHD 상대우위%':>15}")
    for a, b, m, g in keep[:12]:
        print(f"{str(a.date())[:7]:<10}{str(b.date())[:7]:<10}{m:>5}{g:>15.1f}")


if __name__ == '__main__':
    main()
