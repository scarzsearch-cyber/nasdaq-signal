# -*- coding: utf-8 -*-
"""
[v25] 괴리율·체결 마찰 — 가용 가격으로 상한과 모형 이탈을 잰다

[v24 대비 정정 2건 — 둘 다 결론을 뒤집었다]
  (1) DA.kr() 이 458730/133690/418660 의 **미조정 종가**를 읽고 있었다(AdjClose 무시).
      배당 ETF 는 분배금이 통째로 빠져 연 -3%p 짜리 가짜 이탈이 생겼다.
  (2) 레버리지 이론가에 c_daily 를 빼지 않아 **무비용 합성**과 비교했다.
      원화 엔진이 실제로 쓰는 모형은 2x(지수+환) - c_daily 다.
  아래 수치는 원자료가 갱신될 때마다 다시 계산한다. 특정 과거 값이나 결론을 코드에
  고정하지 않는다.

[v24] 괴리율·체결 마찰 상한 — iNAV 없이 얼마나 말할 수 있는가

v21 부터 미결이던 과제다. **진짜 괴리율(시장가 − iNAV)은 KRX/발행사 iNAV 가 있어야
계산할 수 있고, 이 환경에서는 구할 수 없다.** 대신 구할 수 있는 것으로 **상한**을 잰다.

[3가지 대용치]
  ① 이론가 대비 잔차   ETF 가격 / (기초 × 환율) 을 60일 이동평균으로 정규화한 값의 분포.
                      괴리율 + 추적오차 + 시차가 **전부 섞여 있는 상한**이다.
  ② 시초가 갭          Open / 전일 Close − 1 의 표준편차. 실제 체결 시점 불확실성.
  ③ 일중 반전          (Close − Open) 이 시초가 갭과 반대로 가는 정도.
                      연관성만 재며, 괴리·정보·유동성 중 원인을 식별하지 못한다.

[읽는 법] ①은 상한이지 괴리율 그 자체가 아니다. 특히 미국 자산 ETF 는 한국장 마감(15:30 KST)
후에도 미국 시세가 움직이므로 시차가 섞인다. ③의 단순 회귀만으로 그중 얼마가 진짜
괴리인지 분해할 수 없다. 실제 괴리율에는 동시점 iNAV 자료가 별도로 필요하다.

실행:  python axis_krspread.py
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys

try:                       # [코드리뷰 2026-09-04] 이 파일은 콘솔에 표를 찍는다.
    _sys.stdout.reconfigure(encoding='utf-8')   # cp949 콘솔에서 em-dash 로 죽지 않게
except Exception:
    pass
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

import hist_defasset as DA
from axis_lib import COST, rule_w

FXP = 'data/hist/fred_DEXKOUS.csv'

TARGETS = [
    ('458730', 'TIGER 미국배당다우존스', 'div'),
    ('305080', 'TIGER 미국채10년선물', 'ust5'),
    ('308620', 'KODEX 미국10년국채선물', 'ust5'),
    ('411060', 'ACE KRX금현물', 'gold'),
    ('132030', 'KODEX 골드선물(H)', 'gold_h'),
    ('418660', 'TIGER 미국나스닥100레버리지', 'lev'),
    ('133690', 'TIGER 미국나스닥100 (1배·대조군)', 'lev1'),
]


def fx(idx):
    d = pd.read_csv(FXP)
    d.columns = ['Date', 'v']
    d = d[d['v'] != '.']
    d['Date'] = pd.to_datetime(d['Date'])
    s = d.set_index('Date')['v'].astype(float).sort_index()
    return s.reindex(idx.union(s.index)).ffill().reindex(idx)


def theory(kind, idx):
    """원화 기준 이론 가격 지수 (레벨). 환헤지 상품은 환율을 곱하지 않는다."""
    f = fx(idx)
    if kind == 'gold_h':
        r = DA.gold_r(idx)
        return pd.Series(np.cumprod(1 + r), index=idx)
    if kind == 'gold':
        r = DA.gold_r(idx)
    elif kind == 'ust5':
        # [v36] 실물 305080 과 대조하는 자리이므로 **선물형** 모형을 쓴다.
        r = DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE)
    elif kind == 'div':
        import hist_defensive as DF
        r = DF.defensive(idx, 'chain')
    elif kind == 'lev':
        # [v25 정정] 원화 엔진이 실제로 쓰는 모형은 2x(지수+환) - c_daily 다.
        # v24 는 c_daily 를 빼지 않은 무비용 합성과 비교해 이탈을 4.5%p 로 과대추정했다.
        import hist_data as H
        import hist_defensive as DF
        c = DF.build('chain')['c_daily']
        qqq = H._stooq('qqq_us_d.csv')
        qqq = qqq.reindex(idx.union(qqq.index)).ffill().reindex(idx)
        rq = qqq.pct_change().fillna(0).values
        rf = f.pct_change().fillna(0).values
        r = 2 * ((1 + rq) * (1 + rf) - 1) - c
        return pd.Series(np.cumprod(1 + r), index=idx)
    elif kind == 'lev1':
        import hist_data as H
        qqq = H._stooq('qqq_us_d.csv')
        qqq = qqq.reindex(idx.union(qqq.index)).ffill().reindex(idx)
        rq = qqq.pct_change().fillna(0).values
        rf = f.pct_change().fillna(0).values
        return pd.Series(np.cumprod(1 + ((1 + rq) * (1 + rf) - 1)), index=idx)
    else:
        raise ValueError(kind)
    rf = f.pct_change().fillna(0).values
    return pd.Series(np.cumprod(1 + ((1 + r) * (1 + rf) - 1)), index=idx)


def holding_share(idx, pos, start, end, kind):
    """해당 실물의 관측창 안에서 전략 B가 그 다리를 실제 보유한 시간 비중."""
    idx = pd.DatetimeIndex(idx)
    pos = np.asarray(pos, float)
    m = (idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))
    if not m.any():
        raise ValueError('전략 B와 실물 표본이 겹치지 않는다: %s~%s' % (start, end))
    held = pos[m] if kind in ('lev', 'lev1') else 1.0 - pos[m]
    return float(np.mean(held))


def selfcheck():
    ix = pd.date_range('2020-01-01', periods=3)
    # 신호 [공격, 방어, 방어]의 실제 체결은 [공격, 공격, 방어].
    pos = np.array([1.0, 1.0, 0.0])
    assert abs(holding_share(ix, pos, ix[0], ix[-1], 'lev') - 2 / 3) < 1e-12
    assert abs(holding_share(ix, pos, ix[0], ix[-1], 'div') - 1 / 3) < 1e-12


def run():
    selfcheck()
    print('===== ① 이론가 대비 잔차 (60일 이동평균 정규화) — 괴리율의 상한 =====')
    print('%-28s %8s %8s %8s %8s %8s' % ('상품', '표준편차', '95%', '99%', '최대', 'n'))
    residuals = {}
    for code, nm, kind in TARGETS:
        s = DA.kr(code)
        idx = s.index
        try:
            th = theory(kind, idx)
        except Exception as e:
            print('%-28s  이론가 산출 실패 %s' % (nm, e))
            continue
        ratio = (s / th)
        rel = (ratio / ratio.rolling(60, min_periods=30).mean() - 1).dropna()
        a = rel.abs() * 100
        residuals[code] = {'std': float(rel.std()), 'p95': float(a.quantile(.95)) / 100}
        print('%-28s %7.2f%% %7.2f%% %7.2f%% %7.2f%% %8d'
              % (nm, rel.std() * 100, a.quantile(.95), a.quantile(.99), a.max(), len(rel)))
    print('  ※ 상한이다. 미국 자산 ETF 는 한국장 마감 후 미국 시세가 더 움직이므로')
    print('    잔차에는 시차도 섞인다. 이 표와 ③만으로 원인별 비중을 가를 수는 없다.')

    print('\n===== ② 시초가 갭 (Open / 전일 Close − 1) — 체결 시점 불확실성 =====')
    print('%-28s %8s %8s %8s %8s' % ('상품', '평균', '표준편차', '95%', '최대'))
    gaps = {}
    gap_stats = {}
    for code, nm, kind in TARGETS:
        d = pd.read_csv('data/hist/kr_%s_KS.csv' % code, parse_dates=['Date'])
        col = 'Raw' if 'Raw' in d.columns else 'Close'
        if 'Open' not in d.columns:
            continue
        d = d.dropna(subset=['Open', col])
        g = (d['Open'] / d[col].shift(1) - 1).dropna()
        gaps[code] = (d, g)
        gap_stats[code] = {'mean': float(g.mean()), 'std': float(g.std()),
                           'p95': float(g.abs().quantile(.95))}
        print('%-28s %7.3f%% %7.2f%% %7.2f%% %7.2f%%'
              % (nm, g.mean() * 100, g.std() * 100, g.abs().quantile(.95) * 100, g.abs().max() * 100))

    print('\n===== ③ 시초가 갭과 당일 수익의 관계 — 원인 식별 검사가 아님 =====')
    print('%-28s %10s %10s %s' % ('상품', 'beta', 'R2', '해석'))
    reversals = {}
    for code, nm, kind in TARGETS:
        if code not in gaps:
            continue
        d, g = gaps[code]
        col = 'Raw' if 'Raw' in d.columns else 'Close'
        intra = (d[col] / d['Open'] - 1).reindex(g.index)
        m = pd.concat([g.rename('g'), intra.rename('i')], axis=1).dropna()
        if len(m) < 100:
            continue
        A = np.column_stack([np.ones(len(m)), m['g'].values])
        b, *_ = np.linalg.lstsq(A, m['i'].values, rcond=None)
        pred = A @ b
        r2 = 1 - ((m['i'] - pred) ** 2).sum() / ((m['i'] - m['i'].mean()) ** 2).sum()
        reversals[code] = {'beta': float(b[1]), 'r2': float(r2)}
        tag = (('당일 반전 %d%%' % round(-b[1] * 100)) if b[1] < -0.02
               else '당일 반전 거의 없음') + ' — 원인 식별 불가'
        print('%-28s %10.3f %10.3f %s' % (nm, b[1], r2, tag))

    print('\n===== ④ 실물과 모형의 연간 차이 — 비용·추적차이·시차가 섞인 값 =====')
    print('%-28s %10s %10s %10s %10s %s' %
          ('상품', '실물 CAGR', '모형 CAGR', '연 이탈', '창내보유', '보유가중 근사'))
    W = {'div': 0.40, 'ust5': 0.40, 'gold': 0.20, 'gold_h': 0.20, 'lev': 1.0, 'lev1': 0.0}
    import hist_defensive as DF
    bd = DF.build('chain')
    bw = rule_w(bd['ddv'], -0.16, -0.16)
    bpos = np.r_[bw[0], bw[:-1]]
    drifts = {}
    for code, nm, kind in TARGETS:
        s_ = DA.kr(code)
        idx = s_.index
        try:
            th = theory(kind, idx)
        except Exception:
            continue
        yrs = (idx[-1] - idx[0]).days / 365.25
        a = float(s_.iloc[-1] / s_.iloc[0]) ** (1 / yrs) - 1
        b = float(th.iloc[-1] / th.iloc[0]) ** (1 / yrs) - 1
        hold = holding_share(bd['idx'], bpos, idx[0], idx[-1], kind)
        eff = (a - b) * W[kind] * hold
        drifts[code] = {'actual': a, 'model': b, 'delta': a - b,
                        'hold': hold, 'impact': eff}
        print('%-28s %9.2f%% %9.2f%% %9.2f%%p %9.1f%% %9.2f%%p/yr'
              % (nm, a * 100, b * 100, (a - b) * 100, hold * 100, eff * 100))
    print('  ※ 「보유가중 근사」 = 이탈 x 바스켓 비중 x **각 실물의 같은 관측창** 안 보유시간.')
    print('    복리 경로를 다시 재생한 인과효과가 아니라 크기를 보는 1차 근사다.')

    print('\n===== 판정 =====')
    print('  · ①의 표준편차는 전부 시차·추적오차·괴리가 섞인 상한이다.')
    print('  · ③은 시초가 갭과 같은 날 수익의 연관성일 뿐이다. 음의 beta를')
    print('    "그만큼이 진짜 괴리 비용"으로 해석할 수 없고, iNAV 없이 원인은 미확정이다.')
    lev = drifts.get('418660')
    lev1 = drifts.get('133690')
    if lev:
        print('  · ④의 현재 원자료에서 레버리지 실물−모형 차이는 %+.2f%%p/년,'
              ' 같은 관측창 보유비중 %.1f%%를 반영한 1차 근사는 %+.2f%%p/년이다.' %
              (lev['delta'] * 100, lev['hold'] * 100, lev['impact'] * 100))
    if lev1:
        print('    1배 대조군의 실물−모형 차이는 %+.2f%%p/년이다. 둘의 부호와 크기는'
              ' 원자료에서 계산하며 모형 정확성을 단정하지 않는다.' % (lev1['delta'] * 100))
    gap = gap_stats.get('418660')
    if gap:
        print('  · 레버리지 ETF 시초가 갭 표준편차는 %.2f%%로 편도비용 %.2f%%보다 크다.'
              ' 정확한 체결가는 명목 수수료와 별개의 실행 불확실성이다.' %
              (gap['std'] * 100, COST * 100))


if __name__ == '__main__':
    run()
