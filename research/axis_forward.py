# -*- coding: utf-8 -*-
"""
[v59] 앞으로의 위험을 직접 추정하면 나아지는가 — 5개 축

§40 의 질문:
  **"현행의 우위가 좋은 문턱 하나를 찾은 것인가, 아니면 폭락 episode 의 미래
    위험과 반등의 질을 실시간 추정해 더 좋은 타이밍을 할 수 있는가?"**

[다섯 축]
  A  Episode Oracle       각 폭락에서 **사후 최적 복귀일**. 타이밍의 이론적 상한
  B  Forward risk         "앞으로 20일 안에 추가 -10% 할 확률"을 워크포워드로 추정
  C  Change-point         CUSUM / 분산 단절로 생성과정 변화를 탐지
  D  Episode + 반등의 질   저점대비 회복 · 신저점 없음 · 변동성 완화의 결합
  E  CVaR 목적함수         하위 5% **평균**(꼬리손실)으로 격자를 다시 줄세운다

[규율 — 완화하지 않는다]
  §23 완전 워크포워드: 10년 학습 -> 1년 적용. 학습창은 라벨이 필요한 20일을 **뺀다**
      (안 빼면 라벨이 학습창 밖 미래를 본다 — 미묘한 누수다)
  §24 전체기간으로 feature 고르고 같은 기간에서 평가하는 것 **금지**
  §22 결과를 본 뒤 feature·model 을 계속 추가하지 않는다. 이 설계로 한 번만 돈다
  §25 2026-08-27 이후 데이터는 쓰지 않는다 (현재 자료 마지막은 2026-08-26)
  §30 복잡도 감점: 단순 문턱 < 통계모형 < 다변수 ML. 복잡한 쪽은 **명백한** 추가
      성과가 있을 때만 고려한다. sklearn 이 없어 로지스틱을 직접 구현했다(IRLS).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ENTER = -0.16
H, XDROP = 20, -0.10        # 라벨: 앞으로 20일 안에 추가 -10%
TRAIN = 10 * 252
L = 20 * 252
SEGS = [('1972-85', '1972-01-01', '1985-12-31'),
        ('1986-99', '1986-01-01', '1999-12-31'),
        ('2000-13', '2000-01-01', '2013-12-31'),
        ('2014-26', '2014-01-01', '2026-12-31')]


# ============================================================ 로지스틱 (IRLS)
def logistic_fit(X, y, iters=25, ridge=1e-3):
    """sklearn 없이. 표준화된 X 에 절편을 붙여 IRLS 로 푼다."""
    n, k = X.shape
    A = np.c_[np.ones(n), X]
    b = np.zeros(k + 1)
    for _ in range(iters):
        z = np.clip(A @ b, -30, 30)
        p = 1 / (1 + np.exp(-z))
        w = np.maximum(p * (1 - p), 1e-6)
        Hm = A.T @ (A * w[:, None]) + ridge * np.eye(k + 1)
        g = A.T @ (y - p) - ridge * b
        try:
            b = b + np.linalg.solve(Hm, g)
        except np.linalg.LinAlgError:
            break
    return b


def logistic_pred(b, X):
    z = np.clip(np.c_[np.ones(len(X)), X] @ b, -30, 30)
    return 1 / (1 + np.exp(-z))


# ============================================================ 본체
def main():
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, 2)
    ddv = np.asarray(D['ddv'], float)
    px = np.asarray(D['px'], float)
    S = pd.Series(px)
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]
    base = rule_w(ddv, ENTER, ENTER)

    def curve(w, cost=COST):
        pos = np.r_[w[0], w[:-1]]
        r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
        t = np.abs(np.diff(pos, prepend=pos[0]))
        return np.cumprod((1 + r) * (1 - cost * t)), pos

    def dca(c, lo, hi, pay=10 ** 9):
        m = mstart[(mstart > lo) & (mstart < hi)][:pay]
        return float(np.mean(c[hi - 1] / c[m])) if len(m) else np.nan

    def ev(w, cost=COST, step=63, y0=0):
        c, pos = curve(w, cost)
        st = list(range(y0, N - L, step))
        isa = np.array([dca(c, s, s + L, 60) for s in st])
        per = np.array([dca(c, s, s + L) for s in st])
        seg = c[y0:]
        blk = []
        for _, a, b in SEGS:
            lo = int(idx.searchsorted(pd.Timestamp(a)))
            hi = int(idx.searchsorted(pd.Timestamp(b), side='right'))
            blk.append(np.nan if lo < y0 else dca(c, lo, hi))
        return dict(median=float(np.median(isa)), p20=float(np.percentile(isa, 20)),
                    p5=float(np.percentile(isa, 5)),
                    cvar5=float(np.mean(np.sort(isa)[:max(1, len(isa) // 20)])),
                    pm=float(np.median(per)),
                    mdd=float((seg / np.maximum.accumulate(seg) - 1).min()),
                    sw=int((np.abs(np.diff(pos[y0:])) > 1e-9).sum()),
                    blk=np.array(blk), c=c, isa=isa)

    print("=" * 116)
    print("v59 — 미래 위험 추정 5개 축. 구간 %s ~ %s" % (idx[0].date(), idx[-1].date()))
    print("      §25 동결 준수: 2026-08-27 이후 자료 없음(마지막 %s)" % idx[-1].date())
    print("=" * 116)

    # ------------------------------------------------ 에피소드 정의 (§14)
    eps = []
    i = 0
    while i < N:
        if ddv[i] <= ENTER:
            j = i
            while j < N and ddv[j] <= ENTER:
                j += 1
            k = j
            while k < N and ddv[k] <= ENTER:
                k += 1
            eps.append((i, j))
            i = j
            while i < N and ddv[i] > ENTER:
                i += 1
        else:
            i += 1
    print()
    print("  폭락 episode %d개 (DD <= -16%% 진입 ~ -16%% 회복)" % len(eps))

    # ------------------------------------------------ A. Episode Oracle (§17)
    print()
    print("=" * 116)
    print("A. Episode Oracle — 각 폭락에서 **사후 최적 복귀일**. 타이밍의 이론적 상한")
    print("=" * 116)
    w_or = base.copy()
    for n_, (i, j) in enumerate(eps):
        hi = eps[n_ + 1][0] if n_ + 1 < len(eps) else N
        best, bv = j, -1e18
        for k in range(i, hi):
            w = base.copy(); w[i:k] = 0.0; w[k:hi] = 1.0
            c, _ = curve(w)
            v = c[hi - 1] / c[max(i - 1, 0)]
            if v > bv:
                bv, best = v, k
        w_or[i:best] = 0.0; w_or[best:hi] = 1.0
    O = ev(w_or)
    B = ev(base)
    print("  %-24s%9s%8s%8s%10s%9s%7s" % ('', 'ISA중앙', 'P20', 'P5', '영구중앙', 'MDD', '전환'))
    print("  %-24s%9.1f%8.1f%8.1f%10.1f%8.1f%%%7d  <- 기준"
          % ('현행 -16/-16', B['median'], B['p20'], B['p5'], B['pm'], B['mdd'] * 100, B['sw']))
    print("  %-24s%9.1f%8.1f%8.1f%10.1f%8.1f%%%7d  <- **상한(미래참조)**"
          % ('Episode Oracle', O['median'], O['p20'], O['p5'], O['pm'],
             O['mdd'] * 100, O['sw']))
    gap = O['median'] / B['median'] - 1
    print()
    print("  **Oracle - 현행 = %+.0f%%** — episode 안에서 복귀일만 완벽히 골라도 이만큼이다."
          % (gap * 100))

    # ------------------------------------------------ 특징량 (전부 후행)
    rv = S.pct_change().rolling(21, min_periods=21).std().values
    rvz = ((rv - pd.Series(rv).rolling(756, min_periods=252).mean().values)
           / pd.Series(rv).rolling(756, min_periods=252).std().values)
    dd20 = np.r_[np.zeros(20), ddv[20:] - ddv[:-20]]
    rv10 = np.r_[np.zeros(10), rv[10:] - rv[:-10]]
    low60 = S.rolling(60, min_periods=1).min().values
    rec = px / np.maximum(low60, 1e-9) - 1
    inep = np.zeros(N); days = np.zeros(N)
    for (i, j) in eps:
        hi = j
        inep[i:hi] = 1
        days[i:hi] = np.arange(hi - i)
    F = np.column_stack([np.nan_to_num(ddv), np.nan_to_num(dd20),
                         np.nan_to_num(rvz), np.nan_to_num(rv10) * 100,
                         np.nan_to_num(rec), np.log1p(days) / 5.0])
    FN = ['DD', 'DD20일변화', '변동성z', '변동성10일변화', '저점대비회복', '도피경과일']

    # 라벨: 앞으로 H일 안에 추가 XDROP
    fut = np.full(N, np.nan)
    for t in range(N - H):
        fut[t] = px[t + 1:t + 1 + H].min() / px[t] - 1
    y = (fut <= XDROP).astype(float)

    # ------------------------------------------------ B. Forward risk (§23)
    print()
    print("=" * 116)
    print("B. Forward risk — 'H=%d일 안에 추가 %.0f%%%%' 확률을 워크포워드로 추정" % (H, XDROP * 100))
    print("=" * 116)
    P = np.full(N, np.nan)
    y0 = TRAIN + 252
    for t0 in range(y0, N, 252):                       # 1년마다 재학습
        a = max(0, t0 - TRAIN)
        b_ = t0 - H - 1                                # **라벨 누수 방지**: H일 뺀다
        if b_ - a < 504:
            continue
        m = np.isfinite(fut[a:b_])
        Xtr, ytr = F[a:b_][m], y[a:b_][m]
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        beta = logistic_fit((Xtr - mu) / sd, ytr)
        t1 = min(t0 + 252, N)
        P[t0:t1] = logistic_pred(beta, (F[t0:t1] - mu) / sd)
    ok = np.isfinite(P) & np.isfinite(fut)
    print("  예측 가능 구간 %s ~ %s (%d일)"
          % (idx[y0].date(), idx[-1].date(), int(ok.sum())))
    # G13 보정 (§27)
    brier = float(np.mean((P[ok] - y[ok]) ** 2))
    base_rate = float(y[ok].mean())
    brier0 = float(np.mean((base_rate - y[ok]) ** 2))
    print("  기저확률 %.1f%%  ·  Brier %.4f (상수예측 %.4f, 개선 %.1f%%)"
          % (base_rate * 100, brier, brier0, (1 - brier / brier0) * 100))
    print()
    print("  %-14s%10s%10s%12s" % ('예측확률 구간', '표본', '실제빈도', '평균예측'))
    for lo_, hi_ in ((0, .1), (.1, .2), (.2, .35), (.35, .5), (.5, 1.01)):
        m = ok & (P >= lo_) & (P < hi_)
        if m.sum() < 30:
            continue
        print("  %-14s%10d%9.1f%%%11.1f%%" % ('%.0f~%.0f%%' % (lo_ * 100, hi_ * 100),
              int(m.sum()), y[m].mean() * 100, P[m].mean() * 100))

    cd = {'현행 -16/-16': base, 'A Episode Oracle (상한)': w_or}
    for th in (0.15, 0.25, 0.35):
        w = base.copy(); cur = 1.0
        for t in range(N):
            if ddv[t] <= ENTER:
                cur = 0.0
            elif cur < 1.0:
                p = P[t]
                if not np.isfinite(p) or p <= th:
                    cur = 1.0                          # 위험이 낮아지면 복귀
            w[t] = cur
        cd['B 위험확률<%.0f%% 복귀' % (th * 100)] = w

    # ------------------------------------------------ C. Change-point (§11)
    r1 = np.nan_to_num(S.pct_change().values)
    mu = pd.Series(r1).rolling(252, min_periods=60).mean().shift(1).values
    sg = pd.Series(r1).rolling(252, min_periods=60).std().shift(1).values
    zz = np.nan_to_num((r1 - np.nan_to_num(mu)) / np.maximum(np.nan_to_num(sg, nan=1), 1e-9))
    for k_ in (3.0, 5.0):
        cus = np.zeros(N); w = np.ones(N); cur = 1.0
        s_ = 0.0
        for t in range(N):
            s_ = min(0.0, s_ + zz[t] + 0.5)            # 하방 CUSUM
            cus[t] = s_
            if cur >= 1.0 and s_ < -k_:
                cur = 0.0; s_ = 0.0
            elif cur < 1.0 and s_ > -0.5 and ddv[t] > ENTER:
                cur = 1.0
            w[t] = cur
        cd['C CUSUM k=%.0f' % k_] = w

    # ------------------------------------------------ D. 반등의 질 (§19/§20)
    newlow = np.zeros(N, bool)
    for (i, j) in eps:
        run = -1e18
        for t in range(i, j):
            if px[t] <= run * 1.0001:
                newlow[t] = True
            run = min(run, px[t]) if run > -1e17 else px[t]
            run = min(run, px[t])
    nl20 = pd.Series(newlow.astype(float)).rolling(20, min_periods=1).max().values
    for X in (0.05, 0.08):
        w = base.copy(); cur = 1.0
        for t in range(N):
            if ddv[t] <= ENTER:
                cur = 0.0
            elif cur < 1.0:
                # [주의] 여기 'or ddv[t] > ENTER' 를 붙이면 **무발동**이다.
                # 이 분기는 이미 ddv[t] > ENTER 일 때만 도달하므로 항상 참이 된다.
                # v50·v52·v55 초판에 이어 네 번째로 같은 구조를 만들 뻔했다.
                # 반등의 질을 **추가 조건**으로 걸어 복귀를 늦춘다.
                q = (rec[t] >= X) and (nl20[t] < 0.5) and (np.nan_to_num(rv10[t]) < 0)
                if q:
                    cur = 1.0
            w[t] = cur
        cd['D 반등의질 %.0f%%+신저점없음+변동성완화' % (X * 100)] = w

    # ------------------------------------------------ 평가
    print()
    print("=" * 116)
    print("결과 — 전부 같은 엔진·같은 비용·같은 체결규약")
    print("=" * 116)
    R = {nm: ev(w) for nm, w in cd.items()}
    print("  %-34s%9s%8s%8s%9s%10s%9s%7s%6s"
          % ('전략', 'ISA중앙', 'P20', 'P5', 'CVaR5', '영구중앙', 'MDD', '전환', '블록'))
    for nm in cd:
        r = R[nm]
        bw = int(np.nansum(r['blk'] > B['blk']))
        mk = '  <- 기준' if nm.startswith('현행') else ('  <- 상한' if 'Oracle' in nm else '')
        print("  %-34s%9.1f%8.1f%8.1f%9.1f%10.1f%8.1f%%%7d%4d/4%s"
              % (nm, r['median'], r['p20'], r['p5'], r['cvar5'], r['pm'],
                 r['mdd'] * 100, r['sw'], bw, mk))

    dead = [nm for nm in cd if not nm.startswith('현행') and 'Oracle' not in nm
            and abs(R[nm]['median'] - B['median']) < 1e-9 and R[nm]['sw'] == B['sw']]
    if dead:
        print()
        print("  **무발동 %d개**: %s" % (len(dead), ', '.join(dead)))
        print("  조건이 구속력을 갖지 못해 현행과 동일하다. 후보로 세지 않는다.")

    # ------------------------------------------------ Oracle 복귀일 분석 (§35/§37)
    print()
    print("=" * 116)
    print("A-2. Oracle 은 언제 돌아가나 — 왜 +%.0f%% 를 못 잡는가" % (gap * 100))
    print("=" * 116)
    rows = []
    for n_, (i, j) in enumerate(eps):
        hi = eps[n_ + 1][0] if n_ + 1 < len(eps) else N
        best, bv = j, -1e18
        for k in range(i, hi):
            w = base.copy(); w[i:k] = 0.0; w[k:hi] = 1.0
            c, _ = curve(w)
            v = c[hi - 1] / c[max(i - 1, 0)]
            if v > bv:
                bv, best = v, k
        trough = int(np.argmin(ddv[i:hi])) + i
        rows.append((idx[i], best - j, best - trough, hi - i, ddv[trough]))
    d_ = np.array([r[1] for r in rows], float)
    tt = np.array([r[2] for r in rows], float)
    print("  %d개 episode 에서 **Oracle 복귀일 - 현행 복귀일** (거래일)" % len(rows))
    print("    중앙 %+.0f일  ·  평균 %+.0f일  ·  표준편차 %.0f일" % (np.median(d_), d_.mean(), d_.std()))
    print("    현행보다 **빨리** 돌아간 episode %d개 / 늦게 %d개 / 같음 %d개"
          % (int((d_ < 0).sum()), int((d_ > 0).sum()), int((d_ == 0).sum())))
    print()
    print("  **Oracle 복귀일 - 그 episode 저점** (거래일)")
    print("    중앙 %+.0f일  ·  표준편차 %.0f일  ·  범위 %+.0f ~ %+.0f"
          % (np.median(tt), tt.std(), tt.min(), tt.max()))
    print()
    print("  -> 최적 복귀일이 **저점 근처에 몰려 있지 않고 산포가 크면** 사전 예측이 불가능하다.")

    # ------------------------------------------------ E. CVaR 목적함수 (§7)
    print()
    print("=" * 116)
    print("E. CVaR 목적함수 — 하위 5% **평균**으로 격자 210개를 다시 줄세우면")
    print("=" * 116)
    combos = [(round(e, 2), round(x, 2)) for e in np.arange(-0.24, -0.09, 0.01)
              for x in np.arange(e, -0.03, 0.01)]
    cv = {}
    for c in combos:
        rr = ev(rule_w(ddv, c[0], c[1]))
        cv[c] = (rr['cvar5'], rr['median'], rr['p5'])
    order = sorted(combos, key=lambda c: -cv[c][0])
    ic = order.index((-0.16, -0.16)) + 1
    print("  %-12s%10s%10s%10s" % ('규칙', 'CVaR5', 'ISA중앙', 'P5'))
    for c in order[:5]:
        mk = '  <- 현행' if c == (-0.16, -0.16) else ''
        print("  %-12s%10.1f%10.1f%10.1f%s" % ('%.0f/%.0f' % (c[0] * 100, c[1] * 100),
              cv[c][0], cv[c][1], cv[c][2], mk))
    if ic > 5:
        c = (-0.16, -0.16)
        print("  ...")
        print("  %-12s%10.1f%10.1f%10.1f  <- 현행 (%d위/%d)"
              % ('-16/-16', cv[c][0], cv[c][1], cv[c][2], ic, len(combos)))
    print()
    print("  **현행의 CVaR5 순위: %d위 / %d**" % (ic, len(combos)))

    # ------------------------------------------------ 판정
    print()
    print("=" * 116)
    win = []
    for nm in cd:
        if nm.startswith('현행') or 'Oracle' in nm:
            continue
        r = R[nm]
        if (r['median'] > B['median'] and r['p20'] > B['p20'] and r['p5'] > B['p5']
                and r['pm'] > B['pm'] and int(np.nansum(r['blk'] > B['blk'])) >= 3
                and r['mdd'] >= B['mdd']):
            win.append(nm)
    print(verdict('미래 위험 추정이 현행을 개선하는가 (§40)', [
        ('G1~G6 를 전부 통과한 후보가 있다', len(win) > 0,
         ', '.join(win) if win else '없음 / 후보 %d개' % (len(cd) - 2)),
        ('Episode Oracle 이 현행을 크게 앞선다 (타이밍 잠재력)', gap > 0.10,
         'Oracle-현행 %+.0f%%' % (gap * 100)),
        ('예측이 상수예측보다 낫다 (G13)', brier < brier0,
         'Brier %.4f vs %.4f' % (brier, brier0)),
    ], adopt_if=['G1~G6 를 전부 통과한 후보가 있다'])['text'])
    return R, B, O, cd, gap


if __name__ == '__main__':
    main()
