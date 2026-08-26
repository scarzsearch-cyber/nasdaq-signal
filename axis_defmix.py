# -*- coding: utf-8 -*-
"""
[v23 축4] 방어자산을 위기 유형별로 분산한다 — 국채 · 금

문제의식 (전략_v22.md §5.1):
  현재 MDD -68.7% 는 전부 방어자산 탓이다. 2008년에 DVY 가 -59.7% 로 SPY(-54.2%)보다
  더 빠졌다(v21 §2.3). 그런데 v21 이 시험한 방어자산 4종은 전부 주식 계열이었다.
  v21 은 "방어자산의 유효성은 위기의 성격에 달려 있다"고 적고도 다음 단계인
  "성격이 다른 것을 섞자"를 하지 않았다.

사용자 제약 (2026-08-26):
  - 국내 상장 ETF 만. ISA 또는 일반 주식계좌. 미국 직투는 안 한다.
  - 방어자산 매도 -> QLD 매수가 같은 날 즉시 되어야 한다.
  -> 국내에 대응 상품이 있는 것만 후보로 삼는다(hist_defasset.KR_ETF).

출력 순서
  1) 성분 진단        각 방어자산의 CAGR/변동성/MDD + 위기 7종별 성과
  2) 상관             성분 간, 그리고 QQQ 와의 상관 (위기 중 상관 포함)
  3) 본 판정          A/B x 방어자산 후보 12종, 1972-2026 / 2000-2026
  4) MDD 분해         MDD 가 언제 어디서 나오는가
  5) 재조정 규약      일간재조정 vs 도피구간 내 보유(실전)
  6) 검증관문         거래비용 / 체결지연 / 구간 안정성 / 롤링
  7) 원화 실전        환노출 vs 환헤지 — 국내 상품 구조 반영
  8) 국내 실물 ETF    실제 KRX 상품으로 겹침 구간 검증

실행:  python axis_defmix.py
"""
import numpy as np
import pandas as pd

import hist_data as H
import hist_defasset as DA
import hist_defensive as DF
import hist_korea as K
from reentry_lib import met, rolling_stats
from axis_lib import COST, rule_w, check

TYX_START = pd.Timestamp('1977-02-15')      # 30년 금리 고시 시작
GOLD_START = pd.Timestamp('1968-04-01')

# 국내 상장 대응 상품이 있는 조합만 후보로 둔다.
CANDS = [
    ('배당100 (현행 v21)',        dict(div=1.0)),
    ('T-bill100 (참고)',          None),
    ('국채10Y 100',               dict(ust10=1.0)),
    ('금100',                     dict(gold=1.0)),
    ('배당50 국채30 금20',        dict(div=0.5, ust10=0.3, gold=0.2)),
    ('배당40 국채5Y40 금20 [국내]', dict(div=0.4, ust5=0.4, gold=0.2)),
    ('배당50 국채5Y30 금20 [국내]', dict(div=0.5, ust5=0.3, gold=0.2)),
    ('배당34 국채5Y33 금33 [국내]', dict(div=0.34, ust5=0.33, gold=0.33)),
    ('배당40 국채40 금20',        dict(div=0.4, ust10=0.4, gold=0.2)),
    ('배당34 국채33 금33',        dict(div=0.34, ust10=0.33, gold=0.33)),
    ('배당70 금30',               dict(div=0.7, gold=0.3)),
    ('배당60 금40',               dict(div=0.6, gold=0.4)),
    ('배당50 금50',               dict(div=0.5, gold=0.5)),
    ('배당50 국채50',             dict(div=0.5, ust10=0.5)),
    ('국채50 금50 (주식0)',       dict(ust10=0.5, gold=0.5)),
    ('배당60 국채20 금20',        dict(div=0.6, ust10=0.2, gold=0.2)),
    ('배당25 국채25 금25 Tb25',   dict(div=0.25, ust10=0.25, gold=0.25, tbill=0.25)),
]

CRISES = [('73-74 오일', '1973-01-11', '1974-10-03'),
          ('1980-82 인플레', '1980-11-28', '1982-08-12'),
          ('87 블랙먼데이', '1987-08-25', '1987-12-04'),
          ('닷컴 00-02', '2000-03-10', '2002-10-09'),
          ('GFC 07-09', '2007-10-31', '2009-03-09'),
          ('코로나 20', '2020-02-19', '2020-03-23'),
          ('2022 베어', '2022-01-03', '2022-10-12')]


