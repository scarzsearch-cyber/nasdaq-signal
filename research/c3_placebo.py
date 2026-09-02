# -*- coding: utf-8 -*-
"""
[반증 2 · 플라시보] C3 「÷T-bill 낙폭」의 관문 통과는 우연인가 — 무작위 분포로 판정 (§-1 ⓑ, 2026-09-03)

C3 는 54년에서 Calmar +13.4% · 20년창 p05 +26% 로 관문 ①② 를 넘겼다(③ 미달). 39후보를 재는 동안 하나쯤 ①②를 넘는 것은 우연으로도 기대되므로,
「B 의 무작위 변형」과 「C3 기전의 가짜 판」이 같은 관문을 얼마나 자주 넘는지 센다.
  G1 무작위 변형 200개: 문턱 U(−20, −12) · 룩백 U(150, 350) — 규칙 모양은 B 그대로, 파라미터만 흔든 것.
  G2 가짜 기전 ① 상수 드리프트: 가격을 연 g% 로 깎은 지수의 낙폭(g ∈ {1,2,…,8}) — 「금리」가 아니라 「어떤 드리프트든」이면 값이 나오나.
  G3 가짜 기전 ② 뒤섞은 T-bill: 실제 T-bill 일수익을 연 단위 블록으로 뒤섞어(분포 같고 시점 틀림) 깎은 지수 — 200개. 시점이 중요하면 실제 C3 가 이 분포의 꼬리에 있어야 한다.
  G4 기전의 반대 부호: 가격에 T-bill 을 **더한** 지수(문턱이 깊어지는 쪽) — 방향이 맞는지.
판정(사전): C3 의 ΔCalmar(+13.4%)와 Δp05(+26.1%)가 G1·G3 분포의 상위 5% 밖(p<0.05)이면 「파라미터 잡음·시점 무관 잡음이 아니다」. 안이면 우연으로 닫는다.
예측: P1 G1 에서 ΔCalmar ≥ +13.4% 는 5% 미만(문턱 고원은 −14~−16 에 좁다). P2 G2 는 g 가 클수록 단조 — 즉 「얕은 문턱」 효과가 반쯤 섞여 있다.
      P3 G3 뒤섞은 T-bill 의 ΔCalmar 중앙은 +5~+10%(드리프트 크기는 같으니), 실제 C3 는 그 분포의 상위 20% 안 — 즉 시점 효과는 있으나 작다.

실행: python research/c3_placebo.py
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
IDX = pd.DatetimeIndex(G.idx); N = len(IDX)
PX = pd.Series(G.D['px'], index=IDX).astype(float)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float)); MIX = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
RQ = np.nan_to_num(PX.pct_change().values)
tb = pd.read_csv('data/hist/fred_DTB3.csv'); tb.columns = ['d', 'r']; tb['d'] = pd.to_datetime(tb['d'])
TB = (pd.to_numeric(tb.set_index('d')['r'], errors='coerce').reindex(IDX, method='ffill').fillna(0.0) / 100 / 252).values
LO = 252
L = '=' * 100


def dd_of(r, win):
    c = pd.Series(np.cumprod(1 + np.nan_to_num(r)), index=IDX)
    return (c / c.rolling(win, min_periods=win).max() - 1).values


def state(dd, th):
    w = np.ones(N); s = 1
    for t in range(N):
        d = dd[t]
        if not np.isnan(d):
            s = 0 if (s == 1 and d <= th) else (1 if (s == 0 and d > th) else s)
        w[t] = s
    return w


def evalw(w):
    c = np.asarray(EC.sim2(w[LO:], QLDR[LO:], MIX[LO:]), float)
    m = EC.fullmet(c, idx=IDX[LO:]); return m['calmar'], EC.p05_20y(c), m['final']


def main():
    print(L); print('C3 플라시보 — 무작위 변형·가짜 기전 분포에서 C3 의 자리 (규칙 무변경)'); print(L)
    calB, p05B, finB = evalw(state(dd_of(RQ, 252), -0.16))
    ex = (1 + RQ) / (1 + TB) - 1
    calC, p05C, finC = evalw(state(dd_of(ex, 252), -0.16))
    dC, pC = calC / calB - 1, p05C / p05B - 1
    print(f'  B Calmar {calB:.3f} · p05 {p05B:.1f}배 | C3 Calmar {calC:.3f} ({dC:+.1%}) · p05 {p05C:.1f}배 ({pC:+.1%})')
    rng = np.random.default_rng(42)
    # G1
    g1 = []
    for i in range(200):
        th = rng.uniform(-0.20, -0.12); lb = int(rng.integers(150, 351))
        c, p, f = evalw(state(dd_of(RQ, lb), th)); g1.append((c / calB - 1, p / p05B - 1, th, lb))
    a = np.array([x[0] for x in g1]); b = np.array([x[1] for x in g1])
    print(f'\n[G1] B 무작위 변형 200 (문턱 −20~−12 · 룩백 150~350): ΔCalmar 중앙 {np.median(a):+.1%} · p95 {np.quantile(a,.95):+.1%} · '
          f'≥ C3(+{dC*100:.1f}%) 인 비율 {np.mean(a >= dC)*100:.1f}% | Δp05 p95 {np.quantile(b,.95):+.1%} · ≥ C3 비율 {np.mean(b >= pC)*100:.1f}% | '
          f'①② 동시 {np.mean((a > 0.102) & (b >= 0))*100:.1f}%')
    top = sorted(g1, key=lambda x: -x[0])[:5]
    print('   상위 5:', ' · '.join(f'문턱 {th*100:.1f}%·룩백 {lb}: {c:+.1%}/{p:+.1%}' for c, p, th, lb in top))
    # G2
    print('\n[G2] 상수 드리프트로 깎은 낙폭 (연 g%) — ΔCalmar / Δp05')
    for g in (1, 2, 3, 4, 5, 6, 7, 8):
        exg = (1 + RQ) / (1 + g / 100 / 252) - 1
        c, p, f = evalw(state(dd_of(exg, 252), -0.16)); print(f'   g={g}%: {c/calB-1:+6.1%} / {p/p05B-1:+6.1%}   (실제 T-bill 54년 평균 {TB.mean()*252*100:.1f}%)')
    # G3
    yrs = IDX.year.values; uniq = sorted(set(yrs))
    g3 = []
    for i in range(200):
        perm = rng.permutation(len(uniq))
        shuf = np.empty(N)
        pos = 0
        # 연 블록 단위로 T-bill 일수익을 뒤섞어 같은 길이로 잇는다 (연 길이 차이는 순환 보정)
        src = np.concatenate([TB[yrs == uniq[k]] for k in perm])
        shuf = src[:N] if len(src) >= N else np.resize(src, N)
        exs = (1 + RQ) / (1 + shuf) - 1
        c, p, f = evalw(state(dd_of(exs, 252), -0.16)); g3.append((c / calB - 1, p / p05B - 1))
    a3 = np.array([x[0] for x in g3]); b3 = np.array([x[1] for x in g3])
    print(f'\n[G3] 뒤섞은 T-bill(연 블록 순열) 200: ΔCalmar 중앙 {np.median(a3):+.1%} · p95 {np.quantile(a3,.95):+.1%} · ≥ 실제 C3 비율 {np.mean(a3 >= dC)*100:.1f}% | '
          f'Δp05 중앙 {np.median(b3):+.1%} · ≥ 실제 C3 비율 {np.mean(b3 >= pC)*100:.1f}% | ①② 동시 {np.mean((a3 > 0.102) & (b3 >= 0))*100:.1f}%')
    # G4
    exp_ = (1 + RQ) * (1 + TB) - 1
    c, p, f = evalw(state(dd_of(exp_, 252), -0.16)); print(f'\n[G4] 반대 부호(가격 + T-bill): ΔCalmar {c/calB-1:+.1%} / Δp05 {p/p05B-1:+.1%}')
    print('\n판정:')
    print(f"  G1 상위 5% 밖? Calmar {'예' if np.mean(a >= dC) < 0.05 else '아니오'} · p05 {'예' if np.mean(b >= pC) < 0.05 else '아니오'}")
    print(f"  G3 상위 5% 밖? Calmar {'예' if np.mean(a3 >= dC) < 0.05 else '아니오'} · p05 {'예' if np.mean(b3 >= pC) < 0.05 else '아니오'}")
    print('  → 둘 다 「예」일 때만 「파라미터 잡음도 시점 무관 잡음도 아니다」. 하나라도 「아니오」면 그 축에선 우연과 구별되지 않는다.')


if __name__ == '__main__':
    main()
