# -*- coding: utf-8 -*-
"""
[v44] 목적함수를 바꾸면 답이 달라지는가

지금까지 모든 판정은 **최종 금액과 좌측꼬리**로 했다. 그런데 20년을 실제로
버티는 사람에게는 다른 것이 더 아플 수 있다:

  · 물속에 잠겨 있는 기간 (전 고점 회복까지)
  · 원금 밑으로 내려갈 확률
  · 위험을 얼마나 싫어하는지(CRRA 효용)

목적함수가 바뀌면 최적 규칙도 바뀔 수 있다. v41 에서 Calmar 로 재니
-12/-6 이 이겼던 것처럼. 여기서는 5가지 목적함수로 다시 훑는다.

[목적함수]
  O1 최종금액        지금까지 쓰던 것 (20년창 중앙값)
  O2 좌측꼬리        20년창 5분위 (v41 에서 채택한 관문)
  O3 언더워터 기간    전 고점 아래 머문 기간의 중앙/최악
  O4 원금손실 확률    적립식에서 평가액 < 납입액이 될 확률·기간
  O5 CRRA 효용       위험회피계수 gamma=2
  O6 CRRA 효용       위험회피계수 gamma=5

[주의] 목적함수를 늘리면 '어느 하나에서는 이기는' 규칙이 반드시 나온다.
       그게 v41 의 교훈이다(Calmar 만 보면 속는다). 그래서 **여러 목적함수에서
       동시에 이기는가**를 본다. 하나만 이기면 채택하지 않는다.
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import dist, verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def underwater(c):
    """전 고점 아래 머문 구간들의 길이(거래일). 반환 (중앙, 최악)"""
    a = np.asarray(c)
    peak = np.maximum.accumulate(a)
    uw = a < peak * (1 - 1e-12)
    runs, i, n = [], 0, len(uw)
    while i < n:
        if uw[i]:
            j = i
            while j < n and uw[j]:
                j += 1
            runs.append(j - i); i = j
        else:
            i += 1
    if not runs:
        return 0.0, 0.0
    return float(np.median(runs)), float(max(runs))


def crra(x, g):
    """CRRA 효용. x = 최종배수 (>0). 확실성등가로 환산해 배수 단위로 돌려준다."""
    x = np.asarray(x, dtype=float)
    if abs(g - 1.0) < 1e-9:
        return float(np.exp(np.mean(np.log(x))))
    u = (x ** (1 - g) - 1) / (1 - g)
    return float((np.mean(u) * (1 - g) + 1) ** (1 / (1 - g)))


def main():
    D = DF.build('chain')
    idx, ddq, N = D['idx'], D['ddv'], len(D['idx'])
    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    q = D['qldr']
    MONTH = pd.Series(idx).dt.to_period('M').values

    combos = []
    for e in np.arange(-0.24, -0.09, 0.01):
        for x in np.arange(e, -0.03, 0.01):
            combos.append((round(e, 2), round(x, 2)))

    def curve(e, x):
        w = rule_w(ddq, e, x); pos = np.r_[w[0], w[:-1]]
        r = np.nan_to_num(pos * q + (1 - pos) * defr); r[0] = 0
        t = np.abs(np.diff(pos, prepend=pos[0]))
        return np.cumprod((1 + r) * (1 - COST * t)), w

    def accum(w, lo, hi, mp=60, cost=0.002):
        R = C = P = 0.0; prev = w[lo]; mi = -1; v = []; p = []
        for i in range(lo, hi):
            pos = w[i - 1] if i > lo else w[lo]
            if pos != prev:
                if pos >= 1:
                    R += C * (1 - cost); C = 0.0
                else:
                    C += R * (1 - cost); R = 0.0
                prev = pos
            R *= (1 + q[i]); C *= (1 + defr[i])
            if i > lo and MONTH[i] != MONTH[i - 1]:
                mi += 1
                if mi < mp:
                    P += 1.0
                    if pos >= 1:
                        R += 1.0
                    else:
                        C += 1.0
            v.append(R + C); p.append(P)
        return np.array(v), np.array(p)

    L = 20 * 252
    st = list(range(0, N - L, 126))
    print(f"20년 창 {len(st)}개 · 격자 {len(combos)}개\n")

    res = {}
    for c in combos:
        cv, w = curve(*c)
        rr = np.array([cv[s + L] / cv[s] for s in st])
        uwm, uwx = underwater(cv)
        res[c] = dict(final=np.median(rr), p5=np.percentile(rr, 5),
                      uw_med=uwm / 252, uw_max=uwx / 252,
                      crra2=crra(rr, 2), crra5=crra(rr, 5), rr=rr, w=w)

    # O4도 목적함수다. 종전엔 CRRA5 상위 6개+A/B만 재고 그 안의 1등을
    # 격자 210개 1등처럼 인쇄했다. 느려도 전 격자를 같은 잣대로 잰다.
    B = res[(-0.16, -0.16)]
    for c in combos:
        under = []
        for s in st[::3]:
            v, p = accum(res[c]['w'], s, s + L)
            m = p > 0
            under.append(float((v[m] < p[m]).mean()))     # 원금 밑에 있던 시간 비율
        res[c]['under'] = float(np.median(under))
    assert len([c for c in combos if 'under' in res[c]]) == len(combos)
    Bu = res[(-0.16, -0.16)]['under']

    def show(title, key, rev=False, fmt='{:.2f}', unit=''):
        print(f"=== {title} ===")
        rank = sorted(combos, key=lambda c: (res[c][key] if rev else -res[c][key]))
        bi = rank.index((-0.16, -0.16)) + 1
        print(f"  {'규칙':<10}{'값':>10}{'현행대비':>10}   현행 -16/-16 은 {bi}위/{len(combos)}")
        for c in rank[:4]:
            m = ' <- 현행' if c == (-0.16, -0.16) else ''
            d = res[c][key] / B[key] - 1
            print(f"  {f'{c[0]*100:.0f}/{c[1]*100:.0f}':<10}{fmt.format(res[c][key]):>10}{d*100:>9.0f}%{m}")
        if bi > 4:
            print(f"  {'-16/-16':<10}{fmt.format(B[key]):>10}{'0%':>10} <- 현행")
        print()

    show('O1 최종금액 (20년창 중앙)', 'final')
    show('O2 좌측꼬리 (20년창 5분위)', 'p5')
    show('O3 언더워터 기간 — 중앙 (짧을수록 좋음, 년)', 'uw_med', rev=True)
    show('O3 언더워터 기간 — 최악 (년)', 'uw_max', rev=True)
    show('O5 CRRA 효용 gamma=2', 'crra2')
    show('O6 CRRA 효용 gamma=5 (강한 위험회피)', 'crra5')

    print("=== O4 원금손실 — 적립식에서 평가액<납입액 인 시간 비율 ===")
    print(f"  {'규칙':<10}{'비율':>9}{'현행대비':>10}")
    for c in sorted([c for c in res if 'under' in res[c]], key=lambda c: res[c]['under']):
        m = ' <- 현행' if c == (-0.16, -0.16) else (' <- A' if c == (-0.16, -0.11) else '')
        print(f"  {f'{c[0]*100:.0f}/{c[1]*100:.0f}':<10}{res[c]['under']*100:>8.1f}%"
              f"{(res[c]['under']/Bu-1)*100:>9.0f}%{m}")

    print("\n" + "=" * 78)
    print("판정 — 여러 목적함수에서 동시에 이기는 규칙이 있는가")
    print("=" * 78)
    KEYS = [('최종금액', 'final', False), ('좌측꼬리', 'p5', False),
            ('언더워터 중앙', 'uw_med', True), ('언더워터 최악', 'uw_max', True),
            ('CRRA g=2', 'crra2', False), ('CRRA g=5', 'crra5', False)]
    winners = {}
    for c in combos:
        n = sum(1 for _, k, rev in KEYS
                if (res[c][k] < B[k] if rev else res[c][k] > B[k]))
        winners[c] = n
    best = sorted(combos, key=lambda c: -winners[c])[:5]
    print(f"  {'규칙':<10}{'이긴 목적함수':>14}   내역")
    for c in best:
        det = ' '.join(nm for nm, k, rev in KEYS
                       if (res[c][k] < B[k] if rev else res[c][k] > B[k]))
        print(f"  {f'{c[0]*100:.0f}/{c[1]*100:.0f}':<10}{winners[c]:>10}/{len(KEYS)}   {det}")
    top = best[0]
    v = verdict('목적함수를 바꾸면 현행이 뒤집히는가', [
        (f'6개 중 5개 이상에서 이기는 규칙이 있다', winners[top] >= 5,
         f'최고 {top[0]*100:.0f}/{top[1]*100:.0f} 가 {winners[top]}/6'),
        ('그 규칙이 좌측꼬리도 지킨다', res[top]['p5'] >= B['p5'],
         f"{res[top]['p5']:.1f} vs {B['p5']:.1f}"),
        ('그 규칙이 적립식 원금손실도 늘리지 않는다', res[top]['under'] <= B['under'],
         f"{res[top]['under']*100:.2f}% vs {B['under']*100:.2f}%"),
    ])
    print()
    print(v['text'])


if __name__ == '__main__':
    main()
