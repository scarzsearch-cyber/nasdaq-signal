# -*- coding: utf-8 -*-
"""
[v32] 변동성 조기방어 — v31 기각의 재심

v31 §4 는 이 후보를 "파라미터 첨탑 / 워크포워드 실패 / 데이터 편중" 으로 기각했다.
**앞의 두 근거는 틀렸다.**

  - '첨탑' 은 격자의 잘못된 단면을 본 것이다. v31 은 룩백 21일 x 게이트 -5~-12%
    만 봤는데, 워크포워드가 실제로 고르는 영역은 룩백 5~14일 x 게이트 -1~-4% 다.
    그 영역은 42칸 전부가 MDD 를 개선하는 **평지**다.
  - 워크포워드 실패는 **수익 기준으로 골랐기 때문**이다. 수익으로 고르면 첨탑을
    고르게 된다. Calmar 로 고르면 8개 분할에서 파라미터가 안정적으로 수렴한다
    (항상 룩백 10일 / 게이트 -3%, 분위만 p90~p95).

여기서는 **워크포워드가 고른 파라미터만** 쓴다. 내가 고르지 않는다.
그리고 실전 조건 — 실제 방어 바스켓(40/40/20), 원화, 두 규칙(A/B) — 으로 검증한다.

규칙:  실현변동성(10일)이 역대 p92.5 이상이고 낙폭이 이미 -3% 이하면 즉시 방어.
       복귀는 기존과 동일.
"""
import sys
import numpy as np
import pandas as pd

import hist_data as H
import hist_defasset as DA
import hist_defensive as DF
import hist_krfinal as KF
from axis_lib import COST, rule_w
from axis_defmix import materials, mix_monthly_from

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

LB, Q, GATE = 10, 0.925, -0.03           # 워크포워드가 고른 값. 손대지 않는다.
KEYS = ['div', 'ust5', 'gold']
W4020 = {'div': 0.40, 'ust5': 0.40, 'gold': 0.20}
FXS = pd.Timestamp('1981-04-13')


def zc(a, win=756, minp=252):
    s = pd.Series(np.asarray(a, dtype=float)).reset_index(drop=True)
    return ((s - s.rolling(win, min_periods=minp).mean())
            / s.rolling(win, min_periods=minp).std()).fillna(0).values


def exp_q(a, q, minp=252):
    s = pd.Series(np.asarray(a, dtype=float)).reset_index(drop=True)
    return s.expanding(min_periods=minp).quantile(q).shift(1).values


def guard_w(ddq, trig, enter, exit_, gate=GATE):
    return rule_w(np.where(trig & (ddq <= gate), -0.20, ddq), enter, exit_)


def sim(qldr, defr, w, cost=COST, lag=1, lo=0, hi=None):
    n = len(w) if hi is None else hi
    sl = slice(lo, n)
    wv = w[sl]
    pos = np.empty_like(wv)
    pos[:lag] = wv[0]
    pos[lag:] = wv[:-lag]
    r = np.nan_to_num(pos * qldr[sl] + (1 - pos) * defr[sl])
    r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * t))


def st(c, n):
    g = c[-1] ** (252 / n) - 1
    m = (c / np.maximum.accumulate(c) - 1).min()
    return c[-1], g, m, g / abs(m)


def row(lbl, cb, cc, n, w=None, wb=None):
    vb, gb, db, kb = st(cb, n)
    vc, gc, dc, kc = st(cc, n)
    tn = ''
    if w is not None:
        tn = f"  전환 {np.abs(np.diff(wb)).sum():.0f}->{np.abs(np.diff(w)).sum():.0f}"
    print(f"  {lbl:<22} {vb:>11,.1f} -> {vc:>11,.1f} [{(vc/vb-1)*100:+6.1f}%]   "
          f"MDD {db*100:6.2f}% -> {dc*100:6.2f}% [{-(abs(dc)-abs(db))*100:+5.2f}p]   "
          f"Calmar {kb:.3f}->{kc:.3f}{tn}")
    return (vc / vb - 1), -(abs(dc) - abs(db)) * 100, kc - kb


