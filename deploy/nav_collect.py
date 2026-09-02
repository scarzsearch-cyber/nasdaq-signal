#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[v25] 국내 ETF 실측 NAV 수집기 — 진짜 괴리율을 쌓는다

v21 부터 미결이던 과제다. v24 는 iNAV 를 못 구해 **상한**(이론가 대비 잔차)만 쟀다.
이제 실측 NAV 를 얻는 경로를 찾았으므로, 매일 받아서 시계열로 쌓는다.

[왜 과거는 못 쌓는가]
  · KRX 정보데이터시스템(data.krx.co.kr) — 2026-08 현재 **로그인 필수**로 바뀌었다.
    getJsonData.cmd 가 세션 없이 부르면 본문 "LOGOUT" 과 함께 400 을 준다.
  · 발행사(미래에셋 TIGER / 한국투자 ACE) 상세 페이지의 기준가격 ajax 는
    내부 파라미터가 있어야 하고 외부 호출로는 빈 결과를 준다.
  · ETF체크 등 3자 사이트는 API 경로가 공개돼 있지 않다.
  -> **과거 NAV 는 공개 경로가 없다.** 대신 오늘부터 쌓으면 시간이 해결한다.

[출처] 네이버 금융 ETF 전종목 목록 (로그인 불필요, 약 1,160 종목)
    https://finance.naver.com/api/sise/etfItemList.nhn
  nowVal(현재가) 과 nav(순자산가치) 를 함께 준다. 괴리율 = nowVal/nav − 1.

[실행 시각 주의]
  daily-signal.yml 은 07:30 KST 에 돈다. 그때 한국장은 아직 안 열렸으므로
  받는 값은 **직전 거래일 종가 기준 NAV** 다. as_of 컬럼에 그대로 기록한다.

실행:
    python deploy/nav_collect.py            # 1회 수집 -> data/nav_history.csv 에 append
    python deploy/nav_collect.py --report   # 쌓인 것으로 괴리율 리포트
