# -*- coding: utf-8 -*-
"""
[가설 실험 종장, 소유자 지시 2026-08-31] 외부 정보원 총동원의 마지막 빈 칸 —
**공격 구간 사이징**에 외부 눈을 단다.

무덤 대조 (04 §외부): VIX·하이일드·공포탐욕 게이트 기각(동행지표) · VIX 매일
게이트 기각(v51) · VIX 상태변수 기각(v52 — 역대 최강이었으나 1990~ 라 4블록 중
2개 검증 불가) · 장단기 금리차 기각(v31 — 선행하나 산포 7~533일). 전부 **복귀
타이밍 또는 전환 게이트**로 시험된 것. 남은 빈 칸 = 공격 중 연속 사이징의 발동
조건을 외부 자산 상태로 거는 것 (hypo_escape 의 dd 문맥판은 12칸 전멸 — 이번엔
낙폭 대신 남의 자산의 눈으로).

가족 2 (각각 소격자 전부 공개 — 고르지 않는다):
  FTQ  국채가 최근 21일 +θ% 이상 랠리 중(질주하는 안전자산 = 폭풍 지속 가설)일
       때만 변동성 사이징. θ∈{1,2}% × VT∈{40,60}%
  BRD  광역시장(NYA 63일 수익 < φ)이 무너지는데 나스닥은 버틸 때(얇은 리더십)만
       사이징. φ∈{0,−5}% × VT∈{40,60}%
외부 계열 규약: v51 그대로 — reindex+ffill 만, bfill 금지(미래참조). 데이터
이전 구간은 발동 없음(=B). 실행: hypo_hex.three_way (검산 완료 엔진).
평가: 1972-02~ 전창 · 관문 ①② · 퇴화 검산(발동 0 == B).
⚠ 창 단위 비교는 판정 아님(v80).
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

import hist_data as H                                   # noqa: E402
import hypo_gates as G                                  # noqa: E402
import hypo_hex as X                                    # noqa: E402

idx = G.idx
n = len(idx)
wB = X.wB


def ext(path):
    """외부 계열을 체인 달력에 — ffill 만(bfill 금지, v51 규약)."""
    s = H._yahoo(path)
    return s.reindex(idx.union(s.index)).ffill().reindex(idx)


# 국채 10Y 총수익 21일 랠리 (검증 재료 G.r_b10)
b10 = pd.Series(np.cumprod(1 + G.r_b10), index=idx)
ftq21 = (b10 / b10.shift(21) - 1)

# 광역 NYA vs 나스닥 체인 63일 수익
nya = ext(_os.path.join('data', 'hist', 'yahoo_NYA.csv'))
r63_nya = (nya / nya.shift(63) - 1)
pxc = pd.Series(np.cumprod(1 + np.nan_to_num(G.r_eq1)), index=idx)
r63_ndx = (pxc / pxc.shift(63) - 1)


def brake(danger, vt):
    vs = np.clip(vt / X.rv, 0, 1)
    vs[~np.isfinite(vs)] = 1.0
    d = np.asarray(danger.fillna(False), bool)          # 데이터 없으면 발동 없음
    scale = np.where(d, vs, 1.0)
    wq = wB * scale
    return X.three_way(wq, 1 - wB, wB - wq)


def main():
    # 퇴화 검산: 발동 0 == B
    zero = brake(pd.Series(False, index=idx), 0.40)
    ref = X.three_way(wB, 1 - wB, np.zeros(n))
    e = float(np.max(np.abs(zero.values / ref.values - 1)))
    assert e < 1e-12, e
    print(f'[검산] 발동 0 == B 오차 {e:.1e}  OK')

    b = G.report('B', G.cB)
    c1, c2 = b['calmar'] * 1.102, b['q20']
    print(f'\n[가족별 소격자 전부 — 관문① Calmar>{c1:.3f} · 관문② q20≥{c2:.1f} · 1972~ 전창]')
    print(f"{'후보':<24} {'최종배수':>10} {'MDD%':>7} {'Calmar':>7} {'q20':>6} {'①':>3} {'②':>3}")
    wins = []
    cands = []
    for th in (0.01, 0.02):
        for vt in (0.40, 0.60):
            cands.append((f'FTQ 채권21d>{th*100:.0f}% VT{vt*100:.0f}',
                          (ftq21 > th)))
            cands[-1] = (cands[-1][0], cands[-1][1], vt)
    for ph in (0.00, -0.05):
        for vt in (0.40, 0.60):
            cands.append((f'BRD NYA63d<{ph*100:.0f}% VT{vt*100:.0f}',
                          (r63_nya < ph) & (r63_ndx > 0), vt))
    for name, danger, vt in cands:
        r = G.report('', brake(danger, vt))
        m1, m2 = r['calmar'] > c1, r['q20'] >= c2
        if m1 and m2:
            wins.append(name)
        print(f"{name:<24} {r['final']:>10.1f} {r['mdd']:>7.2f} {r['calmar']:>7.3f} "
              f"{r['q20']:>6.1f} {'O' if m1 else '·':>3} {'O' if m2 else '·':>3}"
              + ('   ★' if m1 and m2 else ''))
    print(f'\n동시 통과: {wins if wins else "0/8 — 외부 눈을 달아도 공격측 사이징 공간에 육각형 없음"}')


if __name__ == '__main__':
    main()
