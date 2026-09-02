# -*- coding: utf-8 -*-
"""
[연구 Q5] 근접 알림이 「미리 팔기」를 부르면 얼마를 잃나 — 04 §7 Q5 (2026-09-02, 소유자 「연구만, 반영 금지」)

Q5 의 원래 질문은 행동(재량 개입이 실제로 일어나는가)이고, 그건 동결 이후 체결 기록이 쌓여야 잰다. 지금 잴 수
있는 것은 **그 행동의 가격표**다: 알림을 보고 규칙보다 먼저 파는 사람은 54년에서 무엇을 얻고 잃었나.

방법: eng_common 54년 QQQ 체인 · 채택 방어(배당40/국채40/금20) · 편도 0.1%. 「미리 팔기」의 형태 4종:
    S16  −16/−16 (현행)
    S15  −15/−15 · S14 −14/−14 · S13 −13/−13 — 근접(전환선까지 <3%p)에서 미리 팔고, 근접을 벗어나면 되산다
    H13  근접 구간(−13 ≤ dd > −16)에서 **절반**만 방어, −16 아래에서 전량 방어, −13 위로 오면 전량 공격 (트랜치형)
  에피소드 잣대: 근접 진입(187회) 중 −16 까지 간 것(55%)에서 「먼저 판 사람」이 아낀 폭 vs 되돌아간 것(45%)에서
  되사며 문 왕복 비용 — 한 에피소드당 기대값.

★ 사전 등록 (결과를 보기 전에 적는다 — CLAUDE.md §-1):
  · 관문 없음(판정 아님) — 산출물은 「미리 팔기의 가격표」. 규칙·알림 문구 변경 없음.
  · 예측 P1: S13 의 최종배수는 S16 의 0.6~0.9배, 전환 횟수는 1.5~2배.
  · 예측 P2: S15 는 S16 과 ±10% 안(§5-22: 최악 분할에선 −15 가 −16 보다 나았다 — 표본 내 근소).
  · 예측 P3: H13(절반) 은 S13 과 S16 사이.
  · 예측 P4: 에피소드 기대값은 **음수** — 되돌아가는 45% 의 왕복 비용이 이어지는 55% 의 절약보다 크다.
  · 「틀리면 무엇이 참인가」: P1·P4 가 틀리면(미리 팔기가 이득) 근접 알림은 오히려 규칙 개선 단서가 되고 §5-20 의
    「−16 이 표본 1등」과 충돌한다 — 그 경우 04 에 그대로 적는다. 맞으면 「알림을 보고 먼저 팔면 X 를 잃는다」가
    알림 문구의 근거가 된다(문구는 이미 「아직 할 일 없음」이 먼저다 — 바꾸지 않는다).
  · 행동 측정 규약(동결 이후, 사람이 본다): 체결 기록의 D+n 이 **음수**(신호 전 체결)이거나, 판정이 공격인데 신호
    ±1일 밖에서 418660 매도가 있으면 「재량 개입 1건」. 1건이라도 나오면 근접 알림을 끌지 판단(04 Q5 재개 조건).

실행: python research/q5_near_presell.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                  # noqa: E402

NEAR = -0.13


def half_tranche(dd, near=NEAR, th=-0.16):
    """w: 1(공격) / 0.5(근접 구간) / 0(−16 아래 → 복귀선 위로 올 때까지). 마감 판정."""
    n = len(dd); w = np.ones(n); s = 1        # s: 1 공격, 2 절반, 0 방어
    for i, d in enumerate(dd):
        if s == 0:
            if d > th:
                s = 2 if d <= near else 1
        elif s == 2:
            if d <= th:
                s = 0
            elif d > near:
                s = 1
        else:
            if d <= th:
                s = 0
            elif d <= near:
                s = 2
        w[i] = {1: 1.0, 2: 0.5, 0: 0.0}[s]
    return w


def main():
    G, _ = EC.selfcheck()
    idx = G.idx
    px = pd.Series(G.D['px'], index=idx).astype(float)
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    hi = px.rolling(252, min_periods=252).max(); dd = (px / hi - 1).values
    yrs = (idx[-1] - idx[0]).days / 365.25

    print('=' * 96)
    print('Q5 근접 알림을 보고 먼저 팔면 — 미리 팔기의 가격표 (엔진 54년 · 채택 방어 · 규칙 무변경)')
    print('=' * 96)
    variants = [('S16 −16/−16 (현행)', EC.rule_dd(px, -0.16, -0.16)),
                ('S15 −15/−15', EC.rule_dd(px, -0.15, -0.15)),
                ('S14 −14/−14', EC.rule_dd(px, -0.14, -0.14)),
                ('S13 −13/−13 (근접에서 팔고 벗어나면 되삼)', EC.rule_dd(px, -0.13, -0.13)),
                ('H13 근접 절반·−16 전량 (트랜치형)', half_tranche(np.nan_to_num(dd, nan=0.0)))]
    rows = []
    for nm, w in variants:
        w = np.asarray(w, float)
        a = EC.sim2(w, QLDR, MIXR)
        m = EC.fullmet(a, idx=idx); m['p05'] = EC.p05_20y(a)
        m['sw'] = int(np.sum(np.abs(np.diff(w)) > 0))
        rows.append((nm, m))
    base = rows[0][1]
    print(f"\n  {'규칙':<40}{'최종배수':>12}{'vs현행':>8}{'CAGR':>8}{'MDD':>8}{'Calmar':>8}{'20년p05':>9}{'전환':>6}")
    for nm, m in rows:
        print(f"  {nm:<40}{m['final']:>12,.0f}{m['final']/base['final']:>7.2f}배{m['cagr']:>7.2f}%{m['mdd']:>7.1f}%"
              f"{m['calmar']:>8.3f}{m['p05']:>8.2f}배{m['sw']:>6d}")

    # 에피소드 가격표 — 근접 진입일에 판 사람 vs 규칙대로 −16 마감까지 기다린 사람 (2배 자산 기준)
    w16 = np.asarray(EC.rule_dd(px, -0.16, -0.16), float)
    lev = np.cumprod(1 + QLDR)                       # 2배 자산 곡선
    near = (dd <= NEAR) & (dd > -0.16) & (w16 == 1)  # 공격 상태에서의 근접 구간
    starts = np.where(near & ~np.roll(near, 1))[0]
    saved, cost, n_cont, n_rev = [], [], 0, 0
    for i in starts:
        j = i
        while j < len(dd) and (dd[j] <= NEAR) and w16[j] == 1:
            j += 1
        if j >= len(dd):
            break
        if dd[j] <= -0.16:                           # 이어짐 — 규칙은 j 에서 판다
            n_cont += 1
            saved.append(lev[i] / lev[j] - 1)        # 먼저 판 사람이 피한 추가 하락(2배 자산)
        else:                                        # 되돌아감 — j 에서 되산다
            n_rev += 1
            cost.append(lev[i] / lev[j] - 1 - 2 * EC.COST)   # 팔았다 되사며 놓친 상승 + 왕복 비용
    ev = (np.sum(saved) + np.sum(cost)) / max(1, n_cont + n_rev)
    print(f'\n  근접 진입 에피소드(공격 상태) {n_cont+n_rev}회 — 이어져서 −16 까지 간 것 {n_cont} · 되돌아간 것 {n_rev}')
    print(f'  이어진 경우 먼저 판 사람이 피한 추가 하락: 중앙 {np.median(saved)*100:+.1f}% · 평균 {np.mean(saved)*100:+.1f}%')
    print(f'  되돌아간 경우 되사며 잃은 것(왕복 비용 포함): 중앙 {np.median(cost)*100:+.1f}% · 평균 {np.mean(cost)*100:+.1f}%')
    print(f'  → 에피소드당 기대값 {ev*100:+.2f}% (연 {len(starts)/yrs:.1f}회) · 그런데 이건 이어진 경우의 「절약」이 다음 복귀선까지 그대로 남는다는 가정 —')
    print(f'    실제 곡선 비교(S13 vs S16)가 정답이고 위 표에 있다.')

    print('\n사전 등록 대조:')
    r13 = rows[3][1]; r15 = rows[1][1]; rh = rows[4][1]
    print(f"  P1 (S13 최종 0.6~0.9배 · 전환 1.5~2배): 최종 {r13['final']/base['final']:.2f}배 · 전환 {r13['sw']/base['sw']:.2f}배 → "
          f"{'맞음' if 0.6 <= r13['final']/base['final'] <= 0.9 and 1.5 <= r13['sw']/base['sw'] <= 2.0 else '틀림(방향은 표 참조)'}")
    print(f"  P2 (S15 ±10%): {r15['final']/base['final']:.2f}배 → {'맞음' if 0.9 <= r15['final']/base['final'] <= 1.1 else '틀림'}")
    print(f"  P3 (H13 는 S13 과 S16 사이): {'맞음' if min(r13['final'], base['final']) <= rh['final'] <= max(r13['final'], base['final']) else '틀림'}")
    print(f"  P4 (에피소드 기대값 음수): {'맞음' if ev < 0 else '틀림'} — {ev*100:+.2f}%")
    print('\n이 측정이 낳은 다음 질문 (§-1 절대멈춤 6):')
    print('  · 행동 자체는 동결 이후 체결 기록으로만 잰다(D+n<0 · 무신호 매도). 사건 0건인 지금은 답이 없다 — 규약만 적어 둔다.')
    print('  · S15 가 S16 과 근소하다면 「근접 알림」 문턱 3%p 를 2%p 로 좁혀도 되나 — 알림 빈도(연 3.5회)와의 교환이고 규칙과 무관. 소유자 취향.')


if __name__ == '__main__':
    main()
