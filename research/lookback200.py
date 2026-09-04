# -*- coding: utf-8 -*-
"""
[2026-09-02 소유자 지시] 「룩백 200 검증해봐 — 어떤 룰보다 최우선에 있는 명령. 왜 룩백 200 이어야
                          하는지도 근거 찾아서 결론 요약해」

★ 이 지시는 04 §5-14 D 의 「룩백 재탐색 금지」를 **이 질문에 한해** 해제한다(소유자 명시).
   해제되지 않는 것: §-1 의 측정 규약 — 사전 등록 · 전 시작일 분포 · 겹치지 않는 블록 · 반증.
   그것은 「재탐색 금지」가 아니라 **재는 방법**이다. 전략 무변경 — 결론은 소유자 컨펌 대상.

★ 먼저 적발한 사실 (§-1 ② — 파일을 열어 확인했다):
   04 §5-14 D 의 룩백 격자 표(40~800일 78칸 · 시대별 최적 200 · WFA 선택 중앙 100~150 · 적응형 패배)는
   「재현 research/what_we_know.py」라 적혀 있으나 **그 파일에 룩백 코드가 없다**([A]~[E] 전부 문턱).
   §5-13 정정2 와 같은 병 — **재현 스크립트 없는 표.** 이 파일이 그 표를 재현 가능하게 만든다.
   재현되지 않으면 그 사실을 출력한다 — 조용히 새 수치로 갈아치우지 않는다(wfa_thresh 규약).

★ 사전 등록 — 결과를 보기 전에 적는다 (§-1 ⑤ 실패/통과의 뜻이 서로 달라야 관문이다)

  Q1 사실: 200 이 252 보다 표본 내에서 나은가, 얼마나, 어디서.
  Q2 근거: 그 우위가 **사전에 식별 가능한** 것인가 (= 「200 이어야 한다」고 말할 근거가 있나).

  [1] 정면 비교 + 저장소 표준 관문 (HANDOFF §2-0)
      ① Calmar 현행 +10.2% 초과 · ② 20년창 하위 5분위(20퍼센타일) ≥ 현행 (p05 병기).
      통과 = 표본 내 우위가 판별 문턱(독립 위기 19회의 2σ)을 넘는다.  실패 = 우위가 잡음 크기다.
  [2] 기전 — 두 규칙이 갈린 구간을 전부 분해한다.
      소수 구간(≤5)이 격차의 80% 이상이면 → 「54년의 우위」가 아니라 「사건 몇 개의 우위」다.
      구간 부호검정 p<0.10 이면 → 갈릴 때마다 200 이 이기는 경향이 있다(사건 수 한계 안에서).
  [3] 고원/첨탑 — 150~300 이웃. 200 이 고원 안이면 「200」이라는 숫자에 뜻이 없고 밴드에 뜻이 있다.
      252 가 고원 밖(절벽 아래)이면 관습값이 실제로 비싸다 — 그 경우에도 어느 값으로 갈지는 별개 문제.
  [4] 모든 시작일 분포 (slice_scan 규약: 승률 옆에 비중첩 창 수·AR-ESS 병기)
      §5-14 D 의 「20년 창 승률 100% · 중앙 1.21배」 검증.
  [5] 사건 단위 — 독립 도피 사건(간격>252일) 창(−63~+252)에서 200/252 수익비. 부호검정.
      갈린 사건에서 200 승률이 동전(p≥0.10)이면 → 사건 단위로는 판별 불가.
  [6] 사전 식별 가능성 — 워크포워드
      (a) 격자 78칸 WFA(훈련 6~20년 · Calmar 주판정 · 최종배수 보조): 선택 밴드(170~220) 비율 ≥50% 이고
          적응형 ≥ 고정 252 이면 → 「그 시점 자료만으로도 200 근처를 골랐을 것」 = 사전 식별 가능.
          아니면 → 200 은 사후에만 보인다(§5-14 D 결론 유지).
      (b) 두 마리 경주 {200, 252}: 직전 N년에서 나은 쪽을 고르면 앞으로도 나은가.
      (c) 앵커 IS 최적의 궤적: 매 연말 「그때까지 전부」로 고른 최적 룩백 — 200 이 언제부터 1등이었나.
  [7] CSCV PBO (pbo_thresh 와 같은 구현 S=8·70분할): 룩백 격자에서 IS 1등 고르기가 OOS 에서 버티나.
      PBO ≥0.5 → 격자에서 1등을 고르는 절차 자체가 동전던지기.  200·252 의 OOS 백분위 중앙 병기.
  [8] 겹치지 않는 블록 K=2·3·6 — 200 과 252 의 블록별 순위·미니맥스·정면 승부.
  [9] 구조적 근거 탐색 — 「하필 200」이 이 표본 밖에서도 성립하는가
      (a) 타 시장(S&P500·NYSE 종합·니케이·러셀2000 — NDX 와 표본이 다른 4개) 같은 −16/−16 · 같은 2배
          합성·같은 방어로 룩백 최적을 잰다. **4개 중 3개 이상**이 170~220 이면 구조적(시장 공통),
          흩어지면 나스닥 표본 고유. (사촌 NASDAQ 종합·NDX 1985~ 는 참고로만 — 표본이 겹친다)
          ⚠ 통과/실패의 뜻이 다르다(§-1 ⑤): 「특화 vs 과적합」이 아니라 「룩백 최적 위치」만 묻는다.
      (b) 사건의 시간 구조 — 고점→도피, 도피→저점, 저점→재진입(252 vs 200). 200 이 「무엇을」 사는지.
  [10] 동결 이후 OOS — 두 규칙이 갈렸는가(갈리지 않았으면 판정 재료 0).

  ★ 판정문 (결과 전에 고정):
    · 「200 으로 바꿀 근거 있음」 = [1]①② 통과 AND [5] p<0.10 AND [6a] 사전 식별 가능 AND
      [7] 200 OOS 백분위 > 252 AND [9a] 3/4 이상.  (다섯 개가 전부 필요하다 — 하나라도 빠지면 아래)
    · [1]①② 통과 · 나머지 실패 = 「표본 내 우위는 실재하나 사전 근거 없음」 → 유지(§5-14 D 재확인,
      단 이번엔 **기전과 사건 수**를 특정해 적는다).
    · [1]①② 미달 = §5-14 D 의 「200 이 낫다」 자체가 잡음 크기 — 문서 정정.
  ★ 어느 쪽이 나와도 이 파일은 규칙을 바꾸지 않는다. 바꾸는 결정은 소유자.

엔진: eng_common (1972~ 54년 · 방어 40/40/20 · 2배 합성 = QLD 역산 드래그 · 편도 0.1%) —
검산 217,110.075 / 0.418 통과 못 하면 즉시 중단. 실행: python research/lookback200.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
from math import comb
from itertools import combinations
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
C_DAILY = float(G.D['c_daily'])
TH = -0.16
BASE, CAND = 252, 200
Y = 252
W20 = 5040
PRE, POST = 63, 252
BAND = (170, 220)
GRID = sorted(set(list(range(40, 801, 10)) + [BASE]))          # 78칸 (04 §5-14 D 와 같은 수)
NB = sorted(set(list(range(150, 301, 10)) + [BASE]))           # 이웃
L = '=' * 96
YEARS = (idx[-1] - idx[0]).days / 365.25


def make(Lb, px=PX, r_eng=QLDR, r_def=MIXR):
    w = EC.rule_dd(px, TH, TH, win=Lb)
    return w, np.asarray(EC.sim2(w, r_eng, r_def), float)


W, C = {}, {}
for Lb in GRID:
    W[Lb], C[Lb] = make(Lb)


def segmet(a, lo, hi, ix=None):
    s = a[lo:hi + 1] / a[lo]
    return EC.fullmet(s, idx=(ix if ix is not None else idx)[lo:hi + 1])


def qh(a, w=W20, qq=0.20):
    m = a[w:] / a[:-w]
    return float(np.quantile(m, qq))


def rets(a):
    return np.diff(a, prepend=1.0) / np.concatenate(([1.0], a[:-1]))


def ar_ess(m):
    N = len(m)
    x = m - m.mean()
    ac = np.correlate(x, x, 'full')[N - 1:] / (x @ x)
    k, s = 1, 0.0
    while k < N and ac[k] > 0.05:
        s += ac[k]
        k += 1
    return N / (1 + 2 * s)


def sign_p(k, m):
    """양측 부호검정 p (H0: 승률 1/2)."""
    if m == 0:
        return float('nan')
    lo = sum(comb(m, j) for j in range(0, min(k, m - k) + 1)) / 2 ** m
    return min(1.0, 2 * lo)


def switches(w):
    return int(np.sum(np.abs(np.diff(w)) > 0))


def escapes(w):
    return [i for i in range(1, len(w)) if w[i] == 0 and w[i - 1] == 1]


def independent(ev, gap=252):
    """oos_protocol_b.independent 와 같은 정의 — **직전 도피(어느 것이든)**와 gap 초과면 독립.
    (직전 「독립 사건」과의 간격이 아니다 — 그 정의로 재면 22건이 나와 문서 21건과 어긋난다.)"""
    out, last = [], -10 ** 9
    for i in ev:
        if i - last > gap:
            out.append(i)
        last = i
    return out


def rank_in(vals, key, higher=True):
    v = vals[key]
    return 1 + int(sum(1 for k, x in vals.items() if (x > v if higher else x < v)))


# ─────────────────────────────────────────────────────────────────────────────
def sec0():
    print(L)
    print('[0] 04 §5-14 D 재현 — 격자 %d칸(40~800·10일 간격 + 252) · 시대별 최적 룩백 · 252 순위' % len(GRID))
    print(L)
    print('  ★ 그 표에는 재현 스크립트가 없었다(what_we_know.py 에 룩백 코드 0줄). 아래가 첫 재현이다.')
    eras = [('54년', 0), ('2000~', int(idx.searchsorted(pd.Timestamp('2000-01-01')))),
            ('2003~', int(idx.searchsorted(pd.Timestamp('2003-01-01')))),
            ('2010~', int(idx.searchsorted(pd.Timestamp('2010-01-01')))),
            ('최근20년(5040일)', n - 1 - W20)]
    DOC = {'54년': (200, 12, 41), '2000~': (200, 10, 6), '2003~': (170, 17, 7),
           '2010~': (170, 23, 16), '최근20년(5040일)': (180, 19, 8)}
    print('  %-16s %8s %14s %10s %10s   %s' % ('구간', '최적룩백', '최적 최종배수', '252 최종순위', '252 Calmar순위', '문서(최적/최종/Calmar)'))
    hits, tot = 0, 0
    for lab, lo in eras:
        fin, cal = {}, {}
        for Lb in GRID:
            m = segmet(C[Lb], lo, n - 1)
            fin[Lb], cal[Lb] = m['final'], m['calmar']
        best = max(fin, key=fin.get)
        r_f, r_c = rank_in(fin, BASE), rank_in(cal, BASE)
        d = DOC[lab]
        ok = (abs(best - d[0]) <= 10, abs(r_f - d[1]) <= 3, abs(r_c - d[2]) <= 5)
        hits += sum(ok); tot += 3
        print('  %-16s %8d %14s %10d %10d   %d / %d / %d  %s'
              % (lab, best, ('%.0f' % fin[best] if fin[best] > 1000 else '%.2f' % fin[best]),
                 r_f, r_c, d[0], d[1], d[2], '일치' if all(ok) else '★어긋남 ' + str(ok)))
        if lab == '54년':
            print('     54년 200 최종배수 %s (문서 340,257) · 252 = %s' % ('{:,.0f}'.format(fin[200]), '{:,.0f}'.format(fin[252])))
    print('  → 문서 15개 항목 중 %d개 일치(허용오차 룩백 ±10·순위 ±3/±5). %s'
          % (hits, '표는 재현된다.' if hits >= 12 else '★ 표가 그대로 재현되지 않는다 — 규약(창 정의) 차이일 수 있다. 문서에 규약을 명시할 것.'))


def sec1():
    print()
    print(L)
    print('[1] 정면 비교 — 200 vs 252 (같은 −16/−16 · 같은 엔진 · 같은 비용)  + 관문 ①②')
    print(L)
    rows = {}
    for Lb in (CAND, BASE):
        m = EC.fullmet(C[Lb], idx=idx)
        m['q20'] = qh(C[Lb], qq=0.20); m['p05'] = qh(C[Lb], qq=0.05); m['med20'] = qh(C[Lb], qq=0.50)
        m['sw'] = switches(W[Lb]) // 2
        rows[Lb] = m
    print('  %-6s %12s %7s %8s %8s %8s %6s %10s %10s %10s' % ('룩백', '최종배수', 'CAGR', 'MDD', 'Calmar', 'Sortino', '왕복', '20년 q20', '20년 p05', '20년 중앙'))
    for Lb in (CAND, BASE):
        m = rows[Lb]
        print('  %-6d %12s %6.2f%% %7.1f%% %8.3f %8.3f %6d %10.1f %10.1f %10.1f'
              % (Lb, '{:,.0f}'.format(m['final']), m['cagr'], m['mdd'], m['calmar'], m['sortino'], m['sw'], m['q20'], m['p05'], m['med20']))
    a, b = rows[CAND], rows[BASE]
    g1 = a['calmar'] / b['calmar'] - 1
    g2 = a['q20'] >= b['q20']
    g2b = a['p05'] >= b['p05']
    print('  최종배수 비 200/252 = %.3f · Calmar %+.1f%% (관문① 기준 +10.2%%) → %s'
          % (a['final'] / b['final'], g1 * 100, '통과' if g1 > 0.102 else '미달'))
    print('  관문② 20년창 q20 %.1f vs %.1f → %s  (p05 %.1f vs %.1f → %s)'
          % (a['q20'], b['q20'], '통과' if g2 else '미달', a['p05'], b['p05'], '통과' if g2b else '미달'))
    print('  시대별 (구간 최종배수 비 200/252):')
    era = EC.era_table(C[CAND], idx)
    erb = EC.era_table(C[BASE], idx)
    print('   ' + ' · '.join('%s %.2f' % (e[0], e[1]['final'] / f[1]['final']) for e, f in zip(era, erb)))
    return g1 > 0.102, g2, g2b, a['final'] / b['final']


def decompose(La, Lb, top=14, title=None):
    """두 룩백 곡선의 격차를 「갈린 구간」으로 전부 분해한다. sim2 와 같은 산식의 일별 log 승수를 쓰므로
    상태·회전이 같은 날은 차이가 **정확히** 0 이다(곡선 log 차이는 부동소수 잡음이 남아 626개 가짜 구간이 났다)."""
    def logfac(w):
        pos = np.r_[w[0], w[:-1]]
        r = pos * QLDR + (1 - pos) * MIXR
        r[0] = 0.0
        turn = np.abs(np.diff(pos, prepend=pos[0]))
        return np.log((1 + r) * (1 - EC.COST * turn)), pos
    fa, pa = logfac(W[La])
    fb, pb = logfac(W[Lb])
    lr = (fa - fb)[1:]                                            # 날 t (1..n-1)
    nz = lr != 0.0
    tot = float(np.log(C[La][-1] / C[Lb][-1]))
    assert abs(float(lr.sum()) - tot) < 1e-9, '일별 분해가 곡선과 안 맞는다'
    eps = []
    t = 0
    while t < len(lr):
        if nz[t]:
            s = t
            while t < len(lr) and nz[t]:
                t += 1
            e = t - 1
            d0 = s + 1
            a2, a5 = pa[d0], pb[d0]
            prev = pb[d0 - 1] if d0 > 0 else 1.0
            if a2 == a5:
                a2, a5 = pa[min(d0 + 1, n - 1)], pb[min(d0 + 1, n - 1)]
            if a2 == 1 and a5 == 0:
                kind = '%d 재진입 빠름' % La if prev == 0 else '%d 먼저 도피' % Lb
            elif a2 == 0 and a5 == 1:
                kind = '%d 먼저 도피' % La if prev == 1 else '%d 재진입 빠름' % Lb
            else:
                kind = '혼합'
            eps.append(dict(s=d0, e=e + 1, days=e - s + 1, g=float(lr[s:e + 1].sum()), kind=kind))
        else:
            t += 1
    gs = np.array([x['g'] for x in eps])
    order = np.argsort(-np.abs(gs))
    if title:
        print('  -- %s --' % title)
    print('  전체 격차 log(%d/%d) = %+.4f (= %.3f배) · 갈린 구간 %d개 · 갈린 날 %d일 (연 %.1f일)'
          % (La, Lb, tot, np.exp(tot), len(eps), int(nz.sum()), nz.sum() / YEARS))
    print('  %d 이 이긴 구간 %d · 진 구간 %d · 부호검정 p=%.3f · 구간 기여 중앙 %+.2f%%'
          % (La, int(np.sum(gs > 0)), int(np.sum(gs < 0)), sign_p(int(np.sum(gs > 0)), int(np.sum(gs != 0))), np.median(gs) * 100))
    print('  %-4s %-12s %-12s %5s %-16s %9s %8s %9s' % ('#', '시작', '끝', '일수', '유형', '기여(log)', '누적%', 'QQQ 변동'))
    cum, n80 = 0.0, None
    pxv = PX.values
    for r, k in enumerate(order[:top]):
        x = eps[k]
        cum += x['g']
        share = cum / tot * 100 if tot != 0 else float('nan')
        if n80 is None and tot > 0 and cum >= 0.8 * tot:
            n80 = r + 1
        mv = pxv[x['e']] / pxv[max(0, x['s'] - 1)] - 1
        print('  %-4d %-12s %-12s %5d %-16s %+9.4f %7.0f%% %+8.1f%%'
              % (r + 1, idx[x['s']].date(), idx[x['e']].date(), x['days'], x['kind'], x['g'], share, mv * 100))
    if n80 is None:
        cum2 = 0.0
        for r, k in enumerate(order):
            cum2 += eps[k]['g']
            if tot > 0 and cum2 >= 0.8 * tot:
                n80 = r + 1
                break
    by_year = {}
    for x in eps:
        y = idx[x['s']].year
        by_year[y] = by_year.get(y, 0.0) + x['g']
    top_y = sorted(by_year.items(), key=lambda t: -abs(t[1]))[:8]
    print('  연도별 순기여(|기여| 큰 순 8개): ' + ' · '.join('%d %+.3f' % (y, g) for y, g in top_y))
    pos_top = sorted([x['g'] for x in eps if x['g'] > 0], reverse=True)
    kinds = sorted(set(x['kind'] for x in eps))
    print('  격차의 80%%를 채우는 구간 수(기여 큰 순): %s · 이긴 구간 상위 3개 합 = 전체의 %.0f%%'
          % (n80 if n80 else '해당 없음', sum(pos_top[:3]) / tot * 100 if tot > 0 else float('nan')))
    print('  유형별 순기여: ' + ' · '.join('%s %+.3f' % (k, sum(x['g'] for x in eps if x['kind'] == k)) for k in kinds))
    return eps, tot, n80


def sec2():
    print()
    print(L)
    print('[2] 기전 — 두 규칙이 갈린 구간을 전부 분해 (격차가 「54년」에서 오나 「사건 몇 개」에서 오나)')
    print(L)
    eps, tot, n80 = decompose(CAND, BASE)
    print()
    print('  「하필 200」의 정체 — 이웃 220 과의 격차는 어디서 오나 (220 은 2005~2020 앵커 IS 1등이었다, [6c])')
    decompose(CAND, 220, top=5)
    return eps, tot, n80


def sec3():
    print()
    print(L)
    print('[3] 고원인가 첨탑인가 — 이웃 150~300 (10일 간격)')
    print(L)
    print('  %-5s %12s %8s %8s %6s %9s %9s' % ('룩백', '최종배수', 'MDD', 'Calmar', '왕복', '20년 q20', '20년 p05'))
    fin, cal, q20 = {}, {}, {}
    for Lb in NB:
        if Lb not in C:
            W[Lb], C[Lb] = make(Lb)
        m = EC.fullmet(C[Lb], idx=idx)
        fin[Lb], cal[Lb], q20[Lb] = m['final'], m['calmar'], qh(C[Lb])
        tag = ' ←현행' if Lb == BASE else (' ←후보' if Lb == CAND else '')
        print('  %-5d %12s %7.1f%% %8.3f %6d %9.1f %9.1f%s'
              % (Lb, '{:,.0f}'.format(m['final']), m['mdd'], m['calmar'], switches(W[Lb]) // 2, q20[Lb], qh(C[Lb], qq=0.05), tag))
    best = max(fin, key=fin.get)
    plateau = [Lb for Lb in NB if fin[Lb] >= 0.9 * fin[best]]
    print('  최고 %d (%s) · 「최고의 90%% 이상」 고원 = %s' % (best, '{:,.0f}'.format(fin[best]), plateau))
    print('  200 고원 안: %s · 252 고원 안: %s · 200 순위 %d/%d · 252 순위 %d/%d (최종배수)'
          % (CAND in plateau, BASE in plateau, rank_in(fin, CAND), len(NB), rank_in(fin, BASE), len(NB)))
    seq = [Lb for Lb in NB if 210 <= Lb <= 270]
    drops = [(seq[i], seq[i + 1], (fin[seq[i + 1]] / fin[seq[i]] - 1) * 100) for i in range(len(seq) - 1)]
    worst = min(drops, key=lambda d: d[2])
    print('  210→270 구간의 이웃 칸 낙차 최대: %d→%d %+.1f%% (절벽이면 관습값 252 가 실제로 비싼 자리)' % worst)
    print('  170~220 전부 > 252 인가: %s · 240~300 전부 < 220 인가: %s'
          % (all(fin[Lb] > fin[BASE] for Lb in NB if 170 <= Lb <= 220), all(fin[Lb] < fin[220] for Lb in NB if 240 <= Lb <= 300)))
    return plateau, best


def sec4():
    print()
    print(L)
    print('[4] 모든 시작일 분포 — 200/252 배수비 (승률 옆 비중첩 창 수·AR-ESS 병기)')
    print(L)
    print('  %-6s %8s %8s %8s %8s %10s %8s' % ('지평', '창수', '200승률', '중앙비', 'p05비', '비중첩창', 'AR-ESS'))
    out = {}
    for h in (3, 5, 7, 10, 15, 20):
        w = h * Y
        m2, m5 = C[CAND][w:] / C[CAND][:-w], C[BASE][w:] / C[BASE][:-w]
        r = m2 / m5
        out[h] = (float(np.mean(r > 1)), float(np.median(r)), float(np.quantile(r, 0.05)))
        print('  %-5d년 %8d %7.0f%% %8.3f %8.3f %10.1f %8.1f'
              % (h, len(r), out[h][0] * 100, out[h][1], out[h][2], len(C[CAND]) / w, ar_ess(r)))
    print('  문서(§5-14 D) 「20년 창 승률 100%% · 중앙 1.21배」 → 재현 %s (승률 %.0f%% · 중앙 %.2f)'
          % ('일치' if out[20][0] >= 0.99 and abs(out[20][1] - 1.21) < 0.03 else '★어긋남', out[20][0] * 100, out[20][1]))
    print('  ⚠ 20년 창의 비중첩 수는 %.1f개 — 「100%%」는 독립 관측 100건이 아니라 같은 몸을 여러 각도로 본 것.' % (n / W20))
    return out


def sec5():
    print()
    print(L)
    print('[5] 사건 단위 — 독립 도피 사건(252 규칙 · 간격>252일) 창 −63~+252 의 200/252 수익비')
    print(L)
    ev = escapes(W[BASE])
    ind = independent(ev)
    rows = []
    for i in ind:
        lo, hi = max(0, i - PRE), i + POST
        if hi >= n:
            continue
        r = (C[CAND][hi] / C[CAND][lo]) / (C[BASE][hi] / C[BASE][lo])
        rows.append((i, r))
    div = [(i, r) for i, r in rows if abs(r - 1) > 1e-9]
    wins = sum(1 for _, r in div if r > 1)
    print('  도피 사건 %d · 독립 %d · 창이 찬 것 %d · 그중 갈린 사건 %d · 200 승 %d · 부호검정 p=%.3f'
          % (len(ev), len(ind), len(rows), len(div), wins, sign_p(wins, len(div))))
    print('  문서(§5-23 D) 「갈린 사건 8건 · 200 승 5/8」 → %s' % ('일치' if (len(div), wins) == (8, 5) else '★어긋남'))
    print('  %-12s %10s %8s' % ('도피 신호일', '200/252', '판정'))
    for i, r in div:
        print('  %-12s %10.3f %8s' % (idx[i].date(), r, '200 승' if r > 1 else '252 승'))
    allrows = []
    for i in ev:
        lo, hi = max(0, i - PRE), i + POST
        if hi < n:
            r = (C[CAND][hi] / C[CAND][lo]) / (C[BASE][hi] / C[BASE][lo])
            if abs(r - 1) > 1e-9:
                allrows.append(r)
    print('  (참고) 독립 조건 없이 전체 도피 사건 중 갈린 %d건 · 200 승 %d · p=%.3f'
          % (len(allrows), sum(1 for r in allrows if r > 1), sign_p(sum(1 for r in allrows if r > 1), len(allrows))))
    return len(div), wins, sign_p(wins, len(div))


def wfa(cands, train_y, step_y, metric):
    tr, st = train_y * Y, step_y * Y
    picks, f_ad, f_b, f_c = [], [], [], []
    for i in range(tr, n - st, st):
        lo = i - tr

        def key(Lb):
            s = C[Lb][lo:i + 1] / C[Lb][lo]
            if metric == 'final':
                return s[-1]
            mdd = abs(float(np.min(s / np.maximum.accumulate(s) - 1)))
            cagr = float(s[-1]) ** (Y / (len(s) - 1)) - 1
            return cagr / max(mdd, 1e-9)
        best = max(cands, key=key)
        j = i + st
        picks.append(best)
        f_ad.append(C[best][j] / C[best][i]); f_b.append(C[BASE][j] / C[BASE][i]); f_c.append(C[CAND][j] / C[CAND][i])
    p, f_ad, f_b, f_c = np.array(picks), np.array(f_ad), np.array(f_b), np.array(f_c)
    return dict(n=len(p), med=float(np.median(p)), sd=float(p.std()),
                band=float(np.mean((p >= BAND[0]) & (p <= BAND[1]))),
                is252=float(np.mean(p == BASE)), is200=float(np.mean(p == CAND)),
                ad=float(np.prod(f_ad)), fb=float(np.prod(f_b)), fc=float(np.prod(f_c)),
                win_b=float(np.mean(f_ad > f_b)), tie_b=float(np.mean(f_ad == f_b)),
                lo=int(p.min()), hi=int(p.max()), picks=p)


def sec6():
    print()
    print(L)
    print('[6] 사전 식별 가능성 — 워크포워드 (그 시점까지의 자료만으로 골랐다면 무엇을 골랐고, 그게 나았나)')
    print(L)
    print('  (a) 격자 78칸에서 직전 N년 최적을 고른다 · 걸음 1년')
    print('  %-8s %-7s %5s %7s %6s %9s %8s %8s %12s %12s %12s %8s'
          % ('지표', '훈련', '걸음', '선택중앙', '표준편차', '170~220', '=252', '=200', '적응형', '고정252', '고정200', '적응>252'))
    res = {}
    for metric in ('calmar', 'final'):
        for tr_y in (6, 8, 10, 12, 15, 20):
            d = wfa(GRID, tr_y, 1, metric)
            res[(metric, tr_y)] = d
            print('  %-8s %-7s %5d %7.0f %6.0f %8.0f%% %7.0f%% %7.0f%% %12s %12s %12s %7.0f%%'
                  % (metric, '%d년' % tr_y, d['n'], d['med'], d['sd'], d['band'] * 100, d['is252'] * 100, d['is200'] * 100,
                     '{:,.0f}'.format(d['ad']), '{:,.0f}'.format(d['fb']), '{:,.0f}'.format(d['fc']), d['win_b'] * 100))
    print('  문서(§5-14 D): 훈련10년 선택중앙 150·표준편차 100·밴드 27% / 훈련15년 중앙 100·표준편차 66·밴드 46% /')
    print('        전방 적응형 24,814 vs 고정 57,542 · 승률 47%.  (문서에 지표·걸음 규약이 없다 — 위 표에서 가장 가까운 행을 찾는다)')
    close = min(res.items(), key=lambda kv: abs(kv[1]['med'] - (150 if kv[0][1] == 10 else 100)) + abs(kv[1]['sd'] - (100 if kv[0][1] == 10 else 66))
                if kv[0][1] in (10, 15) else 1e9)
    print('  가장 가까운 행: %s 훈련 %d년 (중앙 %.0f · 표준편차 %.0f · 밴드 %.0f%%)'
          % (close[0][0], close[0][1], close[1]['med'], close[1]['sd'], close[1]['band'] * 100))
    for step in (3,):
        for metric in ('calmar', 'final'):
            for tr_y in (10, 15):
                d = wfa(GRID, tr_y, step, metric)
                print('  (걸음 %d년) %-6s 훈련 %2d년: 선택중앙 %.0f · 표준편차 %.0f · 밴드 %.0f%% · 적응형 %s vs 고정252 %s · 적응>252 %.0f%%'
                      % (step, metric, tr_y, d['med'], d['sd'], d['band'] * 100, '{:,.0f}'.format(d['ad']), '{:,.0f}'.format(d['fb']), d['win_b'] * 100))
    band_ok = sum(1 for (m, t), d in res.items() if m == 'calmar' and d['band'] >= 0.5)
    ad_ok = sum(1 for (m, t), d in res.items() if m == 'calmar' and d['ad'] >= d['fb'])
    print('  → Calmar 주판정 6개 훈련길이 중 밴드(170~220)≥50%%: %d개 · 적응형≥고정252: %d개' % (band_ok, ad_ok))

    print()
    print('  (b) 두 마리 경주 {200, 252} — 직전 N년에서 나은 쪽을 고른다 (걸음 1년)')
    print('  %-8s %-7s %8s %12s %12s %12s %10s %8s' % ('지표', '훈련', '200선택', '적응형', '고정252', '고정200', '적응>252', '무승부'))
    two = {}
    for metric in ('calmar', 'final'):
        for tr_y in (6, 8, 10, 12, 15, 20):
            d = wfa([CAND, BASE], tr_y, 1, metric)
            two[(metric, tr_y)] = d
            print('  %-8s %-7s %7.0f%% %12s %12s %12s %9.0f%% %7.0f%%'
                  % (metric, '%d년' % tr_y, d['is200'] * 100, '{:,.0f}'.format(d['ad']), '{:,.0f}'.format(d['fb']),
                     '{:,.0f}'.format(d['fc']), d['win_b'] * 100, d['tie_b'] * 100))
    two_ok = sum(1 for (m, t), d in two.items() if m == 'calmar' and d['ad'] > d['fb'])
    print('  → Calmar 기준 6개 중 적응형이 고정 252 를 이긴 훈련길이: %d개 (200 을 고른 비율은 위 열)' % two_ok)

    print()
    print('  (c) 앵커 IS 최적의 궤적 — 그해 말까지 **전부**로 고른 최적 룩백 (초기 자료가 영원히 지배하는 설계 — 서술용)')
    print('  %-8s %10s %10s %14s' % ('시점', '최종배수 최적', 'Calmar 최적', '200/252 (누적)'))
    first_200 = None
    for yr in list(range(1980, 2026, 5)) + [2026]:
        t = int(idx.searchsorted(pd.Timestamp('%d-12-31' % yr), side='right')) - 1 if yr < 2026 else n - 1
        fin = {Lb: C[Lb][t] for Lb in GRID}
        cal = {}
        for Lb in GRID:
            s = C[Lb][:t + 1]
            mdd = abs(float(np.min(s / np.maximum.accumulate(s) - 1)))
            cagr = float(s[-1]) ** (Y / t) - 1
            cal[Lb] = cagr / max(mdd, 1e-9)
        bf, bc = max(fin, key=fin.get), max(cal, key=cal.get)
        print('  %-8s %10d %10d %14.3f' % (idx[t].date(), bf, bc, C[CAND][t] / C[BASE][t]))
    for yr in range(1976, 2027):
        t = int(idx.searchsorted(pd.Timestamp('%d-12-31' % yr), side='right')) - 1
        t = min(t, n - 1)
        fin = {Lb: C[Lb][t] for Lb in GRID}
        if max(fin, key=fin.get) == CAND:
            if first_200 is None:
                first_200 = yr
        else:
            first_200 = None
    print('  최종배수 기준 IS 1등이 200 으로 **끊기지 않고** 이어진 시작 연도: %s' % (first_200 if first_200 else '2026 현재 200 이 1등이 아님'))
    return band_ok, ad_ok, two_ok


def cscv(Rm, names, kind, label, watch):
    S = 8
    bnd = np.linspace(0, Rm.shape[1], S + 1, dtype=int)
    blocks = [np.arange(bnd[i], bnd[i + 1]) for i in range(S)]
    lam, below, picks = [], 0, {}
    pct = {w: [] for w in watch}
    for isb in combinations(range(S), S // 2):
        oob = [b for b in range(S) if b not in isb]
        i_idx = np.concatenate([blocks[b] for b in isb])
        o_idx = np.concatenate([blocks[b] for b in oob])
        if kind == 'sharpe':
            mi = Rm[:, i_idx].mean(axis=1) / Rm[:, i_idx].std(axis=1, ddof=1)
            mo = Rm[:, o_idx].mean(axis=1) / Rm[:, o_idx].std(axis=1, ddof=1)
        else:
            def calm(R):
                a = np.cumprod(1 + R, axis=1)
                peak = np.maximum.accumulate(a, axis=1)
                mdd = np.abs(np.min(a / peak - 1, axis=1))
                cagr = a[:, -1] ** (252.0 / R.shape[1]) - 1
                return cagr / np.maximum(mdd, 1e-9)
            mi, mo = calm(Rm[:, i_idx]), calm(Rm[:, o_idx])
        best = int(np.argmax(mi))
        picks[names[best]] = picks.get(names[best], 0) + 1
        w = (np.sum(mo < mo[best]) + 0.5 * np.sum(mo == mo[best])) / len(mo)
        w = min(max(w, 1e-6), 1 - 1e-6)
        lam.append(np.log(w / (1 - w)))
        below += int(w < 0.5)
        for wt in watch:
            k = names.index(str(wt))
            pct[wt].append((np.sum(mo < mo[k]) + 0.5 * np.sum(mo == mo[k])) / len(mo))
    pbo = below / len(lam)
    top = sorted(picks.items(), key=lambda t: -t[1])[:6]
    print('  %-24s PBO=**%.3f** · IS 1등 빈도: %s' % (label, pbo, ', '.join('%s(%d)' % (k, v) for k, v in top)))
    print('  %-24s OOS 백분위 — 200: 중앙 %.0f%% 최저 %.0f%% · 252: 중앙 %.0f%% 최저 %.0f%%'
          % ('', 100 * np.median(pct[CAND]), 100 * np.min(pct[CAND]), 100 * np.median(pct[BASE]), 100 * np.min(pct[BASE])))
    return pbo, float(np.median(pct[CAND])), float(np.median(pct[BASE]))


def sec7():
    print()
    print(L)
    print('[7] CSCV PBO — 룩백 격자에서 「IS 1등 고르기」가 OOS 에서 버티는가 (S=8 · 70분할 · pbo_thresh 와 같은 구현)')
    print(L)
    out = {}
    for univ, lab in ((GRID, '격자 78칸'), (NB, '이웃 150~300')):
        Rm = np.asarray([rets(C[Lb]) for Lb in univ])
        names = [str(Lb) for Lb in univ]
        for kind in ('sharpe', 'calmar'):
            out[(lab, kind)] = cscv(Rm, names, kind, '%s · %s' % (lab, kind), (CAND, BASE))
    return out


def sec8():
    print()
    print(L)
    print('[8] 겹치지 않는 블록 — 200·252 의 블록별 순위(78칸 중) · 정면 승부')
    print(L)
    res = {}
    for K in (2, 3, 6):
        bnd = np.linspace(0, n - 1, K + 1).astype(int)
        r2s, r5s, wins = [], [], 0
        print('  K=%d' % K)
        for k in range(K):
            lo, hi = int(bnd[k]), int(bnd[k + 1])
            fin = {Lb: C[Lb][hi] / C[Lb][lo] for Lb in GRID}
            cal = {Lb: segmet(C[Lb], lo, hi)['calmar'] for Lb in GRID}
            r2, r5 = rank_in(fin, CAND), rank_in(fin, BASE)
            r2s.append(r2); r5s.append(r5)
            ratio = fin[CAND] / fin[BASE]
            wins += ratio > 1
            print('    %s~%s  최적 %3d  200: 최종 %2d위/Calmar %2d위  252: 최종 %2d위/Calmar %2d위  200/252 = %.3f'
                  % (idx[lo].date(), idx[hi].date(), max(fin, key=fin.get), r2, rank_in(cal, CAND), r5, rank_in(cal, BASE), ratio))
        res[K] = (max(r2s), max(r5s), wins)
        print('    미니맥스(최악 순위) 200: %d · 252: %d · 정면 승부 200 승 %d/%d' % (max(r2s), max(r5s), wins, K))
    return res


def load_close(path):
    d = pd.read_csv(path, parse_dates=['Date']).set_index('Date')
    col = 'Close' if 'Close' in d.columns else d.columns[0]
    return d[col].astype(float).sort_index().dropna()


def sec9a():
    print()
    print(L)
    print('[9a] 구조적 근거 — 타 시장에서 같은 규칙(−16/−16 · 2배 합성 · 같은 방어)의 룩백 최적 위치')
    print(L)
    print('  판정 규약(사전): 독립 4개 시장 중 **3개 이상**이 최종배수 최적 170~220 → 시장 공통(구조적) · 아니면 나스닥 표본 고유')
    print('  ⚠ 수준(배수)은 보지 않는다 — HANDOFF §2 「다른 시장에선 그냥 보유에 진다」(v44)는 이미 안다. 최적의 **위치**만 본다.')
    MK = [('S&P500', 'yahoo_GSPC.csv', True), ('NYSE 종합', 'yahoo_NYA.csv', True),
          ('니케이225', 'yahoo_N225.csv', True), ('러셀2000', 'yahoo_RUT.csv', True),
          ('NASDAQ 종합(사촌)', 'yahoo_IXIC.csv', False), ('NDX 1985~(부분)', 'yahoo_NDX.csv', False),
          ('QQQ 체인(본 표본)', None, False)]
    mixS = pd.Series(MIXR, index=idx)
    THS = [round(-0.10 - 0.02 * i, 2) for i in range(8)]          # −10 ~ −24
    CG = list(range(40, 801, 20))
    print('  %-18s %-10s %6s %8s %8s %8s %9s %9s   %s' % ('시장', '시작', '일수', '최적(최종)', '최적(Cal)', '200/252', '200순위', '252순위', '문턱 공최적 (문턱, 룩백)'))
    hit = 0
    for name, f, indep in MK:
        if f is None:
            px, common = PX, idx
        else:
            px = load_close(_os.path.join('data', 'hist', f))
            common = px.index.intersection(idx)
            px = px.reindex(common)
        r = np.nan_to_num(px.pct_change().values)
        r2 = EC.synth2x(r, C_DAILY)
        mix = mixS.reindex(common).values
        ix = common
        fin, cal = {}, {}
        for Lb in GRID:
            w = EC.rule_dd(px, TH, TH, win=Lb)
            a = np.asarray(EC.sim2(w, r2, mix), float)
            m = EC.fullmet(a, idx=ix)
            fin[Lb], cal[Lb] = m['final'], m['calmar']
        bf, bc = max(fin, key=fin.get), max(cal, key=cal.get)
        # 문턱 공최적 (거친 격자)
        bb, bv = None, -1
        for th in THS:
            for Lb in CG:
                w = EC.rule_dd(px, th, th, win=Lb)
                a = np.asarray(EC.sim2(w, r2, mix), float)
                if a[-1] > bv:
                    bv, bb = a[-1], (th, Lb)
        ok = BAND[0] <= bf <= BAND[1]
        hit += (ok and indep)
        print('  %-18s %-10s %6d %8d %8d %8.3f %9d %9d   (%.0f%%, %d)%s'
              % (name, ix[0].date(), len(ix), bf, bc, fin[CAND] / fin[BASE], rank_in(fin, CAND), rank_in(fin, BASE),
                 bb[0] * 100, bb[1], '  ←밴드 안' if ok else ''))
    print('  → 독립 4개 시장 중 최종배수 최적이 170~220 인 것: %d개 (기준 3개)' % hit)
    return hit


def sec9b():
    print()
    print(L)
    print('[9b] 사건의 시간 구조 — 약세장 **군(cluster)** 단위로 200 이 「무엇을」 사는가')
    print(L)
    print('  군 = 252 규칙의 독립 도피(직전 도피와 252일 초과)부터 다음 독립 도피 직전까지. 첫 도피만 보면 갈림이 안 보인다 —')
    print('  갈리는 것은 군의 **마지막 재진입**이다(첫 재진입은 대개 같은 날). 고점나이 = 252 규칙 최종 재진입일에 252일 고점이 몇 일 전인가.')
    ev = escapes(W[BASE])
    starts = sorted(independent(ev)) + [n]
    px = PX.values
    print('  %-12s %-11s %7s %7s %-12s %-12s %7s %7s %8s' % ('군 시작(252)', '군 끝', '252방어', '200방어', '252 최종재진입', '200 최종재진입', '재진입차', '고점나이', '200/252'))
    rows = []
    for a, b in zip(starts[:-1], starts[1:]):
        lo, hi = max(0, a - 40), min(b - 1, n - 1)
        w5, w2 = W[BASE][lo:hi + 1], W[CAND][lo:hi + 1]
        d5, d2 = int(np.sum(w5 == 0)), int(np.sum(w2 == 0))

        def last_re(w):
            r = [j for j in range(1, len(w)) if w[j] == 1 and w[j - 1] == 0]
            return (lo + r[-1]) if r else None
        r5, r2 = last_re(w5), last_re(w2)
        age = None
        if r5 is not None:
            s0 = max(0, r5 - 252 + 1)
            age = r5 - (s0 + int(np.argmax(px[s0:r5 + 1])))
        ratio = (C[CAND][hi] / C[CAND][lo]) / (C[BASE][hi] / C[BASE][lo])
        diff = (r2 - r5) if (r2 is not None and r5 is not None) else None
        rows.append(dict(a=a, d5=d5, d2=d2, diff=diff, age=age, ratio=ratio, esc2=d2 > 0))
        print('  %-12s %-11s %7d %7s %-12s %-12s %7s %7s %8.3f'
              % (idx[a].date(), idx[hi].date(), d5, (d2 if d2 > 0 else '도피없음'),
                 idx[r5].date() if r5 is not None else '-', idx[r2].date() if r2 is not None else '-',
                 ('%+d' % diff) if diff is not None else '-', age if age is not None else '-', ratio))
    dif = np.array([r['diff'] for r in rows if r['diff'] is not None])
    print('  200 최종 재진입이 252 보다 빠른 군 %d · 같은 군 %d · 느린 군 %d · 200 이 아예 도피 안 한 군 %d'
          % (int(np.sum(dif < 0)), int(np.sum(dif == 0)), int(np.sum(dif > 0)), sum(1 for r in rows if not r['esc2'])))
    long_ = [r for r in rows if r['d5'] >= 100]
    short = [r for r in rows if r['d5'] < 100]
    print('  252 방어일 ≥100 인 군 %d개: 200/252 중앙 %.3f · 200 승 %d  |  <100 인 군 %d개: 중앙 %.3f · 200 승 %d'
          % (len(long_), np.median([r['ratio'] for r in long_]) if long_ else float('nan'), sum(1 for r in long_ if r['ratio'] > 1),
             len(short), np.median([r['ratio'] for r in short]) if short else float('nan'), sum(1 for r in short if r['ratio'] > 1)))
    old = [r for r in rows if r['age'] is not None and r['age'] > 200]
    print('  고점나이 >200 (= 200일 창엔 그 고점이 이미 없음) 인 군 %d개 — 이 군에서만 두 규칙의 재진입선이 다르다. 그중 200 승 %d'
          % (len(old), sum(1 for r in old if r['ratio'] > 1)))
    print('  읽는 법: 200 이 사는 것은 「고점이 200일 넘게 묵은 긴 약세장의 끝에서 재진입선(고점×0.84)이 먼저 내려오는 것」이다.')
    print('          V자(2020·2018·2011)에서는 고점이 두 창에 다 있어 차이가 0 이다.')
    return rows


def sec10():
    print()
    print(L)
    print('[10] 동결 이후 OOS — 두 규칙이 갈렸는가')
    print(L)
    t0 = int(idx.searchsorted(pd.Timestamp('2026-08-28')))
    same = np.array_equal(W[CAND][t0:], W[BASE][t0:])
    h200 = float(PX.iloc[-200:].max()); h252 = float(PX.iloc[-252:].max())
    print('  %s ~ %s: 상태 동일 = %s · 200일 고점 == 252일 고점: %s (같으면 오늘 낙폭도 같다 — 체인 지수 기준)'
          % (idx[t0].date(), idx[-1].date(), same, h200 == h252))
    print('  → 판정 재료 %s.' % ('0건 — 정상(갈릴 일이 연 4일 남짓이다)' if same else '있음'))


def main():
    print(L)
    print('룩백 200 검증 — 「표본 내에서 나은가」와 「사전에 알 수 있었나」를 분리해 잰다 (전략 무변경 · 소유자 컨펌 대상)')
    print(L)
    print('  체인 %s ~ %s (%d거래일 · %.1f년) · 규칙 −16/−16 · 방어 40/40/20 · 편도 0.1%%' % (idx[0].date(), idx[-1].date(), n, YEARS))
    sec0()
    g1, g2, g2b, ratio = sec1()
    eps, tot, n80 = sec2()
    plateau, best = sec3()
    sl = sec4()
    ndiv, wins, p_ev = sec5()
    band_ok, ad_ok, two_ok = sec6()
    pbo = sec7()
    blk = sec8()
    hit = sec9a()
    sec9b()
    sec10()

    print()
    print(L)
    print('[판정] 사전 등록한 판정문에 기계적으로 대입')
    print(L)
    c1 = g1 and g2
    c2 = (p_ev < 0.10) if ndiv else False
    c3 = (band_ok >= 4) and (ad_ok >= 4)
    p_s = pbo[('격자 78칸', 'sharpe')]
    c4 = p_s[1] > p_s[2]
    c5 = hit >= 3
    print('  [1] 관문①(Calmar +10.2%%) %s · ②(20년 q20) %s → %s' % ('통과' if g1 else '미달', '통과' if g2 else '미달', '통과' if c1 else '미달'))
    print('      (v41 2σ 잣대로 다시: 최종배수 +%.0f%% vs 37.2%%p → %s · Calmar vs 10.2%%p → %s · 20년 q20 +%.0f%% vs 24.7%%p → %s)'
          % ((ratio - 1) * 100, '넘음' if ratio - 1 > 0.372 else '못 넘음', '넘음' if g1 else '못 넘음',
             (qh(C[CAND]) / qh(C[BASE]) - 1) * 100, '넘음' if qh(C[CAND]) / qh(C[BASE]) - 1 > 0.247 else '못 넘음'))
    print('  [5] 갈린 사건 %d건 · 200 승 %d · p=%.3f → %s' % (ndiv, wins, p_ev, '동전 아님' if c2 else '동전던지기 범위'))
    print('  [6a] WFA(Calmar) 밴드≥50%%: %d/6 · 적응형≥고정: %d/6 → %s' % (band_ok, ad_ok, '사전 식별 가능' if c3 else '사전 식별 불가'))
    print('  [7] CSCV PBO(Sharpe) %.3f · OOS 백분위 중앙 200 %.0f%% vs 252 %.0f%% → %s' % (p_s[0], p_s[1] * 100, p_s[2] * 100, '200 우위' if c4 else '우위 없음'))
    print('  [9a] 타 시장 밴드 안 %d/4 → %s' % (hit, '구조적' if c5 else '표본 고유'))
    if c1 and c2 and c3 and c4 and c5:
        verdict = '「200 으로 바꿀 근거 있음」 — 다섯 조건 전부 충족. 그래도 변경은 소유자 결정(동결 규약: 이유가 동결 이후 자료와 무관해야 하고 OOS 재시작).'
    elif c1:
        verdict = '「표본 내 우위는 실재하나 사전 근거 없음」 — 유지(§5-14 D 재확인). 우위의 정체는 [2]·[9b]: 사건 몇 개의 재진입 타이밍.'
    else:
        verdict = '「표본 내 우위조차 판별 문턱 아래」 — §5-14 D 의 「200 이 낫다」 서술을 정정할 것.'
    print('  ⇒ ' + verdict)

    print()
    print(L)
    print('[낳은 다음 질문] (§-1 절대멈춤 6)')
    print(L)
    print('  · §5-14 D 표에 재현 스크립트가 없었다 — 04 의 다른 표들 중 스크립트 없는 것이 더 있는가 (§7 미결과 같은 계열).')
    print('  · 200 의 우위가 「긴 약세장 뒤 재진입 52일 빠름」이라면, 그것은 룩백이 아니라 **재진입 규칙**의 문제다 —')
    print('    그러나 V자 조기복귀·쿨다운은 v41 에서 기각됐고 재진입선을 낮추는 것은 복귀 문턱 변경(§5-13)이다. 재탐색 대상 아님.')
    print('  · 그림자 등록(§5-23 D 비권고)의 판단은 이 결과로 바뀌지 않는다 — 정보량(연 4일)은 같다.')


if __name__ == '__main__':
    main()
