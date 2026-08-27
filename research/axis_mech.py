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
  D  최소 상태기계  3상태(공격/방어/회복). 회복은 **단 하나의 사건**으로만
  E  시간 잠금     현행 규칙 + 최소 유지일 N. **§27 의 직접 시험**
  F  회복 사건     저점 대비 X% 회복 한 번으로 복귀
  J  비대칭       진입은 DD, 복귀는 사건. 서로 다른 정보원

[규약]
  · 부분비중은 **매일 목표비중 재조정**을 기본 가정으로 하고, B 는 주/월도 잰다.
  · 빠른 적립식 식(mean c[T]/c[t_m])은 부분비중에서도 성립하는지 **먼저 검산**한다.
  · 전환 횟수를 반드시 함께 보고한다(§4, G6).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
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


def curve(rk, dfr, w, cost=COST):
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * t)), pos


def loop_dca(rk, dfr, w, mstart, lo, hi, pay):
    """부분비중 루프 시뮬 — 빠른 식 검산용. 납입금은 목표비중대로 나눠 넣는다."""
    pos = np.r_[w[0], w[:-1]]
    R = C = paid = 0.0
    p = pos[lo]
    mset = set(mstart[(mstart > lo) & (mstart < hi)][:pay].tolist())
    for i in range(lo, hi):
        q = pos[i]
        if q != p:
            tot = (R + C) * (1 - COST * abs(q - p))
            R, C = tot * q, tot * (1 - q)
            p = q
        R *= (1 + np.nan_to_num(rk[i])); C *= (1 + np.nan_to_num(dfr[i]))
        if i in mset:
            paid += 1.0; R += q; C += (1 - q)
        tot = R + C
        R, C = tot * q, tot * (1 - q)           # 매일 목표비중으로 재조정
    return paid, R + C


def zsc(a, win=756, minp=252):
    s = pd.Series(a)
    return ((a - s.rolling(win, min_periods=minp).mean().values)
            / s.rolling(win, min_periods=minp).std().values)


def rebal(w, step):
    """재조정 주기 적용 — step 거래일마다만 비중을 바꾼다."""
    if step <= 1:
        return w
    o = w.copy()
    cur = w[0]
    for i in range(len(w)):
        if i % step == 0:
            cur = w[i]
        o[i] = cur
    return o


def build(D, rv21, rv126, rk):
    ddv = np.asarray(D['ddv'], float)
    n = len(ddv)
    S = pd.Series(np.asarray(D['px'], float))
    base = rule_w(ddv, ENTER, ENTER)
    cd = {'현행 -16/-16': base}

    # ---- A. 동적 노출 — 위험점수로 연속 결정 (DD 사다리가 아니다) ----------
    #   위험점수 = RV 의 **확장창 백분위**(시점별. 전표본 백분위는 미래참조다)
    pct = pd.Series(rv21).expanding(min_periods=252).rank(pct=True).shift(1).values
    for lo_, hi_ in ((0.5, 0.9), (0.6, 0.95)):
        s = np.clip((np.nan_to_num(pct, nan=0.0) - lo_) / (hi_ - lo_), 0, 1)
        cd['A 위험점수 노출 %.0f~%.0f%%' % (lo_ * 100, hi_ * 100)] = 1.0 - s
        # 현행 규칙과 결합 — 방어일 땐 0, 공격일 땐 노출 조절
        cd['A+ 현행 x 위험점수 %.0f~%.0f%%' % (lo_ * 100, hi_ * 100)] = base * (1.0 - s)

    # ---- B. 변동성 타깃 ---------------------------------------------------
    #   추정 변동성 = 레버리지 자산의 21일 실현변동성(연율). shift(1) 필수.
    lev_rv = pd.Series(rk).rolling(21, min_periods=21).std().shift(1).values * np.sqrt(252)
    for tgt in (0.25, 0.35, 0.45):
        w = np.clip(np.nan_to_num(tgt / np.maximum(lev_rv, 1e-6), nan=1.0), 0, 1)
        for step, lab in ((1, '일'), (5, '주'), (21, '월')):
            cd['B 변동성타깃 %.0f%% (%s재조정)' % (tgt * 100, lab)] = rebal(w, step)

    # ---- C. 변동성 충격 — 급등에 축소, **정상화되면 빠르게 복원**(래치) ----
    rz = zsc(np.nan_to_num(rv21, nan=0.0))
    for on, off in ((1.5, 0.5), (2.0, 0.0), (1.0, 0.0)):
        w = np.empty(n); cur = 1.0
        for i in range(n):
            z = np.nan_to_num(rz[i], nan=0.0)
            if cur >= 1.0 and z > on:
                cur = 0.0
            elif cur < 1.0 and z < off:
                cur = 1.0
            w[i] = cur
        cd['C 변동성충격 z%.1f->%.1f' % (on, off)] = w

    # ---- D. 최소 상태기계 — 회복은 단 하나의 사건 -------------------------
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
        cd['D 3상태 회복 20d저점+%.0f%%' % (X * 100)] = w

    # ---- E. 시간 잠금 — §27 의 직접 시험 ----------------------------------
    for N in (3, 5, 10, 20, 30):
        w = np.empty(n); cur = 1.0; held = 10 ** 9
        for i in range(n):
            want = 0.0 if ddv[i] <= ENTER else (1.0 if ddv[i] > ENTER else cur)
            if want != cur and held >= N:
                cur = want; held = 0
            else:
                held += 1
            w[i] = cur
        cd['E 시간잠금 %d일' % N] = w

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
        cd['F 저점대비 DD +%.0f%%p 회복' % (Xp * 100)] = w

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
        cd['J 비대칭 반등%.0f%% 만으로 복귀' % (X * 100)] = w
    return cd


