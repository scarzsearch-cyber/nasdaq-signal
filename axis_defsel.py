# -*- coding: utf-8 -*-
"""
[v27 축5] 방어 안에서도 고를 것인가 — 방어자산 동적 선택

사용자 질문 (2026-08-27):
  "QLD 에서 방어로 들어갈 때, 배당·국채·금의 장 상황(우상향 중인가)에 따라
   배당100 으로 갈지 40/40/20 으로 나눌지 정하면 좋지 않나? QQQ 의 DD 처럼."
  "벌 생각이 없으면 현금으로 빼면 되잖아. 그럼에도 방어자산을 산다는 건
   방어 안에서도 투자를 한다는 방향성이잖아."

두 번째 문장이 이 축의 정당성이다. 맞다 — 방어는 현금이 아니다(§1 이 그 값을 잰다).
그러면 "방어 안에서 무엇을 살지"도 신호로 고를 수 있어야 논리가 일관된다.
**그 논리가 실제로 돈이 되는지를 잰다.**

[검증 순서]
  1) 전제       왜 현금이 아닌가 — 방어자산이 실제로 버는 돈
  2) 예측력     방어자산 3종에 낙폭·모멘텀 신호가 통하는가 (QQQ 대비)
  3) 유효표본   도피 에피소드가 몇 개인가 — 통계적 검정력의 상한
  4) 본 판정    선택규칙 10종 x 전략 A/B, 전구간 / 2000-
  5) 스윕       룩백·문턱이 고원인가 첨탑인가
  6) 워크포워드 1972-1999 에서 고르고 2000- 에 적용 (진짜 OOS)
  7) 롤링       창별 분포 — 중앙값이 아니라 좌측꼬리를 본다
  8) 원화       실제로 사게 될 통화 기준
  9) 판정

실행:  python axis_defsel.py
"""
import numpy as np
import pandas as pd

import hist_data as H
import hist_defasset as DA
import hist_defensive as DF
import hist_krfinal as KF
from axis_lib import COST, rule_w, check
from axis_defmix import sim_def, materials

KEYS = ['div', 'ust5', 'gold', 'tbill']
BASE = {'div': 0.40, 'ust5': 0.40, 'gold': 0.20, 'tbill': 0.0}
NAMEK = {'div': '배당', 'ust5': '국채5Y', 'gold': '금', 'tbill': '현금'}
SLEEVE_COST = 0.0005


# ---------------------------------------------------------------- 신호 (전부 i-1 까지만 본다)
def cum_of(r):
    return np.cumprod(1 + np.nan_to_num(r))


def mom_arr(c, lb):
    """i 일에 쓰는 값 = [i-1-lb, i-1] 누적수익. 미래 참조 없음."""
    n = len(c)
    m = np.full(n, np.nan)
    if lb + 1 < n:
        m[lb + 1:] = c[lb:n - 1] / c[0:n - 1 - lb] - 1.0
    return m


def dd_arr(c, lb):
    s = pd.Series(c)
    return (s / s.rolling(lb, min_periods=lb).max() - 1.0).shift(1).values


def ma_arr(c, lb):
    s = pd.Series(c)
    return (s / s.rolling(lb, min_periods=lb).mean() - 1.0).shift(1).values


def vol_arr(r, lb):
    return pd.Series(np.nan_to_num(r)).rolling(lb).std().shift(1).values


# ---------------------------------------------------------------- 동적 바스켓
def mix_dyn(parts, W, idx, cost=SLEEVE_COST):
    """월초에 W[i] 목표비중으로 재조정하는 바스켓의 일간수익.

    고정비중이면 DA.mix_monthly_parts 와 같은 규약이다(§4 에서 오차 0 검산).
    """
    per = pd.Series(idx).dt.to_period('M').values
    n = len(idx)
    R = np.column_stack([np.nan_to_num(parts[k]) for k in KEYS])
    out = np.zeros(n)
    b = W[0].copy()
    for i in range(n):
        prev = b.sum()                      # [v27 정정] 재조정 비용 차감 **전** 값.
        if i > 0 and per[i] != per[i - 1]:  # 비용 뒤에 재면 비율에서 약분돼 사라진다.
            v = prev
            t = W[i]
            turn = np.abs(b / v - t).sum() / 2.0
            v *= (1 - cost * 2 * turn)
            b = v * t
        b = b * (1 + R[i])
        out[i] = b.sum() / prev - 1.0
    out[0] = 0.0
    return out


def norm(w):
    s = w.sum()
    if s <= 1e-12:
        z = np.zeros(len(KEYS)); z[KEYS.index('tbill')] = 1.0
        return z
    return w / s


MOMK = ('절대모멘텀', '상대모멘텀 1등', '상대모멘텀 2등까지', '모멘텀가중')


