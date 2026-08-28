#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v72] 월 1회 원자료 연장 — 성과 스냅샷(전략 곡선·지평표)을 최신으로 유지한다.

원칙:
  · **기존 행은 절대 고치지 않는다** (동결된 연구 스냅샷 보존). 마지막 날짜 뒤만 붙인다.
  · 수정주가는 **비율 이음(ratio-splice)**: 붙이는 구간 = 야후 수정주가 × k,
    k = 저장된 마지막 종가 / 야후 수정주가(같은 날). 수정주가의 정보는 레벨이 아니라
    **수익률**이므로, 이음새 이후 수익률이 야후의 조정 수익률과 정확히 일치하면 된다.
    배당이 지나 야후가 과거를 재조정해도 k 가 그걸 흡수한다 (자가 치유).
  · 장중 가드: 정규장 진행 중이면 마지막 봉 제외 (update_signal.py 와 같은 판별).
  · 미국·한국 장이 모두 닫힌 시각(매월 1일 07:17 UTC)에 돌도록 예약돼 있다.

대상 (build_stats.py 4개 시나리오의 전방 의존성 전부):
  qqq/qld/schd_us_d.csv   미국 3종 (Close=수정주가, OHLCV)
  yahoo_TNX.csv           10년 금리 (국채 다리)
  lbma_gold_pm.csv        금 — LBMA 는 야후에 없어 GLD 수익률로 이음 (연 0.4% 보수만큼
                          현물보다 불리 — 방어 다리 20% 에 묻히는 크기, 문서화됨)
  kr_*.csv 5종            TIGER 실물 + KOSPI 달력 (Open 원시가 + AdjClose 이음)
  fred_DEXKOUS.csv        원달러 — FRED 공식 CSV 전체 교체 (원천이 안정 시계열)

