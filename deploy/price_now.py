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
import math
import os
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
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


def _finite_number(value, *, positive=False, nonnegative=False):
    """JSON 숫자 중 유한값만 허용한다. bool 은 int 의 하위형이라 명시적으로 거부한다."""
    if type(value) not in (int, float):
        return None
    if not math.isfinite(float(value)):
        return None
    if positive and value <= 0:
        return None
    if nonnegative and value < 0:
        return None
    return value


def json_text(value):
    """브라우저 JSON.parse 와 같은 엄격 JSON을 쓰기 전에 완성한다."""
    return json.dumps(value, ensure_ascii=False, indent=1, allow_nan=False) + '\n'


def atomic_json_write(path, value):
    """직렬화·디스크 쓰기를 모두 마친 파일만 기존 스냅샷과 교체한다."""
    text = json_text(value)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.',
                               suffix='.tmp', dir=parent, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


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
                if _finite_number(it.get('nowVal'), positive=True) is not None}
    except Exception as e:
        print('[price] 네이버 목록 실패(%s) — 예비 출처로' % e, file=sys.stderr)
    missing = [c for c in CODES if c not in have]
    if missing:
        import kr_sources
        items += [it for it in kr_sources.quotes(missing) if _plausible(it)]
    return items


def _last_known(code):
    """nav_history.csv 의 그 종목 마지막 종가 — 예비 출처 가격의 대조 기준(저장소에 있어 러너에서도 읽힌다)."""
    p = os.path.join(ROOT, 'data', 'nav_history.csv')
    if not os.path.exists(p):
        return None
    import csv
    last = None
    with io.open(p, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r.get('code') == code:
                last = r.get('close')
    try:
        value = float(last) if last else None
        return value if value is not None and math.isfinite(value) and value > 0 else None
    except ValueError:
        return None


def _plausible(it, tol=0.25):
    """[2026-09-03] 예비 출처 가격 가드 — 잘못 파싱한 값(다른 종목의 금액 등)이 「오늘의 행동」 주수 계산에
    들어가지 않게, 마지막 알려진 종가와 25% 넘게 어긋나면 그 종목은 싣지 않는다(화면은 없으면 숨긴다).
    2배 ETF 의 하루 최대 움직임(±20%대)보다 넓게 잡았다 — v122 체결가 오타 가드(±20%)와 같은 발상."""
    code = str(it.get('itemcode', ''))
    ref = _last_known(code)
    px = _finite_number(it.get('nowVal'), positive=True)
    if px is None:
        return False
    # [2026-09-04 코드리뷰] ★ 종전엔 대조 기준이 없으면 `return bool(px>0)` 로 **아무 양수나
    #   통과**시켰다 — 이 가드가 막으려던 바로 그 상황(구글 HTML 에서 다른 종목 금액을 긁어온
    #   경우 등)에서 기준이 없으면 그대로 실렸다는 뜻이다. 검증할 수 없으면 검증된 것이 아니다.
    #   → **fail closed**: 대조할 종가가 없으면 싣지 않는다. 화면은 없으면 배지를 숨기고
    #   소유자는 MTS 를 보므로 실패가 눈에 보인다(v176 이 정한 신선도 원칙과 같은 방향).
    #   ⚠ 판정과 무관하다 — 전환은 QQQ 미국 종가만 본다. 잃는 것은 표시용 배지뿐이고,
    #   틀린 가격은 「오늘의 행동」의 주수·금액을 직접 틀리게 만든다. 비대칭이 명백하다.
    #   실측: 현재 CODES 5종 전부 nav_history 에 기준이 있어 이 갈래는 평시엔 안 탄다.
    if ref is None:
        print('[price] 예비 출처 %s — nav_history 에 대조할 종가가 없어 싣지 않음 (%s)'
              % (code, it.get('_source')), file=sys.stderr)
        return False
    if abs(px / ref - 1) > tol:
        print('[price] 예비 출처 %s 값 %s 이 마지막 종가 %s 와 %.0f%% 어긋남 — 싣지 않음 (%s)'
              % (it.get('itemcode'), px, ref, abs(px / ref - 1) * 100, it.get('_source')), file=sys.stderr)
        return False
    return True


def build(items):
    now = datetime.now(KST)
    out = {}
    for it in items:
        c = str(it.get('itemcode', ''))
        if c not in CODES:
            continue
        px = _finite_number(it.get('nowVal'), positive=True)
        if px is None:
            continue                      # 값이 이상하면 아예 싣지 않는다 (화면은 없으면 숨김)
        nav = _finite_number(it.get('nav'), positive=True)
        raw_name = it.get('itemname')
        row = {
            'name': raw_name if isinstance(raw_name, str) else '',
            'role': CODES[c],
            'px': int(px),
            'chg': _finite_number(it.get('changeVal')),
            'chg_pct': _finite_number(it.get('changeRate')),
            'volume': _finite_number(it.get('quant'), nonnegative=True),
        }
        # 괴리율 — 설명서 §③ 「주문 전에」가 쓰라고 한 그 숫자다.
        if nav is not None:
            row['nav'] = round(nav, 1)
            row['dev_pct'] = round((px / nav - 1) * 100, 3)
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
        doc = build(items)
    except Exception as e:
        # 시세를 못 받는 것은 사고가 아니다 — 화면이 옛 스냅샷을 그대로 두고
        # 「언제 잰 값인지」로 알린다. 기존 파일을 절대 덮어쓰지 않는다.
        print('[price] 수집 실패(%s) — 기존 파일 유지' % e, file=sys.stderr)
        return 0

    if not doc['items']:
        print('[price] 대상 종목 0건 — 기존 파일 유지', file=sys.stderr)
        return 0

    try:
        atomic_json_write(OUT, doc)
    except Exception as e:
        print('[price] 저장 실패(%s) — 기존 파일 유지' % type(e).__name__, file=sys.stderr)
        return 0
    print('[price] %s · %d종목' % (doc['as_of_kst'], len(doc['items'])))
    for c, r in doc['items'].items():
        print('   %s %-28s %8s원  %+.2f%%' %
              (c, r['name'][:28], format(r['px'], ','), r.get('chg_pct') or 0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