"""
import csv
import datetime as dt
import json
import os
import sys
import urllib.request

SRC = 'https://finance.naver.com/api/sise/etfItemList.nhn'
OUT = os.path.join('data', 'nav_history.csv')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      'Accept': 'application/json',
      'Referer': 'https://finance.naver.com/sise/etf.naver'}

# 전략이 실제로 쓰는 종목 + 대안 + 대조군
# [2026-08-31] 이름 2건이 운용사에서 바뀌어 있었다 — 308620 「미국채10년선물」→
# 「미국10년국채선물」, 148070 「KOSEF」→「KIWOOM」(브랜드 변경). 매칭은 itemcode 로
# 하므로 기능 영향은 0 이고, nav_history.csv 의 과거 행에는 옛 이름이 남아 있다.
WATCH = {
    '458730': 'TIGER 미국배당다우존스',
    '305080': 'TIGER 미국채10년선물',
    '411060': 'ACE KRX금현물',
    '308620': 'KODEX 미국10년국채선물',
    '132030': 'KODEX 골드선물(H)',
    '453850': 'ACE 미국30년국채액티브(H)',
    '148070': 'KIWOOM 국고채10년',
    '418660': 'TIGER 미국나스닥100레버리지',
    '133690': 'TIGER 미국나스닥100',
}

COLS = ['as_of', 'code', 'name', 'close', 'nav', 'dev_pct', 'volume', 'mktcap_eok',
        'univ_n', 'univ_med_pct', 'univ_sd_pct']


def fetch():
    """네이버 ETF 목록. [2026-09-03 보험] 죽으면 `kr_sources` 예비 체인(네이버 polling → 모바일 → 다음 → 토스 →
    야후 → 구글)으로 감시 종목만 받는다 — 예비엔 NAV 가 없어 그날 행은 안 쌓이지만(collect 가 nav 없는 종목을
    건너뛴다) 수집기 자체가 죽어 전체 단계가 실패하는 일은 없어진다. 판정 무접촉."""
    try:
        raw = urllib.request.urlopen(urllib.request.Request(SRC, headers=UA), timeout=40).read()
        return json.loads(raw.decode('utf-8', 'replace'))['result']['etfItemList']
    except Exception as e:
        print(f'[nav] 네이버 목록 실패({type(e).__name__}) — 예비 출처로 (NAV 없음 → 오늘 행은 기록 안 됨)',
              file=sys.stderr)
        import kr_sources
        return kr_sources.quotes(list(WATCH))


def universe_stats(lst):
    """전 종목 괴리율 분포 — 우리 종목이 정상 범위인지 보는 대조군."""
    d = sorted((i['nowVal'] / i['nav'] - 1) * 100
               for i in lst if i.get('nav') and abs(i['nowVal'] / i['nav'] - 1) < 0.2)
    n = len(d)
    if n < 10:
        return 0, 0.0, 0.0
    med = d[n // 2]
    mean = sum(d) / n
    sd = (sum((x - mean) ** 2 for x in d) / n) ** 0.5
    return n, med, sd


def collect(as_of=None):
    lst = fetch()
    by = {i['itemcode']: i for i in lst}
    n, med, sd = universe_stats(lst)
    as_of = as_of or dt.date.today().isoformat()

    os.makedirs('data', exist_ok=True)
    have = set()
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                have.add((r['as_of'], r['code']))

    rows = []
    for code, nm in WATCH.items():
        it = by.get(code)
        if not it or not it.get('nav'):
            continue
        if (as_of, code) in have:
            continue
        rows.append({'as_of': as_of, 'code': code, 'name': nm,
                     'close': it['nowVal'], 'nav': it['nav'],
                     'dev_pct': round((it['nowVal'] / it['nav'] - 1) * 100, 4),
                     'volume': it.get('quant', ''), 'mktcap_eok': it.get('marketSum', ''),
                     'univ_n': n, 'univ_med_pct': round(med, 4), 'univ_sd_pct': round(sd, 4)})

    new = not os.path.exists(OUT)
    with open(OUT, 'a', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new:
            w.writeheader()
        w.writerows(rows)
    print('%s  신규 %d행 기록 (전체 %d종목, 시장 중앙 %.3f%% / 표준편차 %.3f%%)'
          % (as_of, len(rows), n, med, sd))
    return rows


def report():
    if not os.path.exists(OUT):
        sys.exit('아직 수집분이 없다. 먼저 python deploy/nav_collect.py 를 돌려라.')
    with open(OUT, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    days = sorted({r['as_of'] for r in rows})
    print('===== 실측 괴리율 (시장가 / NAV − 1) =====')
    print('수집 구간 %s ~ %s  (%d 영업일)' % (days[0], days[-1], len(days)))
    print()
    print('%-8s %-28s %8s %8s %8s %8s %6s' %
          ('코드', '이름', '평균', '표준편차', '최소', '최대', 'n'))
    for code, nm in WATCH.items():
        v = [float(r['dev_pct']) for r in rows if r['code'] == code]
        if not v:
            continue
        m = sum(v) / len(v)
        sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5 if len(v) > 1 else 0.0
        print('%-8s %-28s %7.3f%% %7.3f%% %7.3f%% %7.3f%% %6d'
              % (code, nm, m, sd, min(v), max(v), len(v)))
    u = [float(r['univ_sd_pct']) for r in rows if r['univ_sd_pct']]
    if u:
        print('\n  대조군: 국내 전체 ETF 괴리율 표준편차 평균 %.3f%%' % (sum(u) / len(u)))
    if len(days) < 20:
        print('\n  ※ %d 영업일뿐이라 아직 분포를 논하기 이르다.' % len(days))
        print('    daily-signal.yml 이 매일 한 줄씩 쌓으므로 시간이 해결한다.')


if __name__ == '__main__':
    if '--report' in sys.argv:
        report()
    else:
        collect()
