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
import functools
import numpy as np, pandas as pd
import hist_data as H, hist_defensive as DF

@functools.lru_cache(maxsize=None)
def _y(t):
    d = pd.read_csv(f'data/hist/yahoo_{t}.csv', parse_dates=['Date'])
    return d.set_index('Date')['Close'].astype(float).sort_index()


# [코드리뷰 2026-09-04] 종전에는 SCHD·REAL·PROXY 가 모듈 최상위에 있어 **임포트만
# 해도** CSV 5개 + French 전체 파싱 + 월간정합이 돌았다. hist_defensive.defensive()
# 가 함수 안에서 이 모듈을 임포트하므로(순환 회피) 체인 방어자산을 한 번만 써도
# 그 비용을 전부 물었고, yahoo_* 넷 중 하나만 없어도 **임포트 자체가 실패**해 그
# 파일이 필요 없는 defensive_chain('dvy') 경로까지 같이 죽었다. 지연 + 캐시로 바꾼다.
# 모듈 속성(hist_divetf.SCHD 등)으로 접근하던 외부 코드는 __getattr__ 이 그대로 받는다.
@functools.lru_cache(maxsize=None)
def _schd():
    return H._stooq('schd_us_d.csv')


@functools.lru_cache(maxsize=None)
def _real():
    return {'SCHD': _schd(), 'DVY': _y('DVY'), 'VYM': _y('VYM'),
            'SDY': _y('SDY'), 'SPY': _y('SPY')}


@functools.lru_cache(maxsize=None)
def _proxy():
    return {'BE/ME Hi30': DF.ff_beme_daily(), 'D/P Hi30(자율1)': DF.ff_div_daily()}


def __getattr__(name):
    if name == 'SCHD':
        return _schd()
    if name == 'REAL':
        return _real()
    if name == 'PROXY':
        return _proxy()
    raise AttributeError(name)


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
    for n, s in list(_real().items()) + list(_proxy().items()):
        ir = n in _proxy()
        if s.index[0] > pd.Timestamp('2007-10-31'):
            print('%-16s  (상장 전 %s)' % (n, s.index[0].date())); continue
        print('%-16s  구간수익 %7.2f%%   구간MDD %7.2f%%' %
              (n, seg(s, '2007-10-31', '2009-03-09', ir) * 100,
               mdd(s, '2007-10-31', '2009-03-09', ir) * 100))

    print('\n== SCHD 실물과의 상관/성과 (2011-10-20 ~) ==')
    sr = _schd().pct_change().dropna(); sr = sr[sr.index >= DF.SCHD_START]
    for n, s in list(_real().items())[1:] + list(_proxy().items()):
        v = (s if n in _proxy() else s.pct_change()).dropna()
        ix = sr.index.intersection(v.index)
        a, b = sr.reindex(ix), v.reindex(ix)
        print('%-16s n=%5d corr=%.3f  CAGR %6.2f%% (SCHD %6.2f%%)  Vol %5.2f%% (SCHD %5.2f%%)'
              % (n, len(ix), np.corrcoef(a, b)[0, 1],
                 ((1 + b).prod() ** (252 / len(b)) - 1) * 100,
                 ((1 + a).prod() ** (252 / len(a)) - 1) * 100,
                 b.std() * np.sqrt(252) * 100, a.std() * np.sqrt(252) * 100))

    print('\n== 2000-02 닷컴 (2000-03-10 ~ 2002-10-09) ==')
    for n, s in list(_real().items()) + list(_proxy().items()):
        ir = n in _proxy()
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
    수익률 접합이므로 레벨 갭이 없다 — 접합일을 따로 누르지 않는다.
    """
    p = DF.ff_div_daily()
    if kind == 'mix':
        parts = [_y('DVY').pct_change(), _y('VYM').pct_change(), _y('SDY').pct_change()]
        mid = pd.concat(parts, axis=1).mean(axis=1)
    else:
        mid = _y('DVY').pct_change()
    r = pd.concat([p.loc[:pd.Timestamp(SP_DVY) - pd.Timedelta(days=1)],
                   mid.loc[SP_DVY:pd.Timestamp(SP_SCHD) - pd.Timedelta(days=1)],
                   _schd().pct_change().loc[SP_SCHD:]])
    r = r[~r.index.duplicated()].sort_index()
    # [코드리뷰 2026-09-04] 종전에는 접합일 수익률을 '레벨 갭 제거' 명목으로 0 으로
    # 눌렀다. 그러나 이 체인은 레벨이 아니라 **수익률**을 이어붙이므로 지울 갭이 없다.
    # SP_SCHD 는 SCHD 원자료 시작일과 같아 pct_change 가 이미 NaN 이라 무해했지만,
    # SP_DVY 는 DVY 가 2003-11-07 부터라 실재하는 하루 수익률(−0.7320%)을 지우고
    # 있었다 — 방어자산 체인이 그만큼 영구히 유리해졌다. 아래 fillna 가 NaN 만 맡는다.
    return r.fillna(0.0)