# ---------------------------------------------------------------- 재료
def materials(D):
    idx = D['idx']
    base = D['schdr']                                   # 배당체인 (v21 자율규약2)
    comp = {'div': np.asarray(base, dtype=float),
            'ust5': DA.ust_tr(idx, 5, 'TNX'),        # 국내 미국채10년선물 ETF 의 실효 사양
            'ust10': DA.ust_tr(idx, 10, 'TNX'),
            'ust20': DA.ust_tr(idx, 20, 'TYX'),       # ACE 미국30년국채액티브(H) 의 실효 사양
            'ust30': DA.ust_tr(idx, 30, 'TYX'),
            'gold': DA.gold_r(idx),
            'tbill': H.tbill_daily(idx)}
    for k in ('ust20', 'ust30'):
        comp[k][idx < TYX_START] = np.nan                # 30년 고시 이전은 쓰지 않는다
    return comp


def mix_monthly_from(parts, weights, idx, cost=0.0005):
    """이미 만들어진 성분 수익률들로 월초 재조정 바스켓을 만든다(§5 의 실전 규약)."""
    tot = float(sum(weights.values()))
    frac = {k: v / tot for k, v in weights.items() if v > 0}
    per = pd.Series(idx).dt.to_period('M').values
    n = len(idx)
    out = np.zeros(n)
    b = dict(frac)
    for i in range(n):
        prev = sum(b.values())              # [v27 정정] 비용 차감 **전** 값 (hist_defasset 참고)
        if i > 0 and per[i] != per[i - 1]:
            v = prev
            turn = sum(abs(b[k] / v - frac[k]) for k in frac) / 2.0
            v *= (1 - cost * 2 * turn)
            b = {k: v * frac[k] for k in frac}
        for k in frac:
            b[k] *= (1 + np.nan_to_num(parts[k][i]))
        out[i] = sum(b.values()) / prev - 1.0
    out[0] = 0.0
    return out


def mix_r(comp, weights):
    """일간 재조정 바스켓."""
    tot = float(sum(weights.values()))
    r = np.zeros(len(comp['div']))
    for k, w in weights.items():
        if w > 0:
            r = r + (w / tot) * np.nan_to_num(comp[k])
    return r


# ---------------------------------------------------------------- 엔진
def sim_def(D, w, defr, riskr=None, cost=COST, lag=1, start=None, end=None):
    """방어자산 수익률 배열을 갈아끼우는 거치식 시뮬레이터 (axis_lib.sim 과 동치)."""
    idx = D['idx']
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    sl = slice(lo, hi)
    rr = D['qldr'] if riskr is None else riskr
    wv = w[sl]
    pos = np.empty_like(wv)
    pos[:lag] = wv[0]
    pos[lag:] = wv[:-lag]
    r = np.nan_to_num(pos * rr[sl] + (1 - pos) * defr[sl])
    r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return pd.Series(np.cumprod((1 + r) * (1 - cost * turn)), index=idx[sl])


def sim_hold(D, w, comp, weights, riskr=None, cost=COST, lag=1, start=None, end=None,
             rebal=None, rebal_cost=0.0005):
    """[실전 규약] 도피 시점에 비율대로 사서 들고 있는다.

    rebal : None  = 복귀까지 안 건드림 (가장 보수적)
            'M'/'Q' = 도피 구간 안에서 월/분기 리밸런싱 (실제로 하게 되는 것)

    [규약 정합] 하루의 순서는 sim_def / reentry_lib.run 과 정확히 같다:
      ① 전일 신호(w[i-lag])대로 당일 시작에 포지션을 맞추고(전환비용)
      ② 그 포지션으로 당일 수익을 받는다.
    단일자산 바스켓이면 sim_def 와 오차 0 이어야 한다(check_hold() 가 검산).
    """
    idx = D['idx']
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    rr = D['qldr'] if riskr is None else riskr
    keys = [k for k, v in weights.items() if v > 0]
    tot = float(sum(weights.values()))
    frac = {k: weights[k] / tot for k in keys}
    R = {k: np.nan_to_num(comp[k]) for k in keys}
    per = None if rebal is None else pd.Series(idx).dt.to_period(rebal).values

    V = 1.0
    prev = w[lo]
    buckets = None if prev >= 1 else {k: V * frac[k] for k in keys}
    out = []
    for i in range(lo, hi):
        pos = w[i - lag] if i - lag >= lo else w[lo]

        if pos != prev:                                   # ① 당일 시작에 전환
            V *= (1 - cost)
            buckets = None if pos >= 1 else {k: V * frac[k] for k in keys}
            prev = pos
        elif buckets is not None and per is not None and i > lo and per[i] != per[i - 1]:
            turn = sum(abs(buckets[k] / V - frac[k]) for k in keys) / 2.0
            V *= (1 - rebal_cost * 2 * turn)              # 구간 내 리밸런싱
            buckets = {k: V * frac[k] for k in keys}

        if i > lo:                                        # ② 당일 수익
            if buckets is None:                           #   (첫날 수익은 0 — sim_def 규약)
                V *= (1 + np.nan_to_num(rr[i]))
            else:
                for k in keys:
                    buckets[k] *= (1 + R[k][i])
                V = sum(buckets.values())
        out.append(V)
    return pd.Series(out, index=idx[lo:hi])


