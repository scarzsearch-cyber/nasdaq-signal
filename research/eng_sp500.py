# -*- coding: utf-8 -*-
"""
[성장 엔진 교체 연구 B, 2026-08-31] S&P500 2배 합성 엔진 — 가설 A 검증.

엔진: GSPC(1970~) 일수익 × synth2x (2r − c_daily, lev_r k=2 규약 — QQQ/QLD
겹침 역산 비용을 그대로 적용. SSO 보수 0.89% 는 QLD 0.95% 와 유사).
⚠ 전 구간 합성 — 실물 SSO 시계열 캐시 없음 (금지 5: 실물 실적으로 표현 금지).
신호: GSPC 자체 252일 고점 낙폭 (마감 판정, 현행과 동일 구조).
방어 후보 6: mix 40/40/20 · 배당100 · T-bill · 국채10Y · 금 · SPX 1배(디레버).
문턱 격자 9쌍 (지시문 §4) — IS 지도 → WFA(5년 걸음) → 시대 분해 → 부트스트랩.
기준선: 현행 B (동결 −16/−16, QLD+mix — 지시문의 「−16/−11」은 동결 정의와
달라 동결 쪽으로 정정) — eng_common.selfcheck 로 공표 일치 확인 후 진행.
실행: python research/eng_sp500.py
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
import hist_defasset as DA                              # noqa: E402
import hist_data as H                                   # noqa: E402

THS = [(-0.10, -0.05), (-0.12, -0.08), (-0.15, -0.10), (-0.16, -0.11),
       (-0.16, -0.16), (-0.18, -0.12), (-0.20, -0.15), (-0.20, -0.10),
       (-0.25, -0.15)]


def main():
    G, X = EC.selfcheck()
    idx = G.idx
    n = len(idx)
    tb = G.tb

    spx = H._yahoo('data/hist/yahoo_GSPC.csv').reindex(idx).ffill()
    assert spx.isna().sum() == 0, 'GSPC 결측'
    r_spx = np.nan_to_num(spx.pct_change().values)
    r_e = EC.synth2x(r_spx, G.D['c_daily'])

    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    DIVR = np.nan_to_num(np.asarray(G.D['schdr'], float))
    defs = [('mix40/40/20', MIXR), ('배당100', DIVR), ('T-bill', tb),
            ('국채10Y', np.nan_to_num(DA.ust_tr(idx, 10, 'TNX'))),
            ('금', np.nan_to_num(DA.gold_r(idx))), ('SPX1x', r_spx)]

    # 기준선 B (공표 재현 완료) + 참고: 엔진 맨몸 비교
    aB = EC.sim2(np.asarray(G.wB, float), np.nan_to_num(np.asarray(G.D['qldr'], float)),
                 MIXR)
    mB = EC.fullmet(aB, tb, idx)
    g1, g2 = mB['calmar'] * 1.102, EC.p05_20y(aB)
    hold_q = EC.fullmet(np.cumprod(1 + np.nan_to_num(np.asarray(G.D['qldr'], float))), tb, idx)
    hold_s = EC.fullmet(np.cumprod(1 + r_e), tb, idx)
    print(f'\n[기준선 B] final {mB["final"]:.0f} · CAGR {mB["cagr"]:.2f} · MDD {mB["mdd"]:.1f} '
          f'· Calmar {mB["calmar"]:.3f} · Sortino {mB["sortino"]:.2f} · Sharpe {mB["sharpe"]:.2f} '
          f'· 최장회복 {mB["rec"]}일 → 관문① >{g1:.3f} · ② p05≥{g2:.1f}')
    print(f'[맨몸] QLD체인 보유 final {hold_q["final"]:.0f} MDD {hold_q["mdd"]:.0f}% · '
          f'SPX2x합성 보유 final {hold_s["final"]:.0f} MDD {hold_s["mdd"]:.0f}% '
          f'(엔진 소재 차이 — 시스템 비교의 배경)')

    # ---- IS 격자 지도 ----
    print(f'\n[IS 격자 — SPX2x 합성 · 신호 GSPC · 1972-02~ · 편도 0.1% · 판정 아님]')
    print(f"{'문턱':>9} {'방어':<12} {'최종배수':>10} {'CAGR':>6} {'MDD':>7} "
          f"{'Calmar':>7} {'p05':>6} {'①':>2} {'②':>2}")
    best = []
    for (ti, to) in THS:
        w = EC.rule_dd(spx, ti, to)
        for dn, rd in defs:
            a = EC.sim2(w, r_e, rd)
            m = EC.fullmet(a, tb, idx)
            p = EC.p05_20y(a)
            o1, o2 = m['calmar'] > g1, p >= g2
            best.append((m['calmar'], p, ti, to, dn, m))
            if o1 or o2 or (ti, to) == (-0.16, -0.16) or m['calmar'] > mB['calmar']:
                print(f"{ti*100:>4.0f}/{to*100:>4.0f} {dn:<12} {m['final']:>10.1f} "
                      f"{m['cagr']:>6.2f} {m['mdd']:>7.1f} {m['calmar']:>7.3f} {p:>6.1f} "
                      f"{'O' if o1 else '·':>2} {'O' if o2 else '·':>2}")
    both = [(c, p, ti, to, dn) for c, p, ti, to, dn, _ in best if c > g1 and p >= g2]
    print(f'  (표는 관문 근접·주요 칸만 표시 — 전체 {len(best)}칸 중 동시 통과 {len(both)}칸: '
          f'{[(f"{ti*100:.0f}/{to*100:.0f}", dn) for _, _, ti, to, dn in both] if both else "없음"})')

    # ---- 최고 IS 칸의 정밀 검증 (WFA·시대·부트스트랩) ----
    best.sort(key=lambda t: -t[0])
    c0, p0, ti0, to0, dn0, m0 = best[0]
    print(f'\n[IS 1등] {ti0*100:.0f}/{to0*100:.0f} + {dn0}: Calmar {c0:.3f} p05 {p0:.1f} '
          f'(주의 — IS 1등 선택 자체가 PBO 0.5 급 행위, 참고용)')
    rd0 = dict(defs)[dn0]

    # 시대 분해 — IS 1등 vs B
    a0 = EC.sim2(EC.rule_dd(spx, ti0, to0), r_e, rd0)
    print(f'\n[시대 분해 — Calmar (후보 vs B)]')
    eb = dict(EC.era_table(aB, idx))
    for nm, m in EC.era_table(a0, idx):
        print(f'  {nm}: {m["calmar"]:>6.3f} vs {eb[nm]["calmar"]:>6.3f} '
              f'{"우세" if m["calmar"] > eb[nm]["calmar"] else "열세"}')

    # WFA — 5년 걸음, 과거 Calmar 로 (문턱,방어) 선택
    bd = pd.Series(idx).searchsorted(
        [pd.Timestamp(f'{y}-01-01') for y in range(1992, 2027, 5)])
    segs, picks = [], []
    rB_d = np.diff(aB, prepend=1.0) / np.concatenate(([1.0], aB[:-1]))
    for k in range(len(bd)):
        tr, te = bd[k], bd[k + 1] if k + 1 < len(bd) else n
        if te <= tr:
            break
        bc, bpick = -9, None
        for (ti, to) in THS:
            w = EC.rule_dd(spx, ti, to)
            for dn, rd in defs:
                a = EC.sim2(w[:tr], r_e[:tr], rd[:tr])
                c = EC.fullmet(a, idx=idx[:tr])['calmar']
                if c > bc:
                    bc, bpick = c, (ti, to, dn)
        picks.append(f'{idx[tr].year}:{bpick[0]*100:.0f}/{bpick[1]*100:.0f}+{bpick[2]}')
        ti, to, dn = bpick
        w = EC.rule_dd(spx, ti, to)
        af = EC.sim2(w, r_e, dict(defs)[dn])
        rf = np.diff(af, prepend=1.0) / np.concatenate(([1.0], af[:-1]))
        segs.append(rf[tr:te])
    ro = np.concatenate(segs)
    aW = np.cumprod(1 + ro)
    aBs = np.cumprod(1 + rB_d[bd[0]:])
    mW, mBs = EC.fullmet(aW, idx=idx[bd[0]:]), EC.fullmet(aBs, idx=idx[bd[0]:])
    print(f'\n[WFA 1992~] 후보 배수 {mW["final"]:.1f} Calmar {mW["calmar"]:.3f} vs '
          f'B {mBs["final"]:.1f} / {mBs["calmar"]:.3f}')
    print(f'  선택 경로: {" ".join(picks)}')

    # 부트스트랩 — IS 1등 vs B (동시행, L=252, N=500)
    r0 = np.diff(a0, prepend=1.0) / np.concatenate(([1.0], a0[:-1]))
    rng = np.random.default_rng(7)
    L, nrep = 252, 500
    nblk = n // L + 1
    wins = 0
    for b0 in range(0, nrep, 100):
        m_ = min(100, nrep - b0)
        st = rng.integers(0, n - L, size=(m_, nblk))
        pos = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(m_, -1)[:, :n]
        A0 = np.cumprod(1 + r0[pos], axis=1)
        AB = np.cumprod(1 + rB_d[pos], axis=1)

        def cal(A):
            peak = np.maximum.accumulate(A, axis=1)
            mdd = np.abs(np.min(A / peak - 1, axis=1))
            return (A[:, -1] ** (252.0 / n) - 1) / mdd
        wins += int(np.sum(cal(A0) > cal(AB)))
    print(f'\n[부트스트랩 L=252 N=500] IS 1등 Calmar > B: {wins/nrep:.1%}')


if __name__ == '__main__':
    main()
