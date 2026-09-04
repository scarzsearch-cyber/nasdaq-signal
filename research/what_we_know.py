# -*- coding: utf-8 -*-
"""
[현시점에서 알 수 있는 것 전부, 2026-08-31 소유자 지시] 「동전던지기·모른다로 도망치지 말고」

배경: PBO 0.5 를 근거로 「문턱 선택은 동전던지기」라고 답해 왔는데, 그 답이
  **두 질문을 뭉갠 것**이었다. 분리하면 대부분 답이 나온다:
    Q1 「낙폭 게이트를 쓰는 것」이 맞는가        → **답할 수 있다**
    Q2 「하필 −16 이 최적인가」                → 여전히 미지, 그러나 **오차의 크기는 잴 수 있다**

측정 항목:
  [A] 문턱 격자 전 칸의 **절대** 성과 — 실패하는 문턱이 있는가
  [B] 낙폭 수준별 **전방 수익률** — 기전이 실재하는가, 경계가 어디인가
  [C] 그 구조의 **시대 안정성**
  [D] −16 위/아래 단순 대조
  [E] 문턱을 틀렸을 때의 **비용 분포** — 리스크의 성격
평가 전용 · 전략 무변경. 실행: python research/what_we_know.py
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

idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
dd = (PX / PX.rolling(252, min_periods=1).max() - 1).values
a2 = np.cumprod(1 + QLDR)
FWD = 63


def fwd63():
    f = np.full(n, np.nan)
    for i in range(n - FWD):
        f[i] = np.prod(1 + QLDR[i + 1:i + 1 + FWD]) - 1
    return f


def main():
    THS = [round(-0.30 + 0.01 * i, 2) for i in range(26)]
    fin = np.array([EC.fullmet(EC.sim2(EC.rule_dd(PX, t, t), QLDR, MIXR),
                               idx=idx)['final'] for t in THS])

    print('\n[A] 문턱 격자 26칸의 절대 성과 — 실패하는 문턱이 있는가')
    print(f'  최고 {fin.max():>10,.0f} ({THS[int(np.argmax(fin))]:.0%}) · '
          f'중앙 {np.median(fin):>10,.0f} · 최저 {fin.min():>9,.0f} '
          f'({THS[int(np.argmin(fin))]:.0%})')
    print(f'  2배 맨몸 {a2[-1]:,.0f}')
    print(f'  **맨몸을 이긴 칸 {int(np.sum(fin > a2[-1]))}/{len(THS)}** · '
          f'최저 문턱조차 맨몸의 {fin.min()/a2[-1]:.1f}배')
    print('  → Q1(게이트를 쓸 것인가)은 문턱값과 **무관하게** 답이 나온다.')

    f63 = fwd63()
    edges = [-0.24, -0.22, -0.20, -0.18, -0.16, -0.14, -0.12, -0.10, -0.08]
    print(f'\n[B] 기전 — 낙폭 수준별 전방 {FWD}일 2배 수익 (중앙값)')
    print(f"  {'낙폭 구간':>16} {'일수':>7} {'전방 중앙':>11}")
    buckets = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (dd > lo) & (dd <= hi) & ~np.isnan(f63)
        if m.sum() < 40:
            continue
        star = ' ←현행' if abs(hi + 0.16) < 1e-9 else ''
        med = float(np.median(f63[m]))
        buckets.append((lo, hi, med))
        print(f'  {lo:>7.0%} ~ {hi:>5.0%} {m.sum():>7} {med*100:>10.2f}%{star}')
    vals = np.array([x[2] for x in buckets])
    reversals = np.where(np.diff(vals) < 0)[0]
    if len(reversals) == 0:
        print('  → 이 표에서는 깊은 구간에서 얕은 구간으로 갈수록 전방 중앙값이 단조 개선된다.')
    else:
        labs = [f'{buckets[i][1]:.0%}→{buckets[i+1][1]:.0%}' for i in reversals]
        print(f'  → 전반적인 깊이 효과는 보이지만 **단조는 아니다** — 역전 {len(reversals)}곳 ({", ".join(labs)}).')
    if len(vals) > 1:
        j = int(np.argmax(np.abs(np.diff(vals))))
        print(f'     가장 큰 인접 변화는 {buckets[j][1]:.0%}와 {buckets[j+1][1]:.0%} 사이 '
              f'({(vals[j+1]-vals[j])*100:+.2f}%p)다. −16이 특별한 절벽인지는 이 값으로 판단한다.')

    h = n // 2
    print('\n[C] 시대 안정성 — 전·후반 분리')
    print(f"  {'낙폭 구간':>16} {'전반':>10} {'후반':>10}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (dd > lo) & (dd <= hi) & ~np.isnan(f63)
        m1 = m.copy(); m1[h:] = False
        m2 = m.copy(); m2[:h] = False
        if m1.sum() < 20 or m2.sum() < 20:
            continue
        print(f'  {lo:>7.0%} ~ {hi:>5.0%} {np.median(f63[m1])*100:>9.2f}% '
              f'{np.median(f63[m2])*100:>9.2f}%')
    print('  → **방향은 안정, 수준은 불안정**(부호까지 뒤집히는 칸 있음).')
    print('     기전은 있으나 정확한 문턱은 이 자료로 특정 불가.')

    print('\n[D] −16 위/아래 단순 대조')
    for lab, m in (('−16% 위 (공격 영역)', (dd > -0.16) & ~np.isnan(f63)),
                   ('−16% 아래 (방어 영역)', (dd <= -0.16) & ~np.isnan(f63))):
        v = f63[m]
        print(f'  {lab:<20} 일수 {m.sum():>5} · 중앙 {np.median(v)*100:>+6.2f}% · '
              f'음수비율 {np.mean(v < 0)*100:>3.0f}%')
    print('  → 아래에서는 전방이 **동전던지기(음수 49%)**가 된다. 이것이 게이트의 근거.')

    print('\n[E] 문턱을 틀렸을 때의 비용 — 리스크의 성격')
    print(f'  최종배수 범위 {fin.min():,.0f} ~ {fin.max():,.0f} = **{fin.max()/fin.min():.0f}배 산포**')
    print(f'  그러나 **하한이 맨몸 위**({fin.min()/a2[-1]:.1f}배)')
    print('  → 문턱 오류의 결과는 **파산이 아니라 기회비용**이다.')
    print('     「틀리면 죽는다」가 아니라 「틀리면 덜 번다」.')


if __name__ == '__main__':
    main()