def wpath(kind, S, n, param=None):
    """정책별 목표비중 경로 (n x 4). 신호가 없는 초기 구간은 기본 바스켓."""
    base = np.array([BASE[k] for k in KEYS])
    W = np.tile(base, (n, 1))
    if kind == '고정 40/40/20':
        return W
    if kind == '배당100':
        return np.tile(np.array([1., 0., 0., 0.]), (n, 1))
    if kind == '현금100':
        return np.tile(np.array([0., 0., 0., 1.]), (n, 1))
    if kind == '동일가중 1/3':
        return np.tile(np.array([1 / 3, 1 / 3, 1 / 3, 0.]), (n, 1))

    risky = ['div', 'ust5', 'gold']
    lb = (param or 252) if kind in MOMK else 252
    M = np.column_stack([S['mom'][k][lb] for k in risky])
    Mc = S['mom']['tbill'][lb]
    for i in range(n):
        m = M[i]
        if np.isnan(m).any() and kind in MOMK:
            continue
        if kind == '절대모멘텀':
            keep = m > np.nan_to_num(Mc[i])
            w = np.array([BASE[k] if keep[j] else 0.0 for j, k in enumerate(risky)] + [0.0])
            w[3] = sum(BASE[k] for j, k in enumerate(risky) if not keep[j])
            W[i] = norm(w)
        elif kind == '상대모멘텀 1등':
            w = np.zeros(4); w[risky.index(risky[int(np.argmax(m))])] = 1.0
            W[i] = w
        elif kind == '상대모멘텀 2등까지':
            o = np.argsort(-m)[:2]
            w = np.zeros(4)
            for j in o:
                w[j] = BASE[risky[j]]
            W[i] = norm(w)
        elif kind == '낙폭배제':
            th = -(param or 10) / 100.0
            d = np.array([S['dd'][k][252][i] for k in risky])
            if np.isnan(d).any():
                continue
            w = np.array([BASE[k] if d[j] > th else 0.0 for j, k in enumerate(risky)] + [0.0])
            w[3] = sum(BASE[k] for j, k in enumerate(risky) if not (d[j] > th))
            W[i] = norm(w)
        elif kind == 'MA200 위만':
            a = np.array([S['ma'][k][200][i] for k in risky])
            if np.isnan(a).any():
                continue
            w = np.array([BASE[k] if a[j] > 0 else 0.0 for j, k in enumerate(risky)] + [0.0])
            w[3] = sum(BASE[k] for j, k in enumerate(risky) if not (a[j] > 0))
            W[i] = norm(w)
        elif kind == '역변동성':
            v = np.array([S['vol'][k][60][i] for k in risky])
            if np.isnan(v).any() or (v <= 0).any():
                continue
            w = 1.0 / v
            W[i] = norm(np.concatenate([w, [0.0]]))
        elif kind == '모멘텀가중':
            p = np.clip(m, 0, None)
            if p.sum() <= 0:
                W[i] = norm(np.array([0., 0., 0., 1.]))
            else:
                W[i] = norm(np.concatenate([p, [0.0]]))
    return W


def signals(comp, lbs=(63, 126, 189, 252, 378, 504)):
    S = {'mom': {}, 'dd': {}, 'ma': {}, 'vol': {}, 'cum': {}}
    for k in KEYS:
        c = cum_of(comp[k])
        S['cum'][k] = c
        S['mom'][k] = {lb: mom_arr(c, lb) for lb in lbs}
        S['dd'][k] = {252: dd_arr(c, 252)}
        S['ma'][k] = {200: ma_arr(c, 200)}
        S['vol'][k] = {60: vol_arr(comp[k], 60)}
    return S


# ---------------------------------------------------------------- 1) 전제
def s1_premise(D, comp, idx):
    print('===== 1) 전제 — 왜 현금이 아닌가 =====')
    print('"벌 생각이 없으면 현금으로 빼면 된다"는 말이 맞는지부터 잰다.')
    wB = rule_w(D['ddv'], -0.16, -0.16)
    # [규약] 도피 구간은 **전일 신호로 결정된 당일 포지션**이다. 신호 자체(wB==0)로
    # 마스킹하면 전환 당일(폭락일)의 수익까지 방어자산 몫으로 잘못 붙는다.
    # 그 오류는 배당100 의 도피중 수익을 +8.6% -> -8.0% 로 뒤집을 만큼 크다.
    pos = np.concatenate([[wB[0]], wB[:-1]])
    esc = (pos == 0)
    yrs_esc = esc.sum() / 252.0
    parts = {k: comp[k] for k in KEYS}
    print()
    print('  [성분 자체의 도피구간 수익 — 도피한 날짜만 이어붙인 연율]')
    print('  %-10s %10s' % ('성분', '도피중 CAGR'))
    for k in KEYS:
        pr = np.prod(1 + comp[k][esc])
        print('  %-10s %9.2f%%' % (NAMEK[k], (pr ** (1 / yrs_esc) - 1) * 100))
    rows = []
    for nm in ('현금100', '배당100', '고정 40/40/20'):
        dfr = mix_dyn(parts, wpath(nm, None, len(idx)), idx)
        sleeve = np.prod(1 + dfr[esc]) ** (1 / yrs_esc) - 1
        for lab, st in (('1972-', None), ('2000-', '2000-01-03')):
            c = sim_def(D, wB, dfr, start=st)
            y = (c.index[-1] - c.index[0]).days / 365.25
            rows.append(dict(방어=nm, 구간=lab, 최종배수=float(c.iloc[-1]),
                             CAGR=(float(c.iloc[-1]) ** (1 / y) - 1) * 100,
                             MDD=float((c / c.cummax() - 1).min()) * 100,
                             도피중CAGR=sleeve * 100))
    df = pd.DataFrame(rows)
    print()
    print(df.to_string(index=False, float_format=lambda x: format(x, ',.2f')))
    print('  도피 비중은 전체의 %.0f%%(%.1f년). 현금 대비 차이가 "방어도 번다"의 값이다.'
          % (100.0 * esc.mean(), yrs_esc))
    return wB


