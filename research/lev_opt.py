# -*- coding: utf-8 -*-
"""
[번외 심층, 소유자 요청 2026-08-31] 미국 직투 시 최적 레버리지 배율 —
QQQ(1x)+TQQQ(3x) 혼합으로 k 를 연속 조절할 수 있을 때, B 규칙(동결) 아래
어느 k 가 좋은가.

선행 기록: v22 축1 「리스크온 배수」 — 세전 x3=x2 의 2.51배·Calmar 동반 상승,
그러나 ①계좌(ISA 불가→22% 양도세) ②MDD −76% ③1987 소각선 ④2000-09 역전
⑤지연 민감으로 「조건부 비채택」. 이번 재검토의 차이: 미국 진출이면 어차피
해외계좌 → ISA vs 해외 비교가 아니라 **해외계좌 안에서 k 만 고르는 문제**가 된다
(v22 표: 같은 해외계좌면 세후도 x3>x2.5>x2 — 계좌 함정 소멸).

방법: 공격다리 = axis_lib.lev_r(D,k) (k>2 는 비용 과대의 보수적 모형 — v22 규약
그대로), 방어 = mix 40/40/20 · 규칙 = 동결 wB (신호는 QQQ 라 k 와 무관).
격자 k=1.00~3.00 (0.25 步). 퇴화 검산: k=2 가 재현 기준선과 오차 0 이어야 함
(주의 — 기준선 qldr 은 실물 QLD 포함이라 lev_r(D,2) 합성과 다름: 두 줄 다 표기).
평가: 전창 + 20년 p05 + 지평 승률(vs k=2) + 시대 분해 + lag2 + 비용 0.2%
+ 혼합 구현(일일 vs 월 리밸런스) 차이.
판정 아님 · 전략 무변경 · 채택 없음. 실행: python research/lev_opt.py
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
from axis_lib import lev_r                              # noqa: E402

G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
tb = G.tb
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
wB = np.asarray(G.wB, float)
KS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0]


def bcurve(k, cost=0.001, lag=1):
    """lag = 신호일→반영일 총 지연 (sim2 내장 1일 포함). lag=2 면 사전 1일 추가."""
    r_e = np.asarray(lev_r(G.D, k), float)
    pre = lag - 1
    if pre == 0:
        return EC.sim2(wB, r_e, MIXR, cost=cost)
    w2 = np.empty(n)
    w2[:pre] = wB[0]
    w2[pre:] = wB[:-pre]
    return EC.sim2(w2, r_e, MIXR, cost=cost)


def worst_days(k):
    r_e = np.asarray(lev_r(G.D, k), float)
    w1 = float(np.min(r_e))
    r5 = pd.Series(r_e).rolling(5).apply(lambda x: np.prod(1 + x) - 1).min()
    return w1, float(r5)


def p05(a, w=5040):
    return float(np.quantile(a[w:] / a[:-w], 0.05))


def main():
    # 퇴화 대조: 기준선(실물 QLD 포함 체인) vs lev_r(D,2) 합성 — 재료 차이 명시
    ref = EC.sim2(wB, np.nan_to_num(np.asarray(G.D['qldr'], float)), MIXR)
    b2 = bcurve(2.0)
    print(f'\n[대조] B(실물 체인) 최종 {ref[-1]:.0f} vs B(lev_r 합성 k=2) {b2[-1]:.0f} — '
          f'비율 {b2[-1]/ref[-1]:.3f} (합성 규약이 실물보다 {"불리" if b2[-1]<ref[-1] else "유리"}. '
          f'이하 격자는 전부 같은 합성 잣대 — k 간 비교만 유효)')

    print(f'\n[1] k 격자 — 전창 54년 · 방어 mix · 동결 규칙 · 편도 0.1% (합성 잣대)')
    print(f"{'k':>5} {'최종배수':>12} {'CAGR':>6} {'MDD':>7} {'Calmar':>7} {'p05(20y)':>8} "
          f"{'최악1일':>7} {'최악5일':>7}")
    curves = {}
    for k in KS:
        a = bcurve(k)
        curves[k] = a
        m = EC.fullmet(a, tb, idx)
        w1, w5 = worst_days(k)
        print(f'{k:>5.2f} {m["final"]:>12.1f} {m["cagr"]:>6.2f} {m["mdd"]:>7.1f} '
              f'{m["calmar"]:>7.3f} {p05(a):>8.1f} {w1:>7.1%} {w5:>7.1%}')

    print(f'\n[2] k=2 대비 상대 — 지평 승률·최악 상대배수 (창 전수)')
    print(f"{'k':>5} {'5y승률':>7} {'5y최악상대':>9} {'10y승률':>8} {'10y최악':>8} {'20y승률':>8} {'20y최악':>8}")
    a2_ = curves[2.0]
    for k in KS:
        if k == 2.0:
            continue
        a = curves[k]
        line = f'{k:>5.2f}'
        for w in (1260, 2520, 5040):
            rel = (a[w:] / a[:-w]) / (a2_[w:] / a2_[:-w])
            line += f' {np.mean(rel > 1):>7.1%} {rel.min():>8.2f}'
        print(line)

    print(f'\n[3] 시대 분해 — 최종배수 (k=2 대비 비율)')
    eras = [('1972~1999', '1972-01-01', '2000-01-01'), ('2000~2009', '2000-01-01', '2010-01-01'),
            ('2010~2026', '2010-01-01', '2027-01-01')]
    print(f"{'k':>5}" + ''.join(f"{e[0]:>14}" for e in eras))
    for k in (1.5, 2.0, 2.5, 3.0):
        a = curves[k]
        line = f'{k:>5.2f}'
        for _, s, e in eras:
            i0, i1 = pd.Series(idx).searchsorted([pd.Timestamp(s), pd.Timestamp(e)])
            i1 = min(i1, n - 1)
            v = a[i1] / a[i0]
            v2 = a2_[i1] / a2_[i0]
            line += f'  {v:>7.1f} ({v/v2:>4.2f})'
        print(line)

    print(f'\n[4] 스트레스 — 편도 0.2% · 체결 +1일 지연')
    print(f"{'k':>5} {'0.2%최종':>10} {'0.2%Calmar':>10} {'지연최종':>10} {'지연/기본':>9}")
    for k in (2.0, 2.25, 2.5, 3.0):
        a02 = bcurve(k, cost=0.002)
        alag = bcurve(k, lag=2)
        m02 = EC.fullmet(a02, tb, idx)
        print(f'{k:>5.2f} {a02[-1]:>10.0f} {m02["calmar"]:>10.3f} {alag[-1]:>10.0f} '
              f'{alag[-1]/curves[k][-1]:>9.2f}')

    print(f'\n[5] 혼합 구현 — k=2.5 를 QQQ+TQQQ 로 (w_TQQQ=(k−1)/2=0.75)')
    r1x = np.asarray(lev_r(G.D, 1.0), float)
    r3x = np.asarray(lev_r(G.D, 3.0), float)
    w_t = 0.75
    daily = np.cumprod(1 + w_t * r3x + (1 - w_t) * r1x)
    per = pd.Series(idx).dt.to_period('M').values
    mst = np.zeros(n, bool)
    mst[1:] = per[1:] != per[:-1]
    v = 1.0
    hold_t = w_t
    vals = np.empty(n)
    sh3 = w_t
    for i in range(n):
        if mst[i]:
            sh3 = w_t
        g3 = sh3 * (1 + r3x[i])
        g1 = (1 - sh3 if mst[i] else (1 - hold_t)) * (1 + r1x[i])
        tot = g3 + g1
        v *= tot / (sh3 + (1 - sh3))
        sh3 = g3 / tot
        hold_t = sh3
        vals[i] = v
    ref25 = np.cumprod(1 + 2.5 * np.nan_to_num(pd.Series(G.D['px']).pct_change().values)
                       - 1.5 * G.D['c_daily'])
    print(f'  일일 리밸런스 혼합 최종 {daily[-1]:.0f} (상수 k=2.5 합성 {ref25[-1]:.0f} — 동치 확인용)')
    print(f'  월 1회 리밸런스 혼합 최종 {v:.0f} — 일일 대비 {v/daily[-1]:.2f}배 '
          f'(사이 구간 배율 표류 = 모멘텀 편향. 월간이면 관리 부담 12회/yr)')

    print('\n[6] 대응표 — 목표 k → TQQQ 비중 w=(k−1)/2 (잔여 QQQ)')
    print('  ' + ' · '.join(f'k={k:.2f}→{(k-1)/2:.0%}' for k in (2.0, 2.25, 2.5, 2.75, 3.0)))
    print('\n⚠ 판정 아님 — v22 조건표(기간>26y·MDD −76% 감내·2000-09형 감내·소각선)와'
          '\n  함께 읽을 것. 세후는 v22 §2.5 (해외계좌 안에서는 k↑ 순서 유지).')


if __name__ == '__main__':
    main()