def check_hold(D, comp):
    """sim_hold 규약 검산 — 단일자산이면 sim_def 와 같아야 한다."""
    wB = rule_w(D['ddv'], -0.16, -0.16)
    ok = True
    for s in (None, '2000-01-03'):
        for k in ('div', 'ust10', 'gold'):
            a = sim_hold(D, wB, comp, {k: 1.0}, start=s, rebal='M').iloc[-1]
            b = sim_def(D, wB, np.nan_to_num(comp[k]), start=s).iloc[-1]
            e = abs(a / b - 1)
            ok = ok and e < 1e-10
            print('검산 sim_hold %-6s %-12s %14s vs %14s  오차 %.1e'
                  % (k, s or '1972-', format(a, ',.2f'), format(b, ',.2f'), e))
    return ok


# ---------------------------------------------------------------- 1) 진단
def diagnose(D, comp):
    idx = D['idx']
    print('\n===== 1) 방어자산 성분 진단 (1972-02 ~ 2026-08) =====')
    print('%-14s %8s %8s %9s %10s %s' % ('성분', 'CAGR', '변동성', 'MDD', 'QQQ상관', '유효구간'))
    qr = np.nan_to_num(D['px'].pct_change().values)
    for k in ('div', 'tbill', 'ust10', 'ust30', 'gold'):
        r = comp[k]
        ok = ~np.isnan(r)
        rr = r[ok]
        ii = idx[ok]
        c = pd.Series(np.cumprod(1 + rr), index=ii)
        yrs = (ii[-1] - ii[0]).days / 365.25
        cor = float(np.corrcoef(rr[1:], qr[ok][1:])[0, 1])
        print('%-14s %7.2f%% %7.2f%% %8.2f%% %9.3f  %s ~' %
              (k, (c.iloc[-1] ** (1 / yrs) - 1) * 100, rr.std() * np.sqrt(252) * 100,
               (c / c.cummax() - 1).min() * 100, cor, ii[0].date()))

    print('\n----- 위기 7종 구간수익 (%) — 이것이 "위기 유형별 상보성"의 실측 -----')
    print('%-16s %9s %9s %9s %9s %9s %9s' %
          ('위기', 'QQQ', '배당', 'T-bill', '국채10Y', '국채30Y', '금'))
    for nm, s, e in CRISES:
        lo, hi = idx.searchsorted(pd.Timestamp(s)), idx.searchsorted(pd.Timestamp(e), side='right')
        cells = []
        for k in ('div', 'tbill', 'ust10', 'ust30', 'gold'):
            r = comp[k][lo:hi]
            cells.append(np.nan if np.isnan(r).any() else (np.prod(1 + r) - 1) * 100)
        q = (np.prod(1 + qr[lo:hi]) - 1) * 100
        print('%-16s %8.1f%%' % (nm, q) +
              ''.join('%9s' % ('  -  ' if np.isnan(v) else '%8.1f%%' % v) for v in cells))


def correlations(D, comp):
    idx = D['idx']
    qr = np.nan_to_num(D['px'].pct_change().values)
    worst = np.argsort(qr)[:int(len(qr) * 0.05)]         # QQQ 최악 5% 날
    print('\n===== 2) 상관 — 평상시 vs QQQ 최악 5%일 =====')
    print('%-10s %12s %12s %10s' % ('성분', '전체 상관', '최악5%일 상관', '최악일 평균'))
    for k in ('div', 'ust10', 'ust30', 'gold'):
        r = comp[k]
        ok = ~np.isnan(r)
        c1 = float(np.corrcoef(r[ok][1:], qr[ok][1:])[0, 1])
        m = worst[ok[worst]]
        c2 = float(np.corrcoef(r[m], qr[m])[0, 1])
        print('%-10s %11.3f %12.3f %9.2f%%' % (k, c1, c2, r[m].mean() * 100))
    print('  ※ v18 §4-6(d): 배당은 QLD 최악 60일에 상관이 0.71 -> 0.82 로 올라간다.')
    print('    국채·금이 그 자리에서 어떻게 움직이는가가 이 축의 전부다.')