# ---------------------------------------------------------------- 2) 예측력
def _split(rser, sig, valid, idx):
    """월간 표본으로 신호 켜짐/꺼짐을 가른다. 신호는 이미 i-1 기준으로 밀려 있다."""
    mr = (pd.Series(rser, index=idx) + 1).resample('MS').prod() - 1
    sm = pd.Series(np.asarray(sig, dtype=float), index=idx).resample('MS').first()
    vm = pd.Series(np.asarray(valid, dtype=float), index=idx).resample('MS').first()
    m = pd.DataFrame({'r': mr, 's': sm, 'v': vm}).dropna()
    m = m[m['v'] > 0]
    return m[m['s'] > 0]['r'], m[m['s'] <= 0]['r'], len(m)


def _report(tag, nm, on, off):
    if len(on) < 24 or len(off) < 24:
        print('%-12s %-18s %7d  표본부족' % (tag, nm, len(on) + len(off)))
        return
    a = (1 + on.mean()) ** 12 - 1
    b = (1 + off.mean()) ** 12 - 1
    t = (on.mean() - off.mean()) / np.sqrt(on.var() / len(on) + off.var() / len(off))
    print('%-12s %-18s %7d %9.2f%% %9.2f%% %8.2f%%p %7.2f'
          % (tag, nm, len(on) + len(off), a * 100, b * 100, (a - b) * 100, t))


def s2_power(D, comp, idx, S):
    print()
    print('===== 2) 예측력 — 방어자산에 신호가 통하는가 (QQQ 대비) =====')
    print('월간 표본. 신호는 전월말 기준(미래 참조 없음). 켜짐/꺼짐 연율수익과 차이의 t값.')
    print('%-12s %-18s %7s %10s %10s %9s %7s'
          % ('자산', '신호', 'n(월)', '켜짐', '꺼짐', '차이', 't'))
    tb = np.nan_to_num(S['mom']['tbill'][252])
    for k in ('div', 'ust5', 'gold'):
        raw = [('12M 모멘텀 >현금', S['mom'][k][252], S['mom'][k][252] > tb),
               ('252일 낙폭 >-10%', S['dd'][k][252], S['dd'][k][252] > -0.10),
               ('MA200 위', S['ma'][k][200], S['ma'][k][200] > 0)]
        for nm, rawv, sig in raw:
            on, off, _ = _split(comp[k], sig, ~np.isnan(rawv), idx)
            _report(NAMEK[k], nm, on, off)
    print('  ---- 대조군: 같은 신호를 QQQ(1배) 에 걸면 ----')
    rq = np.nan_to_num(D['px'].pct_change().values)
    qc = cum_of(rq)
    for nm, rawv, sig in [('12M 모멘텀 >현금', mom_arr(qc, 252), mom_arr(qc, 252) > tb),
                          ('252일 낙폭 >-10%', dd_arr(qc, 252), dd_arr(qc, 252) > -0.10),
                          ('MA200 위', ma_arr(qc, 200), ma_arr(qc, 200) > 0),
                          ('252일 낙폭 >-16%(현행)', D['ddv'], D['ddv'] > -0.16)]:
        on, off, _ = _split(rq, sig, ~np.isnan(np.asarray(rawv, dtype=float)), idx)
        _report('QQQ', nm, on, off)
    print('  ※ 이 표가 이 축의 핵심이다. 현행 규칙이 QQQ 에서 사는 이유는 수익 예측력이')
    print('    아니라 **2배 상품의 변동성 손실을 끊는 것**이다. 1배 방어자산에는 그 기전이')
    print('    아예 없으므로, 같은 신호를 걸어도 남는 것은 수익 예측력뿐이다.')


