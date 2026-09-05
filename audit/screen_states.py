# -*- coding: utf-8 -*-
"""화면 상태 행렬 생성기 (2026-09-05 · v223) — 1년에 몇 번 안 뜨는 signal.html 상태를 가짜 데이터로 띄운다.

    python audit/screen_states.py <출력폴더>      # 예: python audit/screen_states.py _scen
    python -m http.server 8767 --bind 127.0.0.1   # 저장소 루트에서 정적 서버
    → http://127.0.0.1:8767/<출력폴더>/<이름>/signal.html 을 412px 로 연다

폴더마다 signal.html·guide.html·notes.html·PWA 파일과 data/ 를 **복사**하고 signal.json·oos_log.csv·price.json·
ops_check.json 만 상태에 맞게 바꾼다. 실제 data/ 는 읽기만 한다. 출력 폴더는 커밋하지 마라(.gitignore 대상 아님 — 이름을 `_scen` 으로).
판정 규칙·장부와 무관한 **표시 검사** 도구다. 상태 목록과 기대 문구는 audit/SCREEN_STATES_2026-09-05.md.
"""
import copy
import datetime as dt
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = ['signal.html', 'guide.html', 'notes.html', 'manifest.json', 'icon-192.png', 'icon-512.png']
DATA = ['strategy_stats.json', 'freeze.json', 'kr_holidays.json', 'nav_history.csv', 'dd_percentile.json',
        'crisis_paths.json', 'isa_stats.json']


def _load():
    sig = json.load(io.open(os.path.join(ROOT, 'data/signal.json'), encoding='utf-8'))
    ops = json.load(io.open(os.path.join(ROOT, 'data/ops_check.json'), encoding='utf-8'))
    oos = io.open(os.path.join(ROOT, 'data/oos_log.csv'), encoding='utf-8').read().splitlines()
    pp = os.path.join(ROOT, 'data/price.json')          # price-data 브랜치 산출물 — 없으면 합성
    if os.path.exists(pp):
        price = json.load(io.open(pp, encoding='utf-8'))
    else:
        price = {'as_of_kst': '2026-09-04 15:55', 'as_of_iso': '2026-09-04T15:55:38+09:00',
                 'source': 'synthetic', 'note': '표시 전용', 'items': {
                     '418660': {'name': 'TIGER 미국나스닥100레버리지(합성)', 'role': '공격', 'px': 38585, 'chg': 755,
                                'chg_pct': 2.0, 'volume': 1, 'nav': 38500.0, 'dev_pct': 0.22},
                     '458730': {'name': 'TIGER 미국배당다우존스', 'role': '방어', 'px': 14965, 'chg': -75,
                                'chg_pct': -0.5, 'volume': 1, 'nav': 14966.0, 'dev_pct': -0.007},
                     '305080': {'name': 'TIGER 미국채10년선물', 'role': '방어', 'px': 11000, 'chg': 10,
                                'chg_pct': 0.09, 'volume': 1, 'nav': 11001.0, 'dev_pct': -0.01},
                     '411060': {'name': 'ACE KRX금현물', 'role': '방어', 'px': 27280, 'chg': 125,
                                'chg_pct': 0.46, 'volume': 1, 'nav': 27208.0, 'dev_pct': 0.265}}}
    return sig, ops, oos, price