# ---------------------------------------------------------------- 3) 본 판정
def verdict(D, comp, start, label, cost=COST):
    wA = rule_w(D['ddv'], -0.16, -0.11)
    wB = rule_w(D['ddv'], -0.16, -0.16)
    rows = []
    for nm, wt in CANDS:
        defr = comp['tbill'] if wt is None else mix_r(comp, wt)
        for lab, w in (('A -16/-11', wA), ('B -16/-16', wB)):
            c = sim_def(D, w, defr, cost=cost, start=start)
            m = met(c)
            rows.append(dict(방어=nm if lab.startswith('A') else '', 전략=lab,
                             최종배수=m['final'], CAGR=m['cagr'] * 100, MDD=m['mdd'] * 100,
                             Calmar=m['calmar'], Sortino=m['sortino']))
    df = pd.DataFrame(rows)
    print('\n===== 3) 본 판정 — %s =====' % label)
    with pd.option_context('display.width', 200):
        print(df.to_string(index=False, float_format=lambda x: format(x, ',.2f')))
    return df


# ---------------------------------------------------------------- 4) MDD
def mdd_where(D, comp, start):
    wB = rule_w(D['ddv'], -0.16, -0.16)
    print('\n===== 4) MDD 분해 (B -16/-16, %s~) =====' % (start or '1972'))
    print('%-24s %9s %-12s %-12s %8s' % ('방어자산', 'MDD', '고점', '저점', '회복(년)'))
    for nm, wt in CANDS:
        defr = comp['tbill'] if wt is None else mix_r(comp, wt)
        c = sim_def(D, wB, defr, start=start)
        dd = c / c.cummax() - 1
        t = dd.idxmin()
        p = c.loc[:t].idxmax()
        rec = c.loc[t:]
        rec = rec[rec >= c.loc[p]]
        yr = ((rec.index[0] - t).days / 365.25) if len(rec) else np.nan
        print('%-24s %8.2f%% %-12s %-12s %8s' %
              (nm, dd.min() * 100, str(p.date()), str(t.date()),
               '미회복' if np.isnan(yr) else '%.1f' % yr))


# ---------------------------------------------------------------- 5) 규약
def _mdd(c):
    return float((c / c.cummax() - 1).min()) * 100


def rebal_convention(D, comp, start=None, label=''):
    wB = rule_w(D['ddv'], -0.16, -0.16)
    print('\n===== 5) 재조정 규약 — 어디까지가 백테스트 낙관인가  %s =====' % label)
    print('%-22s %11s %11s %11s %11s %10s %10s' %
          ('방어자산', '일간(낙관)', '월간(실전)', '분기(실전)', '무재조정', '월간MDD', '월간Calmar'))
    for nm, wt in CANDS:
        if wt is None:
            continue
        multi = len([k for k, v in wt.items() if v > 0]) > 1
        a = sim_def(D, wB, mix_r(comp, wt), start=start)
        if multi:
            m = sim_hold(D, wB, comp, wt, start=start, rebal='M')
            q = sim_hold(D, wB, comp, wt, start=start, rebal='Q')
            h = sim_hold(D, wB, comp, wt, start=start, rebal=None)
        else:
            m = q = h = a                       # 단일자산은 재조정 개념이 없다
        mm = met(m)
        print('%-22s %11s %11s %11s %11s %9.2f%% %10.2f' %
              (nm, format(a.iloc[-1], ',.0f'), format(m.iloc[-1], ',.0f'),
               format(q.iloc[-1], ',.0f'), format(h.iloc[-1], ',.0f'),
               mm['mdd'] * 100, mm['calmar']))
    print('  ※ 도피 구간은 보통 수개월~수년이다. 그 안에서 월 1회 리밸런싱은')
    print('    매도·매수 2건이라 실제로 할 수 있다. 판정은 "월간(실전)" 열로 한다.')
    print('  ※ 단일자산(배당100 등)은 재조정 개념이 없어 네 열이 같다.')