# ---------------------------------------------------------------- 3) 유효표본
def s3_episodes(D, comp, idx, wB, S):
    print('\n===== 3) 유효표본 — 도피 에피소드는 몇 개인가 =====')
    z = (wB == 0).astype(int)
    d = np.diff(z, prepend=0)
    st = np.where(d == 1)[0]
    en = np.where(np.diff(z, append=0) == -1)[0]
    n = min(len(st), len(en))
    print('%-12s %-12s %6s %8s %8s %8s %8s  %-8s %-8s %s'
          % ('시작', '종료', '일수', '배당', '국채5Y', '금', '현금', '사후1등', '모멘텀선택', '적중'))
    hit = tot = shown = 0
    for j in range(n):
        a, b = st[j], en[j]
        if b - a < 5:
            continue
        shown += 1
        cells = {}
        for k in KEYS:
            cells[k] = (np.prod(1 + np.nan_to_num(comp[k][a:b + 1])) - 1) * 100
        risky = ['div', 'ust5', 'gold']
        best = max(risky, key=lambda k: cells[k])
        mm = [S['mom'][k][252][a] for k in risky]
        pick = '—' if np.isnan(mm).any() else risky[int(np.argmax(mm))]
        if pick != '—':
            tot += 1
            hit += (pick == best)
        print('%-12s %-12s %6d %7.1f%% %7.1f%% %7.1f%% %7.1f%%  %-8s %-8s %s'
              % (idx[a].date(), idx[b].date(), b - a + 1,
                 cells['div'], cells['ust5'], cells['gold'], cells['tbill'],
                 NAMEK[best], NAMEK.get(pick, pick),
                 '' if pick == '—' else ('O' if pick == best else 'X')))
    print('  도피 에피소드 %d개(그중 5일 이상 %d개). 모멘텀 1등 선택의 **사후 적중 %d/%d = %.0f%%**'
          % (n, shown, hit, tot, 100.0 * hit / max(tot, 1)))
    print('  세 다리 중 하나를 무작위로 찍으면 33%다. 즉 12M 모멘텀은 다음 도피에서')
    print('  어느 방어자산이 1등일지 **맞히지 못한다**(오히려 무작위보다 나쁘다).')
    print('  ※ 이것이 이 축의 유효표본 전체다. 54년을 돌려도 독립 사건은 %d개뿐이고,' % n)
    print('    그중 의미 있는 길이(20일 이상)는 손에 꼽는다. 선택규칙을 3지선다로 놓으면')
    print('    검정력이 없다 — 무엇이 이겨도 우연과 구별되지 않는다.')
    return n


POLICIES = ['고정 40/40/20', '배당100', '현금100', '동일가중 1/3',
            '절대모멘텀', '상대모멘텀 1등', '상대모멘텀 2등까지',
            '낙폭배제', 'MA200 위만', '역변동성', '모멘텀가중']
PARAM = {'낙폭배제': 10}


def defr_of(parts, idx, nm, S, param=None):
    p = param if param is not None else PARAM.get(nm)
    return mix_dyn(parts, wpath(nm, S, len(idx), p), idx)


# ---------------------------------------------------------------- 4) 본 판정
def s4_verdict(D, comp, idx, S, cost=COST, quiet=False):
    parts = {k: comp[k] for k in KEYS}
    wA = rule_w(D['ddv'], -0.16, -0.11)
    wB = rule_w(D['ddv'], -0.16, -0.16)
    rows = []
    cache = {}
    for nm in POLICIES:
        dfr = defr_of(parts, idx, nm, S)
        cache[nm] = dfr
        for lab, w in (('A -16/-11', wA), ('B -16/-16', wB)):
            for per, st in (('1972-', None), ('2000-', '2000-01-03')):
                c = sim_def(D, w, dfr, cost=cost, start=st)
                y = (c.index[-1] - c.index[0]).days / 365.25
                rows.append(dict(정책=nm, 규칙=lab, 구간=per,
                                 최종배수=float(c.iloc[-1]),
                                 CAGR=(float(c.iloc[-1]) ** (1 / y) - 1) * 100,
                                 MDD=float((c / c.cummax() - 1).min()) * 100))
    df = pd.DataFrame(rows)
    if not quiet:
        print('\n===== 4) 본 판정 — 선택규칙 %d종 x 전략 A/B =====' % len(POLICIES))
        for lab in ('B -16/-16', 'A -16/-11'):
            for per in ('1972-', '2000-'):
                s = df[(df['규칙'] == lab) & (df['구간'] == per)].copy()
                s = s.sort_values('최종배수', ascending=False)
                base = float(s[s['정책'] == '고정 40/40/20']['최종배수'].iloc[0])
                s['현행대비'] = (s['최종배수'] / base - 1) * 100
                print('\n  [%s · %s]' % (lab, per))
                print(s[['정책', '최종배수', 'CAGR', 'MDD', '현행대비']].to_string(
                    index=False, float_format=lambda x: format(x, ',.2f')))
    return df, cache