def main():
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

    def dca(c, lo, hi, pay=10 ** 9):
        m = mstart[(mstart > lo) & (mstart < hi)][:pay]
        return float(np.mean(c[hi - 1] / c[m])) if len(m) else np.nan

    # 검산 ① 이진, ② 부분비중
    w0 = rule_w(D['ddv'], ENTER, ENTER)
    p0, f0, _ = AX.accumulate(D, K, w0, 0, N)
    c0, _ = curve(rk, dfr, w0)
    e0 = abs(dca(c0, 0, N) * p0 / f0 - 1)
    wf = np.where(np.asarray(D['ddv'], float) <= -0.12, 0.4, 0.9)
    cf, _ = curve(rk, dfr, wf)
    p1, v1 = loop_dca(rk, dfr, wf, mstart, 0, N, 10 ** 9)
    e1 = abs(dca(cf, 0, N) * p1 / v1 - 1)
    print("  [검산1] 이진비중  vs axis_lib.accumulate()  상대오차 %.2e" % e0)
    print("  [검산2] 부분비중  vs 루프 시뮬              상대오차 %.2e" % e1)
    if e0 > 1e-9 or e1 > 1e-9:
        raise SystemExit('  검산 실패')
    print("  둘 다 오차 0.\n")

    cd = build(D, rv21, rv126, rk)
    st = list(range(0, N - L, 63))
    print("  후보 %d개 · 20년 창 %d개 · 관문 G1~G6 (완화 없음)\n" % (len(cd), len(st)))

    def ev(w, cost=COST, step=63):
        c, pos = curve(rk, dfr, w, cost)
        s = list(range(0, N - L, step))
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
                    sw=float(np.abs(np.diff(pos)).sum()),
                    blk=np.array(blk), c=c)

    R = {nm: ev(w) for nm, w in cd.items()}
    B = R['현행 -16/-16']
    print("  %-32s%9s%8s%8s%10s%8s%9s%9s%6s"
          % ('전략', 'ISA중앙', 'P20', 'P5', '영구중앙', '영구P5', 'MDD', '회전량', '블록'))
    order = ['현행 -16/-16'] + sorted([k for k in cd if k != '현행 -16/-16'],
                                     key=lambda k: -R[k]['median'])
    dead = []
    for nm in order:
        r = R[nm]
        ok = int((r['blk'] > B['blk']).sum())
        same = (not nm.startswith('현행')
                and abs(r['median'] - B['median']) < 1e-9 and abs(r['sw'] - B['sw']) < 1e-9)
        if same:
            dead.append(nm)
        tag = '  <- 기준' if nm.startswith('현행') else ('  <- **무발동**' if same else '')
        print("  %-32s%9.1f%8.1f%8.1f%10.1f%8.1f%8.1f%%%9.0f%4d/4%s"
              % (nm, r['median'], r['p20'], r['p5'], r['pm'], r['pp5'],
                 r['mdd'] * 100, r['sw'], ok, tag))
    if dead:
        print()
        print("  **무발동 %d개** — 조건이 한 번도 구속력을 갖지 못해 현행과 동일하다."
              % len(dead))
        print("  후보로 세지 않는다. (v50·v52 초판에서 같은 실수를 했다)")
    print()
    print("  회전량 = |Δ비중| 합계. 이진 전략의 '전환 횟수'와 같은 단위(현행 %.0f)."
          % B['sw'])
    print()

    print("=" * 118)
    print("G1~G6 (완화 없음)")
    print("=" * 118)
    surv = []
    for nm in order:
        if nm.startswith('현행'):
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
         '%d개 / 후보 %d개' % (len(surv), len(cd) - 1)),
    ])['text'])
    return R, B, cd, surv, order


if __name__ == '__main__':
    main()
