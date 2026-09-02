#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[2026-09-03] 한국 시세 **예비 출처 체인** — 표시·기록·원자료 전용, 판정 무접촉.

소유자 지시: 「한국 시세나 종가는 해외 사이트뿐 아니라 네이버·구글·토스·카카오·증권사 등 뭐든 —
개선이 되고 보험료가 없다면 보험은 많을수록 좋다」.

어디에 붙나 (셋 다 **표시·기록·원자료** 경로 — 전환 판정은 여전히 QQQ 미국 종가 3중 체인 + 캐시):
  · price_now.py / price_poll.py  장중 스냅샷 `price.json` — 네이버 목록이 죽거나 종목이 빠지면 그 종목만 예비로
  · nav_collect.py                일별 NAV 기록 — 네이버 목록이 죽으면 예비로(예비엔 NAV 가 없어 그날 행은 안 쌓임)
  · refresh_hist.py splice_kr     월간 원자료 연장 — 야후가 죽으면 네이버 일봉 XML 로

체인 (종목별, 앞에서부터, 12초씩):
  네이버 polling → 네이버 모바일 basic → 다음(카카오) quotes → 토스 v1 stock-prices → 야후 chart → 구글 파이낸스(HTML)
실측 2026-09-03 (KR IP): 여섯 전부 응답 · 값 일치(418660 종가 37,935). 구글은 HTML 이라 취약 — 맨 뒤.
증권사 API(미래·삼성·한투)는 넣지 않았다 — 키가 계좌에 묶이고 토큰이 하루짜리라 「보험료 0」이 아니다.

실행:
  python deploy/kr_sources.py --probe           # 출처별 생존 표 (Actions 러너에서도: source-probe.yml)
  python deploy/kr_sources.py 418660 458730     # 예비 체인으로 시세 JSON
"""
import datetime as dt
import gzip
import json
import re
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125',
      'Accept': 'application/json,text/html;q=0.9,*/*;q=0.8',
      'Accept-Language': 'ko-KR,ko;q=0.9'}
TIMEOUT = 12
KST = dt.timezone(dt.timedelta(hours=9))
LEGS = ('418660', '458730', '305080', '411060')


def _get(url, hdr=None, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={**UA, **(hdr or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
    if b[:2] == b'\x1f\x8b':
        b = gzip.decompress(b)
    return b


def _num(x):
    """'37,935' · '-3.69' · 37935.0 → float. 못 읽으면 None."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace(',', '').strip()
    return float(s) if re.match(r'^-?\d+(\.\d+)?$', s) else None


def _item(code, px, chg_pct=None, chg=None, vol=None, name='', src=''):
    """price_now.build() 가 먹는 네이버 목록 모양 — NAV 는 예비 출처에 없다(None → 화면은 괴리 배지만 숨김)."""
    if not (px and px > 0):
        raise ValueError('가격 없음')
    return {'itemcode': code, 'itemname': name or '', 'nowVal': int(round(px)), 'nav': None,
            'changeVal': chg, 'changeRate': None if chg_pct is None else round(chg_pct, 2),
            'quant': vol, 'marketSum': None, '_source': src}


# ── 1차: 네이버 ETF 목록 (NAV 포함 · cp949) ─────────────────────────────────────
def naver_list():
    b = _get('https://finance.naver.com/api/sise/etfItemList.nhn',
             {'Referer': 'https://finance.naver.com/sise/etf.naver', 'Accept': 'application/json'}, 40)
    try:
        txt = b.decode('cp949')
    except UnicodeDecodeError:
        txt = b.decode('utf-8', 'replace')
    return json.loads(txt)['result']['etfItemList']


# ── 예비 출처 (종목별) ───────────────────────────────────────────────────────────
def naver_polling(code):
    j = json.loads(_get(f'https://polling.finance.naver.com/api/realtime/domestic/stock/{code}'))['datas'][0]
    return _item(code, _num(j.get('closePrice')), _num(j.get('fluctuationsRatio')),
                 _num(j.get('compareToPreviousClosePrice')), _num(j.get('accumulatedTradingVolume')),
                 j.get('stockName', ''), 'naver polling')


