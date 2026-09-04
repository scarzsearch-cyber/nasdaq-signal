# -*- coding: utf-8 -*-
"""
[v53] 실현변동성 상태변수 — 4블록 검증이 가능한 판으로 다시 잰다

v52 에서 나온 것: VIX 를 **도피 시작 시 한 번만** 읽어 복귀선을 정하면
현행을 중앙 +6% · P20 +10% · P5 +11% 로 이긴다. 그런데 **VIX 가 1990~ 이라
4블록 중 2개를 검증할 수 없어 보류**했다.

여기서는 VIX 를 **21일 실현변동성**으로 바꾼다. 그러면 **1972~ 전구간**이 되고
4블록을 전부 검증할 수 있다. (둘의 상관은 0.675 — 같은 것이 아니다. 대용이다.)

[규칙]
  진입:  DD <= -16% -> 방어                (현행 그대로)
         그 순간 실현변동성의 3년 z 를 **한 번만** 읽는다
  복귀:  진입 시 z >  T (변동성 있음) -> DD > -16% 에서 복귀 (현행)
         진입 시 z <= T (조용함)      -> DD > -11% 까지 기다린다

  기전 가설: 조용히 시작된 하락은 구조적이라 얕은 회복이 가짜일 확률이 높다.
             변동성과 함께 온 급락은 V자로 튄다 -> 현행처럼 빨리 돌아간다.

[관문 6개 — 완화하지 않는다]
  G1 ISA중앙  G2 ISA P20  G3 ISA P5  G4 영구중앙  G5 4블록 3/4  G6 MDD 비악화
  + 정밀검증: 파라미터 이웃 / 비용 / 시작일 / 부분표본 / 위기별

[미래참조] rv·rvz 는 전부 후행창. 상태는 도피 진입일에 확정. 체결은 pos = w.shift(1).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

K = 2
ENTER, LATE = -0.16, -0.11
SEGS = [('1972-85', '1972-01-01', '1985-12-31'),
        ('1986-99', '1986-01-01', '1999-12-31'),
        ('2000-13', '2000-01-01', '2013-12-31'),
        ('2014-26', '2014-01-01', '2026-12-31')]


def rule(ddv, z, T):
    """도피 진입일에 z 를 한 번 읽고, 그 도피 내내 복귀선을 고정한다."""
    n = len(ddv)
    w = np.empty(n)
    cur = 1.0
    line = ENTER
    for i in range(n):
        if ddv[i] <= ENTER:
            if cur >= 1.0:                      # 새 도피 — 여기서만 읽는다
                line = ENTER if np.nan_to_num(z[i], nan=9.0) > T else LATE
            cur = 0.0
        elif cur < 1.0 and ddv[i] > line:
            cur = 1.0
        w[i] = cur
    return w


def curve(rk, dfr, w, cost=COST):
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * t)), pos


def main():
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    ddv = np.asarray(D['ddv'], float)
    S = pd.Series(np.asarray(D['px'], float))
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]
    L = 20 * 252

    rv = S.pct_change().rolling(21, min_periods=21).std().values
    rvz = ((rv - pd.Series(rv).rolling(756, min_periods=252).mean().values)
           / pd.Series(rv).rolling(756, min_periods=252).std().values)

    base = rule_w(ddv, ENTER, ENTER)
    alt = rule_w(ddv, ENTER, LATE)

    def dca(c, lo, hi, pay=10 ** 9):
        m = mstart[(mstart > lo) & (mstart < hi)][:pay]
        return float(np.mean(c[hi - 1] / c[m])) if len(m) else np.nan

    def ev(w, cost=COST, step=63, y0=1972):
        c, pos = curve(rk, dfr, w, cost)
        lo0 = int(idx.searchsorted(pd.Timestamp('%d-01-01' % y0)))
        st = list(range(lo0, N - L, step))
        isa = np.array([dca(c, s, s + L, 60) for s in st])
        per = np.array([dca(c, s, s + L) for s in st])
        seg = c[lo0:]
        return dict(m=float(np.median(isa)), p20=float(np.percentile(isa, 20)),
                    p5=float(np.percentile(isa, 5)), pm=float(np.median(per)),
                    mdd=float((seg / np.maximum.accumulate(seg) - 1).min()),
                    sw=int((np.abs(np.diff(pos[lo0:])) > 1e-9).sum()), c=c, isa=isa)

    B, A = ev(base), ev(alt)
    print("=" * 100)
    print("v53 실현변동성 상태변수 — 1972~2026 전구간 (4블록 전부 검증 가능)")
    print("=" * 100)
    print("  현행 -16/-16 :  중앙 %.1f  P20 %.1f  P5 %.1f  영구 %.1f  MDD %.1f%%  전환 %d"
          % (B['m'], B['p20'], B['p5'], B['pm'], B['mdd'] * 100, B['sw']))
    print("  참조 -16/-11 :  중앙 %.1f  P20 %.1f  P5 %.1f  영구 %.1f  MDD %.1f%%  전환 %d"
          % (A['m'], A['p20'], A['p5'], A['pm'], A['mdd'] * 100, A['sw']))
    print()

    # ---------------------------------------------------- 1 문턱 전수
    print("=" * 100)
    print("1. 문턱 T 를 넓게 훑는다 — 양끝이 두 순수 규칙으로 수렴하는가")
    print("=" * 100)
    print("  %-10s%9s%9s%9s%10s%9s%8s%8s"
          % ('T >', '중앙', 'P20', 'P5', '영구중앙', 'MDD', '전환', '3지표'))
    W = {}
    for T in (-3.0, -1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 9.0):
        r = ev(rule(ddv, rvz, T)); W[T] = r
        win = r['m'] > B['m'] and r['p20'] > B['p20'] and r['p5'] > B['p5']
        note = ''
        if T <= -3.0:
            note = '  <- 현행 수렴'
        elif T >= 9.0:
            note = '  <- -16/-11 수렴'
        print("  %-10.2f%9.1f%9.1f%9.1f%10.1f%8.1f%%%8d%8s%s"
              % (T, r['m'], r['p20'], r['p5'], r['pm'], r['mdd'] * 100, r['sw'],
                 'O' if win else 'X', note))
    grid = sorted(W)
    ridge = [T for T in grid if W[T]['m'] > B['m'] and W[T]['p20'] > B['p20']
             and W[T]['p5'] > B['p5']]
    # [코드리뷰 2026-09-04] 종전에는 len(ridge) 를 「연속 N개」로 인쇄하고 관문에도 그대로
    #   썼다. ridge 는 순서 없는 멤버십 목록이라 흩어진 섬 3개도 진짜 고원과 똑같이 통과한다.
    #   실제 인접성을 격자 위에서 잰다.
    run = best_run = 0
    for T in grid:
        run = run + 1 if T in ridge else 0
        best_run = max(best_run, run)
    print()
    print("  3지표 전부 우세: %s  (총 %d개 · 격자에서 연속 최장 %d개)"
          % (', '.join('%.2f' % t for t in ridge) if ridge else '없음', len(ridge), best_run))
    if not ridge:
        # [코드리뷰 2026-09-04] 종전에는 여기서 그냥 return 이라 verdict() 가 아예 안 불렸다.
        #   즉 이 파일이 낼 수 있는 판정은 채택 하나뿐이었다. 계산값에서 기각을 낸다.
        print()
        print(verdict('실현변동성 상태변수를 채택할 수 있는가', [
            ('3지표를 동시에 개선하는 문턱이 존재한다', False,
             '문턱 %d개 전수에서 0개' % len(W)),
        ])['text'])
        return
    T0 = ridge[len(ridge) // 2]
    print("  대표값 T = %.2f 로 이하 검증한다 (우세 집합의 중앙값 — 능선 중심이 아니다)" % T0)
    print()

    R = ev(rule(ddv, rvz, T0))
    cb, cr = B['c'], R['c']

    # ---------------------------------------------------- 2 4블록
    print("=" * 100)
    print("2. 겹치지 않는 4블록 (영구형 적립, 현행 대비)")
    print("=" * 100)
    wins = 0
    print("  %-10s%12s%12s%11s" % ('블록', '현행', 'T=%.2f' % T0, '차이'))
    for nm, a, b in SEGS:
        lo = int(idx.searchsorted(pd.Timestamp(a)))
        hi = int(idx.searchsorted(pd.Timestamp(b), side='right'))
        v0, v1 = dca(cb, lo, hi), dca(cr, lo, hi)
        wins += (v1 > v0)
        print("  %-10s%12.2f%12.2f%10.0f%%" % (nm, v0, v1, (v1 / v0 - 1) * 100))
    print("\n  이긴 블록 %d/4" % wins)
    print()

    # ---------------------------------------------------- 3 부분표본
    print("=" * 100)
    print("3. 창 시작 연대별 (겹치지 않는 구간, ISA형, 현행 대비)")
    print("=" * 100)
    print("  %-14s%8s%9s%9s%9s" % ('창 시작', '창수', '중앙', 'P20', 'P5'))
    okp = 0
    for lab, y0, y1 in (('1972-79', 1972, 1980), ('1980-89', 1980, 1990),
                        ('1990-99', 1990, 2000), ('2000-06', 2000, 2007)):
        lo = int(idx.searchsorted(pd.Timestamp('%d-01-01' % y0)))
        hi = int(idx.searchsorted(pd.Timestamp('%d-01-01' % y1)))
        st = [s for s in range(lo, min(hi, N - L), 63)]
        if len(st) < 5:
            print("  %-14s%8d  창 부족" % (lab, len(st))); continue
        f = lambda c: np.array([dca(c, s, s + L, 60) for s in st])
        a0, a1 = f(cb), f(cr)
        d = [(np.median(a1) / np.median(a0) - 1) * 100,
             (np.percentile(a1, 20) / np.percentile(a0, 20) - 1) * 100,
             (np.percentile(a1, 5) / np.percentile(a0, 5) - 1) * 100]
        okp += all(x > 0 for x in d)
        print("  %-14s%8d%8.0f%%%8.0f%%%8.0f%%" % (lab, len(st), d[0], d[1], d[2]))
    print("\n  세 지표 전부 양수인 연대 %d/4" % okp)
    print()

    # ---------------------------------------------------- 4 비용·시작일
    print("=" * 100)
    print("4. 비용·시작일 민감도")
    print("=" * 100)
    print("  %-14s%12s%12s%10s" % ('편도비용', '현행 중앙', 'T 중앙', '차이'))
    cost_ok = True
    for cost in (0.0005, 0.001, 0.002, 0.005):
        b2, r2 = ev(base, cost), ev(rule(ddv, rvz, T0), cost)
        cost_ok &= (r2['m'] > b2['m'])
        print("  %-11.2f%%%12.1f%12.1f%9.0f%%"
              % (cost * 100, b2['m'], r2['m'], (r2['m'] / b2['m'] - 1) * 100))
    print()
    print("  %-14s%12s%12s%10s" % ('창 간격', '현행 중앙', 'T 중앙', '차이'))
    step_ok = True
    for step in (21, 63, 126, 252):
        b2, r2 = ev(base, COST, step), ev(rule(ddv, rvz, T0), COST, step)
        step_ok &= (r2['m'] > b2['m'])
        print("  %-11d일%12.1f%12.1f%9.0f%%"
              % (step, b2['m'], r2['m'], (r2['m'] / b2['m'] - 1) * 100))
    print()

    # ---------------------------------------------------- 5 위기별
    print("=" * 100)
    print("5. 위기별 (현행 대비)")
    print("=" * 100)
    print("  %-16s%11s%11s%11s" % ('위기', '현행', 'T', '차이'))
    for nm, a, z in (('1973 오일', '1973-01-01', '1975-12-31'),
                     ('1987 블랙먼데이', '1987-08-01', '1988-12-31'),
                     ('2000 닷컴', '2000-03-01', '2003-12-31'),
                     ('2008 GFC', '2007-10-01', '2009-12-31'),
                     ('2020 코로나', '2020-02-01', '2020-12-31'),
                     ('2022 베어', '2021-11-01', '2023-12-31')):
        lo = int(idx.searchsorted(pd.Timestamp(a)))
        hi = int(idx.searchsorted(pd.Timestamp(z), side='right'))
        v0 = cb[hi - 1] / cb[lo] - 1
        v1 = cr[hi - 1] / cr[lo] - 1
        print("  %-16s%10.1f%%%10.1f%%%10.1f%%p" % (nm, v0 * 100, v1 * 100, (v1 - v0) * 100))
    print()

    # ---------------------------------------------------- 판정
    print("=" * 100)
    # [코드리뷰 2026-09-04] ★ G1~G3 은 관문이 아니라 **선택 조건**이다.
    #   ridge 를 거른 세 조건이 G1/G2/G3 과 글자 그대로 같고, T0 in ridge 이며 ev() 는
    #   결정론적이라 R == W[T0] — 즉 셋은 구성상 항상 참이고 실패할 입력이 없다.
    #   (반대편도 없었다: ridge 가 비면 return 이라 verdict() 가 아예 안 불렸다.)
    #   그래서 셋은 근거로 인쇄하되 **adopt_if 에서 빼고**, 채택 여부는 T0 선택에
    #   쓰이지 않은 독립 관문 7개로만 판정한다. 셋의 이름도 사실대로 바꾼다.
    indep = ['G4 영구형 중앙 개선', 'G5 4블록 3/4 이상', 'G6 MDD 비악화',
             '파라미터 이웃이 격자에서 3칸 이상 연속 우세', '비용 5배까지 우위 유지',
             '창 간격을 바꿔도 유지', '연대별 3/4 이상에서 세 지표 양수']
    print(verdict('실현변동성 상태변수(T=%.2f)를 채택할 수 있는가' % T0, [
        ('[선택조건·관문아님] ISA 중앙 개선', R['m'] > B['m'], '%.1f vs %.1f (%+.0f%%)'
         % (R['m'], B['m'], (R['m'] / B['m'] - 1) * 100)),
        ('[선택조건·관문아님] ISA P20 개선', R['p20'] > B['p20'], '%.1f vs %.1f (%+.0f%%)'
         % (R['p20'], B['p20'], (R['p20'] / B['p20'] - 1) * 100)),
        ('[선택조건·관문아님] ISA P5 개선', R['p5'] > B['p5'], '%.1f vs %.1f (%+.0f%%)'
         % (R['p5'], B['p5'], (R['p5'] / B['p5'] - 1) * 100)),
        ('G4 영구형 중앙 개선', R['pm'] > B['pm'], '%.1f vs %.1f' % (R['pm'], B['pm'])),
        ('G5 4블록 3/4 이상', wins >= 3, '%d/4' % wins),
        ('G6 MDD 비악화', R['mdd'] >= B['mdd'],
         '%.1f%% vs %.1f%%' % (R['mdd'] * 100, B['mdd'] * 100)),
        ('파라미터 이웃이 격자에서 3칸 이상 연속 우세', best_run >= 3,
         '연속 최장 %d칸 (우세 총 %d개)' % (best_run, len(ridge))),
        ('비용 5배까지 우위 유지', cost_ok, '0.5% 포함 전부'),
        ('창 간격을 바꿔도 유지', step_ok, '21/63/126/252일 전부'),
        ('연대별 3/4 이상에서 세 지표 양수', okp >= 3, '%d/4' % okp),
    ], adopt_if=indep)['text'])
    # [코드리뷰 2026-09-04] 이 「채택」을 살아있는 채택 후보로 읽지 마라. v53 은 이 집계
    #   관문들을 전부 통과한 뒤 **집중도(G11)에서 기각**됐다 — 갈린 구간 32개 중 2000년
    #   두 개가 우위의 87% 였고 상위 3개를 빼면 P5 가 뒤집혔다(research_kit.concentration
    #   docstring · 04 5-7). 그 검사는 이 파일이 아니라 research/axis_gate11.py 가 건다.


if __name__ == '__main__':
    main()