def main():
    D = DF.build('chain')
    idx = D['idx']
    ddq = D['ddv']
    N = len(idx)
    rv = zc(D['px'].pct_change().rolling(LB, min_periods=LB).std().values)
    trig = rv >= exp_q(rv, Q)
    print(f"규칙: 실현변동성 {LB}일 z >= 확장창 p{Q*100:.1f}  AND  낙폭 <= {GATE*100:.0f}%  -> 즉시 방어")
    print(f"구간 {idx[0].date()} ~ {idx[-1].date()}  ({N}거래일)")
    print(f"발동일 {int((trig & (ddq <= GATE)).sum())}일 ({(trig & (ddq <= GATE)).sum()/N*100:.1f}%)\n")

    # ---------------------------------------------------------------- 1. 실제 바스켓
    print("=" * 108)
    print("1. 실제 방어 바스켓 40/40/20 (배당40·국채5Y 40·금20, 월 재조정) · 달러 기준")
    print("=" * 108)
    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in KEYS}, W4020, idx)
    for lbl, (e, x) in [('A -16/-11', (-0.16, -0.11)), ('B -16/-16', (-0.16, -0.16))]:
        wb = rule_w(ddq, e, x)
        wc = guard_w(ddq, trig, e, x)
        row(lbl, sim(D['qldr'], defr, wb), sim(D['qldr'], defr, wc), N, wc, wb)

    # ---------------------------------------------------------------- 2. 구간 분해
    print("\n" + "=" * 108)
    print("2. 데이터 구간 분해 — v31 의 세 번째 기각 근거 (이득이 합성구간에만 있나)")
    print("=" * 108)
    wb = rule_w(ddq, -0.16, -0.11)
    wc = guard_w(ddq, trig, -0.16, -0.11)
    for nm, s, e in [('1972-1985 종합지수', '1972-02-07', '1985-09-30'),
                     ('1985-1999 NDX', '1985-10-01', '1999-03-09'),
                     ('1999- QQQ 실물', '1999-03-10', '2026-08-26'),
                     ('2000- (닷컴 포함)', '2000-01-01', '2026-08-26'),
                     ('2011- (현대)', '2011-10-25', '2026-08-26')]:
        lo = int(idx.searchsorted(pd.Timestamp(s)))
        hi = int(idx.searchsorted(pd.Timestamp(e), side='right'))
        row(nm, sim(D['qldr'], defr, wb, lo=lo, hi=hi),
            sim(D['qldr'], defr, wc, lo=lo, hi=hi), hi - lo)

    # ---------------------------------------------------------------- 3. 롤링
    print("\n" + "=" * 108)
    print("3. 롤링 창 — 승률과 좌측꼬리 (v31 은 20년 창 승률 43.3% 로 탈락시켰다)")
    print("=" * 108)
    cb = sim(D['qldr'], defr, wb)
    cc = sim(D['qldr'], defr, wc)
    for yrs in (10, 15, 20):
        L = yrs * 252
        rb = np.array([cb[s + L] / cb[s] for s in range(0, N - L, 63)])
        rc = np.array([cc[s + L] / cc[s] for s in range(0, N - L, 63)])
        mb = np.array([(cb[s:s+L] / np.maximum.accumulate(cb[s:s+L]) - 1).min()
                       for s in range(0, N - L, 63)])
        mc = np.array([(cc[s:s+L] / np.maximum.accumulate(cc[s:s+L]) - 1).min()
                       for s in range(0, N - L, 63)])
        print(f"  {yrs}년 창 n={len(rb):3d}  수익승률 {(rc>rb).mean()*100:5.1f}%  "
              f"MDD개선률 {(np.abs(mc)<np.abs(mb)).mean()*100:5.1f}%  |  "
              f"중앙 {np.median(rb):8.2f}->{np.median(rc):8.2f}  "
              f"5분위 {np.percentile(rb,5):7.2f}->{np.percentile(rc,5):7.2f}  "
              f"최악 {rb.min():6.2f}->{rc.min():6.2f}  "
              f"MDD중앙 {np.median(mb)*100:6.2f}%->{np.median(mc)*100:6.2f}%")

    # ---------------------------------------------------------------- 4. 플라시보
    print("\n" + "=" * 108)
    print("4. 블록 플라시보 (500회) — 뭉침 유지하고 신호구간만 옮긴다")
    print("=" * 108)
    rng = np.random.default_rng(42)
    mask = trig
    seg, i = [], 0
    while i < N:
        if mask[i]:
            j = i
            while j < N and mask[j]:
                j += 1
            seg.append(j - i)
            i = j
        else:
            i += 1
    real_v, _, real_m, _ = st(cc, N)
    bv, bm = 0, 0
    for _ in range(500):
        rm = np.zeros(N, dtype=bool)
        for ln in seg:
            s0 = rng.integers(0, N - ln)
            rm[s0:s0 + ln] = True
        c = sim(D['qldr'], defr, guard_w(ddq, rm, -0.16, -0.11))
        v, _, m, _ = st(c, N)
        if v >= real_v:
            bv += 1
        if abs(m) <= abs(real_m):
            bm += 1
    print(f"  신호구간 {len(seg)}개")
    print(f"  수익이 같거나 나음 {bv}/500 ({bv/500*100:.1f}%)   "
          f"MDD 가 같거나 나음 {bm}/500 ({bm/500*100:.1f}%)   (5% 미만이어야 통과)")

    # ---------------------------------------------------------------- 5. 비용
    print("\n" + "=" * 108)
    print("5. 비용 민감도 — 전환이 늘어난 만큼 비용에 취약해지는가")
    print("=" * 108)
    for c_ in (0.001, 0.002, 0.003, 0.005, 0.01):
        a = sim(D['qldr'], defr, wb, cost=c_)[-1]
        b = sim(D['qldr'], defr, wc, cost=c_)[-1]
        print(f"  편도 {c_*100:4.1f}%   기준 {a:>11,.1f}   후보 {b:>11,.1f}   [{(b/a-1)*100:+6.1f}%]")

    # ---------------------------------------------------------------- 6. 원화
    print("\n" + "=" * 108)
    print("6. 원화 — 실제로 사게 될 통화 (1981-, DEXKOUS 시작)")
    print("=" * 108)
    Dk, kidx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    kcomp = {'div': np.asarray(dfk, dtype=float),
             'ust5': (1 + DA.ust_tr(kidx, 5, 'TNX')) * (1 + fr) - 1,
             'gold': (1 + DA.gold_r(kidx)) * (1 + fr) - 1}
    kdefr = mix_monthly_from(kcomp, W4020, kidx)
    lo = int(kidx.searchsorted(FXS))
    nk = len(kidx) - lo
    for lbl, (e, x) in [('A -16/-11', (-0.16, -0.11)), ('B -16/-16', (-0.16, -0.16))]:
        kb = rule_w(ddq, e, x)
        kc = guard_w(ddq, trig, e, x)
        row(lbl + ' 원화', sim(lev2, kdefr, kb, lo=lo), sim(lev2, kdefr, kc, lo=lo), nk)
    print("  [대조] 같은 창의 달러")
    for lbl, (e, x) in [('A -16/-11', (-0.16, -0.11)), ('B -16/-16', (-0.16, -0.16))]:
        lo2 = int(idx.searchsorted(FXS))
        ub = rule_w(ddq, e, x)
        uc = guard_w(ddq, trig, e, x)
        row(lbl + ' 달러', sim(D['qldr'], defr, ub, lo=lo2),
            sim(D['qldr'], defr, uc, lo=lo2), N - lo2)

    # ---------------------------------------------------------------- 7. 고정 vs 선택
    print("\n" + "=" * 108)
    print("7. **핵심** — 파라미터를 고르는 것과 못박는 것 중 뭐가 나은가")
    print("   겹치지 않는 5년 창 9개. 고정 = 미리 못박은 값 / 선택 = 직전까지 Calmar 최대")
    print("=" * 108)
    FIX = {'(10,p92.5,-3%)': (10, 0.925, -0.03), '(14,p90,-2%)': (14, 0.90, -0.02),
           '(10,p90,-4%)': (10, 0.90, -0.04)}
    FW = {}
    for nm, (lb, q, g) in FIX.items():
        r_ = zc(D['px'].pct_change().rolling(lb, min_periods=lb).std().values)
        FW[nm] = guard_w(ddq, r_ >= exp_q(r_, q), -0.16, -0.11, gate=g)
    LBS, QS, GATES = (5, 7, 10, 14, 21), (0.875, 0.90, 0.925, 0.95), (-0.02, -0.03, -0.04, -0.05)
    SEL = {}
    for lb in LBS:
        r_ = zc(D['px'].pct_change().rolling(lb, min_periods=lb).std().values)
        for q in QS:
            t_ = r_ >= exp_q(r_, q)
            for g in GATES:
                SEL[(lb, q, g)] = guard_w(ddq, t_, -0.16, -0.11, gate=g)

    for tag, qq, dd, ii in [('달러', D['qldr'], defr, idx), ('원화', lev2, kdefr, kidx)]:
        print("\n  --- %s ---" % tag)
        print(f"  {'창':<12}{'기준MDD':>9}" + "".join(f"{n:>19}" for n in FIX) + f"{'선택(WFA)':>17}")
        acc = {n: [] for n in list(FIX) + ['선택(WFA)']}
        for yr in range(1982, 2023, 5):
            sp = int(ii.searchsorted(pd.Timestamp('%d-01-01' % yr)))
            ep = int(ii.searchsorted(pd.Timestamp('%d-12-31' % (yr + 4)), side='right'))
            if ep - sp < 800:
                continue
            n_ = ep - sp
            _, g0, d0, k0 = st(sim(qq, dd, wb, lo=sp, hi=ep), n_)
            cells = []
            for nm in FIX:
                _, _, d1, k1 = st(sim(qq, dd, FW[nm], lo=sp, hi=ep), n_)
                acc[nm].append(((abs(d1) - abs(d0)) * 100, k1 - k0))
                cells.append("%+7.2fp/%+6.3f" % (-(abs(d1) - abs(d0)) * 100, k1 - k0))
            bk, bvv = None, -1e9
            for k_, w_ in SEL.items():
                _, g_, d_, _ = st(sim(qq, dd, w_, lo=0, hi=sp), sp)
                cl = g_ / abs(d_) if d_ < 0 else -1
                if cl > bvv:
                    bvv, bk = cl, k_
            _, _, d2, k2 = st(sim(qq, dd, SEL[bk], lo=sp, hi=ep), n_)
            acc['선택(WFA)'].append(((abs(d2) - abs(d0)) * 100, k2 - k0))
            cells.append("%+6.2fp/%+6.3f" % (-(abs(d2) - abs(d0)) * 100, k2 - k0))
            print(f"  {'%d-%d' % (yr, yr+4):<12}{d0*100:8.2f}%" + "".join(f"{c:>19}" for c in cells[:3])
                  + f"{cells[3]:>17}")
        print()
        for nm in acc:
            a = np.array([x[0] for x in acc[nm]])
            b = np.array([x[1] for x in acc[nm]])
            print(f"    {nm:<16} MDD개선 {(a<0).sum()}/{len(a)} 중앙 {-np.median(a):+.2f}p"
                  f"   Calmar개선 {(b>0).sum()}/{len(b)} 중앙 {np.median(b):+.3f}")
        print("    -> 고정이 선택보다 나으면 '최적화하지 말고 못박으라'는 뜻이다.")

    print("\n[판정] 전략_v32.md 에 기록")


if __name__ == '__main__':
    main()
