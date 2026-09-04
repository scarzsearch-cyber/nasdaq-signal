# -*- coding: utf-8 -*-
"""
[가설 실험 최종장, 소유자 지시 2026-08-30] "육각형" — 관문 ①(위험조정)과
②(부의 바닥)를 **동시에** 넘는 후보가 존재하는가.

관대한 대리 모형 금지 — 재료는 전부 검증분만:
  공격 = D['qldr'] (실물 QLD + 합성 체인, hist_data 검증)
  방어 = DA.mix_monthly 40/40/20 (B 와 동일) · 대기 = T-bill (T4 규약)
  신호 = B 비중 경로(reentry_lib.run 원본) × T4 정본 w (hypo_t4_real, 3중 검산 완료)

후보 8 (전부 B·T4 두 검증 신호의 조합 — 새 신호 발명 없음):
  혼합 x∈{25,50,75}%B   — 두 전략을 일일 고정비율로 (v80 「혼합 0.25B 병기」 포함)
  합의체                — B 방어면 mix, B 공격이면 T4 사이징(잔여 T-bill)
  브레이크 VT∈{40,60}%  — B 공격 구간에 변동성 사이징만(투표 없이), 잔여 T-bill
  브레이크60-mix        — 위와 같되 잔여를 mix 에 (⚠ v32 axis_volguard 계열 인접 —
                          무덤 재탐색 아님을 위해 결과 해석에 명시)

실행 엔진: 3-way(공격/mix/T-bill) 벡터 엔진 — sim_def 와 같은 규약(lag=1, 편도
0.1%). 세 슬리브 전체의 한쪽 편도 회전율을 과금한다. 퇴화 검산 2건(혼합 x=1 == B,
x=0 == T4)이 내장돼
조합 실행의 산수를 기존 검증 곡선과 오차 0 으로 대조한다.

평가: 1972-02~ 전창(54년) · 세전 · 달러 · 거치식.
⚠ 창 단위 비교는 승격 판정이 아니다(v80). 존재 증명 실험일 뿐이다.
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
import hypo_t4_real as R                                # noqa: E402
from axis_defmix import sim_def                         # noqa: E402

idx = G.idx
n = len(idx)
tb = G.tb
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
COST = G.COST

wB = np.nan_to_num(np.asarray(G.wB, float))             # B 비중 경로 (run 원본, 0/1)
wT4 = R.t4_w(G.r_eq1)                                   # T4 정본 w (3중 검산 완료)

sd = pd.Series(G.r_eq1, index=idx).rolling(20).std(ddof=1)
rv = (2.0 * sd * np.sqrt(252)).values                   # 2배 자산 연율 변동성 (T4 와 동일식)


def vscale(vt):
    v = np.clip(vt / rv, 0, 1)
    v[~np.isfinite(v)] = 1.0                            # 워밍업은 브레이크 없음
    return v


def _lag1(w):
    w = np.asarray(w, float)
    out = np.empty(len(w), float); out[:1] = w[0]; out[1:] = w[:-1]
    return out


def _one_way_turnover(*positions):
    """완전투자 포트폴리오의 편도 회전율 = 전체 비중변화 절댓값 합의 절반."""
    return 0.5 * sum(np.abs(np.diff(np.asarray(p, float), prepend=float(p[0])))
                     for p in positions)


def _selfcheck_three_way_cost():
    # 공격 50%가 그대로여도 mix 50%→T-bill 50% 교체는 편도 50%다.
    pq = _lag1([0.5, 0.5, 0.5, 0.5])
    pm = _lag1([0.5, 0.0, 0.0, 0.0])
    pt = _lag1([0.0, 0.5, 0.5, 0.5])
    turn = _one_way_turnover(pq, pm, pt)
    assert np.allclose(turn, [0.0, 0.0, 0.5, 0.0])
    assert np.allclose(np.abs(np.diff(pq, prepend=pq[0])), 0.0)  # 옛 식은 전부 0
    # 두 슬리브 퇴화에서는 기존 공격비중 회전과 정확히 같아야 한다.
    pq2 = _lag1([1.0, 0.0, 0.0]); pm2 = _lag1([0.0, 1.0, 1.0]); pt2 = np.zeros(3)
    assert np.allclose(_one_way_turnover(pq2, pm2, pt2),
                       np.abs(np.diff(pq2, prepend=pq2[0])))


def three_way(wq, wm, wt, cost=COST):
    """공격/mix/T-bill 3분할 실행 — lag=1, 세 슬리브 전체 편도 회전 과금."""
    wq = np.asarray(wq, float); wm = np.asarray(wm, float); wt = np.asarray(wt, float)
    assert len(wq) == len(wm) == len(wt) == n
    assert np.max(np.abs(wq + wm + wt - 1)) < 1e-9
    assert min(np.min(wq), np.min(wm), np.min(wt)) >= -1e-12
    pos, pm, pt = _lag1(wq), _lag1(wm), _lag1(wt)
    r = pos * QLDR + pm * MIXR + pt * tb
    r[0] = 0.0
    turn = _one_way_turnover(pos, pm, pt)
    return pd.Series(np.cumprod((1 + r) * (1 - cost * turn)), index=idx)


def blend(x):
    wq = x * wB + (1 - x) * wT4
    return three_way(wq, x * (1 - wB), (1 - x) * (1 - wT4))


def main():
    _selfcheck_three_way_cost()
    # ---- 퇴화 검산: 조합 실행의 산수가 검증 곡선과 일치하는가 ----
    eB = float(np.max(np.abs(blend(1.0).values / sim_def(G.D, wB, MIXR).values - 1)))
    eT = float(np.max(np.abs(blend(0.0).values / sim_def(G.D, wT4, tb).values - 1)))
    assert eB < 1e-12 and eT < 1e-12, (eB, eT)
    print(f'[검산] 혼합 x=1 == B 오차 {eB:.1e} · x=0 == T4 오차 {eT:.1e}  OK')

    v40, v60 = vscale(0.40), vscale(0.60)
    cands = [
        ('현행 B', three_way(wB, 1 - wB, np.zeros(n))),
        ('T4 정본', three_way(wT4, np.zeros(n), 1 - wT4)),
        ('혼합 75%B', blend(0.75)),
        ('혼합 50%B', blend(0.50)),
        ('혼합 25%B (v80 병기)', blend(0.25)),
        ('합의체 (B게이트×T4w)', three_way(wB * wT4, 1 - wB, wB * (1 - wT4))),
        ('브레이크 VT40', three_way(wB * v40, 1 - wB, wB * (1 - v40))),
        ('브레이크 VT60', three_way(wB * v60, 1 - wB, wB * (1 - v60))),
        ('브레이크 VT60-mix', three_way(wB * v60, 1 - wB * v60, np.zeros(n))),
    ]
    rows = [G.report(nm, c) for nm, c in cands]
    b = rows[0]
    print(f"\n[1972-02~ 전창 54년 · 세전 · 달러 · 거치식 · 판정 아님(v80)]")
    print(f"{'후보':<20} {'최종배수':>10} {'CAGR%':>7} {'MDD%':>7} {'Calmar':>7} "
          f"{'20년창5분위':>10} {'전반C':>6} {'후반C':>6}")
    for r in rows:
        print(f"{r['name']:<20} {r['final']:>10.1f} {r['cagr']:>7.2f} {r['mdd']:>7.2f} "
              f"{r['calmar']:>7.3f} {r['q20']:>10.1f} {r['h1']:>6.3f} {r['h2']:>6.3f}")
    c1, c2 = b['calmar'] * 1.102, b['q20']
    print(f"\n관문① Calmar > {c1:.3f} · 관문② 20년창 5분위 ≥ {c2:.1f}")
    both = []
    for r in rows[1:]:
        g1, g2 = r['calmar'] > c1, r['q20'] is not None and r['q20'] >= c2
        mark = '★ 육각형' if g1 and g2 else ('① 만' if g1 else ('② 만' if g2 else '전패'))
        print(f"  {r['name']}: ① {'통과' if g1 else '탈락'} ({r['calmar']:.3f}) · "
              f"② {'통과' if g2 else '탈락'} ({r['q20']:.1f})  → {mark}")
        if g1 and g2:
            both.append(r['name'])
    print(f"\n사전 지정 후보 8개 중 육각형 후보: "
          f"{both if both else '없음 — 연속 혼합 x 탐색은 아래 부록에서 따로 본다'}")

    # ---- 부록: 혼합 x 전선 지도 — 문턱 근처 한 점 쇼핑(과적합)을 피하려고
    #      전 구간을 훑는다. 이웃한 여러 x 가 같이 넘으면 고원, 한 점이면 첨탑. ----
    print(f"\n[부록] 혼합 x 전선 (관문① Calmar>{c1:.3f} · 관문② q20≥{c2:.1f})")
    print(f"{'x(B비중)':>8} {'Calmar':>7} {'q20':>6} {'①':>3} {'②':>3}")
    for x in np.arange(0.30, 1.0001, 0.05):
        r = G.report('', blend(float(x)))
        m1, m2 = r['calmar'] > c1, r['q20'] >= c2
        print(f"{x:>8.2f} {r['calmar']:>7.3f} {r['q20']:>6.1f} "
              f"{'O' if m1 else '·':>3} {'O' if m2 else '·':>3}"
              + ('   ★ 동시 통과' if m1 and m2 else ''))


if __name__ == '__main__':
    main()
