# -*- coding: utf-8 -*-
"""
과제 ③ 최종 — 실제 TIGER 상품 구조를 반영한 원화 기준 시뮬레이션

[실측으로 확인한 상품 구조]
  TIGER 레버리지(합성) = 1.982 x TIGER 미국나스닥100(원화)  (R2=0.90, alpha 연 -3.57%)
  -> 즉 '원화 기준 지수'를 2배로 추종한다. 환노출도 2배다.
     기존 백테스트의 (1+r_QLD)(1+r_FX)-1 는 환노출을 1배로만 준 과소모형이다.
  TIGER 미국배당다우존스 = 환노출 1배 (SCHD x 환율)

[따라서 원화 수익률]
  레버리지 보유 중 : r = 2*[(1+r_QQQ)(1+r_FX)-1] - c_daily
  배당 보유 중     : r = (1+r_SCHD)(1+r_FX)-1
"""
import numpy as np, pandas as pd
import hist_data as H, hist_defensive as DF, hist_korea as K
from reentry_lib import met
from hyst_core import A, B, switches

ST = '1997-01-02'


def build_krw(defkind='chain'):
    D = DF.build(defkind)
    idx = D['idx']
    fxs = K.fx(idx)
    fr = fxs.pct_change().fillna(0.0).values
    rq = np.nan_to_num(D['px'].pct_change().values)          # QQQ 대리 일간수익
    c = D['c_daily']
    lev2 = 2 * ((1 + rq) * (1 + fr) - 1) - c                 # 환노출 2배 레버리지
    lev1 = (1 + (2 * rq - c)) * (1 + fr) - 1                 # 환노출 1배(비교용)
    dfk = (1 + D['schdr']) * (1 + fr) - 1                    # 배당 1배 환노출
    # [코드리뷰 2026-09-04] rq(QQQ 대리 일간수익)를 D 에 얹어 둔다 — 종전에는
    # 내보내지 않아 __main__ 과 axis_defmix.krw 가 같은 식을 각자 다시 썼다.
    # 반환 튜플의 길이는 바꾸지 않는다(호출부 23곳이 6개로 언패킹한다).
    D['rq'] = rq
    return D, idx, lev2, lev1, dfk, fr


def sim(D, idx, qr, sr, S, krdays, slip=0.001, cost=0.001, start=ST):
    Dx = dict(D); Dx['qldr'] = qr; Dx['schdr'] = sr
    return K.run_kr(Dx, S, cost=cost, slip=slip, start=start, krdays=krdays)


if __name__ == '__main__':
    krd = K.kr_caldays()
    print('※ 1997-01 ~ 2026-08 (KOSPI 실거래일 달력 확보 구간). 국내 ETF 상장 이전 구간은')
    print('  「원화로 환산한 미국 자산」시뮬레이션이며 TIGER 상품의 실제 성과가 아니다.\n')
    for defkind, dlab in [('cash2', '방어=연2% 현금'), ('chain', '방어=배당체인(SCHD계열)'),
                          ('tbill', '방어=T-bill 실측')]:
        D, idx, lev2, lev1, dfk, fr = build_krw(defkind)
        print('===== %s =====' % dlab)
        print('%-40s %-11s %12s %7s %8s %7s' % ('시나리오', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar'))
        for lab, qr, sr in [('달러 기준 (참고)', D['qldr'], D['schdr']),
                            ('원화·환노출 1배 (구모형)', lev1, dfk),
                            ('원화·환노출 2배 (실제 TIGER 구조)', lev2, dfk)]:
            for S in (A, B):
                c, w, t = sim(D, idx, qr, sr, S, krd)
                m = met(c)
                print('%-40s %-11s %12s %6.2f%% %7.2f%% %7.2f'
                      % (lab if S is A else '', S['name'], f"{m['final']:,.1f}",
                         m['cagr'] * 100, m['mdd'] * 100, m['calmar']))
        lo = idx.searchsorted(pd.Timestamp(ST))
        for nm, r in [('TIGER레버리지 계속보유(원화 2배환노출)', lev2[lo:]),
                      ('TIGER나스닥100 계속보유(원화)', ((1 + D['rq']) * (1 + fr) - 1)[lo:])]:
            cc = pd.Series(np.cumprod(1 + r), index=idx[lo:]); m = met(cc)
            print('%-40s %-11s %12s %6.2f%% %7.2f%% %7.2f'
                  % (nm, '-', f"{m['final']:,.1f}", m['cagr'] * 100, m['mdd'] * 100, m['calmar']))
        print()

    # 위기별 원화 기준 방어 성과
    print('== 위기별: 원화 기준으로 이 전략이 실제로 지켜준 것 (방어=배당체인, 환노출 2배 구조) ==')
    D, idx, lev2, lev1, dfk, fr = build_krw('chain')
    CR = [('1997 IMF', '1997-07-01', '1998-06-30'), ('2000-02 닷컴', '2000-03-10', '2002-10-09'),
          ('2007-09 금융위기', '2007-10-31', '2009-03-09'), ('2020 코로나', '2020-02-19', '2020-03-23'),
          ('2022 인플레', '2021-11-19', '2022-12-28')]
    cA, wA, _ = sim(D, idx, lev2, dfk, A, krd)
    cB, wB, _ = sim(D, idx, lev2, dfk, B, krd)
    lv = pd.Series(np.cumprod(1 + lev2), index=idx)
    print('%-16s %10s %10s %10s' % ('위기', 'A -16/-11', 'B -16/-16', 'TIGER레버 보유'))
    for nm, s0, s1 in CR:
        f = lambda c: (c.loc[:s1].iloc[-1] / c.loc[:s0].iloc[-1] - 1) * 100
        print('%-16s %+9.1f%% %+9.1f%% %+9.1f%%' % (nm, f(cA), f(cB), f(lv)))
