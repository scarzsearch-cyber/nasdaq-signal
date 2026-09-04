# -*- coding: utf-8 -*-
"""
[v23] 방어자산 확장용 원자료 다운로더

v21 까지 방어자산 후보는 전부 주식 계열이었다(현금·T-bill·가치주·배당주).
국채·금을 넣으려면 아래 시계열이 필요하다. 전부 data/hist/ 에 캐시하고,
파일이 이미 있으면 건너뛴다(--force 로 강제 갱신).

| 저장 파일 | 출처 | 기간 | 쓰는 곳 |
|---|---|---|---|
| yahoo_TNX.csv | Yahoo ^TNX (10Y 국채금리, %) | 1962~ | 10년 국채 총수익 합성 |
| yahoo_TYX.csv | Yahoo ^TYX (30Y 국채금리, %) | 1977~ | 30년 국채 총수익 합성 |
| yahoo_IEF.csv | Yahoo IEF (7-10Y 실물) | 2002~ | 10년 합성 교차검증 |
| yahoo_TLT.csv | Yahoo TLT (20+Y 실물) | 2002~ | 30년 합성 교차검증 |
| lbma_gold_pm.csv | LBMA 런던 오후 고시(USD/oz) | 1968~ | 금 |
| yahoo_GLD.csv | Yahoo GLD | 2004~ | 금 교차검증 |
| kr_132030_KS.csv | KODEX 골드선물(H) | 2010~ | 국내 실물 검증 |
| kr_411060_KS.csv | ACE KRX금현물 | 2021~ | 국내 실물 검증 |
| kr_305080_KS.csv | TIGER 미국채10년선물 | 2018~ | 국내 실물 검증 |
| kr_308620_KS.csv | KODEX 미국10년국채선물 | 2018~ | 국내 실물 검증 |
| kr_453850_KS.csv | ACE 미국30년국채액티브(H) | 2023~ | 국내 실물 검증 |
| kr_148070_KS.csv | KIWOOM 국고채10년 (한국 국채) | 2011~ | 국내 실물 검증 |

주: FRED 는 이 환경에서 접속이 막혀 있어(타임아웃) DGS10 대신 Yahoo ^TNX 를 썼다.
    둘 다 미 재무부 상수만기(CMT) 고시를 나르는 같은 원천이다.

실행:  python hist_fetch.py [--force]
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import datetime
import json
import os
import sys
import tempfile
import time
import urllib.parse
import urllib.request

import pandas as pd

DIR = 'data/hist'
UA = {'User-Agent': 'Mozilla/5.0'}

YAHOO = [('^TNX', 'yahoo_TNX.csv'), ('^TYX', 'yahoo_TYX.csv'),
         ('IEF', 'yahoo_IEF.csv'), ('TLT', 'yahoo_TLT.csv'),
         ('GLD', 'yahoo_GLD.csv'), ('GC=F', 'yahoo_GCF.csv'),
         ('132030.KS', 'kr_132030_KS.csv'), ('411060.KS', 'kr_411060_KS.csv'),
         ('305080.KS', 'kr_305080_KS.csv'), ('308620.KS', 'kr_308620_KS.csv'),
         ('453850.KS', 'kr_453850_KS.csv'), ('148070.KS', 'kr_148070_KS.csv')]

LBMA = ('https://prices.lbma.org.uk/json/gold_pm.json', 'lbma_gold_pm.csv')


def _get(url, timeout=45):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def fetch_yahoo(sym, start=1960):
    """Yahoo chart v8. deploy/update_signal.py 와 같은 엔드포인트를 쓴다."""
    p1 = int(datetime.datetime(start, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    p2 = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/%s'
           '?period1=%d&period2=%d&interval=1d' % (urllib.parse.quote(sym), p1, p2))
    raw = json.loads(_get(url).decode('utf-8', 'replace'))
    r = raw['chart']['result'][0]
    idx = pd.to_datetime(r['timestamp'], unit='s', utc=True).tz_convert(None).normalize()
    q = r['indicators']['quote'][0]
    df = pd.DataFrame({'Date': idx, 'Open': q.get('open'), 'Close': q.get('close'),
                       'Volume': q.get('volume'), 'Raw': q.get('close')})
    # 배당·분할 반영 종가가 있으면 그것을 Close 로 쓴다(ETF 총수익 기준 유지)
    adj = r['indicators'].get('adjclose')
    if adj and adj[0].get('adjclose'):
        df['Close'] = adj[0]['adjclose']
    df = df.dropna(subset=['Close']).drop_duplicates('Date', keep='last').sort_values('Date')
    return df


def fetch_lbma():
    raw = json.loads(_get(LBMA[0], timeout=60).decode('utf-8', 'replace'))
    rows = [(r['d'], r['v'][0]) for r in raw if r.get('v') and r['v'][0] is not None]
    df = pd.DataFrame(rows, columns=['Date', 'Close'])
    df['Date'] = pd.to_datetime(df['Date'])
    return df.drop_duplicates('Date', keep='last').sort_values('Date')


def save_guarded(path, df, label):
    """[코드리뷰 2026-09-04] 기존 캐시보다 **짧아지거나 뒤로 가면 쓰지 않는다.**

    종전에는 --force 경로에 아무 하한이 없어서, 200 OK 지만 잘린 응답이 오면
    수만 행짜리 원자료를 몇 행으로 덮어쓰고 「저장」이라고 찍었다(실측: yahoo_TNX.csv
    16,151행 1962-01-02~ -> 3행 2025-01-01~, 예외 없음, 종료코드 0).
    yahoo_TNX 는 DA.ust_tr 을 통해 방어 바스켓의 국채 40% 다리를 놓는 유일한 원자료다.
    deploy/refresh_hist.py 는 같은 위험에 「짧아지면 유지」 가드를 갖고 있고 여기만 없었다.
    """
    if df is None or df.empty:
        print('거부  %-22s 받은 행이 0' % label)
        return False
    if os.path.exists(path):
        try:
            old = pd.read_csv(path, parse_dates=['Date'])
        except Exception as e:
            print('거부  %-22s 기존 파일을 못 읽어 비교 불가 (%s)' % (label, type(e).__name__))
            return False
        if len(df) < len(old) * 0.9:
            print('거부  %-22s 행이 %d -> %d 로 줄어든다 (10%% 여유 밖)'
                  % (label, len(old), len(df)))
            return False
        if df['Date'].iloc[-1] < old['Date'].iloc[-1]:
            print('거부  %-22s 마지막 날짜가 %s -> %s 로 뒤로 간다'
                  % (label, old['Date'].iloc[-1].date(), df['Date'].iloc[-1].date()))
            return False
    # 같은 디렉터리에 완성본을 먼저 쓴 뒤 원자적으로 교체한다. 종전 직접 쓰기는
    # 프로세스 중단·디스크 오류 때 정상 캐시를 반쪽 CSV로 만들 수 있었다.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=os.path.dirname(path) or '.',
                                         prefix=os.path.basename(path) + '.',
                                         suffix='.tmp', delete=False) as f:
            tmp = f.name
            df.to_csv(f, index=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
    print('저장  %-22s n=%-6d %s ~ %s' % (label, len(df), df['Date'].iloc[0].date(),
                                         df['Date'].iloc[-1].date()))
    return True


def main(force=False):
    os.makedirs(DIR, exist_ok=True)
    failed = []
    for sym, fn in YAHOO:
        p = os.path.join(DIR, fn)
        if os.path.exists(p) and not force:
            print('skip  %-22s (이미 있음)' % fn)
            continue
        try:
            if not save_guarded(p, fetch_yahoo(sym), fn):
                failed.append(fn)
        except Exception as e:
            print('실패  %-22s %s %s' % (fn, type(e).__name__, str(e)[:50]))
            failed.append(fn)
        time.sleep(0.4)

    p = os.path.join(DIR, LBMA[1])
    if os.path.exists(p) and not force:
        print('skip  %-22s (이미 있음)' % LBMA[1])
    else:
        # [코드리뷰 2026-09-04] 종전엔 여기만 try 밖이라 LBMA 실패가 스크립트를 죽였다
        #   (Yahoo 실패는 12개 전부 실패해도 종료코드 0). 두 경로를 같게 맞춘다.
        try:
            if not save_guarded(p, fetch_lbma(), LBMA[1]):
                failed.append(LBMA[1])
        except Exception as e:
            print('실패  %-22s %s %s' % (LBMA[1], type(e).__name__, str(e)[:50]))
            failed.append(LBMA[1])

    if failed:
        print('\n[경고] %d개 파일을 갱신하지 못했다: %s' % (len(failed), ', '.join(failed)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(force='--force' in sys.argv))
