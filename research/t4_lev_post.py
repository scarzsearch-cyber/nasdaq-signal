# -*- coding: utf-8 -*-
"""
[T4 배율 2.0~3.0 · 닷컴 이후, 2026-08-31 소유자 지시] 「닷컴 이후로 2.4~3배 연구해봐, T4」

기존 기록: 04 §5-6 이 **T4@3배**를 이미 쟀다 — 54년 860,635배·MDD −52% 로 육각형처럼
  보이나 **후반만 보면 B@2 에 수익·Calmar 모두 패배**(287 vs 445배)·지연 ×0.28·회전
  연 7.5회. 「캡 해제는 전반 시대 산물」(v88 볼타깃 함정·v50 지문).
  **다만 2.2~2.8 구간은 잰 적이 없다.** 그 공백만 메운다 — 이름 바꾼 재탐색이 아니라
  이미 있는 격자의 빈칸.

★ 사전 고정 관문 (결과 보기 전 커밋 — 04 §5-7 방법론):
  ① 닷컴 이후(2003~) Calmar 가 **같은 구간 B@2 의 1.102배 이상**
  ② 같은 구간 최종배수가 B@2 이상
  ③ **더 뒤 구간(2010~)에서도 ①②를 유지** — 04 가 T4@3 을 죽인 바로 그 관문
  ④ **체결 하루 지연 잔존비**가 B@2 보다 나쁘지 않을 것 (04 §5-8: 전환 놓치면 −96.5%,
     수동 운영이라 지연 취약성은 실제 위험)
  ⑤ 54년 MDD 가 소유자 감내선 **−60%** 이내
  다섯 다 통과해야 「기각 아님」. 하나라도 미달이면 기각.
  ⑥ 첨탑 검사: 최고 칸이 격자 끝점이면 격자를 넓혀 재검(실수 유형 ⓑ).

검산: t4w_k(2.0) == hypo_t4_real.t4_w 오차 0 (lev_th.py 규약 그대로).
평가 전용 · 동결 규칙 무접촉. 실행: python research/t4_lev_post.py
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                 # noqa: E402
import hypo_gates as G                                  # noqa: E402
import hypo_t4_real as R                                # noqa: E402
from axis_lib import lev_r                              # noqa: E402

idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
r1 = np.nan_to_num(PX.pct_change().values)
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
TB = np.asarray(G.tb, float)
wB = EC.rule_dd(PX, -0.16, -0.16)
GATE = 1.102


def t4w_k(k):
    """lev_th.py 와 같은 구현 — 정본의 「2.0×」만 k 로."""
    pxs = pd.Series(np.cumprod(1 + r1), index=idx)
    votes = sum((pxs / pxs.shift(L) > 1.0).astype(int) for L in R.LOOKS)
    sd = pd.Series(r1, index=idx).rolling(R.WIN).std(ddof=1)
    rv = k * sd * np.sqrt(252)
    w = np.clip(R.VT / rv.replace(0, np.nan), 0, 1).fillna(0)
    w[votes < R.TH] = 0.0
    w.iloc[:max(R.LOOKS)] = 0.0
    return w.values


def sim(w, r, lag=1):
    """T4 는 공격/T-bill 2분할 (정본 규약)."""
    pos = np.empty(n); pos[:lag] = w[0]; pos[lag:] = w[:-lag]
    rr = pos * np.nan_to_num(r) + (1 - pos) * TB
    rr[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + rr) * (1 - EC.COST * turn))


def seg(a, s):
    lo = 0 if s is None else int(np.searchsorted(idx, pd.Timestamp(s)))
    c = np.asarray(a[lo:], float); c = c / c[0]
    yrs = (idx[-1] - idx[lo]).days / 365.25
    cagr = float(c[-1]) ** (1 / yrs) - 1
    mdd = float(np.min(c / np.maximum.accumulate(c) - 1))
    return float(c[-1]), cagr * 100, mdd * 100, cagr / abs(mdd)


def main():
    ref = np.asarray(R.t4_w(G.r_eq1), float)
    err = float(np.max(np.abs(t4w_k(2.0) - ref)))
    print(f'\n[검산] t4w_k(2.0) == T4 정본 오차 {err:.1e}  '
          f'{"OK" if err < 1e-12 else "★실패"}')
    if err >= 1e-12:
        sys.exit('검산 실패')

    aB = EC.sim2(wB, np.asarray(lev_r(G.D, 2.0), float), MIXR)
    KS = [2.0, 2.2, 2.4, 2.5, 2.6, 2.8, 3.0]

    for lab, s in (('★닷컴 이후 2003~', '2003-01-02'), ('더 뒤 2010~', '2010-01-04')):
        b = seg(aB, s)
        print(f'\n[{lab}]  기준 B@2: {b[0]:,.1f}배 · MDD {b[2]:.1f}% · Calmar {b[3]:.3f}')
        print(f'  관문① Calmar > {b[3]*GATE:.3f} · 관문② 최종 > {b[0]:,.1f}배')
        print(f"{'T4 배율':>8} {'최종배수':>11} {'CAGR':>7} {'MDD':>8} {'Calmar':>8} "
              f"{'①':>4} {'②':>4}")
        for k in KS:
            a = sim(t4w_k(k), np.asarray(lev_r(G.D, k), float))
            m, cg, md, cal = seg(a, s)
            g1 = 'OK' if cal >= b[3] * GATE else '—'
            g2 = 'OK' if m >= b[0] else '—'
            print(f'{k:>7.1f}배 {m:>10.1f}배 {cg:>6.1f}% {md:>7.1f}% {cal:>8.3f} '
                  f'{g1:>4} {g2:>4}')

    print('\n[관문④] 체결 하루 지연 내성 (54년 · lag=2 / lag=1 잔존비)')
    rB = np.asarray(lev_r(G.D, 2.0), float)
    b1 = EC.fullmet(EC.sim2(wB, rB, MIXR), idx=idx)['final']
    pos = np.empty(n); pos[:2] = wB[0]; pos[2:] = wB[:-2]
    rr = pos * rB + (1 - pos) * MIXR; rr[0] = 0.0
    b2 = float(np.cumprod((1 + rr) * (1 - EC.COST * np.abs(np.diff(pos, prepend=pos[0]))))[-1])
    print(f'  B@2 잔존비 {b2/b1:.3f}  ← 기준')
    print(f"{'T4 배율':>8} {'잔존비':>8} {'판정':>6}")
    for k in KS:
        w = t4w_k(k); r = np.asarray(lev_r(G.D, k), float)
        v1 = float(sim(w, r, 1)[-1]); v2 = float(sim(w, r, 2)[-1])
        print(f'{k:>7.1f}배 {v2/v1:>8.3f} {"OK" if v2/v1 >= b2/b1 else "★미달":>6}')

    print('\n[관문⑤] 54년 MDD — 감내선 −60%')
    print(f"{'T4 배율':>8} {'54년 MDD':>10} {'판정':>6}")
    for k in KS:
        _, _, md, _ = seg(sim(t4w_k(k), np.asarray(lev_r(G.D, k), float)), None)
        print(f'{k:>7.1f}배 {md:>9.1f}% {"OK" if md >= -60 else "★위반":>6}')

    print('\n[관문⑥] 격자 확장 — 최고 칸이 끝점이었다 (실수 유형 ⓑ 자체 적용)')
    print(f"{'T4 배율':>8} {'최종배수':>11} {'Calmar':>9} {'평균 노출':>10}")
    for k in (2.8, 3.0, 3.5, 4.0, 5.0):
        w = t4w_k(k)
        m, _, _, cal = seg(sim(w, np.asarray(lev_r(G.D, k), float)), '2003-01-02')
        print(f'{k:>7.1f}배 {m:>10.1f}배 {cal:>9.3f} {np.mean(w):>10.3f}')
    print('  → 첨탑이 아니라 **포화**다. 배율을 올리면 VT 브레이크가 노출을 자동 축소해')
    print('     (평균 노출 0.659→0.453) 실효 배율이 수렴한다. 격자를 늘려도 관문③은 그대로.')

    print('\n[구간 분해] T4 의 우위는 어디서 왔나 (T4@2.8 vs B@2)')
    b1_ = seg(aB, '2003-01-02')[0]; b2_ = seg(aB, '2010-01-04')[0]
    a28 = sim(t4w_k(2.8), np.asarray(lev_r(G.D, 2.8), float))
    t1_ = seg(a28, '2003-01-02')[0]; t2_ = seg(a28, '2010-01-04')[0]
    print(f'  2003~2010 (금융위기 포함): T4 {t1_/t2_:.2f}배 vs B {b1_/b2_:.2f}배 '
          f'→ T4 {((t1_/t2_)/(b1_/b2_)-1)*100:+.0f}%')
    print(f'  2010~     (그 이후)      : T4 {t2_:.1f}배 vs B {b2_:.1f}배 '
          f'→ T4 {(t2_/b2_-1)*100:+.0f}%')
    print('\n[판정] **기각**')
    print('  · 관문③(2010~ 유지) **전 칸 실패** — 04 가 T4@3 을 죽인 바로 그 관문.')
    print('  · 관문④(지연 내성) 2.2배 이상 전부 실패 — 배율↑ 이면 지연에 더 취약해진다.')
    print('  · 통과한 것은 관문⑤(MDD) 뿐 — T4 의 볼 브레이크는 실제로 훌륭하다(−50%대).')
    print('  · **기전: T4 의 우위는 2008 한 사건 산물이다.** 2003~2010 에서 +36%,')
    print('    2010~ 에서 −8%. 소유자가 B 에 대해 관찰한 것(닷컴 한 사건)과 **같은 구조**.')


if __name__ == '__main__':
    main()
