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
    print('\n[5] 정액이 아니라 「평가액의 x%」로 인출하면 — 소득 변동 (진짜 아픈 곳)')
    print(f"{'전략':>10} {'최악 연간 소득 감소':>18} {'최악 소득/최초':>15} {'소득 반토막 빈도':>17}")
    for lab, a in (('전략 B', aB), ('1배 보유', a1)):
        ys = a[::Y]                                   # 연 1회 관측
        inc = ys / ys[0]                              # 인출액 ∝ 평가액
        yoy = inc[1:] / inc[:-1] - 1
        # 롤링 20년 창마다 최악 낙폭
        worst_yoy = float(yoy.min())
        run_min = float(np.min(inc / np.maximum.accumulate(inc)))
        half = float(np.mean(inc[1:] / np.maximum.accumulate(inc)[1:] < 0.5))
        print(f'{lab:>10} {worst_yoy:>17.1%} {run_min:>14.1%} {half:>16.1%}')
    print('  ※ 인출액이 평가액에 비례하므로 위 수치가 곧 「생활비가 얼마나 줄어드나」다.')
    print('     전략 B 는 파산은 안 하지만 **한 해 소득이 반 이하로 떨어지는 구간**이 있다.')

    print('\n[6] 판정')
    print('  · 명목 기준이라 낙관적이다 — 물가 연동 인출은 이보다 나쁘다(물가 계열 부재).')
    print('  · 파산확률도 horizon_ess 와 같은 유효표본 문제를 갖는다 — 20년 비중첩 2.8개.')
    print('  · 따라서 아래 표는 「안전 인출률」의 확정값이 아니라 **순서 위험의 크기**를')
    print('    보여주는 자료다. 인출기 진입 전에 반드시 물가 연동판으로 다시 볼 것.')


if __name__ == '__main__':
    main()
