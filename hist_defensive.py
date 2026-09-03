"""
남은 데이터 과제 ① + ④  —  방어자산(SCHD)의 장기 대체 시계열

[문제]
지금까지 SCHD 실물이 없는 2011-10 이전 구간은 '연 2% 고정 현금'으로 채웠다.
그런데 SCHD 는 현금이 아니라 '고배당 + 퀄리티 주식' 펀드다. 2000-2002 처럼
나스닥이 -78% 나던 구간에서 가치·배당주는 오히려 올랐다. 즉 연 2% 현금 규약은
방어자산 성과를 체계적으로 과소평가하고, 그 왜곡은 방어자산에 오래 머무는
A(-16/-11)에게 불리하게 작용한다.

[대체 시계열]  전부 실제 역사 데이터. 새 지표가 아니라 '방어자산 대체'일 뿐이다.
  cash2  : 연 2% 고정            (기존 규약 / 기준선)
  tbill  : FRED DTB3 3개월 T-bill (1954~, 실제 무위험 현금)          ... 과제 ④
  value  : Kenneth French  BE/ME Hi 30 (VW, 배당재투자 총수익, 1926~) ... 과제 ①
  divm   : Kenneth French  D/P  Hi 30 (VW, 월간) — value 대리의 타당성 교차검증용

[한계 — 반드시 명시]
  - BE/ME Hi30 은 '장부/시가' 가치주다. SCHD 는 '고배당 + ROE/FCF-부채/배당성장'
    퀄리티 스크린이 붙은 배당주다. 같은 계열이지만 같은 지수가 아니다.
  - French 포트폴리오는 운용보수·거래비용이 0 이다. SCHD 실물은 0.06%/yr.
    -> 대리구간이 실물보다 유리하게 나오는 편향이 있다(보정치도 함께 보고).
  - French 일간 파일은 2026-06-30 까지다. 그 이후는 SCHD 실물 구간이라 무관.
  - DTB3 는 discount basis 연율이다. 기존 규약대로 /252 로 일할 환산한다.
"""
import numpy as np
import pandas as pd
import hist_data as H

FF_DIR = 'data/hist/ff_tmp'
SCHD_START = '2011-10-20'      # SCHD 실물 상장


# ------------------------------------------------------------------ French 파서
def _ensure_ff():
    """ff_tmp/ 가 없으면 커밋된 zip 에서 풀어 만든다.
    추출본(10MB)은 .gitignore 대상이고 zip(2MB)만 저장소에 있다."""
    import glob, os, zipfile
    if os.path.isdir(FF_DIR) and glob.glob(f'{FF_DIR}/*.csv'):
        return
    os.makedirs(FF_DIR, exist_ok=True)
    zips = sorted(glob.glob('data/hist/ff_*.zip'))
    if not zips:
        raise FileNotFoundError('data/hist/ff_*.zip 이 없다 - French 원자료를 다시 받아야 한다')
    for z in zips:
        with zipfile.ZipFile(z) as f:
            f.extractall(FF_DIR)
    print('[hist_defensive] %s 에 French 원자료 %d개 zip 을 풀었다' % (FF_DIR, len(zips)))


def _ff_block(path, header_line, n_rows=None, col=None, min_rows=500):
    """French CSV 의 한 블록을 읽는다. header_line 은 1-based 컬럼헤더 줄번호.

    [코드리뷰 2026-09-04] header_line·n_rows 는 특정 판본의 줄번호에 묶인 값이다.
    원자료가 재발행돼 헤더가 밀리면 skiprows 가 어긋나 **다른 블록**(동일가중·연간
    등)을 읽는데, dt 정규식은 그런 블록도 통과시키므로 예외 없이 엉뚱한 수익률이
    방어자산으로 들어간다. 그래서 읽은 뒤 판본을 검증한다 — 조용히 틀리느니 죽는다.
    """
    _ensure_ff()
    d = pd.read_csv(path, skiprows=header_line - 1, nrows=n_rows)
    d.columns = ['dt'] + [c.strip() for c in d.columns[1:]]
    d['dt'] = d['dt'].astype(str).str.strip()
    d = d[d['dt'].str.fullmatch(r'\d{6,8}')]
    if len(d) < min_rows:
        raise ValueError('%s: header_line=%s 로 읽은 블록이 %d행뿐이다(기대 >=%d) - '
                         '원자료 판본이 바뀌었는지 확인하라' % (path, header_line, len(d), min_rows))
    if col is not None and col not in d.columns:
        raise ValueError('%s: header_line=%s 블록에 %r 컬럼이 없다(있는 것: %s) - '
                         '원자료 판본이 바뀌었는지 확인하라'
                         % (path, header_line, col, list(d.columns[1:6])))
    w = d['dt'].str.len().unique()
    if len(w) != 1:
        raise ValueError('%s: 날짜 자릿수가 섞여 있다(%s) - 블록 경계가 어긋났다'
                         % (path, sorted(w)))
    return d


