# -*- coding: utf-8 -*-
"""
[새 길 탐구 · 가상] 기계가 정책을 배우면 — 걸어가며 재학습하는 예측 정책 + 「규칙 재발견」 검사 (2026-09-03, 소유자 「알파고처럼 너만의 길」)

무덤에서 가장 가까운 것은 v59 「위험확률 예측모형(IRLS)」 — 한 번 맞춘 로지스틱이 고확률 구간에서 과신(64% → 실제 36%)이라 기각. 그건 **한 번
학습**이었고 정책으로 돌린 적도 없다. 여기서는 셋을 한다:
  M1 걸어가며 재학습하는 로지스틱 정책: 월말마다 특징 15개(나스닥 낙폭 4종·수익 4종·변동성 2종·고점 이후 일수·S&P/금/국채 6개월·단기금리·
     기간 프리미엄)로 「앞 63일 나스닥 2배 수익이 −15% 이하」 확률을 예측한다. 첫 학습 10년(1972-02~1981-12), 매년 1월 지난 12월까지로 재학습(확장 창),
     학습에 쓴 표본의 기저율보다 확률이 높으면 그 달은 방어(40/40/20), 아니면 나스닥 2배. L2 정규화(λ=1) · 특징은 학습 창 평균·표준편차로 표준화 · 미래 정보 0.
  M2 M1 의 문턱을 기저율 ×2(더 신중) 로.
  M3 「규칙 재발견」: 매년 1월, 학습 창 안에서 특징 15개 × 백분위 문턱 19개 × 방향 2 = 570개 「한 조건 규칙」(f ≤ thr 이면 방어)을 전부 돌려
     학습 창 Calmar 최고를 고르고 다음 1년에 적용한다. **기계가 무엇을 고르는지**가 결과다 — 낙폭 계열을 −10~−25% 문턱으로 고른다면 규칙을
     재발견한 것이고, 매년 다른 것을 고른다면 그 자유는 잡음이다.
평가: OOS 1982-01~2026-08(44.6년) vs 같은 창 B · 월 1회 결정(그 달 유지) · 편도 0.1% · 관문 ① Calmar +10.2% ② 20년창 p05 ≥ B ③ 4블록 3+.

★ 사전 등록 예측:
  P1 M1·M2 는 B 의 Calmar 0.5~0.9× — §5-6 「선행 예측형 경보 없음」이 특징 대부분에 해당하고, 월 단위 결정은 V 자 초입을 늦게 잡는다.
  P2 M3 는 연도의 60% 이상에서 낙폭 계열(dd252·dd126·dd63·고점 이후 일수)을 고르고, 고른 문턱의 중앙값은 −10~−25% 안 — 규칙 재발견.
  P3 M1~M3 어느 것도 ①②③ 동시 통과 없음.
  P4 학습 정책의 전환 횟수는 B 의 2~4배(월 단위 확률 신호가 흔들린다).
  「틀리면 무엇이 참인가」: M1/M2 가 ①②③ 을 넘으면 「선행 신호가 있다」가 되어 §5-6 을 다시 써야 한다(그림자 후보 → 소유자). M3 가 낙폭 계열을
  안 고르면 「−16 낙폭이 표본 안 최적」이라는 §5-20 과 충돌 — 그 경우도 그대로 적는다.

실행: python research/ml_policy.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import liquid_design as LD                               # noqa: E402
import eng_common as EC                                  # noqa: E402

IDX, R, col, MIX = LD.IDX, LD.R, LD.col, LD.MIX
N = len(IDX)
L = '=' * 100
PX = pd.Series(LD.G.D['px'], index=IDX).astype(float)
QLDR = np.nan_to_num(np.asarray(LD.G.D['qldr'], float))
RQ = PX.pct_change().fillna(0.0)


def roll_ret(r, w):
    return (pd.Series(np.nan_to_num(r), index=IDX).add(1).cumprod()).pct_change(w).values


def dd(w):
    c = PX; return (c / c.rolling(w, min_periods=w).max() - 1).values


hi252 = PX.rolling(252, min_periods=252).max()
days = np.zeros(N); c = 0
for t in range(N):
    c = 0 if PX.iloc[t] >= hi252.iloc[t] else c + 1
    days[t] = c
tnx = pd.read_csv('data/hist/yahoo_TNX.csv', parse_dates=['Date']).set_index('Date')['Close'].reindex(IDX, method='ffill').values / 100
tb = pd.read_csv('data/hist/fred_DTB3.csv'); tb.columns = ['d', 'r']; tb['d'] = pd.to_datetime(tb['d'])
tb3 = pd.to_numeric(tb.set_index('d')['r'], errors='coerce').reindex(IDX, method='ffill').values / 100
FEAT = {
    'dd252': dd(252), 'dd126': dd(126), 'dd63': dd(63), 'dd21': dd(21),
    'ret21': roll_ret(RQ.values, 21), 'ret63': roll_ret(RQ.values, 63), 'ret126': roll_ret(RQ.values, 126), 'ret252': roll_ret(RQ.values, 252),
    'vol60': RQ.rolling(60).std().values * np.sqrt(252), 'volratio': (RQ.rolling(20).std() / RQ.rolling(120).std()).values,
    'days_hi': days / 252.0,
    'spx126': roll_ret(R[:, col['SPX']], 126), 'gold126': roll_ret(R[:, col['GOLD']], 126), 'ust10_126': roll_ret(R[:, col['UST10c']], 126),
    'tbill': tb3, 'term': tnx - tb3,
}
FN = list(FEAT)
X = np.column_stack([FEAT[k] for k in FN])
lev = np.cumprod(1 + QLDR)
fwd63 = np.full(N, np.nan); fwd63[:-63] = lev[63:] / lev[:-63] - 1
Y = (fwd63 <= -0.15).astype(float)
ME = np.where(LD.MS)[0]                                   # 월초 인덱스 → 결정은 전월 말(ME-1)에
DEC = ME[ME > 0] - 1                                      # 결정일(월말)
DEC = DEC[(DEC >= 252) & (DEC < N - 1)]
YR = IDX.year.values


def logistic_fit(Xa, ya, lam=1.0, iters=50):
    mu, sd = Xa.mean(0), Xa.std(0) + 1e-9
    Z = np.column_stack([np.ones(len(Xa)), (Xa - mu) / sd])
    w = np.zeros(Z.shape[1])
    for _ in range(iters):                              # 뉴턴(IRLS) + L2
        p = 1 / (1 + np.exp(-Z @ w)); Wd = p * (1 - p)
        g = Z.T @ (p - ya) + lam * np.r_[0, w[1:]]
        Hm = (Z * Wd[:, None]).T @ Z + lam * np.diag(np.r_[0, np.ones(Z.shape[1] - 1)])
        step = np.linalg.solve(Hm, g); w -= step
        if np.max(np.abs(step)) < 1e-8:
            break
    return w, mu, sd


def logistic_p(w, mu, sd, Xb):
    Z = np.column_stack([np.ones(len(Xb)), (Xb - mu) / sd]); return 1 / (1 + np.exp(-Z @ w))


GOV = np.searchsorted(DEC, np.arange(N), side='left') - 1     # 날 t 를 지배하는 결정(직전 결정일)의 DEC 색인, 없으면 −1


def weights_from(dec_vec):
    """dec_vec: DEC 길이의 방어 여부(bool) → 일별 w (결정일 다음 날부터 그 달 유지). 벡터화."""
    w = np.ones(N)
    m = GOV >= 0
    w[m] = np.where(dec_vec[GOV[m]], 0.0, 1.0)
    return w


def policy_curve(defense_month, lo):
    dec_vec = np.zeros(len(DEC), bool)
    pos = {int(t): i for i, t in enumerate(DEC)}
    for t, v in defense_month.items():
        if int(t) in pos:
            dec_vec[pos[int(t)]] = bool(v)
    w = weights_from(dec_vec)
    return np.asarray(EC.sim2(w[lo:], QLDR[lo:], MIX[lo:]), float), w


def month_returns_for(sig_defense, lo_i, hi_i):
    """학습 창 안 「이 달 방어 여부」 → 학습 창 Calmar (비용 포함). 벡터화."""
    dec_vec = np.zeros(len(DEC), bool)
    pos = {int(t): i for i, t in enumerate(DEC)}
    for t, v in sig_defense.items():
        if int(t) in pos:
            dec_vec[pos[int(t)]] = bool(v)
    w = weights_from(dec_vec)
    c = np.asarray(EC.sim2(w[lo_i:hi_i], QLDR[lo_i:hi_i], MIX[lo_i:hi_i]), float)
    return EC.fullmet(c, idx=IDX[lo_i:hi_i])['calmar']


def main():
    print(L); print('기계가 정책을 배우면 — 걸어가며 재학습(M1·M2) + 규칙 재발견(M3) · OOS 1982~ vs B (규칙 무변경 · 모의 실험)'); print(L)
    lo = int(np.argmax(YR >= 1982))
    ix = IDX[lo:]
    B = np.asarray(EC.sim2(np.asarray(EC.rule_dd(PX, -0.16, -0.16), float)[lo:], QLDR[lo:], MIX[lo:]), float)
    mB = EC.fullmet(B, idx=ix); mB['p05'] = EC.p05_20y(B)
    bB = [EC.fullmet(B[a:b] / B[a], idx=ix[a:b])['calmar'] for a, b in zip(np.linspace(0, len(B), 5).astype(int)[:-1], np.linspace(0, len(B), 5).astype(int)[1:])]
    wB = np.asarray(EC.rule_dd(PX, -0.16, -0.16), float)

    dec_m1, dec_m2, dec_m3, picks = {}, {}, {}, []
    valid = ~np.isnan(X).any(axis=1) & ~np.isnan(Y)
    years = sorted(set(YR[DEC]))
    for yr in years:
        if yr < 1982:
            continue
        tr = DEC[(YR[DEC] < yr) & valid[DEC] & (IDX[DEC] <= pd.Timestamp(f'{yr-1}-12-31'))]
        tr = tr[fwd63[tr] == fwd63[tr]]                  # 목표가 있는 달만 (마지막 63일 제외)
        te = DEC[YR[DEC] == yr]
        if len(tr) < 100:
            continue
        w, mu, sd = logistic_fit(X[tr], Y[tr])
        base = Y[tr].mean()
        p = logistic_p(w, mu, sd, np.nan_to_num(X[te], nan=0.0))
        for t, pi in zip(te, p):
            dec_m1[t] = pi >= base; dec_m2[t] = pi >= 2 * base
        # M3 규칙 재발견 — 학습 창(월 결정)에서 570개 한 조건 규칙 중 Calmar 최고
        best = (-9, None)
        lo_i, hi_i = int(tr[0]), int(tr[-1]) + 1
        for j, f in enumerate(FN):
            xs = X[tr, j]
            for q in np.linspace(5, 95, 19):
                thr = np.nanpercentile(xs, q)
                for sign in (1, -1):
                    sig = {int(t): (sign * X[t, j] <= sign * thr) for t in tr}
                    cal = month_returns_for(sig, lo_i, hi_i)
                    if cal > best[0]:
                        best = (cal, (f, thr, sign))
        f, thr, sign = best[1]
        picks.append((yr, f, thr, sign, best[0]))
        for t in te:
            dec_m3[t] = (sign * X[t, FN.index(f)] <= sign * thr) if not np.isnan(X[t, FN.index(f)]) else False

    rows = []
    for nm, dec in (('M1 학습 정책 (문턱 = 기저율)', dec_m1), ('M2 학습 정책 (문턱 = 기저율×2)', dec_m2), ('M3 규칙 재발견 (매년 최고 한 조건)', dec_m3)):
        c, w = policy_curve(dec, lo)
        m = EC.fullmet(c, idx=ix); m['p05'] = EC.p05_20y(c)
        e = np.linspace(0, len(c), 5).astype(int)
        bl = [EC.fullmet(c[a:b] / c[a], idx=ix[a:b])['calmar'] for a, b in zip(e[:-1], e[1:])]
        wins = sum(1 for x, y in zip(bl, bB) if x > y)
        sw = int(np.sum(np.abs(np.diff(w[lo:])) > 0)); swB = int(np.sum(np.abs(np.diff(wB[lo:])) > 0))
        agree = float(np.mean(w[lo:] == wB[lo:]))
        rows.append((nm, m, wins, sw, swB, agree))
    print(f"\n  OOS {ix[0].date()} ~ {ix[-1].date()} ({(ix[-1]-ix[0]).days/365.25:.1f}년) · B: 최종 {mB['final']:,.0f} · Calmar {mB['calmar']:.3f} · 20y p05 {mB['p05']:.1f}배 · 전환 {int(np.sum(np.abs(np.diff(wB[lo:]))>0))}")
    print(f"  {'정책':<38}{'최종':>10}{'vsB':>7}{'CAGR':>8}{'MDD':>8}{'Calmar':>8}{'ΔCal':>8}{'20y p05':>9}{'블록':>6}{'전환':>6}{'B와 일치일':>10}  관문")
    verdict = {}
    for nm, m, wins, sw, swB, agree in rows:
        d1 = m['calmar'] / mB['calmar'] - 1; g = (d1 > 0.102, m['p05'] >= mB['p05'], wins >= 3)
        verdict[nm] = (m, g, sw, agree)
        tag = '★①②③' if all(g) else ('①' if g[0] else '-') + ('②' if g[1] else '-') + ('③' if g[2] else '-')
        print(f"  {nm:<38}{m['final']:>10,.0f}{m['final']/mB['final']:>6.2f}x{m['cagr']:>7.2f}%{m['mdd']:>7.1f}%{m['calmar']:>8.3f}{d1*100:>+7.1f}%"
              f"{m['p05']:>8.1f}배{wins:>4d}/4{sw:>6d}{agree*100:>9.0f}%  {tag}")
    print('\n  M3 가 매년 고른 한 조건 규칙 (학습 창 Calmar 최고):')
    fam = 0
    for yr, f, thr, sign, cal in picks:
        isdd = f in ('dd252', 'dd126', 'dd63', 'dd21', 'days_hi')
        fam += isdd
        print(f"    {yr}: {'방어 if' } {f} {'≤' if sign == 1 else '≥'} {thr:+.3f}   (학습 Calmar {cal:.3f}){'  ← 낙폭 계열' if isdd else ''}")
    dd_thr = [thr for _, f, thr, s, _ in picks if f == 'dd252']
    print(f"  → 낙폭 계열 선택 {fam}/{len(picks)}년 ({fam/len(picks)*100:.0f}%) · dd252 를 고른 해의 문턱 중앙값 {np.median(dd_thr)*100 if dd_thr else float('nan'):+.1f}%")

    print('\n' + L); print('사전 등록 대조'); print(L)
    m1 = verdict['M1 학습 정책 (문턱 = 기저율)']; m2 = verdict['M2 학습 정책 (문턱 = 기저율×2)']; m3 = verdict['M3 규칙 재발견 (매년 최고 한 조건)']
    r1, r2 = m1[0]['calmar'] / mB['calmar'], m2[0]['calmar'] / mB['calmar']
    print(f"  P1 (M1·M2 Calmar 0.5~0.9×B): {r1:.2f}× · {r2:.2f}× → {'맞음' if all(0.5 <= x <= 0.9 for x in (r1, r2)) else '틀림'}")
    print(f"  P2 (M3 낙폭 계열 60%+ · dd252 문턱 −10~−25%): {fam/len(picks)*100:.0f}% · 중앙 {np.median(dd_thr)*100 if dd_thr else float('nan'):+.1f}% → "
          f"{'맞음' if (fam/len(picks) >= 0.6 and dd_thr and -0.25 <= np.median(dd_thr) <= -0.10) else '틀림'}")
    passed = [k for k, v in verdict.items() if all(v[1])]
    print(f"  P3 (①②③ 동시 통과 없음): {'맞음' if not passed else '틀림 — ' + str(passed)}")
    swB = int(np.sum(np.abs(np.diff(wB[lo:])) > 0))
    print(f"  P4 (학습 정책 전환 2~4×B): M1 {m1[2]/swB:.1f}× · M2 {m2[2]/swB:.1f}× · M3 {m3[2]/swB:.1f}× → {'맞음' if all(2 <= v[2]/swB <= 4 for v in (m1, m2)) else '틀림'}")
    print('\n이 측정이 낳은 다음 질문 (§-1 절대멈춤 6):')
    print('  · M3 가 낙폭 계열을 고른다면 「기계도 같은 곳에 닿는다」 — 남는 질문은 문턱의 자유도(연도별 흔들림)가 성과를 얼마나 깎았는가 = 적응형의 비용(§5-13 정정3 과 같은 질문).')
    print('  · M1 이 B 와 일치하지 않은 날들에서 누가 옳았나(사건 단위) — 일치일 비율이 낮은데 성과가 비슷하면 다른 길로 같은 곳에 간 것이고, 그건 앙상블 후보다(단, 시도 수).')


if __name__ == '__main__':
    main()
