# -*- coding: utf-8 -*-
"""
[v50] 광역 탐색 — 현행과 **다른 원리**로 작동하는 전략이 있는가

외부 제안(ChatGPT)의 설계 문서를 그대로 실행한다. 이미 답이 있는 군은 반복하지 않는다.

  A  12M 절대모멘텀      v49 기각      -> A' 다중기간·가속만
  D  이중모멘텀          v49 기각      -> D' 상대강도 변형만
  E  실현변동성 임계      v32 기각      -> E' 변화율·정점통과만
  H  단계적 비중(DCA)     v49 완료      -> 반복 안 함
  B,C,F,G,I,J                          -> 전부 새로 잰다

[제안 §23 이 핵심을 짚었다 — 그대로 따른다]
  v46/v49 가 밝힌 기전: 현행의 우위는 **V자 반등 초입을 잡는 것**에서 나온다.
  모멘텀처럼 신호를 **늦추는** 것은 전부 졌다(v49, 승률 0/71).
  그러니 이번엔 **더 빠르게** 감지·확인하는 쪽만 판다:
    · 진입은 -16% 그대로 두거나 **더 빠르게**
    · 복귀를 **저점 대비 회복률·반등·저점갱신중단**으로 더 빨리 확인
    · 복귀 조건을 급락 성격에 따라 **적응**

[관문 6개 — 완화하지 않는다]
  G1 ISA 중앙  G2 ISA P20  G3 ISA P5  G4 영구 중앙
  G5 4블록 일관성(3/4 이상)  G6 현실성(전환 횟수)

[검산] 빠른 식은 v48/v49 에서 이진 2.55e-15 · 부분 7.88e-14 로 확인됨. 여기서 재확인한다.
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


# ================================================================= 엔진
def curve_of(rk, dfr, w):
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - COST * t)), pos


def dca(c, mstart, lo, hi, pay):
    m = mstart[(mstart > lo) & (mstart < hi)][:pay]
    return float(np.mean(c[hi - 1] / c[m])) if len(m) else np.nan


def mdd(c):
    return float((c / np.maximum.accumulate(c) - 1).min())


# ================================================================= 상태기계
def machine(enter_ok, exit_ok, n, exit_first=False):
    """enter_ok[i]=True 면 방어로, exit_ok[i]=True 면 공격으로.

    exit_first=False : 진입 우선. 복귀는 DD 가 -16% 위로 올라온 날에만 가능하다.
                       -> 복귀조건이 그때 거의 항상 참이면 **현행과 동일해진다.**
    exit_first=True  : 복귀 우선. DD 가 아직 -16% 아래여도 복귀신호가 뜨면 돌아간다.
                       제안 §23 이 요구한 '반등을 더 빠르게 확인' 이 이쪽이다.
                       v50 초판이 이걸 빠뜨려 후보 4개가 현행과 똑같이 나왔다.
    """
    w = np.empty(n); cur = 1.0
    for i in range(n):
        if exit_first:
            if cur < 1.0 and exit_ok[i]:
                cur = 1.0
            elif enter_ok[i]:
                cur = 0.0
        else:
            if enter_ok[i]:
                cur = 0.0
            elif cur < 1.0 and exit_ok[i]:
                cur = 1.0
        w[i] = cur
    return w


def stateful(ddv, enter_ok, ret_fn, n):
    """복귀 판단에 '이번 도피의 저점·경과일'이 필요한 후보용."""
    w = np.empty(n); cur = 1.0
    trough = 0.0; since = 0; ent_i = -1
    for i in range(n):
        if enter_ok[i]:
            if cur >= 1.0:
                trough = ddv[i]; since = 0; ent_i = i
            cur = 0.0
        if cur < 1.0:
            since += 1
            trough = min(trough, ddv[i])
            if not enter_ok[i] and ret_fn(i, trough, since, ent_i):
                cur = 1.0
        w[i] = cur
    return w


# ================================================================= 후보
def build(D, rk, dfr):
    px = np.asarray(D['px'], dtype=float)
    ddv = np.asarray(D['ddv'], dtype=float)
    n = len(ddv)
    S = pd.Series(px)
    cd = {}

    base_enter = ddv <= ENTER
    cd['현행 -16/-16'] = rule_w(ddv, ENTER, ENTER)

    # ---- 보조 시계열 -------------------------------------------------------
    def roll_min(k):
        return S.rolling(k, min_periods=1).min().values

    def roll_max(k):
        return S.rolling(k, min_periods=1).max().values

    dchg = {k: np.r_[np.zeros(k), ddv[k:] - ddv[:-k]] for k in (5, 10, 20)}
    rv = S.pct_change().rolling(21, min_periods=21).std().values
    rv_chg = np.r_[np.zeros(21), rv[21:] - rv[:-21]]
    upfrac = {k: S.pct_change().gt(0).rolling(k, min_periods=k).mean().values
              for k in (10, 20, 60)}
    dcum = np.cumprod(1 + np.nan_to_num(dfr))

    def ret(a, k):
        r = np.full(n, np.nan); r[k:] = a[k:] / a[:-k] - 1
        return r

    # ============================================ B — DD 의 시간 구조
    # B1 진입 가속: 얕아도 **빠르게** 무너지면 즉시 방어 (현행보다 빠름)
    for lvl, k, spd in ((-0.10, 10, -0.08), (-0.12, 10, -0.08), (-0.10, 20, -0.12)):
        e = base_enter | ((ddv <= lvl) & (dchg[k] <= spd))
        cd['B1 진입가속 %d%%/%dd/%d%%' % (lvl * 100, k, spd * 100)] = \
            machine(e, ddv > ENTER, n)

    # B4 저점 대비 회복률 R% 에서 복귀 (현행보다 **빠를 수도 늦을 수도** 있다)
    for R in (0.25, 0.40, 0.55, 0.70):
        cd['B4 저점대비 %d%% 회복' % (R * 100)] = stateful(
            ddv, base_enter,
            lambda i, tr, since, e, R=R: ddv[i] >= tr * (1 - R), n)

    # B5 DD 가 -16% 위로 올라온 뒤 N일 유지되면 복귀 (확인 지연)
    for N in (3, 10):
        ok = pd.Series(ddv > ENTER).rolling(N, min_periods=N).min().fillna(0).values > 0
        cd['B5 회복 %d일 확인' % N] = machine(base_enter, ok, n)

    # B6 급락/완만 구분 — 빨리 떨어졌으면 빨리 복귀, 천천히면 -16% 유지
    cd['B6 급락이면 -11%, 완만하면 -16%'] = stateful(
        ddv, base_enter,
        lambda i, tr, since, e: ddv[i] > (-0.11 if (e >= 20 and dchg[20][e] <= -0.12) else ENTER), n)

    # B2 DD 가속도 — 악화가 멈추면 복귀
    slow = (dchg[5] > 0) & (dchg[10] > 0)
    cd['B2 DD 악화중단 + -16% 회복'] = machine(base_enter, (ddv > ENTER) & slow, n)
    cd['B2b DD 악화중단만으로 복귀'] = machine(base_enter, slow & (dchg[5] > 0.02), n)

    # ============================================ C — 단기 반전
    #   [빠름] = 복귀 우선. DD 가 -16% 아래여도 반등이 확인되면 돌아간다.
    for k, X in ((20, 0.05), (20, 0.08), (10, 0.05), (40, 0.10)):
        lowk = roll_min(k)
        reb = px >= lowk * (1 + X)
        cd['C 반등 %dd저점+%d%%' % (k, X * 100)] = machine(base_enter, reb, n)
        cd['C[빠름] 반등 %dd저점+%d%%' % (k, X * 100)] = machine(base_enter, reb, n, True)

    # ============================================ F — 고점·저점 구조
    for k in (10, 20):
        lowk = roll_min(k)
        nonew = px > lowk * 1.0001            # 최근 k일 저점을 안 깼다
        cd['F 저점갱신중단 %dd' % k] = machine(base_enter, nonew, n)
        cd['F[빠름] 저점갱신중단 %dd' % k] = machine(base_enter, nonew, n, True)
    cd['F 20d 신고가 복귀'] = machine(base_enter, px >= roll_max(20) * 0.999, n)
    cd['F[빠름] 20d 신고가 복귀'] = machine(base_enter, px >= roll_max(20) * 0.999, n, True)

    # ============================================ I — 동적 복귀선
    # 저점 이후 회복 속도가 빠르면 즉시, 정체되면 대기
    cd['I 회복속도 적응 (10d +5%)'] = stateful(
        ddv, base_enter,
        lambda i, tr, since, e: (px[i] / roll_min(10)[i] - 1) > 0.05 or ddv[i] > ENTER, n)
    cd['I2 도피 60일 넘으면 -11% 로 완화'] = stateful(
        ddv, base_enter,
        lambda i, tr, since, e: ddv[i] > (-0.11 if since > 60 else ENTER), n)

    # ============================================ E' — 변동성 구조
    cd["E' 변동성 정점통과 복귀"] = machine(
        base_enter, (ddv > ENTER) | ((rv_chg < 0) & (ddv > -0.25)), n)
    cd["E' 하락+변동성급등 진입가속"] = machine(
        base_enter | ((ddv <= -0.10) & (rv_chg > np.nanpercentile(rv_chg, 90))),
        ddv > ENTER, n)

    # ============================================ D' — 상대강도 변형
    q3, d3 = ret(px, 63), ret(dcum, 63)
    cd["D' QQQ-방어 3M 상대강도 회복"] = machine(
        base_enter, (np.nan_to_num(q3, nan=1.) > np.nan_to_num(d3, nan=0.)), n)

    # ============================================ A' — 모멘텀 가속
    q1, q6 = ret(px, 21), ret(px, 126)
    cd["A' 단기가속 (1M>0 & 1M>6M/6)"] = machine(
        base_enter,
        (np.nan_to_num(q1, nan=1.) > 0) & (np.nan_to_num(q1, nan=1.) > np.nan_to_num(q6, nan=0.) / 6), n)

    # ============================================ J — 단순 규칙
    for k, p in ((20, 0.5), (10, 0.6), (60, 0.5)):
        cd['J 상승일비율 %dd>%d%%' % (k, p * 100)] = machine(
            base_enter, np.nan_to_num(upfrac[k], nan=1.) > p, n)
    lo252, hi252 = roll_min(252), roll_max(252)
    posn = (px - lo252) / np.maximum(hi252 - lo252, 1e-12)
    cd['J 가격위치 252d>40%'] = machine(base_enter, posn > 0.40, n)

    # ============================================ G — DD 개선폭 복귀
    # 초판에서 4/6 관문을 통과한 유일한 후보. 인접 파라미터도 함께 본다(제안 §13/§18).
    #   규칙: 현행 -16/-16 + **도피 중이라도 DD 가 최근 k일간 g%p 이상 개선되면 즉시 복귀**
    #   미래참조 없음: dchg[k][i] = ddv[i] - ddv[i-k], 체결은 pos = w.shift(1).
    for k in (10, 20, 40):
        if k not in dchg:
            dchg[k] = np.r_[np.zeros(k), ddv[k:] - ddv[:-k]]
        for g in (0.02, 0.03, 0.05, 0.08):
            w = np.where(ddv > ENTER, 1.0, 0.0)
            w = np.where((ddv <= ENTER) & (dchg[k] > g), 1.0, w)
            cd['G DD개선 %dd>+%d%%p' % (k, g * 100)] = w
    return cd


# ================================================================= 평가
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

    print("=" * 118)
    print("v50 광역 탐색 — 구간 %s ~ %s" % (idx[0].date(), idx[-1].date()))
    print("=" * 118)
    w0 = rule_w(D['ddv'], ENTER, ENTER)
    p0, f0, _ = AX.accumulate(D, K, w0, 0, N)
    c0, _ = curve_of(rk, dfr, w0)
    print("  [검산] 빠른 식 vs axis_lib.accumulate()  상대오차 %.2e"
          % abs(dca(c0, mstart, 0, N, 10 ** 9) * p0 / f0 - 1))
    print()

    cd = build(D, rk, dfr)
    L = 20 * 252
    st = list(range(0, N - L, 126))
    print("  후보 %d개 · 20년 창 %d개  (관문 6개, 완화 없음)\n" % (len(cd), len(st)))

    C = {nm: curve_of(rk, dfr, w) for nm, w in cd.items()}
    BASE = '현행 -16/-16'
    R = {}
    for nm in cd:
        c, pos = C[nm]
        isa = np.array([dca(c, mstart, s, s + L, 60) for s in st])
        per = np.array([dca(c, mstart, s, s + L, 10 ** 9) for s in st])
        blk = []
        for _, a, b in SEGS:
            lo = int(idx.searchsorted(pd.Timestamp(a)))
            hi = int(idx.searchsorted(pd.Timestamp(b), side='right'))
            blk.append(dca(c, mstart, lo, hi, 10 ** 9))
        R[nm] = dict(isa=isa, per=per, blk=np.array(blk), mdd=mdd(c),
                     sw=int((np.abs(np.diff(pos)) > 1e-9).sum()))
    B = R[BASE]

    def q(v, p):
        return float(np.percentile(v, p))

    print("  %-34s%8s%8s%8s%9s%8s%8s%7s%7s"
          % ('전략', 'ISA중앙', 'P20', 'P5', '영구중앙', 'P5', 'MDD', '블록', '전환'))
    order = [BASE] + sorted([k for k in cd if k != BASE],
                            key=lambda k: -np.median(R[k]['isa']))
    for nm in order:
        r = R[nm]
        wins = int((r['blk'] > B['blk']).sum())
        cur = (nm == BASE)
        print("  %-34s%8.1f%8.1f%8.1f%9.1f%8.1f%7.1f%%%5d/4%7d%s"
              % (nm, np.median(r['isa']), q(r['isa'], 20), q(r['isa'], 5),
                 np.median(r['per']), q(r['per'], 5), r['mdd'] * 100,
                 wins, r['sw'], '  <- 기준' if cur else ''))

    print()
    print("=" * 118)
    print("관문 6개 통과 여부 (완화 없음)")
    print("=" * 118)
    passed = []
    for nm in order:
        if nm == BASE:
            continue
        r = R[nm]
        g = [np.median(r['isa']) > np.median(B['isa']),
             q(r['isa'], 20) > q(B['isa'], 20),
             q(r['isa'], 5) > q(B['isa'], 5),
             np.median(r['per']) > np.median(B['per']),
             int((r['blk'] > B['blk']).sum()) >= 3,
             r['sw'] <= B['sw'] * 3]
        if sum(g) >= 4:
            print("  %-34s  통과 %d/6  %s" % (nm, sum(g),
                  ''.join('O' if x else 'X' for x in g)))
        if all(g):
            passed.append(nm)
    print()
    print("  **6관문 전부 통과: %s**" % (', '.join(passed) if passed else '없음'))
    print()
    print("  G1 ISA중앙 · G2 ISA P20 · G3 ISA P5 · G4 영구중앙 · G5 4블록 3/4 · G6 전환 3배이내")
    print()
    print("=" * 118)
    print(verdict('현행과 다른 원리의 전략이 현행을 대체하는가', [
        ('6관문 전부 통과한 후보가 있다', len(passed) > 0,
         '%d개 / 후보 %d개' % (len(passed), len(cd) - 1)),
    ])['text'])
    return R, B, order, cd, C, mstart, idx, st, L


if __name__ == '__main__':
    main()
