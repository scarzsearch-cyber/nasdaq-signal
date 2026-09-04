# -*- coding: utf-8 -*-
"""
[v82] 한국비용(편도 0.2%) 내성 T4 변형 — 정식 탐색 (소유자 승인 2026-08-29)

배경: T4 의 한국비용 페널티(최종 −26%)의 몸통은 게이트 잔왕복이다
  (ON 구간 중앙 5일 · OFF 중앙 4일 · 55%가 5일 이하 — v81 §6).
질문: 잔왕복을 억제하는 **한 손잡이(one-knob)** 변형이 방어(기전)를 잃지 않고
  비용 문제를 고치는가. 살아남으면 T4 옆에 **부(副)후보로 사전 등록**, 전멸이면 기록.

[다중성 선언] 이것은 같은 54년 표본의 17번째 채굴이다. 시험 변형 수 9 + 기준 1.
  표본 안 성적은 등록 자격 심사일 뿐이며, 증거는 미래 그림자 OOS 만이 준다.
  기각 이력 관련: 시간 잠금은 **B 맥락**에서 기각(v55). T4 는 회전 구조가 달라
  (연 7.3, 81%가 게이트) 별개 질문이다 — 기각의 적용 범위를 넘지 않는다.

[변형 — T4 의 vt40·th2·창20·룩백 4종은 불변, 게이트 동역학만]
  BASE      gate = votes ≥ 2 (현행 T4, 무기억)
  HYS(e,x)  OFF→ON 은 votes ≥ e, ON→OFF 는 votes < x.  (3,2) (2,1) (3,1)
  CONF(M)   원신호(votes≥2)가 현 상태와 M일 연속 다를 때만 전환.  M ∈ {2,3,5}
  HOLD(N)   전환 후 N일간 상태 고정.  N ∈ {5,10,21}

[★ 등록 관문 K1~K7 — 실행 전 고정. 전부 충족해야 부후보 등록]
  기준 규약: 54.5년 · T-bill 방어 · lag=1 · **편도 0.2%** (0.1% 는 참고 병기)
  K1 비용 완화   최종 ≥ 1.15 × T4      (T4 0.2% = 109,451 → 한도 ≥ 125,869)
  K2 방어 총량   MDD ≥ T4 MDD − 1.5%p  (T4 0.2% = −54.7% → 한도 ≥ −56.2%)
  K3 방어 사건   독립 도피 사건창 MDD 승률 vs B ≥ 70%
  K4 기전 보존   M1 사전 감속(도피 전 10일 평균 노출 < 0.7) ≥ 60%   (T4 = 16/21=76%, v203)
  K5 고원        같은 패밀리의 이웃 손잡이 값도 K1 의 90% 이상 (한 점 첨탑 배제)
  K6 부분표본    1972–1999 / 2000–2026 두 반쪽 **모두** 최종 ≥ 같은 반쪽의 T4
  K7 지연 강건   lag=2 에서 MDD ≥ T4(lag=2) − 1.5%p
  복수 통과 시 최종(0.2%) 최대인 것 하나만 등록 (사전 선언 타이브레이크).
  등록되어도 **평가 전용**이다 — 채택 검토는 별도로 v41 관문 전체를 요구한다.
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

from axis_lib import sim
from research_kit import verdict
from axis_t4_shadow import build, met, VT, TH, independent_escapes, event_bounds

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

KCOST = 0.002
HALF = '2000-01-01'


# ==================================================================== 게이트
def gate_hys(v, e, x):
    g = np.empty(len(v)); cur = 1.0
    for i, vi in enumerate(v):
        if cur > 0:
            if vi < x:
                cur = 0.0
        else:
            if vi >= e:
                cur = 1.0
        g[i] = cur
    return g


def gate_conf(v, M):
    g = np.empty(len(v)); cur = 1.0; run = 0
    for i, vi in enumerate(v):
        want = 1.0 if vi >= TH else 0.0
        run = run + 1 if want != cur else 0
        if run >= M:
            cur = want; run = 0
        g[i] = cur
    return g


def gate_hold(v, N):
    g = np.empty(len(v)); cur = 1.0; age = N
    for i, vi in enumerate(v):
        want = 1.0 if vi >= TH else 0.0
        if want != cur and age >= N:
            cur = want; age = 0
        else:
            age += 1
        g[i] = cur
    return g


def variants(votes):
    v = votes.fillna(4).values
    out = {'BASE': (v >= TH).astype(float)}
    for e, x in ((3, 2), (2, 1), (3, 1)):
        out['HYS(%d,%d)' % (e, x)] = gate_hys(v, e, x)
    for M in (2, 3, 5):
        out['CONF(%d)' % M] = gate_conf(v, M)
    for N in (5, 10, 21):
        out['HOLD(%d)' % N] = gate_hold(v, N)
    return out


# ==================================================================== 평가
def events(D, wB):
    return independent_escapes(wB)


def ev_stats(D, w, cB, keep):
    c, _ = sim(D, w, cost=KCOST)
    wins, m1 = [], []
    for e in keep:
        a, b = event_bounds(len(D['idx']), e)
        sT = c.iloc[a:b]; sB = cB.iloc[a:b]
        wins.append(float((sT / sT.cummax() - 1).min()) > float((sB / sB.cummax() - 1).min()))
        m1.append(w[max(0, e - 10):e].mean() < 0.7)
    return np.mean(wins), np.mean(m1)


def main():
    D, wT, wB, votes, rv = build('tbill')
    idx = D['idx']
    yrs = (idx[-1] - idx[0]).days / 365.25
    wv = (VT / rv).clip(upper=1.0).fillna(1.0).values
    keep = events(D, wB)
    cB, _ = sim(D, wB, cost=KCOST)

    # T4 기준값 (관문의 분모)
    refs = {}
    base_w = wv * (votes.fillna(4).values >= TH)
    c, _ = sim(D, base_w, cost=KCOST); refs['m'] = met(c)
    c2, _ = sim(D, base_w, cost=KCOST, lag=2); refs['lag2_mdd'] = met(c2)['mdd']
    ca, _ = sim(D, base_w, cost=KCOST, end=HALF); refs['h1'] = float(ca.iloc[-1])
    cb, _ = sim(D, base_w, cost=KCOST, start=HALF); refs['h2'] = float(cb.iloc[-1])

    fam = {'HYS(3,2)': ['HYS(2,1)', 'HYS(3,1)'], 'HYS(2,1)': ['HYS(3,2)', 'HYS(3,1)'],
           'HYS(3,1)': ['HYS(3,2)', 'HYS(2,1)'],
           'CONF(2)': ['CONF(3)'], 'CONF(3)': ['CONF(2)', 'CONF(5)'], 'CONF(5)': ['CONF(3)'],
           'HOLD(5)': ['HOLD(10)'], 'HOLD(10)': ['HOLD(5)', 'HOLD(21)'], 'HOLD(21)': ['HOLD(10)']}

    rows = {}
    print('=' * 108)
    print('한국비용 내성 T4 변형 — 편도 0.2% (참고: 0.1%) · T-bill · lag=1')
    print('=' * 108)
    print('%-10s %10s %8s %8s %7s %6s %6s %6s %10s %10s %8s %9s' %
          ('변형', '최종0.2%', 'MDD', 'Calmar', '회전/yr', '사건승', 'M1', 'lag2MDD',
           '전반72-99', '후반00-26', '최종0.1%', 'K1~K7'))
    for nm, g in variants(votes).items():
        w = wv * g
        c, _ = sim(D, w, cost=KCOST)
        m = met(c)
        turn = np.abs(np.diff(np.r_[w[0], w[:-1]], prepend=w[0])).sum() / yrs
        evw, m1 = ev_stats(D, w, cB, keep)
        c2, _ = sim(D, w, cost=KCOST, lag=2); l2 = met(c2)['mdd']
        ca, _ = sim(D, w, cost=KCOST, end=HALF); h1 = float(ca.iloc[-1])
        cb2, _ = sim(D, w, cost=KCOST, start=HALF); h2 = float(cb2.iloc[-1])
        c1, _ = sim(D, w, cost=0.001); f1 = float(c1.iloc[-1])
        ks = dict(
            K1=m['final'] >= 1.15 * refs['m']['final'],
            K2=m['mdd'] >= refs['m']['mdd'] - 0.015,
            K3=evw >= 0.70, K4=m1 >= 0.60,
            K6=h1 >= refs['h1'] and h2 >= refs['h2'],
            K7=l2 >= refs['lag2_mdd'] - 0.015)
        rows[nm] = dict(m=m, turn=turn, ks=ks)
        print('%-10s %10s %7.1f%% %8.3f %7.1f %5.0f%% %5.0f%% %7.1f%% %10.1f %10.1f %8s %9s' %
              (nm, format(m['final'], ',.0f'), m['mdd'] * 100, m['calmar'], turn,
               evw * 100, m1 * 100, l2 * 100, h1, h2, format(f1, ',.0f'),
               ''.join('O' if ks[k] else 'X' for k in ('K1', 'K2', 'K3', 'K4', 'K6', 'K7'))
               if nm != 'BASE' else '기준'))

    # K5 고원 + 종합 판정
    passers = []
    for nm, r in rows.items():
        if nm == 'BASE' or not all(r['ks'].values()):
            continue
        nb = [rows[q]['m']['final'] for q in fam.get(nm, []) if q in rows]
        k5 = bool(nb) and max(nb) >= 0.90 * 1.15 * refs['m']['final']
        if k5:
            passers.append(nm)
        r['ks']['K5'] = k5
    print()
    if passers:
        best = max(passers, key=lambda q: rows[q]['m']['final'])
        checks = [(k, v, '') for k, v in rows[best]['ks'].items()]
        print(verdict('등록 후보: %s' % best, checks)['text'])
    else:
        fails = {nm: [k for k, v in r['ks'].items() if not v]
                 for nm, r in rows.items() if nm != 'BASE'}
        print('[판정] 전멸 — K1~K7 을 전부 충족한 변형 없음')
        for nm, f in fails.items():
            print('   %-10s 미달: %s' % (nm, ','.join(f) if f else '(K5 고원 미달)'))


if __name__ == '__main__':
    main()
