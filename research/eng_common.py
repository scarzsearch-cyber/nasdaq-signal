# -*- coding: utf-8 -*-
"""
[성장 엔진 교체 연구 공용부, 소유자 지시 2026-08-31] 엔진·규칙·집행·관문.

원칙 (지시문 §2·§8): 새 시뮬레이터는 기존 검증 곡선과 오차 0 검산을 통과해야
쓴다. 합성 레버리지는 실물과 구분 표기(금지 5). 판정 아님 — 연구 전용.

  rule_dd(px, in_th, out_th)  252일 고점 낙폭 상태기계 (마감 판정, w∈{0,1})
      검산: (−16,−16) 을 QQQ 체인에 걸면 reentry_lib.run 의 wB 와 완전 일치.
  sim2(w, r_eng, r_def, cost) 공격/방어 2분할, lag=1, 비용은 회전에만
      검산: B 재현이 build_stats 공표(217110.075/25.26/−60.48/0.418)와 일치.
  synth2x(r_idx, c_daily)     2배 합성 = 2r − c_daily (axis_lib.lev_r 규약 그대로)
  fullmet(curve, tb)          최종배수·CAGR·MDD·Calmar·Sortino·Sharpe·회복일·전환수
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import json
import numpy as np
import pandas as pd

COST = 0.001


def rule_dd(px, in_th, out_th, win=252):
    """마감 낙폭 상태기계. in_th 이하 → 방어(0), out_th 초과 회복 → 공격(1).
    px: pd.Series (신호 기준 지수). 반환: w (np.ndarray, 당일 마감 판정값 —
    집행은 sim2 가 lag=1 로 다음날 반영)."""
    dd = (px / px.rolling(win, min_periods=1).max() - 1).values
    n = len(dd)
    w = np.ones(n)
    att = True
    for i in range(n):
        if att and dd[i] <= in_th:
            att = False
        elif not att and dd[i] > out_th:
            att = True
        w[i] = 1.0 if att else 0.0
    return w


def sim2(w, r_eng, r_def, cost=COST):
    """2분할 실행 — axis_defmix.sim_def 와 같은 규약 (lag=1, 편도 cost×|Δw|)."""
    n = len(w)
    pos = np.empty(n)
    pos[0] = w[0]
    pos[1:] = w[:-1]
    r = pos * np.nan_to_num(r_eng) + (1 - pos) * np.nan_to_num(r_def)
    r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * turn))


def synth2x(r_idx, c_daily):
    """2배 합성 일수익 (lev_r k=2 규약: 2r − c_daily). 실물 아님 — 표기 의무."""
    return 2 * np.nan_to_num(r_idx) - c_daily


def fullmet(a, r_tb=None, idx=None):
    a = np.asarray(a, float)
    n = len(a)
    yrs = ((idx[-1] - idx[0]).days / 365.25) if idx is not None else n / 252.0
    r = np.diff(a, prepend=1.0) / np.concatenate(([1.0], a[:-1]))
    r[0] = 0.0
    peak = np.maximum.accumulate(a)
    ddser = a / peak - 1
    mdd = float(np.min(ddser))
    cagr = a[-1] ** (1 / yrs) - 1
    neg = np.minimum(r, 0.0)
    dside = float(np.sqrt(np.mean(neg ** 2)) * np.sqrt(252))
    ex = r - (np.nan_to_num(r_tb) if r_tb is not None else 0.0)
    ex_sd = float(np.std(ex, ddof=1))
    sharpe = float(np.mean(ex) / ex_sd * np.sqrt(252)) if ex_sd > 0 else np.inf
    # 최장 회복일 (고점→회복)
    rec, cur = 0, 0
    for v in ddser:
        cur = cur + 1 if v < 0 else 0
        rec = max(rec, cur)
    calmar = cagr / abs(mdd) if mdd < 0 else (np.inf if cagr > 0 else np.nan)
    return dict(final=float(a[-1]), cagr=cagr * 100, mdd=mdd * 100,
                calmar=calmar, sortino=cagr / dside if dside > 0 else np.inf,
                sharpe=sharpe, rec=rec)


def p05_20y(a, w=5040):
    a = np.asarray(a, float)
    if len(a) <= w + 252:
        return np.nan
    return float(np.quantile(a[w:] / a[:-w], 0.05))


def era_table(a, idx, bounds=(1972, 1980, 1990, 2000, 2010, 2020, 2027)):
    out = []
    yr = pd.Series(idx).dt.year.values
    for k in range(len(bounds) - 1):
        m = (yr >= bounds[k]) & (yr < bounds[k + 1])
        if m.sum() < 252:
            continue
        seg = np.asarray(a, float)[m]
        seg = seg / seg[0]
        out.append((f'{bounds[k]}~{bounds[k+1]-1}', fullmet(seg, idx=idx[m])))
    return out


def selfcheck():
    """검산 2건 — 통과 못 하면 예외."""
    import hypo_gates as G
    import hypo_hex as X
    n = len(G.idx)
    px = pd.Series(G.D['px'], index=G.idx)
    w = rule_dd(px, -0.16, -0.16)
    err_w = float(np.max(np.abs(w - np.asarray(G.wB, float))))
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    a = sim2(w, QLDR, MIXR)
    ref = X.three_way(np.asarray(w), 1 - np.asarray(w), np.zeros(n)).values
    err_c = float(np.max(np.abs(a / ref - 1)))
    m = fullmet(a, idx=G.idx)
    with open(_os.path.join(_ROOT, 'data', 'strategy_stats.json'), encoding='utf-8') as f:
        stats = json.load(f)
    pub = next(s for s in stats['scenarios'] if s['key'] == 'us_1972')['strategies']['B']
    ok_pub = (abs(m['final'] - float(pub['final'])) < 0.5 and
              abs(m['calmar'] - float(pub['calmar'])) < 0.001)
    assert err_w == 0.0, f'rule_dd 검산 실패 {err_w}'
    assert err_c < 1e-12, f'sim2 검산 실패 {err_c}'
    assert ok_pub, f'B 공표 재현 실패 {m}'
    print(f'[검산] rule_dd==wB 오차 {err_w:.1f} · sim2==three_way 오차 {err_c:.1e} · '
          f'B 공표 재현 final {m["final"]:.3f} Calmar {m["calmar"]:.3f}  OK')
    return G, X


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    selfcheck()
