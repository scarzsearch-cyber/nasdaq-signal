# -*- coding: utf-8 -*-
"""
[통합 연구 Part 1 후속, 2026-08-31] PBO — 이번 가설 총력전에서 실제로 탐색한
후보 전부를 CSCV(조합 대칭 교차검증, Bailey–López de Prado 2014)에 넣어
「표본 내 1등을 고르는 행위」가 얼마나 과적합인지 잰다.

후보 우주 (hypo_* 에서 실제 계산된 것 재조립 — 새 후보 없음):
  혼합 x=0.05~0.95 (19) · hex 조합 4 · escape 격자 12 · external 8 ·
  gates A/K (2) · B · T4  = 47개
방법: 54년 일수익을 S=8 연속 블록으로 자르고 C(8,4)=70 분할 각각에서
  IS 1등 후보의 OOS 상대순위 ω 를 기록. PBO = P(ω<0.5).
지표: Sharpe(주판정 — 블록 이어붙임에 불변) · Calmar(참고 — 이어붙임이 MDD 를
  왜곡하므로 보조). v70 의 T4 변형 PBO 0.437 과 대조 가능.
실행: python research/audit_pbo.py   (gates A/K 재계산 포함 수 분)
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
from itertools import combinations
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hypo_gates as G                                  # noqa: E402
import hypo_hex as X                                    # noqa: E402
import hypo_t4_real as R                                # noqa: E402
import hypo_escape as ES                                # noqa: E402
import hypo_external2 as E                              # noqa: E402

n = len(G.idx)
wT4 = R.t4_w(G.r_eq1)


def rets(curve):
    a = curve.values
    return np.diff(a, prepend=1.0) / np.concatenate(([1.0], a[:-1]))


def build_universe():
    names, rows = [], []

    def add(nm, c):
        names.append(nm)
        rows.append(rets(c))

    add('B', X.three_way(X.wB, 1 - X.wB, np.zeros(n)))
    add('T4', X.three_way(wT4, np.zeros(n), 1 - wT4))
    for x in np.arange(0.05, 0.951, 0.05):
        add(f'mix{x:.2f}', X.blend(float(x)))
    v40, v60 = X.vscale(0.40), X.vscale(0.60)
    add('합의체', X.three_way(X.wB * wT4, 1 - X.wB, X.wB * (1 - wT4)))
    add('VT40', X.three_way(X.wB * v40, 1 - X.wB, X.wB * (1 - v40)))
    add('VT60', X.three_way(X.wB * v60, 1 - X.wB, X.wB * (1 - v60)))
    add('VT60mix', X.three_way(X.wB * v60, 1 - X.wB * v60, np.zeros(n)))
    for th in (-0.02, -0.04, -0.06, -0.08):
        for vt in (0.40, 0.50, 0.60):
            add(f'esc{th*100:.0f}/{vt*100:.0f}', ES.escape(th, vt))
    for th in (0.01, 0.02):
        for vt in (0.40, 0.60):
            add(f'FTQ{th*100:.0f}VT{vt*100:.0f}', E.brake(E.ftq21 > th, vt))
    for ph in (0.00, -0.05):
        for vt in (0.40, 0.60):
            add(f'BRD{ph*100:.0f}VT{vt*100:.0f}',
                E.brake((E.r63_nya < ph) & (E.r63_ndx > 0), vt))
    legsA = [(G.r_eq1, G.r_eq1, 1.0), (G.r_b10, G.r_b3x, 3.0), (G.r_gld, G.r_gld, 1.0)]
    add('gatesA', G.sim_multi(legsA))
    add('gatesK', G.sim_multi([(G.r_eq1, G.r_eq2, 2.0), (G.r_b5f, G.r_b5f, 1.0),
                               (G.r_gld, G.r_gld, 1.0)]))
    return names, np.vstack(rows)


def metric(Rsub, kind):
    if kind == 'sharpe':
        return Rsub.mean(axis=1) / Rsub.std(axis=1, ddof=1)
    a = np.cumprod(1 + Rsub, axis=1)
    peak = np.maximum.accumulate(a, axis=1)
    mdd = np.abs(np.min(a / peak - 1, axis=1))
    cagr = a[:, -1] ** (252.0 / Rsub.shape[1]) - 1
    return cagr / np.maximum(mdd, 1e-9)


def cscv(Rm, names, kind, label):
    S = 8
    bnd = np.linspace(0, Rm.shape[1], S + 1, dtype=int)
    blocks = [np.arange(bnd[i], bnd[i + 1]) for i in range(S)]
    lam, below, picks = [], 0, {}
    for isb in combinations(range(S), S // 2):
        oob = [b for b in range(S) if b not in isb]
        i_idx = np.concatenate([blocks[b] for b in isb])
        o_idx = np.concatenate([blocks[b] for b in oob])
        mi = metric(Rm[:, i_idx], kind)
        mo = metric(Rm[:, o_idx], kind)
        best = int(np.argmax(mi))
        picks[names[best]] = picks.get(names[best], 0) + 1
        w = (np.sum(mo < mo[best]) + 0.5 * np.sum(mo == mo[best])) / len(mo)
        w = min(max(w, 1e-6), 1 - 1e-6)
        lam.append(np.log(w / (1 - w)))
        below += int(w < 0.5)
    lam = np.asarray(lam)
    top = sorted(picks.items(), key=lambda t: -t[1])[:4]
    print(f'  {label:<26} PBO={below/len(lam):.3f} · λ중앙 {np.median(lam):+.2f} · '
          f'IS 1등 빈도: ' + ', '.join(f'{k}({v})' for k, v in top))


def main():
    names, Rm = build_universe()
    print(f'[후보 우주 {len(names)}개 · {Rm.shape[1]}일 · CSCV S=8 (70분할)]')
    for kind in ('sharpe', 'calmar'):
        print(f'\n지표 = {kind}')
        cscv(Rm, names, kind, '전체 47')
        sel = [i for i, nm in enumerate(names) if nm.startswith('mix')]
        cscv(Rm[sel], [names[i] for i in sel], kind, '혼합 가족만 19')
        sel2 = [i for i, nm in enumerate(names) if not nm.startswith('mix')]
        cscv(Rm[sel2], [names[i] for i in sel2], kind, '혼합 제외 28')
    print('\n(참고: v70 T4 변형 PBO 0.437 — PBO≈0.5 는 IS 1등 선택이 동전던지기라는 뜻.'
          '\n PBO 가 낮아도 창단위 비교는 판정이 아니다(v80) — 증거 강도 기록 전용)')


if __name__ == '__main__':
    main()
