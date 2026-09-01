# -*- coding: utf-8 -*-
"""
[실험 · 2026-09-02 — 소유자 「관문은 배제하고, 이전 룰·관문 규약에서 자유롭게 설계해 봐라.
 백테스팅·롤링·OOS 등 검증은 다 거쳐야 한다」]
관문에서 자유로운 설계 3안 + 검증 배터리 — **배터리·통과 기준·예측을 결과 보기 전에 등록**

설계 원칙 (자유롭게 — 단 무덤(04 §1~§5-22)에 있는 것은 이름만 바꿔 다시 하지 않는다)
  처음부터 다시 설계해도 「2배 상품의 왼쪽 꼬리를 자르는 낙폭 스위치」로 수렴한다(04 §0 기전 3:
  노출이 0 이 안 되는 방식은 전부 죽는다). 그래서 규칙을 **대체**하는 안이 아니라 **B 가 구조적으로
  못 보는 구멍**을 겨눈 안만 골랐다:
  X1  장중 재난 스탑 — B 는 종가 판정·익일 체결이라 **하루짜리 급락에는 무보험**이다
      (02 §3: 1987 −3.5%p · 2020 −2.7%p 완화뿐). 공격 중 당일 저가가 「전일까지의 252일 종가고점
      ×(1−s)」를 찍으면 그 자리에서 방어(갭 하락 개장이면 시가 체결·슬리피지 0.1%). 그날 종가 판정이
      공격이면 다음 날 복귀(왕복 비용 0.2%). s ∈ {16,18,20,22,25}%.
      무덤 대조: 체결 「시각」은 무의미(v21·v62)였지만 장중 「가격」 조건은 시험된 적 없다.
      자료: NDX 일중 OHLC 1985-10~ (Yahoo, data/hist/yahoo_NDX_ohlc.csv — 실험 전용 캐시).
  X2  방어에 인버스 슬리브 — §5-14 B: −16 아래 전방 63일 중앙 +1.2%·음수 49% = 동전던지기.
      방어 = (1−x)·바스켓 + x·(−1배 일일 인버스 + T-bill − 보수 0.6%). x ∈ {0.1,0.2,0.3,0.5}.
      무덤 대조: 「방어를 현금으로」·「골라 담기」는 있으나 **역방향 노출은 없다.** 1972~ 체인.
  X3  엔진 교체 — 반도체(SOX) 2배 + 같은 규칙·같은 방어. §5-5 는 SPX·KOSPI(소재가 나쁜 쪽)만
      시험했다 — 소재가 **더 극단적인** 지수는 시험된 적 없다. 1994-05~ (32년, 비중첩 10년창 3.2개).
      2배 합성 드래그 = 0.63·σ²(japan_stress 와 같은 저장소 실측 비율).

검증 배터리 (각 안 × **같은 표본**의 기준 R 대비 — 통과 기준을 결과 보기 전에 고정)
  ① 전체: 최종배수비·MDD·Calmar·**10년창 p05**(주 목적함수 — 02 §2 「나쁜 창의 결과」)·20년창 p05
  ② 비중첩 4블록 승패 (≥3/4)
  ③ 롤링 10년 모든 시작일 승률 + 비중첩 창 수 병기 (참고 — 관문 아님)
  ④ 홀드아웃: 2000-01-01~ 에서 격자 최적(Calmar)을 고르고 **1999 이전**에 적용 — 그 셀이 홀드아웃에서도
     R 을 이기는가 (v18 미관측 28년과 같은 논리). X3 은 1994~ 라 홀드아웃 불가 — 그대로 적는다.
  ⑤ CSCV PBO (S=8·70분할, **기준 R 을 셀에 포함** — pbo_thresh 와 같은 구현) ≤ 0.5
  ⑥ 집중도(G11 형): (C−R) 로그차의 상위 3사건 기여 ≤ 100% ∧ 상위 1건 제외 시 부호 유지
  **통과** = ① (10y p05 ≥ R ∧ MDD 가 R 보다 2%p 넘게 나쁘지 않음) ∧ ② ∧ ④ ∧ ⑤ ∧ ⑥ 전부.
  하나라도 통과하면 ⓐ 반증(파라미터 무작위 200회 분포)을 **먼저** 돌린 뒤에만 보고한다.
  실패하면 참인 것: 그 구멍은 실재해도 **그 방법으로 메우면 평시 비용이 더 크다.**
  통과하면 참인 것: 구멍을 메우는 비용이 역사 안에서 이득보다 작았다 — 그래도 채택이 아니라 소유자 컨펌.

사전 예측 (틀리면 틀렸다고 적는다)
  X1 실패 — 장중 톱니(저가는 찍고 종가는 위) 왕복 비용 > 급락 절약. MDD 개선 ≤ 3%p.
  X2 실패 — 기대수익 0 인 노출에 변동성만 보탬. Calmar↓, MDD 개선 없음.
  X3 실패 — 최종배수는 높아도 MDD 가 감내선 −60% 를 넘고 10년창 p05 가 R 보다 나쁨.

실행:  python research/free_design.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
from itertools import combinations
import numpy as np
import pandas as pd
import eng_common as EC

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

Y = 252
W10, W20 = 10 * Y, 20 * Y
DESIGN = pd.Timestamp('2000-01-01')
COST, SLIP = 0.001, 0.001
DRAG_RATIO = 0.63                      # japan_stress.py / drag_sigma.py 실측 비율
L = '=' * 96

# ---------------------------------------------------------------- 엔진 (검산 먼저)
G, _X = EC.selfcheck()
idx = pd.DatetimeIndex(G.idx)
n = len(idx)
PX = pd.Series(np.asarray(G.D['px'], float), index=idx)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
_cd = G.D['c_daily']                     # 체인에서는 상수(일일 드래그) — 배열이면 그대로
CD = np.full(n, float(_cd)) if np.ndim(_cd) == 0 else np.nan_to_num(np.asarray(_cd, float))
RPX = PX.pct_change().fillna(0.0).values
wB = EC.rule_dd(PX, -0.16, -0.16)
B = np.asarray(EC.sim2(wB, QLDR, MIXR), float)
tb = pd.read_csv('data/hist/fred_DTB3.csv')
tb.columns = ['d', 'r']
tb['d'] = pd.to_datetime(tb['d'])
tb['r'] = pd.to_numeric(tb['r'], errors='coerce')
RF = (tb.set_index('d')['r'].reindex(idx, method='ffill').fillna(0.0) / 100.0 / Y).values


def ohlc(path):
    df = pd.read_csv(path, parse_dates=['Date']).set_index('Date').sort_index()
    df = df[(df.High >= df.Low) & (df.Low > 0)]
    return df


def align(df):
    common = idx.intersection(df.index)
    return idx.get_indexer(common), df.loc[common]


# ---------------------------------------------------------------- 지표
def met(c, ix):
    m = dict(EC.fullmet(np.asarray(c, float), idx=ix))
    m['cagr'], m['mdd'] = m['cagr'] / 100.0, m['mdd'] / 100.0     # fullmet 은 % 단위 → 소수로 통일
    return m


def mdd(c):
    c = np.asarray(c, float)
    return float(np.min(c / np.maximum.accumulate(c) - 1.0))


def wp05(c, W):
    c = np.asarray(c, float)
    if len(c) <= W + 1:
        return float('nan'), 0.0
    m = c[W:] / c[:-W]
    return float(np.percentile(m, 5)), (len(c) - W) / W


def wins(cC, cR, W):
    if len(cC) <= W + 1:
        return float('nan')
    return float(np.mean(cC[W:] / cC[:-W] > cR[W:] / cR[:-W]))


def blocks(cC, cR, K=4):
    b = np.linspace(0, len(cC) - 1, K + 1, dtype=int)
    return [bool(cC[b[i + 1]] / cC[b[i]] > cR[b[i + 1]] / cR[b[i]]) for i in range(K)]


def rets(c):
    c = np.asarray(c, float)
    return np.diff(c, prepend=c[0]) / np.concatenate(([c[0]], c[:-1]))


def _calmar_rows(R):
    a = np.cumprod(1 + R, axis=1)
    peak = np.maximum.accumulate(a, axis=1)
    m = np.abs(np.min(a / peak - 1, axis=1))
    cagr = a[:, -1] ** (Y / R.shape[1]) - 1
    return cagr / np.maximum(m, 1e-9)


def cscv(Rm, names):
    """pbo_thresh.cscv 와 같은 구현 (S=8 · Calmar). 반환: PBO, IS 1등으로 뽑힌 셀 빈도."""
    S = 8
    bnd = np.linspace(0, Rm.shape[1], S + 1, dtype=int)
    blk = [np.arange(bnd[i], bnd[i + 1]) for i in range(S)]
    below, tot, picks = 0, 0, {}
    for isb in combinations(range(S), S // 2):
        oob = [b for b in range(S) if b not in isb]
        i_idx = np.concatenate([blk[b] for b in isb])
        o_idx = np.concatenate([blk[b] for b in oob])
        mi, mo = _calmar_rows(Rm[:, i_idx]), _calmar_rows(Rm[:, o_idx])
        best = int(np.argmax(mi))
        picks[names[best]] = picks.get(names[best], 0) + 1
        w = (np.sum(mo < mo[best]) + 0.5 * np.sum(mo == mo[best])) / len(mo)
        below += int(w < 0.5)
        tot += 1
    return below / tot, picks


def concentration(dlog, groups):
    """groups: 사건 id 배열(사건 밖 = -1). (C−R) 로그차의 사건별 합 → 상위3 기여율·상위1 제외 부호."""
    tot = float(dlog.sum())
    g = pd.Series(dlog[groups >= 0]).groupby(groups[groups >= 0]).sum().sort_values(ascending=False)
    if len(g) == 0 or abs(tot) < 1e-12:
        return float('nan'), True, 0
    top3 = float(g.head(3).sum() / tot) if tot != 0 else float('nan')
    loo_same = np.sign(tot - g.iloc[0]) == np.sign(tot)
    return top3, bool(loo_same), len(g)


# ---------------------------------------------------------------- 배터리
def battery(title, cells, ref, ix, groups_fn=None, holdout=True, pbo=True):
    """cells: {label: curve} · ref: (label, curve) · ix: DatetimeIndex (같은 길이)."""
    rl, rc = ref
    print('\n' + L)
    print(title)
    print(L)
    mR = met(rc, ix)
    p05R, nw = wp05(rc, W10)
    p20R, nw20 = wp05(rc, W20)
    print(f'  기준 {rl}: 최종 {mR["final"]:,.1f}배 · CAGR {mR["cagr"] * 100:.2f}% · MDD {mR["mdd"] * 100:.1f}% · '
          f'Calmar {mR["calmar"]:.3f} · 10y p05 {p05R:.2f}배(비중첩 {nw:.1f}) · 20y p05 {p20R:.2f}배(비중첩 {nw20:.1f})')
    print(f'  {"셀":<10}{"최종/R":>8}{"MDD":>8}{"ΔMDD":>7}{"Calmar":>8}{"10y p05":>9}{"20y p05":>9}{"4블록":>7}{"롤10y승":>8}')
    rows = {}
    for lab, c in cells.items():
        m = met(c, ix)
        p05, _ = wp05(c, W10)
        p20, _ = wp05(c, W20)
        bl = blocks(c, rc)
        rows[lab] = dict(ratio=m['final'] / mR['final'], mdd=m['mdd'], dmdd=m['mdd'] - mR['mdd'],
                         calmar=m['calmar'], p05=p05, p20=p20, blocks=sum(bl), win=wins(c, rc, W10))
        r = rows[lab]
        print(f'  {lab:<10}{r["ratio"]:>8.3f}{r["mdd"] * 100:>7.1f}%{r["dmdd"] * 100:>+6.1f}p{r["calmar"]:>8.3f}'
              f'{r["p05"]:>9.2f}{r["p20"]:>9.2f}{r["blocks"]:>5}/4{r["win"] * 100:>7.0f}%')
    # ④ 홀드아웃
    best, hold_ok = None, None
    if holdout:
        d = ix >= DESIGN
        h = ~d
        def calmar_on(c, mask):
            return met(np.asarray(c)[mask] / np.asarray(c)[mask][0], ix[mask])['calmar']
        best = max(cells, key=lambda k: calmar_on(cells[k], d))
        cH, rH = np.asarray(cells[best])[h], np.asarray(rc)[h]
        cH, rH = cH / cH[0], rH / rH[0]
        mult_ok = cH[-1] > rH[-1]
        mdd_ok = mdd(cH) >= mdd(rH) - 0.02
        hold_ok = bool(mult_ok and mdd_ok)
        print(f'  ④ 홀드아웃: 2000~ Calmar 최적 = {best} → 1999 이전({ix[h][0].date()}~{ix[h][-1].date()}): '
              f'최종 {cH[-1] / rH[-1]:.3f}×R · MDD {mdd(cH) * 100:.1f}% vs R {mdd(rH) * 100:.1f}% → '
              f'{"통과" if hold_ok else "실패"}')
    # ⑤ PBO
    pbo_v = None
    if pbo:
        names = list(cells) + [rl]
        Rm = np.asarray([rets(cells[k]) for k in cells] + [rets(rc)])
        pbo_v, picks = cscv(Rm, names)
        top = ', '.join(f'{k}({v})' for k, v in sorted(picks.items(), key=lambda t: -t[1])[:4])
        print(f'  ⑤ PBO(CSCV S=8, 기준 포함 {len(names)}셀) = **{pbo_v:.3f}** · IS 1등 빈도: {top}')
    # ⑥ 집중도 (홀드아웃 최적 셀 또는 첫 셀)
    conc = None
    if groups_fn is not None:
        lab = best or list(cells)[0]
        dl = np.log(1 + rets(cells[lab])) - np.log(1 + rets(rc))
        top3, loo, ng = concentration(dl, groups_fn(lab))
        conc = (top3, loo)
        print(f'  ⑥ 집중도({lab}): (C−R) 총 로그차 {dl.sum():+.3f} · 사건 {ng}개 · 상위3 기여 {top3 * 100:.0f}% · '
              f'상위1 제외 부호 {"유지" if loo else "반전"}')
    # 판정
    lab = best or list(cells)[0]
    r = rows[lab]
    checks = [
        ('① 10y p05 ≥ R', r['p05'] >= p05R),
        ('① MDD 가 R 보다 2%p 넘게 나쁘지 않음', r['dmdd'] >= -0.02),
        ('② 4블록 ≥ 3/4', r['blocks'] >= 3),
    ]
    if holdout:
        checks.append(('④ 홀드아웃 부호 유지', hold_ok))
    if pbo:
        checks.append(('⑤ PBO ≤ 0.5', pbo_v <= 0.5))
    if conc is not None:
        checks.append(('⑥ 상위3 ≤ 100% ∧ 상위1 제외 부호 유지', (not np.isnan(conc[0])) and conc[0] <= 1.0 and conc[1]))
    ok_all = all(v for _, v in checks)
    print(f'  판정 대상 셀 {lab}: ' + ' · '.join(f'{k} {"O" if v else "X"}' for k, v in checks))
    print(f'  → **{"통과 (→ ⓐ 반증 필요)" if ok_all else "실패"}**')
    return rows, lab, ok_all


# ================================================================ X1 장중 재난 스탑
posN, N = align(ohlc('data/hist/yahoo_NDX_ohlc.csv'))
ixN = idx[posN]
qN, mN, cdN = QLDR[posN], MIXR[posN], CD[posN]
C, O, Lo = N.Close.values, N.Open.values, N.Low.values
cN = pd.Series(C)
wN = EC.rule_dd(cN, -0.16, -0.16)
BR = np.asarray(EC.sim2(wN, qN, mN), float)
hi_prev = cN.rolling(Y, min_periods=1).max().shift(1).values
X1_EVENTS = {}


def x1(s, slip=SLIP, cost=COST):
    nn = len(C)
    r = np.zeros(nn)
    pos = np.empty(nn)
    pos[0] = wN[0]
    pos[1:] = wN[:-1]
    extra = np.zeros(nn)
    grp = np.full(nn, -1)
    k = 0
    for t in range(1, nn):
        if pos[t] == 1 and not np.isnan(hi_prev[t]):
            line = hi_prev[t] * (1 - s)
            if Lo[t] <= line:
                fill = (O[t] if O[t] <= line else line) * (1 - slip)
                r[t] = 2 * (fill / C[t - 1] - 1) - cdN[t]
                grp[t] = k
                if wN[t] == 1 and t + 1 < nn:          # 톱니: 종가 판정은 공격 → 익일 복귀 왕복
                    extra[t + 1] = 2
                    grp[t + 1] = k
                k += 1
                continue
        r[t] = pos[t] * qN[t] + (1 - pos[t]) * mN[t]
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    c = np.cumprod((1 + r) * (1 - cost * turn) * (1 - cost * extra))
    return c, grp


X1 = {}
for s in (0.16, 0.18, 0.20, 0.22, 0.25):
    lab = f's{int(s * 100)}'
    X1[lab], X1_EVENTS[lab] = x1(s)
print(L)
print('X1 장중 재난 스탑 — NDX 일중 자료 정합: 체인 B 와 NDX-종가 규칙 B 의 상태 불일치 '
      f'{int(np.mean(wN != wB[posN]) * 100 * 100) / 100:.2f}% 일 · 표본 {ixN[0].date()}~{ixN[-1].date()} ({len(ixN):,}일)')
for lab in X1:
    g = X1_EVENTS[lab]
    ns = len(set(g[g >= 0]))
    whip = int(np.sum([1 for t in range(len(g)) if g[t] >= 0 and t + 1 < len(g) and g[t + 1] == g[t]]))
    print(f'  {lab}: 스탑 발동 {ns}회 · 그중 톱니(종가는 공격) {whip}회')
rowsX1, labX1, okX1 = battery('X1 장중 재난 스탑 vs R = 같은 표본의 B (NDX 종가 규칙)', X1, ('B', BR), ixN,
                              groups_fn=lambda lab: X1_EVENTS[lab])
# 급락 사건 3개에서 실제로 얼마나 아꼈나 (서술 자료 — 관문 아님)
print('  급락 사건 창(−5~+10 거래일) 곡선비 X1/R:')
for d0 in ('1987-10-19', '2008-10-15', '2020-03-16'):
    t = ixN.get_indexer([pd.Timestamp(d0)])[0]
    if t < 0:
        continue
    for lab in ('s16', 's20'):
        c = X1[lab]
        print(f'    {d0} {lab}: {c[t + 10] / c[t - 5] / (BR[t + 10] / BR[t - 5]):.3f}')

# ================================================================ X2 방어에 인버스 슬리브
X2, X2_GRP = {}, {}
# 방어 에피소드 id (사건별 집중도용)
ep = np.full(n, -1)
k = -1
for t in range(1, n):
    if wB[t - 1] == 1 and wB[t] == 0:
        k += 1
    if wB[t] == 0 or (t > 0 and wB[t - 1] == 0):
        ep[t] = k
for x in (0.1, 0.2, 0.3, 0.5):
    rinv = -RPX + RF - 0.006 / Y
    rdef = (1 - x) * MIXR + x * rinv
    lab = f'x{int(x * 100)}'
    X2[lab] = np.asarray(EC.sim2(wB, QLDR, rdef), float)
rowsX2, labX2, okX2 = battery('X2 방어 인버스 슬리브 vs R = B (1972~ 체인)', X2, ('B', B), idx,
                              groups_fn=lambda lab: ep)
# 서술: 방어 구간에서 인버스가 번 날/잃은 날
d = np.r_[False, wB[:-1] == 0]           # ★ 보유일 = 신호 다음 날(pos = w.shift(1)). 신호일로 재면 교차일의 급락을 인버스가 먹은 것처럼 보인다(선견)
print(f'  방어 보유일 {int(d.sum()):,}일 동안 −1배 인버스(비용 후) 연환산 {((np.prod(1 + (-RPX + RF - 0.006 / Y)[d])) ** (Y / max(d.sum(), 1)) - 1) * 100:+.2f}% · '
      f'바스켓 {((np.prod(1 + MIXR[d])) ** (Y / max(d.sum(), 1)) - 1) * 100:+.2f}%')

# ================================================================ X3 SOX 2배 엔진
posS, S = align(ohlc('data/hist/yahoo_SOX_ohlc.csv'))
ixS = idx[posS]
rs = pd.Series(S.Close.values).pct_change().fillna(0.0).values
var_ann = float(np.var(rs) * Y)
r2s = 2 * rs - DRAG_RATIO * var_ann / Y
wS = EC.rule_dd(pd.Series(S.Close.values), -0.16, -0.16)
XS = np.asarray(EC.sim2(wS, r2s, MIXR[posS]), float)
HS = np.cumprod(1 + r2s)
wR = EC.rule_dd(pd.Series(PX.values[posS]), -0.16, -0.16)
BRs = np.asarray(EC.sim2(wR, QLDR[posS], MIXR[posS]), float)
HN2 = np.cumprod(1 + QLDR[posS])
print('\n' + L)
print(f'X3 SOX 2배 — 표본 {ixS[0].date()}~{ixS[-1].date()} ({len(ixS):,}일) · SOX 연율 σ {np.sqrt(var_ann) * 100:.1f}% → '
      f'2배 드래그 {DRAG_RATIO * var_ann * 100:.2f}%/년 (NDX 체인 실측 드래그 {np.mean(CD[posS]) * Y * 100:.2f}%/년)')
mHS, mHN = met(HS, ixS), met(HN2, ixS)
print(f'  맨몸 2배: SOX 최종 {mHS["final"]:,.1f}배 · MDD {mHS["mdd"] * 100:.1f}%  |  NDX 최종 {mHN["final"]:,.1f}배 · MDD {mHN["mdd"] * 100:.1f}%')
rowsX3, labX3, okX3 = battery('X3 SOX 2배 + 같은 규칙 vs R = NDX 2배 + 같은 규칙 (1994-05~, 같은 방어)', {'SOX-B': XS},
                              ('NDX-B', BRs), ixS, holdout=False, pbo=False)
print(f'  규칙이 SOX 에서도 값을 하나: SOX-B/SOX-맨몸 = {XS[-1] / HS[-1]:.2f}배 (NDX 같은 창 {BRs[-1] / HN2[-1]:.2f}배) · '
      f'SOX-B MDD {mdd(XS) * 100:.1f}% (감내선 −60%)')
print('  ⚠ 홀드아웃·PBO 없음(32년 단일 창·격자 없음) — 이 표는 「이 창에서」로 한정된다.')

# ================================================================ 종합 · 예측 대비 · ⓐ 반증
print('\n' + L)
print('종합 — 사전 예측 대비')
print(L)
pred = {'X1': ('실패 (톱니 왕복 > 급락 절약 · MDD 개선 ≤ 3%p)', okX1, rowsX1[labX1]),
        'X2': ('실패 (Calmar↓ · MDD 개선 없음)', okX2, rowsX2[labX2]),
        'X3': ('실패 (MDD > −60% 감내선 · 10y p05 < R)', okX3, rowsX3[labX3])}
for k_, (p, okv, r) in pred.items():
    print(f'  {k_}: 예측 「{p}」 → 결과 **{"통과" if okv else "실패"}** '
          f'(최종/R {r["ratio"]:.3f} · ΔMDD {r["dmdd"] * 100:+.1f}p · 10y p05 {r["p05"]:.2f})')
if okX1:
    print('\n  ⓐ 반증 — X1 파라미터 무작위 200회 (s ~ U(0.10, 0.30)) 분포:')
    rng = np.random.default_rng(20260902)
    ratio, dm = [], []
    for s in rng.uniform(0.10, 0.30, 200):
        c, _ = x1(float(s))
        ratio.append(c[-1] / BR[-1]); dm.append(mdd(c) - mdd(BR))
    ratio, dm = np.asarray(ratio), np.asarray(dm)
    print(f'    최종/R 중앙 {np.median(ratio):.3f} (P10 {np.percentile(ratio, 10):.3f}) · R 초과 비율 {np.mean(ratio > 1) * 100:.0f}% · '
          f'ΔMDD 중앙 {np.median(dm) * 100:+.1f}p')
if okX2:
    print('\n  ⓐ 반증 — X2 x 무작위 200회 (x ~ U(0, 0.6)):')
    rng = np.random.default_rng(20260902)
    ratio = []
    for x in rng.uniform(0.0, 0.6, 200):
        rdef = (1 - x) * MIXR + x * (-RPX + RF - 0.006 / Y)
        c = np.asarray(EC.sim2(wB, QLDR, rdef), float)
        ratio.append(c[-1] / B[-1])
    ratio = np.asarray(ratio)
    print(f'    최종/R 중앙 {np.median(ratio):.3f} · R 초과 비율 {np.mean(ratio > 1) * 100:.0f}%')

print('\n' + L)
print('이 측정이 낳은 다음 질문 (§-1 절대멈춤 6)')
print(L)
print('  · X1 이 급락 사건에서 실제로 아낀 폭은 얼마이고, 그 값이 톱니 비용의 몇 %인가 — 위 급락 창 표가 재료.')
print('  · X2 의 인버스가 방어 구간에서 실제로 번 해가 있는가(2000~02 · 2008) — 있다면 왜 총합이 그 모양인가.')
print('  · X3 에서 규칙이 SOX 맨몸을 몇 배 살렸는가는 「규칙의 값」이고, SOX-B 가 NDX-B 를 이겼는가는 「소재의 값」이다 — 둘을 분리해 읽어야 한다.')