def s4_check(comp, idx):
    """규약 검산 — 고정비중이면 mix_dyn 이 기존 mix_monthly_parts 와 같아야 한다."""
    parts = {k: comp[k] for k in KEYS}
    a = mix_dyn(parts, wpath('고정 40/40/20', None, len(idx)), idx)
    b = DA.mix_monthly_parts(idx, DA.MIX_V23, {k: comp[k] for k in ('div', 'ust5', 'gold')})
    e = float(np.abs(np.cumprod(1 + a)[-1] / np.cumprod(1 + b)[-1] - 1))
    print('검산 mix_dyn vs mix_monthly_parts (고정 40/40/20) 오차 %.1e  %s'
          % (e, 'OK' if e < 1e-10 else '불일치'))
    return e < 1e-10


# ---------------------------------------------------------------- 5) 스윕
def s5_sweep(D, comp, idx, S):
    print('\n===== 5) 스윕 — 룩백/문턱이 고원인가 첨탑인가 =====')
    parts = {k: comp[k] for k in KEYS}
    wB = rule_w(D['ddv'], -0.16, -0.16)
    base = {}
    for st, lab in ((None, '1972-'), ('2000-01-03', '2000-')):
        c = sim_def(D, wB, defr_of(parts, idx, '고정 40/40/20', S), start=st)
        base[lab] = float(c.iloc[-1])
    print('%-16s %-8s %14s %10s %14s %10s'
          % ('정책', '파라미터', '1972- 배수', '현행대비', '2000- 배수', '현행대비'))
    grid = [('절대모멘텀', (63, 126, 189, 252, 378, 504)),
            ('상대모멘텀 1등', (63, 126, 189, 252, 378, 504)),
            ('상대모멘텀 2등까지', (63, 126, 189, 252, 378, 504)),
            ('모멘텀가중', (63, 126, 189, 252, 378, 504)),
            ('낙폭배제', (5, 8, 10, 15, 20, 30))]
    for nm, ps in grid:
        for p in ps:
            dfr = defr_of(parts, idx, nm, S, param=p)
            cells = []
            for st, lab in ((None, '1972-'), ('2000-01-03', '2000-')):
                v = float(sim_def(D, wB, dfr, start=st).iloc[-1])
                cells += [v, (v / base[lab] - 1) * 100]
            print('%-16s %-8s %14s %9.1f%% %14s %9.1f%%'
                  % (nm, ('%d일' % p) if nm != '낙폭배제' else ('-%d%%' % p),
                     format(cells[0], ',.1f'), cells[1], format(cells[2], ',.1f'), cells[3]))
    print('  ※ 인접 파라미터끼리 부호가 뒤집히면 신호가 아니라 잡음이다.')


# ---------------------------------------------------------------- 5b) 무작위 대조
def s5b_placebo(D, comp, idx, S, n_sim=200):
    """플라시보 — 신호를 **동전던지기로 바꿔도** 그만큼 나오는가.

    이 축에서 유일하게 이긴 규칙(상대모멘텀 2등까지·252일)이 진짜인지 판정하는 방법은
    "같은 자유도를 가진 무의미한 규칙"의 분포를 만들어 그 안 어디에 있는지 보는 것이다.
    매달 3다리 중 1개(또는 2개)를 **무작위로** 고르는 규칙을 n_sim 번 돌린다.
    실제 규칙이 이 분포의 중앙 근처에 있으면, 이긴 것은 신호가 아니라 운이다.
    """
    print()
    print('===== 5b) 무작위 대조 — 이긴 규칙이 동전던지기와 구별되는가 =====')
    parts = {k: comp[k] for k in KEYS}
    wB = rule_w(D['ddv'], -0.16, -0.16)
    per = pd.Series(idx).dt.to_period('M').values
    ms = np.array([0] + [i for i in range(1, len(idx)) if per[i] != per[i - 1]])
    risky = ['div', 'ust5', 'gold']
    base = {}
    for st, lab in ((None, '1972-'), ('2000-01-03', '2000-')):
        base[lab] = float(sim_def(D, wB, defr_of(parts, idx, '고정 40/40/20', S), start=st).iloc[-1])
    real = {}
    for nm in ('상대모멘텀 1등', '상대모멘텀 2등까지'):
        dfr = defr_of(parts, idx, nm, S)
        real[nm] = {lab: (float(sim_def(D, wB, dfr, start=st).iloc[-1]) / base[lab] - 1) * 100
                    for st, lab in ((None, '1972-'), ('2000-01-03', '2000-'))}
    print('%-18s %8s %10s %10s %10s %10s %10s'
          % ('무작위 규칙', 'n', '중앙값', '90%분위', '최고', '실제규칙', '백분위'))
    for pick, nm in ((1, '상대모멘텀 1등'), (2, '상대모멘텀 2등까지')):
        res = {'1972-': [], '2000-': []}
        for sd in range(n_sim):
            rng = np.random.default_rng(9000 + sd)
            W = np.tile(np.array([BASE[k] for k in KEYS]), (len(idx), 1))
            cur = None
            for j, i in enumerate(ms):
                sel = rng.choice(3, size=pick, replace=False)
                w = np.zeros(4)
                for t in sel:
                    w[t] = BASE[risky[t]] if pick > 1 else 1.0
                cur = norm(w)
                nxt = ms[j + 1] if j + 1 < len(ms) else len(idx)
                W[i:nxt] = cur
            dfr = mix_dyn(parts, W, idx)
            for st, lab in ((None, '1972-'), ('2000-01-03', '2000-')):
                res[lab].append((float(sim_def(D, wB, dfr, start=st).iloc[-1]) / base[lab] - 1) * 100)
        for lab in ('1972-', '2000-'):
            a = np.array(res[lab])
            r = real[nm][lab]
            pct = (a < r).mean() * 100
            print('%-18s %8s %9.1f%% %9.1f%% %9.1f%% %9.1f%% %9.0f%%'
                  % ('%d개 무작위 %s' % (pick, lab), n_sim, np.median(a),
                     np.quantile(a, .90), a.max(), r, pct))
    print('  실제규칙 = 12M 모멘텀으로 고른 결과의 현행대비(%). 백분위 = 무작위 분포 안에서의 위치.')
    print('  ※ 백분위가 95% 미만이면 그 규칙은 동전던지기와 구별되지 않는다.')


