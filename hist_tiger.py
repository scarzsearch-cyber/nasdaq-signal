# -*- coding: utf-8 -*-
"""
과제 ③ 본론 — TIGER ETF 실물 데이터 검증
  상장 이전 기간에 현재 상품을 소급하지 않는다(제미나이2.md §148 준수).
  각 상품은 '실제 상장일 이후'만 사용한다.
"""
import functools

import numpy as np, pandas as pd
import hist_data as H, hist_korea as K
from reentry_lib import met


@functools.lru_cache(maxsize=None)
def load(path):
    d = pd.read_csv(path, parse_dates=['Date']).set_index('Date').sort_index()
    f = (d['AdjClose'] / d['Close'])              # 분배금 조정계수
    return pd.DataFrame({'open': d['Open'] * f, 'close': d['AdjClose'], 'raw_close': d['Close'],
                         'raw_open': d['Open']})


# [코드리뷰 2026-09-04] 종전에는 T/US 가 모듈 최상위에 있어 **임포트만 해도**
# 국내 3종 + 미국 3종 CSV 를 전부 읽었다. hist_krreal 이 이 모듈을 임포트하므로
# 그 비용을 항상 물었고, 여섯 파일 중 **하나만 없어도 임포트 자체가 실패**해
# 그 파일이 필요 없는 경로까지 같이 죽었다. 지연 + 캐시로 바꾼다.
# 모듈 속성(hist_tiger.T 등)으로 접근하던 코드는 __getattr__ 이 그대로 받는다.
@functools.lru_cache(maxsize=None)
def _T():
    return {k: load(v[1]) for k, v in K.TIGER.items()}


@functools.lru_cache(maxsize=None)
def _US():
    return {'nasdaq100': H._stooq('qqq_us_d.csv'), 'lev': H._stooq('qld_us_d.csv'),
            'div': H._stooq('schd_us_d.csv')}


NAME = {k: v[2] for k, v in K.TIGER.items()}
TICK = {k: v[0] for k, v in K.TIGER.items()}


def __getattr__(name):
    if name == 'T':
        return _T()
    if name == 'US':
        return _US()
    raise AttributeError(name)


def fx_series():
    f = H._fred(K.FX, 'DEXKOUS')
    return f


if __name__ == '__main__':
    fxr = fx_series()
    print('== TIGER 3종 실물 데이터 범위 ==')
    for k, d in _T().items():
        print('%-12s %-34s %s ~ %s  (%d일, %.1f년)'
              % (TICK[k], NAME[k], d.index[0].date(), d.index[-1].date(), len(d),
                 (d.index[-1] - d.index[0]).days / 365.25))

    # ---------- 추적오차: TIGER(원화) vs 미국ETF x 환율
    print('\n== 추적오차: TIGER 실물 vs [미국ETF x 원달러] (상장 이후 전 구간) ==')
    print('%-34s %6s %9s %9s %9s %8s %9s' %
          ('상품', 'n', 'TIGER연', '이론연', '연차이', '추적오차', '누적차이'))
    for k, d in _T().items():
        u = _US()[k]
        lvl = (u.pct_change().fillna(0) + 1).cumprod()
        rt = d['close'].pct_change().dropna()
        # [코드리뷰 2026-09-04] 이론 레벨은 **미국 달력 위에서만** 만든다.
        #   종전에는 미국+한국 합집합으로 reindex+ffill 한 뒤 pct_change().shift(1) 을
        #   걸었는데, 합집합에서 한 행 미는 것은 '직전 미국 거래일'이 아니라 '직전
        #   합집합 행'이다. 미국 휴장·한국 개장인 날(7월 4일·추수감사절 등)에는
        #   합집합에 한국 날짜만 있고 th 가 ffill 값이라 pct_change 가 0 이 되고,
        #   그 0 이 shift 로 밀리면서 이론 수익률이 미국 세션 하나만큼 어긋났다.
        #   이제 한국 날짜 d 마다 'd 직전에 마감한 미국 세션'의 레벨을 집어와
        #   한국 달력에서 pct_change 한다 — 미국 휴장이면 레벨이 같아 0,
        #   한국 휴장으로 건너뛴 날은 그 사이 미국 세션들이 누적된다.
        th_us = lvl * fxr.reindex(lvl.index).ffill()
        pos = th_us.index.searchsorted(rt.index, side='left') - 1
        ok = pos >= 0
        rth = pd.Series(th_us.values[pos[ok]], index=rt.index[ok]).pct_change().dropna()
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
    for k, d in _T().items():
        gap = (d['raw_open'] / d['raw_close'].shift(1) - 1).dropna()
        print('%-34s %+7.3f%% %+8.3f%% %8.3f%% %8.2f%% %8.2f%%'
              % (NAME[k], gap.median() * 100, gap.mean() * 100, gap.std() * 100,
                 gap.abs().quantile(0.95) * 100, gap.abs().max() * 100))
    print('  * 시초가 갭은 방향성이 없으므로 매수/매도에 평균적으로 상쇄되지만,')
    print('    변동성(표준편차)만큼 개별 전환의 체결 불확실성이 존재한다.')

    # ---------- 일중 변동폭(스프레드 상한 대용)
    print('\n== 참고: 일간 시가-종가 변동폭 (급변장 체결 리스크 대용치) ==')
    for k, d in _T().items():
        oc = (d['raw_close'] / d['raw_open'] - 1).abs()
        print('%-34s 중앙 %5.2f%%  95%% %5.2f%%  최대 %6.2f%%'
              % (NAME[k], oc.median() * 100, oc.quantile(0.95) * 100, oc.max() * 100))
