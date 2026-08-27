# -*- coding: utf-8 -*-
"""
[v26] 적립식 재검증 — 현행 채택안(배당40/국채40/금20)으로, 그리고 **불규칙 납입**으로

왜 다시 하나:
  · v22 축3 이 적립식을 확인했지만 그때 방어자산은 **배당100** 이었다.
    v23 에서 배당40/국채40/금20 으로 바뀌었으므로 결론이 유지되는지 다시 봐야 한다.
  · v22 는 **매달 같은 금액**을 가정했다. 실제로는 금액도 시점도 제멋대로다.
    "고정 적립"만 검증하고 "불규칙 적립"을 안 본 것은 구멍이다.

납입 규약 4종 (전부 같은 총납입액으로 정규화해 비교한다):
  고정        매달 1
  불규칙      매달 로그정규(중앙 1, 시그마 0.8) — 어떤 달은 3배, 어떤 달은 0.3배
  거르기      30% 확률로 그 달 건너뜀, 넣을 때는 1
  몰아넣기    20% 확률로 5, 아니면 0 — 극단적으로 뭉친 납입

측정: 롤링 창, **납입액 대비 최종배수**. 거치식 배수와 직접 비교하면 안 된다.

실행:  python axis_accum2.py
"""
import numpy as np
import pandas as pd

import hist_data as H
import hist_defasset as DA
import hist_defensive as DF
import hist_korea as K
import hist_krfinal as KF
from axis_lib import COST, rule_w, check

SEEDS = 12                      # 불규칙 납입은 난수라 여러 번 돌려 분포를 본다


# ---------------------------------------------------------------- 엔진
def accum(rr, dfr, w, lo, hi, contrib, cost=COST):
    """월초 임의금액 적립. contrib[m] = 그 달 납입액.

    반환 (총납입, 최종평가액, 경로MDD). 전일 신호만 쓴다(미래 참조 없음).
    """
    R = C = paid = 0.0
    prev = w[lo]
    vals = []
    mi = -1
    for i in range(lo, hi):
        # [v33 정정] 전환을 그날 수익 적용 **전에** 한다.
        # 기존 순서(수익 -> 전환)는 전일 종가 신호가 하루 더 늦게 반영되는
        # 실질 2일 지연이었다. 규약은 pos = w.shift(1) = 1일 지연.
        # 검산: 납입 1회면 거치식 axis_lib.sim() 과 오차 0.
        pos = w[i - 1] if i > lo else w[lo]

        if pos != prev:                                     # 전략 전환
            if pos >= 1:
                R += C * (1 - cost); C = 0.0
            else:
                C += R * (1 - cost); R = 0.0
            prev = pos

        R *= (1 + rr[i])
        C *= (1 + dfr[i])

        if i > lo and MONTH[i] != MONTH[i - 1]:              # 월초 납입
            mi += 1
            a = contrib[mi] if mi < len(contrib) else 0.0
            if a:
                paid += a
                if pos >= 1:
                    R += a
                else:
                    C += a

        vals.append(R + C)

    v = pd.Series(vals, index=IDX[lo:hi])
    if paid <= 0:
        return 0.0, 0.0, 0.0
    return paid, float(v.iloc[-1]), float((v / v.cummax() - 1).min())


def make_contrib(kind, n, rng, mret=None):
    """mret: 그 창의 월별 시장수익(전월). 행동 패턴(추격/역추격)에만 쓴다."""
    if kind == '고정':
        return np.ones(n)
    if kind == '불규칙':
        return np.exp(rng.normal(0, 0.8, n) - 0.32)         # 중앙 ~1
    if kind == '거르기':
        return (rng.random(n) > 0.30).astype(float)
    if kind == '몰아넣기':
        return (rng.random(n) < 0.20).astype(float) * 5.0
    if kind in ('추격', '역추격'):
        # 사람이 실제로 하는 것 — 오르면 더 넣고(추격), 빠지면 더 넣고(역추격).
        # "내맘대로" 가 무작위가 아니라 시장 상태와 상관될 때를 잰다.
        r = np.zeros(n) if mret is None else np.resize(np.nan_to_num(mret), n)
        up = r > 0
        if kind == '추격':
            return np.where(up, 2.0, 0.5)
        return np.where(up, 0.5, 2.0)
    raise ValueError(kind)


def month_returns(rr, lo, hi):
    """창 안의 월별 시장수익(전월 대비). 추격/역추격 트리거용."""
    s = pd.Series(np.cumprod(1 + np.nan_to_num(rr[lo:hi])), index=IDX[lo:hi])
    m = s.resample('MS').last().pct_change().fillna(0.0).values
    return np.concatenate([[0.0], m[:-1]])                  # 전월 수익(미래 참조 없음)


# ---------------------------------------------------------------- 실행
FX_START = pd.Timestamp('1981-04-13')      # DEXKOUS 시작. 그 이전은 환율이 없어 쓰면 안 된다


