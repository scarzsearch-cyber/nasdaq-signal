# -*- coding: utf-8 -*-
"""
[외부 전략 비교 2, 소유자 요청 2026-08-31] 라오어 밸류리밸런싱 VR 5.0 (거치식)
vs 현행 B — 같은 54년 잣대. 규칙 출처: quantstack.app/vr/* (2026-08-26 판).

구현 사양 (거치식 오피셜):
  2주(10거래일) 사이클마다: ① V ← V + Pool/G  ② 밴드 = V×0.85~V×1.15
  ③ 평가금 > 상단 → V 까지 매도 (전액 Pool 편입)
     평가금 < 하단 → V 까지 매수하되 사이클당 Pool 의 50% 상한
  초기: 주식 87% / Pool 13% (사이트 예시 P/V=0.15), V0 = 주식 평가금.
  G=10(권장 시작)·20(안정) 두 변형. 대기 현금 T-bill 이자(관대), 편도 0.1%.
근사: 사이클 경계일 종가 일괄 판정(실무는 2주치 LOC 예약 — 경계 근사, 문서화).
외부 정합 검사: 2011~2020(사이트 표본)에서 수익 레버리지(vs 1배 지수)가
  공표 2.98배(/10)·2.74배(/20) 근처인지 확인.
판정 아님 · 전략 무변경. 실행: python research/ext_vr.py
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
from axis_lib import lev_r                              # noqa: E402

COST = 0.001


def run_vr(px, tb, G=10, band=0.15, cyc=10, cap=0.5, init_pv=0.15):
    n = len(px)
    stock0 = 1.0 / (1.0 + init_pv)
    pool = 1.0 - stock0
    sh = stock0 / px[0]
    V = stock0
    vals = np.empty(n)
    for i in range(n):
        pool *= (1 + tb[i])
        if i % cyc == 0 and i > 0:
            V += pool / G
            S = sh * px[i]
            if S > V * (1 + band):
                sell = S - V
                sh -= sell / px[i]
                pool += sell * (1 - COST)
            elif S < V * (1 - band):
                buy = min(V - S, pool * cap, pool / (1 + COST))
                if buy > 0:
                    sh += buy / px[i]
                    pool -= buy * (1 + COST)
        vals[i] = pool + sh * px[i]
        assert pool > -1e-9 and sh > -1e-12
    return vals


def main():
    G_, X = EC.selfcheck()
    idx = G_.idx
    tb = G_.tb
    MIXR = np.nan_to_num(np.asarray(G_.Dm['schdr'], float))
    r3 = np.asarray(lev_r(G_.D, 3.0), float)
    px3 = np.cumprod(1 + r3) * 100.0
    r1 = np.nan_to_num(pd.Series(G_.D['px']).pct_change().values)
    a1 = np.cumprod(1 + r1)

    aB2 = EC.sim2(np.asarray(G_.wB, float), np.nan_to_num(np.asarray(G_.D['qldr'], float)), MIXR)
    aB3 = EC.sim2(np.asarray(G_.wB, float), r3, MIXR)
    aH3 = np.cumprod(1 + r3)

    # ⚠ 구조 발견: 공식상 V 는 단조 증가(하락 조항 없음) — 재난 후 V 가 좌초해
    # 수십 년 매수 신호만 지속(Pool 소진) → 맨몸 보유로 퇴화한다. 따라서 VR 은
    # 창마다 「신규 시작」으로 평가한다 (연속 54년 운용은 아래 별도 1줄).
    n = len(idx)
    cont = run_vr(px3, tb, G=10)
    m = EC.fullmet(cont, idx=idx)
    print(f'[연속 54년 운용 VR/10] 최종 {m["final"]:.0f}배 · MDD {m["mdd"]:.1f} — '
          f'73-74 재난 후 V 좌초로 사실상 맨몸 보유화 (구조 발견, 본표는 창별 신규 시작)')

    # 외부 정합: 2011~2020 신규 시작 — 수익 레버리지 (vs 1배 지수 CAGR)
    i0, i1 = pd.Series(idx).searchsorted([pd.Timestamp('2011-01-01'), pd.Timestamp('2021-01-01')])
    yrs = (idx[i1] - idx[i0]).days / 365.25
    c1x = (a1[i1] / a1[i0]) ** (1 / yrs) - 1
    for nm, g, pub in (('/10', 10, '2.98'), ('/20', 20, '2.74')):
        a = run_vr(px3[i0:i1 + 1], tb[i0:i1 + 1], G=g)
        cv = a[-1] ** (1 / yrs) - 1
        print(f'[정합] 2011~2020 신규 VR{nm} CAGR {cv:.1%} vs 1배 {c1x:.1%} → '
              f'수익 레버리지 {cv/c1x:.2f}배 (공표 {pub}배)')

    for s, lab in (('1972-02-07', '전창 54년'), ('2000-01-01', '2000~'),
                   ('2010-01-01', '2010~ (사이트 표본 시대)')):
        j0 = int(pd.Series(idx).searchsorted(pd.Timestamp(s)))
        rows = [('VR /10 (권장)', run_vr(px3[j0:], tb[j0:], G=10)),
                ('VR /20 (안정)', run_vr(px3[j0:], tb[j0:], G=20)),
                ('현행 B (2배)', aB2[j0:] / aB2[j0]),
                ('B 규칙 × 3배', aB3[j0:] / aB3[j0]),
                ('TQQQ 맨몸', aH3[j0:] / aH3[j0])]
        print(f'\n=== {lab} — VR 은 창 시작일 신규 개설 ===')
        print(f"{'전략':<14} {'최종배수':>11} {'CAGR':>7} {'MDD':>7} {'Calmar':>7} {'물속(년)':>7}")
        for nm, seg in rows:
            m = EC.fullmet(seg, idx=idx[j0:])
            print(f'{nm:<14} {m["final"]:>11.2f} {m["cagr"]:>7.2f} {m["mdd"]:>7.1f} '
                  f'{m["calmar"]:>7.3f} {m["rec"]/252:>7.1f}')

    print('\n[위기 직전 신규 시작 시 위기 구간 계좌 배수 — VR/10 / B(2배)]')
    for nm, s, e in (('닷컴 00-02', '2000-03-10', '2002-10-09'),
                     ('GFC 07-09', '2007-10-31', '2009-03-09'),
                     ('2022 베어', '2022-01-03', '2022-10-12')):
        j0, j1 = pd.Series(idx).searchsorted([pd.Timestamp(s), pd.Timestamp(e)])
        a = run_vr(px3[j0:j1 + 1], tb[j0:j1 + 1], G=10)
        print(f'  {nm}: VR {a[-1]:>6.3f} · B2 {aB2[j1]/aB2[j0]:>6.3f}')


if __name__ == '__main__':
    main()