# ---------------------------------------------------------------- 6) 워크포워드
def s6_wf(D, comp, idx, S):
    print('\n===== 6) 워크포워드 — 과거에서 고르고 미래에 적용 =====')
    parts = {k: comp[k] for k in KEYS}
    wB = rule_w(D['ddv'], -0.16, -0.16)
    splits = [('1972-1989', '1990-01-02'), ('1972-1999', '2000-01-03'),
              ('1972-2009', '2010-01-04')]
    print('%-14s %-20s %16s %16s %s' % ('학습구간', '학습 1등', 'OOS 그 정책', 'OOS 현행', '판정'))
    for tr, cut in splits:
        best, bv = None, -1e18
        for nm in POLICIES:
            dfr = defr_of(parts, idx, nm, S)
            v = float(sim_def(D, wB, dfr, end=cut).iloc[-1])
            if v > bv:
                best, bv = nm, v
        a = float(sim_def(D, wB, defr_of(parts, idx, best, S), start=cut).iloc[-1])
        b = float(sim_def(D, wB, defr_of(parts, idx, '고정 40/40/20', S), start=cut).iloc[-1])
        print('%-14s %-20s %16s %16s %s'
              % (tr, best, format(a, ',.2f'), format(b, ',.2f'),
                 '이김 %+.1f%%' % ((a / b - 1) * 100) if a > b else '짐 %+.1f%%' % ((a / b - 1) * 100)))
    print('  ※ 학습에서 1등이던 정책이 OOS 에서도 이기는가. 이것이 유일한 정직한 시험이다.')


# ---------------------------------------------------------------- 7) 롤링
def s7_rolling(D, comp, idx, S, cache, years=(10, 15, 20), step=126, start=None, tag='달러'):
    print('\n===== 7) 롤링 창 분포 (%s) — 중앙값이 아니라 좌측꼬리를 본다 =====' % tag)
    wB = rule_w(D['ddv'], -0.16, -0.16)
    n = len(idx)
    lo0 = 0 if start is None else int(idx.searchsorted(pd.Timestamp(start)))
    lo0 = max(lo0, 520)
    for y in years:
        span = int(y * 252)
        starts = list(range(lo0, n - span, step))
        print('\n  [%d년 롤링 · 창 %d개]' % (y, len(starts)))
        print('  %-20s %10s %10s %10s %10s %10s'
              % ('정책', '중앙배수', '10%분위', '최악', '중앙MDD', '현행승률'))
        ref = None
        rows = []
        for nm in POLICIES:
            dfr = cache[nm]
            vs, md = [], []
            for lo in starts:
                c = sim_def(D, wB, dfr, start=idx[lo], end=idx[lo + span])
                vs.append(float(c.iloc[-1]))
                md.append(float((c / c.cummax() - 1).min()))
            vs = np.array(vs)
            if nm == '고정 40/40/20':
                ref = vs
            rows.append((nm, vs, np.array(md)))
        for nm, vs, md in rows:
            win = (vs > ref).mean() * 100
            print('  %-20s %10s %10s %10s %9.1f%% %9.0f%%'
                  % (nm, format(np.median(vs), ',.2f'), format(np.quantile(vs, .10), ',.2f'),
                     format(vs.min(), ',.2f'), np.median(md) * 100, win))


