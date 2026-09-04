# -*- coding: utf-8 -*-
"""
[사실 확인] QQQ ↔ 배당 다리(SCHD) — 상관 · 섹터 · 「2008 처럼 같이 빠지나」 (2026-09-03, 소유자 질문 3건)

소유자 질문:
  ① 「그냥 2배보다도 전략이 졌다는 거지?」 (04 §5-30 F8 표에 대한 되물음)
  ② 「QQQ 와 SCHD 의 종목별 상관계수 또는 섹터 차이 같은 것도 분석할 수 있으려나?」
  ③ 「SCHD 는 금융위기 당시 고배당주엔 금융주가 많았기 때문에 07~09 금융위기에서 QQQ 와 같이 하락했잖아? 현 시점에도 그러니?」

⚠ **전략 무접촉** — 규칙·비중·상품을 바꾸지 않는다. 후보를 만들지 않는다. 이 파일은 사실만 잰다(04 §5-16 A 의 상관표를 종목·섹터 쪽으로 넓힌 것).

★ **먼저 알아야 할 사실 (③ 의 전제와 관련)**: **SCHD 는 2011-10-20 상장이라 2008 에 존재하지 않았다.**
  엔진이 2011 이전 방어 배당 다리로 쓰는 것은 Kenneth French **BE/ME Hi30 가치주**(총수익) 대리 시계열이다(`hist_defensive.py` 머리에 명시).
  따라서 「SCHD 가 2008 에 같이 빠졌다」는 **실물 관측이 아니라 대리 시계열의 성질**이다. 여기서는 그 시절 실재했던 **DVY**(iShares Select Dividend,
  2003~ · 고배당 가중 = 당시 금융주 비중이 컸던 바로 그 유형)로 실물을 직접 재고, 오늘의 SCHD 와 비교한다.

무엇을 재나:
  A. 전체 기간 B vs 2배 계속보유 (질문 ①의 정확한 답 — 04 §5-30 F8 은 **사건 구간 안**의 비교였다)
  B. 상관: 252일 이동 상관(QQQ↔SCHD/DVY) · 평시 vs 폭락 중 · 위기별
  C. 섹터: 수익률 기반 스타일 분석(11개 섹터 ETF에 대한 비음수·합1 회귀) — QQQ · SCHD · DVY 의 내재 섹터 배합
  D. 「2008 처럼」: GFC 창에서 DVY·대리·QQQ 낙폭 vs 최근 위기(2020·2022·2025)에서 SCHD·QQQ 낙폭 · 금융(XLF) 베타의 시대 변화

예측 (결과 보기 전 · 틀리면 그대로 적는다 §-1 ⑦):
  P1 GFC 창에서 **DVY 낙폭이 QQQ 보다 깊다**(통념 확인).
  P2 오늘 SCHD 의 내재 금융 비중은 DVY 2008 보다 **낮다**(퀄리티 스크린) — 다만 0 은 아니고 15~25%.
  P3 최근 위기(2020·2022·2025) 셋 다 SCHD 낙폭이 QQQ 보다 **얕다**.
  P4 상관은 평시보다 **폭락 중에 오른다**(양쪽 다) — 04 §5-16 A 의 「방어 중 +0.775」와 같은 방향.
  P5 QQQ 와 SCHD 의 섹터 겹침은 작다 — QQQ 는 기술·통신·경기소비, SCHD 는 금융·헬스케어·필수소비·산업.

실행: python research/schd_qqq_overlap.py   (약 20초 · 네트워크 0 — 캐시만 · 파일 쓰기 0)
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

L = '=' * 106
SECT = {'XLK': '기술', 'XLC': '통신', 'XLY': '경기소비', 'XLF': '금융', 'XLV': '헬스케어',
        'XLP': '필수소비', 'XLI': '산업', 'XLE': '에너지', 'XLU': '유틸리티', 'XLB': '소재', 'XLRE': '부동산'}
CRISES = [('GFC 2007~09', '2007-10-31', '2009-03-09'),
          ('코로나 2020', '2020-02-19', '2020-03-23'),
          ('금리 2022', '2021-11-19', '2022-10-14'),
          ('2025', '2025-02-19', '2025-04-08')]


def load(sym, root=False):
    p = f'{sym}_us_d.csv' if root else f'data/hist/yahoo_{sym}.csv'
    d = pd.read_csv(p)
    date_col = 'Date' if 'Date' in d.columns else d.columns[0]
    # data/hist 의 Yahoo 캐시는 배당·분할을 반영한 AdjClose 한 열만 가진다.
    # 루트의 구형 OHLC 파일과 형식이 다르므로 Close 고정은 실행 즉시 깨진다.
    price_col = next((c for c in ('AdjClose', 'Adj Close', 'Close', 'close') if c in d.columns), None)
    if price_col is None:
        raise ValueError(f'{p}: 가격 열이 없다 (열={list(d.columns)})')
    dates = pd.to_datetime(d[date_col], errors='coerce')
    prices = pd.to_numeric(d[price_col], errors='coerce')
    if dates.isna().any() or not np.isfinite(prices).all():
        raise ValueError(f'{p}: 잘못된 날짜 또는 결측·비유한 가격이 있다')
    out = pd.Series(prices.values, index=dates, name=sym).sort_index()
    out = out[~out.index.duplicated(keep='last')]
    if len(out) < 2 or (out <= 0).any():
        raise ValueError(f'{p}: 유효한 양수 가격 계열이 아니다')
    return out


def nnls(X, y, iters=200):
    """Lawson-Hanson 비음수 최소자승 (scipy 없이). 활성집합법."""
    m, n = X.shape
    P = np.zeros(n, bool); w = np.zeros(n)
    XtX = X.T @ X; Xty = X.T @ y
    for _ in range(iters):
        g = Xty - XtX @ w
        g[P] = -np.inf
        j = int(np.argmax(g))
        if g[j] <= 1e-12:
            break
        P[j] = True
        for _ in range(60):
            s = np.zeros(n)
            A = XtX[np.ix_(P, P)]
            s[P] = np.linalg.lstsq(A + 1e-12 * np.eye(A.shape[0]), Xty[P], rcond=None)[0]
            if s[P].min() > 0:
                w = s; break
            neg = P & (s <= 0)
            alpha = float(np.min(w[neg] / (w[neg] - s[neg] + 1e-300)))
            w = w + alpha * (s - w)
            P &= w > 1e-12
        else:
            break
    return w


def simplex_nnls(Y, X, lam=None):
    """비음수 + 합≈1 제약 최소자승 (수익률 기반 스타일 분석).
    합 제약은 표준 기법대로 X 에 lam·1 행, Y 에 lam 을 덧붙여 건다."""
    n, k = X.shape
    sc = float(np.sqrt(np.mean(X ** 2))) or 1.0
    lam = lam if lam is not None else sc * np.sqrt(n) * 50
    Xa = np.vstack([X, np.full((1, k), lam)])
    Ya = np.concatenate([Y, [lam]])
    w = nnls(Xa, Ya)
    r2 = 1 - np.var(Y - X @ w) / np.var(Y)
    return w, float(r2)


def style(name, r, sec, start, end):
    """창 안에서 **공통 거래일만** 쓴다. ⚠ 초판 버그: 대상 자산의 날짜 하나라도 섹터에 없으면 그 섹터를
    통째로 제외해 QQQ 에서 기술(XLK)이 빠졌다(R² 0.26). 교집합으로 맞춘다."""
    w0 = r.dropna()
    w0 = w0[(w0.index >= start) & (w0.index <= end)]
    # 창 안에서 결측이 전혀 없는 섹터만 후보로 두되, 판정은 **교집합 인덱스**에서 한다
    cols = [c for c in sec.columns if sec[c].reindex(w0.index).notna().mean() > 0.98]
    if not cols:
        return None
    sub = sec[cols].reindex(w0.index)
    ix = sub.dropna().index
    if len(ix) < 120:
        return None
    w, r2 = simplex_nnls(w0.reindex(ix).values, sub.loc[ix].values)
    top = sorted(zip(cols, w), key=lambda t: -t[1])
    return top, r2, len(ix)


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        G, _ = EC.selfcheck()
    IDX = pd.DatetimeIndex(G.idx)
    PX = pd.Series(G.D['px'], index=IDX).astype(float)
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float)); MIX = np.nan_to_num(np.asarray(G.Dm['schdr'], float))

    # ── A. 질문 ① ────────────────────────────────────────────────────────────
    print(L); print('A. 「그냥 2배보다도 전략이 졌다는 거지?」 — 전체 기간에서는 **아니다**'); print(L)
    wB = EC.rule_dd(PX, -0.16, -0.16)
    cB = pd.Series(np.asarray(EC.sim2(wB, QLDR, MIX), float), index=IDX)
    c2 = pd.Series(np.cumprod(1 + QLDR), index=IDX)
    mB = EC.fullmet(cB.values, idx=IDX); m2 = EC.fullmet(c2.values, idx=IDX)
    print(f"  {'':22s}{'최종배수':>12}{'CAGR':>9}{'MDD':>9}{'Calmar':>9}{'20년 p05':>10}")
    print(f"  {'B (−16/−16 전환)':22s}{mB['final']:>12,.0f}{mB['cagr']:>8.2f}%{mB['mdd']:>8.1f}%{mB['calmar']:>9.3f}{EC.p05_20y(cB.values):>9.1f}배")
    print(f"  {'2배 계속보유':22s}{m2['final']:>12,.0f}{m2['cagr']:>8.2f}%{m2['mdd']:>8.1f}%{m2['calmar']:>9.3f}{EC.p05_20y(c2.values):>9.1f}배")
    print(f'  → 54년 전체로는 B 가 2배 보유의 **{mB["final"]/m2["final"]:,.0f}배**. 04 §5-30 의 표는 **사건 구간 안**(고점→회복)만 잘라 본 것이다.')
    print('  즉 「빠르게 무너지고 빠르게 되돌아온 구간」만 떼어 보면 B 가 지는 사건이 있다는 뜻이고, 전체 성적이 아니다.')
    yr = pd.Series(IDX).dt.year.values
    print('\n  10년 단위로 나눠 본 같은 비교(각 구간 시작=1):')
    for a, b in ((1972, 1979), (1980, 1989), (1990, 1999), (2000, 2009), (2010, 2019), (2020, 2026)):
        m = (yr >= a) & (yr <= b)
        if m.sum() < 252:
            continue
        x1 = cB.values[m]; x2 = c2.values[m]
        print(f'    {a}~{b}: B {x1[-1]/x1[0]:>9.2f}배 · 2배보유 {x2[-1]/x2[0]:>9.2f}배 · B/2배 {(x1[-1]/x1[0])/(x2[-1]/x2[0]):>6.2f}')

    # ── B. 상관 ──────────────────────────────────────────────────────────────
    print('\n' + L); print('B. QQQ ↔ 배당 ETF 상관 — 평시와 폭락 중'); print(L)
    qqq = load('QQQ'); schd = load('SCHD'); dvy = load('DVY')
    rq = qqq.pct_change(); rs = schd.pct_change(); rd = dvy.pct_change()
    print('  ※ 종목별(개별 주식) 상관은 이 저장소에 보유종목 데이터가 없어 못 낸다 — 대신 **수익률 상관 + 수익률 기반 섹터 추정**으로 답한다(C).')
    for nm, r2s, lbl in (('SCHD', rs, 'QQQ↔SCHD'), ('DVY', rd, 'QQQ↔DVY')):
        ix = rq.index.intersection(r2s.index)
        a, b = rq.reindex(ix).dropna(), r2s.reindex(ix).dropna()
        ix = a.index.intersection(b.index); a, b = a[ix], b[ix]
        allc = float(np.corrcoef(a, b)[0, 1])
        q05 = a.quantile(0.05)
        worst = a <= q05
        print(f'  {lbl:10s} 전체 {allc:+.3f} ({ix[0].date()}~{ix[-1].date()}, {len(ix)}일) · '
              f'QQQ 최악 5% 일 {float(np.corrcoef(a[worst], b[worst])[0,1]):+.3f} · '
              f'평시(나머지) {float(np.corrcoef(a[~worst], b[~worst])[0,1]):+.3f}')
    print('\n  252일 이동 상관 QQQ↔SCHD (연말 기준):')
    ix = rq.index.intersection(rs.index)
    roll = rq.reindex(ix).rolling(252).corr(rs.reindex(ix))
    for y in range(2012, 2027):
        v = roll[roll.index.year == y]
        if len(v.dropna()):
            print(f'    {y}: {v.dropna().iloc[-1]:+.3f}   (연중 최저 {v.min():+.3f} · 최고 {v.max():+.3f})')

    # ── C. 섹터 ──────────────────────────────────────────────────────────────
    print('\n' + L); print('C. 섹터 차이 — 수익률 기반 스타일 분석(11개 섹터 ETF · 비음수·합1)'); print(L)
    sec = pd.DataFrame({s: load(s).pct_change() for s in SECT})
    for lbl, r, s0, s1 in (('QQQ  (최근 3년)', rq, '2023-09-01', '2026-08-31'),
                           ('SCHD (최근 3년)', rs, '2023-09-01', '2026-08-31'),
                           ('DVY  (최근 3년)', rd, '2023-09-01', '2026-08-31'),
                           ('DVY  (2007~09 위기)', rd, '2007-01-01', '2009-06-30'),
                           ('QQQ  (2007~09 위기)', rq, '2007-01-01', '2009-06-30')):
        out = style(lbl, r, sec, s0, s1)
        if not out:
            print(f'  {lbl}: 자료 부족'); continue
        top, r2, n = out
        line = ' · '.join(f'{SECT[c]} {w*100:.0f}%' for c, w in top if w > 0.02)
        print(f'  {lbl:22s} R²={r2:.2f} n={n}  →  {line}')
    print('\n  ※ 이것은 보유종목 공시가 아니라 **수익률로 역추정한 배합**이다 — 실제 비중과 몇 %p 다를 수 있다(R² 로 신뢰도 판단).')
    print('    특히 SCHD 의 「부동산」은 그 지수가 리츠를 제외하는 것으로 알려져 있어 **금리 민감도가 대신 잡힌 것**일 가능성이 크다 — 저장소 안에서 검증 불가.')
    a = dict((c, w) for c, w in style('q', rq, sec, '2023-09-01', '2026-08-31')[0])
    b = dict((c, w) for c, w in style('s', rs, sec, '2023-09-01', '2026-08-31')[0])
    dv09 = dict((c, w) for c, w in style('d', rd, sec, '2007-01-01', '2009-06-30')[0])
    ov = sum(min(a.get(k, 0), b.get(k, 0)) for k in SECT)
    g3 = ('XLK', 'XLC', 'XLY')
    print(f'\n  **섹터 겹침(min 합) = {ov*100:.0f}%** — QQQ 는 기술·통신·경기소비에 {sum(a.get(k,0) for k in g3)*100:.0f}% 가 몰려 있고 '
          f'SCHD 의 같은 셋 합은 {sum(b.get(k,0) for k in g3)*100:.0f}% 다. 같은 시장을 사지만 **다른 섹터를 산다**.')
    print(f'  금융 비중 대조: **DVY 2007~09 {dv09.get("XLF",0)*100:.0f}%** vs **SCHD 오늘 {b.get("XLF",0)*100:.0f}%** — '
          f'③ 의 「고배당 = 금융 과중」은 DVY 형의 성질이고 오늘의 SCHD 에는 그만큼 없다.')

    # ── D. 「2008 처럼」 ──────────────────────────────────────────────────────
    print('\n' + L); print('D. 「2008 처럼 같이 빠지나」 — 위기별 낙폭과 금융(XLF) 베타'); print(L)
    xlf = load('XLF'); rx = xlf.pct_change()
    print(f"  {'위기':<14}{'QQQ':>9}{'DVY':>9}{'SCHD':>9}{'XLF':>9}   창")
    for nm, s0, s1 in CRISES:
        row = f'  {nm:<14}'
        for ser in (qqq, dvy, schd, xlf):
            seg = ser[(ser.index >= s0) & (ser.index <= s1)]
            row += f'{(seg.iloc[-1]/seg.iloc[0]-1)*100:>8.1f}%' if len(seg) > 2 else f'{"—":>9}'
        print(row + f'   {s0}~{s1}')
    print('\n  금융(XLF) 베타 — 회귀 기울기 (배당 ETF 수익률 ~ XLF 수익률):')
    for lbl, r, s0, s1 in (('DVY 2007~09', rd, '2007-01-01', '2009-06-30'),
                           ('DVY 최근 3년', rd, '2023-09-01', '2026-08-31'),
                           ('SCHD 최근 3년', rs, '2023-09-01', '2026-08-31'),
                           ('SCHD 2012~15', rs, '2012-01-01', '2015-12-31'),
                           ('QQQ 최근 3년', rq, '2023-09-01', '2026-08-31')):
        ix = r.index.intersection(rx.index)
        ix = ix[(ix >= s0) & (ix <= s1)]
        a = r.reindex(ix).dropna(); b = rx.reindex(ix).dropna()
        ix = a.index.intersection(b.index)
        if len(ix) < 120:
            print(f'    {lbl:16s} 자료 부족'); continue
        a, b = a[ix], b[ix]
        # 분자·분모의 자유도를 맞춘다. np.cov 기본(ddof=1)을 np.var 기본(ddof=0)로
        # 나누면 표본 수 n/(n-1)만큼 베타가 부풀었다.
        beta = float(np.cov(a, b, ddof=1)[0, 1] / np.var(b, ddof=1))
        print(f'    {lbl:16s} β(XLF) = {beta:.2f} · 상관 {float(np.corrcoef(a,b)[0,1]):+.2f} · n={len(ix)}')

    print('\n' + L); print('예측 대조'); print(L)
    g = qqq[(qqq.index >= '2007-10-31') & (qqq.index <= '2009-03-09')]
    dv = dvy[(dvy.index >= '2007-10-31') & (dvy.index <= '2009-03-09')]
    p1 = (dv.iloc[-1] / dv.iloc[0]) < (g.iloc[-1] / g.iloc[0])
    print(f'  P1 GFC 창에서 DVY 가 QQQ 보다 깊다 → {"맞음" if p1 else "**틀림**"} (DVY {(dv.iloc[-1]/dv.iloc[0]-1)*100:.1f}% vs QQQ {(g.iloc[-1]/g.iloc[0]-1)*100:.1f}%)')
    print('  P2~P5 는 위 표에서 직접 대조 — 판정문은 04 §5-31 에 적는다.')

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 2011 이전 방어 배당 다리는 **대리 시계열**(French BE/ME Hi30)이다 — 그 대리가 DVY 형(금융 과중)인가 SCHD 형(퀄리티)인가에 따라')
    print('      04 의 GFC 방어 성적(−59.7%)이 낙관/비관 어느 쪽으로 치우치는지. 겹침 구간이 없어 직접 검증은 불가 → §7 대장 후보.')
    print('  Q-b 섹터 배합이 시대에 따라 바뀐다면 「방어 다리의 성질」도 바뀐다 — 그러나 규칙은 상품을 고정한다(§2). 감시 대상인가 아닌가는 소유자 판단.')


if __name__ == '__main__':
    main()
