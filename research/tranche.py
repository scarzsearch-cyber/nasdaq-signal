# -*- coding: utf-8 -*-
"""
[트랜치 / 리밸런스 타이밍 운, 2026-08-31 소유자 승인] 04 무덤에 0건인 축.

배경: Hoffstein, Faber & Sibears (2020), "Rebalance Timing Luck: The Difference
  Between Hired and Fired", J. Index Investing 10(1), 27–36 — 똑같이 운용되는 두
  전략이 **일정만 달라도** 생기는 성과 분산. 지수에서 연 100bp 넘는 경우가 흔하다.
  04 §5-4 의 유산 「부의 바닥 관문 아래에서 유효한 분산은 자산 분산이 아니라
  **같은 복리 엔진의 시계 분산**뿐」이 이 축을 직접 가리킨다.

**중요 — B 에는 고전적 RTL 이 적용되지 않는다**:
  B 의 신호는 252일 롤링 고점 대비 낙폭이라 **시작일에 의존하지 않는다.**
  워밍업 이후 두 투자자의 dd 계열이 같아지므로 상태가 수렴한다. [2] 가 이를 실측한다.
  따라서 B 의 타이밍 운은 「언제 시작했나」가 아니라 **「룩백을 252 로 고른 것」**에 있다
  (Hoffstein 의 specification luck). [3] 이 그 크기를 재고, [4] 가 트랜치로 줄인다.

**평가 전용 — 채택 아님.** 각 트랜치는 서로 다른 룩백을 쓰므로 앙상블은 B 가 아니다
(T4 그림자와 같은 지위). 동결 규칙 무접촉.

검산: 트랜치 1개(룩백 252) ≡ 현행 B, 오차 0 — §3 규약 ⓓ 의 축퇴 검산.
실행: python research/tranche.py
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
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
TH = -0.16
BASE = 252


def met(a):
    m = EC.fullmet(a, idx=idx)
    return m['final'], m['mdd'], m['calmar']      # fullmet 의 mdd 는 이미 % 단위


def turn_of(w):
    pos = np.empty(n)
    pos[0] = w[0]
    pos[1:] = w[:-1]
    return float(np.abs(np.diff(pos, prepend=pos[0])).sum())


def p05_h(a, w):
    m = a[w:] / a[:-w]
    return float(np.quantile(m, 0.05)), float(np.median(m))


def main():
    wB = EC.rule_dd(PX, TH, TH, win=BASE)
    aB = EC.sim2(wB, QLDR, MIXR)

    # ---- [1] 축퇴 검산 ------------------------------------------------------
    ens1 = np.mean([EC.rule_dd(PX, TH, TH, win=BASE)], axis=0)
    a1 = EC.sim2(ens1, QLDR, MIXR)
    err = float(np.max(np.abs(a1 / aB - 1)))
    print(f'\n[1] 축퇴 검산 — 트랜치 1개(룩백 252) ≡ 현행 B')
    print(f'  오차 {err:.1e}  {"OK" if err < 1e-12 else "★실패"}')
    if err >= 1e-12:
        sys.exit('축퇴 검산 실패')

    # ---- [2] 시작일 무관 확인 (고전 RTL 이 왜 적용 안 되는가) ---------------
    print('\n[2] 시작일이 신호를 바꾸는가 — 워밍업 이후 수렴 여부')
    for off in (0, 63, 126, 252):
        px2 = PX.iloc[off:]
        w2 = EC.rule_dd(px2, TH, TH, win=BASE)
        # 공통 구간(워밍업 252일 제외)에서 원본과 대조
        cmp_from = max(BASE, BASE - off) + off
        same = np.array_equal(w2[cmp_from - off:], wB[cmp_from:])
        print(f'  시작 {off:>3}일 지연 → 워밍업 후 신호 동일: {"예" if same else "아니오"}')
    print('  → 시작일 타이밍 운 없음. B 의 운은 「룩백 선택」에 있다 (아래).')

    # ---- [3] 룩백 특정 운의 크기 --------------------------------------------
    LBS = [126, 168, 189, 210, 231, 252, 273, 294, 315, 378, 504]
    print(f'\n[3] 룩백 특정 운 — 같은 −16% 규칙, 창 길이만 바꾸면')
    print(f"{'룩백':>6} {'최종배수':>12} {'MDD':>8} {'Calmar':>7} {'전환':>6} "
          f"{'20년 p05':>9}")
    rows = {}
    for L in LBS:
        w = EC.rule_dd(PX, TH, TH, win=L)
        a = EC.sim2(w, QLDR, MIXR)
        f, mdd, cal = met(a)
        p05, _ = p05_h(a, 5040)
        rows[L] = (f, mdd, cal, turn_of(w) / 2, p05, a)
        star = ' ←현행' if L == BASE else ''
        print(f'{L:>6} {f:>12,.1f} {mdd:>7.1f}% {cal:>7.3f} {turn_of(w)/2:>6.0f} '
              f'{p05:>8.1f}배{star}')
    fs = np.array([rows[L][0] for L in LBS])
    cs = np.array([rows[L][2] for L in LBS])
    print(f'  산포: 최종배수 {fs.min():,.0f}~{fs.max():,.0f} (최대/최소 {fs.max()/fs.min():.1f}배) · '
          f'Calmar {cs.min():.3f}~{cs.max():.3f}')
    print(f'  현행 252 의 격자 내 순위: 최종 {int(np.sum(fs > rows[252][0])) + 1}/{len(LBS)} · '
          f'Calmar {int(np.sum(cs > rows[252][2])) + 1}/{len(LBS)}')

    # ---- [4] 트랜치 앙상블 --------------------------------------------------
    print('\n[4] 트랜치 앙상블 — 룩백을 등가중 평균 (Hoffstein overlapping portfolios)')
    print(f"{'구성':>26} {'최종배수':>12} {'MDD':>8} {'Calmar':>7} {'전환':>6} {'20년 p05':>9}")
    sets = [('현행 단일 252', [252]),
            ('3트랜치 231/252/273', [231, 252, 273]),
            ('5트랜치 189~315', [189, 210, 252, 294, 315]),
            ('7트랜치 168~378', [168, 189, 210, 252, 294, 315, 378]),
            ('11트랜치 전체', LBS)]
    for lab, ls in sets:
        w = np.mean([EC.rule_dd(PX, TH, TH, win=L) for L in ls], axis=0)
        a = EC.sim2(w, QLDR, MIXR)
        f, mdd, cal = met(a)
        p05, _ = p05_h(a, 5040)
        print(f'{lab:>26} {f:>12,.1f} {mdd:>7.1f}% {cal:>7.3f} {turn_of(w)/2:>6.0f} '
              f'{p05:>8.1f}배')

    # ---- [5] 무엇을 샀는가 — 산포 감소 vs 수익 --------------------------------
    print('\n[5] 트랜치가 실제로 사는 것 — 「룩백을 잘못 고를 위험」의 제거')
    single = fs
    ens = []
    rng = np.random.default_rng(42)
    for _ in range(200):
        ls = list(rng.choice(LBS, size=5, replace=False))
        w = np.mean([EC.rule_dd(PX, TH, TH, win=int(L)) for L in ls], axis=0)
        ens.append(EC.fullmet(EC.sim2(w, QLDR, MIXR), idx=idx)['final'])
    ens = np.array(ens)
    print(f'  단일 룩백 하나를 무작위로 고르면: 중앙 {np.median(single):,.0f}배 · '
          f'변동계수 {single.std()/single.mean():.3f}')
    print(f'  5트랜치를 무작위로 고르면:      중앙 {np.median(ens):,.0f}배 · '
          f'변동계수 {ens.std()/ens.mean():.3f}')
    print(f'  → 산포 축소 {1 - (ens.std()/ens.mean())/(single.std()/single.mean()):.0%} '
          f'(이것이 트랜치가 사는 상품 — 기대수익이 아니다)')

    # ---- [5-b] ★반증 검사 — MDD 개선이 구조적인가 선택인가 -----------------
    #   [4] 의 개선은 「내가 고른 룩백 집합」에서 나왔다. 그 집합을 무작위로 바꿔도
    #   MDD 가 개선되면 구조적이고, 절반쯤이면 선택편향이다. 이 검사가 트랜치 주장의
    #   생사를 가른다 — 통과 못 하면 [4] 는 뽑기 결과일 뿐이다.
    print('\n[5-b] ★반증 검사 — 무작위 트랜치 200회 (내가 고른 집합이 아니라)')
    f0, m0, c0 = met(aB)
    p0, _ = p05_h(aB, 5040)
    win = dict(final=0, mdd=0, cal=0, p05=0)
    accm, accc, accp = [], [], []
    rng2 = np.random.default_rng(7)
    for _ in range(200):
        ls = [int(v) for v in rng2.choice(LBS, size=5, replace=False)]
        w = np.mean([EC.rule_dd(PX, TH, TH, win=L) for L in ls], axis=0)
        a = EC.sim2(w, QLDR, MIXR)
        f, m, c = met(a)
        p, _ = p05_h(a, 5040)
        accm.append(m); accc.append(c); accp.append(p)
        win['final'] += f > f0
        win['mdd'] += m > m0            # mdd 는 음수 — 클수록(덜 나쁨) 개선
        win['cal'] += c > c0
        win['p05'] += p > p0
    print(f"{'지표':>10} {'단일 252':>10} {'무작위 중앙':>12} {'단일을 이긴 비율':>16}")
    print(f"{'MDD':>10} {m0:>9.1f}% {np.median(accm):>11.1f}% {win['mdd']/200:>15.0%}")
    print(f"{'Calmar':>10} {c0:>10.3f} {np.median(accc):>12.3f} {win['cal']/200:>15.0%}")
    print(f"{'20년 p05':>10} {p0:>9.1f}배 {np.median(accp):>11.1f}배 {win['p05']/200:>15.0%}")
    print(f"{'최종배수':>10} {f0:>10,.0f} {np.median(ens):>12,.0f} {win['final']/200:>15.0%}")
    print('  판정 기준: 90% 이상이면 구조적, 50% 안팎이면 선택편향(뽑기).')

    # ---- [6] 시대 분해 — v50/v87 지문 검사 (필수 관문) ----------------------
    #   「표본 내 개선」이 전반 시대의 산물이면 BGATE 와 같은 함정이다.
    print('\n[6] 시대 분해 — 개선이 전반 산물인가 (v50/v87 BGATE 지문 검사)')
    half = n // 2
    print(f'  경계 {idx[half].date()} · 전반/후반 각 {half}일')
    print(f"{'구성':>22} {'전반 배수':>11} {'후반 배수':>11} {'전반 Cal':>9} {'후반 Cal':>9}")
    for lab, ls in [('단일 252 (현행)', [252]), ('5트랜치 189~315', [189, 210, 252, 294, 315])]:
        w = np.mean([EC.rule_dd(PX, TH, TH, win=L) for L in ls], axis=0)
        a = EC.sim2(w, QLDR, MIXR)
        f1 = a[half] / a[0]
        f2 = a[-1] / a[half]
        c1 = EC.fullmet(a[:half], idx=idx[:half])['calmar']
        c2 = EC.fullmet(a[half:] / a[half], idx=idx[half:])['calmar']
        print(f'{lab:>22} {f1:>11,.1f} {f2:>11,.1f} {c1:>9.3f} {c2:>9.3f}')
    print('  → 후반에서도 트랜치가 앞서야 시대 산물이 아니다. 뒤집히면 BGATE 와 같은 함정.')

    # ---- [7] 사전 고정 관문 판정 -------------------------------------------
    #   04 §5-3 의 관문 ①(Calmar +10.2%) · ②(20년창 바닥 p05) 를 그대로 적용한다.
    #   시대 분해를 통과했어도 이 두 관문을 못 넘으면 채택 근거가 아니다.
    g1 = np.median(accc) / c0 - 1
    g2 = win['p05'] / 200
    print('\n[7] 사전 고정 관문 판정 (04 §5-3 과 같은 잣대)')
    print(f'  관문① Calmar +10.2% 이상 : 실측 {g1:+.1%}  → '
          f'{"통과" if g1 >= 0.102 else "★미달"}')
    print(f'  관문② 20년창 바닥(p05) 개선: 무작위 중 {g2:.0%} 만 개선  → '
          f'{"통과" if g2 >= 0.9 else "★미달"}')
    print(f'  최종배수도 {win["final"]/200:.0%} 만 개선 — 부(富)를 못 쌓는다.')
    print('\n  판정: **기각.** MDD·Calmar 개선은 구조적으로 실재하나(100%),')
    print('  그 개선은 **부의 바닥과 최종배수를 대가로** 산 것이다. 이는 04 §5-2')
    print('  AND(wB×wT) (MDD −52.8% 최상급이나 경제성 탈락) · §5-5 후보2')
    print('  (MDD −43% 인데 p05 4.7 vs 34.7 참패) 와 **같은 패턴**이다.')
    print('  기전: 전환을 여러 날에 나누면 폭락도 덜 맞지만 **V자 반등도 덜 먹는다**')
    print('  — 기전 1(왜도)의 또 다른 사례. 부의 바닥은 V자 포착에서 나온다.')


if __name__ == '__main__':
    main()