# ---------------------------------------------------------------- 8) 원화
def s8_krw(D, DUSD, SUSD):
    print('\n===== 8) 원화 검증 — 실제로 사게 될 통화 기준 =====')
    Dk, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    tb = H.tbill_daily(idx)                       # 원화 단기금리 대용(달러 T-bill 금리, 환효과 없음)
    comp = {'div': np.asarray(dfk, dtype=float),
            'ust5': (1 + DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE)) * (1 + fr) - 1,
            'gold': (1 + DA.gold_r(idx)) * (1 + fr) - 1,
            'tbill': tb}
    S = signals(comp)
    parts = {k: comp[k] for k in KEYS}
    wB = rule_w(D['ddv'], -0.16, -0.16)
    wA = rule_w(D['ddv'], -0.16, -0.11)
    FXS = pd.Timestamp('1981-04-13')            # DEXKOUS 시작 이전은 환율이 없다
    # [대조군] 같은 창(1981-)의 **달러** 결과를 함께 낸다. 그래야 순위가 바뀌었을 때
    # 그것이 통화 때문인지 창 때문인지 갈린다(v24 에서 쓴 이중차분과 같은 취지).
    print('  [대조 · 달러 동일창 1981- · B -16/-16]')
    print('  %-20s %14s %10s' % ('정책', '최종배수', '현행대비'))
    ub = None
    urow = []
    for nm in POLICIES:
        c = sim_def(D, wB, defr_of({k: DUSD[k] for k in KEYS}, D['idx'], nm, SUSD), start=FXS)
        v = float(c.iloc[-1])
        if nm == '고정 40/40/20':
            ub = v
        urow.append((nm, v))
    for nm, v in sorted(urow, key=lambda r: -r[1]):
        print('  %-20s %14s %9.1f%%' % (nm, format(v, ',.1f'), (v / ub - 1) * 100))
    print()
    print('%-20s %-10s %14s %8s %10s %10s'
          % ('정책', '규칙', '최종배수', 'CAGR', 'MDD', '현행대비'))
    out = {}
    for lab, w in (('B -16/-16', wB), ('A -16/-11', wA)):
        base = None
        res = []
        for nm in POLICIES:
            dfr = defr_of(parts, idx, nm, S)
            out[nm] = dfr
            c = sim_def(dict(idx=idx, qldr=lev2), w, dfr, start=FXS)
            y = (c.index[-1] - c.index[0]).days / 365.25
            v = float(c.iloc[-1])
            if nm == '고정 40/40/20':
                base = v
            res.append((nm, v, (v ** (1 / y) - 1) * 100, float((c / c.cummax() - 1).min()) * 100))
        for nm, v, cg, md in sorted(res, key=lambda r: -r[1]):
            print('%-20s %-10s %14s %7.2f%% %9.2f%% %9.1f%%'
                  % (nm, lab, format(v, ',.1f'), cg, md, (v / base - 1) * 100))
        print()
    return dict(idx=idx, qldr=lev2, ddv=D['ddv']), comp, S, out, FXS


# ---------------------------------------------------------------- 비용 민감도
def s_cost(D, comp, idx, S):
    print('\n===== 비용 민감도 — 방어 다리 회전율은 공짜가 아니다 =====')
    parts = {k: comp[k] for k in KEYS}
    wB = rule_w(D['ddv'], -0.16, -0.16)
    print('%-20s %10s %14s %14s %14s'
          % ('정책', '연 회전율', '수수료 5bp', '15bp', '30bp'))
    for nm in POLICIES:
        W = wpath(nm, S, len(idx), PARAM.get(nm))
        per = pd.Series(idx).dt.to_period('M').values
        ms = np.where(np.diff(per.astype(str), prepend='x') != 0)[0] if False else \
            np.array([i for i in range(1, len(idx)) if per[i] != per[i - 1]])
        turn = np.abs(np.diff(W[ms], axis=0)).sum(axis=1).sum() / 2.0
        yrs = (idx[-1] - idx[0]).days / 365.25
        cells = []
        for c in (0.0005, 0.0015, 0.0030):
            dfr = mix_dyn(parts, W, idx, cost=c)
            cells.append(float(sim_def(D, wB, dfr, start='2000-01-03').iloc[-1]))
        print('%-20s %9.2f회 %14s %14s %14s'
              % (nm, turn / yrs, format(cells[0], ',.2f'), format(cells[1], ',.2f'),
                 format(cells[2], ',.2f')))
    print('  ※ 회전율은 도피 구간에만 실제로 물지만, 목표비중이 바뀌는 빈도 자체가')
    print('    "규칙이 얼마나 자주 마음을 바꾸는가"의 지표다.')


