"""
복귀 로직 연구용 공용 엔진 (HANDOFF.md 작업 ⓪ / 복귀로직_연구프롬프트.md)

verify.py의 데이터 생성·체결·비용 규약을 그대로 따르되, 부분비중(단계적 복귀)을
표현할 수 있도록 상태를 이산 라벨 대신 QLD 비중 w∈[0,1]로 일반화했다.

[verify.py와의 유일한 차이 — 의도된 수정]
verify.py는 sw = (ex != ex.shift(1)) 를 쓰는데 ex[0]은 NaN이라 0일차와 1일차에
거래가 없는데도 편도비용이 두 번 부과된다(0.999^2 = 0.998배). 이 엔진은 그
유령비용을 빼서 계산한다. 따라서 채택안 최종배수가 138.2배가 아니라 138.5배로
나오는데, 138.2 = 138.5 x 0.998 로 정확히 설명된다(check_baseline()이 검증).
모든 후보에 동일 규약을 적용하므로 비교에는 영향이 없다.
"""
import numpy as np
import pandas as pd

ENTER, EXIT, LOOKBACK = -0.16, -0.11, 252
COST = 0.001
CASH_RATE = 0.02
START = '2000-01-03'


# ----------------------------------------------------------------- 데이터
def _load(p):
    return pd.read_csv(p, parse_dates=['Date']).set_index('Date').sort_index()['Close']


def build(cash_rate=CASH_RATE):
    qqq, qld, schd = _load('qqq_us_d.csv'), _load('qld_us_d.csv'), _load('schd_us_d.csv')

    qqq_r, qld_r = qqq.pct_change(), qld.pct_change()
    ov = qqq_r.index.intersection(qld_r.index); ov = ov[ov >= '2006-06-22']
    x, y = qqq_r.reindex(ov).dropna(), qld_r.reindex(ov).dropna()
    cm = x.index.intersection(y.index); x, y = x.reindex(cm), y.reindex(cm)
    c_daily = (2 * x - y).mean()
    pre = qqq_r.index[qqq_r.index < '2006-06-22']
    synth = (2 * qqq_r.reindex(pre) - c_daily).dropna()
    full = pd.concat([synth, y]); full = full[~full.index.duplicated()].sort_index()
    qld_ext = (1 + full).cumprod()

    idx_all = qqq.index.intersection(qld_ext.index).sort_values()
    idx = idx_all[idx_all >= START]
    # [코드리뷰 2026-09-04] 룩백 최대값은 **절단 전** 격자에서 구한다. 종전에는 px 를
    # START 로 자른 뒤 rolling 을 걸어 시작일 이전 가격이 창에 안 들어갔고, 그래서
    # 앞부분 낙폭이 실제보다 얕게 잡혔다(실측 42일 · 최대 15.47%p). −16 문턱에서는
    # 갈리는 날이 0 이라 공표 B 수치는 그대로지만 −0.11/−0.12/−0.14 는 하루씩 갈렸다.
    px_all = qqq.reindex(idx_all)
    dd = (px_all / px_all.rolling(LOOKBACK, min_periods=60).max() - 1).reindex(idx).fillna(0)
    px = px_all.reindex(idx)
    qldr = qld_ext.reindex(idx).pct_change().fillna(0)
    schdr = schd.reindex(idx).pct_change().fillna(cash_rate / 252)
    return dict(idx=idx, px=px, dd=dd,
                qldr=qldr.values.astype(float), schdr=schdr.values.astype(float),
                ddv=dd.values.astype(float), pxv=px.values.astype(float))


