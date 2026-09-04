# -*- coding: utf-8 -*-
"""
[통합 연구 Part 1, 소유자 지시 2026-08-31] 혼합 x·B+(1−x)·T4 현상의 통계 해부.

이 저장소가 한 번도 쓰지 않은 도구(블록 부트스트랩·ESS·Deflated Sharpe)로
04 §5-3 「혼합 고원」이 구조인지 우연인지 판정한다. 승격 판정 아님(v80) —
증거 강도 평가 전용.

  0. 선형성 검산 — 혼합 일수익 ≈ x·rB+(1−x)·rT4 (블록 부트스트랩의 전제)
  1. 혼합 보너스 분해 — 관측 기하수익 초과분 vs 분산산술 예측(리밸런싱 보너스)
     + 국면(B게이트×T4w) 기여표 + 위기별 해부
  2. H4 잭나이프 — 연도 하나씩 제거해 ΔCalmar·Δp05 부호가 뒤집히는 해가 있는가
  3. 블록 부트스트랩 (moving + stationary, L=20/60/120/252, N=500)
     — H1(Calmar 개선>0)·H2(p05 개선>0)·H3(고원 재현 빈도)
  4. ESS — 20년창 겹침의 유효 독립 표본 수 (비중첩·AR·사건 단위 3방법, 범위 제시)
  5. Deflated Sharpe — 스프레드(mix−B) SR 을 탐색 횟수 N으로 벌점
실행: python research/audit_stat.py   (약 1~3분)
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

import hypo_gates as G                                  # noqa: E402
import hypo_hex as X                                    # noqa: E402
import hypo_t4_real as R                                # noqa: E402

idx = G.idx
n = len(idx)
YRS = n / 252.0
wT4 = R.t4_w(G.r_eq1)

cB = X.three_way(X.wB, 1 - X.wB, np.zeros(n))
cT = X.three_way(wT4, np.zeros(n), 1 - wT4)


def rets(curve):
    """곡선 -> 일수익. 곡선은 1.0 에서 시작한다는 규약이라 첫 수익은 a[0]-1 이다.
    [2026-09-04 코드리뷰] 같은 식이 이 파일에 3벌 · audit_pbo.rets() 에 1벌
    있었다. 곡선 규약이 바뀌면 놓친 사본이 첫 수익만 조용히 틀린다."""
    a = np.asarray(curve.values if hasattr(curve, 'values') else curve, float)
    return np.diff(a, prepend=1.0) / np.concatenate(([1.0], a[:-1]))


rB = rets(cB)
rT = rets(cT)


def curve_of(r):
    return np.cumprod(1 + r)


def mdd_of(a):
    peak = np.maximum.accumulate(a)
    return float(np.min(a / peak - 1))


def calmar_of(a):
    cagr = a[-1] ** (252.0 / len(a)) - 1
    m = mdd_of(a)
    return cagr / abs(m) if m < 0 else np.inf


def p05_20y(a, w=5040, p=0.05):
    if len(a) <= w:
        return np.nan
    return float(np.quantile(a[w:] / a[:-w], p))


def mixr(x):
    return x * rB + (1 - x) * rT


def main():
    rng = np.random.default_rng(42)

    # ---- 0. 선형성 검산 ---------------------------------------------------
    print('[0] 선형성 검산 — 혼합(three_way 정확 실행) vs 일수익 선형결합')
    for x in (0.25, 0.40, 0.55):
        exact = X.blend(x).values
        lin = curve_of(mixr(x))
        dev = float(np.max(np.abs(lin / exact - 1)))
        dc = calmar_of(lin) - calmar_of(exact)
        print(f'  x={x:.2f}: 최종배수 편차 {dev*100:.3f}% · Calmar 차 {dc:+.4f} '
              f'(선형이 근소하게 불리 — 회전 상계 미반영, 이하 분석은 보수적)')

    # ---- 1. 혼합 보너스 분해 ----------------------------------------------
    print('\n[1] 혼합 보너스 분해 (연율)')
    aB, aT = np.mean(rB) * 252, np.mean(rT) * 252
    sB, sT = np.std(rB, ddof=1) * np.sqrt(252), np.std(rT, ddof=1) * np.sqrt(252)
    rho = float(np.corrcoef(rB, rT)[0, 1])
    gB = cB.values[-1] ** (1 / YRS) - 1
    gT = cT.values[-1] ** (1 / YRS) - 1
    print(f'  B: 산술 {aB*100:.2f}% 기하 {gB*100:.2f}% 변동성 {sB*100:.1f}% · '
          f'T4: 산술 {aT*100:.2f}% 기하 {gT*100:.2f}% 변동성 {sT*100:.1f}% · 상관 {rho:.3f}')
    print(f"  {'x':>5} {'관측기하%':>9} {'선형보간%':>9} {'보너스bp':>9} {'예측bp':>7} "
          f"{'잔차bp':>7} {'MDD%':>7} {'선형MDD%':>8}")
    for x in (0.25, 0.40, 0.55, 0.75):
        rm = mixr(x)
        a = curve_of(rm)
        gM = a[-1] ** (1 / YRS) - 1
        interp = x * gB + (1 - x) * gT
        bonus = (gM - interp) * 1e4
        varM = np.var(rm, ddof=1) * 252
        pred = 0.5 * (x * sB**2 + (1 - x) * sT**2 - varM) * 1e4
        mM = mdd_of(a) * 100
        mI = (x * mdd_of(cB.values) + (1 - x) * mdd_of(cT.values)) * 100
        print(f'  {x:>5.2f} {gM*100:>9.2f} {interp*100:>9.2f} {bonus:>9.1f} {pred:>7.1f} '
              f'{bonus-pred:>7.1f} {mM:>7.2f} {mI:>8.2f}')
    print('  (보너스≈예측이면 수익 개선은 분산산술[리밸런싱 보너스] — 마법 아님.'
          ' Calmar 개선의 몸통은 MDD 열: 관측 MDD 가 선형보간 MDD 보다 얕은 만큼이 분산효과)')

    # ---- 1b. 국면 기여표 ---------------------------------------------------
    print('\n[1b] 국면별 스프레드(rT4−rB) — 어느 국면이 혼합을 먹여 살리는가')
    st_att = X.wB > 0.5
    hiT = wT4 >= 0.5
    spread = rT - rB
    rel_log = np.log1p(rT) - np.log1p(rB)
    for nm, m in [('B공격·T4강세', st_att & hiT), ('B공격·T4약세', st_att & ~hiT),
                  ('B방어·T4강세', ~st_att & hiT), ('B방어·T4약세', ~st_att & ~hiT)]:
        d = int(m.sum())
        contrib = float(rel_log[m].sum()) * 100
        print(f'  {nm}: {d:>5}일 ({d/n*100:4.1f}%) · 스프레드 연율 '
              f'{np.mean(spread[m])*252*100:+6.2f}% · 로그기여 합 {contrib:+7.1f}%')

    # ---- 1c. 위기별 해부 ---------------------------------------------------
    print('\n[1c] 위기 구간별 배수 (B / T4 / mix40)')
    crises = [('73-74 오일', '1973-01-11', '1974-10-03'),
              ('80-82 인플레', '1980-11-28', '1982-08-12'),
              ('87 블랙먼데이', '1987-08-25', '1987-12-04'),
              ('닷컴 00-02', '2000-03-10', '2002-10-09'),
              ('GFC 07-09', '2007-10-31', '2009-03-09'),
              ('코로나 20', '2020-02-19', '2020-03-23'),
              ('2022 베어', '2022-01-03', '2022-10-12')]
    m40 = pd.Series(curve_of(mixr(0.40)), index=idx)
    dts = pd.Series(idx)
    for nm, s, e in crises:
        # [2026-09-04 코드리뷰] 종전엔 두 경계 모두 side='left' 라 슬라이스가
        # **종료일을 뺐다.** 실측: 코로나 구간이 2020-03-23 이 아니라 03-20 에서,
        # GFC 가 2009-03-09 가 아니라 03-06 에서 끝났다 — 하필 그 날짜들이 각
        # 위기의 실제 바닥이라 일곱 행 전부 바닥을 못 본 값이었다.
        sl = slice(int(dts.searchsorted(pd.Timestamp(s))),
                   int(dts.searchsorted(pd.Timestamp(e), side='right')))
        vb = cB.values[sl][-1] / cB.values[sl][0]
        vt = cT.values[sl][-1] / cT.values[sl][0]
        vm = m40.values[sl][-1] / m40.values[sl][0]
        print(f'  {nm:<12} B {vb:6.3f} · T4 {vt:6.3f} · mix40 {vm:6.3f}')

    # ---- 2. H4 잭나이프 (연도 제거) ----------------------------------------
    print('\n[2] 잭나이프 — 연도 하나 제거 시 mix40−B 의 ΔCalmar·Δp05 부호')
    years = pd.Series(idx).dt.year.values
    a40 = curve_of(mixr(0.40))
    base_dc = calmar_of(a40) - calmar_of(cB.values)
    base_dp = p05_20y(a40) - p05_20y(cB.values)
    flips_c, flips_p = [], []
    for y in range(int(years[0]), int(years[-1]) + 1):
        keep = years != y
        rb2, rm2 = rB[keep], mixr(0.40)[keep]
        dc = calmar_of(curve_of(rm2)) - calmar_of(curve_of(rb2))
        dp = p05_20y(curve_of(rm2)) - p05_20y(curve_of(rb2))
        if dc < 0:
            flips_c.append(y)
        if np.isfinite(dp) and dp < 0:
            flips_p.append(y)
    print(f'  기준: ΔCalmar {base_dc:+.3f} · Δp05 {base_dp:+.1f}')
    print(f'  ΔCalmar 부호 뒤집는 해: {flips_c if flips_c else "없음"}')
    print(f'  Δp05   부호 뒤집는 해: {flips_p if flips_p else "없음"}')

    # ---- 3. 블록 부트스트랩 -------------------------------------------------
    print('\n[3] 블록 부트스트랩 — (rB,rT4) 동시행 재표집, N=500/설정')
    print('    ⚠ 블록 경계는 다년 약세장을 자른다 — L=252 가 주판정, 짧은 L 은 민감도')
    XS = np.arange(0.05, 0.951, 0.05)

    def one_config(L, stationary, nrep=500, batch=100):
        cnt = dict(h1=0, h2=0, both=0, plateau6=0, plat40=0)
        dcs = []
        for b0 in range(0, nrep, batch):
            m = min(batch, nrep - b0)
            if stationary:
                # stationary bootstrap: 기하분포 블록길이 평균 L, 순환 연결
                starts = rng.integers(0, n, size=(m, n))
                cont = rng.random((m, n)) > (1.0 / L)
                pos = np.empty((m, n), dtype=np.int64)
                pos[:, 0] = starts[:, 0]
                for t in range(1, n):
                    nxt = (pos[:, t - 1] + 1) % n
                    pos[:, t] = np.where(cont[:, t], nxt, starts[:, t])
            else:
                nblk = n // L + 1
                # [2026-09-04 코드리뷰] 종전 `n - L` 은 상한 배타라 시작점이
                # 최대 n-L-1 이었고 **마지막 관측 rB[n-1] 이 어떤 재표집에도
                # 못 들어갔다.** stationary 쪽은 순환이라 그 구멍이 없어 두
                # 방식이 서로 다른 모집단을 뽑고 있었다.
                st = rng.integers(0, n - L + 1, size=(m, nblk))
                pos = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(m, -1)[:, :n]
            RB, RT = rB[pos], rT[pos]
            AB = np.cumprod(1 + RB, axis=1)
            AT = np.cumprod(1 + RT, axis=1)

            def met2(A):
                peak = np.maximum.accumulate(A, axis=1)
                mdd = np.min(A / peak - 1, axis=1)
                cagr = A[:, -1] ** (252.0 / n) - 1
                cal = cagr / np.abs(mdd)
                p05 = np.quantile(A[:, 5040:] / A[:, :-5040], 0.05, axis=1)
                return cal, p05

            calB, p05B = met2(AB)
            calT, p05T = met2(AT)
            cal_x, p05_x = {}, {}
            for x in XS:
                Ax = np.cumprod(1 + x * RB + (1 - x) * RT, axis=1)
                cal_x[round(x, 2)], p05_x[round(x, 2)] = met2(Ax)
            c40, p40 = cal_x[0.40], p05_x[0.40]
            cnt['h1'] += int(np.sum(c40 > calB))
            cnt['h2'] += int(np.sum(p40 > p05B))
            cnt['both'] += int(np.sum((c40 > calB) & (p40 > p05B)))
            dcs.extend((c40 - calB).tolist())
            # 고원: 관문①(calB×1.102)·②(p05B) 동시 통과 연속 칸 수
            passmat = np.stack([(cal_x[round(x, 2)] > calB * 1.102)
                                & (p05_x[round(x, 2)] >= p05B) for x in XS])  # (19, m)
            runlen = np.zeros(m, dtype=int)
            cur = np.zeros(m, dtype=int)
            for k in range(len(XS)):
                cur = np.where(passmat[k], cur + 1, 0)
                runlen = np.maximum(runlen, cur)
            cnt['plateau6'] += int(np.sum(runlen >= 6))
            k40 = int(round((0.40 - 0.05) / 0.05))
            cnt['plat40'] += int(np.sum(passmat[k40]))
        dcs = np.asarray(dcs)
        # [코드리뷰] 실제 반복수를 같이 돌려준다 — 종전엔 호출부가 500 을 박아
        # 나눠서 nrep 을 바꾸면 백분율이 조용히 틀렸다.
        return cnt, float(np.median(dcs)), float(np.quantile(dcs, 0.05)), nrep

    print(f"  {'방식':<10} {'L':>4} {'H1 ΔCal>0':>9} {'H2 Δp05>0':>9} {'동시':>6} "
          f"{'고원≥6칸':>8} {'x=.40통과':>9} {'ΔCal중앙':>8} {'5%분위':>7}")
    for stat_, Ls in ((False, (20, 60, 120, 252)), (True, (60, 252))):
        for L in Ls:
            c, med, q5, N = one_config(L, stat_)
            nm = 'stationary' if stat_ else 'moving'
            print(f"  {nm:<10} {L:>4} {c['h1']/N:>9.1%} {c['h2']/N:>9.1%} "
                  f"{c['both']/N:>6.1%} {c['plateau6']/N:>8.1%} {c['plat40']/N:>9.1%} "
                  f"{med:>8.3f} {q5:>7.3f}")

    # ---- 4. ESS -----------------------------------------------------------
    print('\n[4] 20년창 유효 독립 표본 수 (Neff)')
    aB_ = cB.values
    mults = aB_[5040:] / aB_[:-5040]
    N = len(mults)
    nonlap20 = n / 5040
    print(f'  창 수 {N} · 비중첩: 20년 {nonlap20:.1f}개 · 10년 {n/2520:.1f}개 · 5년 {n/1260:.1f}개')
    # [2026-09-04 코드리뷰] 여기 있던 `dm = np.diff(np.log(mults))` 는 계산만 하고
    # 아무 데서도 안 쓰였다. 아래 자기상관은 로그차분이 아니라 **수준(mults)** 으로
    # 잰다 — 읽는 사람이 둘 중 어느 쪽이 의도인지 알 수 없어서 죽은 줄을 지웠다.
    x_ = mults - mults.mean()
    ac = np.correlate(x_, x_, 'full')[N - 1:] / (x_ @ x_)
    k = 1
    s = 0.0
    while k < N and ac[k] > 0.05:
        s += ac[k]
        k += 1
    ess = N / (1 + 2 * s)
    print(f'  AR-ESS(20년배수 계열, ρ>0.05 까지 합산 k={k}): {ess:.1f}개')
    lo5 = mults <= np.quantile(mults, 0.05)
    ends = pd.Series(idx[5040:])[lo5]
    gaps = ends.diff().dt.days.fillna(9999)
    print(f'  p05 이하 창 {int(lo5.sum())}개의 종료일 군집(1년 격리): '
          f'{int((gaps > 365).sum())}개 사건 — 종료 시기 {ends.dt.year.min()}~{ends.dt.year.max()}')
    # [2026-09-04 코드리뷰] 종전엔 여기에 「비중첩 2.7」이 **박혀** 있었다. 바로 위
    # 줄이 같은 값을 자료에서 계산해 2.8 로 찍는데 여기만 2.7 이라, 한 출력 안에서
    # 같은 통계가 두 값으로 나왔다(§-1 ④). 계산한 값을 그대로 쓴다.
    print(f'  → Neff 범위 [비중첩 {nonlap20:.1f}, 사건 군집 수] — p05 는 사실상 소수 사건 통계다')

    # ---- 5. Deflated Sharpe (스프레드 mix40−B) ------------------------------
    print('\n[5] Deflated Sharpe — 개선분(스프레드)의 SR 을 탐색 벌점으로 깎으면')
    sp = mixr(0.40) - rB
    sr = np.mean(sp) / np.std(sp, ddof=1)
    g3 = float(pd.Series(sp).skew())
    g4 = float(pd.Series(sp).kurt()) + 3
    T = len(sp)
    # 시험 SR 분산: 이번 주 실제 탐색한 후보군의 스프레드 SR 표본
    trials = []
    for x in XS:
        s2 = mixr(float(x)) - rB
        trials.append(np.mean(s2) / np.std(s2, ddof=1))
    v40, v60 = X.vscale(0.40), X.vscale(0.60)
    others = [X.three_way(X.wB * wT4, 1 - X.wB, X.wB * (1 - wT4)),
              X.three_way(X.wB * v40, 1 - X.wB, X.wB * (1 - v40)),
              X.three_way(X.wB * v60, 1 - X.wB, X.wB * (1 - v60)),
              X.three_way(X.wB * v60, 1 - X.wB * v60, np.zeros(n))]
    for c in others:
        s2 = rets(c) - rB                                  # [코드리뷰] 공용 rets() 경유
        trials.append(np.mean(s2) / np.std(s2, ddof=1))
    vtr = float(np.var(trials, ddof=1))
    from math import erf, sqrt

    def ncdf(z):
        return 0.5 * (1 + erf(z / sqrt(2)))

    def nppf(p):
        # Beasley-Springer-Moro 근사 (표준 구현, |오차|<3e-9)
        a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
        b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01]
        c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
        d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
             3.754408661907416e+00]
        pl, ph = 0.02425, 1 - 0.02425
        if p < pl:
            q = np.sqrt(-2 * np.log(p))
            return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                   ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        if p > ph:
            q = np.sqrt(-2 * np.log(1 - p))
            return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                   ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        q = p - 0.5
        r_ = q * q
        return (((((a[0]*r_+a[1])*r_+a[2])*r_+a[3])*r_+a[4])*r_+a[5])*q / \
               (((((b[0]*r_+b[1])*r_+b[2])*r_+b[3])*r_+b[4])*r_+1)

    em = 0.5772156649
    for Ntr in (8, 23, 100, 500):
        sr0 = np.sqrt(vtr) * ((1 - em) * nppf(1 - 1.0 / Ntr)
                              + em * nppf(1 - 1.0 / (Ntr * np.e)))
        z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr**2)
        print(f'  N시험={Ntr:>4}: SR0(기대최댓값) {sr0:.4f} · 일간SR {sr:.4f} '
              f'→ DSR {ncdf(z):.3f}')
    print(f'  (시험 SR 분산은 실제 탐색 후보 {len(trials)}개에서 추정 · '
          f'스프레드 왜도 {g3:.2f} 첨도 {g4:.1f})')


if __name__ == '__main__':
    main()
