# -*- coding: utf-8 -*-
"""
[지평 유효표본 감사, 2026-08-31 소유자 승인] 「손실 0 문턱 7년」에 §5-4 의 잣대를 댄다.

배경 — 이 저장소의 일관성 구멍:
  audit_stat.py [4] 는 20년창에 ESS 를 걸어 「비중첩 2.8 · p05 는 2개 사건 군집 →
  소수 사건 통계, 분포 주장 불가」를 냈고, 그 논리로 혼합 고원이 기각됐다(04 §5-4).
  그런데 **같은 표본에서 나온** LEVERAGE_US §9 의 「원금손실 0 문턱 = 7년
  (12,099창 전부, 최악 +6%)」에는 같은 잣대를 대지 않았다. 그 숫자가 지금
  CLAUDE.md·guide.html 확률표·소유자 지평 프레임의 머릿돌로 올라가 있다.

이 스크립트는 판정이 아니라 **오차막대**다. 전략 무변경 · 규칙 무접촉.
  [0] 검산 — horizon_study.py [A] 의 창수·손실확률·최악을 그대로 재현(오차 0)
  [1] 비중첩 창 수 · AR-ESS · 최악 창의 사건 군집 수
  [2] 정상 부트스트랩(L=252, N=500, seed 42 — audit_stat 과 같은 규약)으로
      지평별 손실확률의 신뢰구간

⚠ 부트스트랩 한계는 audit_stat [3] 과 동일: 블록 경계가 다년 약세장을 자른다.
   L=252 가 주판정, 짧은 L 은 민감도로만 읽는다.

실행: python research/horizon_ess.py
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
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
wB = np.asarray(G.wB, float)
HS = [(756, '3년'), (1260, '5년'), (1764, '7년'), (2520, '10년'),
      (3780, '15년'), (5040, '20년')]

# horizon_study.py [A] 공표값 — 검산 대상 (LEVERAGE_US §9 표)
PUB = {'3년': (0.070, 0.48), '5년': (0.012, 0.77), '7년': (0.000, 1.06),
       '10년': (0.000, 1.59), '15년': (0.000, 7.00), '20년': (0.000, 16.9)}


def ar_ess(mults):
    """audit_stat [4] 와 같은 방식 — ρ>0.05 까지 합산."""
    N = len(mults)
    x_ = mults - mults.mean()
    ac = np.correlate(x_, x_, 'full')[N - 1:] / (x_ @ x_)
    k, s = 1, 0.0
    while k < N and ac[k] > 0.05:
        s += ac[k]
        k += 1
    return N / (1 + 2 * s), k


def events(mults, ends, q):
    """하위 q 분위 창의 종료일을 1년 격리로 묶어 독립 사건 수를 센다."""
    lo = mults <= np.quantile(mults, q)
    if lo.sum() == 0:
        return 0, None, None
    e = pd.Series(ends)[lo]
    gaps = e.diff().dt.days.fillna(9999)
    return int((gaps > 365).sum()), e.dt.year.min(), e.dt.year.max()


def main():
    aB = EC.sim2(wB, QLDR, MIXR)

    # ---- [0] 검산 — 공표값 재현 -------------------------------------------
    print('\n[0] 검산 — horizon_study [A] / LEVERAGE_US §9 재현')
    ok = True
    for w, lab in HS:
        mb = aB[w:] / aB[:-w]
        loss, worst = float(np.mean(mb < 1)), float(mb.min())
        pl, pw = PUB[lab]
        d1, d2 = abs(loss - pl), abs(worst - pw)
        # 공표값은 자릿수가 다르다(0.48 은 2자리, 16.9 는 1자리) — 반올림 폭을 허용
        good = d1 < 0.0006 and d2 < max(0.006, pw * 0.002)
        ok = ok and good
        print(f'  {lab:>4}  창 {len(mb):>6}  손실확률 {loss:>6.1%} (공표 {pl:>5.1%})  '
              f'최악 {worst:>6.2f}배 (공표 {pw:>5.2f})  {"OK" if good else "★불일치"}')
    print(f'  → 검산 {"통과" if ok else "실패 — 아래 수치를 신뢰하지 말 것"}')
    if not ok:
        sys.exit('검산 실패: 엔진이 공표 시점과 다르다')

    # ---- [1] 유효 독립 표본 -----------------------------------------------
    print('\n[1] 유효 독립 표본 — 12,099 은 독립 관측이 아니다')
    print(f"{'지평':>5} {'겹친창':>7} {'비중첩':>7} {'AR-ESS':>8} {'최악5% 사건수':>13} {'사건 시기':>14}")
    for w, lab in HS:
        mb = aB[w:] / aB[:-w]
        ends = idx[w:]
        ess, _ = ar_ess(mb)
        ne, y0, y1 = events(mb, ends, 0.05)
        span = f'{y0}~{y1}' if y0 is not None else '—'
        print(f'{lab:>5} {len(mb):>7} {n/w:>7.1f} {ess:>8.1f} {ne:>13} {span:>14}')
    print('  ※ 비중첩 = 54년 ÷ 지평. 「12,099창 전부」의 실제 독립 관측 수는 이 열이다.')

    # ---- [2] 부트스트랩 신뢰구간 -------------------------------------------
    print('\n[2] 정상 부트스트랩 손실확률 (L=252 · N=500 · seed 42 — audit_stat 규약)')
    print('    ⚠ 블록 경계가 다년 약세장을 자른다 (audit_stat [3] 과 같은 한계)')
    rng = np.random.default_rng(42)
    rB = np.diff(aB, prepend=1.0) / np.concatenate(([1.0], aB[:-1]))
    L, nrep, batch = 252, 500, 50
    acc = {lab: [] for _, lab in HS}
    for b0 in range(0, nrep, batch):
        m = min(batch, nrep - b0)
        starts = rng.integers(0, n, size=(m, n))
        cont = rng.random((m, n)) > (1.0 / L)
        pos = np.empty((m, n), dtype=np.int64)
        pos[:, 0] = starts[:, 0]
        for t in range(1, n):
            nxt = (pos[:, t - 1] + 1) % n
            pos[:, t] = np.where(cont[:, t], nxt, starts[:, t])
        A = np.cumprod(1 + rB[pos], axis=1)
        for w, lab in HS:
            mm = A[:, w:] / A[:, :-w]
            acc[lab].extend(np.mean(mm < 1, axis=1).tolist())

    print(f"{'지평':>5} {'실현':>7} {'부트 중앙':>10} {'90% 구간':>18} {'P(손실확률>0)':>14}")
    for w, lab in HS:
        mb = aB[w:] / aB[:-w]
        real = float(np.mean(mb < 1))
        v = np.array(acc[lab])
        lo, hi = np.quantile(v, 0.05), np.quantile(v, 0.95)
        print(f'{lab:>5} {real:>7.1%} {np.median(v):>10.1%} '
              f'{"[" + format(lo, ".1%") + ", " + format(hi, ".1%") + "]":>18} '
              f'{np.mean(v > 0):>14.0%}')
    print('\n  읽는 법: 「실현 0.0%」는 이 표본이 그렸던 한 경로의 결과일 뿐이고,')
    print('  같은 국소 동학에서 다시 뽑으면 손실확률이 얼마나 흔들리는지가 90% 구간이다.')


if __name__ == '__main__':
    main()