def features(D):
    """복귀 신호 후보들의 원재료. 전부 QQQ 종가에서만 만든다(미래 참조 없음)."""
    px, dd = D['px'], D['dd']
    F = {}
    for k in (5, 10, 20, 60):
        F[f'ddrec{k}'] = (dd - dd.shift(k)).fillna(0).values          # 낙폭 회복 폭(%p/100)
    for k in (5, 10, 20, 30, 60):
        F[f'reb{k}'] = (px / px.rolling(k, min_periods=2).min() - 1).fillna(0).values
    for k in (3, 5, 10, 20):
        F[f'ret{k}'] = (px / px.shift(k) - 1).fillna(0).values
    for k in (20, 50):
        ma = px.rolling(k, min_periods=k).mean()
        F[f'ma{k}up'] = (px > ma).fillna(False).values
        F[f'ma{k}slope'] = (ma > ma.shift(5)).fillna(False).values
    return F


# ----------------------------------------------------------------- 엔진
def run(D, ladder, enter=ENTER, cost=COST, lag=1, start=None, end=None, w0=1.0):
    """
    ladder: [(cond, weight, min_days), ...]
      cond   : bool ndarray (길이 = 전체 인덱스) 또는 ('dd', x) 형태의 낙폭 조건
      weight : 그 조건이 켜지면 회복할 QLD 목표비중
      min_days : SCHD 진입 후 최소 경과 거래일
    반환: (곡선 pd.Series, 비중 pd.Series, 일별 회전율 ndarray |diff(pos)|)
    """
    ddv, qldr, schdr, idx = D['ddv'], D['qldr'], D['schdr'], D['idx']
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')

    conds = []
    for c, wt, mind in ladder:
        if isinstance(c, tuple) and c[0] == 'dd':
            conds.append((ddv > c[1], wt, mind))
        else:
            conds.append((np.asarray(c, dtype=bool), wt, mind))

    w = np.empty(n); w[:] = np.nan
    cur, days = w0, 0
    for i in range(lo, hi):
        d = ddv[i]
        if cur >= 1.0:
            if d <= enter:
                cur, days = 0.0, 0
        else:
            days += 1
            if d <= enter:
                cur, days = 0.0, 0      # 재진입도 '진입' — min_days 시계를 다시 센다
            else:
                tgt = cur
                for c, wt, mind in conds:
                    if wt > tgt and days >= mind and c[i]:
                        tgt = wt
                cur = tgt
        w[i] = cur

    seg = slice(lo, hi)
    wv = w[seg]
    pos = np.empty_like(wv)
    if lag:
        pos[:lag] = w0
        pos[lag:] = wv[:-lag]                          # 신호 다음날 체결
    else:
        pos[:] = wv                                    # 당일 신호 = 당일 체결
    r = pos * qldr[seg] + (1 - pos) * schdr[seg]
    r = np.nan_to_num(r); r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    g = (1 + r) * (1 - cost * turn)
    curve = pd.Series(np.cumprod(g), index=idx[seg])
    ws = pd.Series(wv, index=idx[seg])
    return curve, ws, turn


def met(c):
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    cagr = c.iloc[-1] ** (1 / yrs) - 1
    mdd = (c / c.cummax() - 1).min()
    ret = c.pct_change().dropna()
    vol = ret.std() * np.sqrt(252)
    dn = ret[ret < 0].std() * np.sqrt(252)
    return dict(final=float(c.iloc[-1]), cagr=float(cagr), mdd=float(mdd),
                calmar=float(cagr / abs(mdd)) if mdd < 0 else np.nan,
                sharpe=float(ret.mean() * 252 / vol) if vol > 0 else np.nan,
                sortino=float(ret.mean() * 252 / dn) if dn > 0 else np.nan, years=float(yrs))


