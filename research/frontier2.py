# -*- coding: utf-8 -*-
"""
[새 길 탐구 2 · 가상] 경제적 이유가 있는 구조 셋 — 원화 투자자의 환 오버레이 · 계절 노출 · 고점의 정의 (2026-09-03, 소유자 「B 를 능가할 때까지 계속」)

지금까지 36후보가 B 위로 못 올라갔다. 이번엔 파라미터가 아니라 **이유가 있는 구조**만 셋 고른다(04 grep: 환 오버레이·계절·평활 고점 선행 0).
  X1 환 오버레이(원화 1997~): 418660 은 환노출 2배다. 원/달러가 5년 평균보다 **θ 이상 약할 때**(1998·2008~09·2022·2024~25 처럼 극단)만 공격 다리를
     환헤지(2배 헤지 합성, carry 실측)로 바꾸고, 괴리가 θ/2 아래로 내려오면 환노출로 복귀(히스테리시스). 이유: 극단적 원화 약세는 되돌아왔고,
     그 되돌림은 환노출 2배 투자자에게 손실(1998 원화 반등 · 2009 · 2023). θ ∈ {10, 15, 20%}. 신호·문턱·방어는 B 그대로.
  X2 계절 노출(달러 1972~): 공격 상태에서 11~4월 2배, 5~10월 1배(나머지 절반 현금). 이유는 약하다(「Sell in May」) — 대조군으로 넣는다.
  X3 고점의 정의(달러 1972~): 252일 고점을 **원시 종가**가 아니라 **21일 이동평균**으로 잰다(하루 튄 고점이 문턱을 끌어올리는 것을 막는다).
     문턱 −16·복귀 −16 그대로. 이유: 신호의 분모를 안정시키는 것뿐, 규칙은 같다.
관문 ① Calmar +10.2% ② 20년창 p05 ≥ B ③ 4블록 3+ (같은 창의 B 대비). 통과 시 §-1 ⓐ 반증.

★ 사전 등록 예측:
  P1 X1: 1998·2008·2022 창의 원화 낙폭은 얕아지나(3사건) 30년 Calmar 는 ±10% 안 — 사건 3개로는 잡음. ①②③ 미달.
  P2 X2: 최종 0.5~0.8×, Calmar 0.8~1.0× — 진다.
  P3 X3: B 의 ±5% — 같은 규칙의 다른 표기. 갈린 전환 사건 10건 미만.
  P4 셋 다 ①②③ 동시 통과 없음.
  「틀리면 무엇이 참인가」: X1 이 ①②③ 을 넘으면 환 극단 되돌림이 원화 투자자의 진짜 여지다 → 반증(사건 수·θ 고원·역방향 창) 뒤 §7 후보.

실행: python research/frontier2.py
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

import hist_korea as K                                   # noqa: E402
import hist_krfinal as KF                                # noqa: E402
import hist_defasset as DA                               # noqa: E402
import eng_common as EC                                  # noqa: E402

L = '=' * 100
STRAT_B = dict(enter=-0.16, exit=-0.16, name='−16 / −16', ladder=[(('dd', -0.16), 1.0, 0)])
WIN = [('IMF 1997', '1997-06-01', '1998-12-31'), ('닷컴 2000', '2000-03-01', '2002-12-31'), ('금융위기 2008', '2007-10-01', '2009-06-30'),
       ('코로나 2020', '2020-02-01', '2020-06-30'), ('금리 2022', '2021-11-01', '2022-12-31')]


def met(c, ix):
    m = EC.fullmet(np.asarray(c, float), idx=ix); m['p05'] = EC.p05_20y(np.asarray(c, float)); return m


def blocks(c, ix, nb=4):
    c = np.asarray(c, float); e = np.linspace(0, len(c), nb + 1).astype(int)
    return [EC.fullmet(c[a:b] / c[a], idx=ix[a:b])['calmar'] for a, b in zip(e[:-1], e[1:])]


def gate(m, mB, bl, bB):
    wins = sum(1 for x, y in zip(bl, bB) if x > y)
    return (m['calmar'] / mB['calmar'] - 1 > 0.102, (not np.isnan(m['p05'])) and m['p05'] >= mB['p05'], wins >= 3), wins


def show(nm, m, mB, g, wins):
    tag = '★①②③' if all(g) else ('①' if g[0] else '-') + ('②' if g[1] else '-') + ('③' if g[2] else '-')
    print(f"  {nm:<40}{m['final']:>10,.1f}{m['final']/mB['final']:>6.2f}x{m['cagr']:>7.2f}%{m['mdd']:>7.1f}%{m['calmar']:>8.3f}"
          f"{(m['calmar']/mB['calmar']-1)*100:>+7.1f}%{m['p05']:>8.2f}배{(m['p05']/mB['p05']-1)*100:>+7.1f}%{wins:>4d}/4  {tag}")


def header():
    print(f"  {'후보':<40}{'최종':>10}{'vsB':>7}{'CAGR':>8}{'MDD':>8}{'Calmar':>8}{'ΔCal':>8}{'20y p05':>9}{'Δp05':>8}{'블록':>6}  관문")


# ───────────────────────────── X1 환 오버레이 (원화) ─────────────────────────────
def x1():
    D, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    krd = K.kr_caldays()
    rq = np.nan_to_num(D['px'].pct_change().values); c_d = D['c_daily']
    us3 = DA._short_rate(idx)
    kr = pd.read_csv('data/hist/kr_3m_rate.csv'); kr3 = pd.Series(kr['rate'].values, index=pd.to_datetime(kr['date'])).sort_index()
    kr3 = kr3.reindex(idx.union(kr3.index)).ffill().reindex(idx).values / 100.0
    carry = np.nan_to_num((kr3 - us3) / 252.0)
    lev2h = 2 * rq - c_d + carry
    fx = K.fx(idx)
    dev = (fx / fx.rolling(1260, min_periods=756).mean() - 1).values
    raw = {'div': np.asarray(dfk, float), 'ust5': DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE), 'gold': DA.gold_r(idx)}
    parts = {k: (raw[k] if k == 'div' else (1 + raw[k]) * (1 + fr) - 1) for k in DA.MIX_V23}
    sr = DA.mix_monthly_parts(idx, DA.MIX_V23, parts)
    lo = idx.searchsorted(pd.Timestamp(KF.ST))

    def run(qr):
        Dx = dict(D); Dx['qldr'] = qr; Dx['schdr'] = sr
        c, w, t = K.run_kr(Dx, STRAT_B, cost=0.001, slip=0.001, start=KF.ST, krdays=krd)
        return pd.Series(np.asarray(c, float), index=(c.index if hasattr(c, 'index') else idx[lo:lo + len(c)]))

    cB = run(lev2); ixB = cB.index; mB = met(cB.values, ixB); bB = blocks(cB.values, ixB)
    print('\n' + L); print(f'X1 환 오버레이 — 원화 {ixB[0].date()}~{ixB[-1].date()} · B(환노출 2배) Calmar {mB["calmar"]:.3f} · 20y p05 {mB["p05"]:.2f}배 · MDD {mB["mdd"]:.1f}%'); print(L)
    header()
    res = {}
    for th in (0.10, 0.15, 0.20):
        on = np.zeros(len(idx), bool); s = False
        for t in range(len(idx)):
            d = dev[t]
            if not np.isnan(d):
                s = True if (not s and d > th) else (False if (s and d < th / 2) else s)
            on[t] = s
        qr = np.where(on, lev2h, lev2)
        c = run(qr); m = met(c.values, c.index); bl = blocks(c.values, c.index); g, wins = gate(m, mB, bl, bB)
        # 헤지 상태 일수 비율 · 위기 창
        share = float(on[lo:].mean()) * 100
        show(f'X1 θ={th*100:.0f}% (헤지 일수 {share:.0f}%)', m, mB, g, wins)
        res[th] = (c, on)
    print('\n  위기 창 MDD (원화 전략 곡선)          B(환노출)  ' + '  '.join(f'θ={th*100:.0f}%' for th in res))
    for nm, a, b in WIN:
        segB = cB.loc[a:b]; mdB = float(np.min(segB.values / np.maximum.accumulate(segB.values) - 1)) * 100
        cells = []
        for th, (c, on) in res.items():
            seg = c.loc[a:b]; cells.append(float(np.min(seg.values / np.maximum.accumulate(seg.values) - 1)) * 100)
        print(f'  {nm:<14} {a}~{b}  {mdB:>7.1f}%  ' + '  '.join(f'{x:>6.1f}%' for x in cells))
    return {f'X1 θ={th*100:.0f}%': gate(met(c.values, c.index), mB, blocks(c.values, c.index), bB)[0] for th, (c, on) in res.items()}


# ───────────────────────────── X2 · X3 (달러 54년) ─────────────────────────────
def x23():
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        G, _ = EC.selfcheck()
    idx = pd.DatetimeIndex(G.idx); N = len(idx)
    PX = pd.Series(G.D['px'], index=idx).astype(float)
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float)); MIX = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    lo = 252; ix = idx[lo:]
    wB = np.asarray(EC.rule_dd(PX, -0.16, -0.16), float)
    cB = np.asarray(EC.sim2(wB[lo:], QLDR[lo:], MIX[lo:]), float); mB = met(cB, ix); bB = blocks(cB, ix)
    print('\n' + L); print(f'X2 계절 노출 · X3 고점의 정의 — 달러 {ix[0].date()}~{ix[-1].date()} · B Calmar {mB["calmar"]:.3f} · 20y p05 {mB["p05"]:.2f}배'); print(L)
    header()
    out = {}
    # X2: 공격 중 5~10월은 절반 현금(=1배)
    month = idx.month.values
    half = np.isin(month, [5, 6, 7, 8, 9, 10])
    w = wB.copy(); w[half & (wB == 1)] = 0.5
    r_cash = np.zeros(N)                               # 절반은 현금(0 수익) — 보수적
    r_mix = MIX
    # 2분할 시뮬은 w·QLDR + (1−w)·MIX 라 절반 현금을 못 표현 → 3자산 손으로
    pos = np.r_[w[0], w[:-1]]; posB = np.r_[wB[0], wB[:-1]]
    r = pos * QLDR + (posB - pos) * r_cash + (1 - posB) * r_mix
    turn = np.abs(np.diff(pos, prepend=pos[0])) + np.abs(np.diff(posB, prepend=posB[0]))
    c = np.cumprod((1 + r) * (1 - EC.COST * turn))[lo:] / 1.0
    m = met(c, ix); g, wins = gate(m, mB, blocks(c, ix), bB); show('X2 계절 노출 (5~10월 1배)', m, mB, g, wins); out['X2'] = g
    # X3: 21일 이동평균의 252일 고점
    sm = PX.rolling(21).mean()
    dd = (sm / sm.rolling(252, min_periods=252).max() - 1).values
    w3 = np.ones(N); s = 1
    for t in range(N):
        d = dd[t]
        if not np.isnan(d):
            s = 0 if (s == 1 and d <= -0.16) else (1 if (s == 0 and d > -0.16) else s)
        w3[t] = s
    c3 = np.asarray(EC.sim2(w3[lo:], QLDR[lo:], MIX[lo:]), float)
    m3 = met(c3, ix); g3, wins3 = gate(m3, mB, blocks(c3, ix), bB); show('X3 고점 = 21일 이동평균의 252일 최고', m3, mB, g3, wins3); out['X3'] = g3
    diff = int(np.sum((w3 != wB)[lo:])); ev = int(np.sum(((np.diff(w3) != 0) != (np.diff(wB) != 0))[lo:]))
    print(f'  X3 가 B 와 상태가 다른 날 {diff} · 전환 시점이 갈린 사건 {ev}')
    return out


def main():
    print(L); print('새 길 탐구 2 — 환 오버레이 · 계절 노출 · 고점의 정의 (규칙 무변경 · 모의 실험)'); print(L)
    r1 = x1(); r23 = x23()
    allg = {**r1, **r23}
    passed = [k for k, g in allg.items() if all(g)]
    print('\n' + L); print('사전 등록 대조'); print(L)
    print(f"  P4 (①②③ 동시 통과 없음): {'맞음' if not passed else '틀림 — ' + str(passed) + ' → 반증 필요'}")
    print('  P1~P3 은 위 표의 ΔCal·Δp05·갈린 사건 수로 대조 (본문에 기록).')
    print('\n이 측정이 낳은 다음 질문 (§-1 절대멈춤 6):')
    print('  · X1 이 위기 창 낙폭을 줄였다면 그 값은 「환 극단」 3사건의 것이다 — 다음 극단(원화 +20% 약세)이 동결 이후에 오면 사건 단위로 잰다.')
    print('  · X3 의 갈린 사건 수가 적다면 고점의 정의는 B 의 자유도가 아니다 — 문턱·룩백과 같은 서랍에 넣고 닫는다.')


if __name__ == '__main__':
    main()
