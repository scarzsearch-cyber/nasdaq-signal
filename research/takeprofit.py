# -*- coding: utf-8 -*-
"""
[익절 규칙, 2026-08-31 소유자 질문] 「수익률 n%마다 전량 매도하면 손해야?」

배경: 04 §5-6 이 라오어 무한매수법(승자 익절+패자 물타기)을 기각했으나 그건
  **결합 시스템**이었다. 「순수 익절 규칙」 단독은 이 저장소에서 잰 적이 없다.
  추측으로 답하지 않고 실측한다.

정의 문제: 「팔고 나서 무엇을 하는가」가 정해져야 전략이 된다. 두 변형을 잰다.
  V1 쿨다운형 : 익절 → 방어 바스켓, N 거래일 뒤 무조건 재공격
  V2 딥매수형 : 익절 → 방어 바스켓, 낙폭이 −d% 도달하면 재공격
  (둘 다 기존 −16% 게이트는 그대로 살아 있다 — 익절은 게이트에 얹는 층이다)

★ 사전 고정 관문 (결과 보기 전 커밋 — 04 §5-7 방법론 기록):
  ① Calmar 가 현행 B 대비 **+10.2% 이상**
  ② 20년창 바닥(p05)이 현행 B 이상
  ③ 시대 분해에서 **전반·후반 양쪽** 우세 (v50/v87 BGATE 지문 회피)
  셋 다 통과해야 「기각 아님」. 하나라도 미달이면 기각.

평가 전용 · 동결 규칙 무접촉. 실행: python research/takeprofit.py
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                 # noqa: E402

G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
TH = -0.16
DD = (PX / PX.rolling(252, min_periods=1).max() - 1).values

GATE1 = 0.102          # 관문① Calmar +10.2%


def w_takeprofit(tp, mode, param):
    """−16% 게이트 위에 익절 층을 얹은 비중 경로.

    tp    : 익절 문턱 (진입가 대비 +tp)
    mode  : 'cool'(N거래일 후 재진입) | 'dip'(낙폭 −param 도달 시 재진입)
    """
    w = np.ones(n)
    att = True            # 공격 중인가
    entry = PX.iloc[0]    # 마지막 공격 진입가
    locked = False        # 익절로 나온 상태인가 (게이트가 아니라)
    wait = 0
    for i in range(n):
        px = PX.iloc[i]
        if att:
            if DD[i] <= TH:                       # ① 게이트가 최우선
                att, locked, wait = False, False, 0
            elif px / entry - 1 >= tp:            # ② 익절
                att, locked, wait = False, True, 0
        else:
            if locked:                            # 익절로 나온 상태의 복귀
                wait += 1
                back = (wait >= param) if mode == 'cool' else (DD[i] <= -param)
                if DD[i] <= TH:                   # 익절 중 폭락 → 게이트가 인수
                    locked = False
                elif back:
                    att, locked, entry = True, False, px
            else:                                 # 게이트로 나온 상태 — 기존 규칙
                if DD[i] > TH:
                    att, entry = True, px
        w[i] = 1.0 if att else 0.0
    return w


def met(a):
    m = EC.fullmet(a, idx=idx)
    p05 = float(np.quantile(a[5040:] / a[:-5040], 0.05))
    return m['final'], m['mdd'], m['calmar'], p05


def era(a):
    h = n // 2
    c2 = EC.fullmet(a[h:] / a[h], idx=idx[h:])['calmar']
    return a[h] / a[0], a[-1] / a[h], EC.fullmet(a[:h], idx=idx[:h])['calmar'], c2


def main():
    wB = EC.rule_dd(PX, TH, TH)
    aB = EC.sim2(wB, QLDR, MIXR)
    f0, m0, c0, p0 = met(aB)
    print(f'\n기준선 B: 최종 {f0:,.1f}배 · MDD {m0:.1f}% · Calmar {c0:.3f} · p05 {p0:.1f}배')
    print(f'관문① Calmar > {c0*(1+GATE1):.3f} · 관문② p05 > {p0:.1f} · 관문③ 전·후반 양쪽 우세')

    TPS = [0.10, 0.20, 0.30, 0.50, 1.00]
    for mode, param, lab in [('cool', 21, 'V1 쿨다운 21거래일'),
                             ('dip', 0.05, 'V2 딥매수 −5%')]:
        print(f'\n[{lab}] 익절 후 이렇게 돌아온다')
        print(f"{'익절선':>7} {'최종배수':>13} {'MDD':>8} {'Calmar':>8} "
              f"{'p05':>8} {'관문①':>7} {'관문②':>7}")
        for tp in TPS:
            w = w_takeprofit(tp, mode, param)
            a = EC.sim2(w, QLDR, MIXR)
            f, m, c, p = met(a)
            g1 = 'OK' if c >= c0 * (1 + GATE1) else '미달'
            g2 = 'OK' if p >= p0 else '미달'
            print(f'{tp:>6.0%} {f:>13,.1f} {m:>7.1f}% {c:>8.3f} {p:>7.1f}배 '
                  f'{g1:>7} {g2:>7}')

    # 최선 후보만 시대 분해 (관문③)
    print('\n[관문③] 위에서 가장 나은 칸의 시대 분해')
    best = None
    for mode, param in [('cool', 21), ('dip', 0.05)]:
        for tp in TPS:
            a = EC.sim2(w_takeprofit(tp, mode, param), QLDR, MIXR)
            _, _, c, _ = met(a)
            if best is None or c > best[0]:
                best = (c, mode, param, tp, a)
    c, mode, param, tp, a = best
    e1, e2, ec1, ec2 = era(a)
    b1, b2, bc1, bc2 = era(aB)
    print(f'  최선: {mode} {param} · 익절 {tp:.0%} (Calmar {c:.3f})')
    print(f"{'':>10} {'전반 배수':>11} {'후반 배수':>11} {'전반 Cal':>9} {'후반 Cal':>9}")
    print(f'{"현행 B":>10} {b1:>11,.1f} {b2:>11,.1f} {bc1:>9.3f} {bc2:>9.3f}')
    print(f'{"익절 최선":>10} {e1:>11,.1f} {e2:>11,.1f} {ec1:>9.3f} {ec2:>9.3f}')

    print('\n[판정]')
    print('  위 표에서 관문①②를 동시에 통과한 칸이 하나라도 있는가로 읽는다.')
    print('  없으면 기각 — 「손해다」가 답이다.')


if __name__ == '__main__':
    main()