def ff_beme_daily(col='Hi 30'):
    """BE/ME 분위 포트폴리오 일간 가치가중 수익률 (총수익, %)."""
    p = f'{FF_DIR}/Portfolios_Formed_on_BE-ME_Daily.csv'
    d = _ff_block(p, 24, n_rows=26299 - 25, col=col, min_rows=20000)
    r = pd.Series(d[col].astype(float).values / 100.0,
                  index=pd.to_datetime(d['dt'], format='%Y%m%d'))
    return r[r > -0.9].sort_index()        # -99.99 결측 제거


def ff_dp_monthly(col='Hi 30'):
    """D/P 분위 포트폴리오 월간 가치가중 수익률 (총수익, %)."""
    p = f'{FF_DIR}/Portfolios_Formed_on_D-P.csv'
    d = _ff_block(p, 20, n_rows=1211 - 21, col=col, min_rows=900)
    r = pd.Series(d[col].astype(float).values / 100.0,
                  index=pd.to_datetime(d['dt'], format='%Y%m'))
    return r[r > -0.9].sort_index()


def ff_div_daily(fee=0.0):
    """
    [클로드 자율 추가 규약 1] 배당수익률 포트폴리오의 '일간' 대리 시계열.

    왜 필요한가: SCHD 는 배당(D/P) 계열인데 French 의 D/P 포트폴리오는 월간뿐이고,
    일간으로 있는 BE/ME Hi30 은 SCHD 보다 CAGR 이 1.7%p 높고 변동성이 3.7%p 크다
    (proxy_quality() 참조). 그대로 쓰면 방어자산이 실제 SCHD 보다 과하게 좋아져
    방어자산에 오래 머무는 A(-16/-11)에게 유리한 방향으로 결과가 왜곡된다.

    무엇을 하는가: BE/ME Hi30 일간 수익률의 '월내 모양'은 그대로 두고, 각 달의
    로그수익률 합이 D/P Hi30 의 실제 월간 수익률과 일치하도록 일간 로그수익률에
    상수를 더한다(표준적 시간분해). 새 지표를 만드는 것이 아니라, 실재하는 두
    French 시계열을 결합해 '일간 배당주 총수익'을 복원하는 것이다.
    검증: SCHD 겹침구간 CAGR/변동성이 실물에 얼마나 근접하는지 proxy_quality2() 로 보고.
    """
    d = ff_beme_daily()
    m = ff_dp_monthly()
    ld = np.log1p(d)
    key = ld.index.to_period('M')
    tgt = np.log1p(m)
    tgt.index = tgt.index.to_period('M')
    cnt = ld.groupby(key).count()
    cur = ld.groupby(key).sum()
    common = cur.index.intersection(tgt.index)
    adj = ((tgt.reindex(common) - cur.reindex(common)) / cnt.reindex(common))
    out = ld + pd.Series(key.map(adj).values, index=ld.index).fillna(0.0)
    return np.expm1(out) - fee / 252


