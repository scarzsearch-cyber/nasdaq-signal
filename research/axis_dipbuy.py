# -*- coding: utf-8 -*-
"""
[v40] 낙폭을 '싸게 사는 기회'로 쓸 수 있는가 — 안 해본 축

v32 를 정정하다가 나온 질문이다. 현행 규칙에서 낙폭이 -16% 를 넘으면 전략은
방어 상태이고, **그때 들어오는 납입금도 방어 바스켓을 산다**. 실측하니 매수
시점의 평균 낙폭이 -4.85% 로, 낙폭을 매수 기회로 쓰고 있지 **않다**.

그런데 신호의 목적은 **이미 쌓인 자산**을 레버리지 붕괴에서 지키는 것이다.
새로 들어오는 돈은 지킬 게 없다. 그렇다면 납입금만 다르게 취급할 수 있지 않을까?

[시험할 것]
  A 현행          납입금이 신호를 따른다 (방어 중이면 방어 바스켓)
  B 항상 레버리지   납입금은 상태와 무관하게 항상 레버리지를 산다
  C 깊을 때만      낙폭이 문턱 이하일 때만 납입금을 레버리지로 (그 외 현행)
  D 증액          낙폭이 깊으면 더 많이 넣는다 (총 납입액은 경로마다 달라질 수 있음)

[이미 기각된 것 — 혼동하지 말 것]
  v22 축3 / v26: **현금으로 쌓아뒀다가 낙폭에 일괄 투입** -> 기여 정확히 0.
  여기서 보는 건 그게 아니다. 납입 시점은 그대로 두고 **어디에 넣느냐**만 바꾼다.

판정은 research_kit 의 관문을 쓴다. 좌측꼬리와 경로 MDD 를 같이 본다.
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defasset as DA
import hist_defensive as DF
import hist_krfinal as KF
from axis_lib import rule_w
from axis_defmix import mix_monthly_from, UST_FEE
from research_kit import dist, fmt_dist, mdd, mdd_vs_paid, verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

COST = 0.002                      # 편도 0.1% + 슬리피지 0.1%
MONTHS = 60                       # ISA 5년 납입


def build():
    D = DF.build('chain')
    Dk, ki, lev2, _, dfk, fr = KF.build_krw('chain')
    kc = {'div': np.asarray(dfk, dtype=float),
          'ust5': (1 + DA.ust_tr(ki, 5, 'TNX', futures=True, fee=UST_FEE)) * (1 + fr) - 1,
          'gold': (1 + DA.gold_r(ki)) * (1 + fr) - 1}
    kdef = mix_monthly_from(kc, {'div': .4, 'ust5': .4, 'gold': .2}, ki)
    return D, ki, lev2, kdef


def accum(lev, dfr, w, ddq, month, lo, hi, mode, thr=-0.16, mp=MONTHS, cost=COST):
    """적립 시뮬레이터. mode 가 납입금의 행선지를 정한다.

    R = 레버리지 버킷, C = 방어 버킷. 전략 전환 시 통째로 옮긴다(전량 전환 규약).
    납입금만 mode 에 따라 다른 버킷으로 들어간다.

    mode='signal'  현행 — 그때 상태를 따른다
    mode='always'  항상 레버리지
    mode='deep'    낙폭 <= thr 이면 레버리지, 아니면 현행
    mode='boost'   현행 + 직전 종가 낙폭 <= thr 이면 2배 납입
                   납입 총액은 경로마다 달라질 수 있다
    """
    R = C = paid = 0.0
    prev = w[lo]
    mi = -1
    vals, pays = [], []
    for i in range(lo, hi):
        pos = w[i - 1] if i > lo else w[lo]
        if pos != prev:                              # 전량 전환
            if pos >= 1:
                R += C * (1 - cost); C = 0.0
            else:
                C += R * (1 - cost); R = 0.0
            prev = pos
        R *= (1 + lev[i]); C *= (1 + dfr[i])
        if i > lo and month[i] != month[i - 1]:
            mi += 1
            if mi < mp:
                signal_dd = ddq[i - 1]              # 직전 종가까지 확인 가능한 낙폭
                a = 2.0 if mode == 'boost' and signal_dd <= thr else 1.0
                paid += a
                to_lev = (pos >= 1)
                if mode == 'always':
                    to_lev = True
                elif mode == 'deep':
                    to_lev = (pos >= 1) or (signal_dd <= thr)

                if to_lev:
                    R += a
                else:
                    C += a
        vals.append(R + C); pays.append(paid)
    return np.array(vals), np.array(pays)


def selfcheck_accum():
    """납입 판단은 전일 정보만 쓰고 미래 경로로 과거 납입액을 다시 맞추지 않는다."""
    months = pd.PeriodIndex(
        ['2000-01', '2000-02', '2000-02'], freq='M').values
    zero = np.zeros(3)
    v, p = accum(np.array([0., 0., 1.]), zero, zero,
                 np.array([-.30, 0., 0.]), months,
                 0, 3, 'deep', thr=-.20, mp=1, cost=0)
    assert np.isclose(v[-1], 2.0) and np.isclose(p[-1], 1.0)

    months = pd.PeriodIndex(
        ['2000-01', '2000-02', '2000-03', '2000-04'], freq='M').values
    dd_early = np.array([-.30, 0., 0., 0.])
    dd_future = np.array([-.30, -.30, -.30, 0.])
    _, p1 = accum(np.zeros(4), np.zeros(4), np.zeros(4), dd_early,
                  months, 0, 4, 'boost', thr=-.20, mp=3, cost=0)
    _, p2 = accum(np.zeros(4), np.zeros(4), np.zeros(4), dd_future,
                  months, 0, 4, 'boost', thr=-.20, mp=3, cost=0)
    assert np.isclose(p1[1], 2.0) and np.isclose(p2[1], 2.0)
    assert np.isclose(p1[-1], 4.0) and np.isclose(p2[-1], 6.0)

    drawdowns = dist([-.10, -.30, -.20], 'selfcheck')
    assert np.isclose(drawdowns['worst'], -.30)
    assert not np.isclose(drawdowns['worst'], drawdowns['median'])


def main():
    selfcheck_accum()
    D, ki, lev, dfr = build()
    ddq = D['ddv']
    month = pd.Series(ki).dt.to_period('M').values
    W = rule_w(ddq, -0.16, -0.16)
    fx = int(ki.searchsorted(pd.Timestamp('1981-04-13')))
    print(f"원화 · 규칙 B(-16/-16) · 방어 40/40/20 · 기본 납입 1 × {MONTHS}개월 · 편도 {COST*100:.1f}%")
    print(f"구간 {ki[fx].date()} ~ {ki[-1].date()}\n")
    print("※ 증액 경로는 직전 종가 낙폭에 따라 납입액이 달라져 총 납입액도 경로마다 다를 수 있습니다.\n")

    CASES = [
        ('A 현행 (신호를 따름)', 'signal', None),
        ('B 항상 레버리지', 'always', None),
        ('C 낙폭 -16% 이하면', 'deep', -0.16),
        ('C 낙폭 -25% 이하면', 'deep', -0.25),
        ('C 낙폭 -35% 이하면', 'deep', -0.35),
        ('D 증액 (-20% 이하 2배)', 'boost', -0.20),
        ('D 증액 (-30% 이하 2배)', 'boost', -0.30),
    ]
    for yrs in (10, 15, 20):
        L = yrs * 252
        starts = range(fx, len(ki) - L, 126)
        res = {}
        for lab, mode, thr in CASES:
            fin, md, pr = [], [], []
            for s in starts:
                v, p = accum(lev, dfr, W, ddq, month, s, s + L, mode,
                             thr if thr is not None else -0.16)
                fin.append(v[-1] / p[-1])
                k = int(np.searchsorted(p, MONTHS - 1e-9))
                md.append(mdd(v, since=k, kind='accum'))
                pr.append(mdd_vs_paid(v, p))
            res[lab] = (dist(fin, lab), dist(md, lab), dist(pr, lab))
        base = res[CASES[0][0]][0]
        print(f"=== {yrs}년 창 (n={len(list(starts))}) ===")
        print(f"  {'':<24}{'중앙':>9}{'현행대비':>9}{'5분위':>9}{'최악':>9}"
              f"{'경로MDD중앙':>12}{'원금대비최악':>12}")
        for lab, _, _ in CASES:
            f, m, p = res[lab]
            d = f"{(f['median']/base['median']-1)*100:+8.1f}%" if lab != CASES[0][0] else f"{'-':>9}"
            print(f"  {lab:<24}{f['median']:9.2f}{d}{f['p5']:9.2f}{f['worst']:9.2f}"
                  f"{m['median']*100:11.1f}%{p['worst']*100:11.1f}%")
        print()

    # 판정 — 20년 창 기준
    L = 20 * 252
    starts = list(range(fx, len(ki) - L, 126))
    out = {}
    for lab, mode, thr in CASES:
        fin, pr = [], []
        for s in starts:
            v, p = accum(lev, dfr, W, ddq, month, s, s + L, mode,
                         thr if thr is not None else -0.16)
            fin.append(v[-1] / p[-1]); pr.append(mdd_vs_paid(v, p))
        out[lab] = (np.array(fin), dist(fin, lab), dist(pr, lab))
    b = out[CASES[0][0]]
    print("=" * 78)
    for lab, _, _ in CASES[1:]:
        a = out[lab]
        wins = float((a[0] > b[0]).mean())
        v = verdict(lab, [
            ('중앙값이 현행보다 높다', a[1]['median'] > b[1]['median'],
             f"{a[1]['median']:.2f} vs {b[1]['median']:.2f}"),
            ('20년창 승률 > 55%', wins > 0.55, f"{wins*100:.1f}%"),
            ('5분위(좌측꼬리)가 현행 이상', a[1]['p5'] >= b[1]['p5'],
             f"{a[1]['p5']:.2f} vs {b[1]['p5']:.2f}"),
            ('원금대비 최악이 현행 이상', a[2]['worst'] >= b[2]['worst'],
             f"{a[2]['worst']*100:.1f}% vs {b[2]['worst']*100:.1f}%"),
        ])
        print(v['text']); print()


if __name__ == '__main__':
    main()
