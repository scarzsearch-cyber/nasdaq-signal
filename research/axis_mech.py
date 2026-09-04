# -*- coding: utf-8 -*-
"""
[v55] 운용 메커니즘 자체를 바꾼다 — 신호가 아니라 구조

§27 의 질문: **현행의 약점이 신호 부족 때문인가, 운용 메커니즘 자체 때문인가?**

v27~v54 는 전부 "신호를 무엇으로 할까"였다. 이번엔 신호를 그대로 두고
**포지션을 어떻게 굴릴까**를 바꾼다.

[데이터 실태 — §15/§30]
  전략군 G 유동성(TED·FRA-OIS·SOFR)  **FRED 접속 불가 -> 건너뜀**
  전략군 H 크로스에셋 펀딩(USD·유가)    **원천 없음 -> 건너뜀**
                                     (금+국채+VIX 조합은 v54 F 에서 이미 기각)
  나머지 A~F·J 는 **전부 QQQ 종가만으로 계산되고 1972~ 전구간**이다.
  -> 데이터 제약 없이 §27 질문에 답할 수 있다.

[후보]
  A  동적 노출     위험점수(RV 백분위)로 QLD 비중을 연속 결정. DD 사다리가 아니다
  B  변동성 타깃   w = 목표변동성 / 추정변동성. 일/주/월 재조정을 각각 잰다
  C  변동성 충격   RV 급등에 노출 축소 -> **정상화되면 빠르게 복원**(래치)
  D  이진 사건복귀  공격/방어 2상태. 회복은 **단 하나의 사건**으로만
  E  시간 잠금     현행 규칙 + 최소 유지일 N. **§27 의 직접 시험**
  F  회복 사건     저점 대비 X% 회복 한 번으로 복귀
  J  비대칭 별칭   진입은 DD, 복귀는 사건. D 와 같은 경로면 중복으로 센다

[규약]
  · 신호는 당일 종가까지 계산하고 **다음 거래일 한 번만** 반영한다.
  · 부분비중은 위험/방어 잔고를 따로 굴린다. B 의 주/월 판은 예약일에만
    실제 잔고를 목표비중으로 맞추고, 실제 이동 비중에만 비용을 낸다.
  · 거치식과 적립식은 같은 잔고 엔진을 쓴다. 빠른 적립식 식
    (mean c[T]/c[t_m])은 직접 적립 루프와 일치하는지 **먼저 검산**한다.
  · 전환 횟수를 반드시 함께 보고한다(§4, G6).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
from bisect import bisect_right, insort_right

import numpy as np
import pandas as pd

import hist_defensive as DF
import axis_lib as AX
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

K = 2
ENTER = -0.16
SEGS = [('1972-85', '1972-01-01', '1985-12-31'),
        ('1986-99', '1986-01-01', '1999-12-31'),
        ('2000-13', '2000-01-01', '2013-12-31'),
        ('2014-26', '2014-01-01', '2026-12-31')]
L = 20 * 252


def prior_percentile(a, min_prior=252):
    """현재값을 *현재 이전* 유효 관측치의 경험분포에 놓은 백분위.

    expanding().rank().shift(1)은 전일 값의 전일까지 순위를 오늘 신호로 쓰므로,
    바깥의 1일 실행 지연과 합쳐져 실질 2일 지연이 된다. 여기서는 오늘 값 자체는
    쓰되 비교 분포만 어제까지로 제한한다.
    """
    out = np.full(len(a), np.nan, dtype=float)
    seen = []
    for i, x in enumerate(np.asarray(a, dtype=float)):
        if np.isfinite(x):
            if len(seen) >= min_prior:
                out[i] = bisect_right(seen, float(x)) / len(seen)
            insort_right(seen, float(x))
    return out


def sleeve_engine(rk, dfr, w, *, step=1, cost=COST, lo=0, hi=None,
                  initial=1.0, contribution_days=()):
    """위험/방어 잔고를 직접 굴리는 공용 거치식·적립식 엔진.

    w[t]는 t일 종가로 만든 목표비중이고 t+1일 수익부터 적용한다. step>1이면
    0, step, 2*step ... 번째 종가의 목표만 다음 거래일에 집행한다. 예약일이
    아니면 두 잔고가 각자 움직여 생긴 비중 표류를 그대로 둔다.

    납입금은 그날 수익 뒤 현재 펀드의 실제 비중으로 들어간다. 새 돈 때문에
    숨어 있는 재조정이 생기지 않으므로 같은 엔진의 NAV 단위매수와 정확히 같다.
    """
    rk = np.asarray(rk, dtype=float)
    dfr = np.asarray(dfr, dtype=float)
    w = np.asarray(w, dtype=float)
    if not (len(rk) == len(dfr) == len(w)):
        raise ValueError('sleeve_engine: rk/dfr/w 길이가 다르다')
    if step < 1 or int(step) != step:
        raise ValueError('sleeve_engine: step은 1 이상의 정수여야 한다')
    if np.any(~np.isfinite(w)) or np.any((w < 0) | (w > 1)):
        raise ValueError('sleeve_engine: 목표비중은 유한한 0~1이어야 한다')
    step = int(step)
    hi = len(w) if hi is None else int(hi)
    lo = int(lo)
    if not (0 <= lo < hi <= len(w)):
        raise ValueError('sleeve_engine: 잘못된 lo/hi')

    # lo일 수익에 적용 가능한 마지막 예약 신호. lo=0은 첫 비중으로 시작한다.
    decision = 0 if lo == 0 else ((lo - 1) // step) * step
    active = float(w[decision])
    fund_risk = active
    fund_defense = 1.0 - active
    # 중간 창에서 시작해도 전역 예약일 이후 lo 직전까지의 표류 비중을 복원한다.
    for i in range(decision + 1, lo):
        rr = rk[i] if np.isfinite(rk[i]) else 0.0
        dr = dfr[i] if np.isfinite(dfr[i]) else 0.0
        fund_risk *= 1.0 + rr
        fund_defense *= 1.0 + dr
    fund_total = fund_risk + fund_defense
    start_pos = fund_risk / fund_total
    risk = float(initial) * start_pos
    defense = float(initial) * (1.0 - start_pos)
    contrib = set(int(x) for x in contribution_days if lo <= int(x) < hi)
    paid = 0.0
    values = np.empty(hi - lo, dtype=float)
    positions = np.empty(hi - lo, dtype=float)
    turns = np.zeros(hi - lo, dtype=float)

    for j, i in enumerate(range(lo, hi)):
        # 종가 i-1의 신호를 i일에 한 번만 집행한다.
        if i > 0 and (i - 1) % step == 0:
            active = float(w[i - 1])
            fund_total = fund_risk + fund_defense
            actual = fund_risk / fund_total
            turn = abs(active - actual)
            fund_total *= 1.0 - cost * turn
            fund_risk = fund_total * active
            fund_defense = fund_total * (1.0 - active)
            total = (risk + defense) * (1.0 - cost * turn)
            risk, defense = total * active, total * (1.0 - active)
            turns[j] = turn

        fund_total = fund_risk + fund_defense
        positions[j] = fund_risk / fund_total
        # 자료 첫 행에는 선행 종가가 없으므로 수익률 0이라는 기존 엔진 계약을 지킨다.
        rr = 0.0 if i == 0 else (rk[i] if np.isfinite(rk[i]) else 0.0)
        dr = 0.0 if i == 0 else (dfr[i] if np.isfinite(dfr[i]) else 0.0)
        fund_risk *= 1.0 + rr
        fund_defense *= 1.0 + dr
        risk *= 1.0 + rr
        defense *= 1.0 + dr

        if i in contrib:
            fund_total = fund_risk + fund_defense
            actual = fund_risk / fund_total
            risk += actual
            defense += 1.0 - actual
            paid += 1.0
        values[j] = risk + defense

    return values, positions, turns, paid


def curve(rk, dfr, w, cost=COST, step=1):
    values, positions, turns, _ = sleeve_engine(
        rk, dfr, w, step=step, cost=cost)
    return values, positions, float(turns.sum())


def loop_dca(rk, dfr, w, mstart, lo, hi, pay, cost=COST, step=1):
    """공용 잔고 엔진으로 직접 적립 — 빠른 NAV 식의 독립 검산용."""
    days = mstart[(mstart > lo) & (mstart < hi)][:pay]
    values, _, _, paid = sleeve_engine(
        rk, dfr, w, step=step, cost=cost, lo=lo, hi=hi, initial=0.0,
        contribution_days=days)
    return paid, float(values[-1])


def zsc(a, win=756, minp=252):
    s = pd.Series(a)
    a = np.asarray(a, dtype=float)
    return ((a - s.rolling(win, min_periods=minp).mean().values)
            / s.rolling(win, min_periods=minp).std().values)


def candidate(w, step=1):
    return {'w': np.asarray(w, dtype=float), 'step': int(step)}


def duplicate_aliases(cd):
    """같은 목표경로와 같은 집행주기의 뒤쪽 라벨을 앞쪽 라벨의 별칭으로 표시."""
    unique = []
    aliases = {}
    for name, spec in cd.items():
        match = next((old for old in unique
                      if spec['step'] == cd[old]['step']
                      and np.array_equal(spec['w'], cd[old]['w'])), None)
        if match is None:
            unique.append(name)
        else:
            aliases[name] = match
    return aliases


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def self_checks():
    """지연·분포·잔고·비용·적립 계약을 작은 반례로 고정한다."""
    z = np.zeros(4)

    # 신호 t는 수익 t+1에만 닿는다. t와 t+2 어느 쪽으로도 밀리면 실패한다.
    v, p, _, _ = sleeve_engine(
        np.array([0.0, 1.0, 1.0, 0.0]), z, np.array([0.0, 1.0, 1.0, 1.0]),
        cost=0.0)
    require(np.allclose(p, [0.0, 0.0, 1.0, 1.0]), '신호가 정확히 하루 뒤에 적용되지 않았다')
    require(np.allclose(v, [1.0, 1.0, 2.0, 2.0]), '실행 지연 반례의 평가액이 틀렸다')

    # 현재값은 과거 분포에만 놓는다. 현재 관측을 분모에 넣거나 전일 값을 쓰면 깨진다.
    pct = prior_percentile([3.0, 1.0, 2.0, 4.0], min_prior=2)
    require(np.isnan(pct[:2]).all() and np.allclose(pct[2:], [0.5, 1.0]),
            '과거전용 백분위 계약이 깨졌다')

    # 비예약일에는 표류를 그대로 둔다: +100%, -50%는 원금으로 돌아온다.
    risk = np.array([0.0, 1.0, -0.5])
    target = np.full(3, 0.5)
    slow, _, slow_turn, _ = sleeve_engine(risk, np.zeros(3), target,
                                          step=5, cost=0.0)
    daily, _, _, _ = sleeve_engine(risk, np.zeros(3), target,
                                   step=1, cost=0.0)
    require(abs(slow[-1] - 1.0) < 1e-12, '비예약일에 숨은 재조정이 일어났다')
    require(abs(daily[-1] - 1.125) < 1e-12, '일간 재조정 반례가 축퇴하지 않았다')
    require(np.count_nonzero(slow_turn) == 0, '비예약일에 회전량이 잡혔다')

    # 비용은 예약 집행일의 실제 이동분에만 붙는다.
    _, _, turns, _ = sleeve_engine(
        np.zeros(8), np.zeros(8), np.array([.2, .9, .1, .8, .7, .6, .5, .4]),
        step=3, cost=.01)
    require(np.flatnonzero(turns).tolist() == [4, 7], '예약일 밖에서 비용이 발생했다')
    require(np.allclose(turns[[4, 7]], [.6, .3]), '실제 이동 비중 계산이 틀렸다')

    # 직접 적립과 같은 잔고 엔진의 NAV 단위매수가 주간 판에서도 같아야 한다.
    rr = np.array([0, .10, -.03, .02, .04, -.01, .03, -.02, .01, .02, -.01, .01])
    dr = np.array([0, .01, .00, -.01, .01, .00, .01, .00, -.01, .00, .01, .00])
    wt = np.array([.2, .8, .4, .7, .3, .6, .5, .9, .1, .5, .3, .8])
    nav, _, _, _ = sleeve_engine(rr, dr, wt, step=5, cost=.002)
    days = np.array([2, 5, 8])
    direct, _, _, paid = sleeve_engine(
        rr, dr, wt, step=5, cost=.002, lo=1, initial=0.0,
        contribution_days=days)
    expected = sum(nav[-1] / nav[d] for d in days)
    require(paid == len(days) and abs(direct[-1] - expected) < 1e-12,
            '직접 적립과 NAV 단위매수가 일치하지 않는다')

    # NaN 워밍업은 유효 관측 수가 찰 때까지 남는다.
    zz = zsc(np.array([np.nan, np.nan, 1.0, 2.0, 3.0, 4.0]), win=4, minp=3)
    require(np.isnan(zz[:4]).all() and np.isfinite(zz[4:]).all(),
            'NaN 워밍업이 유효 관측 전에 풀렸다')

    toy = {'원형': candidate([1, 0, 1]),
           '별칭': candidate([1, 0, 1]),
           '다른 주기': candidate([1, 0, 1], step=5)}
    require(duplicate_aliases(toy) == {'별칭': '원형'}, '중복 경로 분모 검사가 틀렸다')


def build(D, rv21, rv126, rk):
    ddv = np.asarray(D['ddv'], float)
    n = len(ddv)
    S = pd.Series(np.asarray(D['px'], float))
    base = rule_w(ddv, ENTER, ENTER)
    cd = {'현행 -16/-16': candidate(base)}

    # ---- A. 동적 노출 — 위험점수로 연속 결정 (DD 사다리가 아니다) ----------
    #   오늘 RV를 오늘 이전 RV의 경험분포에 놓는다. 목표는 내일 한 번만 집행한다.
    pct = prior_percentile(rv21, min_prior=252)
    for lo_, hi_ in ((0.5, 0.9), (0.6, 0.95)):
        risk = np.ones(n, dtype=float)              # 분포가 차기 전에는 중립=전량 공격
        valid = np.isfinite(pct)
        risk[valid] = 1.0 - np.clip((pct[valid] - lo_) / (hi_ - lo_), 0, 1)
        cd['A 위험점수 노출 %.0f~%.0f%%' % (lo_ * 100, hi_ * 100)] = candidate(risk)
        # 현행 규칙과 결합 — 방어일 땐 0, 공격일 땐 노출 조절
        cd['A+ 현행 x 위험점수 %.0f~%.0f%%' % (lo_ * 100, hi_ * 100)] = candidate(base * risk)

    # ---- B. 변동성 타깃 ---------------------------------------------------
    #   오늘까지의 21일 변동성으로 오늘 목표를 만들고, 공용 엔진이 내일 집행한다.
    lev_rv = pd.Series(rk).rolling(21, min_periods=21).std().values * np.sqrt(252)
    for tgt in (0.25, 0.35, 0.45):
        w = np.ones(n, dtype=float)
        valid = np.isfinite(lev_rv)
        w[valid] = np.clip(tgt / np.maximum(lev_rv[valid], 1e-6), 0, 1)
        for step, lab in ((1, '일'), (5, '주'), (21, '월')):
            cd['B 변동성타깃 %.0f%% (%s재조정)' % (tgt * 100, lab)] = candidate(w, step)

    # ---- C. 변동성 충격 — 급등에 축소, **정상화되면 빠르게 복원**(래치) ----
    rz = zsc(rv21)
    for on, off in ((1.5, 0.5), (2.0, 0.0), (1.0, 0.0)):
        w = np.empty(n); cur = 1.0
        for i in range(n):
            z = rz[i]
            if not np.isfinite(z):                 # 유효 관측이 찰 때까지 상태를 보존
                w[i] = cur
                continue
            if cur >= 1.0 and z > on:
                cur = 0.0
            elif cur < 1.0 and z < off:
                cur = 1.0
            w[i] = cur
        cd['C 변동성충격 z%.1f->%.1f' % (on, off)] = candidate(w)

    # ---- D. 이진 사건복귀 — 회복은 단 하나의 사건 -------------------------
    low20 = S.rolling(20, min_periods=1).min().values
    px = S.values
    for X in (0.05, 0.08, 0.12):
        w = np.empty(n); cur = 1.0
        for i in range(n):
            if ddv[i] <= ENTER:
                cur = 0.0
            elif cur < 1.0 and px[i] >= low20[i] * (1 + X):
                cur = 1.0                       # 회복 사건 하나만
            w[i] = cur
        cd['D 이진 사건복귀 20d저점+%.0f%%' % (X * 100)] = candidate(w)

    # ---- E. 시간 잠금 — §27 의 직접 시험 ----------------------------------
    for N in (3, 5, 10, 20, 30):
        w = np.empty(n); cur = 1.0; held = 10 ** 9
        for i in range(n):
            want = 0.0 if ddv[i] <= ENTER else (1.0 if ddv[i] > ENTER else cur)
            if want != cur and held >= N:
                # 전환일 자체가 보유 1일째다. 0으로 시작하면 N일 잠금이 실제로는
                # N+1일이 되어 이름과 경로가 어긋난다.
                cur = want; held = 1
            else:
                held += 1
            w[i] = cur
        cd['E 시간잠금 %d일' % N] = candidate(w)

    # ---- F. 회복 사건 — DD 회복폭 한 번으로 복귀 --------------------------
    for Xp in (0.03, 0.05, 0.08):
        w = np.empty(n); cur = 1.0; trough = 0.0
        for i in range(n):
            if ddv[i] <= ENTER:
                if cur >= 1.0:
                    trough = ddv[i]
                cur = 0.0
                trough = min(trough, ddv[i])
            elif cur < 1.0:
                trough = min(trough, ddv[i])
                if ddv[i] - trough >= Xp:
                    cur = 1.0
            w[i] = cur
        cd['F 저점대비 DD +%.0f%%p 회복' % (Xp * 100)] = candidate(w)

    # ---- J. 비대칭 — 진입 DD, 복귀는 사건 ---------------------------------
    #   [주의] 'DD > -16% 또는 반등' 형태는 **무발동**이다. DD 조건이 먼저
    #   참이 되므로 반등 조건이 구속력을 갖지 못한다. v50 초판·v52 초판에
    #   이어 세 번째로 같은 구조를 만들 뻔했다. 의미 있는 비대칭은 반등이
    #   **DD 가 아직 -16% 아래여도** 발동하는 형태인데, 그건 v50 이
    #   'exit_first' 로 이미 시험했고 MDD -81~93% 로 기각됐다.
    #   그래서 여기서는 **DD 조건을 아예 빼고** 반등만으로 복귀하는 판을 쓴다.
    for X in (0.05, 0.08):
        w = np.empty(n); cur = 1.0
        for i in range(n):
            if ddv[i] <= ENTER:
                cur = 0.0
            elif cur < 1.0 and px[i] >= low20[i] * (1 + X):
                cur = 1.0                       # 반등만으로 복귀 (DD 조건 없음)
            w[i] = cur
        cd['J 비대칭 반등%.0f%% 만으로 복귀' % (X * 100)] = candidate(w)
    return cd


def main():
    self_checks()
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    D = dict(D); D['schdr'] = dfr
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]
    S = pd.Series(np.asarray(D['px'], float))
    rv21 = S.pct_change().rolling(21, min_periods=21).std().values
    rv126 = S.pct_change().rolling(126, min_periods=126).std().values

    print("=" * 118)
    print("v55 운용 메커니즘 — 구간 %s ~ %s" % (idx[0].date(), idx[-1].date()))
    print("=" * 118)
    print("  [건너뜀] 전략군 G 유동성(TED·FRA-OIS·SOFR) — FRED 접속 불가, 원천 없음")
    print("  [건너뜀] 전략군 H 크로스에셋 펀딩(USD·유가) — 원천 없음")
    print("  나머지 A~F·J 는 QQQ 종가만으로 계산되고 **1972~ 전구간**이다.\n")
    print("  [합성검산] 1일 지연 · 과거전용 백분위 · 실제 잔고 · 예약일 비용 · 워밍업 PASS\n")

    def dca(c, lo, hi, pay=10 ** 9):
        m = mstart[(mstart > lo) & (mstart < hi)][:pay]
        return float(np.mean(c[hi - 1] / c[m])) if len(m) else np.nan

    # 검산 ① 현행 이진 경로, ② 실제 잔고식 주간 부분비중
    w0 = rule_w(D['ddv'], ENTER, ENTER)
    p0, f0, _ = AX.accumulate(D, K, w0, 0, N)
    c0, _, _ = curve(rk, dfr, w0)
    ref0, _ = AX.sim(D, w0, riskon_r=rk)
    lp0, lf0 = loop_dca(rk, dfr, w0, mstart, 0, N, 10 ** 9)
    e0 = max(abs(dca(c0, 0, N) * lp0 / lf0 - 1),
             abs(lp0 - p0), abs(lf0 / f0 - 1),
             float(np.max(np.abs(c0 / ref0.values - 1))))
    wf = np.where(np.asarray(D['ddv'], float) <= -0.12, 0.4, 0.9)
    cf, _, _ = curve(rk, dfr, wf, step=5)
    p1, v1 = loop_dca(rk, dfr, wf, mstart, 0, N, 10 ** 9, step=5)
    e1 = abs(dca(cf, 0, N) * p1 / v1 - 1)
    print("  [검산1] 현행 이진  vs axis_lib·직접적립       최대오차 %.2e" % e0)
    print("  [검산2] 주간 부분비중 NAV vs 직접적립          상대오차 %.2e" % e1)
    if e0 > 1e-9 or e1 > 1e-9:
        raise SystemExit('  검산 실패')
    print("  둘 다 오차 0.\n")

    cd = build(D, rv21, rv126, rk)
    aliases = duplicate_aliases(cd)
    for x in (5, 8):
        j = 'J 비대칭 반등%d%% 만으로 복귀' % x
        d = 'D 이진 사건복귀 20d저점+%d%%' % x
        require(aliases.get(j) == d, '%s는 %s의 중복 별칭이어야 한다' % (j, d))
    distinct_novel = [nm for nm in cd
                      if nm != '현행 -16/-16' and nm not in aliases]
    st = list(range(0, N - L, 63))
    print("  후보 라벨 %d개 · 서로 다른 후보 경로 %d개 · 20년 창 %d개 · 관문 G1~G6 (완화 없음)\n"
          % (len(cd) - 1, len(distinct_novel), len(st)))

    def ev(spec, cost=COST, sample_step=63):
        w, rebalance_step = spec['w'], spec['step']
        c, pos, sw = curve(rk, dfr, w, cost, step=rebalance_step)
        s = list(range(0, N - L, sample_step))
        isa = np.array([dca(c, x, x + L, 60) for x in s])
        per = np.array([dca(c, x, x + L) for x in s])
        blk = []
        for _, a, b in SEGS:
            lo = int(idx.searchsorted(pd.Timestamp(a)))
            hi = int(idx.searchsorted(pd.Timestamp(b), side='right'))
            blk.append(dca(c, lo, hi))
        return dict(median=float(np.median(isa)), p20=float(np.percentile(isa, 20)),
                    p5=float(np.percentile(isa, 5)), pm=float(np.median(per)),
                    pp5=float(np.percentile(per, 5)),
                    mdd=float((c / np.maximum.accumulate(c) - 1).min()),
                    sw=sw,
                    blk=np.array(blk), c=c)

    R = {nm: ev(spec) for nm, spec in cd.items()}
    B = R['현행 -16/-16']
    print("  %-32s%9s%8s%8s%10s%8s%9s%9s%6s"
          % ('전략', 'ISA중앙', 'P20', 'P5', '영구중앙', '영구P5', 'MDD', '회전량', '블록'))
    order = ['현행 -16/-16'] + sorted([k for k in cd if k != '현행 -16/-16'],
                                     key=lambda k: -R[k]['median'])
    for nm in order:
        r = R[nm]
        ok = int((r['blk'] > B['blk']).sum())
        tag = ('  <- 기준' if nm.startswith('현행') else
               ('  <- **중복 별칭: %s**' % aliases[nm] if nm in aliases else ''))
        print("  %-32s%9.1f%8.1f%8.1f%10.1f%8.1f%8.1f%%%9.0f%4d/4%s"
              % (nm, r['median'], r['p20'], r['p5'], r['pm'], r['pp5'],
                 r['mdd'] * 100, r['sw'], ok, tag))
    if aliases:
        print()
        print("  **중복 별칭 %d개** — 같은 목표경로·집행주기의 뒤쪽 라벨은 표에는 남기되"
              % len(aliases))
        print("  서로 다른 후보 수와 관문 분모에서는 제외한다.")
    print()
    print("  회전량 = |Δ비중| 합계. 이진 전략의 '전환 횟수'와 같은 단위(현행 %.0f)."
          % B['sw'])
    print()

    print("=" * 118)
    print("G1~G6 (완화 없음)")
    print("=" * 118)
    surv = []
    for nm in order:
        if nm.startswith('현행') or nm in aliases:
            continue
        r = R[nm]
        g = [r['median'] > B['median'], r['p20'] > B['p20'], r['p5'] > B['p5'],
             r['pm'] > B['pm'], int((r['blk'] > B['blk']).sum()) >= 3,
             r['mdd'] >= B['mdd'] and r['sw'] <= B['sw'] * 3]
        if sum(g) >= 4:
            print("  %-32s %d/6  %s" % (nm, sum(g), ''.join('O' if x else 'X' for x in g)))
        if all(g):
            surv.append(nm)
    print()
    print("  **G1~G6 전부 통과: %s**" % (', '.join(surv) if surv else '없음'))
    print()
    print("=" * 118)
    print(verdict('운용 메커니즘 변경이 현행을 개선하는가 (§27)', [
        ('G1~G6 를 전부 통과한 후보가 있다', len(surv) > 0,
         '%d개 / 서로 다른 후보 %d개' % (len(surv), len(distinct_novel))),
    ])['text'])
    return R, B, cd, surv, order


if __name__ == '__main__':
    main()