def proxy_quality2():
    """세 대리안이 SCHD 실물을 얼마나 재현하는지 (겹침구간 직접 비교)."""
    schd = H._stooq('schd_us_d.csv').pct_change().dropna()
    cands = {'BE/ME Hi30 원본': ff_beme_daily(),
             'D/P 월간정합 일간(자율규약1)': ff_div_daily(),
             'D/P 월간정합 -0.06%보수': ff_div_daily(fee=0.0006)}
    rows = []
    for nm, v in cands.items():
        ix = schd.index.intersection(v.index); ix = ix[ix >= SCHD_START]
        a, b = schd.reindex(ix), v.reindex(ix)
        rows.append(dict(proxy=nm, n=len(ix), corr=float(np.corrcoef(a, b)[0, 1]),
                         cagr_schd=float((1 + a).prod() ** (252 / len(a)) - 1),
                         cagr_proxy=float((1 + b).prod() ** (252 / len(b)) - 1),
                         vol_schd=float(a.std() * np.sqrt(252)),
                         vol_proxy=float(b.std() * np.sqrt(252))))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 방어자산 시계열
def defensive(idx, kind, fee=0.0):
    """
    idx 위에서 평가한 방어자산 일간수익률.
    SCHD 실물 구간(2011-10-20~)은 어떤 kind 든 항상 SCHD 실물을 쓴다
    (기존 규약 유지 — 실물이 있으면 실물이 우선).
    kind='pure_*' 는 전구간을 그 자산으로 채운다(SCHD 피신 vs 현금 피신 비교용).
    """
    schd = H._stooq('schd_us_d.csv')
    sr = schd.reindex(idx).pct_change()

    if kind in ('cash2', 'pure_cash2'):
        base = pd.Series(H.CASH_RATE / 252, index=idx)
    elif kind in ('tbill', 'pure_tbill'):
        base = pd.Series(H.tbill_daily(idx), index=idx)
    elif kind in ('chain', 'pure_chain', 'chainmix', 'pure_chainmix'):
        import hist_divetf as DE
        lv = (1 + DE.defensive_chain('mix' if 'mix' in kind else 'dvy')).cumprod()
        lv = lv.reindex(idx.union(lv.index)).ffill().reindex(idx)
        base = lv.pct_change().fillna(0.0) - fee / 252
        return base.fillna(0.0).values.astype(float)      # 체인은 이미 실물 우선
    elif kind in ('div', 'pure_div'):
        lv = (1 + ff_div_daily()).cumprod()
        lv = lv.reindex(idx.union(lv.index)).ffill().reindex(idx)
        base = lv.pct_change().fillna(0.0) - fee / 252
    elif kind in ('value', 'pure_value'):
        lv = (1 + ff_beme_daily()).cumprod()
        lv = lv.reindex(idx.union(lv.index)).ffill().reindex(idx)
        base = lv.pct_change().fillna(0.0) - fee / 252
    else:
        raise ValueError(kind)

    if kind.startswith('pure_'):
        return base.fillna(0.0).values.astype(float)
    return sr.where(sr.notna(), base).fillna(0.0).values.astype(float)


def build(kind='cash2', start=H.START_EXT, fee=0.0):
    """hist_data.build_ext 와 동일하되 방어자산만 교체한다."""
    D = H.build_ext(cash='fixed2', start=start)
    D = dict(D)
    D['schdr'] = defensive(D['idx'], kind, fee=fee)
    D['defensive'] = kind
    return D


