# -*- coding: utf-8 -*-
"""
[v24] 괴리율·체결 마찰 상한 — iNAV 없이 얼마나 말할 수 있는가

v21 부터 미결이던 과제다. **진짜 괴리율(시장가 − iNAV)은 KRX/발행사 iNAV 가 있어야
계산할 수 있고, 이 환경에서는 구할 수 없다.** 대신 구할 수 있는 것으로 **상한**을 잰다.

[3가지 대용치]
  ① 이론가 대비 잔차   ETF 가격 / (기초 × 환율) 을 60일 이동평균으로 정규화한 값의 분포.
                      괴리율 + 추적오차 + 시차가 **전부 섞여 있는 상한**이다.
  ② 시초가 갭          Open / 전일 Close − 1 의 표준편차. 실제 체결 시점 불확실성.
  ③ 일중 되돌림        (Close − Open) 이 전일 갭과 반대로 가는 정도.
                      갭이 괴리(일시적 미스프라이싱)면 되돌아오고, 정보면 안 되돌아온다.

[읽는 법] ①은 상한이지 괴리율 그 자체가 아니다. 특히 미국 자산 ETF 는 한국장 마감(15:30 KST)
후에도 미국 시세가 움직이므로 잔차의 대부분이 **시차**다. 그래서 ③으로 되돌림을 본다 —
되돌림이 크면 그만큼이 진짜 마찰(괴리)이고, 작으면 시차다.

실행:  python axis_krspread.py
"""
import numpy as np
import pandas as pd

import hist_defasset as DA

FXP = 'data/hist/fred_DEXKOUS.csv'

TARGETS = [
    ('458730', 'TIGER 미국배당다우존스', 'div'),
    ('305080', 'TIGER 미국채10년선물', 'ust5'),
    ('308620', 'KODEX 미국채10년선물', 'ust5'),
    ('411060', 'ACE KRX금현물', 'gold'),
    ('132030', 'KODEX 골드선물(H)', 'gold_h'),
    ('418660', 'TIGER 미국나스닥100레버리지', 'lev'),
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
        r = DA.ust_tr(idx, 5, 'TNX')
    elif kind == 'div':
        import hist_defensive as DF
        r = DF.defensive(idx, 'chain')
    elif kind == 'lev':
        import hist_data as H
        qqq = H._stooq('qqq_us_d.csv').reindex(idx.union(H._stooq('qqq_us_d.csv').index))
        qqq = qqq.ffill().reindex(idx)
        rq = qqq.pct_change().fillna(0).values
        rf = f.pct_change().fillna(0).values
        r = 2 * ((1 + rq) * (1 + rf) - 1)
        return pd.Series(np.cumprod(1 + r), index=idx)
    else:
        raise ValueError(kind)
    rf = f.pct_change().fillna(0).values
    return pd.Series(np.cumprod(1 + ((1 + r) * (1 + rf) - 1)), index=idx)


def run():
    print('===== ① 이론가 대비 잔차 (60일 이동평균 정규화) — 괴리율의 상한 =====')
    print('%-28s %8s %8s %8s %8s %8s' % ('상품', '표준편차', '95%', '99%', '최대', 'n'))
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
        print('%-28s %7.2f%% %7.2f%% %7.2f%% %7.2f%% %8d'
              % (nm, rel.std() * 100, a.quantile(.95), a.quantile(.99), a.max(), len(rel)))
    print('  ※ 상한이다. 미국 자산 ETF 는 한국장 마감 후 미국 시세가 더 움직이므로')
    print('    잔차의 상당부분이 괴리가 아니라 시차다. ③ 이 그 둘을 갈라 준다.')

    print('\n===== ② 시초가 갭 (Open / 전일 Close − 1) — 체결 시점 불확실성 =====')
    print('%-28s %8s %8s %8s %8s' % ('상품', '평균', '표준편차', '95%', '최대'))
    gaps = {}
    for code, nm, kind in TARGETS:
        d = pd.read_csv('data/hist/kr_%s_KS.csv' % code, parse_dates=['Date'])
        col = 'Raw' if 'Raw' in d.columns else 'Close'
        if 'Open' not in d.columns:
            continue
        d = d.dropna(subset=['Open', col])
        g = (d['Open'] / d[col].shift(1) - 1).dropna()
        gaps[code] = (d, g)
        print('%-28s %7.3f%% %7.2f%% %7.2f%% %7.2f%%'
              % (nm, g.mean() * 100, g.std() * 100, g.abs().quantile(.95) * 100, g.abs().max() * 100))

    print('\n===== ③ 일중 되돌림 — 갭이 괴리인가 정보인가 =====')
    print('%-28s %10s %10s %s' % ('상품', 'beta', 'R2', '해석'))
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
        tag = ('되돌림 %d%% — 그만큼이 마찰' % round(-b[1] * 100)) if b[1] < -0.02 else '되돌림 거의 없음 — 갭은 정보'
        print('%-28s %10.3f %10.3f %s' % (nm, b[1], r2, tag))

    print('\n===== ④ 모형 대비 연간 이탈 — 백테스트에 안 들어간 진짜 비용 =====')
    print('%-28s %10s %10s %10s %s' % ('상품', '실물 CAGR', '모형 CAGR', '연 이탈', '전략 영향'))
    HOLD = {'div': 0.18, 'ust5': 0.18, 'gold': 0.18, 'gold_h': 0.18, 'lev': 0.82}
    W = {'div': 0.40, 'ust5': 0.40, 'gold': 0.20, 'gold_h': 0.20, 'lev': 1.0}
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
        eff = (a - b) * W[kind] * HOLD[kind]
        print('%-28s %9.2f%% %9.2f%% %9.2f%%p %9.2f%%p/yr'
              % (nm, a * 100, b * 100, (a - b) * 100, eff * 100))
    print('  ※ 「전략 영향」 = 이탈 x 바스켓 비중 x 그 자산을 들고 있는 시간비율.')
    print('    방어자산은 전체 기간의 약 18%만 보유하므로 영향이 크게 희석된다.')

    print('\n===== 판정 =====')
    print('  · ①의 표준편차는 전부 시차·추적오차·괴리가 섞인 상한이다.')
    print('  · ③에서 되돌림 beta 가 0 에 가까우면 갭이 정보(미국장 움직임)라는 뜻이고,')
    print('    실제로 물게 되는 마찰은 ①보다 훨씬 작다.')
    print('  · 진짜 괴리율은 여전히 KRX/발행사 iNAV 가 있어야 계산할 수 있다.')
    print('    이 스크립트는 "얼마나 나쁠 수 있는가"의 상한만 준다.')
    print('  · v21 §13.4 결론(체결 시각 고민은 무의미)은 여기서도 유지된다 —')
    print('    시초가 갭 표준편차가 편도비용 0.1% 보다 한 자릿수 크기 때문이다.')


if __name__ == '__main__':
    run()
