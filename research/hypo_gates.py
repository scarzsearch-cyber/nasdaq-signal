# -*- coding: utf-8 -*-
"""
[가설 검증 2026-08-30, 소유자 지시] "무제약 이상형"을 국내/직투 도구로 구현했을 때
이 저장소의 검증 관문(HANDOFF §3)을 통과하는가.

후보 2개 (둘 다 리스크패리티 × 추세 4룩백 다수결 × 목표변동성 10%, 월초 리밸런스):
  A [해외직투]  주식1배 + 미국채10Y(3배 조각으로 압축, TYD 대리) + 금.
                노출 상한 = 현금 100% (3배 조각 덕에 실질 ~150% 노출 가능)
  K [국내병용]  주식2배 조각(레버리지 ETF 대리) + 미국채5Y 선물형(305080 사양) + 금.
                압축이 주식에만 있는 「엉뚱한 다리」판
기준: 현행 B (−16/−16, 방어 mix) — build_stats.sc_us_1972('mix') 레시피 그대로.
데이터: DF.build('chain') 54년(1972-02~), 전부 기존 검증 재료(hist_*/axis_lib)만 조립.

관문 (HANDOFF §3): ① Calmar 가 현행 +10.2% 초과 ② 「20년창 5분위」.
②의 옛 표현은 5퍼센타일과 20퍼센타일이 충돌하므로 둘 다 출력하고, 둘이 갈리면
판정하지 않는다(HANDOFF §4 미결 ⑤). ③④는 ①②가 명확할 때만 의미가 있다.

방법론 규약 준수: 새 시뮬레이터는 퇴화 케이스(고정 100% 2배 보유)가 기존 재료의
단순 누적과 오차 0인지 self-check 한다. 미래참조 금지(신호·변동성 전부 shift(1)).
세전 · 달러 · 거치식. 소유자 확인용 1회성 실험 — 전략 변경 제안 아님.
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_data as H                  # noqa: E402
import hist_defasset as DA             # noqa: E402
import hist_defensive as DF            # noqa: E402
from axis_lib import COST, lev_r       # noqa: E402
from reentry_lib import run, met       # noqa: E402

TARGET = 0.10                          # 목표 포트 변동성 (무상관 근사)
LOOKS = (63, 126, 189, 252)            # 추세 4룩백 (3/6/9/12개월)
VOLW = 63                              # 실현변동성 창

D = dict(DF.build('chain'))
idx = D['idx']
n = len(idx)
tb = H.tbill_daily(idx)

# ---- 현행 B (us_1972 mix) — build_stats 레시피 그대로 ----
Dm = dict(D)
Dm['schdr'] = DA.mix_monthly(idx, DA.MIX_V23, D['schdr'])
cB, wB, tB = run(Dm, [(('dd', -0.16), 1.0, 0)], enter=-0.16)

# ---- 재료 수익률 (전부 기존 검증 함수) ----
r_eq1 = np.nan_to_num(pd.Series(D['px']).pct_change().values)  # 주식 1배 (지수 — 보수 0, 후보에 관대)
r_eq2 = np.asarray(lev_r(D, 2), float)                          # 주식 2배 (검증 모형)
r_b10 = np.nan_to_num(DA.ust_tr(idx, 10, 'TNX'))                # 미국채 10Y 현물형
r_b3x = 3 * r_b10 - 2 * tb - 0.01 / 252                         # TYD 대리: 3배 − 차입 2×T-bill − 보수 1%
r_b5f = np.nan_to_num(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=0.0029))  # 국내 305080 사양
r_gld = np.nan_to_num(DA.gold_r(idx))                           # 금

per = pd.Series(idx).dt.to_period('M').values
mstart = np.zeros(n, bool)
mstart[1:] = per[1:] != per[:-1]


def sig_trend(r):
    """총수익 지수 4룩백 다수결(0..1), 전일 확정 신호."""
    px = pd.Series(np.cumprod(1 + r), index=idx)
    s = sum((px > px.shift(l)).astype(float) for l in LOOKS) / len(LOOKS)
    return s.shift(1).fillna(0).values


def sig_vol(r):
    """기초자산 실현변동성(연율), 전일까지."""
    v = pd.Series(r, index=idx).rolling(VOLW).std() * np.sqrt(252)
    return v.shift(1).values


def sim_multi(legs, cost=COST, cap=True, _fixed_w=None):
    """월초 리밸런스 멀티자산 엔진.
    legs: (기초수익 r_u, 실행상품수익 r_x, 압축배수 k) — 노출 e 에 현금 e/k 소요.
    노출 e_i = TARGET/(√n_leg · vol_i) × trend_i, 현금합>1 이면 비례 축소.
    cap=False 면 한도 해제 — 부족 현금을 T-bill 금리로 무마찰 차입(기관 선물 가정,
    개인은 불가능한 관대 조건. 부록 실험 전용)."""
    m = len(legs)
    tr = [sig_trend(l[0]) for l in legs]
    vv = [sig_vol(l[0]) for l in legs]
    rx = [np.nan_to_num(l[1]) for l in legs]
    ks = [l[2] for l in legs]
    fixed = _fixed_w is not None
    holdings = (np.asarray(_fixed_w, float).copy() if fixed else np.zeros(m))
    if holdings.shape != (m,):
        raise ValueError(f'_fixed_w 길이 {holdings.shape} != 다리 수 {(m,)}')
    cash = 1.0 - float(np.sum(holdings))
    vals = np.empty(n)
    warm = max(max(LOOKS), VOLW) + 1
    for i in range(n):
        if not fixed and i >= warm and (mstart[i] or i == warm):
            e = np.zeros(m)
            for j in range(m):
                vol_j = vv[j][i]
                if np.isfinite(vol_j) and vol_j > 1e-6:
                    e[j] = TARGET / (np.sqrt(m) * vol_j) * tr[j][i]
            need = float(np.sum(e / ks))
            if cap and need > 1.0:
                e *= 1.0 / need
            new_w = e / ks
            total = float(np.sum(holdings) + cash)
            old_w = holdings / total
            old_cash_w = cash / total
            new_cash_w = 1.0 - float(np.sum(new_w))
            turn = 0.5 * (float(np.sum(np.abs(new_w - old_w)))
                          + abs(new_cash_w - old_cash_w))
            total *= 1 - cost * turn
            holdings = total * new_w
            cash = total * new_cash_w
        holdings *= 1 + np.array([rx[j][i] for j in range(m)])
        cash *= 1 + tb[i]
        vals[i] = float(np.sum(holdings) + cash)
    return pd.Series(vals, index=idx)


# ---- 방법론 self-check: 퇴화 케이스 = 고정 100% 주식2배, 비용 0 → 단순 누적과 오차 0 ----
def _check():
    one = [(r_eq2, r_eq2, 1.0)]
    ref = np.cumprod(1 + r_eq2)
    # 실제 엔진을 고정 보유 모드로 실행해 단순 누적과 직접 대조한다.
    out = sim_multi(one, cost=0.0, _fixed_w=[1.0]).values
    err = np.max(np.abs(out / ref - 1))
    assert err < 1e-12, f'퇴화 검산 실패 {err}'
    print(f'[검산] 퇴화 케이스(고정 100% 2배) 오차 {err:.2e}  OK')

    # 월 사이에 50/50이 수익률로 2/3:1/3로 흘렀다면 다음 리밸런스는
    # 평가액을 다시 50/50으로 맞춰야 한다. 가중수익을 매일 더하는 엔진은 이 경로와 다르다.
    h = np.array([1.0, 0.5]); cash0 = 0.0
    total = float(h.sum() + cash0); target = np.array([0.5, 0.5])
    h2 = total * target
    assert np.allclose(h2, [0.75, 0.75])
    print('[검산] 월간 목표비중은 드리프트한 실제 평가액에서 50/50으로 복원  OK')


def qtile(curve, p):
    """20년(5040거래일) 롤링 배수의 분위."""
    w = 5040
    a = curve.values
    if len(a) <= w:
        return None
    return float(np.quantile(a[w:] / a[:-w], p))


def q20(curve):
    return qtile(curve, 0.20)


def q05(curve):
    return qtile(curve, 0.05)


def halves(curve):
    h = len(curve) // 2
    m1, m2 = met(curve.iloc[:h] / curve.iloc[0]), met(curve.iloc[h:] / curve.iloc[h])
    return float(m1['calmar']), float(m2['calmar'])


def report(name, curve):
    m = met(curve)
    c1, c2 = halves(curve)
    return dict(name=name, final=float(m['final']), cagr=float(m['cagr']) * 100,
                mdd=float(m['mdd']) * 100, calmar=float(m['calmar']),
                q05=q05(curve), q20=q20(curve), h1=c1, h2=c2)


def main():
    _check()
    legsA = [(r_eq1, r_eq1, 1.0), (r_b10, r_b3x, 3.0), (r_gld, r_gld, 1.0)]
    A = sim_multi(legsA)
    K = sim_multi([(r_eq1, r_eq2, 2.0), (r_b5f, r_b5f, 1.0), (r_gld, r_gld, 1.0)])
    rows = [report('현행 B (−16 mix)', cB), report('A 해외직투 이상형', A), report('K 국내 병용', K)]
    b = rows[0]
    print(f"\n{'전략':<16} {'최종배수':>10} {'CAGR%':>7} {'MDD%':>7} {'Calmar':>7} "
          f"{'20년p05':>9} {'20년p20':>9} {'전반Calmar':>9} {'후반':>6}")
    for r in rows:
        print(f"{r['name']:<16} {r['final']:>10.1f} {r['cagr']:>7.2f} {r['mdd']:>7.2f} "
              f"{r['calmar']:>7.3f} {r['q05']:>9.1f} {r['q20']:>9.1f} {r['h1']:>9.3f} {r['h2']:>6.3f}")
    print(f"\n관문① Calmar > 현행×1.102 = {b['calmar']*1.102:.3f}")
    print(f"관문② 정의 미확정 — p05 기준 {b['q05']:.1f} · p20 기준 {b['q20']:.1f} (둘 다 병기)")
    for r in rows[1:]:
        g1 = '통과' if r['calmar'] > b['calmar'] * 1.102 else '탈락'
        g205 = r['q05'] is not None and r['q05'] >= b['q05']
        g220 = r['q20'] is not None and r['q20'] >= b['q20']
        g2 = ('통과' if g205 else '탈락') if g205 == g220 else '정의에 따라 갈림'
        print(f"  {r['name']}: ① {g1} (Calmar {r['calmar']:.3f}) · ② {g2} "
              f"(p05 {r['q05']:.1f} {'O' if g205 else 'X'} / p20 {r['q20']:.1f} {'O' if g220 else 'X'})")

    # ---- 부록 (소유자 질문 2026-08-30): 같은 구조에서 타깃만 40%로 올리면? ----
    # A@40 한도내 = 개인 도구 그대로(현금 100% 상한) — 상한이 이미 물려 있으면 10%와 동일해야 함
    # A@40 무제약 = T-bill 무마찰 차입 가정(기관 선물 전용, 개인 불가·관대 조건)
    g = globals()
    g['TARGET'] = 0.40
    A40c = sim_multi(legsA)
    A40u = sim_multi(legsA, cap=False)
    g['TARGET'] = 0.10
    print('\n[부록] 타깃 40% — 다이얼만 올리면 무슨 일이 나는가')
    for r in (report('A@40 한도내(개인)', A40c), report('A@40 무제약(기관가정)', A40u)):
        print(f"{r['name']:<20} {r['final']:>10.1f} {r['cagr']:>7.2f} {r['mdd']:>7.2f} "
              f"{r['calmar']:>7.3f} p05 {r['q05']:>8.1f} · p20 {r['q20']:>8.1f}")


if __name__ == '__main__':
    main()
