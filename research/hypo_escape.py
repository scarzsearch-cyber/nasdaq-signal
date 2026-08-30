# -*- coding: utf-8 -*-
"""
[가설 실험 외전, 소유자 지시 2026-08-30] "어떤 수를 써도 좋다" — B의 손실 모드를
해부하고, 상처에만 작동하는 **폭풍 문맥 조건부 브레이크**를 격자 전체로 시험한다.

설계:  w = w_B × [ dd > TH 이면 1 (브레이크 해제 — 강세 포착 보존)
                   dd ≤ TH 이면 clip(VT/rv, 0, 1) (낙폭 진행 중에만 변동성 사이징) ]
       브레이크로 뺀 몫은 T-bill, B 방어 구간은 mix — hypo_hex.three_way 재사용.
       dd 는 규칙이 이미 쓰는 D['ddv'] 그대로(새 데이터 0), rv 는 T4 정본식.

파라미터는 고르지 않는다 — TH∈{−2,−4,−6,−8%} × VT∈{40,50,60%} 12칸 전부 공개.
이웃한 여러 칸이 관문을 같이 넘으면 고원(의미), 한 칸이면 첨탑(기각) — v41 규약.
인접 계보 명시: v32 axis_volguard(변동성 조기 전환)와 다르다 — 이건 전환이 아니라
공격 구간 내 연속 사이징이고, 발동 조건이 낙폭 문맥으로 게이트된다.

먼저 진단: B의 20년창 하위 5분위(관문②의 바닥)를 만드는 창이 언제 끝나는 창들인지.
⚠ 창 단위 비교는 판정 아님(v80). 세전 · 달러 · 거치식 · 1972-02~ 전창.
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
import hypo_hex as X                                    # noqa: E402  three_way·wB·rv 재사용

idx = G.idx
n = len(idx)
ddv = np.asarray(G.D['ddv'], float)                     # 규칙이 쓰는 그 낙폭 경로
wB = X.wB


def diagnose():
    """관문②의 바닥을 만드는 20년 창들의 정체."""
    a = G.cB.values
    w = 5040
    mult = a[w:] / a[:-w]
    ends = idx[w:]
    q = np.quantile(mult, 0.20)
    bad = ends[mult <= q]
    print(f'[진단] B 20년창 {len(mult):,}개 · 하위 5분위 경계 {q:.1f}배')
    print(f'  최악 창: {mult.min():.1f}배 (끝 {ends[mult.argmin()].date()})')
    print(f'  하위 20% 창의 끝 날짜 범위: {bad.min().date()} ~ {bad.max().date()}')
    # 연도별 분포 (하위 창이 몰린 시기)
    yrs = pd.Series(bad.year).value_counts().sort_index()
    tops = ', '.join(f'{y}({c})' for y, c in yrs.items() if c > len(bad) * 0.06)
    print(f'  몰린 연도(6%+): {tops}')


def escape(th, vt):
    vs = np.clip(vt / X.rv, 0, 1)
    vs[~np.isfinite(vs)] = 1.0
    scale = np.where(ddv > th, 1.0, vs)                 # 폭풍 문맥에서만 브레이크
    wq = wB * scale
    return X.three_way(wq, 1 - wB, wB - wq)


def main():
    diagnose()
    b = G.report('B', G.cB)
    c1, c2 = b['calmar'] * 1.102, b['q20']
    print(f'\n[격자 12칸 전부 — 관문① Calmar>{c1:.3f} · 관문② q20≥{c2:.1f}]')
    print(f"{'TH%':>5} {'VT%':>4} {'최종배수':>10} {'MDD%':>7} {'Calmar':>7} {'q20':>6} {'①':>3} {'②':>3}")
    passes = []
    for th in (-0.02, -0.04, -0.06, -0.08):
        for vt in (0.40, 0.50, 0.60):
            r = G.report('', escape(th, vt))
            m1, m2 = r['calmar'] > c1, r['q20'] >= c2
            if m1 and m2:
                passes.append((th, vt))
            print(f"{th*100:>5.0f} {vt*100:>4.0f} {r['final']:>10.1f} {r['mdd']:>7.2f} "
                  f"{r['calmar']:>7.3f} {r['q20']:>6.1f} "
                  f"{'O' if m1 else '·':>3} {'O' if m2 else '·':>3}"
                  + ('   ★' if m1 and m2 else ''))
    print(f'\n동시 통과 칸: {len(passes)}/12 — '
          + ('고원 여부를 위 표에서 판독' if passes else '이 설계 공간에도 육각형 없음'))


if __name__ == '__main__':
    main()
