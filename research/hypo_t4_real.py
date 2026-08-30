# -*- coding: utf-8 -*-
"""
[가설 실험 3단계, 소유자 지시 2026-08-30] **정본 T4 스펙**으로 다시.

앞선 hypo_t4wide.py 의 "T4류 근사"는 스펙이 달랐다(가격 4룩백 3/6/9/12개월·63일
변동성·월 1회 집행). 여기서는 deploy/oos_log.py 에 사전 고정된 **진짜 T4 정의**를
그대로 쓴다:
    투표 = #{k ∈ {21,63,126,252}: 종가/종가[k일 전] > 1}
    rv   = 2 × (일간수익 20일 표본표준편차 ddof=1) × √252     (2배 자산 연율화)
    w    = clip(40% / rv, 0, 1) × 1[투표 ≥ 2]                  (매일 갱신)
집행: 검증 엔진 axis_defmix.sim_def (lag=1, 편도 0.1%, 대기 = T-bill —
[v68 규약] 공표수치 재현은 cash=tbill).

재현 정확성 검증 2중:
  ① deploy.oos_log.t4_shadow('2026-08-28') 호출 → 장부 실측 (3, 36.7, 1.0) 일치
  ② 벡터화 w 를 무작위 표본일에 deploy 수식 스칼라 계산과 대조 → 오차 0

행: 현행 B · T4 정본(단축) · T4×3 굵은줄(각 다리에 동일 스펙, 슬리브 1/3 균등,
30년국채 2x·금 2x 조각은 hypo_t4wide 와 같은 대리 모형). 공통 창 1978-01~.

⚠ 이 표의 창 단위 총성적 비교는 **승격 판정이 아니다** — v80 부속서가 그 판정법을
폐기했고(승률 49~53% 동전), 유효한 심판은 사건 단위 그림자 장부뿐. 가설 확인 전용.
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
_sys.path.insert(0, _os.path.join(_ROOT, 'deploy'))
# ---------------------------------------------------------------------------
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hypo_gates as G                                  # noqa: E402  재료·기준 B 재사용
import hypo_t4wide as W                                 # noqa: E402  30Y·금 2x 대리 재사용
import oos_log as OL                                    # noqa: E402  정본 스펙 (읽기 전용)
from axis_defmix import sim_def                         # noqa: E402  검증 엔진

idx = G.idx
tb = G.tb
D = G.D
EVAL = W.EVAL

LOOKS, TH, VT, WIN = OL.T4_LOOKS, OL.T4_TH, OL.T4_VT, OL.T4_WIN


def t4_w(r_u):
    """정본 T4 목표비중(벡터) — deploy.t4_shadow 와 같은 수식. r_u = 기초 일간수익."""
    px = pd.Series(np.cumprod(1 + np.nan_to_num(r_u)), index=idx)
    votes = sum((px / px.shift(k) > 1.0).astype(int) for k in LOOKS)
    sd = pd.Series(np.nan_to_num(r_u), index=idx).rolling(WIN).std(ddof=1)
    rv = 2.0 * sd * np.sqrt(252)
    w = np.clip(VT / rv.replace(0, np.nan), 0, 1).fillna(0)
    w[votes < TH] = 0.0
    w.iloc[:max(LOOKS)] = 0.0                           # 워밍업은 대기(T-bill)
    return w.values


def _check():
    # ① 라이브 장부 대조 — deploy 함수를 그대로 호출
    got = OL.t4_shadow('2026-08-28')
    assert got == (3, 36.7, 1.0), f'장부 대조 실패: {got}'
    print(f'[검산①] deploy.t4_shadow(2026-08-28) = {got} == 장부 (3, 36.7, 1.0)  OK')
    # ② 벡터화 vs 스칼라 수식 — 체인 px 위 무작위 20일
    r_u = G.r_eq1
    px = np.cumprod(1 + np.nan_to_num(r_u))
    wv = t4_w(r_u)
    rng = np.random.default_rng(42)
    for i in rng.integers(max(LOOKS) + WIN, len(px), 20):
        votes = sum(1 for k in LOOKS if px[i] / px[i - k] > 1.0)
        rets = [px[j] / px[j - 1] - 1.0 for j in range(i - WIN + 1, i + 1)]
        mu = sum(rets) / len(rets)
        var = sum((x - mu) ** 2 for x in rets) / (len(rets) - 1)
        rv = 2.0 * (var ** 0.5) * (252 ** 0.5)
        w = min(1.0, VT / rv) if rv > 0 else 1.0
        if votes < TH:
            w = 0.0
        assert abs(w - wv[i]) < 1e-9, f'벡터화 불일치 i={i}: {w} vs {wv[i]}'
    print('[검산②] 벡터화 w == deploy 수식 (무작위 20일, 오차 < 1e-9)  OK')


def multi_t4(legs, cost=G.COST):
    """슬리브 균등(1/n) — 각 다리가 정본 T4 를 독립 수행. lag=1, 대기 T-bill."""
    m = len(legs)
    ws = [t4_w(l[0]) for l in legs]
    rx = [np.nan_to_num(l[1]) for l in legs]
    n = len(idx)
    pos = np.zeros(m)
    v = 1.0
    vals = np.empty(n)
    vals[0] = 1.0                                       # sim_def 규약: 첫날 r=0
    for i in range(1, n):
        newp = np.array([ws[j][i - 1] for j in range(m)])
        v *= (1 - cost * float(np.sum(np.abs(newp - pos))) / m)
        pos = newp
        ret = float(sum((pos[j] * rx[j][i] + (1 - pos[j]) * tb[i]) for j in range(m))) / m
        v *= (1 + ret)
        vals[i] = v
    return pd.Series(vals, index=idx)


def main():
    _check()
    w_eq = t4_w(G.r_eq1)
    t4 = sim_def(D, w_eq, tb)                           # 정본 T4 (검증 엔진)
    # 엔진 교차검산: multi_t4 단일 다리 == sim_def — 같은 공식 재료(D.qldr: 실물+합성 체인)
    QLDR = np.nan_to_num(np.asarray(D['qldr'], float))
    solo = multi_t4([(G.r_eq1, QLDR)])
    err = float(np.max(np.abs(solo.values / t4.values - 1)))
    assert err < 1e-9, f'멀티 엔진 교차검산 {err}'
    print(f'[검산③] 멀티 엔진 단일다리 vs sim_def 오차 {err:.2e}  OK')

    wide = multi_t4([(G.r_eq1, QLDR), (W.r_b30, W.r_b30x2), (G.r_gld, W.r_gldx2)])

    rows = [W.row('현행 B (−16 mix)', G.cB),
            W.row('T4 정본 (단축)', t4),
            W.row('T4×3 굵은줄', wide)]
    b = rows[0]
    print(f"\n[공통 창: {EVAL} ~ 끝 · 세전 · 달러 · 거치식 · 창단위 비교는 판정 아님(v80)]")
    print(f"{'전략':<18} {'최종배수':>10} {'CAGR%':>7} {'MDD%':>7} {'Calmar':>7} "
          f"{'20년창5분위':>10} {'전반C':>6} {'후반C':>6}")
    for r in rows:
        print(f"{r['name']:<18} {r['final']:>10.1f} {r['cagr']:>7.2f} {r['mdd']:>7.2f} "
              f"{r['calmar']:>7.3f} {r['q20']:>10.1f} {r['h1']:>6.3f} {r['h2']:>6.3f}")
    print(f"\n관문① Calmar > 현행×1.102 = {b['calmar']*1.102:.3f} · 관문② 5분위 ≥ {b['q20']:.1f}")
    for r in rows[1:]:
        g1 = '통과' if r['calmar'] > b['calmar'] * 1.102 else '탈락'
        g2 = '통과' if r['q20'] is not None and r['q20'] >= b['q20'] else '탈락'
        print(f"  {r['name']}: ① {g1} ({r['calmar']:.3f}) · ② {g2} ({r['q20']:.1f})")


if __name__ == '__main__':
    main()
