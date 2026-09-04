# -*- coding: utf-8 -*-
"""
[통합 연구 Part 2·4, 2026-08-31] 혼합 원리의 일반화 — 「전략 간 분산」은
B×T4 에 특유한가, 아무 희석에나 생기는가.

대조군 (해석의 핵심 — 이게 통과하면 고원은 마법이 아니라 그냥 디레버리징):
  C1  B×T-bill    x·B + (1−x)·T-bill      (수비수가 무수익 현금)
  C2  B×mix       x·B + (1−x)·방어mix 상시 (수비수가 정적 자산)
일반화 후보 (수비수가 「다른 전략」):
  G1  B×A         A = hypo_gates 다자산 리스크패리티×추세 (상관 낮음, ② 참패했던 그 전략)
  G2  B×T4×A      3전략 균등 + 0.4/0.4/0.2
검증 규율 (섹션 15):
  WFA — 5년마다 과거 데이터로 x*(Calmar 최대)를 고르고 다음 5년에 적용,
  1992~ 이어붙인 곡선을 같은 기간 B 와 비교. x* 경로의 안정성도 기록.
판정 아님(v80) — 원리 규명 전용. 실행: python research/cand_general.py
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

import hypo_gates as G                                  # noqa: E402
import hypo_hex as X                                    # noqa: E402
import hypo_t4_real as R                                # noqa: E402

idx = G.idx
n = len(idx)
wT4 = R.t4_w(G.r_eq1)


def rets(curve):
    a = np.asarray(curve, float)
    return np.diff(a, prepend=1.0) / np.concatenate(([1.0], a[:-1]))


def p05(a, w=5040):
    a = np.asarray(a, float)
    if len(a) <= w:
        return np.nan
    return float(np.quantile(a[w:] / a[:-w], 0.05))


def calmar(a):
    a = np.asarray(a, float)
    peak = np.maximum.accumulate(a)
    m = abs(float(np.min(a / peak - 1)))
    return (a[-1] ** (252.0 / len(a)) - 1) / max(m, 1e-9)


def scan(nm, rD, rB, g1, g2):
    """수비수 일수익 rD 와 B 를 x 격자로 혼합 — 관문 동시 통과 칸 나열."""
    rho = float(np.corrcoef(rB, rD)[0, 1])
    passes = []
    line = []
    for x in np.arange(0.30, 0.951, 0.05):
        a = np.cumprod(1 + x * rB + (1 - x) * rD)
        c, p = calmar(a), p05(a)
        ok = c > g1 and p >= g2
        if ok:
            passes.append(round(float(x), 2))
        line.append((float(x), a[-1], c, p, ok))
    print(f'\n  [{nm}] 상관(B,수비수) {rho:+.3f}')
    print(f"  {'x':>5} {'최종배수':>12} {'Calmar':>7} {'p05':>6} {'①②':>4}")
    for x, f, c, p, ok in line:
        print(f"  {x:>5.2f} {f:>12.1f} {c:>7.3f} {p:>6.1f} {'★' if ok else '·':>4}")
    print(f'  동시 통과: {passes if passes else "없음"}'
          f' ({len(passes)}칸{" — 고원" if len(passes) >= 3 else ""})')
    return passes


def wfa(rB, rT, label):
    """5년 걸음 WFA — 과거로 x* 선택, 다음 5년 적용 (x 후보 0.05~0.95)."""
    ystart = 1992
    bd = pd.Series(idx).searchsorted(
        [pd.Timestamp(f'{y}-01-01') for y in range(ystart, 2027, 5)])
    xs = np.arange(0.05, 0.951, 0.05)
    out = []
    picks = []
    for k in range(len(bd)):
        tr_end = bd[k]
        te_end = bd[k + 1] if k + 1 < len(bd) else n
        if te_end <= tr_end:
            break
        best_x, best_c = None, -9
        for x in xs:
            c = calmar(np.cumprod(1 + x * rB[:tr_end] + (1 - x) * rT[:tr_end]))
            if c > best_c:
                best_c, best_x = c, float(x)
        picks.append(f'{idx[tr_end].year}:x={best_x:.2f}')
        out.append(best_x * rB[tr_end:te_end] + (1 - best_x) * rT[tr_end:te_end])
    ro = np.concatenate(out)
    s = bd[0]
    aW, aB = np.cumprod(1 + ro), np.cumprod(1 + rB[s:])
    print(f'\n  [WFA {label}] 1992~ 이어붙임: 배수 {aW[-1]:.1f} (B {aB[-1]:.1f}) · '
          f'Calmar {calmar(aW):.3f} (B {calmar(aB):.3f})')
    print(f'  x* 경로: {" ".join(picks)}')


def main():
    cB = X.three_way(X.wB, 1 - X.wB, np.zeros(n))
    cT = X.three_way(wT4, np.zeros(n), 1 - wT4)
    rB, rT = rets(cB.values), rets(cT.values)
    g1 = calmar(cB.values) * 1.102
    g2 = p05(cB.values)
    print(f'[관문① Calmar > {g1:.3f} · ② p05 ≥ {g2:.1f} · 전창 54년 · 편도 0.1%]')

    # 수비수들
    r_tb = G.tb
    # [2026-09-04 코드리뷰] 종전엔 rets(np.cumprod(1 + r)) 로 수익→곡선→수익을 왕복했다.
    # rets 정의상 그 왕복은 입력을 그대로 되돌려준다(첫 원소 포함) — 배열 두 개와
    # 나눗셈만 버리고, 읽는 사람은 무슨 정규화가 있는 줄 알고 확인해야 했다.
    # G.Dm['schdr'] 은 이미 일수익 계열이다.
    r_mx = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    legsA = [(G.r_eq1, G.r_eq1, 1.0), (G.r_b10, G.r_b3x, 3.0), (G.r_gld, G.r_gld, 1.0)]
    cA = G.sim_multi(legsA)
    rA = rets(cA.values)

    scan('C1 대조: B×T-bill', r_tb, rB, g1, g2)
    scan('C2 대조: B×정적mix', r_mx, rB, g1, g2)
    scan('참고: B×T4 (원 고원)', rT, rB, g1, g2)
    pA = scan('G1: B×A(다자산추세)', rA, rB, g1, g2)
    rTA = (rT + rA) / 2
    scan('G2a: B×(T4+A 반반)', rTA, rB, g1, g2)
    # G2b 고정 3전략: 0.4B+0.4T4+0.2A — 단일점 보고
    a = np.cumprod(1 + 0.4 * rB + 0.4 * rT + 0.2 * rA)
    print(f'\n  [G2b 0.4B+0.4T4+0.2A] 최종 {a[-1]:.1f} · Calmar {calmar(a):.3f} · '
          f'p05 {p05(a):.1f} · {"★ 동시 통과" if calmar(a) > g1 and p05(a) >= g2 else "탈락"}')

    # WFA — x 선택이 사전에 가능했는가
    wfa(rB, rT, 'B×T4')
    if pA:
        wfa(rB, rA, 'B×A')

    print('\n(해석 지침: C1/C2 가 통과하면 고원=일반 디레버리징 — T4 특유성 없음.'
          '\n C 탈락 + G 통과면 「수비수가 전략일 것」이 조건 — 전략 간 분산 원리.)')


if __name__ == '__main__':
    main()
