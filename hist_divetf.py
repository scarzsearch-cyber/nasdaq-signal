# -*- coding: utf-8 -*-
"""
[클로드 자율 추가 규약 2] 2008년 방어자산 낙폭의 실측 보정

왜: French BE/ME·D/P Hi30 은 2007-09 에 -60~63% 빠진다. 이는 2007년 당시 고배당
    상위 30% 가 금융주로 가득했기 때문이다. 그러나 SCHD 가 추종하는 Dow Jones US
    Dividend 100 은 ROE·FCF/부채·배당성장 퀄리티 스크린이 있어 금융주 편중이 훨씬
    약하다. 즉 French 대리는 2008 방어자산 손실을 과대평가한다.
무엇: 2008을 실제로 겪은 배당 ETF 실물(DVY 2003-11~, VYM 2006-11~, SDY 2005-11~)로
    대리의 편향 크기를 측정하고, 방어자산 체인에 실물 구간을 최대한 끼워넣는다.
    새 지표가 아니라 기존 QQQ 체인과 동일한 '일간수익률 접합' 규약의 적용이다.
"""
import numpy as np, pandas as pd
import hist_data as H, hist_defensive as DF

def _y(t):
    d = pd.read_csv(f'data/hist/yahoo_{t}.csv', parse_dates=['Date'])
    return d.set_index('Date')['Close'].astype(float).sort_index()

SCHD = H._stooq('schd_us_d.csv')
REAL = {'SCHD': SCHD, 'DVY': _y('DVY'), 'VYM': _y('VYM'), 'SDY': _y('SDY'), 'SPY': _y('SPY')}
PROXY = {'BE/ME Hi30': DF.ff_beme_daily(), 'D/P Hi30(자율1)': DF.ff_div_daily()}


def rets(s, is_ret):
    return s if is_ret else s.pct_change()


def seg(s, a, b, is_ret=False):
    r = rets(s, is_ret).loc[a:b]
    return float(np.prod(1 + r.dropna()) - 1)


def mdd(s, a=None, b=None, is_ret=False):
    r = rets(s, is_ret).loc[a:b].dropna()
    lv = (1 + r).cumprod()
    return float((lv / lv.cummax() - 1).min())


if __name__ == '__main__':
    print('== 2007-09 금융위기 실측 vs 대리 (2007-10-31 ~ 2009-03-09) ==')
    for n, s in list(REAL.items()) + list(PROXY.items()):
        ir = n in PROXY
        if s.index[0] > pd.Timestamp('2007-10-31'):
            print('%-16s  (상장 전 %s)' % (n, s.index[0].date())); continue
        print('%-16s  구간수익 %7.2f%%   구간MDD %7.2f%%' %
              (n, seg(s, '2007-10-31', '2009-03-09', ir) * 100,
               mdd(s, '2007-10-31', '2009-03-09', ir) * 100))

    print('\n== SCHD 실물과의 상관/성과 (2011-10-20 ~) ==')
    sr = SCHD.pct_change().dropna(); sr = sr[sr.index >= DF.SCHD_START]
    for n, s in list(REAL.items())[1:] + list(PROXY.items()):
        v = (s if n in PROXY else s.pct_change()).dropna()
        ix = sr.index.intersection(v.index)
        a, b = sr.reindex(ix), v.reindex(ix)
        print('%-16s n=%5d corr=%.3f  CAGR %6.2f%% (SCHD %6.2f%%)  Vol %5.2f%% (SCHD %5.2f%%)'
              % (n, len(ix), np.corrcoef(a, b)[0, 1],
                 ((1 + b).prod() ** (252 / len(b)) - 1) * 100,
                 ((1 + a).prod() ** (252 / len(a)) - 1) * 100,
                 b.std() * np.sqrt(252) * 100, a.std() * np.sqrt(252) * 100))

    print('\n== 2000-02 닷컴 (2000-03-10 ~ 2002-10-09) ==')
    for n, s in list(REAL.items()) + list(PROXY.items()):
        ir = n in PROXY
        if s.index[0] > pd.Timestamp('2000-03-10'):
            print('%-16s  (상장 전 %s)' % (n, s.index[0].date())); continue
        print('%-16s  구간수익 %7.2f%%   구간MDD %7.2f%%'
              % (n, seg(s, '2000-03-10', '2002-10-09', ir) * 100,
                 mdd(s, '2000-03-10', '2002-10-09', ir) * 100))


# --------------------------------------------------- 방어자산 최적 체인 (자율규약2)
SP_DVY = '2003-11-10'          # DVY 상장 익일
SP_SCHD = '2011-10-25'         # SCHD 상장일


def defensive_chain(kind='dvy'):
    """
    일간수익률 접합(기존 QQQ 체인과 동일 규약).
      ~2003-11-07  French D/P Hi30 일간정합 (자율규약1)
      2003-11-10 ~ 2011-10-24  DVY 실물 (kind='dvy') 또는 DVY/VYM/SDY 등가중(kind='mix')
      2011-10-25 ~            SCHD 실물
    접합일 수익률은 0 으로 눌러 레벨 갭을 제거한다.
    """
    p = DF.ff_div_daily()
    if kind == 'mix':
        parts = [_y('DVY').pct_change(), _y('VYM').pct_change(), _y('SDY').pct_change()]
        mid = pd.concat(parts, axis=1).mean(axis=1)
    else:
        mid = _y('DVY').pct_change()
    r = pd.concat([p.loc[:pd.Timestamp(SP_DVY) - pd.Timedelta(days=1)],
                   mid.loc[SP_DVY:pd.Timestamp(SP_SCHD) - pd.Timedelta(days=1)],
                   SCHD.pct_change().loc[SP_SCHD:]])
    r = r[~r.index.duplicated()].sort_index()
    for s in (SP_DVY, SP_SCHD):
        t = r.index[r.index.searchsorted(pd.Timestamp(s))]
        r.loc[t] = 0.0
    return r.fillna(0.0)
