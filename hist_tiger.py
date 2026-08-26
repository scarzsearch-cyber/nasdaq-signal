# -*- coding: utf-8 -*-
"""
과제 ③ 본론 — TIGER ETF 실물 데이터 검증
  상장 이전 기간에 현재 상품을 소급하지 않는다(제미나이2.md §148 준수).
  각 상품은 '실제 상장일 이후'만 사용한다.
"""
import numpy as np, pandas as pd
import hist_data as H, hist_korea as K
from reentry_lib import met

def load(path):
    d = pd.read_csv(path, parse_dates=['Date']).set_index('Date').sort_index()
    f = (d['AdjClose'] / d['Close'])              # 분배금 조정계수
    return pd.DataFrame({'open': d['Open'] * f, 'close': d['AdjClose'], 'raw_close': d['Close'],
                         'raw_open': d['Open']})

T = {k: load(v[1]) for k, v in K.TIGER.items()}
US = {'nasdaq100': H._stooq('qqq_us_d.csv'), 'lev': H._stooq('qld_us_d.csv'),
      'div': H._stooq('schd_us_d.csv')}
NAME = {k: v[2] for k, v in K.TIGER.items()}
TICK = {k: v[0] for k, v in K.TIGER.items()}


def fx_series():
    f = H._fred(K.FX, 'DEXKOUS')
    return f


if __name__ == '__main__':
    fxr = fx_series()
    print('== TIGER 3종 실물 데이터 범위 ==')
    for k, d in T.items():
        print('%-12s %-34s %s ~ %s  (%d일, %.1f년)'
              % (TICK[k], NAME[k], d.index[0].date(), d.index[-1].date(), len(d),
                 (d.index[-1] - d.index[0]).days / 365.25))

    # ---------- 추적오차: TIGER(원화) vs 미국ETF x 환율
    print('\n== 추적오차: TIGER 실물 vs [미국ETF x 원달러] (상장 이후 전 구간) ==')
    print('%-34s %6s %9s %9s %9s %8s %9s' %
          ('상품', 'n', 'TIGER연', '이론연', '연차이', '추적오차', '누적차이'))
    for k, d in T.items():
        u = US[k]
        lvl = (u.pct_change().fillna(0) + 1).cumprod()
        # 미국 종가 t 는 한국 t+1 에 반영 -> 한국 달력으로 shift
        th = (lvl * fxr.reindex(lvl.index).ffill())
        th = th.reindex(th.index.union(d.index)).ffill()
        rt = d['close'].pct_change().dropna()
        # 이론치는 '전일 미국 종가' 기준이므로 한국 날짜에서 하루 당겨 맞춘다
        rth = th.pct_change().shift(1).reindex(rt.index).dropna()
        ix = rt.index.intersection(rth.index)
        a, b = rt.reindex(ix), rth.reindex(ix)
        n = len(ix)
        ca = (1 + a).prod() ** (252 / n) - 1
        cb = (1 + b).prod() ** (252 / n) - 1
        te = (a - b).std() * np.sqrt(252)
        print('%-34s %6d %8.2f%% %8.2f%% %+8.2f%%p %7.2f%% %+8.2f%%'
              % (NAME[k], n, ca * 100, cb * 100, (ca - cb) * 100, te * 100,
                 ((1 + a).prod() / (1 + b).prod() - 1) * 100))

    # ---------- 시초가 갭 = 이 전략이 실제로 내는 체결 마찰
    print('\n== 시초가 체결 마찰: 한국 개장 시초가 vs 직전 종가 (전량매매 시 실제 슬리피지) ==')
    print('%-34s %8s %9s %9s %9s %9s' % ('상품', '중앙값', '평균', '표준편차', '95퍼센타일', '최악'))
    for k, d in T.items():
        gap = (d['raw_open'] / d['raw_close'].shift(1) - 1).dropna()
        print('%-34s %+7.3f%% %+8.3f%% %8.3f%% %8.2f%% %8.2f%%'
              % (NAME[k], gap.median() * 100, gap.mean() * 100, gap.std() * 100,
                 gap.abs().quantile(0.95) * 100, gap.abs().max() * 100))
    print('  * 시초가 갭은 방향성이 없으므로 매수/매도에 평균적으로 상쇄되지만,')
    print('    변동성(표준편차)만큼 개별 전환의 체결 불확실성이 존재한다.')

    # ---------- 일중 변동폭(스프레드 상한 대용)
    print('\n== 참고: 일간 시가-종가 변동폭 (급변장 체결 리스크 대용치) ==')
    for k, d in T.items():
        oc = (d['raw_close'] / d['raw_open'] - 1).abs()
        print('%-34s 중앙 %5.2f%%  95%% %5.2f%%  최대 %6.2f%%'
              % (NAME[k], oc.median() * 100, oc.quantile(0.95) * 100, oc.max() * 100))
