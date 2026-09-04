# -*- coding: utf-8 -*-
"""
[성장 엔진 교체 연구 C, 2026-08-31] KOSPI 2배 합성 엔진 — 가설 B 검증.

데이터 한계 (금지 5·6 준수 — 전부 명시):
  - 지수: ^KS11 (KOSPI 종합, 1997-01~) — KOSPI200 아님(상관 ~0.98 대리),
    30년 창 하나뿐. 20년창 p05 는 표본 ~2,400개(겹침 심함)라 참고치.
  - 레버리지: 전 구간 합성 (실물 122630 캐시 없음). 차입비용은 미국
    c_daily 를 기본으로 쓰되 — 한국 금리가 더 높았으므로(IMF 기 20%+)
    기본형은 후보에 유리한 낙관 가정. 민감도 +1%/+2%p 연 추가 드래그 병행.
  - KRW 현금 방어는 금리 시계열이 없어 0% 로 — 방어에 불리(보수적).
프레임: 한국 투자자 원화 기준 — 미국 자산·기준선 B 는 DEXKOUS 로 원화 환산
  (환노출형. 현행 실전과 동일하게 환헤지 없음).
비교: 같은 창(1997~)의 B(원화 환산) 대비 관문 ①(Calmar×1.102)·②(p05).
실행: python research/eng_kospi.py
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
import hist_korea as K                                  # noqa: E402
import hist_defasset as DA                              # noqa: E402

THS = [(-0.10, -0.05), (-0.12, -0.08), (-0.15, -0.10), (-0.16, -0.11),
       (-0.16, -0.16), (-0.18, -0.12), (-0.20, -0.15), (-0.20, -0.10),
       (-0.25, -0.15)]


def _us_curve_known_at_korea_close(us_curve, us_idx, kidx):
    """한국 날짜마다 그 시각에 이미 끝난 직전 미국 세션 값만 고른다."""
    us_idx = pd.DatetimeIndex(us_idx)
    kidx = pd.DatetimeIndex(kidx)
    curve = np.asarray(us_curve, float)
    assert len(curve) == len(us_idx) and us_idx.is_monotonic_increasing
    pos = us_idx.searchsorted(kidx, side='left') - 1       # 같은 날짜 미국 종가는 미래
    if np.any(pos < 0):
        raise ValueError('첫 한국 날짜보다 앞선 미국 세션이 없어 원화 환산 불가')
    return curve[pos]


def _selfcheck_market_clock():
    us = pd.to_datetime(['2020-01-01', '2020-01-02', '2020-01-03'])
    kr = pd.to_datetime(['2020-01-02', '2020-01-03'])
    got = _us_curve_known_at_korea_close([1.0, 2.0, 4.0], us, kr)
    assert np.array_equal(got, [1.0, 2.0])                 # [2,4]면 같은 날 미래참조


def to_krw(us_curve, us_idx, kidx, fxk):
    """미국 달러 누적곡선 → 한국 거래일 원화곡선 (직전 미국 종가 × 당일 환율)."""
    v = _us_curve_known_at_korea_close(us_curve, us_idx, kidx)
    out = np.asarray(v * np.asarray(fxk, float), float)
    return out / out[0]


def main():
    _selfcheck_market_clock()
    G, X = EC.selfcheck()
    us_idx = G.idx
    tb = G.tb

    ks = K._kr(K.KOSPI)['Close'].astype(float)
    ks = ks[ks.index >= '1997-01-01']
    kidx = ks.index
    nk = len(kidx)
    fxk = K.fx(kidx).values
    r_k = np.nan_to_num(ks.pct_change().values)
    print(f'\n[창] {kidx[0].date()} ~ {kidx[-1].date()} · {nk}일 ({nk/252:.1f}년 상당) — '
          f'단일 30년 창, 시대 일반화 불가(금지 4)')

    # ---- 기준선 B 를 원화로 ----
    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    aB_us = EC.sim2(np.asarray(G.wB, float),
                    np.nan_to_num(np.asarray(G.D['qldr'], float)), MIXR)
    aB = to_krw(aB_us, us_idx, kidx, fxk)
    mB = EC.fullmet(aB, idx=kidx)
    pB = EC.p05_20y(aB)
    g1, g2 = mB['calmar'] * 1.102, pB
    print(f'[기준선 B(원화) 1997~] final {mB["final"]:.1f} · CAGR {mB["cagr"]:.2f} · '
          f'MDD {mB["mdd"]:.1f} · Calmar {mB["calmar"]:.3f} · p05(참고) {pB:.1f} '
          f'→ 관문① >{g1:.3f} · ② ≥{g2:.1f}')

    # ---- 방어 후보 (원화) ----
    def us_asset_krw(r_us):
        return np.nan_to_num(np.diff(
            to_krw(np.cumprod(1 + np.nan_to_num(r_us)), us_idx, kidx, fxk),
            prepend=1.0)) / np.concatenate(
            ([1.0], to_krw(np.cumprod(1 + np.nan_to_num(r_us)), us_idx, kidx, fxk)[:-1]))

    r_usd_cash = us_asset_krw(tb)                        # 달러현금(T-bill+환)
    r_ust10 = us_asset_krw(np.nan_to_num(DA.ust_tr(us_idx, 10, 'TNX')))
    r_gold = us_asset_krw(np.nan_to_num(DA.gold_r(us_idx)))
    r_usmix = us_asset_krw(MIXR)
    defs = [('현금0%', np.zeros(nk)), ('달러현금', r_usd_cash),
            ('미국채10Y', r_ust10), ('금', r_gold), ('미국mix', r_usmix),
            ('KOSPI1x', r_k)]

    # ---- 엔진 (합성 — 비용 3단) ----
    for extra, tag in ((0.0, '기본(미국비용 — 낙관)'), (0.01, '+1%p/yr'), (0.02, '+2%p/yr')):
        r_e = EC.synth2x(r_k, G.D['c_daily'] + extra / 252)
        hold = EC.fullmet(np.cumprod(1 + r_e), idx=kidx)
        print(f'\n=== 합성 KOSPI2x [{tag}] — 맨몸 보유 final {hold["final"]:.2f} '
              f'CAGR {hold["cagr"]:.2f}% MDD {hold["mdd"]:.0f}% ===')
        best = []
        shown = 0
        for (ti, to) in THS:
            w = EC.rule_dd(ks, ti, to)
            for dn, rd in defs:
                a = EC.sim2(w, r_e, rd)
                m = EC.fullmet(a, idx=kidx)
                p = EC.p05_20y(a)
                best.append((m['calmar'], p, ti, to, dn, m))
        best.sort(key=lambda t: -t[0])
        both = [(c, p, ti, to, dn) for c, p, ti, to, dn, _ in best
                if c > g1 and (np.isnan(p) or np.isnan(g2) or p >= g2)]
        print(f"{'문턱':>9} {'방어':<10} {'최종배수':>9} {'CAGR':>6} {'MDD':>7} "
              f"{'Calmar':>7} {'p05':>6} {'①':>2}")
        for c, p, ti, to, dn, m in best[:6]:
            print(f"{ti*100:>4.0f}/{to*100:>4.0f} {dn:<10} {m['final']:>9.1f} "
                  f"{m['cagr']:>6.2f} {m['mdd']:>7.1f} {c:>7.3f} {p:>6.1f} "
                  f"{'O' if c > g1 else '·':>2}")
        print(f'  54칸 중 관문① 통과 {sum(1 for c,_,_,_,_,_ in best if c>g1)}칸 · '
              f'동시(②p05 포함) {len(both)}칸')

    # ---- 기본형 상위 후보 시대 분해 (1997~2009 / 2010~) ----
    r_e = EC.synth2x(r_k, G.D['c_daily'])
    c0, p0, ti0, to0, dn0, m0 = sorted(
        [(EC.fullmet(EC.sim2(EC.rule_dd(ks, ti, to), r_e, rd), idx=kidx)['calmar'],
          EC.p05_20y(EC.sim2(EC.rule_dd(ks, ti, to), r_e, rd)), ti, to, dn,
          EC.fullmet(EC.sim2(EC.rule_dd(ks, ti, to), r_e, rd), idx=kidx))
         for ti, to in THS for dn, rd in defs], key=lambda t: -t[0])[0]
    a0 = EC.sim2(EC.rule_dd(ks, ti0, to0), r_e, dict(defs)[dn0])
    print(f'\n[IS 1등(기본형)] {ti0*100:.0f}/{to0*100:.0f} + {dn0}: Calmar {c0:.3f}')
    yr = pd.Series(kidx).dt.year.values
    for lab, m_ in (('1997~2009', yr <= 2009), ('2010~2026', yr >= 2010)):
        s0, sB = a0[m_] / a0[m_][0], aB[m_] / aB[m_][0]
        f0, fB = EC.fullmet(s0, idx=kidx[m_]), EC.fullmet(sB, idx=kidx[m_])
        print(f'  {lab}: 후보 배수 {f0["final"]:>7.2f} Calmar {f0["calmar"]:.3f} vs '
              f'B {fB["final"]:>7.2f} / {fB["calmar"]:.3f} '
              f'{"우세" if f0["calmar"] > fB["calmar"] else "열세"}')

    # ---- 부트스트랩 (동시행 L=252 N=500) — IS 1등 vs B ----
    r0 = np.diff(a0, prepend=1.0) / np.concatenate(([1.0], a0[:-1]))
    rB = np.diff(aB, prepend=1.0) / np.concatenate(([1.0], aB[:-1]))
    rng = np.random.default_rng(7)
    L, nrep = 252, 500
    nblk = nk // L + 1
    wins = 0
    for b0 in range(0, nrep, 100):
        m_ = min(100, nrep - b0)
        st = rng.integers(0, nk - L, size=(m_, nblk))
        pos = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(m_, -1)[:, :nk]
        A0 = np.cumprod(1 + r0[pos], axis=1)
        AB = np.cumprod(1 + rB[pos], axis=1)

        def cal(A):
            peak = np.maximum.accumulate(A, axis=1)
            mdd = np.abs(np.min(A / peak - 1, axis=1))
            return (A[:, -1] ** (252.0 / nk) - 1) / mdd
        wins += int(np.sum(cal(A0) > cal(AB)))
    print(f'\n[부트스트랩 L=252 N=500] IS 1등(기본형) Calmar > B(원화): {wins/nrep:.1%}')
    print('\n(주의: 후보는 IS 1등 + 낙관 비용 가정 + 단일 30년 창 — 세 겹의 상향 편향)')


if __name__ == '__main__':
    main()