# ---------------------------------------------------------------- 9) 판정
def s9_verdict():
    print()
    print('===== 9) 판정 — 기각. 방어 바스켓은 고정한다 =====')
    print()
    print('  [사용자 가설] "방어자산도 우상향 여부를 보고 고르면 낫지 않나?"')
    print('  [답] 논리는 맞다. 그런데 네 개의 관문을 전부 통과하지 못한다.')
    print()
    print('  ① 예측력(§2)  배당·국채는 어떤 신호에도 t ~ 0 이다. 금만 12M 모멘텀 t=3.86')
    print('     으로 진짜 신호다. 그런데 금은 바스켓의 20% 이고 그 바스켓은 전체 시간의')
    print('     18% 만 산다 — 신호가 통해도 전략에 닿는 지분이 3.6% 다.')
    print('  ② 적중(§3)   모멘텀 1등이 다음 도피의 실제 1등을 맞힌 비율 23%. 무작위 33%')
    print('     보다 **나쁘다**. 도피는 직전 추세가 꺾이는 자리라서 그렇다.')
    print('  ③ 첨탑(§5)   유일하게 이긴 규칙(상대모멘텀 2등까지)은 252일에서만 +16% 고')
    print('     189일 -6%, 378일 -15% 다. 고원이 아니라 첨탑이면 잡음이다.')
    print('  ④ 플라시보(§5b) 그 +16% 는 매달 동전을 던져 2개를 고르는 규칙 분포의 82백분위다.')
    print('     무작위 규칙 5개 중 1개가 그보다 낫다. 95% 문턱을 못 넘는다.')
    print('  ⑤ 워크포워드(§6) 학습에서 1등이던 규칙은 OOS 에서 3전 3패다(-33%/-36%/-3%).')
    print()
    print('  [뒤집힌 것] 이 축의 진짜 소득은 반대편에 있다.')
    print('  · §1  [v36 정정] 국채 다리를 **선물형**으로 고치자 도피구간 연율이')
    print('    국채 7.92% -> 2.50%, 바스켓 9.32% -> 7.08% 로 내려갔다.')
    print('    **바스켓이 성분을 전부 이긴다는 주장은 더 이상 성립하지 않는다**')
    print('    (배당 8.57 / 금 8.55 > 바스켓 7.08). 재조정 프리미엄이 근거가 아니다.')
    print('    바스켓의 근거는 **낙폭과 좌측꼬리**다 — MDD -60.48% vs 배당100 -68.12%,')
    print('    원화 20년창 5분위 40.82 vs 35.73, 2008 위기 +9.0% vs -22.7%.')
    print('  · §1  현금100 은 여전히 바스켓에 진다(-17.85%, 1972-). MDD 도 더 나쁘다')
    print('    (-63.1% vs -60.5%) — 위기에 버는 자산이 있으면 낙폭 자체가 얕아지기 때문이다.')
    print('    "벌 생각 없으면 현금" 은 틀렸다. 방어도 벌어야 한다 — 다만 **고르지 말고**.')
    print('  · §8  원화에서 배당100 이 +12.2% 로 1등처럼 보이지만, 달러 동일창(1981-)에서도')
    print('    똑같이 +12.2% 다. 이중차분 0.0%p — 통화가 아니라 **창** 효과다.')
    print('  · §4  동일가중 1/3(+1.8%) 과 역변동성(-9.7%~+4.3%) 은 현행과 사실상 동률이다.')
    print('    비중은 고원이다 — 40/40/20 을 소수점까지 지킬 필요는 없다.')
    print()
    print('  [채택] 방어 바스켓은 배당40 / 국채40 / 금20 고정, 월 1회 재조정. 변경 없음.')


if __name__ == '__main__':
    D = DF.build('chain')
    assert check(D), '검산 실패'
    idx = D['idx']
    comp = materials(D)
    comp = {k: np.nan_to_num(comp[k]) for k in KEYS}
    assert s4_check(comp, idx), 'mix_dyn 규약 불일치'
    S = signals(comp)

    wB = s1_premise(D, comp, idx)
    s2_power(D, comp, idx, S)
    s3_episodes(D, comp, idx, wB, S)
    df, cache = s4_verdict(D, comp, idx, S)
    s5_sweep(D, comp, idx, S)
    s5b_placebo(D, comp, idx, S)
    s6_wf(D, comp, idx, S)
    s7_rolling(D, comp, idx, S, cache, start='1973-01-02', tag='달러')
    s_cost(D, comp, idx, S)
    Dk, ck, Sk, ok, fxs = s8_krw(D, comp, S)
    s7_rolling(Dk, ck, Dk['idx'], Sk, ok, years=(15, 20), start=fxs, tag='원화')
    s9_verdict()
