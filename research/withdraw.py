# -*- coding: utf-8 -*-
"""
[인출 엔진, 2026-08-31 소유자 승인] 지평 프레임의 뒷단 — 형성기 반대편이 비어 있었다.

배경: `axis_lib.accumulate()` (적립)는 있으나 **인출(decumulation) 엔진이 없다.**
  CLAUDE.md 의 인출기는 「배당이 생활비를 덮는지 직접 확인」이라는 정성 한 줄뿐.
  MDD −60% · 물속 4.7년짜리 전략에서 정액 인출은 적립과 대칭이 아니다 —
  바닥에서 파는 것이 강제되면 복리가 영구 손상된다(sequence-of-returns risk).

  · Bengen (1994), "Determining Withdrawal Rates Using Historical Data", J. Financial Planning
  · Cooley, Hubbard & Walz (1998), Trinity study, AAII Journal
  · Scott, Sharpe & Watson (2009), "The 4% Rule—At What Price?", J. Investment Management

⚠ 한계 (반드시 병기): 이 저장소에 **물가 계열이 없다.** 아래는 **명목 정액** 인출이라
  실질 구매력 기준보다 **낙관적**이다. 인플레이션 연동 인출은 파산확률을 높인다.
⚠ 유효표본: horizon_ess 와 같은 문제 — 20년 비중첩 창은 2.8개뿐. 확률은 점추정이 아니다.

평가 전용 · 전략 무변경 · 동결 규칙 무접촉. 실행: python research/withdraw.py
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
Y = 252


def ruin_curve(a, rate, H):
    """명목 정액 인출(연초, 최초 원금의 rate) — 파산확률·잔존배수 분포."""
    starts = np.arange(0, n - H * Y)
    V = np.ones(len(starts))
    dead = np.zeros(len(starts), bool)
    for y in range(H):
        V = V - rate
        dead |= (V <= 0)
        V = np.maximum(V, 0.0)
        g = a[starts + (y + 1) * Y] / a[starts + y * Y]
        V = V * g
    return float(dead.mean()), V, dead


def main():
    wB = EC.rule_dd(PX, -0.16, -0.16)
    aB = EC.sim2(wB, QLDR, MIXR)
    a1 = np.cumprod(1 + np.nan_to_num(PX.pct_change().values))

    RATES = [0.03, 0.04, 0.05, 0.06, 0.08]
    HS = [10, 15, 20]

    print('\n[1] 파산확률 — 전략 B (명목 정액 인출, 롤링 창 전수)')
    print(f"{'인출률':>7} " + ' '.join(f'{h}년'.rjust(9) for h in HS) +
          f"{'비중첩 창':>12}")
    for r in RATES:
        row = f'{r:>6.0%} '
        for h in HS:
            p, _, _ = ruin_curve(aB, r, h)
            row += f'{p:>9.1%}'
        row += f'{n/(HS[-1]*Y):>11.1f}개'
        print(row)

    print('\n[2] 같은 인출을 1배 지수 보유로 했다면 (레버리지·규칙 없음)')
    print(f"{'인출률':>7} " + ' '.join(f'{h}년'.rjust(9) for h in HS))
    for r in RATES:
        row = f'{r:>6.0%} '
        for h in HS:
            p, _, _ = ruin_curve(a1, r, h)
            row += f'{p:>9.1%}'
        print(row)

    print('\n[3] 20년 인출 후 남는 돈 (원금 대비 배수) — 전략 B')
    print(f"{'인출률':>7} {'p05':>8} {'중앙':>9} {'p95':>10} {'파산':>8}")
    for r in RATES:
        p, V, dead = ruin_curve(aB, r, 20)
        print(f'{r:>6.0%} {np.quantile(V,0.05):>8.2f}배 {np.median(V):>8.2f}배 '
              f'{np.quantile(V,0.95):>9.2f}배 {p:>7.1%}')

    print('\n[4] 최악 창 — 언제 시작하면 죽는가 (인출 5%·20년)')
    p, V, dead = ruin_curve(aB, 0.05, 20)
    starts = np.arange(0, n - 20 * Y)
    if dead.any():
        ds = pd.Series(idx[starts][dead])
        gaps = ds.diff().dt.days.fillna(9999)
        print(f'  파산 창 {int(dead.sum())}개 · 독립 사건(1년 격리) '
              f'{int((gaps>365).sum())}개 · 시작 시기 {ds.dt.year.min()}~{ds.dt.year.max()}')
    else:
        print('  파산 창 없음')
    worst = int(np.argmin(V))
    print(f'  최악 잔존: {idx[starts][worst].date()} 시작 → {V[worst]:.2f}배')

    # ---- [5] 진짜 위험은 파산이 아니라 소득 붕괴 ---------------------------
    #   명목 정액은 100배로 불어난 계좌에 묻혀 파산이 안 난다 — 이 표본의 성장이
    #   극단적이라 검사가 무력해진다. 실전에서 아픈 건 **인출액 자체의 급감**이다.
    # [순회 B15 · 2026-09-05] 종전엔 연 1회 표본을 **위상 하나**(a[::252])로만 찍어 값이 표본 격자에 매달렸다 —
    #   v210 이 114행을 빼자 같은 코드가 −51.3% → −16.0% 를 냈다(위상 252개 중 최악 −53.6% · 중앙 −37.4% · 최선 −16.0%).
    #   위상 252개 전수 + 롤링 1년(모든 시작일)로 재정의한다. 판정([6])도 여기서 계산한 값을 쓴다.
    print('\n[5] 정액이 아니라 「평가액의 x%」로 인출하면 — 소득 변동 (진짜 아픈 곳)')
    print(f"{'전략':>10} {'롤링1년 최악':>12} {'위상최악 연간감소':>16} {'위상중앙':>9} {'최악 소득/이전고점':>17} {'반토막 빈도(중앙)':>17}")
    INC = {}
    for lab, a in (('전략 B', aB), ('1배 보유', a1)):
        roll = float(np.min(a[Y:] / a[:-Y] - 1))                     # 모든 시작일의 1년 수익 최악
        ws, rm, hf = [], [], []
        for p in range(Y):                                           # 연 1회 관측일을 어디에 두느냐 — 252가지 전부
            ys = a[p::Y]; inc = ys / ys[0]; yoy = inc[1:] / inc[:-1] - 1
            ws.append(float(yoy.min())); rm.append(float(np.min(inc / np.maximum.accumulate(inc))))
            hf.append(float(np.mean(inc[1:] / np.maximum.accumulate(inc)[1:] < 0.5)))
        INC[lab] = dict(roll=roll, w_min=min(ws), w_med=float(np.median(ws)), rm_min=min(rm), hf_med=float(np.median(hf)))
        d = INC[lab]
        print(f"{lab:>10} {d['roll']:>11.1%} {d['w_min']:>15.1%} {d['w_med']:>8.1%} {d['rm_min']:>14.1%} {d['hf_med']:>16.1%}")
    print('  ※ 인출액이 평가액에 비례하므로 위 수치가 곧 「생활비가 얼마나 줄어드나」다. 「위상」= 연 1회 관측일의 자리(252가지) —')
    print('     한 자리만 보면 값이 표본 격자에 매달린다(v210 정정 전 −51.3% 는 그 한 자리 값). 롤링 1년 최악이 위상과 무관한 크기다.')

    # ---- [5-b] 물가 연동 인출 — 초판의 미결을 스윕으로 메운다 ---------------
    #   ⚠ FRED CPIAUCSL 을 받으려 했으나 이 환경에서 접속 불가(3회 재시도 실패).
    #   실계열 대신 **물가율 스윕**으로 민감도를 본다. 소유자 지평이 3~20년이므로
    #   과거 경로보다 전방 가정 스윕이 오히려 판단에 맞다.
    #   ★ 단, 54년 표본의 1970~80년대는 어떤 상수보다도 물가가 높았으므로
    #     아래 표는 **그 구간에 대해 낙관적**이다. 실계열 확보 시 재계산할 것.
    print('\n[5-b] 물가 연동 인출 — 인출액이 매년 물가만큼 늘어난다면 (파산확률)')

    def ruin_infl(a, rate, H, infl):
        starts = np.arange(0, n - H * Y)
        V = np.ones(len(starts))
        dead = np.zeros(len(starts), bool)
        for y in range(H):
            V = V - rate * ((1 + infl) ** y)          # 인출액이 물가만큼 증가
            dead |= (V <= 0)
            V = np.maximum(V, 0.0)
            V = V * (a[starts + (y + 1) * Y] / a[starts + y * Y])
        return float(dead.mean())

    print(f"{'인출률':>7} " + ' '.join(f'물가{int(i*100)}%'.rjust(9)
                                      for i in (0.0, 0.02, 0.04, 0.06)))
    for r in (0.04, 0.05, 0.06, 0.08):
        row = f'{r:>6.0%} '
        for infl in (0.0, 0.02, 0.04, 0.06):
            row += f'{ruin_infl(aB, r, 20, infl):>9.1%}'
        print(row)
    print('  (20년 지평 · 전략 B · 명목 정액이 왼쪽 끝 열)')
    print('  → 물가를 넣어도 파산은 거의 안 난다. [5] 와 같은 이유로 이 표본의 성장이')
    print('     인출을 압도하기 때문 — 즉 **파산확률은 이 전략의 인출 위험 지표가 아니다.**')
    print('     실제 위험은 아래 [5] 의 소득 변동이다.')

    print('\n[6] 판정')
    print('  · **파산확률은 이 전략의 인출 위험 지표가 아니다.** 물가 6% 를 넣어도')
    print(f'    5% 인출에서 파산 {ruin_infl(aB, 0.05, 20, 0.06):.1%} — 표본의 성장(20년 중앙 {np.median(aB[20*Y:] / aB[:-20*Y]):.0f}배)이 인출을 압도한다.')
    b_ = INC['전략 B']
    print(f"  · **실제 위험은 소득 변동이다**([5]): 롤링 1년 최악 {b_['roll']:+.1%}(위상 최악 {b_['w_min']:+.1%} · 중앙 {b_['w_med']:+.1%}),")
    print(f"    소득이 이전 고점의 {b_['rm_min']:.1%} 까지 떨어지는 구간이 있다. → **1년치 생활비 현금 완충이 설계 요건.**")
    print('  · 남은 한계 둘: ① 물가는 상수 스윕이고 실계열(CPIAUCSL)은 접속 불가라')
    print('    못 썼다 — 1970~80년대는 어떤 상수보다 높았으므로 그 구간엔 낙관적이다.')
    print('    ② 유효표본 문제는 그대로다(20년 비중첩 2.8개, horizon_ess 와 같은 한계).')


if __name__ == '__main__':
    main()
