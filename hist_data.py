"""
역사 확장 데이터 빌더 (1971-02-05 ~ 현재)

목적: -16/-11(A) vs -16/-16(B) 를 1973-74, 1987, 1990, 1998 을 포함한
      실제 역사 구간에서 비교하기 위한 QQQ 대체 시계열을 만든다.

[체인 구성]  전부 '일간 수익률'로 이어붙인다(레벨은 무의미).
  구간1 1971-02-05 ~ 1985-09-30 : Nasdaq Composite (FRED NASDAQCOM, 원천 Nasdaq OMX)
  구간2 1985-10-01 ~ 1999-03-09 : Nasdaq-100      (Yahoo ^NDX)
  구간3 1999-03-10 ~ 현재        : QQQ 실물        (기존 qqq_us_d.csv, 수정주가)

[명시해야 할 대체/한계]  (전략_v20.md 에 그대로 기재)
  - 구간1·2는 '가격지수'라 배당이 빠져 있다. 구간3만 배당 포함 수정주가다.
  - 구간1은 Nasdaq-100 이 존재하지 않던 시기라 Composite 로 대체했다.
    1973년 Composite 는 약 2,500개 소형 OTC 주식 묶음이고 현재 QQQ 는
    메가캡 기술주 100종목이다. 즉 '같은 자산'이 아니라 '같은 시장의 조상'이다.
  - 2x 합성비용 c_daily 는 2006-06-22 이후 QQQ/QLD 실물 겹침에서 역산한 값을
    그대로 1971년까지 소급 적용한다(기존 verify.py 규약 유지).
  - SCHD 대체는 기존 규약대로 연 2% 현금. 1970-80년대 실제 단기금리는
    7~15% 였으므로 이 규약은 방어자산 수익을 크게 과소평가한다.
    -> A(방어자산 체류가 긴 쪽)에 불리하게 작용하므로, 실제 3개월 T-bill
       (FRED DTB3)로 바꾼 민감도를 별도로 함께 보고한다.
"""
import numpy as np
import pandas as pd

LOOKBACK = 252
COST = 0.001
CASH_RATE = 0.02
SPLICE_NDX = '1985-10-01'
SPLICE_QQQ = '1999-03-10'
START_EXT = '1972-02-07'          # 1971-02-05 + 252거래일 (완전한 룩백 확보)


def _fred(path, col):
    """FRED CSV 한 계열. col 은 실제로 그 컬럼을 고른다.

    [코드리뷰 2026-09-04] 종전에는 col 을 받아 놓고 바로 d.columns 를 덮어써
    **한 번도 쓰지 않았다** — 어떤 이름을 넘겨도 결과가 같았다. 다중 컬럼 파일을
    넘기면 두 번째 컬럼이 조용히 선택됐다. 이제 이름이 있으면 그것으로 고르고,
    없으면 종전대로 두 번째 컬럼으로 물러선다(기존 호출부 7곳 전부 동작 동일).
    """
    d = pd.read_csv(path)
    name = col if col in d.columns else d.columns[1]
    d = d[[d.columns[0], name]]
    d.columns = ['Date', 'v']
    d = d[d['v'] != '.']
    d['Date'] = pd.to_datetime(d['Date'])
    return d.set_index('Date')['v'].astype(float).sort_index()


def _yahoo(path):
    d = pd.read_csv(path, parse_dates=['Date'])
    return d.set_index('Date')['Close'].astype(float).sort_index()


def _stooq(path):
    d = pd.read_csv(path, parse_dates=['Date'])
    return d.set_index('Date')['Close'].astype(float).sort_index()


def crosscheck():
    """FRED vs Yahoo 동일 구간 대조 — 데이터 출처 신뢰도 확인용."""
    fc = _fred('data/hist/fred_NASDAQCOM.csv', 'NASDAQCOM')
    yi = _yahoo('data/hist/yahoo_IXIC.csv')
    f1 = _fred('data/hist/fred_NASDAQ100.csv', 'NASDAQ100')
    yn = _yahoo('data/hist/yahoo_NDX.csv')
    out = []
    for nm, a, b in [('NasdaqComposite FRED vs Yahoo', fc, yi), ('Nasdaq100 FRED vs Yahoo', f1, yn)]:
        ix = a.index.intersection(b.index)
        rel = (a.reindex(ix) / b.reindex(ix) - 1).abs()
        ra = a.reindex(ix).pct_change().dropna()
        rb = b.reindex(ix).pct_change().dropna()
        cm = ra.index.intersection(rb.index)
        out.append(dict(pair=nm, n=len(ix), start=str(ix[0].date()), end=str(ix[-1].date()),
                        max_level_diff=float(rel.max()), med_level_diff=float(rel.median()),
                        ret_corr=float(np.corrcoef(ra.reindex(cm), rb.reindex(cm))[0, 1])))
    return pd.DataFrame(out)