실행:  python deploy/refresh_hist.py          # 저장소 루트에서
"""
import io
import json
import os
import sys
import urllib.request

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


def chart(symbol, years=3):
    """야후 v8 chart — (DataFrame[open,close,adj,volume], 장중이면 마지막 봉 제거됨)"""
    import datetime
    p2 = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    p1 = p2 - years * 366 * 86400
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
           f'?period1={p1}&period2={p2}&interval=1d')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read().decode('utf-8', 'replace'))['chart']['result'][0]
    idx = pd.to_datetime(res['timestamp'], unit='s', utc=True).tz_convert(None).normalize()
    q = res['indicators']['quote'][0]
    adj = (res['indicators'].get('adjclose') or [{}])[0].get('adjclose') or q['close']
    df = pd.DataFrame({'open': q['open'], 'high': q.get('high'), 'low': q.get('low'),
                       'close': q['close'], 'adj': adj, 'volume': q['volume']}, index=idx)
    df = df[~df.index.duplicated(keep='last')].sort_index().dropna(subset=['close'])
    # 장중 가드 (update_signal.py 와 동일 판별)
    meta = res.get('meta', {})
    qt = meta.get('regularMarketTime')
    end = meta.get('currentTradingPeriod', {}).get('regular', {}).get('end')
    if qt and end and qt < end and len(df) > 0:
        live = pd.to_datetime(qt, unit='s', utc=True).tz_convert(None).normalize()
        if df.index[-1] == live:
            df = df.iloc[:-1]
    return df


def read_csv(path):
    return pd.read_csv(path, parse_dates=['Date'])


def append_rows(path, new_df, cols):
    """new_df(컬럼=파일과 동일)를 파일 끝에 붙인다. 붙일 게 없으면 0."""
    if new_df.empty:
        print(f'  {os.path.basename(path):22s} 추가 0행 (이미 최신)')
        return 0
    old = read_csv(path)
    out = pd.concat([old, new_df[cols]], ignore_index=True)
    out.to_csv(path, index=False)
    print(f'  {os.path.basename(path):22s} 추가 {len(new_df)}행 '
          f'(~{new_df["Date"].iloc[-1].date()})')
    return len(new_df)


def splice_us(path, symbol):
    """미국 3종: Close=수정주가 비율 이음. OHL 도 같은 비율로 조정해 붙인다."""
    old = read_csv(path)
    last_d, last_c = old['Date'].iloc[-1], float(old['Close'].iloc[-1])
    df = chart(symbol)
    if last_d not in df.index:
        print(f'  {os.path.basename(path):22s} [경고] 이음날 {last_d.date()} 이 야후에 없음 — 건너뜀',
              file=sys.stderr)
        return 0
    k = last_c / float(df.loc[last_d, 'adj'])
    new = df[df.index > last_d].copy()
    f = (new['adj'] * k / new['close'])              # 원시 → 이 파일의 수정 기준
    out = pd.DataFrame({'Date': new.index,
                        'Open': new['open'] * f, 'High': new['high'] * f,
                        'Low': new['low'] * f, 'Close': new['adj'] * k,
                        'Volume': new['volume'].fillna(0).astype('int64')})
    return append_rows(path, out, ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])


def splice_kr(path, symbol):
    """한국 종목 — 파일 형식이 둘이다 (hist_defasset.kr 의 주석과 동일):
      A) Date,Open,Close,AdjClose        : Open/Close 원시가 + AdjClose 만 비율 이음
      B) Date,Open,Close,Volume,Raw      : Close 가 이미 조정본 → Close 를 비율 이음,
                                           Raw 에 원시 종가, Open 은 원시가 그대로
    """
    old = read_csv(path)
    has_adj = 'AdjClose' in old.columns
    adj_col = 'AdjClose' if has_adj else 'Close'
    last_d, last_a = old['Date'].iloc[-1], float(old[adj_col].iloc[-1])
    df = chart(symbol)
    if last_d not in df.index:
        print(f'  {os.path.basename(path):22s} [경고] 이음날 {last_d.date()} 이 야후에 없음 — 건너뜀',
              file=sys.stderr)
        return 0
    k = last_a / float(df.loc[last_d, 'adj'])
    new = df[df.index > last_d]
    if has_adj:
        out = pd.DataFrame({'Date': new.index, 'Open': new['open'],
                            'Close': new['close'], 'AdjClose': new['adj'] * k})
        cols = ['Date', 'Open', 'Close', 'AdjClose']
    else:
        out = pd.DataFrame({'Date': new.index, 'Open': new['open'],
                            'Close': new['adj'] * k,
                            'Volume': new['volume'].fillna(0), 'Raw': new['close']})
        cols = ['Date', 'Open', 'Close', 'Volume', 'Raw']
    return append_rows(path, out, cols)


def splice_tnx(path):
    """금리(^TNX)는 수익률이 아니라 **수준**이라 이음 없이 원시 종가를 붙인다."""
    old = read_csv(path)
    last_d = old['Date'].iloc[-1]
    df = chart('^TNX')
    new = df[df.index > last_d]
    out = pd.DataFrame({'Date': new.index, 'Open': new['open'], 'Close': new['close']})
    return append_rows(path, out, ['Date', 'Open', 'Close'])


def splice_gold(path):
    """LBMA 오후 고시는 야후에 없다. GLD 수정주가 **수익률**로 잇는다 (비율 이음과 동일)."""
    old = read_csv(path)
    last_d, last_c = old['Date'].iloc[-1], float(old['Close'].iloc[-1])
    df = chart('GLD')
    if last_d not in df.index:
        print(f'  {os.path.basename(path):22s} [경고] 이음날 {last_d.date()} 이 야후에 없음 — 건너뜀',
              file=sys.stderr)
        return 0
    k = last_c / float(df.loc[last_d, 'adj'])
    new = df[df.index > last_d]
    out = pd.DataFrame({'Date': new.index, 'Close': new['adj'] * k})
    return append_rows(path, out, ['Date', 'Close'])


def refresh_fx(path):
    """FRED 공식 CSV 전체 교체. 실패해도 치명적이지 않다(ffill 로 며칠 버팀)."""
    url = 'https://fred.stlouisfed.org/graphs/fredgraph.csv?id=DEXKOUS'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read().decode('utf-8', 'replace')
    n_old = sum(1 for _ in io.open(path, encoding='utf-8')) - 1
    n_new = txt.count('\n') - 1
    if n_new < n_old:                      # 원천이 갑자기 짧아지면 뭔가 잘못된 것
        print(f'  fred_DEXKOUS.csv       [경고] 새 파일({n_new}행)이 기존({n_old}행)보다 짧음 — 유지',
              file=sys.stderr)
        return 0
    io.open(path, 'w', encoding='utf-8', newline='').write(txt)
    print(f'  fred_DEXKOUS.csv       {n_old} → {n_new}행 (전체 교체, ~{txt.strip().rsplit(chr(10),1)[-1].split(",")[0]})')
    return n_new - n_old


def main():
    if not os.path.exists('qqq_us_d.csv'):
        sys.exit('저장소 루트에서 실행해야 한다: python deploy/refresh_hist.py')
    total = 0
    print('== 미국 3종 (수정주가 비율 이음) ==')
    for p, s in [('qqq_us_d.csv', 'QQQ'), ('qld_us_d.csv', 'QLD'), ('schd_us_d.csv', 'SCHD')]:
        total += splice_us(p, s)
    print('== 보조 시계열 ==')
    total += splice_tnx('data/hist/yahoo_TNX.csv')
    total += splice_gold('data/hist/lbma_gold_pm.csv')
    try:
        total += refresh_fx('data/hist/fred_DEXKOUS.csv')
    except Exception as e:
        print(f'  fred_DEXKOUS.csv       [경고] FRED 실패({e}) — 기존 유지', file=sys.stderr)
    print('== 한국 실물 + 달력 ==')
    for p, s in [('data/hist/kr__5EKS11.csv', '^KS11'),
                 ('data/hist/kr_133690_KS.csv', '133690.KS'),
                 ('data/hist/kr_418660_KS.csv', '418660.KS'),
                 ('data/hist/kr_458730_KS.csv', '458730.KS'),
                 ('data/hist/kr_305080_KS.csv', '305080.KS'),
                 ('data/hist/kr_411060_KS.csv', '411060.KS')]:
        total += splice_kr(p, s)
    print(f'\n총 추가 {total}행')
    return total


if __name__ == '__main__':
    main()