def weight_plateau(D, comp, start=None, label=''):
    """가중치가 평지인가 스파이크인가 — v18 §5-1 이 요구한 관문."""
    wB = rule_w(D['ddv'], -0.16, -0.16)
    print('\n===== 6-5) 가중치 평지 확인 (월간 재조정, %s) =====' % label)
    print('  배당 비중을 0.0~1.0 으로 훑고 나머지는 국채:금 = 6:4 로 나눈다')
    print('  %-8s %13s %10s %9s' % ('배당비중', '최종배수', 'MDD', 'Calmar'))
    for d in [x / 10 for x in range(0, 11)]:
        rest = 1 - d
        wt = dict(div=d, ust10=rest * 0.6, gold=rest * 0.4)
        wt = {k: v for k, v in wt.items() if v > 1e-9}
        c = (sim_hold(D, wB, comp, wt, start=start, rebal='M')
             if len(wt) > 1 else sim_def(D, wB, mix_r(comp, wt), start=start))
        m = met(c)
        print('  %-8.1f %13s %9.2f%% %9.2f' % (d, format(m['final'], ',.0f'), m['mdd'] * 100, m['calmar']))
    print('\n  배당 0.5 고정, 국채:금 비율을 훑는다')
    print('  %-8s %13s %10s %9s' % ('국채:금', '최종배수', 'MDD', 'Calmar'))
    for u in [x / 10 for x in range(0, 6)]:
        wt = dict(div=0.5, ust10=u, gold=0.5 - u)
        wt = {k: v for k, v in wt.items() if v > 1e-9}
        c = (sim_hold(D, wB, comp, wt, start=start, rebal='M')
             if len(wt) > 1 else sim_def(D, wB, mix_r(comp, wt), start=start))
        m = met(c)
        print('  %-8s %13s %9.2f%% %9.2f' % ('%.0f:%.0f' % (u * 100, (0.5 - u) * 100),
                                             format(m['final'], ',.0f'), m['mdd'] * 100, m['calmar']))


# ---------------------------------------------------------------- 6) 관문
def gates(D, comp, pick):
    wB = rule_w(D['ddv'], -0.16, -0.16)
    cur = dict(div=1.0)
    print('\n===== 6) 검증관문 — 현행(배당100) vs 채택후보 =====')

    print('\n[6-1] 편도 거래비용 (2000-2026)')
    print('%-24s %10s %10s %10s %10s' % ('방어자산', '0.05%', '0.10%', '0.20%', '0.50%'))
    for nm, wt in (('배당100 (현행)', cur), (pick[0], pick[1])):
        v = [sim_def(D, wB, mix_r(comp, wt), cost=c, start='2000-01-03').iloc[-1]
             for c in (0.0005, 0.001, 0.002, 0.005)]
        print('%-24s %10s %10s %10s %10s' % (nm, *[format(x, ',.1f') for x in v]))

    print('\n[6-2] 체결지연 (2000-2026)')
    print('%-24s %10s %10s %10s %10s' % ('방어자산', 'lag1', 'lag2', 'lag3', 'lag5'))
    for nm, wt in (('배당100 (현행)', cur), (pick[0], pick[1])):
        v = [sim_def(D, wB, mix_r(comp, wt), lag=L, start='2000-01-03').iloc[-1]
             for L in (1, 2, 3, 5)]
        print('%-24s %10s %10s %10s %10s' % (nm, *[format(x, ',.1f') for x in v]))

    print('\n[6-3] 구간 안정성 (최종배수 / MDD)')
    SEG = [('1972-1985', '1972-02-07', '1985-12-31'), ('1986-1999', '1986-01-01', '1999-12-31'),
           ('2000-2009', '2000-01-03', '2009-12-31'), ('2010-2026', '2010-01-01', None)]
    print('%-12s %24s %24s' % ('구간', '배당100 (현행)', pick[0]))
    for nm, s, e in SEG:
        cells = []
        for wt in (cur, pick[1]):
            c = sim_def(D, wB, mix_r(comp, wt), start=s, end=e)
            m = met(c)
            cells.append('%12s / %7.2f%%' % (format(m['final'], ',.1f'), m['mdd'] * 100))
        print('%-12s %24s %24s' % (nm, *cells))

    print('\n[6-4] 롤링 승률 (QQQ 대비, 2000-2026)')
    qqq = pd.Series(np.cumprod(1 + np.nan_to_num(D['px'].pct_change().values)), index=D['idx'])
    qqq = qqq.loc['2000-01-03':]
    print('%-24s %9s %9s %9s %11s' % ('방어자산', '3Y', '5Y', '10Y', '10Y최악CAGR'))
    for nm, wt in (('배당100 (현행)', cur), (pick[0], pick[1])):
        c = sim_def(D, wB, mix_r(comp, wt), start='2000-01-03')
        rs = rolling_stats(c, qqq / qqq.iloc[0])
        print('%-24s %8.1f%% %8.1f%% %8.1f%% %10.2f%%' %
              (nm, rs[3]['win'], rs[5]['win'], rs[10]['win'], rs[10]['cagr_worst']))


