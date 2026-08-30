# -*- coding: utf-8 -*-
"""
[운영 위험·전제 감시 6축, 2026-08-31 소유자 지시] 신호 축이 아닌 곳을 판다.

04 무덤은 **신호·외부정보·메커니즘·구조·엔진·배율** 축을 전부 소진했다. 남은 공간은
「규칙을 바꾸는 것」이 아니라 **「규칙을 실제로 굴릴 때 무엇이 깨지는가」**다.
사전 확인: 방어 재조정 주기·룩백 변경·쿨다운은 v41 기각 완료(HANDOFF §2) — 재탐색 아님.

★ 관문을 **결과 보기 전에** 못 박는다 (트랜치 교훈 — 04 §5-7 방법론 기록):
  [1] 전환 1회 통째 놓침 : 중앙 손실 >10% = 중대 운영위험 · <5% = 허용
  [2] 주식·채권 상관 국면 : 최근 상관이 역사 p90 초과 → Level 1 감시 등재
  [3] 일반계좌엔 1배 보유 : 관문① 세후 +10.2% · ② p05 개선 (04 §5-3 과 같은 잣대)
  [4] 비용 손익분기      : 손익분기 왕복비용 <0.6%(모형 0.2%의 3배) = 취약
  [5] 종가 오입력 내성   : 단일 오류 중앙 손실 >2% = 입력 검증 필요
  [6] 연속 손실 전환     : 서술적 (판정선 없음) — 심리적 인내 요건 파악

평가 전용 · 전략 무변경 · 동결 규칙 무접촉. 실행: python research/ops_risk.py
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
R1 = np.nan_to_num(PX.pct_change().values)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
TH = -0.16
wB = EC.rule_dd(PX, TH, TH)
aB = EC.sim2(wB, QLDR, MIXR)
SW = np.where(np.abs(np.diff(wB)) > 0)[0] + 1          # 전환 시점


def fin(a):
    return float(a[-1])


def p05(a, w=5040):
    return float(np.quantile(a[w:] / a[:-w], 0.05))


def main():
    base = fin(aB)
    print(f'\n기준선: B 최종 {base:,.1f}배 · 전환 {len(SW)}회 · 20년 p05 {p05(aB):.1f}배')

    # ---- [1] 전환 1회를 통째로 놓치면 -------------------------------------
    print('\n[1] 전환 1회 통째로 놓침 — 아프거나 폰이 죽어 그날을 넘긴 경우')
    print('    (놓친 전환은 건너뛰고 다음 전환에서야 상태가 맞춰진다)')
    losses = []
    for k in range(len(SW) - 1):
        w2 = wB.copy()
        i, j = SW[k], SW[k + 1]
        w2[i:j] = wB[i - 1]                            # 이전 상태를 유지 = 놓침
        losses.append(fin(EC.sim2(w2, QLDR, MIXR)) / base - 1)
    losses = np.array(losses)
    med = float(np.median(losses))
    print(f'  {len(losses)}회 각각 놓쳤을 때 최종배수 변화:')
    print(f'    중앙 {med:+.1%} · 최악 {losses.min():+.1%} · 최선 {losses.max():+.1%}')
    print(f'    10% 넘게 잃는 전환 {int(np.sum(losses < -0.10))}회 / '
          f'{int(np.sum(losses > 0))}회는 오히려 이득')
    kw = int(np.argmin(losses))
    print(f'    최악: {idx[SW[kw]].date()} 전환을 놓치면 {losses[kw]:+.1%}')
    v = ('★중대 운영위험' if med < -0.10 else '허용 가능' if med > -0.05 else '경계')
    print(f'  판정(사전 고정): 중앙 {med:+.1%} → **{v}**')

    # ---- [2] 방어 다리의 상관 국면 ----------------------------------------
    print('\n[2] 방어 바스켓이 아직 분산되는가 — QQQ 대비 상관의 국면 변화')
    W = 1260                                            # 5년 롤링
    s = pd.Series(R1)
    d = pd.Series(MIXR)
    roll = s.rolling(W).corr(d).values
    ok = ~np.isnan(roll)
    cur = float(roll[-1])
    p90 = float(np.nanquantile(roll[ok], 0.90))
    p50 = float(np.nanquantile(roll[ok], 0.50))
    print(f'  방어바스켓 vs 지수 5년 롤링 상관: 현재 {cur:+.3f} · '
          f'역사 중앙 {p50:+.3f} · p90 {p90:+.3f}')
    hi = idx[ok][int(np.nanargmax(roll[ok]))]
    print(f'  역사 최고 {np.nanmax(roll[ok]):+.3f} ({hi.date()})')
    v2 = '★Level 1 등재' if cur > p90 else '정상'
    print(f'  판정(사전 고정): 현재가 p90 {"초과" if cur > p90 else "이하"} → **{v2}**')
    # 2022 형 국면(주식·채권 동반 하락)이 실제로 있었는지
    y22 = (idx >= '2022-01-01') & (idx <= '2022-12-31')
    print(f'  참고 2022년: 지수 {np.prod(1+R1[y22])-1:+.1%} · '
          f'방어바스켓 {np.prod(1+MIXR[y22])-1:+.1%} (동반 하락 국면 실측)')

    # ---- [3] 일반계좌 몫은 1배 보유가 나은가 (세후) ------------------------
    print('\n[3] 일반계좌 몫 — B(전환마다 15.4%) vs 1배 보유(매도 시 1회)')
    GEN, ISA = 0.154, 0.099
    a1 = np.cumprod(1 + R1)

    def after_tax_B(a, rate):
        """전환마다 실현 과세 — 전환 시점의 이득에 rate 를 물린다."""
        v, last = 1.0, a[0]
        for i in SW:
            g = a[i] / last
            if g > 1:
                v *= 1 + (g - 1) * (1 - rate)
            else:
                v *= g
            last = a[i]
        g = a[-1] / last
        v *= (1 + (g - 1) * (1 - rate)) if g > 1 else g
        return v

    bt_gen = after_tax_B(aB, GEN)
    bt_isa = 1 + (fin(aB) - 1) * (1 - ISA)              # ISA: 만기 1회 과세
    h1_gen = 1 + (fin(a1) - 1) * (1 - GEN)              # 1배 보유: 매도 1회
    print(f'  ISA 에서 B         : {bt_isa:>12,.1f}배 (세후)')
    print(f'  일반계좌에서 B      : {bt_gen:>12,.1f}배 (세후)')
    print(f'  일반계좌에서 1배 보유: {h1_gen:>12,.1f}배 (세후)')
    g1 = bt_gen / h1_gen - 1
    print(f'  관문① 일반계좌에서 B 가 1배 보유 대비 +10.2% 이상? 실측 {g1:+.1%} → '
          f'{"통과" if g1 >= 0.102 else "★미달"}')
    print(f'  (관문② p05: B {p05(aB):.1f}배 vs 1배 {p05(a1):.1f}배 — 세전 기준)')

    # ---- [4] 비용 손익분기 -------------------------------------------------
    print('\n[4] 비용 손익분기 — 왕복비용이 얼마면 B 가 맨몸 2배에 지나')
    hold2 = np.cumprod(1 + QLDR)
    print(f"{'편도비용':>9} {'B 최종':>14} {'맨몸2배 대비':>13}")
    be = None
    for c in (0.001, 0.002, 0.003, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03):
        a = EC.sim2(wB, QLDR, MIXR, cost=c)
        r = fin(a) / fin(hold2)
        if be is None and r < 1:
            be = c
        star = ' ←모형' if abs(c - 0.001) < 1e-9 else ''
        print(f'{c:>8.2%} {fin(a):>14,.1f} {r:>12.2f}배{star}')
    print(f'  손익분기 편도비용: {"없음(3% 까지 우세)" if be is None else f"{be:.2%}"}')
    v4 = '★취약' if (be is not None and be < 0.003) else '강건'
    print(f'  판정(사전 고정): 손익분기 <0.3% 편도(=왕복 0.6%) 면 취약 → **{v4}**')

    # ---- [5] 종가 오입력 내성 ---------------------------------------------
    print('\n[5] 종가를 하루 잘못 넣으면 — 오전환과 그 대가')
    rng = np.random.default_rng(11)
    for err in (0.03, 0.05, 0.10):
        ds = []
        spur = 0
        for _ in range(200):
            i = int(rng.integers(300, n - 300))
            px2 = PX.copy()
            px2.iloc[i] *= (1 + err * (1 if rng.random() < 0.5 else -1))
            w2 = EC.rule_dd(px2, TH, TH)
            if not np.array_equal(w2, wB):
                spur += 1
            ds.append(fin(EC.sim2(w2, QLDR, MIXR)) / base - 1)
        ds = np.array(ds)
        print(f'  ±{err:.0%} 오류 200회: 신호 변경 {spur:>3}회 · '
              f'최종 중앙 {np.median(ds):+.2%} · 최악 {ds.min():+.2%}')
    print('  판정(사전 고정): 단일 오류 중앙 손실 >2% 면 입력 검증 필요')

    # ---- [6] 연속 손실 전환 (심리적 인내 요건) ------------------------------
    print('\n[6] 연속 손실 전환 — 몇 번까지 연속으로 틀리나 (인내 요건)')
    segs = []
    for k in range(len(SW) - 1):
        segs.append(aB[SW[k + 1]] / aB[SW[k]] - 1)
    segs = np.array(segs)
    run, best, cum, bestcum = 0, 0, 1.0, 1.0
    for s_ in segs:
        if s_ < 0:
            run += 1
            cum *= (1 + s_)
            best = max(best, run)
            bestcum = min(bestcum, cum)
        else:
            run, cum = 0, 1.0
    print(f'  전환 간 구간 {len(segs)}개 중 손실 {int(np.sum(segs<0))}개 '
          f'({np.mean(segs<0):.0%})')
    print(f'  최장 연속 손실 {best}회 · 그 구간 누적 {bestcum-1:+.1%}')
    print(f'  단일 최악 구간 {segs.min():+.1%} · 중앙 {np.median(segs):+.1%}')
    print('  → 이 숫자가 「규칙을 의심하게 되는 순간」의 크기다 (판정선 없음).')


if __name__ == '__main__':
    main()
