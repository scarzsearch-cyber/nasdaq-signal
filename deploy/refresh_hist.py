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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_check import validate_frame            # noqa: E402  [v73] 검증 게이트

FAILURES = []                                    # 검증 실패 파일 목록

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


def append_rows(path, new_df, cols, price_cols=('Close',), prev=None, allow_move=()):
    """new_df 를 검증 게이트에 통과시킨 뒤에만 파일 끝에 붙인다. 붙일 게 없으면 0.
    [v73] 검증 실패 시: 쓰지 않고(기존 데이터 유지) FAILURES 에 기록 — main 이
    종료코드 1 로 끝나 workflow 가 build_stats 를 돌리지 않는다 (downstream 보호)."""
    if new_df.empty:
        print(f'  {os.path.basename(path):22s} 추가 0행 (이미 최신)')
        return 0
    probs = validate_frame(new_df, os.path.basename(path), list(price_cols),
                           prev_close=prev, allow_move_cols=allow_move)
    if probs:
        for msg in probs:
            print(f'  [검증실패] {msg}', file=sys.stderr)
        print(f'  {os.path.basename(path):22s} 갱신 중단 — 기존 데이터 유지, 수동 검증 필요',
              file=sys.stderr)
        FAILURES.append(os.path.basename(path))
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
    return append_rows(path, out, ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'],
                       price_cols=('Close', 'Open'), prev=last_c)


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
    try:
        df = chart(symbol)
    except Exception as e:
        # [2026-09-03 보험] 야후가 죽으면 네이버 일봉 XML 로 잇는다. ⚠ 수정주가가 아니라 배당락이 반영되지 않는다 —
        #   이음 비율 k 가 수준 차이는 흡수하지만 458730(월배당) 은 배당락일마다 0.3% 안팎이 어긋난다.
        #   야후가 돌아오면 다음 달 이음은 다시 수정주가 기준이다(이미 붙은 행은 남는다 — 월간 성과표엔 무시할 크기).
        print(f'  {os.path.basename(path):22s} [경고] 야후 실패({type(e).__name__}) — 네이버 일봉으로 보강(배당락 미반영)',
              file=sys.stderr)
        import kr_sources
        df = kr_sources.history_df(symbol, count=90)
    if last_d not in df.index:
        print(f'  {os.path.basename(path):22s} [경고] 이음날 {last_d.date()} 이 출처에 없음 — 건너뜀',
              file=sys.stderr)
        return 0
    k = last_a / float(df.loc[last_d, 'adj'])
    new = df[df.index > last_d]
    if has_adj:
        out = pd.DataFrame({'Date': new.index, 'Open': new['open'],
                            'Close': new['close'], 'AdjClose': new['adj'] * k})
        cols = ['Date', 'Open', 'Close', 'AdjClose']
        pcols = ('AdjClose', 'Close', 'Open')
    else:
        out = pd.DataFrame({'Date': new.index, 'Open': new['open'],
                            'Close': new['adj'] * k,
                            'Volume': new['volume'].fillna(0), 'Raw': new['close']})
        cols = ['Date', 'Open', 'Close', 'Volume', 'Raw']
        pcols = ('Close', 'Open')
    return append_rows(path, out, cols, price_cols=pcols, prev=last_a)


def splice_tnx(path):
    """금리(^TNX)는 수익률이 아니라 **수준**이라 이음 없이 원시 종가를 붙인다."""
    old = read_csv(path)
    last_d = old['Date'].iloc[-1]
    df = chart('^TNX')
    new = df[df.index > last_d]
    out = pd.DataFrame({'Date': new.index, 'Open': new['open'], 'Close': new['close']})
    # 금리는 수준이라 ±30% 검사 제외 (2020-03 처럼 하루 -40% 가 실제로 있다)
    return append_rows(path, out, ['Date', 'Open', 'Close'],
                       price_cols=('Close', 'Open'), allow_move=('Close', 'Open'))


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
    return append_rows(path, out, ['Date', 'Close'], price_cols=('Close',), prev=last_c)


