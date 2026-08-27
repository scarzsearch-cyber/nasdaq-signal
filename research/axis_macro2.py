# -*- coding: utf-8 -*-
"""
[v30 축6-2] 공포탐욕 역발상 신호를 긴 구간(1972~)에서 재검증

axis_macro.py 는 2011-2026 구간에서만 잴 수 있었다(SCHD 시작일). 그 15년은
모든 하락이 V자로 회복한 예외적 시기다. 닷컴(2000-2002)·금융위기(2007-2009)
처럼 2년씩 갈아뭉개는 장에서는 "공포극단이면 2배 레버리지 유지"가 치명적일 수
있다. 프로젝트 자체 엔진(hist_defensive.build)으로 1972년까지 늘려 재판정한다.

공포탐욕 대용치는 VIX 시작(1990) 이전까지 잇기 위해 '실현변동성'으로 대체한다.
1990- 구간에서 VIX판과 실현변동성판이 같은 결론을 내는지 먼저 확인한다(§1).

[v31 감사] z() 의 이중 지연을 정정했다(아래). 그리고 §1 의 '두 점수 상관 0.918'
은 판정 근거로 약하다 — 점수가 닮아도 **문턱을 넘는 날의 집합**은 다를 수 있다.
실제 자카드 겹침은 61.7% 다. 정정본은 axis_macro3.py [A5].
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import sys
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import COST, rule_w

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def z(a, win=756, minp=252):
    """[v31 정정] shift(1) 을 뺐다.

    sim() 이 pos = w.shift(1) 로 이미 한 번 지연시킨다. 여기서 또 shift(1) 하면
    공포탐욕 신호만 **이틀 전 값**이 되어 낙폭 신호(하루 전)와 정렬이 어긋난다.
    미래훔쳐보기는 아니었지만(보수적 방향) 두 신호의 시점이 달랐다.
    정정 후 전구간 결과: -43.2% -> -53.3% (기각 결론은 동일, 더 나빠졌다).
    """
    s = pd.Series(np.asarray(a, dtype=float)).reset_index(drop=True)
    m = s.rolling(win, min_periods=minp).mean()
    sd = s.rolling(win, min_periods=minp).std()
    return ((s - m) / sd).fillna(0).values


def sim(D, w, defr=None, cost=COST, lag=1, lo=0, hi=None):
    """프로젝트 규약: pos = w.shift(1), 회전율 비례 비용."""
    n = len(D['idx']) if hi is None else hi
    sl = slice(lo, n)
    rr = D['qldr'][sl]
    dr = (D['schdr'] if defr is None else defr)[sl]
    wv = w[sl]
    pos = np.empty_like(wv)
    pos[:lag] = wv[0]
    pos[lag:] = wv[:-lag]
    r = np.nan_to_num(pos * rr + (1 - pos) * dr)
    r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * turn))


def stats(cum, ndays):
    cagr = cum[-1] ** (252 / ndays) - 1
    peak = np.maximum.accumulate(cum)
    m = (cum / peak - 1).min()
    return cum[-1], cagr, m, cagr / abs(m)


def fg_build(D, vix=None):
    """공포탐욕 대용 점수(0~100, 높을수록 탐욕). 전부 shift(1) — 미래 미참조."""
    px = D['px']
    idx = D['idx']
    r = px.pct_change().fillna(0)

    # ① 주가 모멘텀 (CNN 원본 정의: 지수 vs 125일 이평)
    mom = (px / px.rolling(125, min_periods=125).mean() - 1)

    # ② 변동성 — VIX 가 있으면 VIX, 없으면 21일 실현변동성 (부호 반전: 높을수록 공포)
    if vix is not None:
        vol = -pd.Series(vix, index=idx)
    else:
        vol = -r.rolling(21, min_periods=21).std()

    # ③ 안전자산 선호 — 주식 20일수익 (국채 대용이 긴 구간엔 없어 주식 단독)
    safe = px.pct_change(20)

    sc = 50 + 12.5 * (z(mom) + z(vol) + z(safe)) / np.sqrt(3)
    return np.clip(sc, 0, 100)


def run_case(D, fg, lo, label, thr=20):
    base_w = rule_w(D['ddv'], -0.16, -0.11)
    contra_w = np.where(fg <= thr, 1.0, base_w)
    n = len(D['idx']) - lo
    cb = sim(D, base_w, lo=lo)
    cc = sim(D, contra_w, lo=lo)
    mb, gb, db, kb = stats(cb, n)
    mc, gc, dc, kc = stats(cc, n)
    ov = int(((fg <= thr) & (base_w < 1.0))[lo:].sum())
    print(f"  {label}")
    print(f"    기존   : {mb:>12,.1f}배  CAGR {gb*100:6.2f}%  MDD {db*100:7.2f}%  Calmar {kb:.3f}")
    print(f"    역발상 : {mc:>12,.1f}배  CAGR {gc*100:6.2f}%  MDD {dc*100:7.2f}%  Calmar {kc:.3f}"
          f"   [{'개선' if mc > mb else '악화'} {(mc/mb-1)*100:+.1f}%]")
    print(f"    신호로 뒤집은 날 {ov}일 ({ov/n*100:.1f}%)")
    return dict(base=(mb, gb, db, kb), contra=(mc, gc, dc, kc))


def main():
    D = DF.build('chain')
    idx = D['idx']
    print(f"구간 {idx[0].date()} ~ {idx[-1].date()}  ({len(idx)}거래일)  방어=배당체인")

    # ---------------------------------------------------------- §1 VIX판 vs 실현변동성판
    print("\n[1] 대용치 타당성 — 1990- 공통구간에서 VIX판과 실현변동성판이 같은 결론인가")
    v = pd.read_csv('data/hist/yahoo_VIX.csv')
    v['Date'] = pd.to_datetime(v['Date'])
    vix = v.set_index('Date')['Close'].reindex(idx).ffill()
    lo90 = int(idx.searchsorted(pd.Timestamp('1990-01-02')))

    fg_vix = fg_build(D, vix=vix.values)
    fg_rv = fg_build(D, vix=None)
    both = ~np.isnan(fg_vix)
    print(f"  두 점수 상관 = {np.corrcoef(fg_vix[lo90:], fg_rv[lo90:])[0,1]:+.3f}")
    run_case(D, fg_vix, lo90, '1990- · VIX 사용')
    run_case(D, fg_rv, lo90, '1990- · 실현변동성 사용')

    # ---------------------------------------------------------- §2 긴 구간 본판정
    print("\n[2] 본판정 — 실현변동성판으로 구간을 늘려 간다")
    for label, start in [('전구간 1972-', None), ('1990-', '1990-01-02'),
                         ('2000- (닷컴 포함)', '2000-01-01'),
                         ('2007- (금융위기 포함)', '2007-01-01'),
                         ('2011- (axis_macro 구간)', '2011-10-25')]:
        lo = 0 if start is None else int(idx.searchsorted(pd.Timestamp(start)))
        run_case(D, fg_rv, lo, label)

    # ---------------------------------------------------------- §3 위기별 분해
    print("\n[3] 위기별 기여 — 어디서 벌고 어디서 잃는가")
    base_w = rule_w(D['ddv'], -0.16, -0.11)
    contra_w = np.where(fg_rv <= 20, 1.0, base_w)
    crises = {
        '1973 오일쇼크': ('1973-01-01', '1974-12-31'),
        '1987 블랙먼데이': ('1987-08-01', '1988-06-30'),
        '2000 닷컴': ('2000-03-01', '2002-10-31'),
        '2008 금융위기': ('2007-10-01', '2009-03-31'),
        '2020 COVID': ('2020-01-15', '2020-04-15'),
        '2022 긴축': ('2022-01-01', '2022-12-31'),
    }
    rb = sim(D, base_w)
    rc = sim(D, contra_w)
    for nm, (s, e) in crises.items():
        m = (idx >= s) & (idx <= e)
        if m.sum() < 20:
            continue
        i0, i1 = np.where(m)[0][[0, -1]]
        pb = rb[i1] / rb[i0] - 1
        pc = rc[i1] / rc[i0] - 1
        print(f"  {nm}: 기존 {pb*100:+7.2f}%  역발상 {pc*100:+7.2f}%  차이 {(pc-pb)*100:+7.2f}%p"
              f"  {'←손실' if pc < pb else ''}")

    # ---------------------------------------------------------- §4 문턱 스윕
    print("\n[4] 문턱 스윕 (전구간) — 고원인가 첨탑인가")
    print("   문턱   최종배수      CAGR     MDD    Calmar   기존대비")
    mb0 = sim(D, base_w)[-1]
    for thr in (5, 10, 15, 20, 25, 30, 35):
        cw = np.where(fg_rv <= thr, 1.0, base_w)
        c = sim(D, cw)
        mm, gg, dd, kk = stats(c, len(idx))
        print(f"   <{thr:2d}  {mm:>11,.1f}배  {gg*100:6.2f}%  {dd*100:7.2f}%  {kk:.3f}   {(mm/mb0-1)*100:+7.1f}%")

    # ---------------------------------------------------------- §5 블록 플라시보 (전구간)
    print("\n[5] 블록 플라시보 (전구간, 500회) — 뭉침을 유지한 채 신호구간을 옮긴다")
    rng = np.random.default_rng(42)
    mask = fg_rv <= 20
    seg = []
    i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            seg.append(j - i)
            i = j
        else:
            i += 1
    real = sim(D, contra_w)[-1]
    better = 0
    for _ in range(500):
        rm = np.zeros(len(mask), dtype=bool)
        for ln in seg:
            st = rng.integers(0, len(mask) - ln)
            rm[st:st + ln] = True
        rw = np.where(rm, 1.0, base_w)
        if sim(D, rw)[-1] >= real:
            better += 1
    print(f"  신호구간 {len(seg)}개  실제 {real:,.1f}배  무작위 중 같거나 나음 {better}/500 ({better/500*100:.1f}%)")

    # ---------------------------------------------------------- §6 워크포워드
    print("\n[6] 워크포워드 — 1972-1999 에서 정하고 2000- 에 적용")
    split = int(idx.searchsorted(pd.Timestamp('2000-01-01')))
    print("   IS(1972-1999) 최적 문턱 찾기:")
    best_thr, best_v = None, -1
    for thr in (5, 10, 15, 20, 25, 30, 35):
        cw = np.where(fg_rv <= thr, 1.0, base_w)
        v = sim(D, cw, hi=split)[-1]
        if v > best_v:
            best_v, best_thr = v, thr
    print(f"     최적 문턱 = <{best_thr}  (IS 배수 {best_v:,.1f})")
    cw = np.where(fg_rv <= best_thr, 1.0, base_w)
    oos_c = sim(D, cw, lo=split)
    oos_b = sim(D, base_w, lo=split)
    n_oos = len(idx) - split
    _, gc, dc, kc = stats(oos_c, n_oos)
    _, gb, db, kb = stats(oos_b, n_oos)
    print(f"   OOS(2000-): 기존 {oos_b[-1]:,.2f}배 CAGR {gb*100:.2f}% MDD {db*100:.2f}% Calmar {kb:.3f}")
    print(f"               역발상 {oos_c[-1]:,.2f}배 CAGR {gc*100:.2f}% MDD {dc*100:.2f}% Calmar {kc:.3f}"
          f"  [{(oos_c[-1]/oos_b[-1]-1)*100:+.1f}%]")

    print("\n[7] 판정은 전략_v30.md 에 기록")


if __name__ == '__main__':
    main()