def naver_mobile(code):
    j = json.loads(_get(f'https://m.stock.naver.com/api/stock/{code}/basic', {'Referer': 'https://m.stock.naver.com/'}))
    return _item(code, _num(j.get('closePrice')), _num(j.get('fluctuationsRatio')),
                 _num(j.get('compareToPreviousClosePrice')), None, j.get('stockName', ''), 'naver mobile')


def daum(code):
    j = json.loads(_get(f'https://finance.daum.net/api/quotes/A{code}?summary=false&changeStatistics=true',
                        {'Referer': f'https://finance.daum.net/quotes/A{code}'}))
    cr = _num(j.get('changeRate'))
    return _item(code, _num(j.get('tradePrice')), None if cr is None else cr * 100,
                 _num(j.get('changePrice')), _num(j.get('accTradeVolume')), j.get('name', ''), 'daum(kakao)')


def toss(code):
    j = json.loads(_get(f'https://wts-info-api.tossinvest.com/api/v1/stock-prices/A{code}',
                        {'Referer': 'https://tossinvest.com/'}))['result']
    px, base = _num(j.get('close')), _num(j.get('base'))
    chg_pct = (px / base - 1) * 100 if (px and base) else None
    return _item(code, px, chg_pct, (px - base) if (px and base) else None, _num(j.get('volume')), '', 'toss')


def yahoo(code):
    m = json.loads(_get(f'https://query1.finance.yahoo.com/v8/finance/chart/{code}.KS?range=2d&interval=1d'))
    m = m['chart']['result'][0]['meta']
    px, prev = _num(m.get('regularMarketPrice')), _num(m.get('chartPreviousClose'))
    chg_pct = (px / prev - 1) * 100 if (px and prev) else None
    return _item(code, px, chg_pct, (px - prev) if (px and prev) else None, _num(m.get('regularMarketVolume')), '', 'yahoo')


def google(code):
    html = _get(f'https://www.google.com/finance/quote/{code}:KRX', {'Accept': 'text/html'}).decode('utf-8', 'replace')
    m = re.search(r'₩([\d,]+\.\d\d)', html)          # 종목 페이지 첫 ₩ 금액 = 현재가 (실측 2026-09-03)
    return _item(code, _num(m.group(1)) if m else None, None, None, None, '', 'google(html)')


CHAIN = [('naver polling', naver_polling), ('naver mobile', naver_mobile), ('daum(kakao)', daum),
         ('toss', toss), ('yahoo', yahoo), ('google(html)', google)]


def quote(code):
    """예비 체인에서 첫 성공을 돌려준다. 전부 실패하면 None (조용히 — 화면은 옛 값을 「몇 분 전」으로 보여준다)."""
    errs = []
    for nm, fn in CHAIN:
        try:
            return fn(code)
        except Exception as e:
            errs.append(f'{nm}:{type(e).__name__}')
    print(f'[kr_sources] {code} 전 출처 실패 — {" · ".join(errs)}', file=sys.stderr)
    return None


def quotes(codes):
    out = []
    for c in codes:
        it = quote(c)
        if it:
            out.append(it)
    return out


# ── 원자료 보강: 네이버 일봉 XML ─────────────────────────────────────────────────
def history(symbol, count=60):
    """네이버 fchart 일봉 → [(date, open, high, low, close, volume)]. ⚠ 수정주가가 아니다(배당락 미반영)."""
    sym = 'KOSPI' if symbol in ('^KS11', 'KOSPI') else str(symbol).split('.')[0]
    xml = _get(f'https://fchart.stock.naver.com/sise.nhn?symbol={sym}&timeframe=day&count={count}&requestType=0',
               timeout=30).decode('utf-8', 'replace')
    rows = []
    for d in re.findall(r'data="([^"]+)"', xml):
        p = d.split('|')
        if len(p) < 6:
            continue
        try:
            rows.append((dt.datetime.strptime(p[0], '%Y%m%d'), *[float(x) for x in p[1:6]]))
        except ValueError:
            continue
    if not rows:
        raise RuntimeError(f'네이버 일봉 응답에 행이 없다: {sym}')
    return rows


