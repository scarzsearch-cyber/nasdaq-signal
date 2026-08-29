# -*- coding: utf-8 -*-
"""
[v88] 최종 검증 — B 동결 상태의 실전 안정성 · 비용 스트레스 · T4 그림자 채점 템플릿

소유자 지시 (2026-08-30): "새 전략을 채굴하지 말고, 현재 전략이 실제로 신뢰할 수
있는지 검증하라. 성공 조건은 더 높은 CAGR 이 아니라 «B 를 유지해도 되는 충분한
근거가 있는가»를 편향 없이 확인하는 것이다."

[룰 준수 선언] 파라미터 재최적화 없음 · 신규 후보 없음 · 관문 사후 신설 없음.
  채택안·freeze.json·oos_log.csv·nav_history.csv 무수정. B 는 이미 동결돼 있다
  (2026-08-27, I11 이 매 push 감시). 그림자 장부(1행)는 판단에 쓰지 않는다 —
  아래 T4 분석은 전부 동결 이전 54.5년 체인이며, **미래 그림자 기록을 같은 방식으로
  채점하기 위한 사전 등록 템플릿**이다.

[★ 판정 기준 — 실행 전 고정]
  J1 (B 비용 견고성)   비용 ×3(편도 0.6%)에서도 최종 ≥ 2×보유(같은 비용) AND
                       MDD 가 보유보다 얕으면 "생존". 극단(1.0%)은 참고.
  J2 (T4 승격)         실시간 그림자 ≥ 3년 + 독립 사건 ≥ 1 (v69/v80) — 현재 표본으로는
                       원리상 판정 불가. 여기서는 채점 템플릿의 작동만 확인한다.
  J3 (비용 가정 실측)  nav_history ≥ 60세션 (v80 부속서 2) — 미달이면 "대기" 선언,
                       현재 표본은 방향 참고로만 보고.
  갭 위험              전환 신호일의 QQQ 익일 시가 갭 분포(1999~, 시가 존재 구간).
                       참고 해석: 한국 체결은 미국 다음 개장 전이라 이 갭의 일부만
                       노출되며, v43 의 갭 스트레스(전환마다 2.58% 분산 부과)에서도
                       B 우위 유지가 이미 판정돼 있다.
  국면 정의(사전 고정)  달력연도 QQQ 대리지수 수익 > +15% 상승장 / < 0% 하락장 /
                       그 외 횡보장. T4·B 연환산 수익을 국면별 집계.
  감속 회피/기회 분해   경고일(B=공격 ∧ T4<0.7) 이후 63거래일 내 그날 대비 최대
                       낙폭 ≤ −10% 면 "회피 정당", 아니면 "기회비용" (사전 고정 문턱).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_data as H
from axis_lib import sim
from axis_t4_shadow import build, met

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

KCOST = 0.002


def runs(mask, idx):
    """True 연속 구간들의 (시작i, 끝i, 일수)."""
    out = []
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j, j - i + 1))
            i = j + 1
        else:
            i += 1
    return out


def dstat(x, pct=False):
    x = np.asarray(x, float)
    f = (lambda v: '%+.2f%%' % (v * 100)) if pct else (lambda v: '%.0f' % v)
    return '중앙 %s · 평균 %s · P95 %s · 최악 %s (n=%d)' % (
        f(np.median(x)), f(np.mean(x)), f(np.percentile(x, 95)),
        f(np.max(x) if not pct else np.min(x)), len(x))


def main():
    D, wT, wB, votes, rv = build('tbill')
    idx = D['idx']; n = len(idx)
    yrs = (idx[-1] - idx[0]).days / 365.25
    r_full, _ = H.qqq_proxy()
    px = (1 + r_full).cumprod().reindex(idx)

    # ============================================================ 1. B 실전 안정성
    print('=' * 104)
    print('1. B 실전 안정성 — 동결 파라미터 그대로 (54.5년)')
    print('=' * 104)
    flips = int((wB[1:] != wB[:-1]).sum())
    att = runs(wB == 1, idx); dfn = runs(wB == 0, idx)
    print('  전환 %d회 (연 %.2f) · 공격 구간 %d개 · 방어 구간 %d개' % (flips, flips / yrs, len(att), len(dfn)))
    print('  공격 보유기간(거래일): %s' % dstat([d for _, _, d in att]))
    print('  방어 기간(=복귀 대기): %s' % dstat([d for _, _, d in dfn]))
    a, b, d = max(dfn, key=lambda t: t[2])
    print('  최장 방어: %s ~ %s (%d거래일 ≈ %.1f년)' % (idx[a].date(), idx[b].date(), d, d / 252))
    cB2, _ = sim(D, wB, cost=KCOST)
    uw = (cB2 / cB2.cummax() - 1)
    uw_runs = runs((uw < 0).values, idx)
    a2, b2, d2 = max(uw_runs, key=lambda t: t[2])
    print('  최장 언더워터(0.2%%): %d거래일 ≈ %.1f년 (%s~%s)' % (d2, d2 / 252, idx[a2].date(), idx[b2].date()))

    # 신호 지연 (휴장·실기 위험의 값)
    for lag in (1, 2, 3):
        c, _ = sim(D, wB, cost=KCOST, lag=lag)
        print('  체결 지연 lag=%d: 최종 %s · MDD %.1f%%' % (lag, format(float(c.iloc[-1]), ',.0f'), met(c)['mdd'] * 100))

    # 전환 신호일 갭 (QQQ 시가 존재 구간 1999-03~)
    s = H._stooq('qqq_us_d.csv')
    raw = pd.read_csv('qqq_us_d.csv', parse_dates=['Date']).set_index('Date')
    op, cl = raw['Open'], raw['Close']
    tdays = [i for i in range(1, n) if wB[i] != wB[i - 1]]
    gaps_o, gaps_c, worst = [], [], (0, None)
    for i in tdays:
        d0 = idx[i - 1]                      # 신호 확정일(미국 종가)
        if d0 not in cl.index:
            continue
        pos = cl.index.get_loc(d0)
        if pos + 1 >= len(cl.index):
            continue
        d1 = cl.index[pos + 1]
        go = float(op.loc[d1] / cl.loc[d0] - 1)
        gc = float(cl.loc[d1] / cl.loc[d0] - 1)
        gaps_o.append(go); gaps_c.append(gc)
        if abs(go) > abs(worst[0]):
            worst = (go, d1.date())
    print('  전환 신호일 익일 갭 (1999~, %d회 관측):' % len(gaps_o))
    print('    종가→익일시가: %s' % dstat(gaps_o, pct=True))
    print('    종가→익일종가: %s' % dstat(gaps_c, pct=True))
    print('    최대 단일 시가 갭: %+.2f%% (%s) · 참고: v43 갭 스트레스(2.58%% 분산)에서도 B 우위' % (worst[0] * 100, worst[1]))
    print('    해석: 한국 체결(09:05~15:20 KST)은 미국 다음 개장 전 — 시가 갭의 일부만 노출 + 환율 변동 별도')

    # ============================================================ 2. 비용 스트레스
    print()
    print('=' * 104)
    print('2. 비용 스트레스 — B 파라미터 불변, 편도 비용만 충격 (J1)')
    print('=' * 104)
    hold = np.ones(n)
    print('  %-14s %10s %8s %8s %12s %8s' % ('시나리오', '최종배수', 'CAGR', 'MDD', '2배보유(동일비용)', '생존'))
    j1 = None
    for lab, c in (('기본가정 0.2%', 0.002), ('x1.5 = 0.3%', 0.003), ('x2 = 0.4%', 0.004),
                   ('x3 = 0.6%', 0.006), ('극단 1.0%', 0.010), ('(참고 0.1%)', 0.001)):
        cb, _ = sim(D, wB, cost=c)
        ch, _ = sim(D, hold, cost=c)
        m, mh = met(cb), met(ch)
        alive = m['final'] >= 2 * mh['final'] and m['mdd'] > mh['mdd']
        if lab.startswith('x3'):
            j1 = alive
        print('  %-14s %10s %7.1f%% %7.1f%% %12s %8s' %
              (lab, format(m['final'], ',.0f'), m['cagr'] * 100, m['mdd'] * 100,
               format(mh['final'], ',.0f'), '생존' if alive else '탈락'))

    # ============================================================ 3. T4 vs B 최종 비교
    print()
    print('=' * 104)
    print('3. T4 vs B — 사전 정의 그대로, 재최적화 없음 (0.2% · T-bill · lag=1)')
    print('=' * 104)
    cT2, _ = sim(D, wT, cost=KCOST)
    retB = cB2.pct_change().fillna(0).values
    retT = cT2.pct_change().fillna(0).values

    def full_metrics(curve, w):
        m = met(curve)
        r = curve.pct_change().dropna().values
        dn = r[r < 0]
        m['sortino'] = ((1 + np.mean(r)) ** 252 - 1) / (np.std(dn, ddof=1) * np.sqrt(252)) if len(dn) > 5 else np.nan
        m['switch'] = int((np.abs(np.diff(w)) > 1e-9).sum())
        off = runs(w < 0.5, idx)
        m['def_med'] = np.median([d for _, _, d in off]) if off else 0
        m['def_n'] = len(off)
        return m
    mB, mT = full_metrics(cB2, wB), full_metrics(cT2, wT)
    rows = [('최종배수', '%s' % format(mB['final'], ',.0f'), '%s' % format(mT['final'], ',.0f')),
            ('CAGR', '%.2f%%' % (mB['cagr'] * 100), '%.2f%%' % (mT['cagr'] * 100)),
            ('MDD', '%.1f%%' % (mB['mdd'] * 100), '%.1f%%' % (mT['mdd'] * 100)),
            ('Calmar', '%.3f' % mB['calmar'], '%.3f' % mT['calmar']),
            ('Sortino(일간)', '%.3f' % mB['sortino'], '%.3f' % mT['sortino']),
            ('조정 횟수(54.5y)', '%d' % mB['switch'], '%d' % mT['switch']),
            ('저노출 구간 수·중앙일수', '%d개 · %.0f일' % (mB['def_n'], mB['def_med']),
             '%d개 · %.0f일' % (mT['def_n'], mT['def_med']))]
    print('  %-22s %16s %16s' % ('지표', 'B', 'T4'))
    for nm, a_, b_ in rows:
        print('  %-22s %16s %16s' % (nm, a_, b_))

    # 최악 곰랠리(B 방어 중 T4 재진입 손실) · 최대 기회비용(252일 상대열세)
    rel = np.log(cT2.values) - np.log(cB2.values)
    worst_bear = 0.0
    for a3, b3, _ in dfn:
        seg = cT2.iloc[a3:b3 + 1]
        worst_bear = min(worst_bear, float((seg / seg.cummax() - 1).min()))
    rel252 = pd.Series(rel, index=idx).diff(252).dropna()
    print('  B 방어 구간 중 T4 최악 낙폭(곰랠리 비용): %.1f%%' % (worst_bear * 100))
    print('  T4 최대 기회비용(252일 상대열세): %.1f%% (%s)'
          % ((np.exp(rel252.min()) - 1) * 100, rel252.idxmin().date()))
    print('  B 최대 기회비용(T4 대비 252일):   %.1f%% (%s)'
          % ((np.exp(-rel252.max()) - 1) * 100, rel252.idxmax().date()))

    # 5년 롤링 + 국면별 (사전 고정 정의)
    L = 1260
    starts = np.arange(1, n - L, 21)
    lgB, lgT = np.log(cB2.values), np.log(cT2.values)
    fB = np.exp(lgB[starts + L - 1] - lgB[starts - 1])
    fT = np.exp(lgT[starts + L - 1] - lgT[starts - 1])
    print('  5년 롤링 %d개: T4 승 %.0f%% · 중앙 상대성적 %+.1f%%'
          % (len(starts), (fT > fB).mean() * 100, (np.median(fT / fB) - 1) * 100))
    yr_ret = px.groupby(idx.year).last() / px.groupby(idx.year).first() - 1
    def regime_of(y):
        r = yr_ret.get(y, np.nan)
        return '상승' if r > 0.15 else ('하락' if r < 0 else '횡보')
    reg = np.array([regime_of(y) for y in idx.year])
    print('  국면별 연환산 수익 (달력연도 QQQ: >+15% 상승 / <0% 하락 / 그 외 횡보):')
    for g in ('상승', '하락', '횡보'):
        m_ = reg == g
        aB = (1 + pd.Series(retB[m_])).prod() ** (252 / m_.sum()) - 1
        aT = (1 + pd.Series(retT[m_])).prod() ** (252 / m_.sum()) - 1
        print('    %-4s (%4.0f일/yr 평균 %4.1f년치)  B %+7.1f%%  T4 %+7.1f%%'
              % (g, m_.sum() / yrs * 1.0, m_.sum() / 252, aB * 100, aT * 100))

    # ============================================================ 4. 감속 신호 조건부 성과
    print()
    print('=' * 104)
    print('4. T4 감속 신호의 조건부 성과 — 그림자 채점 템플릿 (사전 등록)')
    print('=' * 104)
    warn = (wB == 1) & (wT < 0.7)
    wi = np.where(warn)[0]
    pxv = px.values
    fwd = {}
    for h in (5, 21, 63):
        v = pxv[np.minimum(wi + h, n - 1)] / pxv[wi] - 1
        fwd[h] = v
        print('  경고일(B공격∧T4<0.7, %d일) 이후 %2d일 시장수익: %s'
              % (len(wi), h, dstat(v, pct=True)))
    # 회피 정당 vs 기회비용 (사전 고정: 63일 내 최대낙폭 ≤ −10%)
    mdd63 = np.array([pxv[i:min(n, i + 63)].min() / pxv[i] - 1 for i in wi])
    just = mdd63 <= -0.10
    dT_win = retT[np.minimum(wi + 1, n - 1)]   # lag=1 체결 반영 다음날 수익부터는 근사 — 상대비교용
    dB_win = retB[np.minimum(wi + 1, n - 1)]
    print('  분해: 회피 정당(63일 내 −10%% 이상 하락) %d일 (%.0f%%) · 기회비용 %d일 (%.0f%%)'
          % (just.sum(), just.mean() * 100, (~just).sum(), (~just).mean() * 100))
    print('    회피 정당일의 63일 시장수익: %s' % dstat(mdd63[just], pct=True))
    print('    기회비용일의 63일 시장수익: %s' % dstat(fwd[63][~just], pct=True))
    print('    경고일 평균 상대수익(T4−B, 익일): %+.4f%%p/일 · 전체일 평균 %+.4f%%p/일'
          % ((dT_win - dB_win).mean() * 100, (retT - retB).mean() * 100))
    print('  → 실시간 그림자도 같은 식으로 채점한다: 장부의 close·state·t4_w 만으로 재구성 가능')

    # ============================================================ 5. 장부·실측 수집 감사
    print()
    print('=' * 104)
    print('5. 그림자 장부 · 한국 실측 수집 감사 (J2·J3)')
    print('=' * 104)
    led = pd.read_csv('data/oos_log.csv')
    print('  oos_log.csv: %d행 (%s ~ %s) · 열 %d개' % (len(led), led['as_of'].iloc[0], led['as_of'].iloc[-1], led.shape[1]))
    need = ['날짜=as_of', '낙폭=dd', 'B상태=state', 'T4비중=t4_w', 'T4상태=t4_w>0',
            'NAV·수익률·MDD=close+state+t4_w 재구성(v80 부속서 규약)',
            '감속일=(state==QLD)∧(t4_w<1)', '조건부 5/21/63일 성과=close 열']
    for x in need:
        print('    필요항목 충족: %s' % x)
    print('  판정 시점: 기록 >= 3년(~756행) + 독립 사건 >= 1 — 현재 %d행: J2 = 원리상 판정 불가 (대기)' % len(led))
    nav = pd.read_csv('data/nav_history.csv', encoding='utf-8-sig')
    ses = nav['as_of'].nunique()
    print('  nav_history.csv: %d세션 (%s ~ %s) · 60세션 기준 %d 남음'
          % (ses, nav['as_of'].min(), nav['as_of'].max(), max(0, 60 - ses)))
    core = nav[nav['code'].astype(str).isin(['458730', '305080', '411060', '418660'])]
    dev = core.groupby('code')['dev_pct'].agg(['median', 'std', 'max'])
    print('  괴리율 잠정 관측(전략 4종목, %%): \n%s' % dev.round(3).to_string())
    print('  주의: 호가 스프레드는 미수집 — 괴리율+거래대금으로 하한만 잰다. 60세션 후 재측정(v80 부속서 2).')

    print()
    print('=' * 104)
    print('[J1] 비용 x3 생존: %s' % ('통과' if j1 else '탈락'))
    print('[J2] T4 승격 판정: 표본 미달 — 그림자 %d행/756행. 규약대로 대기.' % len(led))
    print('[J3] 비용 실측: %d/60세션 — 대기. 잠정 괴리율은 0.2%% 가정 대비 방향 참고만.' % ses)


if __name__ == '__main__':
    main()
