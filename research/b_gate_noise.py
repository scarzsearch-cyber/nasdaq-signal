# -*- coding: utf-8 -*-
"""
[이식 검산 · B 통제조건] 「B 의 무작위 이웃 분포」를 B 의 정식 엔진으로 다시 잰다 — 관문 ①②③ 이 파라미터 잡음 위에 서 있는가 (2026-09-03)

발단: 소유자 「별도 탐구 결과 중 B 에 도움되는 것은 반영해도 좋다 — 단 B 의 실험 통제조건과 다르니 그걸 감안해서」.
  별도 탐구(research/EXPLORATION.md B-2, c3_placebo.py G1)는 C3 를 재려고 「B 무작위 변형 200」 분포를 만들었는데, 그 분포는 B 자체에 대한
  정보다: B 의 관문 ①(Calmar +10.2%)·②(20년창 p05 ≥ B)·③(4블록 3+) 을 **파라미터만 흔든 후보**가 얼마나 자주 넘는가 = 관문의 잡음 폭.
  탐구는 자체 상태기계(첫 252일 절단 · min_periods=win)로 쟀다. B 의 정식 규약은 eng_common.rule_dd(min_periods=1 · 첫날부터) · sim2 · fullmet ·
  p05_20y 이고 selfcheck 가 공표 수치(217,110 / Calmar 0.418)를 재현한다. **여기서는 정식 규약으로 같은 분포를 다시 만든다.** 후보는 고르지 않는다
  (재탐색 금지 — 분포만 본다).

무엇을 재나:
  N1 넓은 이웃 200: 문턱 U(−20,−12) · 룩백 U(150,350) — 탐구 G1 과 **같은 난수열(seed 42 · 같은 호출 순서)** → 파라미터 집합이 동일, 차이는 엔진 규약뿐.
  N2 좁은 이웃 200: 문턱 U(−17.5,−14.5) · 룩백 U(202,302) — 「B 를 조금 흔든 것」(새 측정 · 탐구엔 없음 · seed 43).
  후보마다 vs B: ΔCalmar · Δp05(20년창 5% 분위) · 4블록 Calmar 승수 → 관문 ① ② ③ 통과 비율.

사전 등록 (결과 전에 적음 — ⚠ N1 의 중앙·p95·①② 는 탐구에서 이미 본 값이 있다: 중앙 −5.0% · p95 +7.9% · ①② 1.0%. 따라서 N1 은 「재현」이지
새 검사가 아니고, 아래 P2~P4 만 눈감고 세운 예측이다):
  P1 N1 정식 엔진 재현: ΔCalmar 중앙·p95 가 탐구 값의 ±2%p 안 (규약 차이는 첫 252일과 min_periods 뿐).
  P2 (새) N1 에서 ΔCalmar > 0 인 비율 20~35% — B 는 이웃의 상위 1/3 안이되 1위는 아니다(§5-20 「자기 표본 1위」는 2000~ 격자 이야기, 54년엔 아님).
  P3 (새) N1 Δp05 p95 < +15% · ③ 통과 비율 < 10% · ①②③ 동시 0%.
  P4 (새) N2 좁은 이웃: ΔCalmar p95 < +5% · ①② 동시 0% — 관문 ① 은 「B 를 조금 흔든 잡음」 폭의 2배 위에 있다.
  판정 규칙(사전): 관문 ① (+10.2%) 이 N1·N2 의 ΔCalmar p95 보다 **크면** 「① 은 파라미터 잡음 위」 → B 관문 체계의 보강 기록(04 §5-29).
  p95 가 ① 을 **넘으면** 「① 은 잡음 안」 → 04 관문 ① 을 p95 이상으로 올리자는 제안(매매 규칙 변경 아님 · 후보 심사 기준 · 소유자 결정).
  ①②③ 동시 통과 이웃이 있으면 그 파라미터를 **적지만 채택 후보로 다루지 않는다**(§5-22: 통짜 1위는 비중첩 창 1개 · PBO 0.40~0.83).

실행: python research/b_gate_noise.py   (약 1분 · 네트워크 0 · 파일 쓰기 0)
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import io
import contextlib
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    G, _ = EC.selfcheck()
IDX = pd.DatetimeIndex(G.idx)
PX = pd.Series(G.D['px'], index=IDX).astype(float)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIX = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
GATE1 = 0.102
EXPL = dict(med=-0.050, p95=0.079, g12=0.010)           # 탐구 G1 (EXPLORATION.md B-2 표) — 재현 대조용
L = '=' * 100


def curve(th, lb):
    w = EC.rule_dd(PX, th, th, win=lb)
    return np.asarray(EC.sim2(w, QLDR, MIX), float)


def blocks(c, nb=4):
    e = np.linspace(0, len(c), nb + 1).astype(int)
    return [EC.fullmet(c[a:b] / c[a], idx=IDX[a:b])['calmar'] for a, b in zip(e[:-1], e[1:])]


def measure(c):
    m = EC.fullmet(c, idx=IDX)
    return m['calmar'], EC.p05_20y(c), m['final'], blocks(c)


B = curve(-0.16, 252)
calB, p05B, finB, blB = measure(B)
assert abs(finB - 217110.075) < 0.5 and abs(calB - 0.418) < 0.001, f'B 공표 재현 실패 {finB} {calB}'


def neighborhood(name, draw, n=200, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        th, lb = draw(rng)
        cal, p05, fin, bl = measure(curve(th, lb))
        wins = sum(1 for x, y in zip(bl, blB) if x > y)
        rows.append(dict(th=th, lb=lb, dcal=cal / calB - 1, dp05=p05 / p05B - 1, fin=fin / finB, wins=wins))
    df = pd.DataFrame(rows)
    g1, g2, g3 = df.dcal > GATE1, df.dp05 >= 0, df.wins >= 3
    print('\n' + L); print(name); print(L)
    print(f'  ΔCalmar  중앙 {df.dcal.median():+.1%} · p95 {df.dcal.quantile(.95):+.1%} · 최대 {df.dcal.max():+.1%} · B 보다 높은 이웃 {np.mean(df.dcal > 0):.1%}')
    print(f'  Δp05     중앙 {df.dp05.median():+.1%} · p95 {df.dp05.quantile(.95):+.1%} · B 이상 {np.mean(g2):.1%}')
    print(f'  최종배수 vs B 중앙 {df.fin.median():.2f}배 · 4블록 승수 중앙 {df.wins.median():.0f}/4')
    print(f'  관문 통과 비율: ① {np.mean(g1):.1%} · ② {np.mean(g2):.1%} · ③ {np.mean(g3):.1%} · ①② {np.mean(g1 & g2):.1%} · ①②③ {np.mean(g1 & g2 & g3):.1%}')
    top = df.sort_values('dcal', ascending=False).head(3)
    print('  ΔCalmar 상위 3: ' + ' · '.join(f'문턱 {r.th*100:.1f}%·룩백 {int(r.lb)}: {r.dcal:+.1%}/{r.dp05:+.1%}/{int(r.wins)}블록' for r in top.itertuples()))
    hit = df[g1 & g2 & g3]
    if len(hit):
        print('  ⚠ ①②③ 동시 통과 이웃(채택 후보 아님 — 기록만): ' + ' · '.join(f'문턱 {r.th*100:.1f}%·룩백 {int(r.lb)}' for r in hit.itertuples()))
    return df


def main():
    print(L); print('B 의 무작위 이웃 분포 — 정식 엔진(rule_dd·sim2·fullmet·p05_20y) · 54년 · 채택 방어 · 편도 0.1% (규칙 무변경 · 후보 선택 없음)'); print(L)
    print(f'  B: 최종 {finB:,.0f} · Calmar {calB:.3f} · 20년 p05 {p05B:.1f}배 · 4블록 Calmar {" / ".join(f"{x:.2f}" for x in blB)}  (공표 재현 OK)')
    n1 = neighborhood('[N1] 넓은 이웃 200 — 문턱 U(−20,−12) · 룩백 U(150,350) · seed 42 (탐구 G1 과 같은 파라미터 집합)',
                      lambda r: (r.uniform(-0.20, -0.12), int(r.integers(150, 351))), seed=42)
    n2 = neighborhood('[N2] 좁은 이웃 200 — 문턱 U(−17.5,−14.5) · 룩백 U(202,302) · seed 43 (새 측정)',
                      lambda r: (r.uniform(-0.175, -0.145), int(r.integers(202, 303))), seed=43)

    # N2 의 판정이 경계선(p95 vs 관문 ①)이면 씨앗 하나로 말하면 안 된다(§-1 ⓑ: 손으로 고른 하나가 아니라 분포) — 씨앗 3개 더
    print('\n' + L); print('[N2 씨앗 감도] 같은 좁은 이웃 · 씨앗 44·45·46 (각 200)'); print(L)
    with contextlib.redirect_stdout(io.StringIO()):
        extra = [neighborhood('x', lambda r: (r.uniform(-0.175, -0.145), int(r.integers(202, 303))), seed=s) for s in (44, 45, 46)]
    for s, d in zip((44, 45, 46), extra):
        print(f'  seed {s}: ΔCalmar p95 {d.dcal.quantile(.95):+.1%} · B 보다 높은 이웃 {np.mean(d.dcal > 0):.1%} · ①② {np.mean((d.dcal > GATE1) & (d.dp05 >= 0)):.1%} · '
              f'①②③ {np.mean((d.dcal > GATE1) & (d.dp05 >= 0) & (d.wins >= 3)):.1%}')
    allq = [n2.dcal.quantile(.95)] + [d.dcal.quantile(.95) for d in extra]
    print(f'  4씨앗 p95 범위 {min(allq):+.1%} ~ {max(allq):+.1%} · 관문 ① +10.2% 를 넘는 씨앗 {sum(q >= GATE1 for q in allq)}/4')

    print('\n' + L); print('예측 대조 (사전 등록)'); print(L)
    m1, q1, j1 = n1.dcal.median(), n1.dcal.quantile(.95), np.mean((n1.dcal > GATE1) & (n1.dp05 >= 0))
    print(f'  P1 재현: 중앙 {m1:+.1%} (탐구 {EXPL["med"]:+.1%}) · p95 {q1:+.1%} (탐구 {EXPL["p95"]:+.1%}) · ①② {j1:.1%} (탐구 {EXPL["g12"]:.1%}) → '
          f'{"맞음" if abs(m1-EXPL["med"]) <= 0.02 and abs(q1-EXPL["p95"]) <= 0.02 else "틀림"}')
    s = np.mean(n1.dcal > 0)
    print(f'  P2 N1 에서 B 보다 Calmar 높은 이웃 {s:.1%} (예측 20~35%) → {"맞음" if 0.20 <= s <= 0.35 else "틀림"}')
    p3 = (n1.dp05.quantile(.95) < 0.15, np.mean(n1.wins >= 3) < 0.10, np.mean((n1.dcal > GATE1) & (n1.dp05 >= 0) & (n1.wins >= 3)) == 0)
    print(f'  P3 N1 Δp05 p95 {n1.dp05.quantile(.95):+.1%} (<15%) · ③ {np.mean(n1.wins >= 3):.1%} (<10%) · ①②③ {np.mean((n1.dcal > GATE1) & (n1.dp05 >= 0) & (n1.wins >= 3)):.1%} (=0) → '
          + ' · '.join('맞음' if x else '틀림' for x in p3))
    q2 = n2.dcal.quantile(.95); j2 = np.mean((n2.dcal > GATE1) & (n2.dp05 >= 0))
    print(f'  P4 N2 ΔCalmar p95 {q2:+.1%} (<5%) · ①② {j2:.1%} (=0) → {"맞음" if q2 < 0.05 else "틀림"} · {"맞음" if j2 == 0 else "틀림"}')
    print('\n판정 규칙(사전) 적용:')
    for nm, q in (('N1', q1), ('N2', q2)):
        print(f'  {nm}: 관문 ① +10.2% 는 ΔCalmar p95 {q:+.1%} 보다 {"큼 → ① 은 파라미터 잡음 위" if GATE1 > q else "작거나 같음 → ① 은 잡음 안 · 상향 제안"}')

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 파라미터 잡음으로는 ①②③ 을 못 넘는데 §5-3~5-28 에서 ①② 를 넘긴 후보(트랜치·C3)가 있었다 — 그것들은 파라미터가 아니라 **입력 계열·구조**를 바꾼 후보다.')
    print('      그 종류의 잡음은 이 분포가 아니라 「입력 뒤섞기 플라시보」(EXPLORATION.md B-2 G3)가 잰다 → CLAUDE §-1 반증 방아쇠 ⓔ 로 등재(04 §5-29).')
    print('  Q-b B 보다 Calmar 가 높은 이웃이 있는 것은 「고원 위」인가 「이웃 최적 아님」인가 → 답은 §5-22(CSCV PBO 0.40~0.83: IS 1등 고르기는 동전던지기 이하) — 재탐색 근거가 못 된다.')
    print('  Q-c 좁은 이웃의 p95 가 관문 ① 의 절반 아래라면 ① 은 「위기 1개 제거 폭」이라는 경제적 뜻과 「잡음 2배」라는 통계적 뜻을 동시에 갖는다 — 04 관문 정의에 그 둘을 함께 적었나(§5-29 에서 적음).')


if __name__ == '__main__':
    main()