# ------------------------------------------------------------------ 대리 타당성
def proxy_quality():
    """SCHD 실물 겹침 구간에서 BE/ME Hi30 이 얼마나 SCHD 를 닮았는가."""
    schd = H._stooq('schd_us_d.csv').pct_change().dropna()
    v = ff_beme_daily()
    ix = schd.index.intersection(v.index)
    ix = ix[ix >= SCHD_START]
    a, b = schd.reindex(ix), v.reindex(ix)
    dp = ff_dp_monthly()
    sm = (1 + schd).resample('ME').prod() - 1
    vm = (1 + v).resample('ME').prod() - 1
    mi = sm.index.intersection(dp.index.to_period('M').to_timestamp('M'))
    dpm = dp.copy(); dpm.index = dpm.index.to_period('M').to_timestamp('M')
    mi = mi[mi >= SCHD_START]
    rows = [
        dict(pair='SCHD vs BE/ME Hi30 (일간)', n=len(ix), corr=float(np.corrcoef(a, b)[0, 1]),
             cagr_a=float((1 + a).prod() ** (252 / len(a)) - 1),
             cagr_b=float((1 + b).prod() ** (252 / len(b)) - 1),
             vol_a=float(a.std() * np.sqrt(252)), vol_b=float(b.std() * np.sqrt(252))),
        dict(pair='SCHD vs BE/ME Hi30 (월간)', n=len(mi),
             corr=float(np.corrcoef(sm.reindex(mi), vm.reindex(mi))[0, 1]),
             cagr_a=float((1 + sm.reindex(mi)).prod() ** (12 / len(mi)) - 1),
             cagr_b=float((1 + vm.reindex(mi)).prod() ** (12 / len(mi)) - 1),
             vol_a=float(sm.reindex(mi).std() * np.sqrt(12)), vol_b=float(vm.reindex(mi).std() * np.sqrt(12))),
        dict(pair='SCHD vs D/P Hi30 (월간)', n=len(mi),
             corr=float(np.corrcoef(sm.reindex(mi), dpm.reindex(mi))[0, 1]),
             cagr_a=float((1 + sm.reindex(mi)).prod() ** (12 / len(mi)) - 1),
             cagr_b=float((1 + dpm.reindex(mi)).prod() ** (12 / len(mi)) - 1),
             vol_a=float(sm.reindex(mi).std() * np.sqrt(12)), vol_b=float(dpm.reindex(mi).std() * np.sqrt(12))),
        dict(pair='BE/ME Hi30 vs D/P Hi30 (월간, 1927~)', n=0, corr=np.nan,
             cagr_a=np.nan, cagr_b=np.nan, vol_a=np.nan, vol_b=np.nan),
    ]
    vm2, dp2 = vm.copy(), dpm.copy()
    ci = vm2.index.intersection(dp2.index)
    rows[3].update(n=len(ci), corr=float(np.corrcoef(vm2.reindex(ci), dp2.reindex(ci))[0, 1]),
                   cagr_a=float((1 + vm2.reindex(ci)).prod() ** (12 / len(ci)) - 1),
                   cagr_b=float((1 + dp2.reindex(ci)).prod() ** (12 / len(ci)) - 1),
                   vol_a=float(vm2.reindex(ci).std() * np.sqrt(12)),
                   vol_b=float(dp2.reindex(ci).std() * np.sqrt(12)))
    return pd.DataFrame(rows)


if __name__ == '__main__':
    pd.set_option('display.width', 200)
    q = proxy_quality()
    print('== 대리자산 타당성 (a=앞자산, b=뒷자산) ==')
    for _, r in q.iterrows():
        print('%-34s n=%5d  corr=%.3f  CAGR %6.2f%% vs %6.2f%%  Vol %5.2f%% vs %5.2f%%'
              % (r['pair'], r['n'], r['corr'], r['cagr_a'] * 100, r['cagr_b'] * 100,
                 r['vol_a'] * 100, r['vol_b'] * 100))
    v = ff_beme_daily()
    print('\nBE/ME Hi30 일간 범위 :', v.index[0].date(), '->', v.index[-1].date(), 'n =', len(v))
    print()
    q2 = proxy_quality2()
    print('== 자율규약1 검증: 세 대리안 vs SCHD 실물 (2011-10~) ==')
    for _, r in q2.iterrows():
        print('%-28s corr=%.3f  CAGR %6.2f%% (실물 %6.2f%%)  Vol %5.2f%% (실물 %5.2f%%)'
              % (r['proxy'], r['corr'], r['cagr_proxy'] * 100, r['cagr_schd'] * 100,
                 r['vol_proxy'] * 100, r['vol_schd'] * 100))
    print()
    for nm, k in [('연2% 현금', 'cash2'), ('T-bill', 'tbill'), ('가치주BE/ME', 'value'), ('배당주D/P', 'div')]:
        D = build(k)
        s = pd.Series(D['schdr'], index=D['idx'])
        pre = s[s.index < SCHD_START]
        print('%-10s 방어자산 1972-2011 CAGR = %6.2f%%   전체 %6.2f%%'
              % (nm, ((1 + pre).prod() ** (252 / len(pre)) - 1) * 100,
                 ((1 + s).prod() ** (252 / len(s)) - 1) * 100))
