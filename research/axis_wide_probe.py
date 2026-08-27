# -*- coding: utf-8 -*-
"""
[v50-b] 유일한 생존 후보 정밀 검증 — G (DD 개선폭 복귀)

v50 광역탐색 49개 중 6관문을 4개 통과한 유일한 후보:

    현행 -16/-16  +  **도피 중이라도 DD 가 최근 20일간 +3%p 이상 개선되면 즉시 복귀**

  ISA중앙 69.0 (-9%)   P20 46.2 (+26%)   P5 30.8 (+20%)   4블록 4/4   전환 256

제안 §18 이 요구한 정밀검증을 전부 돌린다.
  1 파라미터 이웃      인접값도 함께 좋은가, 아니면 첨탑인가
  2 비용 민감도        전환이 1.8배다. 비용을 올려도 우위가 남는가
  3 시작일 민감도      시작일을 옮겨도 유지되는가
  4 기전 설명          어디서 벌고 어디서 잃는가 (§24)
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, lev_r
from axis_defmix import materials, mix_monthly_from
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

K = 2
ENTER = -0.16
BEST = (20, 0.03)


def gw(ddv, k, g):
    """현행 + DD 가 최근 k일간 g 이상 개선되면 즉시 복귀."""
    d = np.r_[np.zeros(k), ddv[k:] - ddv[:-k]]
    w = np.where(ddv > ENTER, 1.0, 0.0)
    return np.where((ddv <= ENTER) & (d > g), 1.0, w)


def curve(rk, dfr, w, cost):
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * t)), pos


def dca(c, mstart, lo, hi, pay=60):
    m = mstart[(mstart > lo) & (mstart < hi)][:pay]
    return float(np.mean(c[hi - 1] / c[m])) if len(m) else np.nan


def main():
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    ddv = np.asarray(D['ddv'], float)
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]
    L = 20 * 252
    base_w = rule_w(ddv, ENTER, ENTER)

    def stats(w, cost=0.001, step=126):
        c, pos = curve(rk, dfr, w, cost)
        st = list(range(0, N - L, step))
        v = np.array([dca(c, mstart, s, s + L) for s in st])
        m = float((c / np.maximum.accumulate(c) - 1).min())
        return (float(np.median(v)), float(np.percentile(v, 20)),
                float(np.percentile(v, 5)), m,
                int((np.abs(np.diff(pos)) > 1e-9).sum()), v)

    # -------------------------------------------------- 1 파라미터 이웃
    print("=" * 100)
    print("1. 파라미터 이웃 — 인접값도 함께 좋은가 (제안 §13: 첨탑이면 과적합)")
    print("=" * 100)
    b = stats(base_w)
    print("  현행 기준선:  중앙 %.1f   P20 %.1f   P5 %.1f   MDD %.1f%%   전환 %d"
          % (b[0], b[1], b[2], b[3] * 100, b[4]))
    print()
    print("  %-6s" % 'k\\g' + ''.join('%22s' % ('+%.0f%%p' % (g * 100))
                                      for g in (0.02, 0.03, 0.04, 0.05, 0.06)))
    print("  %-6s" % '' + ''.join('%22s' % '중앙/P20/P5  (MDD)' for _ in range(5)))
    for k in (10, 15, 20, 25, 30, 40):
        row = "  %-6d" % k
        for g in (0.02, 0.03, 0.04, 0.05, 0.06):
            m, p20, p5, mx, sw, _ = stats(gw(ddv, k, g))
            mark = '*' if (k, g) == BEST else ' '
            row += "%s%5.1f/%4.1f/%4.1f(%5.1f)" % (mark, m, p20, p5, mx * 100)
        print(row)
    print()
    print("  * = v50 이 뽑은 값. 굵은 개선은 k=20, g=3~5%p 에만 몰려 있는가?")
    print()

    # -------------------------------------------------- 2 비용 민감도
    print("=" * 100)
    print("2. 비용 민감도 — 전환이 %d 대 %d 다. 비용을 올려도 우위가 남는가"
          % (stats(gw(ddv, *BEST))[4], b[4]))
    print("=" * 100)
    print("  %-12s%12s%12s%12s%12s" % ('편도비용', '현행 P20', 'G P20', '현행 P5', 'G P5'))
    for cost in (0.0005, 0.001, 0.002, 0.003, 0.005):
        bb = stats(base_w, cost)
        gg = stats(gw(ddv, *BEST), cost)
        mk = '  <- 실제 가정' if abs(cost - 0.001) < 1e-9 else ''
        print("  %-9.2f%%%12.1f%12.1f%12.1f%12.1f%s"
              % (cost * 100, bb[1], gg[1], bb[2], gg[2], mk))
    print()

    # -------------------------------------------------- 3 시작일 민감도
    print("=" * 100)
    print("3. 시작일 민감도 — 창 간격을 바꿔도 유지되는가")
    print("=" * 100)
    print("  %-12s%12s%12s%12s%12s" % ('창 간격', '현행 P20', 'G P20', '현행 P5', 'G P5'))
    for step in (21, 63, 126, 252):
        bb = stats(base_w, 0.001, step)
        gg = stats(gw(ddv, *BEST), 0.001, step)
        print("  %-9d일%12.1f%12.1f%12.1f%12.1f" % (step, bb[1], gg[1], bb[2], gg[2]))
    print()

    # -------------------------------------------------- 4 기전
    print("=" * 100)
    print("4. 기전 — 어디서 벌고 어디서 잃는가 (제안 §24)")
    print("=" * 100)
    wg = gw(ddv, *BEST)
    diff = (wg > base_w)
    print("  G 가 현행보다 먼저 공격으로 돌아가 있는 날 %d일 / %d일 (%.1f%%)"
          % (diff.sum(), N, diff.mean() * 100))
    cg, _ = curve(rk, dfr, wg, 0.001)
    cb, _ = curve(rk, dfr, base_w, 0.001)
    print("  거치식 MDD   현행 %.1f%%  ->  G %.1f%%   (%+.1f%%p)"
          % ((cb / np.maximum.accumulate(cb) - 1).min() * 100,
             (cg / np.maximum.accumulate(cg) - 1).min() * 100,
             ((cg / np.maximum.accumulate(cg) - 1).min()
              - (cb / np.maximum.accumulate(cb) - 1).min()) * 100))
    print()
    print("  위기별 — G 가 먼저 복귀한 뒤 어떻게 됐나")
    print("  %-14s%12s%12s%10s" % ('위기', '현행', 'G', '차이'))
    for nm, a, z in (('1973 오일', '1973-01-01', '1975-12-31'),
                     ('1987 블랙먼데이', '1987-08-01', '1988-12-31'),
                     ('2000 닷컴', '2000-03-01', '2003-12-31'),
                     ('2008 GFC', '2007-10-01', '2009-12-31'),
                     ('2020 코로나', '2020-02-01', '2020-12-31'),
                     ('2022 베어', '2021-11-01', '2023-12-31')):
        lo = int(idx.searchsorted(pd.Timestamp(a)))
        hi = int(idx.searchsorted(pd.Timestamp(z), side='right'))
        vb = cb[hi - 1] / cb[lo] - 1
        vg = cg[hi - 1] / cg[lo] - 1
        print("  %-14s%11.1f%%%11.1f%%%9.1f%%p" % (nm, vb * 100, vg * 100, (vg - vb) * 100))
    print()

    # -------------------------------------------------- 판정
    nb = [stats(gw(ddv, k, g))[1] for k, g in
          ((20, 0.02), (20, 0.04), (20, 0.05), (15, 0.03), (25, 0.03))]
    n_ok = sum(1 for x in nb if x > b[1])
    c5 = stats(gw(ddv, *BEST), 0.005)
    b5 = stats(base_w, 0.005)
    print("=" * 100)
    print(verdict('G(DD개선 복귀) 를 보조전략으로 채택할 수 있는가', [
        ('파라미터 이웃 5개 중 4개 이상이 P20 개선', n_ok >= 4,
         '%d/5 개선' % n_ok),
        ('비용 0.5% 에서도 P20 우위 유지', c5[1] > b5[1],
         'G %.1f vs 현행 %.1f' % (c5[1], b5[1])),
        ('거치식 MDD 를 악화시키지 않는다',
         (cg / np.maximum.accumulate(cg) - 1).min()
         >= (cb / np.maximum.accumulate(cb) - 1).min(),
         '%.1f%% vs %.1f%%' % ((cg / np.maximum.accumulate(cg) - 1).min() * 100,
                               (cb / np.maximum.accumulate(cb) - 1).min() * 100)),
    ])['text'])


if __name__ == '__main__':
    main()
