# -*- coding: utf-8 -*-
"""
[자유 설계 · 가상 전략] 「세상의 흐름을 따라 흐르는 전략」 — 소유자 전략과 별개의 모의 실험 (2026-09-03)

소유자 지시: 「내 전략과 별개로 가상으로 — QQQ·SCHD·S&P·필라델피아 등 지수 ETF 마음대로, 방어형(금·채권·선물)도
마음대로, 유동성 전략을 네가 설계해 봐. 기준 틀 없이 자유롭게.」

그래서 이 파일은 −16% 스위치·2배·고정 방어를 **전제하지 않는다.** 여섯 가지 형태를 내 생각대로 짰고, 소유자 전략(B)은
비교 기준으로만 둔다. 어느 것도 채택·반영하지 않는다 — 결과는 04 에 기록만.

우주: 엔진 5 = 나스닥100(NDX 체인) · S&P500 · 필라델피아 반도체(SOX) · 러셀2000 · 배당주 체인(SCHD 계열)
      방어 5 = 금 · 미국채 10년 현물 · 30년 현물 · 5년 선물(현행 다리) · T-bill
      비용 편도 0.1%(회전분에만) · 2배는 합성(2r − c) · 월 1회 재조정(월초 첫 거래일, 전월 말 신호) · 일 단위 스위치는 마감 판정 · 체결 다음 날.

여섯 형태:
  F1 흐름 로테이션(1배)   매월 6개월 모멘텀 상위 2 엔진 균등 — T-bill 보다 못한 엔진은 그 몫을 방어 바스켓(40/40/20)으로
  F2 흐름 로테이션(2배)   F1 과 같되 엔진을 2배로
  F3 온도계 + 유동 엔진    나스닥 −16% 스위치는 「세상의 온도계」로 두고, 켜져 있을 땐 모멘텀 1등 엔진 2배 · 꺼지면 40/40/20
  F4 단계 노출            노출 = 네 신호(200일선 위 · 6개월 모멘텀 + · 12개월 모멘텀 + · 낙폭 > −16%)의 평균 → 0·¼·½·¾·1 배 × 나스닥 2배, 나머지 40/40/20
  F5 전천후 모멘텀(1배)    엔진·방어 10개를 한 통에 놓고 6개월 모멘텀 상위 3 균등 — 양수가 3개 미만이면 나머지는 T-bill
  F6 방어 유동 B          B 그대로인데 방어를 모멘텀 상위 2(금·10년·30년·T-bill·배당) 균등으로
기준: B(나스닥 2배 · −16/−16 · 40/40/20) · 나스닥 2배 맨몸 · 나스닥 1배 맨몸.
창: 1994-05~2026-08(SOX 공통, 32년) · 1987-09~(RUT, SOX 제외) 강건성. 블록 4개.

★ 사전 등록 (결과를 보기 전에 적는다 — CLAUDE.md §-1):
  관문(저장소 잣대 그대로): ① Calmar 상대 +10.2% ② 20년창 p05 ≥ B ③ 4블록 중 3 이상 B 를 이김(Calmar) ④ 룩백 3/6/12개월 고원.
  예측:
    P1 최종배수로 B 를 이기는 형태는 없다(B 는 지난 30년 최고 지수의 2배다).
    P2 F5(전천후 1배)가 가장 얕은 MDD(−30% 안쪽)를 갖고 Calmar 는 B 의 0.8~1.2배.
    P3 F3(온도계+유동 엔진)은 B 의 0.3~0.8배 — 모멘텀이 SOX 를 1999·2020 고점 근처에서 고른다.
    P4 F4(단계 노출)는 MDD 가 B 보다 10~20%p 얕지만 최종 0.3~0.6배(트랜치 계열).
    P5 F6(방어 유동)은 B 의 ±15% 안 — 방어 로테이션은 소음.
    P6 ①②③ 을 동시에 넘는 형태는 없다.
  「틀리면 무엇이 참인가」: 어떤 형태가 ①②③ 을 넘으면 그것은 **그림자 후보**(장부에 병행 기록, 사건 단위 판정)가 되고 소유자 결정으로
  넘어간다. 전부 실패하면 §5-24 의 결론(처음부터 다시 설계해도 낙폭 스위치로 수렴)이 **엔진·방어를 자유롭게 풀어도** 유지된다.

실행: python research/liquid_design.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import io
import sys
import contextlib
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                  # noqa: E402
import hist_defasset as DA                               # noqa: E402
import hist_data as H                                    # noqa: E402

COST = 0.001
Y = 252
L = '=' * 100

with contextlib.redirect_stdout(io.StringIO()):
    G, _ = EC.selfcheck()
IDX = pd.DatetimeIndex(G.idx)
N = len(IDX)
CD = float(G.D['c_daily'])


def load_close(path, col='Close'):
    d = pd.read_csv(path)
    dc = [c for c in d.columns if c.lower() in ('date', 'observation_date')][0]
    d[dc] = pd.to_datetime(d[dc], errors='coerce')
    c = col if col in d.columns else [x for x in d.columns if x != dc][0]
    s = pd.to_numeric(d.set_index(dc)[c], errors='coerce').dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]


def to_ret(px):
    """가격 → 일간수익(IDX 정렬, 없는 날 0). 가격이 없는 구간은 NaN 으로 남겨 창 선택에 쓴다."""
    s = px.reindex(IDX.union(px.index)).ffill().reindex(IDX)
    r = s.pct_change()
    r[s.isna()] = np.nan
    return r.values


# ── 자산 (일간수익 벡터, NaN = 자료 없음) ──────────────────────────────────────
ENG = {
    'NDX': np.nan_to_num(pd.Series(G.D['px'], index=IDX).pct_change().values),
    'SPX': to_ret(load_close('data/hist/yahoo_GSPC.csv')),
    'SOX': to_ret(load_close('data/hist/yahoo_SOX_ohlc.csv')),
    'RUT': to_ret(load_close('data/hist/yahoo_RUT.csv')),
    'DIV': np.nan_to_num(np.asarray(G.D['schdr'], float)),          # 배당주 체인 (총수익)
}
DEF = {
    'GOLD': DA.gold_r(IDX),
    'UST10c': DA.ust_tr(IDX, 10, 'TNX'),
    'UST30c': np.where(IDX < pd.Timestamp('1977-02-15'), np.nan, DA.ust_tr(IDX, 30, 'TYX')),
    'UST5f': DA.ust_tr(IDX, 5, 'TNX', futures=True, fee=DA.UST_FEE),   # 현행 다리
    'TBILL': H.tbill_daily(IDX),
}
MIX = np.nan_to_num(np.asarray(G.Dm['schdr'], float))                  # 40/40/20 채택 방어(월 1회 재조정 내장)
ASSETS = {**ENG, **DEF}
NAMES = list(ASSETS)
R = np.column_stack([np.asarray(ASSETS[k], float) for k in NAMES])      # N × K (NaN 허용)
K = len(NAMES)
col = {k: i for i, k in enumerate(NAMES)}


def lev2(r):
    return 2.0 * np.nan_to_num(r) - CD


def cum(r):
    return np.cumprod(1.0 + np.nan_to_num(r))


def mom(r, lb):
    """룩백 lb 일 누적수익 (자료 없으면 NaN)."""
    rs = pd.Series(r, index=IDX)
    c = pd.Series(cum(r), index=IDX)
    m = c / c.shift(lb) - 1.0
    full = rs.notna().rolling(lb, min_periods=lb).sum().eq(lb)
    m[~full] = np.nan
    return m.values


def dd_of(r, win=252):
    c = pd.Series(cum(r), index=IDX)
    return (c / c.rolling(win, min_periods=win).max() - 1.0).values


def month_starts():
    m = IDX.to_period('M')
    return np.r_[True, m[1:] != m[:-1]]


MS = month_starts()


def month_ends():
    m = IDX.to_period('M')
    return np.r_[m[1:] != m[:-1], True]


ME = month_ends()


def sim_multi(W, RM, cost=COST):
    """W: N×K 목표 비중(그날 마감 판정) → 다음 날 적용. 비용은 현금까지 포함한 편도 회전율."""
    pos = np.vstack([W[:1], W[:-1]])
    r = np.nansum(pos * np.nan_to_num(RM), axis=1)
    r[0] = 0.0
    dw = np.diff(pos, axis=0, prepend=pos[:1])
    turn = (np.abs(dw).sum(axis=1) + np.abs(dw.sum(axis=1))) / 2.0
    return np.cumprod((1.0 + r) * (1.0 - cost * turn))


def mix_weight_rows(w_mix):
    """방어 바스켓 몫(스칼라 벡터) — MIX 는 이미 조립된 한 자산처럼 다룬다."""
    return w_mix


# ── 형태 ────────────────────────────────────────────────────────────────────
def build(lo):
    """lo: 시작 인덱스. 모든 형태를 같은 창에서 만든다. 반환: {이름: 곡선}, 보조 정보."""
    engs = [k for k in ENG if not np.isnan(R[lo:, col[k]]).all()]
    defs = [k for k in DEF if not np.isnan(R[lo:, col[k]]).all()]
    M6 = {k: mom(ASSETS[k], 126) for k in NAMES}
    M12 = {k: mom(ASSETS[k], 252) for k in NAMES}
    M3 = {k: mom(ASSETS[k], 63) for k in NAMES}
    tb6 = mom(DEF['TBILL'], 126)
    ndx_dd = dd_of(ENG['NDX'])
    ndx_c = pd.Series(cum(ENG['NDX']), index=IDX)
    ndx_ma = (ndx_c > ndx_c.rolling(200).mean()).values
    out, info = {}, {}

    def rot_weights(top, lev, lb='6'):
        """엔진 로테이션 — 매월 모멘텀 상위 top 균등. T-bill 미달 엔진 몫은 방어(MIX)."""
        Mm = {'3': M3, '6': M6, '12': M12}[lb]
        W = np.zeros((N, K)); Wmix = np.zeros(N)
        cur = None
        for t in range(lo, N):
            if ME[t] or cur is None:
                sc = {k: Mm[k][t] for k in engs if not np.isnan(Mm[k][t])}
                rank = sorted(sc, key=lambda k: -sc[k])[:top]
                cur = [(k, sc[k] > (tb6[t] if not np.isnan(tb6[t]) else 0)) for k in rank]
            if cur:
                share = 1.0 / len(cur)
                for k, ok in cur:
                    if ok:
                        W[t, col[k]] = share
                    else:
                        Wmix[t] += share
        return W, Wmix

    def curve_from(W, Wmix, lev):
        RM = R.copy()
        if lev == 2:
            for k in engs:
                RM[:, col[k]] = lev2(R[:, col[k]])
        # MIX 를 K+1 번째 자산으로 붙인다
        W2 = np.column_stack([W, Wmix]); RM2 = np.column_stack([RM, MIX])
        c = sim_multi(W2[lo:], RM2[lo:])
        return c, W2[lo:]

    for lb in ('3', '6', '12'):
        W, Wm = rot_weights(2, 1, lb); c, W2 = curve_from(W, Wm, 1); out[f'F1 흐름 로테이션 1배 (lb{lb})'] = c
        if lb == '6':
            info['F1'] = W2
        W, Wm = rot_weights(2, 2, lb); c, W2 = curve_from(W, Wm, 2); out[f'F2 흐름 로테이션 2배 (lb{lb})'] = c
        if lb == '6':
            info['F2'] = W2

    # F3 온도계 + 유동 엔진(1등, 2배)
    for lb in ('3', '6', '12'):
        Mm = {'3': M3, '6': M6, '12': M12}[lb]
        W = np.zeros((N, K)); Wmix = np.zeros(N); cur = None; s = 1
        for t in range(lo, N):
            d = ndx_dd[t]
            if not np.isnan(d):
                s = 0 if (s == 1 and d <= -0.16) else (1 if (s == 0 and d > -0.16) else s)
            if ME[t] or cur is None:
                sc = {k: Mm[k][t] for k in engs if not np.isnan(Mm[k][t])}
                cur = max(sc, key=sc.get) if sc else 'NDX'
            if s == 1:
                W[t, col[cur]] = 1.0
            else:
                Wmix[t] = 1.0
        c, W2 = curve_from(W, Wmix, 2); out[f'F3 온도계+유동 엔진 2배 (lb{lb})'] = c
        if lb == '6':
            info['F3'] = W2

    # F4 단계 노출 (나스닥 2배 × 0..1, 나머지 MIX)
    W = np.zeros((N, K)); Wmix = np.zeros(N)
    for t in range(lo, N):
        sig = [ndx_ma[t], (M6['NDX'][t] or 0) > 0, (M12['NDX'][t] or 0) > 0, (ndx_dd[t] if not np.isnan(ndx_dd[t]) else 0) > -0.16]
        e = sum(bool(x) for x in sig) / 4.0
        W[t, col['NDX']] = e; Wmix[t] = 1.0 - e
    c, W2 = curve_from(W, Wmix, 2); out['F4 단계 노출 (0·¼·½·¾·1 × 나스닥 2배)'] = c; info['F4'] = W2

    # F5 전천후 모멘텀 1배 — 10자산 한 통, 상위 3, 양수 아니면 T-bill
    for lb in ('3', '6', '12'):
        Mm = {'3': M3, '6': M6, '12': M12}[lb]
        W = np.zeros((N, K)); cur = None
        univ = engs + defs
        for t in range(lo, N):
            if ME[t] or cur is None:
                sc = {k: Mm[k][t] for k in univ if not np.isnan(Mm[k][t])}
                rank = sorted(sc, key=lambda k: -sc[k])[:3]
                cur = [(k if sc[k] > 0 else 'TBILL') for k in rank]
            for k in cur:
                W[t, col[k]] += 1.0 / 3
        c = sim_multi(W[lo:], R[lo:]); out[f'F5 전천후 모멘텀 1배 (lb{lb})'] = c
        if lb == '6':
            info['F5'] = np.column_stack([W[lo:], np.zeros(N - lo)])

    # F6 방어 유동 B — 방어 = 모멘텀 상위 2 (금·10년·30년·T-bill·배당)
    for lb in ('3', '6', '12'):
        Mm = {'3': M3, '6': M6, '12': M12}[lb]
        pool = [k for k in ('GOLD', 'UST10c', 'UST30c', 'TBILL', 'DIV') if k in engs + defs]
        W = np.zeros((N, K)); cur = None; s = 1
        for t in range(lo, N):
            d = ndx_dd[t]
            if not np.isnan(d):
                s = 0 if (s == 1 and d <= -0.16) else (1 if (s == 0 and d > -0.16) else s)
            if ME[t] or cur is None:
                sc = {k: Mm[k][t] for k in pool if not np.isnan(Mm[k][t])}
                cur = sorted(sc, key=lambda k: -sc[k])[:2]
            if s == 1:
                W[t, col['NDX']] = 1.0
            else:
                for k in cur:
                    W[t, col[k]] += 0.5
        RM = R.copy(); RM[:, col['NDX']] = lev2(R[:, col['NDX']])
        c = sim_multi(W[lo:], RM[lo:]); out[f'F6 방어 유동 B (lb{lb})'] = c
        if lb == '6':
            info['F6'] = np.column_stack([W[lo:], np.zeros(N - lo)])

    # 기준
    wB = np.asarray(EC.rule_dd(pd.Series(G.D['px'], index=IDX), -0.16, -0.16), float)
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
    out['B 소유자 전략 (나스닥 2배 · −16/−16 · 40/40/20)'] = np.asarray(EC.sim2(wB[lo:], QLDR[lo:], MIX[lo:]), float)
    out['나스닥 2배 맨몸'] = cum(QLDR[lo:])
    out['나스닥 1배 맨몸'] = cum(ENG['NDX'][lo:])
    return out, info, engs, defs


def metrics(c, ix):
    m = EC.fullmet(c, idx=ix)
    m['p05_20'] = EC.p05_20y(c)
    w = 2520
    m['p05_10'] = float(np.quantile(c[w:] / c[:-w], 0.05)) if len(c) > w + 252 else np.nan
    return m


def blocks(c, ix, nb=4):
    edges = np.linspace(0, len(c), nb + 1).astype(int)
    outm = []
    for a, b in zip(edges[:-1], edges[1:]):
        seg = c[a:b] / c[a]
        outm.append(EC.fullmet(seg, idx=ix[a:b])['calmar'])
    return outm


def crisis(c, ix):
    s = pd.Series(c, index=ix); res = {}
    for nm, a, b in (('닷컴', '2000-03-01', '2002-12-31'), ('2008', '2007-10-01', '2009-06-30'),
                     ('2020', '2020-02-01', '2020-06-30'), ('2022', '2021-11-01', '2022-12-31')):
        seg = s.loc[a:b]
        res[nm] = float(np.min(seg.values / np.maximum.accumulate(seg.values) - 1)) * 100 if len(seg) > 20 else np.nan
    return res


def run_window(lo, label):
    ix = IDX[lo:]
    out, info, engs, defs = build(lo)
    base = metrics(out['B 소유자 전략 (나스닥 2배 · −16/−16 · 40/40/20)'], ix)
    bB = blocks(out['B 소유자 전략 (나스닥 2배 · −16/−16 · 40/40/20)'], ix)
    print('\n' + L)
    print(f'{label}  {ix[0].date()} ~ {ix[-1].date()} ({(ix[-1]-ix[0]).days/365.25:.1f}년) · 엔진 {engs} · 방어 {defs}')
    print(L)
    print(f"  {'형태':<44}{'최종배수':>10}{'vsB':>7}{'CAGR':>8}{'MDD':>8}{'Calmar':>8}{'ΔCal':>8}{'20y p05':>9}{'10y p05':>9}{'블록':>6}  관문")
    verdict = {}
    for nm, c in out.items():
        m = metrics(c, ix); bl = blocks(c, ix)
        wins = sum(1 for x, y in zip(bl, bB) if x > y)
        d1 = m['calmar'] / base['calmar'] - 1
        g1 = d1 > 0.102; g2 = (m['p05_20'] >= base['p05_20']) if not np.isnan(m['p05_20']) else False; g3 = wins >= 3
        tag = ('★①②③' if (g1 and g2 and g3) else '  ' + ('①' if g1 else '-') + ('②' if g2 else '-') + ('③' if g3 else '-')) if not nm.startswith(('B ', '나스닥')) else ''
        verdict[nm] = (g1, g2, g3, m)
        print(f"  {nm:<44}{m['final']:>10,.1f}{m['final']/base['final']:>6.2f}x{m['cagr']:>7.2f}%{m['mdd']:>7.1f}%{m['calmar']:>8.3f}"
              f"{d1*100:>+7.1f}%{(m['p05_20'] if not np.isnan(m['p05_20']) else float('nan')):>8.2f}배{m['p05_10']:>8.2f}배{wins:>4d}/4  {tag}")
    print('\n  위기 창 MDD (전략 곡선 · 창 안 최대낙폭)')
    print(f"  {'형태':<44}{'닷컴':>8}{'2008':>8}{'2020':>8}{'2022':>8}")
    for nm, c in out.items():
        if '(lb3)' in nm or '(lb12)' in nm:
            continue
        cr = crisis(c, ix)
        print(f"  {nm:<44}" + ''.join(f"{cr[k]:>7.1f}%" if not np.isnan(cr[k]) else f"{'—':>8}" for k in ('닷컴', '2008', '2020', '2022')))
    # 시간 점유 (lb6)
    print('\n  자산별 시간 점유 (lb6 · 비중 평균)')
    for key in ('F1', 'F2', 'F3', 'F4', 'F5', 'F6'):
        W2 = info.get(key)
        if W2 is None:
            continue
        share = W2.mean(axis=0)
        parts = [f'{NAMES[i]} {share[i]*100:.0f}%' for i in np.argsort(-share[:K])[:4] if share[i] > 0.02]
        if W2.shape[1] > K and share[K] > 0.02:
            parts.append(f'방어바스켓 {share[K]*100:.0f}%')
        print(f'  {key}: ' + ' · '.join(parts))
    return verdict


def main():
    print(L); print('자유 설계 — 세상의 흐름을 따라 흐르는 전략 6형태 × 룩백 3/6/12 vs 소유자 전략 B (규칙 무변경 · 모의 실험)'); print(L)
    lo1 = int(np.argmax(~np.isnan(R[:, col['SOX']])))
    v1 = run_window(lo1, '창 A · SOX 공통창')
    lo2 = int(np.argmax(~np.isnan(R[:, col['RUT']])))
    v2 = run_window(lo2, '창 B · 러셀 공통창 (SOX 는 자료 시작 뒤 합류)')
    print('\n' + L); print('사전 등록 대조 (창 A 기준)'); print(L)
    def get(prefix):
        ks = [k for k in v1 if k.startswith(prefix) and ('(lb6)' in k or 'lb' not in k)]
        return v1[ks[0]] if ks else None
    B = get('B 소유자'); F3 = get('F3'); F4 = get('F4'); F5 = get('F5'); F6 = get('F6')
    allF = {k: v for k, v in v1.items() if k[:2] in ('F1', 'F2', 'F3', 'F4', 'F5', 'F6')}
    print(f"  P1 (최종배수로 B 를 이기는 형태 없음): {'맞음' if all(v[3]['final'] < B[3]['final'] for v in allF.values()) else '틀림'} — "
          f"이긴 것: {[k for k, v in allF.items() if v[3]['final'] >= B[3]['final']]}")
    print(f"  P2 (F5 MDD −30% 안쪽 · Calmar 0.8~1.2×B): MDD {F5[3]['mdd']:.1f}% · Calmar {F5[3]['calmar']/B[3]['calmar']:.2f}×B → "
          f"{'맞음' if (F5[3]['mdd'] > -30 and 0.8 <= F5[3]['calmar']/B[3]['calmar'] <= 1.2) else '틀림'}")
    print(f"  P3 (F3 최종 0.3~0.8×B): {F3[3]['final']/B[3]['final']:.2f}×B → {'맞음' if 0.3 <= F3[3]['final']/B[3]['final'] <= 0.8 else '틀림'}")
    print(f"  P4 (F4 MDD 10~20%p 얕고 최종 0.3~0.6×B): ΔMDD {F4[3]['mdd']-B[3]['mdd']:+.1f}%p · 최종 {F4[3]['final']/B[3]['final']:.2f}×B → "
          f"{'맞음' if (10 <= F4[3]['mdd']-B[3]['mdd'] <= 20 and 0.3 <= F4[3]['final']/B[3]['final'] <= 0.6) else '틀림'}")
    print(f"  P5 (F6 최종 ±15%): {F6[3]['final']/B[3]['final']:.2f}×B → {'맞음' if 0.85 <= F6[3]['final']/B[3]['final'] <= 1.15 else '틀림'}")
    passed = [k for k, v in allF.items() if v[0] and v[1] and v[2]]
    print(f"  P6 (①②③ 동시 통과 없음): {'맞음' if not passed else '틀림'} — 통과: {passed}")
    print('\n이 측정이 낳은 다음 질문 (§-1 절대멈춤 6):')
    print('  · 자유 설계에서 「흐름」이 값을 하는 자리가 있다면 어디인가 — 위기 창 표에서 B 보다 얕은 칸이 있는 형태가 그 답이다(있으면 위에 보인다).')
    print('  · 1배 전천후(F5)가 「잠이 오는 전략」으로서 갖는 값은 최종배수가 아니라 회복기간·MDD 다 — 소유자의 감내선이 바뀌면 그때 다시 볼 것.')


if __name__ == '__main__':
    main()
