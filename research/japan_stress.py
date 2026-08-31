# -*- coding: utf-8 -*-
"""
[전제 스트레스 테스트 — 일본 1989, 2026-08-31 소유자 승인] 「지수가 회복 안 하면?」

왜 이 표본인가: 저장소의 54년 표본에는 **「지수가 수십 년 회복 못 하는 경우」가 한 건도
  없다.** 닷컴도 15년에 돌아왔고 KOSPI 도 회복했다. 니케이 225 는 1989-12 고점을
  **2024년에야** 넘었다(약 35년). B 의 작동 전제는 「−16% 아래로 빠졌다가 **회복하면**
  다시 공격」이므로, 회복이 오지 않는 세계에서 규칙이 무엇을 하는지 이 표본만 답할 수 있다.

★ 이 검사가 답하는 것 / 못 하는 것 (결과 보기 전에 못 박는다):
  답한다 : 「나스닥이 일본처럼 되면 B 는 뭘 하나」 — **조건부** 질문.
  못 한다: 「그렇게 될 확률」 — 표본 1개로는 불가능.
  그리고 **나스닥이 일본이 되면 나스닥 전략은 전부 죽는다.** 질문은 「B 가 죽나」가 아니라
  **「B 가 덜 죽나」**다. SURVIVAL_MONITOR 의 「죽는 건 맨몸」이 다른 시장에서도 성립하는지
  보는 것이며, **채택·기각 판정이 아니다**(다른 지수·다른 통화 = 다른 자산).

규약:
  · 신호   : 니케이 252거래일 고점 대비 −16% (B 와 동일 규칙, 파라미터 무변경)
  · 공격   : 니케이 2배 합성 = 2r − drag. drag = 0.63·σ² — **저장소 실측 비율**
             (drag_sigma.py: 실측 3.30% ÷ σ² 5.20% = 0.63. 교과서 σ² 는 과대평가)
  · 방어   : **현금 0%** — 일본 장기 제로금리 반영, B 에게 보수적(불리)인 선택
  · 비용   : 편도 0.1% (저장소 규약)
  · 통화   : 엔화 기준 (환 효과 배제 — 순수 전제 검사)
실행: python research/japan_stress.py
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
DRAG_RATIO = 0.63              # drag_sigma.py 실측: 실측드래그 / σ²

px = pd.read_csv('data/hist/yahoo_N225.csv', parse_dates=['Date']).set_index('Date')['Close']
px = px.sort_index().dropna()
idx = px.index
n = len(px)
r1 = np.nan_to_num(px.pct_change().values)
var_ann = float(np.nanvar(r1)) * 252
drag_d = DRAG_RATIO * var_ann / 252
r2 = 2 * r1 - drag_d                                  # 2배 합성 일수익


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


def sim(w, r, rdef=0.0):
    pos = np.empty(n); pos[0] = w[0]; pos[1:] = w[:-1]
    rr = pos * r + (1 - pos) * rdef; rr[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + rr) * (1 - COST * turn))


def stat(a, lo, hi=None):
    hi = n if hi is None else hi
    c = np.asarray(a[lo:hi], float); c = c / c[0]
    yrs = (idx[hi - 1] - idx[lo]).days / 365.25
    mdd = float(np.min(c / np.maximum.accumulate(c) - 1)) * 100
    peak = np.maximum.accumulate(c)
    under = int(np.max(np.diff(np.flatnonzero(np.concatenate(
        ([True], c >= peak * 0.9999, [True]))))) - 1) if len(c) > 1 else 0
    return float(c[-1]), (float(c[-1]) ** (1 / yrs) - 1) * 100, mdd, under / 252, yrs


def main():
    print(f'\n니케이225 {idx[0].date()} ~ {idx[-1].date()} ({n:,}일)')
    print(f'연율 변동성 {np.sqrt(var_ann):.1%} → 2배 드래그 {drag_d*252:.2%}/년 '
          f'(저장소 실측 비율 0.63·σ² 적용)')

    pk = int(np.argmax(px.values[:len(px)]))
    print(f'\n[0] 이 표본이 왜 특별한가 — 회복까지 걸린 시간')
    hi89 = px[:'1990'].max(); i89 = int(px[:'1990'].values.argmax())
    after = px.iloc[i89 + 1:]                # 고점 **다음날**부터 — 당일은 회복이 아니다
    rec = after[after >= hi89]
    print(f'  1989 고점 {hi89:,.0f} ({idx[i89].date()})')
    if len(rec):
        yrs = (rec.index[0] - idx[i89]).days / 365.25
        print(f'  회복일 {rec.index[0].date()} — **{yrs:.1f}년**  ← 저장소 표본에 없는 사건')
    print(f'  (참고: 나스닥 닷컴 회복 14년 11개월 · KOSPI 도 회복함)')

    w = rule_w(px)
    aB = sim(w, r2)                      # B 규칙 × 2배
    a2 = np.cumprod(1 + r2)              # 2배 맨몸
    a1 = np.cumprod(1 + r1)              # 1배 맨몸
    rows = [('B 규칙 × 2배', aB), ('2배 맨몸', a2), ('1배 맨몸(지수)', a1)]

    for lab, s in (('★1989 고점에서 시작 (최악의 진입)', i89),
                   ('1970~ 전체', 0)):
        print(f'\n[{lab}]')
        print(f"{'전략':>16} {'최종배수':>10} {'CAGR':>8} {'MDD':>9} {'물속(년)':>9}")
        for nm, a in rows:
            m, cg, md, un, yy = stat(a, s)
            print(f'{nm:>16} {m:>10.2f}배 {cg:>7.1f}% {md:>8.1f}% {un:>8.1f}')

    print('\n[2] 1989 고점 이후 지평별 — 「전제가 깨진 세계」의 지평 표')
    print(f"{'지평':>5} {'B 규칙×2배':>12} {'2배 맨몸':>11} {'1배 지수':>10}")
    for h in (10, 15, 20, 25, 30, 35):
        hi = i89 + h * 252
        if hi >= n:
            continue
        v = [stat(a, i89, hi)[0] for _, a in rows]
        print(f'{h:>4}년 {v[0]:>11.2f}배 {v[1]:>10.2f}배 {v[2]:>9.2f}배')

    print('\n[3] 판정 — 미리 정한 해석 규칙대로')
    m_b, _, d_b, _, _ = stat(aB, i89)
    m_2, _, d_2, _, _ = stat(a2, i89)
    m_1, _, d_1, _, _ = stat(a1, i89)
    print(f'  최악 진입(1989 고점)에서 B {m_b:.2f}배 vs 2배 맨몸 {m_2:.2f}배 vs 지수 {m_1:.2f}배')
    print(f'  낙폭        B {d_b:.1f}% vs 2배 맨몸 {d_2:.1f}% vs 지수 {d_1:.1f}%')
    if m_b > m_2 and d_b > d_2:
        print('  → **규칙이 전제가 깨진 세계에서도 맨몸보다 덜 죽었다.**')
        print('     「죽는 건 맨몸」(SURVIVAL_MONITOR)이 다른 시장에서도 성립.')
    else:
        print('  → 규칙이 이 세계에서는 맨몸을 못 지켰다 — 지평·배율 설계에 반영할 것.')
    print('\n  ⚠ 이것은 **다른 지수·다른 통화**다. 채택·기각 판정이 아니라')
    print('     「전제가 깨지면 어디까지 가나」의 바닥 그림이다.')


if __name__ == '__main__':
    main()