def qqq_proxy():
    """3구간 체인 -> (수익률 시리즈, 출처 라벨 시리즈)"""
    comp = _fred('data/hist/fred_NASDAQCOM.csv', 'NASDAQCOM')
    ndx = _yahoo('data/hist/yahoo_NDX.csv')
    qqq = _stooq('qqq_us_d.csv')

    r1 = comp.pct_change().loc[:pd.Timestamp(SPLICE_NDX) - pd.Timedelta(days=1)]
    r2 = ndx.pct_change().loc[SPLICE_NDX:pd.Timestamp(SPLICE_QQQ) - pd.Timedelta(days=1)]
    r3 = qqq.pct_change().loc[SPLICE_QQQ:]
    src = pd.concat([pd.Series('NasdaqComposite', index=r1.index),
                     pd.Series('NDX', index=r2.index),
                     pd.Series('QQQ', index=r3.index)])
    r = pd.concat([r1, r2, r3])
    r = r[~r.index.duplicated()].sort_index()
    src = src[~src.index.duplicated()].sort_index()
    # 이어붙인 첫날의 갭 수익률은 지수 간 레벨 차이라 0으로 눌러 제거
    for s in (SPLICE_NDX, SPLICE_QQQ):
        t = r.index[r.index.searchsorted(pd.Timestamp(s))]
        r.loc[t] = 0.0
    return r.fillna(0.0), src


def tbill_daily(idx):
    """FRED DTB3(연율 %, discount basis) -> 일간 현금수익률"""
    t = _fred('data/hist/fred_DTB3.csv', 'DTB3') / 100.0
    t = t.reindex(idx.union(t.index)).ffill().reindex(idx).bfill()
    return (t / 252.0).values.astype(float)


def build_ext(cash='fixed2', start=START_EXT):
    """
    reentry_lib.run() 이 요구하는 D 딕셔너리와 같은 형태로 확장 데이터셋을 만든다.
    cash: 'fixed2'  = 기존 규약(연 2% 현금 + 2011-10 이후 SCHD 실물)
          'tbill'   = SCHD 실물 이전 구간을 실제 3개월 T-bill 로 대체
    """
    r, src = qqq_proxy()
    px = (1 + r).cumprod()

    # 2x 합성비용: 기존 규약 그대로 QQQ/QLD 실물 겹침에서 역산
    qld = _stooq('qld_us_d.csv')
    qqq = _stooq('qqq_us_d.csv')
    qqq_r, qld_r = qqq.pct_change(), qld.pct_change()
    ov = qqq_r.index.intersection(qld_r.index)
    ov = ov[ov >= '2006-06-22']
    x, y = qqq_r.reindex(ov).dropna(), qld_r.reindex(ov).dropna()
    cm = x.index.intersection(y.index)
    c_daily = float((2 * x.reindex(cm) - y.reindex(cm)).mean())

    pre = r.index[r.index < '2006-06-22']
    synth = (2 * r.reindex(pre) - c_daily)
    full = pd.concat([synth, y])
    full = full[~full.index.duplicated()].sort_index()
    qld_ext = (1 + full).cumprod()

    idx_all = px.index.intersection(qld_ext.index).sort_values()
    idx = idx_all[idx_all >= start]
    # [코드리뷰 2026-09-04] 룩백 최대값은 **절단 전** 격자에서 구한다. 종전에는 px 를
    # start 로 자른 뒤 rolling 을 걸어 START_EXT 주석이 약속한 '완전한 룩백 확보'가
    # 무효였다 — 1972-02-07~1973-01-22 의 220일이 dd=0 으로 눌려 그 1년간 어떤
    # 낙폭도 신호를 못 냈다. −16/−11 문턱에서는 갈리는 날이 0 이라 공표 수치는 그대로.
    px_all = px.reindex(idx_all)
    dd = (px_all / px_all.rolling(LOOKBACK, min_periods=LOOKBACK).max() - 1).reindex(idx).fillna(0)
    px = px_all.reindex(idx)
    qldr = qld_ext.reindex(idx).pct_change().fillna(0)

    schd = _stooq('schd_us_d.csv')
    if cash == 'tbill':
        base = pd.Series(tbill_daily(idx), index=idx)
        sr = schd.reindex(idx).pct_change()
        schdr = sr.where(sr.notna(), base)
    else:
        schdr = schd.reindex(idx).pct_change().fillna(CASH_RATE / 252)

    return dict(idx=idx, px=px, dd=dd, src=src.reindex(idx),
                c_daily=c_daily,
                qldr=qldr.values.astype(float), schdr=schdr.values.astype(float),
                ddv=dd.values.astype(float), pxv=px.values.astype(float))


if __name__ == '__main__':
    print(crosscheck().to_string(index=False))
    D = build_ext()
    print('\nrange', D['idx'][0].date(), '->', D['idx'][-1].date(), 'n =', len(D['idx']))
    print('c_daily (2x synth drag) = %.6f%%/day  = %.2f%%/yr' % (D['c_daily'] * 100, D['c_daily'] * 252 * 100))
    print(D['src'].value_counts().to_string())
    print('\nmin dd by year (proxy):')
    yy = D['dd'].groupby(D['dd'].index.year).min()
    print(''.join('%d %6.1f%%  ' % (k, v * 100) + ('\n' if i % 5 == 4 else '')
                  for i, (k, v) in enumerate(yy.items())))
