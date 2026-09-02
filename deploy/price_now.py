# -*- coding: utf-8 -*-
"""
[v145] 4다리 시세 스냅샷 — `data/price.json`

목적: 소유자가 「굳이 주식앱을 안 봐도」 화면에서 보유 자산 시세를 훑을 수 있게.
      실시간이 아니다 — 장중 30분 간격 스냅샷이며, 화면은 **언제 잰 값인지**를
      항상 같이 보여준다(신선도 원칙).

★ 전략 무접촉: 이 파일은 **신호 판정에 쓰이지 않는다.**
  판정은 `update_signal.py` 가 QQQ 미국 종가로만 한다(동결 규칙). 여기서 만든
  값은 화면 표시 전용이고, 실패해도 신호·판정에 아무 영향이 없다(그래서 항상 exit 0).

출처: `nav_collect.py` 와 **같은 엔드포인트**(네이버 ETF 시세 목록).
      새 의존성·새 실패 모드를 만들지 않으려고 일부러 같은 곳을 쓴다.
      응답은 cp949 다 (utf-8 아님 — nav_collect.py 가 겪은 것과 같은 함정).

실행:  python deploy/price_now.py
"""
import io
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'price.json')

SRC = 'https://finance.naver.com/api/sise/etfItemList.nhn'
UA = {'User-Agent': 'Mozilla/5.0',
      'Referer': 'https://finance.naver.com/sise/etf.naver'}

# 동결 4다리 + 참고 1배. freeze.json 과 같은 코드다 — 여기서 비중은 다루지 않는다.
CODES = {
    '418660': '공격',
    '458730': '방어',
    '305080': '방어',
    '411060': '방어',
    '133690': '참고',      # 1배 — 레버리지 괴리 감각용
}
KST = timezone(timedelta(hours=9))


def fetch_naver_list():
    raw = urllib.request.urlopen(
        urllib.request.Request(SRC, headers=UA), timeout=40).read()
    return json.loads(raw.decode('cp949'))['result']['etfItemList']


def fetch():
    """[2026-09-03 보험] 1차 네이버 ETF 목록(NAV 포함) → 못 받거나 4다리 중 빠진 종목이 있으면 그 종목만
    `kr_sources` 예비 체인(네이버 polling → 네이버 모바일 → 다음(카카오) → 토스 → 야후 → 구글)이 채운다.
    예비 출처엔 NAV 가 없다 → 화면은 괴리 배지만 숨긴다(devBadge 는 nav 없으면 빈 문자열). 판정 무접촉."""
    items, have = [], set()
    try:
        items = [it for it in fetch_naver_list() if str(it.get('itemcode')) in CODES]
        have = {str(it.get('itemcode')) for it in items
                if isinstance(it.get('nowVal'), (int, float)) and it.get('nowVal') > 0}
    except Exception as e:
        print('[price] 네이버 목록 실패(%s) — 예비 출처로' % e, file=sys.stderr)
    missing = [c for c in CODES if c not in have]
    if missing:
        import kr_sources
        items += kr_sources.quotes(missing)
    return items


def build(items):
    now = datetime.now(KST)
    out = {}
    for it in items:
        c = str(it.get('itemcode', ''))
        if c not in CODES:
            continue
        px = it.get('nowVal')
        if not isinstance(px, (int, float)) or px <= 0:
            continue                      # 값이 이상하면 아예 싣지 않는다 (화면은 없으면 숨김)
        nav = it.get('nav')
        row = {
            'name': it.get('itemname') or '',
            'role': CODES[c],
            'px': int(px),
            'chg': it.get('changeVal'),
            'chg_pct': it.get('changeRate'),
            'volume': it.get('quant'),
        }
        # 괴리율 — 설명서 §③ 「주문 전에」가 쓰라고 한 그 숫자다.
        if isinstance(nav, (int, float)) and nav > 0:
            row['nav'] = round(float(nav), 1)
            row['dev_pct'] = round((px / float(nav) - 1) * 100, 3)
        out[c] = row
    # [2026-09-03] 어느 출처가 채웠는지 남긴다 — 예비가 끼면 「naver etfItemList + daum(kakao)」처럼.
    srcs = sorted({str(it.get('_source') or 'naver etfItemList') for it in items
                   if str(it.get('itemcode', '')) in out})
    return {
        'as_of_kst': now.strftime('%Y-%m-%d %H:%M'),
        'as_of_iso': now.isoformat(timespec='seconds'),
        'source': ' + '.join(srcs) if srcs else 'naver etfItemList',
        'note': '표시 전용 — 신호 판정에 쓰지 않는다',
        'items': out,
    }


def main():
    try:
        items = fetch()
    except Exception as e:
        # 시세를 못 받는 것은 사고가 아니다 — 화면이 옛 스냅샷을 그대로 두고
        # 「언제 잰 값인지」로 알린다. 기존 파일을 절대 덮어쓰지 않는다.
        print('[price] 수집 실패(%s) — 기존 파일 유지' % e, file=sys.stderr)
        return 0

    doc = build(items)
    if not doc['items']:
        print('[price] 대상 종목 0건 — 기존 파일 유지', file=sys.stderr)
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('[price] %s · %d종목' % (doc['as_of_kst'], len(doc['items'])))
    for c, r in doc['items'].items():
        print('   %s %-28s %8s원  %+.2f%%' %
              (c, r['name'][:28], format(r['px'], ','), r.get('chg_pct') or 0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
