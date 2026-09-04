#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전향적 OOS 장부 — 규칙 동결(2026-08-27) 이후를 하루 한 줄씩 **덧붙인다**.

`data/signal.json` 은 매일 덮어쓰므로 과거가 남지 않는다. 순수 out-of-sample
표본을 만들려면 **append-only 기록**이 필요하다. 이 스크립트가 그 일을 한다.

  · 하루 한 줄. 이미 있는 날짜는 건드리지 않는다(재실행해도 안전).
  · 기록만 한다. **어떤 판단도 하지 않는다.**
  · 이 장부를 보고 규칙을 바꾸면 순수 OOS 가 사라진다 — `data/freeze.json` 참조.

GitHub Actions 의 일일 신호 갱신 뒤에 호출된다.
로컬 확인:  python3 deploy/oos_log.py
"""
import csv
import datetime as dt
import io
import json
import math
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

SIG = os.path.join('data', 'signal.json')
FRZ = os.path.join('data', 'freeze.json')
QQQ = os.path.join('data', 'qqq.csv')
OUT = os.path.join('data', 'oos_log.csv')
COLS = ['as_of', 'close', 'high_252', 'dd', 'state', 'changed', 'rule', 'fingerprint',
        't4_votes', 't4_rv', 't4_w']
KST = dt.timezone(dt.timedelta(hours=9))

# [v69] T4 그림자 — 평가 전용. 채택안이 아니다. 어떤 판단·매매에도 쓰지 않는다.
# 정의와 사전 고정 파라미터는 docs/history/전략_v68_추세추종.md:
#   투표 = #{k ∈ {21,63,126,252} : 종가/종가[k일 전] > 1}
#   w    = clip(40% / 실현변동성, 0, 1) × 1[투표 ≥ 2]
#   실현변동성 = 2배 자산 근사 = 2 × (QQQ 일간수익 20일 표본표준편차) × √252
# 종가 원천은 이 장부의 close 와 같은 data/qqq.csv — 장부 안에서 일관되게.
# ([v80 정정] 이 캐시는 Yahoo **수정주가**다. 네이버 예비 소스는 최신 봉만 원시로
#  붙이는데 최신 봉은 두 값이 같다 — update_signal.py [v71] 참조. 구판 주석의
#  "(비수정)"은 오기였다. 신호 계산엔 영향 없음: 원천 이원화 실측 게이트 불일치
#  0.04% — research/axis_t4_shadow.py A-3.)
# 이 파라미터를 나중에 바꾸면 그때까지의 그림자 기록은 무효다(사전 고정이 전부다).
T4_LOOKS = (21, 63, 126, 252)
T4_TH = 2
T4_VT = 0.40
T4_WIN = 20


def qqq_snapshot(as_of):
    """QQQ 마지막 수정종가·252일 고점·직전 거래일. signal만 믿지 않는다."""
    if not os.path.exists(QQQ):
        raise ValueError('qqq.csv가 없음')
    dates, closes = [], []
    with io.open(QQQ, encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != ['Date', 'Close']:
            raise ValueError('qqq.csv 헤더가 Date,Close가 아님')
        for row in reader:
            day = _iso_day(row.get('Date'), 'qqq Date')
            try:
                close = float(row.get('Close'))
            except (TypeError, ValueError) as e:
                raise ValueError('qqq.csv Close가 수치가 아님') from e
            if not math.isfinite(close) or close <= 0:
                raise ValueError('qqq.csv Close가 비유한 값이거나 0 이하임')
            dates.append(day)
            closes.append(close)
    if not dates or len(set(dates)) != len(dates) or dates != sorted(dates):
        raise ValueError('qqq.csv 날짜가 비었거나 중복·역순임')
    if dates[-1].isoformat() != as_of:
        raise ValueError(f'qqq.csv 마지막 날짜({dates[-1]}) != signal as_of({as_of})')
    if len(closes) < 252:
        raise ValueError('qqq.csv가 252거래일보다 짧음')
    previous = dates[-2].isoformat() if len(dates) >= 2 else None
    return closes[-1], max(closes[-252:]), previous


def t4_shadow(as_of):
    """as_of 종가까지의 데이터로 T4 목표비중을 계산한다. (votes, rv%, w) 또는 None."""
    if not os.path.exists(QQQ):
        return None
    px, last = [], None
    with io.open(QQQ, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if r['Date'][:10] <= as_of:
                px.append(float(r['Close']))
                last = r['Date'][:10]
    if last != as_of:
        # [v80] 가격 파일이 as_of 까지 안 왔다 — 전일 값을 오늘 날짜로 그럴듯하게
        # 기록하는 것보다 빈 칸이 낫다 (그림자 실패는 본 기록을 해치지 않는다).
        print('[경고] qqq.csv 마지막 날짜(%s) != as_of(%s) — T4 그림자 빈 칸'
              % (last, as_of), file=sys.stderr)
        return None
    if len(px) < max(T4_LOOKS) + 1:
        return None
    votes = sum(1 for k in T4_LOOKS if px[-1] / px[-1 - k] > 1.0)
    rets = [px[i] / px[i - 1] - 1.0 for i in range(len(px) - T4_WIN, len(px))]
    mu = sum(rets) / len(rets)
    var = sum((x - mu) ** 2 for x in rets) / (len(rets) - 1)          # 표본(ddof=1)
    rv = 2.0 * (var ** 0.5) * (252 ** 0.5)                            # 2배 자산 연율화
    w = min(1.0, T4_VT / rv) if rv > 0 else 1.0
    if votes < T4_TH:
        w = 0.0
    return votes, round(rv * 100, 1), round(w, 3)


def _atomic_append_row(path, row, replace_func=os.replace):
    """기존 장부 바이트를 보존한 채 한 행만 원자적으로 덧붙인다."""
    original = ''
    if os.path.exists(path):
        with io.open(path, encoding='utf-8', newline='') as fh:
            original = fh.read()
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=COLS, extrasaction='ignore', lineterminator='\n')
    if not original:
        writer.writeheader()
    writer.writerow(row)
    suffix = '' if not original or original.endswith(('\n', '\r')) else '\n'
    text = original + suffix + buf.getvalue()
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.oos_log.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        replace_func(tmp, path)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def _fail(message):
    print('[실패] ' + message, file=sys.stderr)
    return 2


def _iso_day(value, label):
    if not isinstance(value, str):
        raise ValueError(f'{label}가 문자열이 아님')
    parsed = dt.date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError(f'{label}가 YYYY-MM-DD가 아님')
    return parsed


def _validate_existing_row(row, freeze):
    """이미 봉인된 한 OOS 행도 새 append 전에 현행 동결 계약과 대조한다."""
    if set(row) != set(COLS):
        raise ValueError('기존 OOS 장부 행의 열 계약이 불완전하다')
    try:
        close = float(row['close'])
        high = float(row['high_252'])
        dd = float(row['dd'])
        changed = int(row['changed'])
        votes = int(row['t4_votes'])
        rv = float(row['t4_rv'])
        weight = float(row['t4_w'])
    except (TypeError, ValueError) as e:
        raise ValueError('기존 OOS 장부에 비수치 필드가 있다') from e
    if (not all(math.isfinite(x) for x in (close, high, dd, rv, weight))
            or close <= 0 or high <= 0 or high + 1e-9 < close):
        raise ValueError('기존 OOS 장부의 종가·고점·T4 수치 범위가 잘못됐다')
    if abs((close / high - 1) * 100 - dd) > 0.02:
        raise ValueError('기존 OOS 장부의 낙폭이 종가/고점과 다르다')
    if row['changed'] not in ('0', '1') or changed not in (0, 1):
        raise ValueError('기존 OOS 장부 changed가 0/1이 아니다')
    expected_state = 'SCHD' if dd <= float(freeze['rule']['enter']) * 100 else 'QLD'
    if row['state'] != expected_state:
        raise ValueError('기존 OOS 장부 상태가 동결 B 규칙과 다르다')
    if row['rule'] != freeze['rule']['name'] or row['fingerprint'] != freeze['fingerprint']:
        raise ValueError('기존 OOS 장부 규칙 이름·지문이 freeze.json과 다르다')
    if not 0 <= votes <= 4 or rv < 0 or not 0 <= weight <= 1:
        raise ValueError('기존 OOS 장부 T4 값 범위가 잘못됐다')
    expected_w = 0.0 if votes < T4_TH else (1.0 if rv == 0 else min(1.0, 40.0 / rv))
    if abs(weight - expected_w) > 0.003:
        raise ValueError('기존 OOS 장부 T4 비중이 투표·변동성과 다르다')


def _read_existing(today, freeze):
    """기존 append-only 장부의 구조·날짜를 먼저 읽는다."""
    rows = []
    if not os.path.exists(OUT):
        return rows
    with io.open(OUT, encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLS:
            raise ValueError('기존 OOS 장부 헤더가 현행 계약과 다르다')
        rows = list(reader)
    dates = [r.get('as_of', '') for r in rows]
    try:
        parsed = [_iso_day(day, '기존 OOS as_of') for day in dates]
    except (TypeError, ValueError) as e:
        raise ValueError('기존 OOS 장부 날짜가 비었거나 ISO 형식이 아니다') from e
    if len(set(dates)) != len(dates) or parsed != sorted(parsed):
        raise ValueError('기존 OOS 장부 날짜가 중복·역순이다')
    if parsed and parsed[-1] > today:
        raise ValueError('기존 OOS 장부 끝 날짜가 미래다')
    for row in rows:
        _validate_existing_row(row, freeze)
    return rows


def main():
    if not os.path.exists(SIG) or not os.path.exists(FRZ):
        return _fail('signal.json 또는 freeze.json 이 없다 — 장부를 쓰지 않는다')
    j = json.load(io.open(SIG, encoding='utf-8'))
    f = json.load(io.open(FRZ, encoding='utf-8'))

    try:
        as_of = j['as_of']
        as_day = _iso_day(as_of, 'signal as_of')
        start_day = _iso_day(f['oos_start'], 'freeze oos_start')
    except (KeyError, TypeError, ValueError) as e:
        return _fail(f'장부 기준 날짜를 해석할 수 없다: {e}')
    today = dt.datetime.now(KST).date()
    if as_day > today:
        return _fail('signal as_of가 KST 현재 날짜보다 미래다')

    # 이미 성공 기록된 슬롯은 QQQ/T4 일시 장애와 무관한 no-op이어야 한다. 단 기존
    # 장부 자체의 헤더·날짜 계약은 먼저 확인한다.
    try:
        rows = _read_existing(today, f)
    except ValueError as e:
        return _fail(str(e))
    if any(r['as_of'] == as_of for r in rows):
        print('%s 는 이미 기록됨 — 변경하지 않는다 (append-only)' % as_of)
        return 0

    if as_day < start_day:
        print('%s 는 동결일 이전 — 기록하지 않는다' % as_of)
        return 0
    if rows and as_day <= _iso_day(rows[-1]['as_of'], '기존 OOS 끝 날짜'):
        return _fail('새 OOS 날짜가 기존 장부 끝보다 늦지 않다 — 중간 삽입을 거부한다')

    # 동결 규칙은 signal.json 의 'B' 항목이다. freeze.json 과 문턱이 일치하는지
    # 확인하고 쓴다 — 이름 문자열을 파싱하지 않는다(몇 년을 무인으로 돌 코드다).
    b = (j.get('strategies') or {}).get('B') or {}
    # [2026-09-04 코드리뷰] ★ 종전 가드는 `if b and 'enter' in b and ...` 라 **b 가 비면
    #   통째로 건너뛰었고**, 아래 row 가 최상위 A 미러(−16/−11)로 물러섰다. 즉 B 가 없을 때
    #   **A 의 판정이 동결 장부에 그대로 기록된다.** data/oos_log.csv 는 §2 절대 수정 금지
    #   대상이고 B 판정 규약(02 §5-1)의 유일한 근거다 — 다른 전략의 상태가 섞이면 되돌릴
    #   방법이 없다. 실측: signal.json 31커밋 중 strategies.B 가 없는 것은 **동결(08-27)
    #   이전 초기 포맷 3건뿐**이고 update_signal 은 항상 B 를 쓴다 — 되살아날 수 없는
    #   경로이면서 해만 끼친다. 없으면 기록하지 않는 쪽이 옳다(빈 날은 다시 채울 수 있다).
    if not b or not all(k in b for k in ('enter', 'exit', 'state')):
        return _fail('signal.json 에 완전한 strategies.B 가 없다 — A 미러로 대신 쓰지 않는다')
    try:
        enter = float(b['enter']) / 100
        exit_ = float(b['exit']) / 100
        close = float(j['close'])
        high = float(j['high_252'])
        dd = float(j['dd'])
    except (KeyError, TypeError, ValueError):
        return _fail('signal.json 의 B 문턱·종가·고점·낙폭을 수치로 읽을 수 없다')
    if not all(math.isfinite(x) for x in (enter, exit_, close, high, dd)):
        return _fail('signal.json 의 B 문턱·종가·고점·낙폭에 비유한 값이 있다')
    if abs(enter - f['rule']['enter']) > 1e-9 or abs(exit_ - f['rule']['exit']) > 1e-9:
        return _fail('signal.json 의 B 진입·복귀선이 동결값과 다르다')
    if close <= 0 or high <= 0 or high + 1e-9 < close:
        return _fail('signal.json 의 종가·252일 고점 범위가 잘못됐다')
    calc_dd = (close / high - 1) * 100
    if abs(calc_dd - dd) > 0.02:
        return _fail('signal.json 의 낙폭이 종가/252일 고점과 일치하지 않는다')
    expected_state = 'SCHD' if dd <= f['rule']['enter'] * 100 else 'QLD'
    if b['state'] != expected_state:
        return _fail('signal.json 의 B 상태가 -16% 대칭 규칙과 일치하지 않는다')
    try:
        qclose, qhigh, qprev = qqq_snapshot(as_of)
    except Exception as e:
        return _fail('QQQ 원천 교차검증 실패(%s) — 장부를 쓰지 않는다' % e)
    if abs(close - qclose) > 0.011 or abs(high - qhigh) > 0.011:
        return _fail('signal 종가·252일 고점이 qqq.csv 원천과 일치하지 않는다')
    changed_today = b.get('changed_today')
    if type(changed_today) is not bool:
        return _fail('signal.json 의 B changed_today가 JSON 불리언이 아니다')
    row = {
        'as_of': as_of,
        'close': close,
        'high_252': high,
        'dd': dd,
        'state': b['state'],
        'changed': int(changed_today),
        'rule': f['rule']['name'],
        'fingerprint': f['fingerprint'],
    }
    # T4는 J2 판정의 필수 입력이다. 빈 행을 쌓으면 3년 뒤에도 성숙도를 재구성할 수 없다.
    try:
        t4 = t4_shadow(as_of)
        if not t4:
            return _fail('T4 그림자 계산 결과가 없다 — 빈 칸 장부를 쓰지 않는다')
        row.update({'t4_votes': t4[0], 't4_rv': t4[1], 't4_w': t4[2]})
    except Exception as e:
        return _fail('T4 그림자 계산 실패(%s) — 장부를 쓰지 않는다' % e)

    # 연속된 거래일일 때만 changed_today를 이전 장부 상태와 대조한다. 전환 당일의
    # append가 일시 실패해 하루가 비면, 다음 날 신호는 이미 새 상태라 changed_today=False다.
    # 그때 마지막 *기록*과 무조건 비교하면 이후 모든 날짜를 영구 거부한다.
    if rows and rows[-1]['as_of'] == qprev:
        expected_changed = int(rows[-1].get('state') != b['state'])
        if row['changed'] != expected_changed:
            return _fail('changed_today가 기존 장부의 실제 상태 전환과 다르다')

    _atomic_append_row(OUT, row)
    rows.append(row)
    print('OOS 장부 %d행 (동결 %s 이후 %d영업일 기록)'
          % (len(rows), f['frozen_at'], len(rows)))
    return 0


def selftest():
    """틀린 B 상태·문턱·낙폭이 append-only 장부에 들어가지 않는 최소 반례."""
    global SIG, FRZ, QQQ, OUT, t4_shadow, qqq_snapshot
    saved = SIG, FRZ, QQQ, OUT, t4_shadow, qqq_snapshot
    try:
        with tempfile.TemporaryDirectory() as td:
            SIG, FRZ, QQQ, OUT = [os.path.join(td, n) for n in
                                  ('signal.json', 'freeze.json', 'qqq.csv', 'oos.csv')]
            freeze = {'frozen_at': '2026-08-27', 'oos_start': '2026-08-28',
                      'rule': {'name': '-16/-16', 'enter': -0.16, 'exit': -0.16},
                      'fingerprint': '16201b974d4e383b'}
            with io.open(FRZ, 'w', encoding='utf-8') as fh:
                json.dump(freeze, fh)
            t4_shadow = lambda as_of: (2, 30.0, 1.0)
            qqq_snapshot = lambda as_of: (80.0, 100.0, '2026-08-31')

            def write_signal(as_of, state='SCHD', exit_line=-16, dd=-20.0,
                             close=80.0, high=100.0, changed=True):
                payload = {'as_of': as_of, 'close': close, 'high_252': high, 'dd': dd,
                           'strategies': {'B': {'enter': -16, 'exit': exit_line,
                                               'state': state,
                                               'changed_today': changed}}}
                with io.open(SIG, 'w', encoding='utf-8') as fh:
                    json.dump(payload, fh)

            write_signal('2026-09-01')
            assert main() == 0
            with open(OUT, 'rb') as fh:
                original = fh.read()

            # 같은 날짜 no-op도 기존 장부 값 검증 뒤에만 가능하다.
            corrupted = original.replace(b'16201b974d4e383b', b'0000000000000000', 1)
            with open(OUT, 'wb') as fh:
                fh.write(corrupted)
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == corrupted
            with open(OUT, 'wb') as fh:
                fh.write(original)

            def fail_replace(src, dst):
                raise OSError('교체 실패 모의')
            try:
                _atomic_append_row(OUT, {'as_of': '2099-01-01'}, replace_func=fail_replace)
                raise AssertionError('원자 교체 실패를 성공으로 처리했다')
            except OSError:
                pass
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            # 이미 기록된 날짜는 T4/QQQ가 잠시 죽어도 완전한 no-op이다.
            t4_shadow = lambda as_of: (_ for _ in ()).throw(RuntimeError('T4 일시 실패'))
            assert main() == 0
            with open(OUT, 'rb') as fh:
                assert fh.read() == original
            t4_shadow = lambda as_of: (2, 30.0, 1.0)

            write_signal('2026-09-02', exit_line=-11, changed=False)
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            write_signal('2026-09-02', state='QLD', changed=False)
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            write_signal('2026-09-02', dd=-19.0, close=80.0, changed=False)
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            write_signal('2026-09-02', changed='false')
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            # close/high/dd끼리는 맞지만 QQQ 원천과 함께 틀린 coherent 거짓값도 거부한다.
            write_signal('2026-09-02', close=80.0, high=160.0, dd=-50.0,
                         state='SCHD', changed=False)
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            write_signal('2099-01-01', changed=False)
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            write_signal('2026-9-2', changed=False)
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            qqq_snapshot = lambda as_of: (80.0, 100.0, '2026-09-01')
            write_signal('2026-09-02', changed=True)
            assert main() == 2
            with open(OUT, 'rb') as fh:
                assert fh.read() == original

            write_signal('2026-09-02', changed=False)
            assert main() == 0
            with open(OUT, 'rb') as fh:
                written = fh.read()
            assert written.startswith(original) and len(written) > len(original)

            # 전환일(09-03) 장부가 빠졌더라도 09-04의 changed_today=False 행은 복구돼야 한다.
            # 직전 QQQ 거래일이 장부에 없으므로 마지막 *기록*과의 상태차를 오늘 전환으로
            # 오인해 영구 거부하지 않는다.
            qqq_snapshot = lambda as_of: (90.0, 100.0, '2026-09-03')
            write_signal('2026-09-04', state='QLD', dd=-10.0, close=90.0,
                         high=100.0, changed=False)
            assert main() == 0
            with open(OUT, encoding='utf-8', newline='') as fh:
                recovered = list(csv.DictReader(fh))
            assert recovered[-1]['as_of'] == '2026-09-04'
            assert recovered[-1]['state'] == 'QLD' and recovered[-1]['changed'] == '0'
    finally:
        SIG, FRZ, QQQ, OUT, t4_shadow, qqq_snapshot = saved
    print('oos_log selftest: PASS (날짜/불리언 · B/QQQ 교차검증 · T4 · 원자 append/no-op)')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        sys.exit(main())
