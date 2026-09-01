# -*- coding: utf-8 -*-
"""
[공유용 변형 — WFA/OOS + PBO(+DSR), 2026-09-01] share_variant_threshold_scan.py 후속.
소유자 요청: "OOS랑 PBO까지 해봐." 이 저장소의 기존 방법론을 그대로 재사용한다
(재발명 금지 — CSCV 는 research/audit_pbo.py, DSR 은 research/dsr_b.py 와 동일 공식).
판정 아님 · 전략 B 무변경. 실제 숫자(문턱 등)는 이 파일·터미널에만 남고
공유 아티팩트에는 올리지 않는다(소유자의 비공개 요청 유지).

시행 공간: 비율 9(S9Q1~S1Q9) × 문턱 10(share_variant_threshold_scan.py 와 동일 격자)
  = 90개 후보, 방어는 이미 별도로 재확인한 국채70/금30 고정.

[A] WFA/OOS: Train 5년(1260거래일)/Test 1년(252거래일) 롤링, 매 스텝 IS(직전 5년)에서
    Sharpe 최고 후보를 뽑아 OOS(다음 1년)에 적용, OOS 구간만 이어붙여 실제로
    "그때그때 다시 골랐다면" 성과를 낸다. 비교군: 재선택 없이 처음부터 끝까지
    고정 배합 하나로 버텼을 때(같은 OOS 구간만 잘라서 공정 비교).
[B] PBO: CSCV(Bailey–López de Prado 2014), S=8 블록 C(8,4)=70분할, audit_pbo.py 와
    동일 코드.
[C] 보너스 — DSR: dsr_b.py 와 동일 공식으로, 90개 격자를 다 뒤진 뒤에도 최고 후보의
    Sharpe 가 통계적으로 실재하는지("우연에 불과하지 않은지") 본다.

실행: python research/share_variant_oos_pbo.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
import sys
from itertools import combinations
from math import erf, sqrt, exp
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_defensive as DF                                # noqa: E402
import hist_defasset as DA                                 # noqa: E402
import eng_common as EC                                     # noqa: E402

D = dict(DF.build('chain'))
idx = D['idx']
px = pd.Series(D['px'], index=idx)
n = len(idx)

r_qqq1x = np.nan_to_num(px.pct_change().values)
r_div = np.asarray(D['schdr'], float)
r_ust5 = np.nan_to_num(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE))
r_gold = np.nan_to_num(DA.gold_r(idx))
r_def = DA.mix_monthly_parts(idx, dict(ust5=0.70, gold=0.30), dict(ust5=r_ust5, gold=r_gold))

RATIOS = [(9, 1), (8, 2), (7, 3), (6, 4), (5, 5), (4, 6), (3, 7), (2, 8), (1, 9)]
TH_GRID = list(range(-8, -27, -2))
CHOSEN = ('S6Q4', -16)   # 앞선 격자+고원 검증에서 고른 안 — 이 파일·터미널에서만 노출


def rets(a):
    return np.diff(a, prepend=1.0) / np.concatenate(([1.0], a[:-1]))


def build_universe():
    names, R = [], []
    for s, q in RATIOS:
        r_atk = DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10), dict(div=r_div, qqq=r_qqq1x))
        for th in TH_GRID:
            w = EC.rule_dd(px, th / 100, th / 100)
            c = EC.sim2(w, r_atk, r_def)
            names.append((f'S{s}Q{q}', th))
            R.append(rets(c))
    return names, np.vstack(R)


def sharpe(r):
    return float(np.mean(r) / np.std(r, ddof=1)) if np.std(r, ddof=1) > 0 else -np.inf


def metric_matrix(Rsub, kind):
    if kind == 'sharpe':
        sd = Rsub.std(axis=1, ddof=1)
        return np.where(sd > 0, Rsub.mean(axis=1) / np.where(sd > 0, sd, 1), -np.inf)
    a = np.cumprod(1 + Rsub, axis=1)
    peak = np.maximum.accumulate(a, axis=1)
    mdd = np.abs(np.min(a / peak - 1, axis=1))
    cagr = a[:, -1] ** (252.0 / Rsub.shape[1]) - 1
    return cagr / np.maximum(mdd, 1e-9)


# ------------------------------------------------------------- [A] WFA/OOS
def walk_forward(names, R, train=1260, test=252):
    chosen_idx = [i for i, nm in enumerate(names) if nm == CHOSEN]
    assert len(chosen_idx) == 1
    fixed = chosen_idx[0]

    oos_pick, oos_fixed, picks_log = [], [], []
    i = 0
    while i + train + test <= n:
        Rtr = R[:, i:i + train]
        Rte = R[:, i + train:i + train + test]
        m = metric_matrix(Rtr, 'sharpe')
        best = int(np.argmax(m))
        oos_pick.append(Rte[best])
        oos_fixed.append(Rte[fixed])
        picks_log.append(names[best])
        i += test

    walk_r = np.concatenate(oos_pick)
    fixed_r = np.concatenate(oos_fixed)

    def summarize(r):
        c = np.cumprod(1 + r)
        yrs = len(r) / 252.0
        cagr = c[-1] ** (1 / yrs) - 1
        mdd = float(np.min(c / np.maximum.accumulate(c) - 1))
        return dict(final=float(c[-1]), cagr=cagr * 100, mdd=mdd * 100,
                    calmar=cagr / abs(mdd), sharpe=sharpe(r) * np.sqrt(252))

    same_ratio = sum(1 for p in picks_log if p[0] == CHOSEN[0])
    exact_same = sum(1 for p in picks_log if p == CHOSEN)
    return summarize(walk_r), summarize(fixed_r), picks_log, same_ratio, exact_same, len(picks_log)


# ------------------------------------------------------------- [B] PBO(CSCV)
def cscv(R, names, kind):
    S = 8
    bnd = np.linspace(0, R.shape[1], S + 1, dtype=int)
    blocks = [np.arange(bnd[i], bnd[i + 1]) for i in range(S)]
    lam, below, picks = [], 0, {}
    for isb in combinations(range(S), S // 2):
        oob = [b for b in range(S) if b not in isb]
        i_idx = np.concatenate([blocks[b] for b in isb])
        o_idx = np.concatenate([blocks[b] for b in oob])
        mi = metric_matrix(R[:, i_idx], kind)
        mo = metric_matrix(R[:, o_idx], kind)
        best = int(np.argmax(mi))
        picks[names[best]] = picks.get(names[best], 0) + 1
        w = (np.sum(mo < mo[best]) + 0.5 * np.sum(mo == mo[best])) / len(mo)
        w = min(max(w, 1e-6), 1 - 1e-6)
        lam.append(np.log(w / (1 - w)))
        below += int(w < 0.5)
    lam = np.asarray(lam)
    top = sorted(picks.items(), key=lambda t: -t[1])[:6]
    return below / len(lam), float(np.median(lam)), top


# ------------------------------------------------------------- [C] DSR (보너스)
EULER = 0.5772156649015329


def ncdf(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def nppf(p):
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
        q = sqrt(-2 * np.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = sqrt(-2 * np.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r_ = q * q
    return (((((a[0]*r_+a[1])*r_+a[2])*r_+a[3])*r_+a[4])*r_+a[5])*q / \
           (((((b[0]*r_+b[1])*r_+b[2])*r_+b[3])*r_+b[4])*r_+1)


def dsr(sr, sr0, r):
    T = len(r)
    g3 = float(pd.Series(r).skew())
    g4 = float(pd.Series(r).kurt()) + 3.0
    den = sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4.0 * sr * sr))
    return ncdf((sr - sr0) * sqrt(T - 1) / den), g3, g4


def main():
    EC.selfcheck()
    print(f'\n시행 공간: 비율 9 x 문턱 10 = 90칸 (방어 국채70/금30 고정) · {n}거래일\n')
    names, R = build_universe()

    print('=' * 70)
    print('[A] Walk-Forward OOS — Train 5년(1260일)/Test 1년(252일) 롤링')
    print('=' * 70)
    wf, fx, picks_log, same_ratio, exact_same, nwin = walk_forward(names, R)
    print(f'롤링 창 수: {nwin}개 (OOS 구간만 이어붙인 합성 곡선)\n')
    print(f"{'':<28}{'최종배수':>10}{'CAGR%':>8}{'MDD%':>8}{'Calmar':>8}{'연Sharpe':>9}")
    print(f"{'매 구간 IS 1등으로 재선택':<28}{wf['final']:>10.2f}{wf['cagr']:>8.2f}"
          f"{wf['mdd']:>8.2f}{wf['calmar']:>8.3f}{wf['sharpe']:>9.3f}")
    print(f"{'고정(재선택 없음, 같은 OOS창)':<28}{fx['final']:>10.2f}{fx['cagr']:>8.2f}"
          f"{fx['mdd']:>8.2f}{fx['calmar']:>8.3f}{fx['sharpe']:>9.3f}")
    print(f'\n선택 안정성: {nwin}개 창 중 같은 비율(S6Q4) 재선택 {same_ratio}회'
          f' · 완전히 같은 (비율,문턱) 재선택 {exact_same}회')
    print('직전 10개 창의 실제 선택:', picks_log[-10:])

    print('\n' + '=' * 70)
    print('[B] PBO — CSCV (Bailey-Lopez de Prado 2014, S=8, C(8,4)=70분할)')
    print('=' * 70)
    for kind in ('sharpe', 'calmar'):
        pbo, lam_med, top = cscv(R, names, kind)
        print(f'\n지표={kind}: PBO={pbo:.3f} (0.5=동전던지기) · λ중앙 {lam_med:+.2f}')
        print('  IS 1등으로 가장 자주 뽑힌 후보:', ', '.join(f'{nm}({c})' for nm, c in top))

    print('\n' + '=' * 70)
    print('[C] 보너스 — Deflated Sharpe (90칸 탐색 벌점을 최고 후보에게)')
    print('=' * 70)
    full_metric = metric_matrix(R, 'sharpe')
    best_i = int(np.argmax(full_metric))
    print(f'격자 내 Sharpe 최고: {names[best_i]} (일간 SR {full_metric[best_i]:.5f})'
          f' · CHOSEN({CHOSEN}) 순위 {int(np.where(np.argsort(-full_metric) == names.index(CHOSEN))[0][0]) + 1}/{len(names)}')
    sr_chosen = float(full_metric[names.index(CHOSEN)])
    sig = float(full_metric[np.isfinite(full_metric)].std(ddof=1))
    for NN in (90, 210, 500):
        sr0 = sig * ((1 - EULER) * nppf(1 - 1.0 / NN) + EULER * nppf(1 - 1.0 / (NN * exp(1))))
        d, g3, g4 = dsr(sr_chosen, sr0, R[names.index(CHOSEN)])
        tag = '실재' if d > 0.95 else ('경계' if d > 0.90 else '미달')
        print(f'  가정 시행수 N={NN:>4}: E[maxSR|H0]={sr0:.5f} · DSR={d:.3f}  {tag}')


if __name__ == '__main__':
    main()