def build(out_root):
    sig, ops, oos, price = _load()
    today = dt.date.today()

    def days_ago(n):
        return (today - dt.timedelta(days=n)).isoformat()

    def base(name):
        d = os.path.join(out_root, name)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(os.path.join(d, 'data'))
        for f in STATIC:
            shutil.copy(os.path.join(ROOT, f), d)
        for f in DATA:
            shutil.copy(os.path.join(ROOT, 'data', f), os.path.join(d, 'data', f))
        return d

    def wj(d, rel, obj):
        io.open(os.path.join(d, 'data', rel), 'w', encoding='utf-8').write(json.dumps(obj, ensure_ascii=False, indent=1))

    def wt(d, rel, text):
        io.open(os.path.join(d, 'data', rel), 'w', encoding='utf-8', newline='\n').write(text)

    def sigmod(state='QLD', prev=None, changed=False, dd=None, as_of=None):
        j = copy.deepcopy(sig)
        if dd is not None:
            j['dd'] = dd
            j['close'] = round(j['high_252'] * (1 + dd / 100), 2)
        if as_of:
            j['as_of'] = as_of
        for k in ('B', 'A'):
            st = j['strategies'][k]
            st['state'] = state; st['prev_state'] = prev or state; st['changed_today'] = changed
            line = -16.0 if k == 'B' else (-11.0 if state == 'SCHD' else -16.0)
            st['next_line'] = line
            st['gap_pp'] = round(abs((dd if dd is not None else j['dd']) - line), 2)
        j['state'] = state; j['prev_state'] = prev or state; j['changed_today'] = changed
        j['recent'][0]['B'] = state; j['recent'][0]['dd'] = j['dd']; j['recent'][0]['c'] = j['close']
        if prev and prev != state:
            j['recent'][1]['B'] = prev
        if as_of:
            j['recent'][0]['d'] = as_of
        return j

    def oos_rows(rows):
        out = [oos[0]]
        for a, c, h, dd, st, ch in rows:
            out.append('%s,%s,%s,%s,%s,%s,-16/-16,16201b974d4e383b,3,30.0,1.0' % (a, c, h, dd, st, ch))
        return '\n'.join(out) + '\n'

    def std(d, j=None, price_on=True, ops_on=True, oos_text=None):
        if j is not None:
            wj(d, 'signal.json', j)
        if price_on:
            wj(d, 'price.json', price)
        if ops_on:
            wj(d, 'ops_check.json', ops)
        wt(d, 'oos_log.csv', oos_text if oos_text else '\n'.join(oos) + '\n')

    H = 745.34
    d = base('defense'); rows = [(days_ago(23), 600.0, H, -19.5, 'QLD', 0), (days_ago(22), 595.0, H, -20.2, 'SCHD', 1)] + \
        [(days_ago(n), 596.0, H, -20.1, 'SCHD', 0) for n in (21, 20, 19, 15, 8, 1)]
    std(d, sigmod('SCHD', 'SCHD', False, dd=-20.1), oos_text=oos_rows(rows))
    d = base('defense_due'); rows = [(days_ago(31), 600.0, H, -19.5, 'QLD', 0), (days_ago(30), 595.0, H, -20.2, 'SCHD', 1)] + \
        [(days_ago(n), 596.0, H, -20.1, 'SCHD', 0) for n in (29, 22, 15, 8, 1)]
    std(d, sigmod('SCHD', 'SCHD', False, dd=-20.1), oos_text=oos_rows(rows))
    d = base('switch_defense'); std(d, sigmod('SCHD', 'QLD', True, dd=-16.5),
                                   oos_text=oos_rows([(days_ago(2), 640.0, H, -14.1, 'QLD', 0), (days_ago(1), 622.4, H, -16.5, 'SCHD', 1)]))
    d = base('switch_attack'); std(d, sigmod('QLD', 'SCHD', True, dd=-15.2),
                                  oos_text=oos_rows([(days_ago(2), 610.0, H, -18.1, 'SCHD', 0), (days_ago(1), 632.0, H, -15.2, 'QLD', 1)]))
    d = base('near'); std(d, sigmod('QLD', None, False, dd=-13.8))
    d = base('gray'); std(d, sigmod('QLD', None, False, dd=-12.0))
    d = base('trigger'); std(d, sigmod('QLD', None, False, dd=-16.0))
    d = base('pending'); std(d, sigmod('QLD', None, False))      # 브라우저에서 localStorage b_port_v1 에 방어 보유를 넣고 새로고침
    # 신선도: 평일 as_of 를 오늘 기준 3거래일·5거래일 전으로
    def biz_back(n):
        t = today
        while n > 0:
            t -= dt.timedelta(days=1)
            if t.weekday() < 5:
                n -= 1
        return t.isoformat()
    d = base('stale_warn'); std(d, sigmod('QLD', None, False, as_of=biz_back(3)))
    d = base('stale_bad'); std(d, sigmod('QLD', None, False, as_of=biz_back(5)))
    d = base('ops_todo'); o = copy.deepcopy(ops)
    o['todo'] = ['AUM 경보: 305080 순자산 280억 < 300억', 'B 판정 규약: 주의 — 1건']; o['protocol_b'] = {'verdict': 'warn', 'events': 1}
    std(d, sigmod(), ops_on=False); wj(d, 'ops_check.json', o)
    d = base('ops_stale'); o = copy.deepcopy(ops); o['as_of'] = days_ago(66); o['protocol_b'] = {'verdict': 'error', 'events': 0}
    std(d, sigmod(), ops_on=False); wj(d, 'ops_check.json', o)
    d = base('load_fail'); std(d, None)                           # signal.json 없음 → 로드 실패 배너 + 수동 입력
    d = base('price_missing'); std(d, sigmod(), price_on=False)
    d = base('price_old'); p = copy.deepcopy(price)
    p['as_of_kst'] = days_ago(4) + ' 15:55'; p['as_of_iso'] = days_ago(4) + 'T15:55:38+09:00'
    std(d, sigmod(), price_on=False); wj(d, 'price.json', p)
    return sorted(os.listdir(out_root))


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '_scen'
    print('\n'.join(build(os.path.abspath(out))))