def rolling(policies, years, step=126,
            kinds=('고정', '불규칙', '거르기', '몰아넣기', '추격', '역추격')):
    n = len(IDX)
    span = int(years * 252)
    first = int(IDX.searchsorted(FX_START))
    starts = list(range(first, n - span, step))
    out = []
    for kind in kinds:
        seeds = [0] if kind in ('고정', '추격', '역추격') else range(SEEDS)
        for nm, rr, w in policies:
            mult, mdd = [], []
            for sd in seeds:
                rng = np.random.default_rng(1000 + sd)
                for lo in starts:
                    hi = lo + span
                    mr = month_returns(QMKT, lo, hi) if kind in ('추격', '역추격') else None
                    c = make_contrib(kind, years * 12 + 2, rng, mr)
                    p, v, m = accum(rr, DEF[nm], w, lo, hi, c)
                    if p > 0:
                        mult.append(v / p); mdd.append(m)
            mult = np.array(mult)
            out.append(dict(납입=kind, 정책=nm, 중앙값=np.median(mult),
                            분위10=np.quantile(mult, .10), 최악=mult.min(),
                            최고=mult.max(), 경로MDD중앙=np.median(mdd) * 100, n=len(mult)))
    return pd.DataFrame(out)


def show(df, title):
    print('\n===== %s =====' % title)
    piv = df.pivot(index='정책', columns='납입', values='중앙값')
    order = [p for p in ORDER if p in piv.index]
    with pd.option_context('display.width', 200):
        print(df.set_index(['납입', '정책']).loc[
            [(k, p) for k in df['납입'].unique() for p in order]].to_string(
            float_format=lambda x: format(x, ',.2f')))
    print('\n  [납입규약별 중앙값 — 규약이 순위를 바꾸는가]')
    print(piv.loc[order].to_string(float_format=lambda x: format(x, ',.2f')))


def min_contribution():
    """실무 제약 — 방어 상태에서 3종을 비중대로 1주 이상씩 사려면 월 얼마가 필요한가.

    국내 ETF 는 1주 단위 거래다. 비중이 가장 작은 다리(금 20%)의 주가가 병목이 된다.
    """
    import csv
    import math
    try:
        rows = list(csv.DictReader(open('data/nav_history.csv', encoding='utf-8')))
    except FileNotFoundError:
        print('\n(data/nav_history.csv 없음 — deploy/nav_collect.py 를 먼저 돌려라)')
        return
    last = {}
    for r in rows:
        last[r['code']] = r
    print('\n===== 실무 제약 — 방어 상태 3종 분할에 필요한 최소 월납입 =====')
    print('%-28s %10s %6s %14s' % ('종목', '현재가', '비중', '필요 월납입'))
    need = 0.0
    for leg in DA.MIX_LEGS:
        c = leg['code']
        if c not in last:
            continue
        px = float(last[c]['close'])
        req = px / (leg['weight'] / 100.0)
        need = max(need, req)
        print('%-28s %10s %5d%% %13s원' % (leg['name'], format(px, ',.0f'), leg['weight'],
                                           format(req, ',.0f')))
    print('  -> 월 %s원 이상이면 매달 3종을 다 살 수 있다.'
          % format(math.ceil(need / 10000) * 10000, ','))
    print('  그 미만이면 매달 3종을 쪼개지 말고 **비중이 가장 미달한 것 하나만** 사라.')
    print('  결과는 같다 — 납입 자체가 리밸런싱을 대신한다.')


if __name__ == '__main__':
    D = DF.build('chain')
    assert check(D), '검산 실패'
    IDX = D['idx']
    MONTH = pd.Series(IDX).dt.to_period('M').values

    # ---- 원화 실전 재료 (환노출 2배 레버리지 + 채택 바스켓, 전부 환노출)
    Dk, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    parts = {'div': dfk,
             'ust5': (1 + DA.ust_tr(idx, 5, 'TNX')) * (1 + fr) - 1,
             'gold': (1 + DA.gold_r(idx)) * (1 + fr) - 1}
    mix_krw = DA.mix_monthly_parts(idx, DA.MIX_V23, parts)
    rq = np.nan_to_num(D['px'].pct_change().values)
    qqq_krw = (1 + rq) * (1 + fr) - 1
    QMKT = qqq_krw                                   # 행동 패턴 트리거 = 원화 기준 시장

    wB = rule_w(D['ddv'], -0.16, -0.16)
    wA = rule_w(D['ddv'], -0.16, -0.11)
    one = np.ones(len(IDX))

    ORDER = ['QQQ 적립(1배)', 'QLD 그냥 적립(2배)', '전략A -16/-11', '전략B -16/-16']
    POL = [('QQQ 적립(1배)', qqq_krw, one),
           ('QLD 그냥 적립(2배)', lev2, one),
           ('전략A -16/-11', lev2, wA),
           ('전략B -16/-16', lev2, wB)]
    DEF = {'QQQ 적립(1배)': mix_krw, 'QLD 그냥 적립(2배)': mix_krw,
           '전략A -16/-11': mix_krw, '전략B -16/-16': mix_krw}

    print('원화 기준 · 환노출 2배 · 방어자산 = 배당40/국채40/금20(월간 재조정, 전부 환노출)')
    print('구간 %s ~ %s   불규칙 납입은 시드 %d개 x 창 전부' % (IDX[0].date(), IDX[-1].date(), SEEDS))
    for y in (10, 15, 20):
        show(rolling(POL, y), '원화 · %d년 롤링 (납입액 대비 배수)' % y)
    min_contribution()
