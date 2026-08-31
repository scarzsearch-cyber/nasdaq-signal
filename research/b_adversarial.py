# -*- coding: utf-8 -*-
"""
[B 적대적 검증, 2026-08-31 소유자 질문] 「B 에게도 확증편향이 있는 건 아닌가」

문제 의식: 지금까지의 모든 기각은 **B 를 심판으로 놓은 시험**이었다. B 자신이 같은
  54년 자료에서 500+ 후보 중 골라진 것이라면, 그 심판이 편향돼 있을 수 있다.
  §5(v56/v57) 가 선택편향 감사를 했으나 「자기 표본 3위」였고, **오늘 Sharpe 로 재니
  자기 격자 1위/153** 이었다(04 §5-7). 그 실을 당긴다.

★ 사전 판정 기준 — **결과 보기 전에 못 박는다.** 하나라도 걸리면 B 의 우위는 의심 대상:
  ① 타 시장 무재조정 이식: −16/−16·252 를 **그대로** 다른 지수에 얹었을 때
     **과반에서** 2배 맨몸에 진다  → 규칙이 나스닥 전용(=맞춤)이라는 증거
  ② 문턱 워크포워드: 과거만으로 고른 문턱이 **불안정**하고, 그 전방 성과가
     −16 고정과 **차이 없다**    → −16 은 사후 지식이라는 증거
  ③ 무작위 규칙 귀무분포: 같은 회전수의 무작위 0/1 규칙 분포에서
     B 가 **중앙 90% 안**에 든다  → 우위가 운과 구별 불가라는 증거

규약: 각 시장 **자기 통화·자기 지수**로 계산. 공격=2배 합성(drag=0.63·σ², drag_sigma
  실측 비율), 방어=현금 0%, 비용 편도 0.1%. 파라미터는 **일절 재조정하지 않는다**.
실행: python research/b_adversarial.py
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

COST = 0.001
TH = -0.16
WIN = 252
DRAG_RATIO = 0.63

MARKETS = [('나스닥100', 'data/hist/yahoo_NDX.csv'),
           ('나스닥종합', 'data/hist/yahoo_IXIC.csv'),
           ('S&P500', 'data/hist/yahoo_GSPC.csv'),
           ('니케이225', 'data/hist/yahoo_N225.csv'),
           ('KOSPI', 'data/hist/kr__5EKS11.csv'),
           ('러셀2000', 'data/hist/yahoo_RUT.csv'),
           ('NYSE종합', 'data/hist/yahoo_NYA.csv')]


def load(path):
    d = pd.read_csv(path, parse_dates=['Date']).set_index('Date')
    col = 'Close' if 'Close' in d.columns else d.columns[0]
    return d[col].astype(float).sort_index().dropna()


def rule_w(p, th=TH, win=WIN):
    dd = (p / p.rolling(win, min_periods=1).max() - 1).values
    w = np.ones(len(p)); att = True
    for i in range(len(p)):
        if att and dd[i] <= th:
            att = False
        elif (not att) and dd[i] > th:
            att = True
        w[i] = 1.0 if att else 0.0
    return w


def curve(w, r):
    m = len(w)
    pos = np.empty(m); pos[0] = w[0]; pos[1:] = w[:-1]
    rr = pos * r; rr[0] = 0.0
    return np.cumprod((1 + rr) * (1 - COST * np.abs(np.diff(pos, prepend=pos[0]))))


def mdd(a):
    return float(np.min(a / np.maximum.accumulate(a) - 1)) * 100


def prep(px):
    r1 = np.nan_to_num(px.pct_change().values)
    r2 = 2 * r1 - DRAG_RATIO * (float(np.nanvar(r1)) * 252) / 252
    return r1, r2


def test1():
    print('\n' + '=' * 76)
    print(' ① 타 시장 무재조정 이식 — −16/−16·252 를 그대로 얹는다')
    print(' 과반에서 2배 맨몸에 지면 「나스닥 전용 맞춤」 증거')
    print('=' * 76)
    print(f"{'시장':>10} {'기간':>16} {'B규칙×2배':>12} {'2배 맨몸':>12} "
          f"{'B/맨몸':>8} {'B MDD':>8} {'승패':>5}")
    wins = 0; total = 0
    for lab, path in MARKETS:
        if not _os.path.exists(path):
            continue
        px = load(path)
        if len(px) < 252 * 10:
            continue
        r1, r2 = prep(px)
        aB = curve(rule_w(px), r2)
        a2 = np.cumprod(1 + r2)
        rat = aB[-1] / a2[-1]
        total += 1
        win = rat > 1
        wins += win
        print(f'{lab:>10} {str(px.index[0].date())[:7]}~{str(px.index[-1].date())[:7]} '
              f'{aB[-1]:>11,.1f}배 {a2[-1]:>11,.1f}배 {rat:>7.2f}배 {mdd(aB):>7.1f}% '
              f'{"승" if win else "★패":>5}')
    print(f'\n  → {total}개 시장 중 **{wins}승 {total-wins}패**  '
          f'{"(과반 승 — 이식 성공)" if wins > total/2 else "★(과반 패 — 나스닥 전용 의심)"}')
    return wins, total


def test2():
    print('\n' + '=' * 76)
    print(' ② 문턱 워크포워드 — 과거만으로 골랐다면 −16 이 나왔을까')
    print(' 선택이 불안정하고 전방 성과가 −16 고정과 같으면 「사후 지식」 증거')
    print('=' * 76)
    px = load('data/hist/yahoo_NDX.csv')
    r1, r2 = prep(px)
    idx = px.index
    n = len(px)
    THS = [round(-0.24 + 0.01 * i, 2) for i in range(17)]
    ws = {t: rule_w(px, t) for t in THS}
    cs = {t: curve(ws[t], r2) for t in THS}
    step = 252 * 3
    start = 252 * 10
    picks, fwd_sel, fwd_fix = [], [], []
    for i in range(start, n - step, step):
        best = max(THS, key=lambda t: cs[t][i] / cs[t][0])
        picks.append(best)
        j = min(i + step, n - 1)
        fwd_sel.append(cs[best][j] / cs[best][i])
        fwd_fix.append(cs[-0.16][j] / cs[-0.16][i])
    picks = np.array(picks)
    print(f'  워크포워드 {len(picks)}회 (3년 걸음, 10년 워밍업)')
    print(f'  선택된 문턱: 중앙 {np.median(picks):+.2f} · 범위 {picks.min():+.2f}~{picks.max():+.2f}'
          f' · 표준편차 {picks.std():.3f}')
    print(f'  −16 이 뽑힌 비율: {np.mean(picks == -0.16):.0%}')
    fs, ff = np.array(fwd_sel), np.array(fwd_fix)
    print(f'  전방 3년 성과 — 워크포워드 선택 {np.prod(fs):,.1f}배 vs '
          f'−16 고정 {np.prod(ff):,.1f}배')
    print(f'  선택이 고정을 이긴 구간 비율: {np.mean(fs > ff):.0%}')
    unstable = picks.std() > 0.02
    nodiff = abs(np.prod(fs) / np.prod(ff) - 1) < 0.20
    print(f'\n  → 선택 {"불안정" if unstable else "안정"} · '
          f'전방 차이 {"거의 없음" if nodiff else "있음"}')
    return unstable and nodiff


def test3():
    print('\n' + '=' * 76)
    print(' ③ 무작위 규칙 귀무분포 — 같은 회전수의 아무 규칙과 비교')
    print(' B 가 중앙 90% 안에 들면 「운과 구별 불가」 증거')
    print('=' * 76)
    px = load('data/hist/yahoo_NDX.csv')
    r1, r2 = prep(px)
    n = len(px)
    wB = rule_w(px)
    aB = curve(wB, r2)
    sw = int(np.sum(np.abs(np.diff(wB))))
    inatt = float(np.mean(wB))
    print(f'  B: 전환 {sw}회 · 공격 비중 {inatt:.1%} · 최종 {aB[-1]:,.1f}배')
    rng = np.random.default_rng(42)
    outs = []
    for _ in range(2000):
        # 같은 전환 횟수·같은 공격 비중을 갖는 무작위 0/1 경로
        cuts = np.sort(rng.choice(np.arange(1, n), size=sw, replace=False))
        w = np.zeros(n); state = 1.0; prev = 0
        for c in cuts:
            w[prev:c] = state; state = 1 - state; prev = c
        w[prev:] = state
        if abs(np.mean(w) - inatt) > 0.15:      # 공격 비중이 크게 다르면 버림
            continue
        outs.append(curve(w, r2)[-1])
    outs = np.array(outs)
    pct = float(np.mean(outs < aB[-1]))
    print(f'  무작위 {len(outs)}개: 중앙 {np.median(outs):,.1f}배 · '
          f'p95 {np.quantile(outs,0.95):,.1f}배 · 최대 {outs.max():,.1f}배')
    print(f'  **B 의 백분위: {pct:.1%}**')
    inside = 0.05 < pct < 0.95
    print(f'  → B 가 중앙 90% {"안 ★" if inside else "밖"} '
          f'({"운과 구별 불가" if inside else "운으로 설명 안 됨"})')
    return inside


def main():
    w, t = test1()
    f2 = test2()
    f3 = test3()
    print('\n' + '=' * 76)
    print(' 종합 판정 (사전 기준대로)')
    print('=' * 76)
    print(f'  ① 타 시장 이식 : {w}/{t} 승 → '
          f'{"★과적합 신호" if w <= t/2 else "통과"}')
    print(f'  ② 문턱 WFA     : {"★과적합 신호" if f2 else "통과"}')
    print(f'  ③ 무작위 귀무   : {"★과적합 신호" if f3 else "통과"}')


if __name__ == '__main__':
    main()
