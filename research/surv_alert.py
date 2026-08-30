# -*- coding: utf-8 -*-
"""
[생존성 연구 ②, 소유자 지시 2026-08-31] 선행 경보 검증 — 엄격 규율.

규율 (지시문 §9·§13): 임계값 사후 최적화 금지 · 상관 하나로 선행 주장 금지 ·
반쪽 부호 일관 + 독립 사건 반복이 있어야 「약한 증거」 이상. 판정 4단계:
유용 / 약한 증거 / 무의미 / 과적합 의심.

방법:
  후행 지표(시점 t 까지만): 지수 3/5/10년 CAGR · 3년 변동성 · 3년 드래그 ·
    5년 방어비중 · 5년 전환수 · B 5년 CAGR · B 5년 Calmar
  전방 결과(t 이후 5년): B CAGR · B 초과(log B−log 맨몸, 연율) · B Calmar
  검정: Spearman 전체+전/후반 부호 일관 · 최악 10% 전방창 사건화(504일 격리)
    → 사건 시작 시점의 지표 백분위 표.
  + 재진입 효율 시계열 (재진입 후 60/120/252일 B 수익 — 최근이 나빠졌는가)
  + Level 참조 밴드: 느린 변수의 역사 min/p05/p10 (임계 최적화가 아니라 분포 위치).
전략 무변경·판정 아님. 실행: python research/surv_alert.py
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

import eng_common as EC                                 # noqa: E402

G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
r1 = np.nan_to_num(pd.Series(G.D['px']).pct_change().values)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
aB = EC.sim2(np.asarray(G.wB, float), QLDR, MIXR)
a2 = np.cumprod(1 + QLDR)
wB = np.asarray(G.wB, float)

L1 = np.concatenate(([0], np.cumsum(np.log1p(r1))))
L2 = np.concatenate(([0], np.cumsum(np.log1p(np.diff(a2, prepend=1.0) / np.concatenate(([1.0], a2[:-1]))))))
LB = np.concatenate(([0], np.cumsum(np.log1p(np.diff(aB, prepend=1.0) / np.concatenate(([1.0], aB[:-1]))))))
S1 = np.concatenate(([0], np.cumsum(r1)))
Q1 = np.concatenate(([0], np.cumsum(r1 ** 2)))
DEF = np.concatenate(([0], np.cumsum(1 - wB)))
SW = np.concatenate(([0], np.cumsum(np.abs(np.diff(wB, prepend=wB[0])))))


def cagr(L, i, w):
    return np.expm1((L[i + 1] - L[i + 1 - w]) * 252.0 / w)


def vol(i, w):
    m = (S1[i + 1] - S1[i + 1 - w]) / w
    v = (Q1[i + 1] - Q1[i + 1 - w]) / w - m * m
    return np.sqrt(max(v, 0)) * np.sqrt(252)


def wmdd(a, lo, hi):
    seg = a[lo:hi]
    peak = np.maximum.accumulate(seg)
    return abs(float(np.min(seg / peak - 1)))


def spearman(x, y):
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    W2 = 2520  # 후행 최대 10년 필요
    F = 1260   # 전방 5년
    ts = list(range(W2 - 1, n - F, 5))
    rows = []
    for i in ts:
        ind = dict(
            t=i,
            idx3y=cagr(L1, i, 756), idx5y=cagr(L1, i, 1260), idx10y=cagr(L1, i, 2520),
            vol3y=vol(i, 756), drag3y=2 * cagr(L1, i, 756) - cagr(L2, i, 756),
            def5y=(DEF[i + 1] - DEF[i + 1 - 1260]) / 1260,
            sw5y=SW[i + 1] - SW[i + 1 - 1260],
            b5y=cagr(LB, i, 1260),
            bcal5y=cagr(LB, i, 1260) / max(wmdd(aB, i + 1 - 1260, i + 1), 1e-9),
        )
        j = i + F
        ind['fwdB'] = cagr(LB, j, F)
        ind['fwdEx'] = ((LB[j + 1] - LB[i + 1]) - (L2[j + 1] - L2[i + 1])) * 252.0 / F
        ind['fwdCal'] = ind['fwdB'] / max(wmdd(aB, i + 1, j + 1), 1e-9)
        rows.append(ind)
    df = pd.DataFrame(rows)
    inds = ['idx3y', 'idx5y', 'idx10y', 'vol3y', 'drag3y', 'def5y', 'sw5y', 'b5y', 'bcal5y']
    outs = ['fwdB', 'fwdEx', 'fwdCal']
    half = len(df) // 2

    print(f'\n[A] 후행 지표 → 전방 5년 결과 — Spearman (전체 | 전반 | 후반) · 창 {len(df)}개(보폭 5일)')
    print(f"  {'지표':<8}" + ''.join(f"{o:>26}" for o in outs))
    verdicts = {}
    for k in inds:
        line = f'  {k:<8}'
        vsum = []
        for o in outs:
            r_all = spearman(df[k], df[o])
            r1_ = spearman(df[k][:half], df[o][:half])
            r2_ = spearman(df[k][half:], df[o][half:])
            cons = (np.sign(r1_) == np.sign(r2_)) and abs(r_all) >= 0.25
            line += f'  {r_all:+.2f} ({r1_:+.2f}|{r2_:+.2f}){"*" if cons else " "}'
            vsum.append((r_all, cons))
        print(line)
        verdicts[k] = vsum
    print('  (* = |ρ|≥0.25 이고 전·후반 부호 일치 — 겹침 창이라 유효표본 ~9개, 과신 금지)')

    # ---- B. 사건 검증: 전방 5년 B CAGR 최악 10% 창의 시작점 ----
    thr = np.quantile(df.fwdB, 0.10)
    bad = df[df.fwdB <= thr].copy()
    eps = []
    last = -10**9
    for _, r_ in bad.iterrows():
        if r_.t - last > 504:
            eps.append(int(r_.t))
        last = r_.t
    print(f'\n[B] 전방 5년 B CAGR 최악 10% (≤{thr*100:.1f}%) — 독립 사건 {len(eps)}개, 시작 시점의 지표 백분위')
    print(f"  {'시작':>12}" + ''.join(f"{k:>8}" for k in inds))
    for t0 in eps:
        r_ = df[df.t == t0].iloc[0]
        line = f'  {str(idx[t0].date()):>12}'
        for k in inds:
            line += f"{float(np.mean(df[k] <= r_[k])):>8.0%}"
        print(line)

    # ---- C. 재진입 효율 시계열 ----
    re_i = np.where(np.diff(wB) > 0)[0] + 1
    print(f'\n[C] 재진입 후 60/120/252일 B 수익 — 재진입 {len(re_i)}회 (시대별 평균)')
    eras = [(1972, 1990), (1990, 2000), (2000, 2010), (2010, 2020), (2020, 2027)]
    yr = pd.Series(idx).dt.year.values
    for a_, b_ in eras:
        sel = [i for i in re_i if a_ <= yr[i] < b_ and i + 252 < n]
        if not sel:
            continue
        m60 = np.mean([aB[i + 60] / aB[i] - 1 for i in sel])
        m120 = np.mean([aB[i + 120] / aB[i] - 1 for i in sel])
        m252 = np.mean([aB[i + 252] / aB[i] - 1 for i in sel])
        print(f'  {a_}~{b_-1}: n={len(sel):>2} · 60일 {m60:+.1%} · 120일 {m120:+.1%} · 252일 {m252:+.1%}')

    # ---- D. Level 참조 밴드 (느린 변수 — 분포 위치, 최적화 아님) ----
    print('\n[D] 감시 밴드 — 역사 분포 위치 (Level 규약 후보: p10 아래=주의 · 역사 최저 아래=역사 범위 밖)')
    for k, w, lab in (('idx10y', 2520, '지수 10년 CAGR'), ('idx5y', 1260, '지수 5년 CAGR'),
                      ('vol3y', 756, '지수 3년 변동성(상단)'), ('drag3y', 756, '2배 드래그 3년(상단)')):
        s = df[k]
        cur = dict(idx10y=cagr(L1, n - 1, 2520), idx5y=cagr(L1, n - 1, 1260),
                   vol3y=vol(n - 1, 756), drag3y=2 * cagr(L1, n - 1, 756) - cagr(L2, n - 1, 756))[k]
        if '상단' in lab:
            print(f'  {lab:<18} p90 {np.quantile(s,0.90)*100:5.1f}% · 역사 최고 {s.max()*100:5.1f}% · 현재 {cur*100:5.1f}%')
        else:
            print(f'  {lab:<18} p10 {np.quantile(s,0.10)*100:5.1f}% · 역사 최저 {s.min()*100:5.1f}% · 현재 {cur*100:5.1f}%')


if __name__ == '__main__':
    main()
