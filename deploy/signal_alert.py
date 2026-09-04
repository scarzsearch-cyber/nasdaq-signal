#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[v76] 전환 신호 알림 — changed_today 인 날만 notify.py 로 폰에 알린다.

이 전략에서 놓치면 안 되는 날은 1년에 두어 번뿐인 전환일이다. 그날 아침
신호 갱신 직후 이 스크립트가 돌고, secret(notify.py 참조)이 있으면 알림이 간다.
전환이 없으면 아무것도 하지 않는다.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


STATE = os.path.join('data', 'signal_alert_state.json')
FREEZE = os.path.join('data', 'freeze.json')


def already_alerted(as_of):
    """앞선 슬롯에서 이 전환의 알림 전송과 상태 저장까지 성공했는가."""
    if not os.path.exists(STATE):
        return False
    try:
        state = json.load(open(STATE, encoding='utf-8'))
        if not isinstance(state, dict):
            raise ValueError('상태가 JSON 객체가 아님')
        return state.get('last_success_as_of') == as_of
    except Exception as e:                       # 못 읽으면 보내는 쪽 — 누락보다 중복이 낫다
        print(f'[경고] 알림 성공 표시를 읽지 못했다({e}) — 중복 위험을 감수하고 보낸다',
              file=sys.stderr)
        return False


