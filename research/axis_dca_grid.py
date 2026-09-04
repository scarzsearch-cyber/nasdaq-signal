# -*- coding: utf-8 -*-
"""
[v48] 적립식 목적함수로 **문턱 격자 210개**를 훑는다

사용자 질문: "매달매달 적립식으로 투자시에도 현행 전략이 최고였니?"

v47 은 **다른 종류의 전략**(RSI·이평선·현금비중)을 적립식으로 쟀고 14전 14패였다.
그런데 **문턱 자체**(-16/-16 을 -14/-12 로 바꾸는 식)는 적립식으로 훑은 적이 없다.
v22/v26 도 A(-16/-11) 와 B(-16/-16) **둘만** 비교했다. 격자 전체는 처음이다.

[두 가지 납입 방식을 모두 본다]
  ISA형    월 1단위 x 60개월 납입 후 창 끝까지 보유   (연 2천만 x 5년)
  영구형   창 20년 내내 매달 1단위                    ("매달매달")

[가속 — 그리고 그것을 검산한다]
  비중이 0/1 이고 납입금이 그때의 보유처로 들어가면, m 월에 넣은 1단위는
  거치식 곡선 c 를 그대로 탄다. 따라서

        최종/납입 = mean_m ( c[T] / c[t_m] )

  루프 없이 계산된다. **이게 맞는지 루프 시뮬과 오차 0 인지 먼저 확인한다.**
  (검산 없이 빠른 길을 쓰면 v30 처럼 규약을 어긴다)
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
import axis_lib as AX
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import dist, verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

K = 2
CUR = (-0.16, -0.16)


def curve_of(rk, dfr, w):
    """거치식 곡선 (비용 포함). 체결규약 pos = w.shift(1)."""
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr)
    r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - COST * t))


def dca_fast(c, mstart, lo, hi, pay):
    """최종/납입 = mean( c[T] / c[t_m] ). mstart = 월초(납입일) 인덱스 배열."""
    m = mstart[(mstart > lo) & (mstart < hi)][:pay]
    if len(m) == 0:
        return np.nan
    return float(np.mean(c[hi - 1] / c[m]))


def selfcheck(D, rk, dfr, mstart, months):
    """빠른 식이 axis_lib.accumulate() 와 같은가 — 오차 0 이어야 한다."""
    w = rule_w(D['ddv'], *CUR)
    n = len(D['idx'])
    paid0, fin0, _ = AX.accumulate(D, K, w, 0, n)
    c = curve_of(rk, dfr, w)
    fast = dca_fast(c, mstart, 0, n, 10 ** 9)
    err = abs(fast * paid0 / fin0 - 1)
    print("  [검산] 빠른 식 vs axis_lib.accumulate()")
    print("         납입 %.0f   최종 %.3f vs %.3f   상대오차 %.2e"
          % (paid0, fast * paid0, fin0, err))
    if err > 1e-9:
        raise SystemExit('  검산 실패 — 빠른 식이 규약을 어긴다.')
    print("         오차 0 — 같은 계산이다.\n")


def sweep(rk, dfr, ddv, combos, st, L, mstart, pay, label):
    print("=" * 96)
    print(label)
    print("=" * 96)
    res = {}
    for e, x in combos:
        c = curve_of(rk, dfr, rule_w(ddv, e, x))
        v = np.array([dca_fast(c, mstart, s, s + L, pay) for s in st])
        res[(e, x)] = v
    b = res[CUR]
    db = dist(b, '현행')

    rank_med = sorted(combos, key=lambda k: -np.median(res[k]))
    rank_p5 = sorted(combos, key=lambda k: -np.percentile(res[k], 5))
    i_med = rank_med.index(CUR) + 1
    i_p5 = rank_p5.index(CUR) + 1
    print("  현행 -16/-16 :  중앙 %.1f (%d위/%d)   5분위 %.1f (%d위/%d)"
          % (db['median'], i_med, len(combos), db['p5'], i_p5, len(combos)))
    print()
    print("  %-12s%9s%9s%9s%8s%9s" % ('규칙', '중앙', '5분위', '최악', '승률', '중앙대비'))
    for k in rank_med[:6]:
        d = dist(res[k], '')
        cur = (k == CUR)
        wr = '%6.0f%%' % ((res[k] > b).mean() * 100) if not cur else '%7s' % '-'
        rel = '%7.0f%%' % ((d['median'] / db['median'] - 1) * 100) if not cur else '%8s' % '-'
        print("  %-12s%9.1f%9.1f%9.1f%8s%9s%s"
              % ('%.0f/%.0f' % (k[0] * 100, k[1] * 100), d['median'], d['p5'],
                 d['worst'], wr, rel, '  <- 현행' if cur else ''))
    if i_med > 6:
        print("  %-12s%9.1f%9.1f%9.1f%8s%9s  <- 현행"
              % ('-16/-16', db['median'], db['p5'], db['worst'], '-', '-'))

    # 현행을 세 관문 모두에서 이기는 규칙
    win = []
    for k in combos:
        if k == CUR:
            continue
        d = dist(res[k], '')
        if (d['median'] > db['median'] and d['p5'] > db['p5']
                and (res[k] > b).mean() > 0.55):
            win.append((k, d, float((res[k] > b).mean())))
    print()
    if win:
        print("  현행을 **중앙·5분위·승률 모두**에서 이긴 규칙 %d개:" % len(win))
        for k, d, wr in sorted(win, key=lambda t: -t[1]['median'])[:8]:
            print("    %-12s 중앙 %7.1f (%+.0f%%)  5분위 %6.1f  승률 %.0f%%"
                  % ('%.0f/%.0f' % (k[0] * 100, k[1] * 100), d['median'],
                     (d['median'] / db['median'] - 1) * 100, d['p5'], wr * 100))
    else:
        print("  현행을 중앙·5분위·승률 **모두**에서 이긴 규칙: 없음")
    print()
    return res, win, i_med, i_p5


def blocks(rk, dfr, ddv, cand, mstart, idx, pay):
    """겹치지 않는 4블록 — 과적합 걸러내기 (v43/v44 와 같은 관문)."""
    print("=" * 96)
    print("겹치지 않는 4블록에서도 유지되는가 (적립식, 납입 %s)"
          % ('60개월' if pay < 10 ** 6 else '내내'))
    print("=" * 96)
    segs = [('1972-85', '1972-01-01', '1985-12-31'),
            ('1986-99', '1986-01-01', '1999-12-31'),
            ('2000-13', '2000-01-01', '2013-12-31'),
            ('2014-26', '2014-01-01', '2026-12-31')]
    cs = {k: curve_of(rk, dfr, rule_w(ddv, *k)) for k in cand}
    base = cs[CUR]
    print("  %-12s" % '규칙' + ''.join('%11s' % s[0] for s in segs) + "%10s" % '최악')
    out = {}
    for k in cand:
        row, rel = [], []
        for _, a, b_ in segs:
            lo = int(idx.searchsorted(pd.Timestamp(a)))
            hi = int(idx.searchsorted(pd.Timestamp(b_), side='right'))
            v = dca_fast(cs[k], mstart, lo, hi, pay)
            v0 = dca_fast(base, mstart, lo, hi, pay)
            rel.append(v / v0 - 1)
        out[k] = rel
        mk = '  <- 현행' if k == CUR else ''
        print("  %-12s" % ('%.0f/%.0f' % (k[0] * 100, k[1] * 100))
              + ''.join('%10.0f%%' % (r * 100) for r in rel)
              + '%9.0f%%%s' % (min(rel) * 100, mk))
    print()
    return out


def robust_joint(w1, w2, block_rel):
    """두 납입규약에서 *같은* 후보가 이기고 네 블록도 모두 비악화해야 한다."""
    a = {row[0] for row in w1}
    b = {row[0] for row in w2}
    common = a & b
    robust = {k for k in common if k in block_rel and min(block_rel[k]) >= 0}
    return common, robust


def main():
    D = DF.build('chain')
    idx, ddv, N = D['idx'], D['ddv'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    D = dict(D); D['schdr'] = dfr
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]

    print("=" * 96)
    print("적립식 문턱 격자 — 구간 %s ~ %s" % (idx[0].date(), idx[-1].date()))
    print("=" * 96)
    selfcheck(D, rk, dfr, mstart, months)

    combos = []
    for e in np.arange(-0.24, -0.09, 0.01):
        for x in np.arange(e, -0.03, 0.01):
            combos.append((round(e, 2), round(x, 2)))
    L = 20 * 252
    st = list(range(0, N - L, 126))
    print("  격자 %d개 · 20년 창 %d개\n" % (len(combos), len(st)))

    r1, w1, m1, p1 = sweep(rk, dfr, ddv, combos, st, L, mstart, 60,
                           "1. ISA형 — 월 1단위 x 60개월 납입 후 보유")
    r2, w2, m2, p2 = sweep(rk, dfr, ddv, combos, st, L, mstart, 10 ** 9,
                           "2. 영구형 — 20년 내내 매달 납입 (\"매달매달\")")

    top2 = sorted(combos, key=lambda k: -np.median(r2[k]))[:4]
    preliminary_common = {row[0] for row in w1} & {row[0] for row in w2}
    cand = [CUR] + [k for k in top2 if k != CUR]
    cand += [k for k in sorted(preliminary_common) if k not in cand]
    block_rel = blocks(rk, dfr, ddv, cand, mstart, idx, 10 ** 9)
    common, robust = robust_joint(w1, w2, block_rel)

    # 서로 다른 승자 하나씩으로는 통과할 수 없다. 네 블록 중 하나라도 지면 탈락한다.
    fake1 = [((-.10, -.10), {}, 1.0)]
    fake2 = [((-.11, -.11), {}, 1.0)]
    assert robust_joint(fake1, fake2, {}) == (set(), set())

    print("=" * 96)
    print(verdict('적립식에서 현행을 바꿔야 하는가', [
        ('같은 규칙이 ISA형·영구형을 모두 이긴다', bool(common),
         '%d개 (ISA %d개 · 영구 %d개)' % (len(common), len(w1), len(w2))),
        ('그 규칙이 겹치지 않는 네 시대에서도 안 진다', bool(robust),
         '%d개' % len(robust)),
    ])['text'])


if __name__ == '__main__':
    main()