def history_df(symbol, count=60):
    """refresh_hist.chart() 와 같은 모양(open/high/low/close/adj/volume, adj=close) — 장중 봉은 잘라낸다."""
    import pandas as pd
    rows = history(symbol, count)
    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume']).set_index('date').sort_index()
    df['adj'] = df['close']
    now = dt.datetime.now(KST)
    if len(df) and df.index[-1].date() == now.date() and (now.hour, now.minute) < (15, 40):
        df = df.iloc[:-1]                        # 오늘 장중이면 마지막 봉 제거 (chart() 의 장중 가드와 같은 뜻)
    return df[['open', 'high', 'low', 'close', 'adj', 'volume']]


# ── 생존 점검 ──────────────────────────────────────────────────────────────────
def probe(codes=LEGS):
    print(f'예비 출처 생존 점검 · {dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")}')
    t = time.time()
    try:
        lst = naver_list()
        by = {str(i['itemcode']): i for i in lst}
        miss = [c for c in codes if c not in by or not by[c].get('nowVal')]
        print(f'  1차 네이버 목록      OK  {len(lst)}종목 {time.time()-t:4.1f}s' + (f'  ⚠ 빠진 종목 {miss}' if miss else '  (4다리 전부 · NAV 포함)'))
        primary_ok = not miss
    except Exception as e:
        print(f'  1차 네이버 목록      FAIL {type(e).__name__}: {str(e)[:60]}')
        primary_ok = False
    alive = {}
    for nm, fn in CHAIN:
        row, okn = [], 0
        for c in codes:
            t = time.time()
            try:
                it = fn(c); row.append(f'{c}:{it["nowVal"]:,}'); okn += 1
            except Exception as e:
                row.append(f'{c}:{type(e).__name__}')
        alive[nm] = okn
        print(f'  {nm:<18} {"OK " if okn == len(codes) else ("부분" if okn else "FAIL")}  ' + '  '.join(row))
    t = time.time()
    try:
        h = history('418660.KS', 5)
        print(f'  네이버 일봉(원자료)   OK  {h[-1][0].date()} 종가 {h[-1][4]:,.0f} {time.time()-t:4.1f}s')
        hist_ok = True
    except Exception as e:
        print(f'  네이버 일봉(원자료)   FAIL {type(e).__name__}')
        hist_ok = False
    full = sum(1 for v in alive.values() if v == len(codes))
    print(f'→ 1차 {"살아있음" if primary_ok else "죽음"} · 예비 {full}/{len(CHAIN)} 출처가 4다리 전부 응답 · 원자료 예비 {"OK" if hist_ok else "FAIL"}')
    probe_us()
    return primary_ok or full >= 1


def probe_us():
    """판정 경로(QQQ 종가)의 출처 3개 생존 — update_signal 의 함수를 **읽기만** 호출한다(파일 쓰기 0 · 판정 0).
    fetch_naver 는 미국장이 열려 있으면 「확정 종가 아님」으로 스스로 거부한다 — 그건 정상(가드 작동)이다."""
    print('판정 경로(QQQ 종가) 출처 생존 — 읽기만, 판정·파일 무접촉')
    try:
        import update_signal as U
    except Exception as e:
        print(f'  update_signal 임포트 실패 {type(e).__name__} — 건너뜀')
        return
    for nm, fn in (('야후 query1', lambda: U.fetch('query1')), ('야후 query2', lambda: U.fetch('query2')),
                   ('네이버 해외종목', U.fetch_naver)):
        t = time.time()
        try:
            s = fn()
            print(f'  {nm:<18} OK  마지막 {s.index[-1].date()} 종가 {float(s.iloc[-1]):.2f} {time.time()-t:4.1f}s')
        except Exception as e:
            msg = str(e)
            tag = '장중(정상 거부)' if 'marketStatus' in msg or '새롭지 않음' in msg else 'FAIL'
            print(f'  {nm:<18} {tag} {type(e).__name__}: {msg[:70]}')


if __name__ == '__main__':
    if '--probe' in sys.argv:
        sys.exit(0 if probe() else 1)
    print(json.dumps(quotes([a for a in sys.argv[1:] if a.isdigit()] or ['418660']), ensure_ascii=False, indent=1))