def mark_alerted(as_of):
    """알림 성공 뒤에만 중복 방지 표시를 원자적으로 기록한다."""
    state = {}
    if os.path.exists(STATE):
        state = json.load(open(STATE, encoding='utf-8'))
        if not isinstance(state, dict):
            raise ValueError('알림 성공 상태가 JSON 객체가 아니다')
    state['last_success_as_of'] = as_of
    directory = os.path.dirname(os.path.abspath(STATE))
    fd, tmp = tempfile.mkstemp(prefix='.signal_alert_state.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def _fraction(value):
    """signal은 -16, freeze는 -0.16이므로 둘을 같은 비율 단위로 맞춘다."""
    value = float(value)
    return value / 100.0 if abs(value) > 1 else value


def validate_changed_b(j, b):
    """실제 매매 문구를 만들기 전에 동결 B와 현재 상태의 일치를 확인한다."""
    changed = b.get('changed_today')
    if type(changed) is not bool:
        raise ValueError('B changed_today가 JSON 불리언이 아님')
    if not changed:
        return False
    state = b.get('state')
    if state not in ('QLD', 'SCHD'):
        raise ValueError(f'B state가 허용값이 아님: {state!r}')
    if not os.path.exists(FREEZE):
        raise ValueError('freeze.json이 없음')
    freeze = json.load(open(FREEZE, encoding='utf-8'))
    rule = freeze.get('rule') or {}
    try:
        enter, exit_ = _fraction(b['enter']), _fraction(b['exit'])
        frozen_enter, frozen_exit = float(rule['enter']), float(rule['exit'])
        dd = float(j['dd'])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError('B 문턱·낙폭을 수치로 읽을 수 없음') from e
    if not all(math.isfinite(v) for v in (enter, exit_, frozen_enter, frozen_exit, dd)):
        raise ValueError('B 문턱·낙폭에 비유한 값이 있음')
    if abs(enter - frozen_enter) > 1e-9 or abs(exit_ - frozen_exit) > 1e-9:
        raise ValueError('signal B 문턱이 freeze.json과 다름')
    if abs(frozen_enter - frozen_exit) > 1e-12:
        raise ValueError('동결 B가 대칭 문턱이 아님')
    expected = 'SCHD' if dd <= frozen_enter * 100 else 'QLD'
    if state != expected:
        raise ValueError(f'B state가 낙폭/동결 문턱과 다름({state} != {expected})')
    return True


def main(sender=subprocess.call):
    sig = os.path.join('data', 'signal.json')
    if not os.path.exists(sig):
        return 0
    j = json.load(open(sig, encoding='utf-8'))
    b = (j.get('strategies') or {}).get('B') or {}
    # [2026-09-04 코드리뷰] 최상위 changed_today·state 는 **A(−16/−11) 미러**다(v192 적발).
    # B 가 없을 때 그리로 물러서면 **A 가 전환한 날 카톡이 가고 B 의 전환일엔 안 간다.**
    # 그건 「알림이 없는 것」보다 나쁘다 — 틀린 날에 팔게 만든다. 없으면 말하고 멈춘다.
    if not b:
        print('[경고] signal.json 에 strategies.B 가 없다 — 알림을 보내지 않는다', file=sys.stderr)
        return 2
    try:
        changed = validate_changed_b(j, b)
    except Exception as e:
        print(f'[실패] 전환 B 검증 실패({e}) — 매매 알림을 보내지 않는다', file=sys.stderr)
        return 2
    if not changed:
        print('전환 없음 — 알림 생략')
        return 0
    # [2026-09-04 코드리뷰] ★ daily-signal 슬롯이 하루 여러 번 돈다(실측 4~7회) —
    #   전환일에는 **매 슬롯이 같은 카톡을 보낸다.** changed_today 는 그날 내내 참이고
    #   이 스크립트는 모든 슬롯에서 무조건 돌기 때문이다. 동결 후 전환이 0회라 아직
    #   안 드러났을 뿐 반드시 일어난다. 하필 **1년에 두어 번뿐인 가장 중요한 알림**이
    #   도배로 오면, 이 저장소가 내내 경계해 온 알림 피로가 최악의 순간에 터진다.
    #   → OOS 장부는 알림 성공 여부가 아니다. 발송이 실패해도 뒤 스텝이 장부를 쓰므로
    #   장부로 중복을 막으면 다음 슬롯의 재시도까지 영구 차단된다. 전송 성공 뒤에만
    #   signal_alert_state.json 을 쓰고, 실패하면 표시를 남기지 않아 다음 슬롯이 재시도한다.
    if already_alerted(j['as_of']):
        print('이 전환은 앞선 슬롯에서 알림 전송까지 성공했다 — 중복 발송 생략')
        return 0
    st = b['state']
    if st == 'QLD':
        act = '방어 바스켓 전량 매도 → TIGER 나스닥100레버리지(418660) 매수'
    else:
        act = 'QLD 전량 매도 → 방어 바스켓 매수 (배당40 458730 / 국채40 305080 / 금20 411060)'
    msg = (f"낙폭 {j.get('dd')}% (종가 {j.get('close')}, {j.get('as_of')})\n"
           f"오늘 한국장 09:05~15:20 에: {act}")
    rc = sender([sys.executable, os.path.join('deploy', 'notify.py'),
                 '전환 신호 발생', 'signal', msg])
    if rc != 0:
        print(f'[실패] 전환 알림을 보내지 못했다(returncode={rc}) — 다음 슬롯에서 재시도',
              file=sys.stderr)
        return rc or 2
    try:
        mark_alerted(j['as_of'])
    except Exception as e:
        # 알림은 갔지만 표시가 없으므로 다음 슬롯에서 한 번 더 갈 수 있다. 누락보다 안전하다.
        print(f'[실패] 알림 성공 표시 저장 실패({type(e).__name__}: {e}) — '
              '중복 위험을 감수하고 다음 슬롯에서 재시도', file=sys.stderr)
        return 2
    print(f"전환 알림 성공 표시 저장 — {j['as_of']}")
    return 0


def selftest():
    """발송 실패 뒤 OOS 장부가 생겨도 재시도하고, 성공 뒤에만 중복을 막는다."""
    import shutil
    root = os.getcwd()
    td = tempfile.mkdtemp(prefix='signal_alert_selftest_')
    calls = []
    try:
        os.chdir(td)
        os.makedirs('data')
        signal = {'as_of': '2026-09-03', 'close': 600, 'dd': -16.2,
                  'strategies': {'B': {'state': 'SCHD', 'changed_today': True,
                                       'enter': -16, 'exit': -16}}}
        json.dump(signal, open('data/signal.json', 'w', encoding='utf-8'))
        json.dump({'rule': {'enter': -0.16, 'exit': -0.16}},
                  open('data/freeze.json', 'w', encoding='utf-8'))
        # 앞선 실패 뒤에도 OOS 기록은 독립적으로 생긴다는 실제 순서를 재현한다.
        open('data/oos_log.csv', 'w', encoding='utf-8').write(
            'as_of,changed\n2026-09-03,1\n')

        def fail_sender(args):
            calls.append(args)
            return 2

        signal['strategies']['B']['state'] = '?'
        json.dump(signal, open('data/signal.json', 'w', encoding='utf-8'))
        assert main(fail_sender) == 2 and not calls
        signal['strategies']['B']['state'] = 'QLD'
        json.dump(signal, open('data/signal.json', 'w', encoding='utf-8'))
        assert main(fail_sender) == 2 and not calls
        signal['strategies']['B']['state'] = 'SCHD'
        signal['strategies']['B']['changed_today'] = 'false'
        json.dump(signal, open('data/signal.json', 'w', encoding='utf-8'))
        assert main(fail_sender) == 2 and not calls
        signal['strategies']['B']['changed_today'] = True
        json.dump(signal, open('data/signal.json', 'w', encoding='utf-8'))

        assert main(fail_sender) == 2
        assert len(calls) == 1 and not os.path.exists(STATE)

        def ok_sender(args):
            calls.append(args)
            return 0

        assert main(ok_sender) == 0
        assert len(calls) == 2 and already_alerted('2026-09-03')
        assert main(ok_sender) == 0 and len(calls) == 2

        signal['strategies']['B']['changed_today'] = False
        json.dump(signal, open('data/signal.json', 'w', encoding='utf-8'))
        assert main(ok_sender) == 0 and len(calls) == 2
    finally:
        os.chdir(root)
        shutil.rmtree(td, ignore_errors=True)
    print('signal_alert selftest: PASS (B 동결/상태 · 실패 재시도 · 성공 후 중복 방지)')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        sys.exit(main() or 0)
