# -*- coding: utf-8 -*-
"""
[목표 도달 가능성] 「초기금 X + 월 적립 Y 로 N년 안에 Z 원이 되는가」 — 전수 창 분포.

소유자 질문 (2026-09-03): 「1,000만원 + 월 100만원으로 5년 안에 10억(그리고 5억)을
만들려면 TQQQ 버전으로 가능한가」. 배율 다이얼 연구(research/LEVERAGE_US.md)는
「k 를 얼마로 할까」를 답하지만 **「목표액에 닿는가」는 한 번도 안 쟀다.**

★ 사전 등록 예측 (결과 보기 전, 2026-09-03):
    P1 어떤 5년 창에서도 10억 도달 0건.            -> ★ 틀림 (3배 1.4% · 2배 0.1%)
    P2 최고 창조차 목표의 절반 미만.                -> ★ 틀림 (3배 최고 28.3억 = 목표의 283%)
    P3 도달 창이 있다면 특정 한 시대에 몰린다.       -> 맞음 (전부 1992~1996 시작 1국면)
    P4 배율보다 적립액이 목표 달성을 더 크게 움직인다. -> 맞음
  P1·P2 는 틀렸으므로 그대로 적는다 (CLAUDE.md §-1 ⑦).
  **틀린 방향이 중요하다** — 나는 「불가능」 쪽으로 틀렸고, 실제로는 「한 국면에서만
  가능」이었다. 결론(5년은 계획의 근거가 못 된다)은 P3 이 지탱하지 P1 이 아니다.

판정: **채택·기각 대상이 아니다** — 전략 후보가 아니라 계획 산술이다. 전략 무접촉.
  5억 필요 CAGR 76.2% · 10억 108.4% (저장소 공표 2배 B 25.3% · 3배 합성 31.5%).
  도달 국면이 1개(비중첩 10개 중)라 **확률로 읽으면 안 된다** — 달성률 6.5% 는
  「16창에 1번」이 아니라 「1990년대 중반에 시작했다면」이다.

⚠ 합성 잣대 주의 (LEVERAGE_US.md §1 그대로): lev_r 규약은 k>2 에 비용을 과대
  부과(보수적)하고 실물 체인보다 8% 낮게 나온다 — **k 사이 비교만 유효**.
⚠ 5년 창 비중첩 10개 · 3배는 국내에서 못 산다(미국 직투 = ISA 밖 · 22% 양도세).

실행: python research/goal_feasibility.py [초기금만원] [월적립만원] [목표만원] [년]
      기본값 1000 100 100000 5
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                  # noqa: E402
from axis_lib import lev_r                               # noqa: E402

KS = [('1배 QQQ', 1.0), ('2배 현행 B', 2.0), ('2.5배', 2.5), ('3배 TQQQ', 3.0)]


def build():
    G, X = EC.selfcheck()          # 공표 재현 검산 내장 (final 217110 / Calmar 0.418)
    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    wB = np.asarray(G.wB, float)
    cur = {nm: np.asarray(EC.sim2(wB, np.asarray(lev_r(G.D, k), float), MIXR), float)
           for nm, k in KS}
    return G.idx, cur


def terminal(curve, P0, PM, W, months):
    """모든 시작일에 대해 적립식 만기 평가액. 월 적립은 창을 months 등분한 시점."""
    steps = [round(W * m / months) for m in range(1, months + 1)]
    n = len(curve)
    out = np.empty(n - W)
    for s in range(n - W):
        c = curve[s:s + W + 1]
        c = c / c[0]
        v = P0 * c[-1] + PM                      # 마지막 달 적립은 성장 0
        for t in steps[:-1]:
            v += PM * (c[-1] / c[t])
        out[s] = v
    return out


def episodes(mask, W):
    """도달 시작일을 독립 국면으로 묶는다 — 간격이 창 길이를 넘으면 새 국면."""
    hit = np.where(mask)[0]
    if len(hit) == 0:
        return []
    eps, cur = [], [hit[0]]
    for a, b in zip(hit[:-1], hit[1:]):
        if b - a > W:
            eps.append(cur); cur = [b]
        else:
            cur.append(b)
    eps.append(cur)
    return eps


def need_cagr(P0, PM, months, tgt):
    f = lambda r: P0 * (1 + r) ** months + PM * ((1 + r) ** months - 1) / r
    lo, hi = 1e-6, 1.0
    for _ in range(400):
        mid = (lo + hi) / 2
        if f(mid) < tgt:
            lo = mid
        else:
            hi = mid
    return ((1 + (lo + hi) / 2) ** 12 - 1) * 100


def years_to(curve, P0, PM, tgt, cap_y=20, step=63):
    """월 적립을 유지하며 목표에 닿기까지 걸린 햇수 — 절단 편향을 막으려고
    남은 활주로가 cap_y 년 이상인 시작일만 쓴다."""
    n = len(curve); got = []
    for s in range(0, n - 252 * cap_y, step):
        cc = curve[s:] / curve[s]
        v, hit = P0, None
        for t in range(1, min(len(cc), 252 * cap_y + 1)):
            v *= cc[t] / cc[t - 1]
            if t % 21 == 0:
                v += PM
            if v >= tgt:
                hit = t / 252.0
                break
        got.append(hit)
    ok = [g for g in got if g is not None]
    return (len(ok) / len(got) if got else float('nan'),
            float(np.median(ok)) if ok else float('nan'))


def main():
    a = sys.argv[1:]
    P0 = float(a[0]) if len(a) > 0 else 1000.0
    PM = float(a[1]) if len(a) > 1 else 100.0
    TGT = float(a[2]) if len(a) > 2 else 100000.0
    YR = float(a[3]) if len(a) > 3 else 5.0
    W = int(round(252 * YR)); months = int(round(12 * YR))
    paid = P0 + PM * months

    idx, cur = build()
    n = len(idx)
    print('표본 %s ~ %s · %g년 창 %d개 (비중첩 %.1f개)'
          % (idx[0].date(), idx[-1].date(), YR, n - W, (n - W) / W))
    print('초기 %.0f만 + 월 %.0f만 x %d개월 = 납입 %.0f만원 · 목표 %.0f만원 (납입의 %.1f배)'
          % (P0, PM, months, paid, TGT, TGT / paid))
    print('필요 연CAGR %.1f%%   |   저장소 공표: 2배 B 54년 25.3%% · 3배 합성 31.5%%'
          % need_cagr(P0, PM, months, TGT))
    print()

    hdr = '%-12s %8s %8s %8s %8s %8s %7s %6s' % (
        '전략', '최악', 'p05', '중앙', 'p95', '최고', '달성률', '국면')
    print(hdr); print('-' * len(hdr))
    R = {}
    for nm, k in KS:
        v = terminal(cur[nm], P0, PM, W, months); R[nm] = v
        m = v >= TGT
        eps = episodes(m, W)
        print('%-12s %8.0f %8.0f %8.0f %8.0f %8.0f %6.1f%% %6d'
              % (nm, v.min(), np.percentile(v, 5), np.median(v),
                 np.percentile(v, 95), v.max(), 100 * m.mean(), len(eps)))
    print('  ※ 단위 만원 · 납입 %.0f만원' % paid)
    print()

    print('[도달 국면 — 이 열이 표의 핵심이다]')
    any_hit = False
    for nm, k in KS:
        eps = episodes(R[nm] >= TGT, W)
        if not eps:
            print('  %-12s 없음' % nm); continue
        any_hit = True
        print('  %-12s %d국면: %s' % (nm, len(eps), ' / '.join(
            '%s~%s' % (idx[e[0]].date(), idx[e[-1]].date()) for e in eps[:4])))
    if any_hit:
        print('  => 국면이 1개면 달성률은 확률이 아니라 「그 시대에 시작했다면」이다.')
    print()

    print('[목표를 %g년에 묶지 않으면 — 월 %.0f만 유지 시 도달까지]' % (YR, PM))
    for nm, k in KS:
        rate, med = years_to(cur[nm], P0, PM, TGT)
        print('  %-12s 20년내 도달 %3.0f%% · 중앙 %.1f년' % (nm, 100 * rate, med))
    print()

    print('[%g년에 굳이 맞추려면 — 월 적립을 얼마로]' % YR)
    steps = [round(W * m / months) for m in range(1, months + 1)]
    for nm, k in KS:
        c = cur[nm]; A = []; Bm = []
        for s in range(0, n - W, 21):
            cc = c[s:s + W + 1]; cc = cc / cc[0]
            A.append(cc[-1])
            Bm.append(1.0 + sum(cc[-1] / cc[t] for t in steps[:-1]))
        nd = (TGT - P0 * np.array(A)) / np.array(Bm)
        nd = nd[nd > 0]
        print('  %-12s 중앙 창 월 %.0f만원 · 나쁜 창(p95) 월 %.0f만원'
              % (nm, np.median(nd), np.percentile(nd, 95)))
    print()

    # §-1 ⑥ — 이 측정이 낳은 다음 질문
    print('[이 측정이 낳은 질문]')
    print('  Q-a 도달 국면이 1992~96 하나라는 것은 「닷컴 상승기」라는 뜻인데,')
    print('      그 창들의 만기(1997~2001)가 폭락 직전이다 — 만기 시점을 목표로')
    print('      삼는 계획은 그 자체가 시점 위험이다. (04 §5-26 니케이형과 같은 축)')
    print('  Q-b 배율을 올려 얻는 시간 단축(5억 9.4->7.3년)의 대가는 MDD -60.5->-78.4%.')
    print('      LEVERAGE_US.md §9 B 의 5년 지평 합리적 k* 는 감마=3 에서 2.4 다.')
    print('  Q-c 적립액을 올리는 쪽은 시장에 안 걸린 확실한 수단이다 — 배율과 달리')
    print('      나쁜 창에서도 값이 그대로다. 04 §7 대장 후보는 아니다(전략 밖).')


if __name__ == '__main__':
    main()
