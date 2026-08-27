# -*- coding: utf-8 -*-
"""
[v51] 외부 정보원 — QQQ 밖의 시장 상태가 현행을 개선하는가

외부 제안(ChatGPT ver2). 핵심 질문:
  "QQQ 가격만 보지 않고 공포(VIX)·시장내부(breadth)·신용(credit)을 쓰면
   V자 반등을 놓치지 않으면서 falling-knife 재진입을 줄일 수 있는가?"

특히 §20 — v50 의 G 전략(DD 20일 +3%p 개선 시 조기복귀)은 적립식 꼬리를
크게 개선했지만 2000 닷컴에서 -41%p 를 잃었다(데드캣 바운스). **외부정보로
그 데드캣을 걸러낼 수 있는가**가 이 연구의 핵심이다.

[데이터 실태 — §11 을 그대로 적용한다. 보간하지 않는다]
  VIX            1990-01 ~     -> 4블록 중 2.5개
  VIX term       **없다**       -> ^VIX3M/^VIX9D 가 1행만 반환. **검증 불가**
  진짜 breadth    **없다**       -> A/D line·이평상회비율 무료 원천 없음. **검증 불가**
  breadth 대용    1970-01 ~     -> NYSE종합(NYA, 약 2천종목) vs NDX(100종목).
                                  좁은 지수와 넓은 지수의 괴리 = 시장 내부구조.
                                  **4블록 전부 커버한다.**
  러셀2000        1987-09 ~     -> 소형주 breadth 대용. 3블록
  VXN            2001-01 ~     -> 나스닥 변동성. 1.5블록
  신용(HYG/IEF)   2007-04 ~     -> 1.5블록. **4블록 검증 불가**
  금리(TNX/DTB3)  1954/1962 ~   -> 4블록 커버

[규약]
  · 진입은 현행 -16% 그대로. **복귀 timing 만** 외부정보로 바꾼다(§7/§8).
  · 외부 계열은 reindex+ffill 만 쓴다. bfill 금지 — 미래참조가 된다.
  · 신호는 i일 종가까지로 계산, 체결은 pos = w.shift(1) 로 i+1일.
  · 각 정보원은 **가용 구간에서만** 재고, 기준선도 같은 구간으로 자른다.
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
ENTER = -0.16
SEGS = [('1972-85', '1972-01-01', '1985-12-31'),
        ('1986-99', '1986-01-01', '1999-12-31'),
        ('2000-13', '2000-01-01', '2013-12-31'),
        ('2014-26', '2014-01-01', '2026-12-31')]


def load(path, idx):
    """외부 계열을 QQQ 달력에 맞춘다. **ffill 만** — bfill 은 미래참조."""
    d = pd.read_csv(path)
    c = [x for x in d.columns if x.lower() in ('date', 'observation_date')][0]
    v = [x for x in d.columns if x.lower() in ('close', 'adj close', 'value')]
    v = v[0] if v else d.columns[-1]
    s = pd.Series(pd.to_numeric(d[v], errors='coerce').values,
                  index=pd.to_datetime(d[c])).sort_index().dropna()
    s = s[~s.index.duplicated(keep='last')]
    first = s.index[0]
    out = s.reindex(idx, method='ffill')
    out[idx < first] = np.nan               # 데이터 이전 구간은 비운다
    return out.values, first


def curve(rk, dfr, w, cost=COST):
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * t)), pos


def dca(c, mstart, lo, hi, pay):
    m = mstart[(mstart > lo) & (mstart < hi)][:pay]
    return float(np.mean(c[hi - 1] / c[m])) if len(m) else np.nan


def chg(a, k):
    """k일 변화. 앞쪽은 NaN 유지 (미래참조 방지)."""
    o = np.full(len(a), np.nan)
    o[k:] = a[k:] - a[:-k]
    return o


def main():
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    ddv = np.asarray(D['ddv'], float)
    px = np.asarray(D['px'], float)
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]
    L = 20 * 252

    # ---------------------------------------------------------- 데이터 실태
    print("=" * 112)
    print("0. 데이터 실태 (§11 — 없는 건 없다고 적는다. 보간하지 않는다)")
    print("=" * 112)
    SRC = {}
    for key, path in (('VIX', 'data/hist/yahoo_VIX.csv'),
                      ('VXN', 'data/hist/yahoo_VXN.csv'),
                      ('NYA', 'data/hist/yahoo_NYA.csv'),
                      ('RUT', 'data/hist/yahoo_RUT.csv'),
                      ('GSPC', 'data/hist/yahoo_GSPC.csv'),
                      ('HYG', 'data/hist/yahoo_HYG.csv'),
                      ('IEF', 'data/hist/yahoo_IEF.csv'),
                      ('TNX', 'data/hist/yahoo_TNX.csv'),
                      ('DTB3', 'data/hist/fred_DTB3.csv')):
        if not _os.path.exists(path):
            print("  %-6s 파일 없음 -> 검증 불가" % key); continue
        v, first = load(path, idx)
        SRC[key] = v
        nb = sum(1 for _, a, b in SEGS
                 if first <= pd.Timestamp(b))
        print("  %-6s %s ~   유효 %5d일 / %d   4블록 커버 %d/4"
              % (key, first.date(), int(np.isfinite(v).sum()), N, nb))
    print("  %-6s **없음** — ^VIX3M/^VIX9D 가 1행만 반환. VIX term structure 검증 불가" % 'VIX3M')
    print("  %-6s **없음** — A/D line·이평상회비율의 무료 원천이 없다. 진짜 breadth 검증 불가" % 'A/D')
    print("           -> NYA(약 2천종목) vs NDX(100종목) 괴리를 **대용**으로 쓴다. 대용임을 명시한다.")
    print()

    # ---------------------------------------------------------- 후보
    base = rule_w(ddv, ENTER, ENTER)
    dd20 = chg(ddv, 20)
    G = np.where((ddv <= ENTER) & (dd20 > 0.03), 1.0, np.where(ddv > ENTER, 1.0, 0.0))

    cd = {'현행 -16/-16': (base, 1972), 'G (v50 최근접)': (G, 1972)}

    # --- A. VIX -------------------------------------------------------------
    if 'VIX' in SRC:
        vix = SRC['VIX']
        v5 = chg(vix, 5)
        vz = pd.Series(vix).rolling(756, min_periods=252).mean().values
        vsd = pd.Series(vix).rolling(756, min_periods=252).std().values
        vzz = (vix - vz) / vsd
        # A1 공포 완화로 복귀 (DD 회복 + VIX 5일 하락)
        cd['A1 현행 + VIX완화 복귀'] = (
            np.where((ddv <= ENTER) & (np.nan_to_num(v5, nan=1.) < -2.0), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1990)
        # A2 VIX 극단에서 매수 (공포 정점)
        cd['A2 현행 + VIX 2σ초과+하락'] = (
            np.where((ddv <= ENTER) & (np.nan_to_num(vzz, nan=0.) > 2.0)
                     & (np.nan_to_num(v5, nan=1.) < 0), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1990)
        # A3 G + VIX 확인 (데드캣 필터) — 이 연구의 핵심 가설
        cd['A3 G + VIX 완화확인'] = (
            np.where((ddv <= ENTER) & (dd20 > 0.03) & (np.nan_to_num(v5, nan=1.) < 0), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1990)
        cd['A4 G + VIX 30 미만'] = (
            np.where((ddv <= ENTER) & (dd20 > 0.03) & (np.nan_to_num(vix, nan=99.) < 30), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1990)

    # --- B'. Breadth 대용 (NYA vs NDX) --------------------------------------
    if 'NYA' in SRC:
        nya = SRC['NYA']
        nya_dd = nya / pd.Series(nya).rolling(252, min_periods=60).max().values - 1
        b20 = chg(np.nan_to_num(nya_dd, nan=0.), 20)
        cd["B1 현행 + 시장전체 낙폭개선"] = (
            np.where((ddv <= ENTER) & (np.nan_to_num(b20, nan=-1.) > 0.02), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1972)
        # B2 G + breadth 확인 (데드캣 필터)
        cd["B2 G + 시장전체도 회복중"] = (
            np.where((ddv <= ENTER) & (dd20 > 0.03)
                     & (np.nan_to_num(b20, nan=-1.) > 0), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1972)
        # B3 divergence — 나스닥만 빠지고 시장은 견조하면 얕은 조정
        dv = np.nan_to_num(nya_dd, nan=0.) - ddv
        cd["B3 나스닥만 빠짐(괴리>8%p) 조기복귀"] = (
            np.where((ddv <= ENTER) & (dv > 0.08), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1972)

    # --- C. VIX + Breadth ---------------------------------------------------
    if 'VIX' in SRC and 'NYA' in SRC:
        cd["C1 G + VIX완화 + 시장회복"] = (
            np.where((ddv <= ENTER) & (dd20 > 0.03)
                     & (np.nan_to_num(chg(SRC['VIX'], 5), nan=1.) < 0)
                     & (np.nan_to_num(b20, nan=-1.) > 0), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1990)

    # --- D. Credit (HYG/IEF) -----------------------------------------------
    if 'HYG' in SRC and 'IEF' in SRC:
        cr = np.log(SRC['HYG'] / SRC['IEF'])         # 오르면 신용 안정
        c20 = chg(cr, 20)
        cd["D1 G + 신용 안정확인"] = (
            np.where((ddv <= ENTER) & (dd20 > 0.03) & (np.nan_to_num(c20, nan=-1.) > 0), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 2007)

    # --- F. Cross-asset -----------------------------------------------------
    if 'GSPC' in SRC:
        sp = SRC['GSPC']
        sp_dd = sp / pd.Series(sp).rolling(252, min_periods=60).max().values - 1
        cd["F1 G + S&P도 회복중"] = (
            np.where((ddv <= ENTER) & (dd20 > 0.03)
                     & (np.nan_to_num(chg(np.nan_to_num(sp_dd, nan=0.), 20), nan=-1.) > 0), 1.0,
                     np.where(ddv > ENTER, 1.0, 0.0)), 1972)

    # ---------------------------------------------------------- 평가
    print("=" * 112)
    print("1. 결과 — 각 후보는 **자기 데이터 가용구간**에서, 기준선도 같은 구간으로 잘라 비교")
    print("=" * 112)
    C = {nm: curve(rk, dfr, w) for nm, (w, _) in cd.items()}
    cbase, _ = C['현행 -16/-16']

    def evalr(nm, y0):
        c, pos = C[nm]
        lo0 = int(idx.searchsorted(pd.Timestamp('%d-01-01' % y0)))
        st = [s for s in range(lo0, N - L, 126)]
        isa = np.array([dca(c, mstart, s, s + L, 60) for s in st])
        per = np.array([dca(c, mstart, s, s + L, 10 ** 9) for s in st])
        seg = c[lo0:]
        m = float((seg / np.maximum.accumulate(seg) - 1).min())
        blk = []
        for _, a, b in SEGS:
            lo = int(idx.searchsorted(pd.Timestamp(a)))
            hi = int(idx.searchsorted(pd.Timestamp(b), side='right'))
            if lo < lo0:
                blk.append(np.nan); continue
            blk.append(dca(c, mstart, lo, hi, 10 ** 9) / dca(cbase, mstart, lo, hi, 10 ** 9) - 1)
        return dict(isa=isa, per=per, mdd=m, blk=np.array(blk), st=st,
                    sw=int((np.abs(np.diff(pos)) > 1e-9).sum()), y0=y0)

    R = {nm: evalr(nm, y0) for nm, (_, y0) in cd.items()}
    BASE = {}                       # 시작연도별 기준선 (같은 구간끼리 비교해야 한다)
    for _, y0 in cd.values():
        if y0 not in BASE:
            BASE[y0] = evalr('현행 -16/-16', y0)

    print("  괄호 안 = **같은 구간으로 자른 현행 기준선**. 구간이 다르면 절대값 비교 금지(§23).")
    print()
    print("  %-30s%6s%16s%15s%14s%15s%9s%7s%6s"
          % ('전략', '시작', 'ISA중앙(현행)', 'P20(현행)', 'P5(현행)',
             '영구P5(현행)', 'MDD', '블록', '전환'))
    for nm in cd:
        r = R[nm]
        b = BASE[r['y0']]
        ok = int(np.nansum(r['blk'] > 0))
        tot = int(np.isfinite(r['blk']).sum())
        if len(r['isa']) < 5:
            print("  %-30s%6d   **20년 창 %d개 — 검증 불가**(§11 원칙 B). 전환 %d회"
                  % (nm, r['y0'], len(r['isa']), r['sw']))
            continue
        f = lambda v, w: '%7.1f(%5.1f)' % (v, w)
        print("  %-30s%6d%16s%15s%14s%15s%8.1f%%%5d/%d%6d"
              % (nm, r['y0'],
                 f(np.median(r['isa']), np.median(b['isa'])),
                 f(np.percentile(r['isa'], 20), np.percentile(b['isa'], 20)),
                 f(np.percentile(r['isa'], 5), np.percentile(b['isa'], 5)),
                 f(np.percentile(r['per'], 5), np.percentile(b['per'], 5)),
                 r['mdd'] * 100, ok, tot, r['sw']))
    print()
    print("  ※ '블록 n/m' 의 m 이 4 미만이면 **4블록 검증 불가**(§11 원칙 B). 확대해석 금지.")
    print()

    # ---------------------------------------------------------- 관문
    print("=" * 112)
    print("2. 6관문 (각자의 가용구간 기준선과 비교, 완화 없음)")
    print("=" * 112)
    passed = []
    for nm in cd:
        if nm.startswith('현행'):
            continue
        r = R[nm]
        if len(r['isa']) < 5:
            print("  %-30s  20년 창 %d개 — **관문 적용 불가**" % (nm, len(r['isa'])))
            continue
        b = BASE[r['y0']]
        g = [np.median(r['isa']) > np.median(b['isa']),
             np.percentile(r['isa'], 20) > np.percentile(b['isa'], 20),
             np.percentile(r['isa'], 5) > np.percentile(b['isa'], 5),
             np.median(r['per']) > np.median(b['per']),
             int(np.isfinite(r['blk']).sum()) == 4 and int(np.nansum(r['blk'] > 0)) >= 3,
             r['mdd'] >= b['mdd']]
        print("  %-30s %d/6  %s   %s" % (nm, sum(g),
              ''.join('O' if x else 'X' for x in g),
              '' if int(np.isfinite(r['blk']).sum()) == 4 else '(4블록 검증 불가)'))
        if all(g):
            passed.append(nm)
    print()
    print("  G1 ISA중앙 · G2 P20 · G3 P5 · G4 영구중앙 · G5 4블록 3/4 · G6 MDD 비악화")
    print()

    # ---------------------------------------------------------- 데드캣 사례
    print("=" * 112)
    print("3. §9/§20 핵심 — 2000 닷컴 데드캣을 외부정보가 걸러냈는가")
    print("=" * 112)
    lo = int(idx.searchsorted(pd.Timestamp('2000-03-01')))
    hi = int(idx.searchsorted(pd.Timestamp('2003-12-31'), side='right'))
    print("  %-30s%12s%12s" % ('전략', '2000-03~2003', '현행 대비'))
    v0 = cbase[hi - 1] / cbase[lo] - 1
    for nm in cd:
        if R[nm]['y0'] > 2000:
            continue
        c = C[nm][0]
        v = c[hi - 1] / c[lo] - 1
        print("  %-30s%11.1f%%%11.1f%%p" % (nm, v * 100, (v - v0) * 100))
    print()

    print("=" * 112)
    print(verdict('외부 정보원이 현행을 개선하는가', [
        ('6관문 전부 통과한 후보가 있다', len(passed) > 0,
         '%d개 / 후보 %d개' % (len(passed), len(cd) - 2)),
    ])['text'])


if __name__ == '__main__':
    main()