# ---------------------------------------------------------------- 7) 원화
def krw(D, comp, pick, krd, start='1997-01-02', label='1997-2026'):
    """국내 상품 구조 반영. 환노출/환헤지가 방어자산 선택을 바꾸는가?"""
    idx = D['idx']
    fr = K.fx(idx).pct_change().fillna(0.0).values
    rq = np.nan_to_num(D['px'].pct_change().values)
    lev2 = 2 * ((1 + rq) * (1 + fr) - 1) - D['c_daily']       # TIGER 레버리지: 환노출 2배
    from hyst_core import A, B

    def krw_def(weights, hedged):
        """hedged=True 인 성분은 환효과 제거, False 인 성분은 (1+r)(1+fx)-1.
        바스켓은 §5 의 실전 규약대로 월초 재조정한다."""
        parts = {}
        for k, w in weights.items():
            if w <= 0:
                continue
            x = np.nan_to_num(comp[k])
            parts[k] = x if hedged.get(k, False) else ((1 + x) * (1 + fr) - 1)
        if len(parts) == 1:
            return list(parts.values())[0]
        return mix_monthly_from(parts, weights, idx)

    print('\n===== 7) 원화 실전 — 환노출 vs 환헤지 (%s, 한국 거래일, 슬리피지 0.1%%) =====' % label)
    print('%-34s %-12s %12s %8s %9s %8s  %s' %
          ('방어자산 구성', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar', 'MDD시점'))
    # [실측 반영] 국내 미국채10년선물 ETF 는 환노출이고 실효만기가 5년이다(axis_krspec.py).
    SCEN = [
        ('배당100 환노출 (현행)', dict(div=1.0), {}),
        ('배당40 국채(5Y)40 금20  ← 국내 실제 사양', dict(div=0.4, ust5=0.4, gold=0.2), {}),
        ('배당50 국채(5Y)30 금20', dict(div=0.5, ust5=0.3, gold=0.2), {}),
        ('배당40 국채(10Y)40 금20  (이상)', dict(div=0.4, ust10=0.4, gold=0.2), {}),
        ('배당40 국채(20Y,H)40 금20  453850', dict(div=0.4, ust20=0.4, gold=0.2), dict(ust20=True)),
        ('배당50 금50 (국채 없음)', dict(div=0.5, gold=0.5), {}),
        ('배당60 금40 (국채 없음)', dict(div=0.6, gold=0.4), {}),
    ]
    out = {}
    for nm, wt, hd in SCEN:
        sr = krw_def(wt, hd)
        for S in (A, B):
            Dx = dict(D); Dx['qldr'] = lev2; Dx['schdr'] = sr
            c, w, t = K.run_kr(Dx, S, cost=COST, slip=0.001, start=start, krdays=krd)
            m = met(c)
            out[(nm, S['name'])] = m
            dd = c / c.cummax() - 1
            t = dd.idxmin()
            print('%-34s %-12s %12s %7.2f%% %8.2f%% %8.2f  %s' %
                  (nm if S is A else '', S['name'], format(m['final'], ',.1f'),
                   m['cagr'] * 100, m['mdd'] * 100, m['calmar'], str(t.date())))
    print('  ※ 환헤지 모형은 헤지 캐리(한미 금리차)를 0 으로 뒀다. 한국 금리가 높던')
    print('    2000년대에는 실제로 플러스였으므로 환헤지에 보수적인 가정이다.')
    return out


# ---------------------------------------------------------------- 8) 실물
def real_kr(D, comp):
    """국내 상장 실물 ETF 로 대리자산 타당성 검증 (겹침 구간)."""
    print('\n===== 8) 국내 실물 ETF 교차검증 =====')
    print('%-8s %-26s %-12s %9s %9s %9s %9s %9s' %
          ('코드', '이름', '겹침시작', 'CAGR', '변동성', 'MDD', '동일일상관', '1일시차'))
    print('  ※ 한국장은 15:30 KST 마감이라 미국 채권·금 시세를 하루 늦게 반영한다.')
    fxs = K.fx(D['idx'])
    for code, (nm, kind, fx, _M) in DA.KR_ETF.items():
        try:
            s = DA.kr(code)
        except Exception:
            continue
        ii = s.index.intersection(D['idx'])
        if len(ii) < 250:
            continue
        rr = s.reindex(ii).pct_change().fillna(0).values
        key = {'금': 'gold', '미국채': 'ust5' if _M == 5 else 'ust20'}.get(kind)
        cor = lagc = np.nan
        if key:
            pos = D['idx'].searchsorted(ii)
            proxy = np.nan_to_num(comp[key])[pos]
            if '환노출' in fx:                      # 원화 환산해서 비교
                f = fxs.reindex(ii).pct_change().fillna(0).values
                proxy = (1 + proxy) * (1 + f) - 1
            ok = ~np.isnan(proxy)
            cor = float(np.corrcoef(rr[ok][1:], proxy[ok][1:])[0, 1])
            a, b = rr[ok], proxy[ok]
            lagc = float(np.corrcoef(a[1:], b[:-1])[0, 1])
        c = pd.Series(np.cumprod(1 + rr), index=ii)
        yrs = (ii[-1] - ii[0]).days / 365.25
        print('%-8s %-26s %-12s %8.2f%% %8.2f%% %8.2f%% %9s %9s' %
              (code, nm, str(ii[0].date()), (c.iloc[-1] ** (1 / yrs) - 1) * 100,
               rr.std() * np.sqrt(252) * 100, (c / c.cummax() - 1).min() * 100,
               '-' if np.isnan(cor) else '%.3f' % cor,
               '-' if np.isnan(cor) else '%.3f' % lagc))



# ---------------------------------------------------------------- 9) 실물 운용
def _krseries(code):
    """분배금 반영 종가. AdjClose 가 있으면 그것, 없으면 Close(이미 조정본)."""
    d = pd.read_csv('data/hist/kr_%s_KS.csv' % code, parse_dates=['Date'])
    col = 'AdjClose' if 'AdjClose' in d.columns else 'Close'
    return d.set_index('Date')[col].astype(float).sort_index()


REAL_MIX = [
    ('배당100 (현행)', {'458730': 1.0}),
    ('배당50 국채30 금20 (금=KRX금현물)', {'458730': 0.5, '305080': 0.3, '411060': 0.2}),
    ('배당50 국채30 금20 (금=골드선물H)', {'458730': 0.5, '305080': 0.3, '132030': 0.2}),
    ('배당40 국채40 금20', {'458730': 0.4, '305080': 0.4, '411060': 0.2}),
    ('국채50 금50 (주식0)', {'305080': 0.5, '411060': 0.5}),
]
REAL_NAME = {'458730': 'TIGER 미국배당다우존스', '305080': 'TIGER 미국채10년선물',
             '411060': 'ACE KRX금현물', '132030': 'KODEX 골드선물(H)',
             '418660': 'TIGER 미국나스닥100레버리지'}


def real_run(D, start='2023-06-20', slip=0.001, cost=COST):
    """실제 국내 상장 ETF 만으로 돌린다. 소급 없음 — 전부 상장 이후 구간이다.

    신호: QQQ 미국 종가 252일 낙폭 (기존과 동일)
    체결: 그 다음 한국 거래일. v21 §13.4 가 "시각 차이는 묻힌다"고 판정했으므로
          종가 기준으로 잡고 슬리피지 0.1% 를 강제한다(제미나이.md 규약).
    """
    lev = _krseries('418660')
    print('\n===== 9) 국내 상장 실물 ETF 만으로 — 소급 없음 (%s ~) =====' % start)
    print('  위험자산 = %s' % REAL_NAME['418660'])
    for wB_lab, ex in (('B -16/-16', -0.16), ('A -16/-11', -0.11)):
        wsig = pd.Series(rule_w(D['ddv'], -0.16, ex), index=D['idx'])
        print('\n  [%s]' % wB_lab)
        print('  %-38s %10s %9s %9s %6s' % ('방어자산', '최종배수', 'CAGR', 'MDD', '전환'))
        for nm, mix in REAL_MIX:
            ser = {c: _krseries(c) for c in mix}
            ii = lev.index
            for c in ser:
                ii = ii.intersection(ser[c].index)
            ii = ii[ii >= pd.Timestamp(start)]
            if len(ii) < 200:
                print('  %-38s  겹침 부족(%d일)' % (nm, len(ii)))
                continue
            rl = lev.reindex(ii).pct_change().fillna(0).values
            rd = {c: ser[c].reindex(ii).pct_change().fillna(0).values for c in mix}
            pos = []
            cur = 1.0
            for d in ii:
                z = wsig.loc[:d - pd.Timedelta(days=1)]
                if len(z):
                    cur = float(z.iloc[-1])
                pos.append(cur)
            pos = np.array(pos)
            V = 1.0
            buckets = None
            prev = pos[0]
            out = []
            for i in range(len(ii)):
                p = pos[i - 1] if i > 0 else pos[0]
                if buckets is None:
                    V *= (1 + rl[i]) if p >= 1 else 1.0
                else:
                    for c in mix:
                        buckets[c] *= (1 + rd[c][i])
                    V = sum(buckets.values())
                if p != prev:
                    V *= (1 - cost - slip)
                    buckets = None if p >= 1 else {c: V * mix[c] for c in mix}
                    prev = p
                out.append(V)
            cv = pd.Series(out, index=ii)
            m = met(cv)
            print('  %-38s %10.3f %8.2f%% %8.2f%% %6d' %
                  (nm, m['final'], m['cagr'] * 100, m['mdd'] * 100,
                   int((np.abs(np.diff(pos)) > 0).sum())))
    ii = lev.index[lev.index >= pd.Timestamp(start)]
    cc = lev.reindex(ii) / lev.reindex(ii).iloc[0]
    m = met(cc)
    print('\n  [대조] %s 계속보유  %.3f배  CAGR %.2f%%  MDD %.2f%%'
          % (REAL_NAME['418660'], m['final'], m['cagr'] * 100, m['mdd'] * 100))
    print('  ※ 3.2년은 판정하기엔 짧다. 이 표는 "국내 상품으로 실제 굴러가는가"의 확인이지')
    print('    우열 판정이 아니다. 판정은 §3~§7 의 54년 표가 한다.')


def liquidity():
    """사용자 조건 — "필요할 때 매도 후 QLD 매수가 바로 되는가"의 정량화."""
    print('\n----- 유동성 (최근 1년 일간 거래대금) -----')
    print('  %-8s %-26s %12s %12s %10s' % ('코드', '이름', '일평균', '중앙값', '최소일'))
    for code, (nm, kind, fx, _M) in DA.KR_ETF.items():
        d = pd.read_csv('data/hist/kr_%s_KS.csv' % code, parse_dates=['Date'])
        if 'Volume' not in d.columns:
            continue
        d = d.dropna(subset=['Volume'])
        v = d['Raw'] * d['Volume'] / 1e8
        z = v[d['Date'] >= d['Date'].max() - pd.Timedelta(days=365)]
        print('  %-8s %-26s %10.1f억 %10.1f억 %8.1f억' % (code, nm, z.mean(), z.median(), z.min()))
    print('  ※ ETF 는 LP 호가 의무가 있고(09:05~15:20), 매도대금은 같은 날 재매수에 쓸 수 있다.')
    print('    개인 자금 규모에서 위 6종은 전부 당일 전환이 가능한 수준이다.')
    print('    다만 미국채10년선물 2종(9~17억)은 다른 4종보다 얇다.')


if __name__ == '__main__':
    D = DF.build('chain')
    print('데이터 %s ~ %s  n=%d  편도비용 %.2f%%'
          % (D['idx'][0].date(), D['idx'][-1].date(), len(D['idx']), COST * 100))
    assert check(D), '검산 실패'
    comp = materials(D)
    assert check_hold(D, comp), 'sim_hold 규약 검산 실패'

    diagnose(D, comp)
    correlations(D, comp)
    verdict(D, comp, None, '1972-2026 (54.5년)')
    verdict(D, comp, '2000-01-03', '2000-2026 (26.6년)')
    mdd_where(D, comp, None)
    mdd_where(D, comp, '2000-01-03')
    rebal_convention(D, comp, None, '1972-2026')
    rebal_convention(D, comp, '2000-01-03', '2000-2026')

    # 국내 ISA 실전 채택안. 국내에 '미국채 환노출형'이 없어 §7 에서 국채 다리가
    # 이득을 잃는다 -> 환노출 상품이 있는 금만으로 간다. 달러 최적은 배당40/국채40/금20.
    PICK = ('배당40 국채5Y40 금20 [국내]', dict(div=0.4, ust5=0.4, gold=0.2))
    PICK_USD = ('배당50 금50 (국채없음)', dict(div=0.5, gold=0.5))
    gates(D, comp, PICK_USD)
    gates(D, comp, PICK)
    weight_plateau(D, comp, None, '1972-2026')
    weight_plateau(D, comp, '2000-01-03', '2000-2026')
    real_kr(D, comp)
    liquidity()
    krd = K.kr_caldays()
    krw(D, comp, PICK, krd)
    krw(D, comp, PICK, krd, '2000-01-03', '2000-2026 (IMF 환율반전 제외)')
    real_run(D)