def refresh_fx(path):
    """FRED 공식 CSV 전체 교체. FRED 가 죽어 있으면 **야후 KRW=X 로 최근 구간만 이어 붙인다** (보험, 2026-09-03).

    [보험을 든 이유] 2026-09-02~03 FRED 가 이틀째 타임아웃이었다(urllib·curl 모두). 종전엔 예외 → main 의
    「기존 유지」로만 물러섰는데, 달을 넘겨 계속 죽어 있으면 원화 시나리오의 환율이 조용히 낡는다.
    야후 KRW=X 종가는 DEXKOUS(뉴욕 정오 매입환율)와 고시 시점이 달라 0.1~0.3% 차이가 있으나 ffill 로
    버티는 것보다 낫고, FRED 가 돌아오면 전체 교체가 야후 행을 덮어쓴다.
    ★ 그래서 「짧아지면 유지」 가드를 행 수가 아니라 **마지막 날짜**로 판정한다 — 야후 행이 몇 개 붙은 뒤엔
      FRED 파일이 행 수로는 잠깐 짧을 수 있다(FRED 는 1주쯤 늦게 고시한다). 행 수 가드는 손상 탐지용으로
      10% 여유를 두고 남긴다."""
    old = pd.read_csv(path)
    n_old = len(old)
    old_last = pd.to_datetime(old.iloc[:, 0], errors='coerce').max()
    try:
        url = 'https://fred.stlouisfed.org/graphs/fredgraph.csv?id=DEXKOUS'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode('utf-8', 'replace')
        if not txt.startswith('observation_date'):
            raise RuntimeError('FRED 응답 형식 아님')
        new = pd.read_csv(io.StringIO(txt))
        n_new = len(new)
        new_last = pd.to_datetime(new.iloc[:, 0], errors='coerce').max()
        if n_new < n_old * 0.9 or new_last < old_last - pd.Timedelta(days=45):
            print(f'  fred_DEXKOUS.csv       [경고] 새 파일({n_new}행, ~{new_last.date()})이 기존({n_old}행, '
                  f'~{old_last.date()})보다 뒤처짐 — 유지', file=sys.stderr)
            return 0
        io.open(path, 'w', encoding='utf-8', newline='').write(txt)
        print(f'  fred_DEXKOUS.csv       {n_old} → {n_new}행 (FRED 전체 교체, ~{new_last.date()})')
        return n_new - n_old
    except Exception as e:
        print(f'  fred_DEXKOUS.csv       [경고] FRED 실패({type(e).__name__}: {e}) — 야후 KRW=X 로 최근 구간 보강',
              file=sys.stderr)
    # ── 보험: 야후 KRW=X (chart() 는 장중 봉을 이미 잘라 준다) ──
    df = chart('KRW=X', years=1)
    add = df.loc[df.index > old_last, 'close'].dropna()
    if add.empty:
        print(f'  fred_DEXKOUS.csv       보강할 행 없음 (~{old_last.date()} 이후 야후 종가 없음)')
        return 0
    with io.open(path, 'a', encoding='utf-8', newline='') as f:
        for d, v in add.items():
            f.write(f'{d.date().isoformat()},{v:.4f}\n')
    print(f'  fred_DEXKOUS.csv       야후 KRW=X 로 {len(add)}행 보강 (~{add.index[-1].date()}) — FRED 복구 시 전체 교체됨')
    return len(add)


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
    # [2026-09-04 코드리뷰] ★ append_rows 의 docstring 이 「main 이 종료코드 1 로 끝나
    #   workflow 가 build_stats 를 돌리지 않는다(downstream 보호)」고 **약속하는데 그 코드가
    #   없었다.** FAILURES 에 쌓기만 하고 아무도 읽지 않았고, main 은 행 수를 돌려주며
    #   __main__ 은 그 값을 버려 언제나 0 으로 끝났다.
    #   결과: 원자료가 검증에 막혀 옛날 그대로인데 monthly-stats 는 다음 스텝으로 넘어가
    #   build_stats 가 **낡은 입력으로 계산해 새 generated_at 을 찍고 커밋한다.**
    #   그러면 파수꾼 stats 모드(45일 문턱)도 「방금 갱신됨」으로 보므로 **낡음이 보이지
    #   않게 된다** — 조용히 틀린 값을 오래 믿게 되는, 이 저장소가 가장 싫어하는 실패다.
    if FAILURES:
        for ln in ['', f'[실패] 검증에 막혀 갱신하지 못한 파일 {len(FAILURES)}개:',
                   *[f'  · {f}' for f in FAILURES],
                   '기존 데이터는 그대로 있다. 위 [검증실패] 줄을 보고 손으로 확인할 것.',
                   '(이 스텝이 실패하므로 build_stats 는 돌지 않는다 — 낡은 입력으로',
                   ' 새 성과표를 찍어 낡음을 감추는 것을 막는다.)']:
            print(ln, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
