# -*- coding: utf-8 -*-
"""
[v54] 외부정보 2차 — 상태변수 방식. SPY 계열 전면 제외.

핵심 질문(§0): QQQ 가격만 보는 것보다 공포·변동성구조·채권·신용·시장내부를 쓰면
**V자 반등 포착은 유지하면서 falling-knife 재진입만 줄일 수 있는가?**

[설계 원칙 — 제안 §12/§13 그대로]
  · 진입은 현행 -16% 유지. **복귀 조건만** 외부정보로 바꾼다.
  · 외부정보는 **매일 게이트가 아니라 도피 진입 시 한 번 읽는 상태변수**로 쓴다.
    (v51 에서 매일 게이트가 전환 80 -> 218회를 만들었다)
  · 상태는 정해진 **해제 사건**으로만 바뀐다(latch).
  · SPY·QQQ/SPY 상대강도는 **어떤 형태로도 쓰지 않는다**.

[데이터 실태 — §15. 보간·합성 금지]
  전략군      원천                 기간          4블록
  A VIX      yahoo_VIX          1990-01~      2.5/4  (부분)
  B Breadth  NYSE종합 NYA        1970-01~      **4/4**   (대용. 진짜 A/D 는 없다)
             러셀2000 RUT        1987-09~      3/4
  C A+B      교집합              1990-01~      2.5/4
  D Treasury TNX(10년) 1962~ · DTB3(3개월) 1954~   **4/4**
  E Credit   HYG/IEF            2007-04~      **20년 창 0개 -> 건너뛴다**(v51 확인)
  F Cross    금 lbma 1968~ · 국채 · VIX          부분
  G RV구조   QQQ 종가에서 산출     1972~        **4/4**
  H Dispersion  **종목 단위 데이터 없음 -> 건너뛴다**(§10 조건 미충족)
  I Overnight   OHLC 가 1999-03~ 뿐 -> **1.5블록. 참고로만**

[관문] G1~G6 + G7 파라미터 + G8 비용 + G9 시작일 + G10 미래참조 + **G11 집중도**
       G11 은 research_kit.concentration / leave_one_crisis_out 으로 강제한다.
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
from research_kit import verdict, concentration, leave_one_crisis_out

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
L = 20 * 252


def load(path, idx):
    """외부 계열을 QQQ 달력에 맞춘다. ffill 만 — bfill 은 미래참조."""
    d = pd.read_csv(path)
    c = [x for x in d.columns if x.lower() in ('date', 'observation_date')][0]
    vv = [x for x in d.columns if x.lower() in ('close', 'adj close', 'value')]
    v = vv[0] if vv else d.columns[-1]        # FRED 는 열 이름이 계열코드다
    s = pd.Series(pd.to_numeric(d[v], errors='coerce').values,
                  index=pd.to_datetime(d[c])).sort_index().dropna()
    s = s[~s.index.duplicated(keep='last')]
    o = s.reindex(idx, method='ffill')
    o[idx < s.index[0]] = np.nan
    return o.values, s.index[0]


def zsc(a, win=756, minp=252):
    s = pd.Series(a)
    return ((a - s.rolling(win, min_periods=minp).mean().values)
            / s.rolling(win, min_periods=minp).std().values)


def chg(a, k):
    o = np.full(len(a), np.nan); o[k:] = a[k:] - a[:-k]; return o


def state_latch(ddv, enter_z, release=None, T=0.0, hold=0):
    """[§13] 도피 진입 시 상태를 한 번 읽고 latch. 해제 사건으로만 바뀐다.

    enter_z  : 진입 시 읽는 상태값. > T 면 '스트레스' -> 현행대로 빨리 복귀
                                  <= T 면 '조용함'   -> LATE 까지 기다린다
    release  : 스트레스 해제 사건(불리언 배열). 주면 조용함->현행 으로 완화한다
    hold     : 최소 유지일 (0 이면 도피 끝까지)
    """
    n = len(ddv)
    w = np.empty(n); cur = 1.0
    line = ENTER; since = 0
    for i in range(n):
        if ddv[i] <= ENTER:
            if cur >= 1.0:
                line = ENTER if np.nan_to_num(enter_z[i], nan=9.0) > T else LATE
                since = 0
            cur = 0.0
        elif cur < 1.0:
            since += 1
            if (release is not None and line == LATE
                    and since >= hold and bool(release[i])):
                line = ENTER                       # 해제 사건 -> 현행 복귀선으로
            if ddv[i] > line:
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
        blk = []
        for _, a, b in SEGS:
            lo = int(idx.searchsorted(pd.Timestamp(a)))
            hi = int(idx.searchsorted(pd.Timestamp(b), side='right'))
            blk.append(np.nan if lo < lo0 else dca(c, lo, hi))
        return dict(median=float(np.median(isa)), p20=float(np.percentile(isa, 20)),
                    p5=float(np.percentile(isa, 5)),
                    pm=float(np.median(per)), pp20=float(np.percentile(per, 20)),
                    pp5=float(np.percentile(per, 5)),
                    mdd=float((seg / np.maximum.accumulate(seg) - 1).min()),
                    sw=int((np.abs(np.diff(pos[lo0:])) > 1e-9).sum()),
                    blk=np.array(blk), c=c, w=w, y0=y0)

    # ---------------------------------------------------------- 외부 계열
    print("=" * 116)
    print("0. 데이터 실태 (§15 — 보간·합성 금지. 없으면 건너뛴다)")
    print("=" * 116)
    SRC = {}
    for key, path in (('VIX', 'data/hist/yahoo_VIX.csv'),
                      ('NYA', 'data/hist/yahoo_NYA.csv'),
                      ('RUT', 'data/hist/yahoo_RUT.csv'),
                      ('TNX', 'data/hist/yahoo_TNX.csv'),
                      ('DTB3', 'data/hist/fred_DTB3.csv'),
                      ('GOLD', 'data/hist/lbma_gold_pm.csv')):
        v, first = load(path, idx)
        SRC[key] = v
        nb = sum(1 for _, a, b in SEGS if first <= pd.Timestamp(a))
        print("  %-6s %s ~   4블록 %d/4" % (key, first.date(), nb))
    print("  %-6s 종목 단위 데이터 없음 -> **전략군 H 건너뜀**" % 'DISP')
    print("  %-6s HYG 2007-04~ -> 20년 창 0개 -> **전략군 E 건너뜀**(v51 확인)" % 'CREDIT')
    print("  %-6s OHLC 가 1999-03~ 뿐 -> **전략군 I 는 4블록 불가**" % 'OVNT')
    print()

    # 상태 변수들
    vix, nya, rut = SRC['VIX'], SRC['NYA'], SRC['RUT']
    tnx, tb3, gold = SRC['TNX'], SRC['DTB3'], SRC['GOLD']
    rv21 = S.pct_change().rolling(21, min_periods=21).std().values
    rv126 = S.pct_change().rolling(126, min_periods=126).std().values

    cd = {'현행 -16/-16': (rule_w(ddv, ENTER, ENTER), 1972)}

    # ---- A. VIX shock + persistence (1990~) --------------------------------
    vz = zsc(vix)
    v5 = chg(vix, 5)
    for T in (0.0, 0.5, 1.0):
        cd['A VIX z>%.1f 상태' % T] = (state_latch(ddv, vz, None, T), 1990)
    # A3 해제 사건: VIX 가 진입 대비 정상화 -> 상태를 푼다
    rel_vix = np.nan_to_num(vz, nan=9.) < 0.0
    for hold in (5, 20):
        cd['A3 VIX z>0 + %d일후 정상화해제' % hold] = (
            state_latch(ddv, vz, rel_vix, 0.0, hold), 1990)

    # ---- B. Breadth 대용 (NYA·RUT, SPY 아님) — 1970~ ----------------------
    nya_dd = nya / pd.Series(nya).rolling(252, min_periods=60).max().values - 1
    b20 = chg(np.nan_to_num(nya_dd, nan=0.), 20)
    # 진입 시 '시장 전체도 무너졌나' 를 읽는다
    bz = zsc(np.nan_to_num(nya_dd, nan=0.))
    for T in (-0.5, 0.0, 0.5):
        cd['B 시장전체 낙폭z>%.1f 상태' % T] = (state_latch(ddv, bz, None, T), 1972)
    rel_b = np.nan_to_num(b20, nan=-1.) > 0.02          # 시장 전체가 회복 중
    cd['B5 조용함 + 시장회복시 해제'] = (
        state_latch(ddv, bz, rel_b, 0.0, 10), 1972)

    # ---- C. VIX + Breadth (1990~) -----------------------------------------
    both = np.where(np.isfinite(vz) & np.isfinite(bz), vz + bz, np.nan)
    for T in (0.0, 0.5):
        cd['C VIX+시장 합산z>%.1f' % T] = (state_latch(ddv, both, None, T), 1990)
    cd['C2 VIX상태 + 시장회복해제'] = (
        state_latch(ddv, vz, rel_b, 0.0, 10), 1990)

    # ---- D. Treasury flight-to-safety (1962~) — 4블록 전부 -----------------
    # 도피 진입 시 국채가 오르고 있으면(=수익률 하락) 전형적 안전자산 도피
    ty20 = chg(tnx, 20)                                  # +면 금리 상승 = 국채 하락
    tsz = zsc(np.nan_to_num(ty20, nan=0.))
    for T in (-0.5, 0.0, 0.5):
        cd['D 금리20일변화z>%.1f' % T] = (state_latch(ddv, tsz, None, T), 1972)
    # 장단기차 (10년 - 3개월)
    curve_s = tnx - tb3
    cz = zsc(curve_s)
    for T in (0.0, -0.5):
        cd['D2 장단기차z>%.1f' % T] = (state_latch(ddv, cz, None, T), 1972)
    # D4 해제: 금리가 다시 정상화
    cd['D4 금리충격 + 정상화해제'] = (
        state_latch(ddv, tsz, np.nan_to_num(tsz, nan=9.) < 0, 0.0, 10), 1972)

    # ---- F. Cross-asset (금 + 국채 + VIX, SPY 없음) ------------------------
    g20 = pd.Series(gold).pct_change(20).values
    gz = zsc(np.nan_to_num(g20, nan=0.))
    stress = np.where(np.isfinite(gz) & np.isfinite(tsz), gz - tsz, np.nan)
    for T in (0.0, 0.5):
        cd['F 금-금리 스트레스z>%.1f' % T] = (state_latch(ddv, stress, None, T), 1972)

    # ---- G. RV **구조** (v53 의 수준 규칙과 다르다) — 1972~ -----------------
    ratio = np.where(rv126 > 0, rv21 / rv126, np.nan)    # 단기/장기 비율
    rz = zsc(np.nan_to_num(ratio, nan=1.))
    for T in (0.0, 0.5, 1.0):
        cd['G1 단기/장기 RV비율z>%.1f' % T] = (state_latch(ddv, rz, None, T), 1972)
    spd = chg(np.nan_to_num(rv21, nan=0.), 10)           # RV 급등 속도
    sz = zsc(np.nan_to_num(spd, nan=0.))
    for T in (0.0, 0.5):
        cd['G2 RV급등속도z>%.1f' % T] = (state_latch(ddv, sz, None, T), 1972)
    # G3 RV 정점 통과로 해제
    cd['G3 RV구조 + 정점통과해제'] = (
        state_latch(ddv, rz, np.nan_to_num(chg(np.nan_to_num(rv21, nan=0.), 10),
                                           nan=1.) < 0, 0.0, 10), 1972)

    # ---------------------------------------------------------- 평가
    R, BASE = {}, {}
    for nm, (w, y0) in cd.items():
        R[nm] = ev(w, y0=y0)
        if y0 not in BASE:
            BASE[y0] = ev(cd['현행 -16/-16'][0], y0=y0)

    print("=" * 116)
    print("1. 결과 — 각 후보는 자기 가용구간, 기준선도 같은 구간으로 잘라 비교")
    print("=" * 116)
    print("  %-28s%6s%15s%14s%13s%13s%9s%7s%7s"
          % ('전략', '시작', 'ISA중앙(현행)', 'P20(현행)', 'P5(현행)', '영구P5(현행)',
             'MDD', '블록', '전환'))
    for nm in cd:
        r, b = R[nm], BASE[R[nm]['y0']]
        ok = int(np.nansum(r['blk'] > b['blk']))
        tot = int(np.isfinite(r['blk']).sum())
        f = lambda x, y: '%7.1f(%5.1f)' % (x, y)
        print("  %-28s%6d%15s%14s%13s%13s%8.1f%%%5d/%d%7d"
              % (nm, r['y0'], f(r['median'], b['median']), f(r['p20'], b['p20']),
                 f(r['p5'], b['p5']), f(r['pp5'], b['pp5']),
                 r['mdd'] * 100, ok, tot, r['sw']))
    print()
    print("  ※ 블록 n/m 의 m<4 이면 **4블록 검증 불가**(§15). 확대해석 금지.")
    print()

    # ---------------------------------------------------------- 관문
    print("=" * 116)
    print("2. G1~G6 (완화 없음)")
    print("=" * 116)
    surv = []
    for nm in cd:
        if nm.startswith('현행'):
            continue
        r, b = R[nm], BASE[R[nm]['y0']]
        g = [r['median'] > b['median'], r['p20'] > b['p20'], r['p5'] > b['p5'],
             r['pm'] > b['pm'],
             int(np.isfinite(r['blk']).sum()) == 4
             and int(np.nansum(r['blk'] > b['blk'])) >= 3,
             r['mdd'] >= b['mdd']]
        if sum(g) >= 4:
            print("  %-28s %d/6  %s%s" % (nm, sum(g), ''.join('O' if x else 'X' for x in g),
                  '' if int(np.isfinite(r['blk']).sum()) == 4 else '   (4블록 불가)'))
        if all(g):
            surv.append(nm)
    print()
    print("  **G1~G6 전부 통과: %s**" % (', '.join(surv) if surv else '없음'))
    print()
    return R, BASE, cd, surv, idx, N, rk, dfr, mstart, ev


if __name__ == '__main__':
    out = main()
    R, BASE, cd, surv, idx, N, rk, dfr, mstart, ev = out
    print("=" * 116)
    if not surv:
        print(verdict('외부정보 2차 — 현행을 대체하는 후보가 있는가', [
            ('G1~G6 를 전부 통과한 후보가 있다', False, '0개 / 후보 %d개' % (len(cd) - 1)),
        ])['text'])
        print()
        print("  -> G11(집중도)까지 갈 후보가 없다. **현행 -16/-16 유지.**")
    else:
        print("  G11 집중도 검사로 넘어갈 후보: %s" % ', '.join(surv))
        print("  (research/axis_gate11.py 와 같은 방식으로 개별 검증 필요)")
