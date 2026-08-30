# -*- coding: utf-8 -*-
"""
[가설 실험 2단계, 소유자 지시 2026-08-30] "T4 이상화" — 국내 레버리지 라인업
(주식 2x · 미국채30년 2x · 골드선물 2x, KODEX/RISE/ACE류 대리)으로 낚싯대를
늘리고 줄을 굵게 한 다자산 × 타깃 40% 판이 관문을 통과하는가.

hypo_gates.py 의 엔진·재료를 그대로 import (새 로직 없음). 30년물 금리(TYX)가
1977-02 시작이라 모든 곡선을 1978-01 이후 같은 창으로 잘라 비교한다.

비교 행:
  현행 B          — 같은 창으로 자른 기준
  T4류 근사(단축)  — 나스닥 2배 단일축 × 추세 4룩백 × 타깃 40%.
                    ⚠ 실제 T4(v68 스펙: 추세 다수결 구성·창이 다름)가 아니며,
                    T4 판정은 v80 부속서(사건 단위)만 유효 — 이 행은 참고용 근사다.
  W40 굵은줄 3다리 — 주식2x + 미국채30Y 2x + 금 2x, 타깃 40% (질문의 본체)
  W25 중간체급     — 같은 구성, 타깃 25% (다이얼 곡선 확인용)

레버리지 조각 대리 모형: 2×기초 − T-bill 차입 1배 − 보수 0.6%/년 (일중 경로
미반영 — 일일 리셋 감가는 선형 비용으로만 근사). 실물 상품 보수·ETN 신용위험·
원유 롤비용 등은 미반영(후보에 관대한 방향). 세전 · 달러 · 거치식 · 전일 신호.
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

import hypo_gates as G                 # noqa: E402  (재료·엔진 재사용)
import hist_defasset as DA             # noqa: E402

EVAL = '1978-01-01'                    # TYX(1977-02) 워밍업 이후 공통 창

idx = G.idx
tb = G.tb
r_b30 = np.nan_to_num(DA.ust_tr(idx, 30, 'TYX'))       # 미국채 30Y 현물형 (1977~, 이전 0)
r_b30x2 = 2 * r_b30 - tb - 0.006 / 252                  # 30Y 2배 조각 (국채레버리지 대리)
r_gldx2 = 2 * G.r_gld - tb - 0.006 / 252                # 금 2배 조각 (골드선물레버리지 대리)


def sl(curve):
    c = curve.loc[EVAL:]
    return c / c.iloc[0]


def row(name, curve):
    r = G.report(name, sl(curve))
    return r


def main():
    g = globals()
    B = G.run.__self__ if False else None  # noqa: F841 (가독용 자리표시)
    # 현행 B — hypo_gates 가 이미 만든 곡선 재사용
    rows = [row('현행 B (−16 mix)', G.cB)]

    G.TARGET = 0.40
    t4n = G.sim_multi([(G.r_eq1, G.r_eq2, 2.0)])                    # 단축 T4류 근사
    w40 = G.sim_multi([(G.r_eq1, G.r_eq2, 2.0),
                       (r_b30, r_b30x2, 2.0),
                       (G.r_gld, r_gldx2, 2.0)])                    # 굵은줄 3다리
    G.TARGET = 0.25
    w25 = G.sim_multi([(G.r_eq1, G.r_eq2, 2.0),
                       (r_b30, r_b30x2, 2.0),
                       (G.r_gld, r_gldx2, 2.0)])
    G.TARGET = 0.10

    rows += [row('T4류 근사(단축 2x·40%)', t4n),
             row('W40 굵은줄 3다리', w40),
             row('W25 중간체급', w25)]

    b = rows[0]
    print(f"[공통 창: {EVAL} ~ 끝, 세전·달러·거치식]")
    print(f"{'전략':<22} {'최종배수':>10} {'CAGR%':>7} {'MDD%':>7} {'Calmar':>7} "
          f"{'20년창5분위':>10} {'전반C':>6} {'후반C':>6}")
    for r in rows:
        print(f"{r['name']:<22} {r['final']:>10.1f} {r['cagr']:>7.2f} {r['mdd']:>7.2f} "
              f"{r['calmar']:>7.3f} {r['q20']:>10.1f} {r['h1']:>6.3f} {r['h2']:>6.3f}")
    print(f"\n관문① Calmar > 현행×1.102 = {b['calmar']*1.102:.3f} · 관문② 5분위 ≥ {b['q20']:.1f}")
    for r in rows[1:]:
        g1 = '통과' if r['calmar'] > b['calmar'] * 1.102 else '탈락'
        g2 = '통과' if r['q20'] is not None and r['q20'] >= b['q20'] else '탈락'
        print(f"  {r['name']}: ① {g1} ({r['calmar']:.3f}) · ② {g2} ({r['q20']:.1f})")


if __name__ == '__main__':
    main()
