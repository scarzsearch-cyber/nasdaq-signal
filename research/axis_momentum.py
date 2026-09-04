# -*- coding: utf-8 -*-
"""
[v49] 절대모멘텀 · 이중모멘텀 · DD+모멘텀 하이브리드 · 단계적 비중

제안 출처: 사용자가 가져온 외부 제안(ChatGPT). 7개 후보 중 **진짜 새로운 것**만 잰다.

  ① 절대 모멘텀          미검증 -> 잰다
  ② 이중 모멘텀          미검증 -> 잰다
  ③ DD + 모멘텀 하이브리드 미검증 -> 잰다 (제안자·나 둘 다 1순위로 꼽은 것)
  ④ 단계적 비중 전환      v18 §4-2 에서 기각됐으나 **거치식으로만** -> 적립식 재시험
  ⑤ 변동성 기반          v32 에서 적립식으로 기각 (승률 24~33%) -> 안 한다
  ⑥ 이동평균 레짐        v47 에서 20/60/200 기각 -> 100/150 만 보탠다
  ⑦ 변동성+낙폭 복합      v32 가 사실상 이것 -> 안 한다

[관문 — 제안된 것과 내 것이 같다. 그대로 쓴다]
  1 ISA형 60개월 월납 · 2 영구형 20년 월납
  3 중앙 / 5분위 / 20분위 / 최악      (제안은 20% 꼬리, 내 기준은 5% — 둘 다 낸다)
  4 겹치지 않는 4블록
  5 현행 -16/-16 대비
  6 전환 횟수(비용 이미 반영)

  **CAGR 1위가 아니라 '현행 대비 일관되게 우월한가'로 판정한다.**

[주의 — 부분비중의 모형 가정]
  단계적 비중은 curve 상에서 **매일 목표비중으로 재조정**된다고 본다.
  실제로는 그렇게 못 한다(비용·호가). 그러니 ④가 이기면 그때 현실적 재조정으로
  다시 재야 한다. 지면 그럴 필요가 없다.
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
M6, M12 = 126, 252          # 6개월 / 12개월 (거래일)


# ================================================================= 공용
def curve_of(rk, dfr, w):
    """비중경로 -> 거치식 곡선. pos = w.shift(1), 비용 |Δpos| 비례.
    부분비중이면 매일 목표비중으로 재조정한다고 본다."""
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr)
    r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - COST * t)), pos


def ma_signal(px, window):
    """이동평균이 준비되기 전에는 기존 계약대로 공격(1), 이후에만 비교한다."""
    s = pd.Series(np.asarray(px, dtype=float))
    ma = s.rolling(window, min_periods=window).mean()
    return np.where(ma.isna(), 1.0, (s > ma).astype(float)).astype(float)


def _selfcheck_ma_warmup():
    rising = np.arange(1.0, 6.0)
    assert np.array_equal(ma_signal(rising, 3), np.ones(5))
    falling = np.arange(5.0, 0.0, -1.0)
    assert np.array_equal(ma_signal(falling, 3), [1, 1, 0, 0, 0])


def dca_fast(c, mstart, lo, hi, pay):
    m = mstart[(mstart > lo) & (mstart < hi)][:pay]
    if len(m) == 0:
        return np.nan
    return float(np.mean(c[hi - 1] / c[m]))


def loop_dca(rk, dfr, w, mstart, lo, hi, pay):
    """루프 시뮬 — 빠른 식 검산용. 납입금은 그때의 목표비중대로 나눠 넣는다."""
    pos = np.r_[w[0], w[:-1]]
    R = C = paid = 0.0
    p = pos[lo]
    R, C = 0.0, 0.0
    mset = set(mstart[(mstart > lo) & (mstart < hi)][:pay].tolist())
    for i in range(lo, hi):
        q = pos[i]
        if q != p:                                   # 목표비중으로 재조정
            tot = R + C
            newR = tot * q
            R, C = newR, tot - newR
            tot2 = tot * (1 - COST * abs(q - p))
            R *= tot2 / max(tot, 1e-300); C *= tot2 / max(tot, 1e-300)
            p = q
        R *= (1 + np.nan_to_num(rk[i])); C *= (1 + np.nan_to_num(dfr[i]))
        if i in mset:
            paid += 1.0
            R += q; C += (1 - q)
        # 부분비중은 매일 목표로 되돌린다 (curve_of 와 같은 가정)
        tot = R + C
        R, C = tot * q, tot * (1 - q)
    return paid, R + C


# ================================================================= 후보
def candidates(D, rk, dfr):
    px = np.asarray(D['px'], dtype=float)
    ddv = np.asarray(D['ddv'], dtype=float)
    n = len(ddv)
    cd = {}

    def mom(lb):
        """lb 거래일 수익률. 그날까지의 값 (체결은 lag 가 담당)."""
        m = np.full(n, np.nan)
        m[lb:] = px[lb:] / px[:-lb] - 1
        return m

    m6, m12, m9 = mom(M6), mom(M12), mom(189)
    # 방어 바스켓의 같은 기간 수익률 (상대강도용)
    dcum = np.cumprod(1 + np.nan_to_num(dfr))
    d12 = np.full(n, np.nan); d12[M12:] = dcum[M12:] / dcum[:-M12] - 1

    base = rule_w(ddv, *CUR)
    cd['현행 -16/-16'] = base

    # ---------------------------------------------------------- ① 절대 모멘텀
    for lb, nm in ((M6, '6M'), (189, '9M'), (M12, '12M')):
        m = {M6: m6, 189: m9, M12: m12}[lb]
        cd['① 절대모멘텀 %s' % nm] = np.where(np.nan_to_num(m, nan=1.0) > 0, 1.0, 0.0)

    # ---------------------------------------------------------- ② 이중 모멘텀
    dual = (np.nan_to_num(m12, nan=1.0) > 0) & (np.nan_to_num(m12, nan=1.0) > np.nan_to_num(d12, nan=-1.0))
    cd['② 이중모멘텀 12M'] = np.where(dual, 1.0, 0.0)

    # ------------------------------------------- ③ DD + 모멘텀 하이브리드 (제안 원안)
    # 방어로: DD <= -16% **그리고** 12M 모멘텀 < 0
    # 복귀로: DD > -11%  **그리고** 6M  모멘텀 > 0
    def hybrid(enter, exitl, mo_in, mo_out, lb_in=M12, lb_out=M6):
        mi = {M6: m6, 189: m9, M12: m12}[lb_in]
        mo = {M6: m6, 189: m9, M12: m12}[lb_out]
        w = np.empty(n); cur = 1.0
        for i in range(n):
            a = np.nan_to_num(mi[i], nan=1.0)
            b = np.nan_to_num(mo[i], nan=1.0)
            if cur >= 1.0:
                if ddv[i] <= enter and (not mo_in or a < 0):
                    cur = 0.0
            else:
                if ddv[i] <= enter and (not mo_in or a < 0):
                    cur = 0.0
                elif ddv[i] > exitl and (not mo_out or b > 0):
                    cur = 1.0
            w[i] = cur
        return w

    cd['③ DD-16/-11 + 모멘텀(원안)'] = hybrid(-0.16, -0.11, True, True)
    cd['③b DD-16/-16 + 복귀모멘텀만'] = hybrid(-0.16, -0.16, False, True)
    cd['③c DD-16/-11 + 복귀모멘텀만'] = hybrid(-0.16, -0.11, False, True)
    cd['③d DD-16/-16 + 진입모멘텀만'] = hybrid(-0.16, -0.16, True, False)

    # ---------------------------------------------------------- ④ 단계적 비중
    def ladder(steps):
        w = np.ones(n)
        for lvl, wt in steps:
            w = np.where(ddv <= lvl, wt, w)
        return w

    cd['④ 사다리 10/15/20/25 (원안)'] = ladder(
        [(-0.10, .75), (-0.15, .50), (-0.20, .25), (-0.25, .0)])
    cd['④b 사다리 16/20/25'] = ladder([(-0.16, .50), (-0.20, .25), (-0.25, .0)])
    # 히스테리시스 있는 사다리 (톱니 완화)
    w = np.ones(n); cur = 1.0
    for i in range(n):
        d = ddv[i]
        tgt = 1.0 if d > -0.10 else .75 if d > -0.15 else .50 if d > -0.20 else .25 if d > -0.25 else 0.0
        if tgt < cur or d > -0.08:          # 내릴 땐 즉시, 올릴 땐 -8% 회복 후
            cur = tgt
        w[i] = cur
    cd['④c 사다리 + 히스테리시스'] = w

    # ---------------------------------------------------------- ⑥ 이평 100/150
    for nn in (100, 150):
        cd['⑥ 이평 %d일' % nn] = ma_signal(px, nn)
    return cd


# ================================================================= 판정
def evaluate(cd, rk, dfr, mstart, st, L, idx):
    curves = {}
    for nm, w in cd.items():
        c, pos = curve_of(rk, dfr, w)
        curves[nm] = (c, pos)

    out = {}
    for pay, mode in ((60, 'ISA형'), (10 ** 9, '영구형')):
        print("=" * 100)
        print("%s — %s" % (mode, '월 1단위 x 60개월 후 보유' if pay == 60 else '20년 내내 매달'))
        print("=" * 100)
        res = {nm: np.array([dca_fast(curves[nm][0], mstart, s, s + L, pay) for s in st])
               for nm in cd}
        b = res['현행 -16/-16']
        db = dist(b, '')
        print("  %-28s%8s%8s%8s%8s%7s%8s%7s"
              % ('후보', '중앙', '20분위', '5분위', '최악', '승률', '중앙대비', '전환'))
        for nm in cd:
            d = dist(res[nm], '')
            p20 = float(np.percentile(res[nm], 20))
            cur = (nm == '현행 -16/-16')
            sw = int((np.abs(np.diff(curves[nm][1])) > 1e-9).sum())
            wr = '%6.0f%%' % ((res[nm] > b).mean() * 100) if not cur else '%7s' % '-'
            rel = '%7.0f%%' % ((d['median'] / db['median'] - 1) * 100) if not cur else '%8s' % '-'
            print("  %-28s%8.1f%8.1f%8.1f%8.1f%8s%9s%7d%s"
                  % (nm, d['median'], p20, d['p5'], d['worst'], wr, rel, sw,
                     '  <- 현행' if cur else ''))
        # 세 관문 동시 통과
        win = [nm for nm in cd if nm != '현행 -16/-16'
               and dist(res[nm], '')['median'] > db['median']
               and dist(res[nm], '')['p5'] > db['p5']
               and (res[nm] > b).mean() > 0.55]
        print()
        print("  현행을 중앙·5분위·승률 **모두** 이긴 후보: %s"
              % (', '.join(win) if win else '없음'))
        print()
        out[mode] = (res, win)
    return curves, out


def blocks(curves, mstart, idx, names):
    print("=" * 100)
    print("겹치지 않는 4블록 (영구형 적립, 현행 대비 %)")
    print("=" * 100)
    segs = [('1972-85', '1972-01-01', '1985-12-31'),
            ('1986-99', '1986-01-01', '1999-12-31'),
            ('2000-13', '2000-01-01', '2013-12-31'),
            ('2014-26', '2014-01-01', '2026-12-31')]
    print("  %-28s" % '후보' + ''.join('%10s' % s[0] for s in segs) + "%10s%8s" % ('최악', '이긴블록'))
    base = curves['현행 -16/-16'][0]
    for nm in names:
        c = curves[nm][0]
        rel = []
        for _, a, b_ in segs:
            lo = int(idx.searchsorted(pd.Timestamp(a)))
            hi = int(idx.searchsorted(pd.Timestamp(b_), side='right'))
            rel.append(dca_fast(c, mstart, lo, hi, 10 ** 9)
                       / dca_fast(base, mstart, lo, hi, 10 ** 9) - 1)
        print("  %-28s" % nm + ''.join('%9.0f%%' % (r * 100) for r in rel)
              + '%9.0f%%%7d/4%s' % (min(rel) * 100, sum(1 for r in rel if r > 0),
                                    '  <- 현행' if nm == '현행 -16/-16' else ''))
    print()


def main():
    _selfcheck_ma_warmup()
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    D = dict(D); D['schdr'] = dfr
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]

    print("=" * 100)
    print("v49 모멘텀·하이브리드·사다리 — 구간 %s ~ %s" % (idx[0].date(), idx[-1].date()))
    print("=" * 100)
    # 검산 ① 이진 비중: axis_lib.accumulate() 와 오차 0
    w = rule_w(D['ddv'], *CUR)
    paid0, fin0, _ = AX.accumulate(D, K, w, 0, N)
    c0, _ = curve_of(rk, dfr, w)
    f0 = dca_fast(c0, mstart, 0, N, 10 ** 9)
    e0 = abs(f0 * paid0 / fin0 - 1)
    # 검산 ② 부분비중: 빠른 식 vs 루프 시뮬
    wl = np.where(D['ddv'] <= -0.15, 0.5, 1.0)
    cl, _ = curve_of(rk, dfr, wl)
    p1, v1 = loop_dca(rk, dfr, wl, mstart, 0, N, 10 ** 9)
    e1 = abs(dca_fast(cl, mstart, 0, N, 10 ** 9) * p1 / v1 - 1)
    print("  [검산1] 이진비중  vs axis_lib.accumulate()   상대오차 %.2e" % e0)
    print("  [검산2] 부분비중  vs 루프 시뮬               상대오차 %.2e" % e1)
    if e0 > 1e-9 or e1 > 1e-9:
        raise SystemExit('  검산 실패 — 결과를 믿을 수 없다.')
    print("  둘 다 오차 0.\n")

    cd = candidates(D, rk, dfr)
    L = 20 * 252
    st = list(range(0, N - L, 126))
    print("  후보 %d개 · 20년 창 %d개\n" % (len(cd), len(st)))

    curves, out = evaluate(cd, rk, dfr, mstart, st, L, idx)
    blocks(curves, mstart, idx, list(cd.keys()))

    w1 = out['ISA형'][1]; w2 = out['영구형'][1]
    both = sorted(set(w1) & set(w2))
    print("=" * 100)
    print(verdict('모멘텀·하이브리드·사다리가 현행을 대체하는가', [
        ('ISA형에서 현행을 모두 이긴 후보가 있다', len(w1) > 0, '%d개' % len(w1)),
        ('영구형에서 현행을 모두 이긴 후보가 있다', len(w2) > 0, '%d개' % len(w2)),
        ('양쪽 모두에서 이긴 후보가 있다', len(both) > 0,
         ', '.join(both) if both else '없음'),
    ])['text'])


if __name__ == '__main__':
    main()
