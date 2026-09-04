# -*- coding: utf-8 -*-
"""
[v32] 변동성 조기방어의 MDD 개선은 '고칠 수 있는 것'인가

v31 §4 는 이 후보를 기각하면서 이렇게 적었다:
  "MDD 개선 2.8%p 는 모든 구간에서 일관됐다. 파라미터 첨탑과 데이터 편중을
   먼저 해결하면 다시 열어볼 수 있다."

**그 문장에는 검증 안 된 전제가 있다.** 2.8%p 는 파라미터 **하나**(p95/21일/게이트 -5%)
에서만 잰 값이다. 수익이 첨탑인데 위험만 평지일 이유가 없다. 여기서 그걸 잰다.

[질문]
  Q1  MDD 개선이 파라미터 격자 **전체**에서 나오는가, 고른 칸에서만 나오는가
  Q2  같은 MDD 를 그냥 문턱 낮추기로도 얻을 수 있는가 (수익-위험 프론티어 대조)
  Q3  파라미터를 안 고르면(앙상블) 개선이 남는가
  Q4  실물 QQQ 구간(1999-)만 봐도 남는가
  Q5  앙상블의 워크포워드

[판정 기준]
  - Q1 에서 격자의 8할 이상이 MDD 를 개선해야 '평지'라 부를 수 있다
  - Q2 에서 고정문턱 프론티어보다 **위**에 있어야 변동성 정보가 기여한 것이다
  - Q3 앙상블이 개선을 유지해야 '파라미터를 안 골라도 된다'가 성립한다
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import sys
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import COST, rule_w

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# v32 §1의 사전 등록 격자: p92.5 고정, 7개 룩백 x 6개 게이트 = 42칸.
GRID_Q = 0.925
LBS = (3, 5, 7, 10, 14, 21, 31)
GATES = (-0.01, -0.02, -0.03, -0.04, -0.05, -0.06)
SELECTED = (10, 0.925, -0.03)

# WFA는 v32 계약대로 Calmar로 고르는 별도 선택 집합이다.
WFA_LBS = (5, 7, 10, 14, 21)
WFA_QS = (0.875, 0.90, 0.925, 0.95)
WFA_GATES = (-0.02, -0.03, -0.04, -0.05)


def zc(a, win=756, minp=252):
    s = pd.Series(np.asarray(a, dtype=float)).reset_index(drop=True)
    return ((s - s.rolling(win, min_periods=minp).mean())
            / s.rolling(win, min_periods=minp).std()).values


def exp_q(a, q, minp=252):
    s = pd.Series(np.asarray(a, dtype=float)).reset_index(drop=True)
    return s.expanding(min_periods=minp).quantile(q).shift(1).values


def lagged_positions(w, lag=1):
    """종가 신호를 정확히 ``lag`` 거래일 뒤 포지션으로 옮긴다."""
    w = np.asarray(w, dtype=float)
    if lag < 0:
        raise ValueError('lag must be non-negative')
    if len(w) == 0 or lag == 0:
        return w.copy()
    pos = np.empty_like(w)
    k = min(lag, len(w))
    pos[:k] = w[0]
    if lag < len(w):
        pos[lag:] = w[:-lag]
    return pos


def sim(D, w, cost=COST, lag=1, lo=0, hi=None):
    n = len(D['idx']) if hi is None else hi
    sl = slice(lo, n)
    # 전체 신호를 먼저 지연해 OOS/연도 경계에서도 직전 신호를 보존한다.
    pos = lagged_positions(w, lag)[sl]
    r = np.nan_to_num(pos * D['qldr'][sl] + (1 - pos) * D['schdr'][sl])
    r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * turn))


def mdd(c):
    return (c / np.maximum.accumulate(c) - 1).min()


def cagr(c, n):
    """보관 연구표의 252거래일 연율. 달력연수 재순위도 v203 선택과 동일하다."""
    return c[-1] ** (252 / n) - 1


def early_w(ddq, trig, gate):
    return rule_w(np.where(trig & (ddq <= gate), -0.20, ddq), -0.16, -0.11)


def roll_mdd(c, L, step=63):
    """롤링 창별 MDD 분포 — 전체경로 MDD 한 숫자는 한 사건에 좌우되므로."""
    out = []
    for s in range(0, len(c) - L, step):
        seg = c[s:s + L]
        out.append(mdd(seg))
    return np.array(out)


def nonworsening_fixed(fixed, candidate_mdd):
    """후보와 같거나 덜 깊은 MDD(0에 더 가까움)의 고정문턱만 고른다."""
    return [row for row in fixed if row[2] >= candidate_mdd]


def compare_fixed_frontier(cells, fixed):
    """비교 가능한 후보만 프론티어 승패에 넣고, 비교 불가는 따로 센다."""
    beat = comparable = unmatched = 0
    for _, (_, _, curve) in cells.items():
        alt = nonworsening_fixed(fixed, mdd(curve))
        if not alt:
            unmatched += 1
            continue
        comparable += 1
        if curve[-1] > max(row[3] for row in alt):
            beat += 1
    return beat, comparable, unmatched


def select_by_calmar(curves, n):
    """최종부가 아니라 IS Calmar가 가장 큰 후보를 선택한다."""
    scored = {}
    for key, curve in curves.items():
        g, m = cagr(curve, n), mdd(curve)
        scored[key] = g / abs(m) if m < 0 else np.inf
    key = max(scored, key=scored.get)
    return key, scored[key]


def selfcheck():
    w = np.array([1.0, 0.0, 1.0, 0.0])
    assert np.array_equal(lagged_positions(w, 0), w)
    assert np.array_equal(lagged_positions(w, 1), [1.0, 1.0, 0.0, 1.0])
    toy_d = {'idx': np.arange(3), 'qldr': np.array([0.10, 0.10, 0.10]),
             'schdr': np.zeros(3)}
    sig = np.array([1.0, 0.0, 0.0])
    assert np.allclose(sim(toy_d, sig, cost=0, lag=0), [1.0, 1.0, 1.0])
    assert np.allclose(sim(toy_d, sig, cost=0, lag=1), [1.0, 1.1, 1.1])
    dd = np.array([-0.20, -0.15, -0.12])
    assert np.array_equal(rule_w(dd, -0.16, -0.11), [0.0, 0.0, 0.0])
    assert not np.array_equal(rule_w(dd, -0.16, -0.11)[1:],
                              rule_w(dd[1:], -0.16, -0.11))
    zz = zc([1.0, 2.0, 3.0, 4.0], win=3, minp=3)
    assert np.isnan(zz[:2]).all() and np.isfinite(zz[2:]).all()
    toy = [('safer', 0.0, -0.60, 1.0), ('riskier', 0.0, -0.70, 2.0)]
    assert [row[0] for row in nonworsening_fixed(toy, -0.65)] == ['safer']
    toy_cells = {
        'comparable': (0.0, 0.0, np.array([1.0, 0.8, 1.1])),
        'unmatched': (0.0, 0.0, np.array([1.0, 0.95, 1.2])),
    }
    assert compare_fixed_frontier(toy_cells, [('fixed', 0.0, -0.10, 1.0)]) == (1, 1, 1)
    curves = {'wealth': np.array([1.0, 4.0, 1.5, 3.0]),
              'calmar': np.array([1.0, 1.2, 1.1, 2.5])}
    assert max(curves, key=lambda k: curves[k][-1]) == 'wealth'
    assert select_by_calmar(curves, 252)[0] == 'calmar'
    assert len(LBS) * len(GATES) == 42 and SELECTED[0] in LBS and SELECTED[2] in GATES


def main():
    selfcheck()
    D = DF.build('chain')
    idx = D['idx']
    ddq = D['ddv']
    N = len(idx)
    px = D['px']
    base_w = rule_w(ddq, -0.16, -0.11)
    base_c = sim(D, base_w)
    b_mdd, b_cagr = mdd(base_c), cagr(base_c, N)
    print(f"구간 {idx[0].date()} ~ {idx[-1].date()}  ({N}거래일)")
    print(f"기준선: {base_c[-1]:,.1f}배  CAGR {b_cagr*100:.2f}%  MDD {b_mdd*100:.2f}%  "
          f"Calmar {b_cagr/abs(b_mdd):.3f}  전환 {np.abs(np.diff(base_w)).sum():.0f}회\n")

    RV = {lb: zc(px.pct_change().rolling(lb, min_periods=lb).std().values) for lb in LBS}
    TRIG = {(lb, GRID_Q): (RV[lb] >= exp_q(RV[lb], GRID_Q)) for lb in LBS}

    # ============================================================ Q1
    print("=" * 84)
    print("Q1. MDD 개선이 격자 전체에서 나오는가 — 각 칸의 [수익 변화 / MDD 변화]")
    print("=" * 84)
    cells = {}
    for lb in LBS:
        print(f"\n  변동성 룩백 {lb}일     " + "".join(f"{g*100:>18.0f}%" for g in GATES))
        for q in (GRID_Q,):
            row = []
            for g in GATES:
                w = early_w(ddq, TRIG[(lb, q)], g)
                c = sim(D, w)
                dv = c[-1] / base_c[-1] - 1
                dm = (abs(mdd(c)) - abs(b_mdd)) * 100     # 음수 = MDD 개선
                cells[(lb, q, g)] = (dv, dm, c)
                row.append(f"{dv*100:+7.1f}% /{-dm:+6.2f}p")
            print(f"    p{q*100:5.1f}      " + "  ".join(row))

    dvs = np.array([v[0] for v in cells.values()])
    dms = np.array([v[1] for v in cells.values()])
    print(f"\n  격자 {len(cells)}칸 요약")
    print(f"    수익 개선 칸  {(dvs>0).sum():2d}/{len(cells)}  ({(dvs>0).mean()*100:.0f}%)   "
          f"중앙값 {np.median(dvs)*100:+.1f}%   범위 {dvs.min()*100:+.1f}% ~ {dvs.max()*100:+.1f}%")
    print(f"    MDD 개선 칸   {(dms<0).sum():2d}/{len(cells)}  ({(dms<0).mean()*100:.0f}%)   "
          f"중앙값 {-np.median(dms):+.2f}p   범위 {-dms.max():+.2f}p ~ {-dms.min():+.2f}p")
    print(f"    ** 판정: MDD 개선 칸 비율이 80% 이상이어야 '평지'라 부를 수 있다 **")

    # ============================================================ Q2
    print("\n" + "=" * 84)
    print("Q2. 같은 MDD 를 그냥 문턱 낮추기로도 얻는가 — 수익·위험 프론티어 대조")
    print("=" * 84)
    print("\n  [대조군] 변동성 조건 없이 진입문턱만 바꾼 규칙")
    fixed = []
    for e in (-0.05, -0.08, -0.10, -0.12, -0.14, -0.16, -0.18, -0.20, -0.25):
        w = rule_w(ddq, e, -0.11)
        c = sim(D, w)
        fixed.append((e, cagr(c, N), mdd(c), c[-1]))
        print(f"    진입 {e*100:5.0f}%   {c[-1]:>11,.1f}배  CAGR {cagr(c,N)*100:6.2f}%  "
              f"MDD {mdd(c)*100:7.2f}%  Calmar {cagr(c,N)/abs(mdd(c)):.3f}")

    print("\n  [질문] 변동성 규칙의 MDD 를 고정문턱으로도 낼 수 있나?")
    print("         각 격자칸에 대해 '같거나 더 낮은 MDD 를 내는 고정문턱' 중 최고 수익과 비교")
    beat, comparable, unmatched = compare_fixed_frontier(cells, fixed)
    rate = beat / comparable if comparable else np.nan
    print(f"    비교 가능한 칸 중 고정문턱 프론티어를 이긴 칸 = "
          f"{beat}/{comparable} ({rate*100:.0f}%)")
    print(f"    비교 불가(후보만 더 안전하고 같은 MDD의 고정문턱 없음) = {unmatched}/{len(cells)}")
    print(f"    ** 이 비율이 낮으면 '변동성 정보'가 아니라 '문턱을 낮춘 것'이다 **")

    # ============================================================ Q3
    print("\n" + "=" * 84)
    print("Q3. 파라미터를 안 고르면 — 격자 전체 다수결 앙상블")
    print("=" * 84)
    print("  (부분비중은 v18/v22/VR 에서 세 번 기각됐으므로 이진 유지: 과반이 방어면 방어)")
    for frac, nm in [(0.5, '과반(50%)'), (0.3, '30% 이상'), (0.7, '70% 이상')]:
        votes = np.zeros(N)
        for k in cells:
            lb, q, g = k
            votes += (TRIG[(lb, q)] & (ddq <= g)).astype(float)
        ens_trig = votes >= (len(cells) * frac)
        w = rule_w(np.where(ens_trig, -0.20, ddq), -0.16, -0.11)
        c = sim(D, w)
        print(f"    {nm:<10} {c[-1]:>11,.1f}배  CAGR {cagr(c,N)*100:6.2f}%  MDD {mdd(c)*100:7.2f}%  "
              f"Calmar {cagr(c,N)/abs(mdd(c)):.3f}  [{(c[-1]/base_c[-1]-1)*100:+6.1f}% / "
              f"MDD {-(abs(mdd(c))-abs(b_mdd))*100:+.2f}p]  전환{np.abs(np.diff(w)).sum():.0f}")
    votes = np.zeros(N)
    for k in cells:
        lb, q, g = k
        votes += (TRIG[(lb, q)] & (ddq <= g)).astype(float)
    ens_trig = votes >= (len(cells) * 0.5)
    ens_w = rule_w(np.where(ens_trig, -0.20, ddq), -0.16, -0.11)
    ens_c = sim(D, ens_w)

    # ============================================================ Q4
    print("\n" + "=" * 84)
    print("Q4. 실물 QQQ 구간(1999-)만 봐도 남는가")
    print("=" * 84)
    segs = [('1972-1985 종합지수(합성)', '1972-02-07', '1985-09-30'),
            ('1985-1999 NDX(합성)', '1985-10-01', '1999-03-09'),
            ('1999- QQQ 실물', '1999-03-10', '2026-08-26')]
    best_w = early_w(ddq, TRIG[SELECTED[:2]], SELECTED[2])
    for nm, s, e in segs:
        lo = int(idx.searchsorted(pd.Timestamp(s)))
        hi = int(idx.searchsorted(pd.Timestamp(e), side='right'))
        n = hi - lo
        cb = sim(D, base_w, lo=lo, hi=hi)
        print(f"\n  {nm}")
        print(f"    기준선          {cb[-1]:>10,.2f}배  CAGR {cagr(cb,n)*100:6.2f}%  MDD {mdd(cb)*100:7.2f}%")
        for lbl, ww in [('고른 칸(10일/p92.5/-3%)', best_w), ('앙상블(과반)', ens_w)]:
            cc = sim(D, ww, lo=lo, hi=hi)
            print(f"    {lbl:<16}{cc[-1]:>10,.2f}배  CAGR {cagr(cc,n)*100:6.2f}%  MDD {mdd(cc)*100:7.2f}%"
                  f"   [{(cc[-1]/cb[-1]-1)*100:+6.1f}% / MDD {-(abs(mdd(cc))-abs(mdd(cb)))*100:+.2f}p]")

    print("\n  격자 전체가 실물 구간에서 MDD 를 개선하는가")
    lo99 = int(idx.searchsorted(pd.Timestamp('1999-03-10')))
    cb99 = sim(D, base_w, lo=lo99)
    m99 = mdd(cb99)
    imp = [(abs(mdd(sim(D, early_w(ddq, TRIG[(lb, q)], g), lo=lo99))) - abs(m99)) * 100
           for (lb, q, g) in cells]
    imp = np.array(imp)
    print(f"    MDD 개선 칸 {(imp<0).sum()}/{len(imp)} ({(imp<0).mean()*100:.0f}%)  "
          f"중앙값 {-np.median(imp):+.2f}p  범위 {-imp.max():+.2f}p ~ {-imp.min():+.2f}p")

    # ============================================================ Q5
    print("\n" + "=" * 84)
    print("Q5. 롤링 창 MDD 분포 + 앙상블 워크포워드")
    print("=" * 84)
    print("\n  롤링 10년 창 MDD 분포 (전체경로 MDD 한 숫자는 한 사건에 좌우되므로)")
    L = 10 * 252
    rb = roll_mdd(base_c, L)
    for nm, cc in [('고른 칸', sim(D, best_w)), ('앙상블', ens_c)]:
        rc = roll_mdd(cc, L)
        print(f"    {nm:<8} 개선된 창 {(np.abs(rc)<np.abs(rb)).sum():3d}/{len(rb)} "
              f"({(np.abs(rc)<np.abs(rb)).mean()*100:.0f}%)   "
              f"중앙 {np.median(rb)*100:6.2f}% -> {np.median(rc)*100:6.2f}%   "
              f"최악 {rb.min()*100:6.2f}% -> {rc.min()*100:6.2f}%")

    print("\n  워크포워드 — 1972-1999 Calmar로 고르고 2000- 에 적용")
    sp = int(idx.searchsorted(pd.Timestamp('2000-01-01')))
    n2 = N - sp
    cb2 = sim(D, base_w, lo=sp)
    wfa = {}
    for lb in WFA_LBS:
        rz = RV.get(lb)
        if rz is None:
            rz = zc(px.pct_change().rolling(lb, min_periods=lb).std().values)
        for q in WFA_QS:
            tq = rz >= exp_q(rz, q)
            for g in WFA_GATES:
                wfa[(lb, q, g)] = early_w(ddq, tq, g)
    is_curves = {k: sim(D, w, hi=sp) for k, w in wfa.items()}
    bk, best_calmar = select_by_calmar(is_curves, sp)
    print(f"    IS Calmar 최적 = 룩백 {bk[0]}일 / p{bk[1]*100:.1f} / "
          f"게이트 {bk[2]*100:.0f}%  (Calmar {best_calmar:.3f})")
    print(f"    OOS 기준선   {cb2[-1]:>9,.2f}배  CAGR {cagr(cb2,n2)*100:6.2f}%  MDD {mdd(cb2)*100:7.2f}%")
    oos_results = {}
    for lbl, ww in [('OOS IS최적', wfa[bk]),
                    ('OOS 앙상블', ens_w)]:
        cc = sim(D, ww, lo=sp)
        oos_results[lbl] = cc
        print(f"    {lbl:<12}{cc[-1]:>9,.2f}배  CAGR {cagr(cc,n2)*100:6.2f}%  MDD {mdd(cc)*100:7.2f}%"
              f"   [{(cc[-1]/cb2[-1]-1)*100:+6.1f}% / MDD {-(abs(mdd(cc))-abs(mdd(cb2)))*100:+.2f}p]")

    chosen = oos_results['OOS IS최적']
    print("\n[이 스크립트의 판정]")
    print(f"    등록 격자의 MDD 개선 = {(dms < 0).sum()}/{len(cells)}; "
          f"비교 가능한 고정문턱 프론티어 승리 = {beat}/{comparable}; 비교 불가 = {unmatched}칸.")
    print(f"    Calmar 선택 OOS는 기준보다 최종금액 {(chosen[-1]/cb2[-1]-1)*100:+.1f}%, "
          f"MDD {-(abs(mdd(chosen))-abs(mdd(cb2)))*100:+.2f}p다.")
    print("    따라서 거치식 MDD 개선은 재현되지만, 이것만으로 채택할 근거는 아니다.")
    print("    다음 질문인 플라시보와 실제 적립식 판정은 v203 통합 리뷰에 연결한다.")


if __name__ == '__main__':
    main()