def ulcer_uw(c):
    """[v60] 낙폭의 **깊이**만이 아니라 **넓이**를 재는 두 지표.

    MDD 는 최악의 한 점만 본다. 그래서 「얕지만 3년을 끄는 곡선」과
    「깊지만 반년에 되찾는 곡선」을 구분하지 못한다. 2배 레버리지에서는
    그 구분이 실제로 버틸 수 있는지를 가른다.

      Ulcer Index   sqrt(mean(dd_t^2)) x 100. 전 구간 평균적 고통. 낮을수록 좋다.
      최장 회복기간  전고점에서 그 전고점을 되찾을 때까지의 최장 달력일수.
                    끝까지 못 되찾았으면 마지막 날까지 세고 open=True 로 표시한다.

    반환 (ulcer_pct, worst_days, worst_open, mean_dd_pct).

    [v62] 평균 낙폭도 같이 준다. Ulcer 는 제곱평균이라 깊은 구간에 가중이 실려
    '평균 몇 % 물속이었나'와 정확히 같지는 않다(원화 29.6년: Ulcer 20.6 / 평균 16.0).
    화면에서 체감값으로 쓰려면 **평균 쪽**을 보여줘야 정확하다.
    """
    v = np.asarray(c.values, dtype=float)
    dd = v / np.maximum.accumulate(v) - 1.0
    ulcer = float(np.sqrt(np.mean(dd ** 2)) * 100)
    mean_dd = float(-np.mean(dd) * 100)

    at_peak = dd >= -1e-12                      # dd[0] == 0 이므로 항상 True 로 시작
    ix = np.arange(len(v))
    last_peak = np.maximum.accumulate(np.where(at_peak, ix, 0))
    day = c.index.values.astype('datetime64[D]').astype('int64')
    spans = day - day[last_peak]
    worst = int(spans.max())
    # 마지막까지 물속이고 그 구간이 최장과 같으면 '아직 진행 중'이다.
    # 동률도 True 다 — 이미 최악과 같은 길이인데 내일 더 길어질 구간이므로.
    worst_open = bool(not at_peak[-1] and int(spans[-1]) == worst)
    return ulcer, worst, worst_open, mean_dd


def bench(D):
    """QLD 계속보유 / QQQ 계속보유 곡선"""
    idx = D['idx']
    qld_only = pd.Series(np.cumprod(1 + D['qldr']), index=idx)
    qqq_only = pd.Series(np.cumprod(1 + np.nan_to_num(D['px'].pct_change().values)), index=idx)
    return qld_only, qqq_only


def rolling_stats(curve, ref, windows=(1, 3, 5, 10, 15), step=5):
    """ref 대비 롤링 승률/초과CAGR. verify.py와 같은 5거래일 스텝."""
    a, b = curve.values, ref.reindex(curve.index).values
    n = len(a); out = {}
    for W in windows:
        m = W * 252
        if m >= n:
            continue
        wins, tot, ex, cg = 0, 0, [], []
        for s in range(0, n - m, step):
            e = s + m
            pa, pb = a[e - 1] / a[s], b[e - 1] / b[s]
            if pa > pb:
                wins += 1
            tot += 1
            ex.append(pa ** (252 / m) - pb ** (252 / m))
            cg.append(pa ** (252 / m) - 1)
        out[W] = dict(win=wins / tot * 100, ex_med=float(np.median(ex)) * 100,
                      ex_mean=float(np.mean(ex)) * 100, ex_worst=float(np.min(ex)) * 100,
                      cagr_med=float(np.median(cg)) * 100, cagr_worst=float(np.min(cg)) * 100,
                      n=tot)
    return out


CRISES = {'닷컴 2000-2002': ('2000-01-01', '2002-12-31'),
          'GFC 2007-2009': ('2007-10-01', '2009-03-31'),
          'GFC반등 2009-2010': ('2009-03-01', '2010-12-31'),
          '코로나 2020': ('2020-02-01', '2020-04-30'),
          '2022 베어': ('2022-01-01', '2022-12-31'),
          '2023-현재': ('2023-01-01', '2026-08-24')}


def seg_ret(curve, s, e):
    z = curve.loc[s:e]
    if len(z) < 2:
        return np.nan
    return (z.iloc[-1] / z.iloc[0] - 1) * 100


BASE_LADDER = [(('dd', EXIT), 1.0, 0)]


def check_baseline(D):
    c, w, t = run(D, BASE_LADDER)
    m = met(c)
    return m, float(m['final'] * (1 - COST) ** 2)
