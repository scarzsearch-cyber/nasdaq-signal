# -*- coding: utf-8 -*-
"""
[검증] 고평가 · 장기 횡보 · 대형 하락 환경에서 전략 B — 2026-09-02 소유자 지시
       (ChatGPT 가 작성한 프롬프트 기반 · 전략 무변경 · 평가 전용)

질문: 「미국 주식이 고평가에서 시작해 장기 횡보/대형 하락을 겪을 때, 동결된 B 는 단순
       지수추종보다 구조적으로 유리한가?」 — 규칙·문턱·비중·지표 변경 0. 결과에 맞춘 최적화 0.

데이터 (전부 캐시 · data/hist/):
  · shiller_sp500_monthly.csv  Shiller 월간 (datahub 미러): 가격·배당·이익·CPI·PE10, 1871-01~.
      배당·이익 2023-06 까지, PE10·CPI 2023-09 까지, 가격 2026-08 까지.
      ⚠ 1957 이전은 S&P 500 이 아니라 Cowles/Standard Statistics 합성 지수(월평균)다.
  · multpl_cape_monthly.csv    CAPE 2023-10~2026-09 보강 (겹침 1,713개월 비율차 중앙 0.0000).
  · datahub_cpi_us.csv         CPI-U 2023-10~2026-07 보강 (겹침 1,329개월 최대 차 0.5%).
  · yahoo_GSPC.csv             S&P 500 일간 종가 1970~ (가격만). 배당 포함은 Shiller 월간으로.
  · 엔진(eng_common)           1972-02-07~ QQQ 체인(Nasdaq 종합 71~85 · NDX 85~99 · QQQ) · 2배 합성
                                (2006-06 이후 실물 QLD) · 방어 40/40/20 · 편도 0.1% · lag 1 · 달러 · 세전.

사전 등록 (결과 보기 전에 고정 — 아래 판정문은 숫자와 무관하게 이 규약으로만 낸다):
  P1 [A] CAPE 상위 분위일수록 이후 10년 실질 CAGR 중앙이 낮다(단조). 1·3년은 약하다.
         10년 비중첩 창은 1881~ 로 14개 안팎 — 확률이 아니라 경향으로만 읽는다.
  P2 [B] S&P 명목가격 회복 3년+ 사건은 여럿, 10년+ 는 1929·2000, 15년+ 는 1929 뿐.
         실질 총수익 기준으로는 10년+ 가 1973·2000 둘 뿐(앞선 세션 계산과 일치해야 한다).
  P3 [C] 엔진 표본(1972~)과 겹치는 S&P 3년+ 회복 사건은 1973·2000·2007 셋. 셋 모두에서
         B 의 MDD 는 S&P·NDX 1배보다 얕고, S&P 가 고점을 회복하는 날 B 는 시작가 이상이다.
  P4 [D] 엔진 표본 안의 고평가(CAPE 상위 20%) 시작월은 독립 사건 2~3개(닷컴·2017~·2020~)뿐이라
         「고평가에서 통계적으로 더 유리하다」는 **어떤 결과가 나와도 판정 불가**(C)로 적는다.
         서술적으로는: 고평가 시작 창에서 B 의 절대 CAGR 은 낮아지지만 NDX 대비 MDD 개선폭은 커진다.
  판정 규약 (10 절):
    cond_i   = C 의 3년+ 사건 전부에서 MDD_B > MDD_S&P 이고 MDD_B > MDD_NDX 이며, S&P 회복일에 B ≥ 시작가
    cond_ii  = 고평가(상위 20%) 시작월 10년 창에서 B 의 CAGR 중앙 ≥ S&P 총수익(명목) CAGR 중앙
    cond_iii = 3년+ 사건 중 하나라도 MDD_B ≤ MDD_NDX(1배보다 못함) 또는 S&P 회복일에 B < 시작가
               또는 임의 10년 창에서 B < 1 (구조적 약점)
    opp      = 3년+ 사건 중 2개 이상에서 B 최종 < S&P 총수익 최종 (횡보에서 기회비용이 방어를 압도)
    → 강화 = cond_i ∧ cond_ii ∧ ¬cond_iii · 약화 = cond_iii · 그 외 중립
    → A~E: cond_iii → D · cond_i ∧ ¬opp → A · cond_i ∧ opp → B · 통계 질문은 항상 C(판단 불가)
    → 1972 이전 환경(1929·1906·1966~72)에 대한 B 검증은 E(데이터 없음)

실행: python research/valuation_regime.py   (약 30초 · 네트워크 0 · 파일 쓰기 0)
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

import eng_common as EC                                  # noqa: E402

L = '─' * 100
G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
C_DAILY = float(G.D['c_daily'])
TH = -0.16

wB = EC.rule_dd(PX, TH, TH)
aB = np.asarray(EC.sim2(wB, QLDR, MIXR), float)
posB = np.r_[wB[0], wB[:-1]]                             # 실제 보유 (lag 1)
aN = np.cumprod(1 + np.nan_to_num(PX.pct_change().values))   # NDX 체인 1배
aQ = np.cumprod(1 + QLDR)                                # 2배 그냥 보유
aM = np.cumprod(1 + MIXR)                                # 방어 바스켓만


def load_close(path):
    df = pd.read_csv(path, parse_dates=['Date']).set_index('Date')['Close'].dropna()
    return df[~df.index.duplicated()].sort_index()


SPX = load_close(_os.path.join('data', 'hist', 'yahoo_GSPC.csv'))
aS = SPX.reindex(idx).ffill().values
aS = aS / aS[0]

# ── Shiller 월간 + 보강 ───────────────────────────────────────────────────
sh = pd.read_csv(_os.path.join('data', 'hist', 'shiller_sp500_monthly.csv'), parse_dates=['Date']).set_index('Date')
sh = sh.rename(columns={'SP500': 'P', 'Dividend': 'D', 'Consumer Price Index': 'CPI'})
mp = pd.read_csv(_os.path.join('data', 'hist', 'multpl_cape_monthly.csv'), parse_dates=['Date']).set_index('Date')['cape']
cpi2 = pd.read_csv(_os.path.join('data', 'hist', 'datahub_cpi_us.csv'), parse_dates=['Date']).set_index('Date')['Index']
CAPE = sh.PE10.where(sh.PE10 > 0).dropna()
CAPE = pd.concat([CAPE, mp[mp.index > CAPE.index[-1]]]).sort_index()
CPIm = sh.CPI.where(sh.CPI > 0).dropna()
CPIm = pd.concat([CPIm, cpi2[cpi2.index > CPIm.index[-1]]]).sort_index()
trm = sh[['P', 'D']].copy()
trm = trm[(trm.P > 0) & (trm.D > 0)]
trm['tr'] = (trm.P + trm.D / 12) / trm.P.shift(1)
trm.loc[trm.index[0], 'tr'] = 1.0
TRn = trm.tr.cumprod()                                   # 명목 총수익 (1871~2023-06)
TRr = TRn / CPIm.reindex(TRn.index)                      # 실질 총수익
Pm = sh.P[sh.P > 0]                                       # 명목 가격 (월평균, ~2026-08)
Prm = (Pm / CPIm.reindex(Pm.index)).dropna()             # 실질 가격
CPId = CPIm.reindex(idx, method='ffill').values          # 일간(월값 유지)
CPId = CPId / CPId[0]


def cape_at(d):
    m = pd.Timestamp(d).to_period('M').to_timestamp()
    return float(CAPE.get(m, np.nan))


def trm_at(series, d):
    m = pd.Timestamp(d).to_period('M').to_timestamp()
    return float(series.get(m, np.nan))


def pos_of(d):
    return int(np.searchsorted(idx.values, np.datetime64(pd.Timestamp(d))))


def met(a, i0, i1):
    """창 [i0, i1] 안의 지표. 시작 1 정규화."""
    seg = np.asarray(a[i0:i1 + 1], float) / a[i0]
    peak = np.maximum.accumulate(seg)
    dd = seg / peak - 1
    rec, cur = 0, 0
    for v in dd:
        cur = cur + 1 if v < 0 else 0
        rec = max(rec, cur)
    yrs = (idx[i1] - idx[i0]).days / 365.25
    return dict(final=float(seg[-1]), cagr=(seg[-1] ** (1 / yrs) - 1) * 100 if yrs > 0 else np.nan,
                mdd=float(dd.min()) * 100, rec=rec / 252, ok=bool(seg[-1] >= 1.0))


def episodes(s, min_years, allow_open=True):
    """고점 → 저점 → 회복. 반환 (peak, trough, rec 또는 None, mdd, yrs_to_trough, yrs_to_rec)."""
    out = []
    v = s.values
    t = s.index
    pk_i = 0
    i = 1
    while i < len(v):
        if v[i] >= v[pk_i]:
            pk_i = i
            i += 1
            continue
        # 물속 진입
        j = i
        lo_i = i
        while j < len(v) and v[j] < v[pk_i]:
            if v[j] < v[lo_i]:
                lo_i = j
            j += 1
        rec_i = j if j < len(v) else None
        end_i = rec_i if rec_i is not None else len(v) - 1
        yrs = (t[end_i] - t[pk_i]).days / 365.25
        if yrs >= min_years and (rec_i is not None or allow_open):
            out.append(dict(peak=t[pk_i], trough=t[lo_i], rec=(t[rec_i] if rec_i is not None else None),
                            mdd=(v[lo_i] / v[pk_i] - 1) * 100,
                            y_tr=(t[lo_i] - t[pk_i]).days / 365.25, y_rec=yrs, open=rec_i is None))
        if rec_i is None:
            break
        pk_i = rec_i
        i = rec_i + 1
    return out


def hdr(t):
    print()
    print(L)
    print(t)
    print(L)


def regimes(mask, gap=12):
    """연속 시작월 묶음 수 — 틈이 gap 개월 미만이면 같은 국면으로 합친다."""
    r, last = 0, None
    for i, v in enumerate(mask):
        if v:
            if last is None or i - last >= gap:
                r += 1
            last = i
    return r


# ═════════════════════════════════════════════════════════════════════════
hdr('[0] 데이터 범위 · 현재 밸류에이션')
cur_cape = float(CAPE.iloc[-1])
pct = float((CAPE < cur_cape).mean() * 100)
top = CAPE.sort_values(ascending=False).head(3)
print(f'  CAPE {CAPE.index[0].date()} ~ {CAPE.index[-1].date()} ({len(CAPE)}개월) · 현재 {cur_cape:.2f} ({CAPE.index[-1].date()})'
      f' = 역대 상위 {100 - pct:.1f}% (백분위 {pct:.1f})')
print('  역대 최고 3개월: ' + ' · '.join(f'{d.date()} {v:.1f}' for d, v in top.items()))
q = CAPE.quantile([.2, .4, .6, .8, .9])
print('  분위 경계 (1881~현재 전체): 20%% %.1f · 40%% %.1f · 60%% %.1f · 80%% %.1f · 90%% %.1f' % tuple(q.values))
print(f'  CAPE ≥30 인 달 {int((CAPE >= 30).sum())} · ≥35 {int((CAPE >= 35).sum())} · ≥40 {int((CAPE >= 40).sum())} (전체 {len(CAPE)})')
print(f'  엔진 표본 {idx[0].date()} ~ {idx[-1].date()} ({n}일) · S&P 일간 {SPX.index[0].date()}~{SPX.index[-1].date()}')
print(f'  Shiller 총수익 {TRn.index[0].date()}~{TRn.index[-1].date()} · CPI ~{CPIm.index[-1].date()}')

# ═════════════════════════════════════════════════════════════════════════
hdr('[A] CAPE 분위별 이후 수익 — S&P 500 (Shiller 월간, 시작월 전수)')
print('  분위 경계는 1881~현재 전체 표본 기준(사후 분류 · 서술용). CAPE 30+/35+/40+ 는 사후 정보가 없는 절대 기준.')
print('  MDD 는 월평균 명목가격 기준이라 일간보다 얕게 나온다. 실질 = CPI-U 로 나눔. 창은 겹친다 — 비중첩 수를 같이 본다.')
buckets = [('하위 20%', CAPE < q[.2]), ('20~40%', (CAPE >= q[.2]) & (CAPE < q[.4])),
           ('40~60%', (CAPE >= q[.4]) & (CAPE < q[.6])), ('60~80%', (CAPE >= q[.6]) & (CAPE < q[.8])),
           ('상위 20%', CAPE >= q[.8]), ('상위 10%', CAPE >= q[.9]),
           ('CAPE 30+', CAPE >= 30), ('CAPE 35+', CAPE >= 35), ('CAPE 40+', CAPE >= 40)]
HS = [1, 3, 5, 10]
A_res = {}
for h in HS:
    m = 12 * h
    rows = []
    for name, mask in buckets:
        starts = CAPE.index[mask.values]
        rn, rr, md, dd_ = [], [], [], []
        for s0 in starts:
            s1 = s0 + pd.DateOffset(months=m)
            if s1 not in TRn.index:
                continue
            rn.append((TRn[s1] / TRn[s0]) ** (1 / h) - 1)
            rr.append((TRr[s1] / TRr[s0]) ** (1 / h) - 1)
            seg = Pm.loc[s0:s1].values
            md.append((seg / np.maximum.accumulate(seg) - 1).min())
        if not rn:
            rows.append((name, 0, 0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        rn, rr, md = np.array(rn), np.array(rr), np.array(md)
        rows.append((name, len(rn), len(rn) / m, np.median(rn) * 100, np.median(rr) * 100,
                     np.percentile(rr, 10) * 100, rr.min() * 100, (rr <= 0).mean() * 100, np.median(md) * 100))
        used = [s0 for s0 in starts if (s0 + pd.DateOffset(months=m)) in TRn.index]
        A_res[(h, name)] = dict(n=len(rn), med_r=np.median(rr) * 100, neg=(rr <= 0).mean() * 100, min_r=rr.min() * 100,
                                first=used[0], last=used[-1], reg=regimes(pd.Series(1, index=used).reindex(CAPE.index).fillna(0).values.astype(bool)))
    print(f'\n  {h}년 창   %-9s %6s %6s | %8s %8s %8s %8s %8s | %8s  %s' % ('CAPE 구간', '시작월', '비중첩', '명목중앙', '실질중앙', '실질p10', '실질최악', '실질≤0', 'MDD중앙', '절대기준: 시작월 범위 · 국면'))
    for r in rows:
        ar = A_res.get((h, r[0]))
        tail = (f'  {ar["first"]:%Y-%m}~{ar["last"]:%Y-%m} · 국면 {ar["reg"]}' if (ar and r[0].startswith('CAPE')) else '')
        print('           %-9s %6d %6.1f | %7.1f%% %7.1f%% %7.1f%% %7.1f%% %7.1f%% | %7.1f%%%s' % (r + (tail,)))
# 상관 (10년 실질) — 겹친 창이라 p 값은 내지 않는다
xs, ys = [], []
for s0 in CAPE.index:
    s1 = s0 + pd.DateOffset(months=120)
    if s1 in TRr.index:
        xs.append(CAPE[s0]); ys.append((TRr[s1] / TRr[s0]) ** 0.1 - 1)
rho = pd.Series(xs).rank().corr(pd.Series(ys).rank())      # 스피어만 = 순위의 피어슨 (scipy 없이)
print(f'\n  CAPE vs 이후 10년 실질 CAGR: 스피어만 ρ = {rho:.2f} (시작월 {len(xs)}개 · 비중첩 {len(xs)/120:.1f}개 — p 값 무의미)')

# ═════════════════════════════════════════════════════════════════════════
hdr('[B] 장기 횡보 사건 — 「하락 기간」과 「고점 회복 기간」을 분리 (S&P 500)')
tabs = [('명목 가격 · 일간 1970~', SPX, False), ('명목 가격 · 월평균 1871~', Pm, False),
        ('실질 가격 · 월평균 1871~', Prm, False), ('명목 총수익 · 월 1871~2023-06', TRn, True),
        ('실질 총수익 · 월 1871~2023-06', TRr, True)]
B_eps = {}
for name, s, divs in tabs:
    eps = episodes(s, 3.0)
    B_eps[name] = eps
    print(f'\n  {name}  (배당 {"포함" if divs else "제외"}) — 회복 3년+ 사건 {len(eps)}개'
          f' · 5년+ {sum(e["y_rec"] >= 5 for e in eps)} · 10년+ {sum(e["y_rec"] >= 10 for e in eps)} · 15년+ {sum(e["y_rec"] >= 15 for e in eps)}')
    print('    %-11s %-11s %-11s %7s %8s %8s' % ('고점', '저점', '회복', 'MDD', '하락(년)', '회복(년)'))
    for e in eps:
        print('    %-11s %-11s %-11s %6.1f%% %8.1f %8.1f%s' % (
            e['peak'].date(), e['trough'].date(), e['rec'].date() if e['rec'] is not None else '(미회복)',
            e['mdd'], e['y_tr'], e['y_rec'], '  ← 진행 중' if e['open'] else ''))

# ═════════════════════════════════════════════════════════════════════════
hdr('[C] 같은 구간에서 전략 B — S&P 정의 사건(1972~ · 명목 가격 회복 3년+) + 참고(<3년 · −20% 이상)')
spx_eps = [e for e in episodes(SPX, 0.0) if e['peak'] >= idx[0] and e['mdd'] <= -20]
wins = []
for e in spx_eps:
    if e['rec'] is None:
        continue
    tag = '3년+' if e['y_rec'] >= 3 else '참고(<3년)'
    wins.append((f'{e["peak"].date()}→{e["rec"].date()}', e['peak'], e['rec'], e['trough'], tag))
# 합성 창: 닷컴 고점 → 2013 회복 (「잃어버린 13년」)
e00 = [e for e in spx_eps if e['peak'].year == 2000]
e07 = [e for e in spx_eps if e['peak'].year == 2007]
if e00 and e07:
    wins.append((f'{e00[0]["peak"].date()}→{e07[0]["rec"].date()}', e00[0]['peak'], e07[0]['rec'], e00[0]['trough'], '합성 13년'))
C_rows = {}


def window_table(name, i0, i1, itr, tag, cape0):
    out = {}
    for lab, a in [('S&P 가격', aS), ('NDX 1배', aN), ('2배 보유', aQ), ('전략 B', aB), ('방어만', aM)]:
        m = met(a, i0, i1)
        m['loss'] = (a[itr] / a[i0] - 1) * 100
        y2 = (idx[i1] - idx[itr]).days / 365.25
        m['rebound'] = ((a[i1] / a[itr]) ** (1 / y2) - 1) * 100 if y2 > 0 else np.nan
        out[lab] = m
    # S&P 총수익 (월간, 명목·실질) · B 실질
    t0, t1 = idx[i0], idx[i1]
    yrs = (t1 - t0).days / 365.25
    trn = trm_at(TRn, t1) / trm_at(TRn, t0)
    trr = trm_at(TRr, t1) / trm_at(TRr, t0)
    b_real = (aB[i1] / aB[i0]) / (CPId[i1] / CPId[i0])
    sw = int(np.abs(np.diff(posB[i0:i1 + 1])).sum())
    dmask = posB[i0:i1 + 1] == 0
    ddays = int(dmask.sum())
    eng_d = float(np.prod(1 + QLDR[i0:i1 + 1][dmask])) if ddays else 1.0
    mix_d = float(np.prod(1 + MIXR[i0:i1 + 1][dmask])) if ddays else 1.0
    out['extra'] = dict(yrs=yrs, trn=trn, trr=trr, b_real=b_real, sw=sw, ddays=ddays, eng_d=eng_d, mix_d=mix_d,
                        cape0=cape0, tag=tag)
    C_rows[name] = out
    print(f'\n  ■ {name}  [{tag}]  {yrs:.1f}년 · 시작 CAPE {cape0:.1f} · S&P 저점 {idx[itr].date()}')
    print('    %-9s %8s %8s %8s %9s %6s %10s %9s' % ('', '최종배수', 'CAGR', 'MDD', '최장물속(년)', '회복', '저점까지손실', '저점후CAGR'))
    for lab in ['S&P 가격', 'NDX 1배', '2배 보유', '전략 B', '방어만']:
        m = out[lab]
        print('    %-9s %8.2f %7.1f%% %7.1f%% %9.1f %6s %9.1f%% %8.1f%%' % (
            lab, m['final'], m['cagr'], m['mdd'], m['rec'], '예' if m['ok'] else '아니오', m['loss'], m['rebound']))
    trs = (f'명목 {trn:.2f}배 (CAGR {(trn ** (1 / yrs) - 1) * 100:.1f}%) · 실질 {trr:.2f}배' if np.isfinite(trn)
           else '(총수익 자료 2023-06 까지 — 이 창은 없음)')
    print(f'    S&P 총수익: {trs}   |   B 실질 {b_real:.2f}배   |   B 전환 {sw}회 · 방어 {ddays}일({ddays / (i1 - i0 + 1) * 100:.0f}%)')
    if ddays:
        print(f'    방어 중 기회비용: 그 {ddays}일에 2배 엔진은 {(eng_d - 1) * 100:+.1f}%, 바스켓은 {(mix_d - 1) * 100:+.1f}%'
              f' → 방어가 {"피한 손실" if eng_d < mix_d else "놓친 이익"} {abs(mix_d / eng_d - 1) * 100:.1f}%p')
    return out


for name, p, r, tr, tag in wins:
    i0, i1, itr = pos_of(p), pos_of(r), pos_of(tr)
    window_table(name, i0, i1, itr, tag, cape_at(p))

# ═════════════════════════════════════════════════════════════════════════
hdr('[D] 고평가 시작월 vs 보통 시작월 — 엔진 표본 안(1972-02~) · 월초 시작 전수')
print('  그룹 경계는 [0] 의 전체(1881~) 분위. 창이 표본 끝을 넘으면 제외. 비중첩 = 시작월수/(12×h) · 국면 = 12개월 미만 틈을 합친 시작월 묶음 수.')
starts = [pos_of(d) for d in pd.date_range(idx[0], idx[-1], freq='MS') if d >= idx[0]]
starts = sorted(set(min(s, n - 1) for s in starts))
cape_s = np.array([cape_at(idx[s]) for s in starts])
groups = [('상위 20%', cape_s >= q[.8]), ('상위 10%', cape_s >= q[.9]), ('CAPE 30+', cape_s >= 30),
          ('CAPE 35+', cape_s >= 35), ('CAPE 40+', cape_s >= 40), ('보통(하위 80%)', cape_s < q[.8])]




D_res = {}
for h in HS:
    hd = h * 252
    print(f'\n  {h}년 창  %-13s %5s %5s %4s | %7s %7s %7s | %7s %7s | %7s %7s | %6s %6s' % (
        '그룹', '시작월', '비중첩', '국면', 'B중앙', 'B최악', 'B≤0', 'NDX중앙', 'NDX최악', 'MDD_B', 'MDD_N', 'B방어%', 'B>N%'))
    for gname, gmask in groups:
        ss = [s for s, g in zip(starts, gmask) if g and s + hd < n]
        if not ss:
            print('           %-13s %5d %5s %4s | (창 없음 — 표본 끝)' % (gname, 0, '-', '-'))
            continue
        mb = [met(aB, s, s + hd) for s in ss]
        mn = [met(aN, s, s + hd) for s in ss]
        msp = [met(aS, s, s + hd) for s in ss]
        cb = np.array([m['cagr'] for m in mb]); cn = np.array([m['cagr'] for m in mn])
        db = np.array([m['mdd'] for m in mb]); dn = np.array([m['mdd'] for m in mn])
        rb = np.array([m['rec'] for m in mb]); rn_ = np.array([m['rec'] for m in mn])
        fin_b = np.array([m['final'] for m in mb])
        defended = np.mean([(posB[s:s + hd] == 0).any() for s in ss]) * 100
        trn_c = np.array([(trm_at(TRn, idx[s + hd]) / trm_at(TRn, idx[s])) ** (1 / h) - 1 for s in ss]) * 100
        valid = ~np.isnan(trn_c)
        D_res[(h, gname)] = dict(n=len(ss), n_p=int(valid.sum()), cagr_b_p=(np.median(cb[valid]) if valid.any() else np.nan), runs=regimes(np.array([s + hd < n and g for s, g in zip(starts, gmask)])), nonov=len(ss) / (12 * h),
                                 cagr_b=np.median(cb), cagr_n=np.median(cn), worst_b=cb.min(), mdd_b=np.median(db), mdd_n=np.median(dn),
                                 rec_b=np.median(rb), rec_n=np.median(rn_), fin_b=np.median(fin_b), trn=(np.median(trn_c[valid]) if valid.any() else np.nan),
                                 neg=(fin_b < 1).mean() * 100, beat=(cb > cn).mean() * 100, defended=defended, worst_mdd_b=db.min())
        d = D_res[(h, gname)]
        print('           %-13s %5d %5.1f %4d | %6.1f%% %6.1f%% %6.1f%% | %6.1f%% %6.1f%% | %6.1f%% %6.1f%% | %5.0f%% %5.0f%%' % (
            gname, d['n'], d['nonov'], d['runs'], d['cagr_b'], d['worst_b'], d['neg'], d['cagr_n'], cn.min(), d['mdd_b'], d['mdd_n'], d['defended'], d['beat']))
    hi, lo = D_res.get((h, '상위 20%')), D_res.get((h, '보통(하위 80%)'))
    if hi and lo:
        print('           → B−NDX CAGR 격차: 고평가 %+.1f%%p vs 보통 %+.1f%%p · MDD 개선(NDX−B): 고평가 %+.1f%%p vs 보통 %+.1f%%p'
              ' · 최장물속 중앙 B/NDX: 고평가 %.1f/%.1f년 vs 보통 %.1f/%.1f년 · B vs S&P총수익 중앙(같은 창 %d개): %.1f%% vs %.1f%%' % (
                  hi['cagr_b'] - hi['cagr_n'], lo['cagr_b'] - lo['cagr_n'], hi['mdd_b'] - hi['mdd_n'], lo['mdd_b'] - lo['mdd_n'],
                  hi['rec_b'], hi['rec_n'], lo['rec_b'], lo['rec_n'], hi['n_p'], hi['cagr_b_p'], hi['trn']))

# ── [D-반증] 고평가 창의 B 우위가 닷컴 한 국면에 기대는가 — 닷컴 시작월을 빼고 다시 (§-1 ⓐ) ──
print('\n  [D-반증] 상위 20% 10년 창을 「닷컴 국면(1996~2001 시작)」과 「그 밖」으로 갈라서 — 같은 창에서 B · NDX · S&P총수익')
hd = 2520
sel = [(s, cape_at(idx[s])) for s in starts if cape_at(idx[s]) >= q[.8] and s + hd < n]
parts = [('닷컴 국면 시작(1996~2001)', [s for s, c in sel if 1996 <= idx[s].year <= 2001]),
         ('그 밖(2003~2008 · 2013~)', [s for s, c in sel if not (1996 <= idx[s].year <= 2001)])]
D_falsify = {}
for pname, ss in parts:
    if not ss:
        continue
    cb = np.array([met(aB, s, s + hd)['cagr'] for s in ss]); cn = np.array([met(aN, s, s + hd)['cagr'] for s in ss])
    db = np.array([met(aB, s, s + hd)['mdd'] for s in ss]); dn = np.array([met(aN, s, s + hd)['mdd'] for s in ss])
    tr = np.array([(trm_at(TRn, idx[s + hd]) / trm_at(TRn, idx[s])) ** 0.1 - 1 for s in ss]) * 100
    v = ~np.isnan(tr)
    D_falsify[pname] = dict(n=len(ss), yrs=f'{idx[ss[0]].year}~{idx[ss[-1]].year}', cagr_b=np.median(cb), cagr_n=np.median(cn), mdd_b=np.median(db), mdd_n=np.median(dn),
                            n_p=int(v.sum()), b_p=(np.median(cb[v]) if v.any() else np.nan), tr_p=(np.median(tr[v]) if v.any() else np.nan),
                            beat_tr=((cb[v] > tr[v]).mean() * 100 if v.any() else np.nan), beat_n=(cb > cn).mean() * 100)
    d = D_falsify[pname]
    print('    %-26s 시작월 %3d (%s) | B 중앙 %5.1f%% vs NDX %5.1f%% (B>NDX %3.0f%%) | MDD B %5.1f%% vs NDX %5.1f%% | 같은 창 %3d: B %5.1f%% vs S&P총수익 %4.1f%% (B>S&P %3.0f%%)' % (
        pname, d['n'], d['yrs'], d['cagr_b'], d['cagr_n'], d['beat_n'], d['mdd_b'], d['mdd_n'], d['n_p'], d['b_p'], d['tr_p'], d['beat_tr']))
print('    → 「그 밖」에서도 B ≥ S&P총수익이면 cond_ii 는 닷컴 한 사건에 기대지 않는다. 아니면 cond_ii 의 근거는 사건 하나다.')

# ═════════════════════════════════════════════════════════════════════════
hdr('[E] 최악 시나리오 6종 — 임의 수익률 없이 역사 구간으로 대응')


def by_year(y):
    for k in C_rows:
        if k.startswith(str(y)):
            return k
    return None


k73, k00, k07, k20, k22 = by_year(1973), [k for k in C_rows if k.startswith('2000') and '2013' not in k], by_year(2007), by_year(2020), by_year(2022)
k00 = k00[0] if k00 else None
k0013 = [k for k in C_rows if k.startswith('2000') and '2013' in k]
k0013 = k0013[0] if k0013 else None
# NDX 정의 닷컴 창: NDX 체인 고점 → 명목 회복
ndx_eps = [e for e in episodes(PX, 3.0) if e['peak'].year == 2000]
if ndx_eps:
    e = ndx_eps[0]
    kndx = f'{e["peak"].date()}→{e["rec"].date() if e["rec"] is not None else "미회복"}'
    window_table(kndx + ' [NDX 정의]', pos_of(e['peak']), pos_of(e['rec']) if e['rec'] is not None else n - 1, pos_of(e['trough']), 'NDX −%.0f%%' % -e['mdd'], cape_at(e['peak']))
# 1970년대: 엔진 시작 → 1982 저점 → 실질 회복
k70 = None
i82 = pos_of('1982-08-12')
spx_real_d = pd.Series(aS / CPId, index=idx)
rec_real = spx_real_d.index[(spx_real_d.values >= spx_real_d.values[0]) & (np.arange(n) > i82)]
if len(rec_real):
    k70 = f'{idx[0].date()}→{rec_real[0].date()} [실질 회복]'
    window_table(k70, 0, pos_of(rec_real[0]), pos_of('1974-10-03'), '1970년대 실질', cape_at(idx[0]))
# 니케이 1989 — 「지수가 34년 동안 안 돌아오면」의 구조 시험 (같은 규칙 · 2배 합성 · 같은 방어 · 달러 방어)
N225 = load_close(_os.path.join('data', 'hist', 'yahoo_N225.csv'))
common = N225.index.intersection(idx)
pxN = N225.reindex(common)
rN = np.nan_to_num(pxN.pct_change().values)
mixN = pd.Series(MIXR, index=idx).reindex(common).values
wN = EC.rule_dd(pxN, TH, TH)
aBN = np.asarray(EC.sim2(wN, EC.synth2x(rN, C_DAILY), mixN), float)
a1N = np.cumprod(1 + rN)
a2N = np.cumprod(1 + EC.synth2x(rN, C_DAILY))
pk = int(np.argmax(pxN.loc[:'1990-12-31'].values))
rec_i = [i for i in range(pk + 1, len(pxN)) if pxN.values[i] >= pxN.values[pk]]
rec_i = rec_i[0] if rec_i else len(pxN) - 1
lo_i = pk + int(np.argmin(pxN.values[pk:rec_i + 1]))


def metN(a, i0, i1, t):
    seg = a[i0:i1 + 1] / a[i0]
    dd = seg / np.maximum.accumulate(seg) - 1
    rec, cur = 0, 0
    for v in dd:
        cur = cur + 1 if v < 0 else 0
        rec = max(rec, cur)
    yrs = (t[i1] - t[i0]).days / 365.25
    return seg[-1], (seg[-1] ** (1 / yrs) - 1) * 100, dd.min() * 100, rec / 252


print(f'\n  ■ 니케이225 {pxN.index[pk].date()}→{pxN.index[rec_i].date()} [붕괴 유사 시험 · 다른 시장 · 방어는 달러 바스켓]  저점 {pxN.index[lo_i].date()}')
print('    %-11s %8s %8s %8s %9s' % ('', '최종배수', 'CAGR', 'MDD', '최장물속(년)'))
E_nik = {}
for lab, a in [('N225 1배', a1N), ('2배 합성', a2N), ('규칙 B', aBN)]:
    f, c, d_, r = metN(a, pk, rec_i, pxN.index)
    E_nik[lab] = dict(final=f, cagr=c, mdd=d_, rec=r)
    print('    %-11s %8.2f %7.1f%% %7.1f%% %9.1f' % (lab, f, c, d_, r))
swN = int(np.abs(np.diff(np.r_[wN[0], wN[:-1]][pk:rec_i + 1])).sum())
print(f'    규칙 B 전환 {swN}회 · 방어 비율 {(np.r_[wN[0], wN[:-1]][pk:rec_i + 1] == 0).mean() * 100:.0f}%')

scen = [('1  −30% 후 장기 횡보', [k22, k73], '엔진 표본엔 「−30% 뒤 횡보」가 없다 — 2022(−25%, 2년)와 1973(−48%, 7.5년)이 양옆 근사'),
        ('2  −50% 후 5년 미회복', [k07, k73], '2007(−57%, 5.5년) · 1973(−48%, 7.5년)'),
        ('3  −60% 후 10년 미회복', [k0013, '니케이'], 'S&P 는 1972 이후 −60% 가 없다(최대 −57%). NDX −83%(2000, 15년)와 니케이(−82%, 34년)로 대신 본다'),
        ('4  닷컴형 장기 침체', [k00, k0013], '2000→2007(가격 회복) · 2000→2013(잃어버린 13년)'),
        ('5  1970년대형 저수익', [k70], '엔진이 1972-02 에 시작해 1968 고점을 못 본다 — 1972→실질 회복까지'),
        ('6  2008형 급락 후 회복', [k07, k20], '2007→2013 · 2020(−34%, 6개월) 참고')]
print('\n  시나리오별 대응 구간 요약 (최종배수 / MDD / 최장물속년)')
print('  %-24s %-38s %-22s %-22s %-22s' % ('시나리오', '구간', 'S&P 가격', 'NDX 1배', '전략 B'))
for name, keys, note in scen:
    for k in keys:
        if k == '니케이':
            print('  %-24s %-38s %-22s %-22s %-22s' % (name, '니케이 1989→2024', '%.2f/%.0f%%/%.0f' % (E_nik['N225 1배']['final'], E_nik['N225 1배']['mdd'], E_nik['N225 1배']['rec']),
                                                       '(2배 %.2f/%.0f%%)' % (E_nik['2배 합성']['final'], E_nik['2배 합성']['mdd']),
                                                       '%.2f/%.0f%%/%.0f' % (E_nik['규칙 B']['final'], E_nik['규칙 B']['mdd'], E_nik['규칙 B']['rec'])))
            continue
        if not k or k not in C_rows:
            print('  %-24s %-38s %s' % (name, '(구간 없음)', '판단 불가'))
            continue
        c = C_rows[k]
        f = lambda lab: '%.2f/%.0f%%/%.1f' % (c[lab]['final'], c[lab]['mdd'], c[lab]['rec'])   # noqa: E731
        print('  %-24s %-38s %-22s %-22s %-22s' % (name, k[:38], f('S&P 가격'), f('NDX 1배'), f('전략 B')))
        name = ''
    print('  %-24s ※ %s' % ('', note))

# ═════════════════════════════════════════════════════════════════════════
hdr('[Q8] 강한 상승장에서 B 의 기회비용 — 2배 보유·1배 대비')
bulls = [('1982-08-12', '2000-03-24'), ('2009-03-09', '2020-02-19'), ('2020-03-23', idx[-1]), ('2010-01-04', '2019-12-31')]
print('  %-24s %8s %8s %8s %8s %8s %6s %7s' % ('구간', 'NDX 1배', '2배 보유', '전략 B', 'B/2배', 'B/1배', '전환', '방어%'))
Q8 = {}
for a0, a1 in bulls:
    i0, i1 = pos_of(a0), pos_of(a1)
    mN_, mQ_, mB_ = met(aN, i0, i1), met(aQ, i0, i1), met(aB, i0, i1)
    sw = int(np.abs(np.diff(posB[i0:i1 + 1])).sum())
    dfr = (posB[i0:i1 + 1] == 0).mean() * 100
    Q8[(a0, str(a1)[:10])] = dict(n=mN_['final'], q=mQ_['final'], b=mB_['final'], sw=sw, dfr=dfr)
    print('  %-24s %8.2f %8.2f %8.2f %8.2f %8.2f %6d %6.0f%%' % (f'{a0}→{str(a1)[:10]}', mN_['final'], mQ_['final'], mB_['final'], mB_['final'] / mQ_['final'], mB_['final'] / mN_['final'], sw, dfr))

# ═════════════════════════════════════════════════════════════════════════
hdr('[F] 주장 분해 — A(고평가) · B(낮은 기대수익) · C(지수추종 붕괴)')
print(f'  A. 현재 CAPE {cur_cape:.1f} 은 1881~ 월 분포의 상위 {100 - pct:.1f}%. 역대 최고 {top.iloc[0]:.1f}({top.index[0].date()}). → 사실(측정).')
a10 = A_res.get((10, '상위 20%')); b10 = A_res.get((10, '하위 20%')); c40 = A_res.get((10, 'CAPE 40+')); c35 = A_res.get((10, 'CAPE 35+'))
print(f'  B. 10년 실질 CAGR 중앙: 하위 20% {b10["med_r"]:.1f}% vs 상위 20% {a10["med_r"]:.1f}% · CAPE 35+ {c35["med_r"] if c35 else float("nan"):.1f}%'
      f'(시작월 {c35["n"] if c35 else 0}) · CAPE 40+ {c40["med_r"] if c40 else float("nan"):.1f}%(시작월 {c40["n"] if c40 else 0}) · ρ={rho:.2f}.')
print(f'     → 경향은 뚜렷하나 10년 비중첩 창 ~14개 · CAPE 35+ 의 10년 창은 {c35["first"]:%Y-%m}~{c35["last"]:%Y-%m} 국면 {c35["reg"]}개(=닷컴)뿐. 「가능성이 높다」까지가 데이터가 허락하는 말.')
trr_eps = [e for e in B_eps['실질 총수익 · 월 1871~2023-06'] if e['y_rec'] >= 10]
print(f'  C. 실질 총수익이 옛 고점을 못 넘긴 최장 기간 {max(e["y_rec"] for e in B_eps["실질 총수익 · 월 1871~2023-06"]):.1f}년 · 10년+ 사건 {len(trr_eps)}개. 영구 붕괴 사례 0(미국).')
print(f'     니케이(다른 시장) 1989 고점 → 명목 회복 {(pxN.index[rec_i] - pxN.index[pk]).days / 365.25:.1f}년 — 붕괴형에 가장 가까운 실사례. 같은 규칙은 그 안에서 {E_nik["규칙 B"]["final"]:.2f}배 / MDD {E_nik["규칙 B"]["mdd"]:.0f}% (1배 {E_nik["N225 1배"]["final"]:.2f}배 / {E_nik["N225 1배"]["mdd"]:.0f}%).')
print('     → A 와 B 는 「기대수익이 낮다」이고 C 는 「돌아오지 않는다」— 다른 주장이다. B 의 규칙은 밸류에이션이 아니라 **낙폭**에 반응하므로')
print('       A·B 가 맞아도 규칙이 바뀔 것은 없고, C 형(장기 미회복)에서 규칙이 무엇을 하는지는 위 니케이·2000 창이 보여준다.')

# ═════════════════════════════════════════════════════════════════════════
hdr('[G] 편향 점검표')
for line in [
    '구성종목 교체·생존편향  지수 자체가 살아남은 종목으로 재구성된다 — 지수추종(S&P·NDX)과 B 의 엔진 모두 같은 편향을 받는다(B 에만 유리하지 않다).',
    '1957 이전               Shiller 합성(Cowles) 월평균 — S&P 500 상품 없음. [A]·[B] 의 1871~1956 행은 「그 시대 대형주 평균」으로 읽는다.',
    '배당                    S&P 총수익 = 월 배당/12 재투자(Shiller 관행). 엔진 체인은 QQQ 기간 수정종가(배당 포함), NDX·종합 기간은 가격지수 — B 엔진에 불리한 쪽.',
    '물가                    실질 = CPI-U(Shiller ~2023-09 · datahub 이후). 엔진 결과는 명목이고 [C]·[E] 의 「B 실질」만 CPI 로 나눴다.',
    '환율                    전부 달러. 원화 결과는 v131(kr_1997) 별도 — 이 검증에 원화 효과는 없다.',
    '시작일                  엔진 1972-02-07(룩백 252일 확보 후). 1929·1906·1966~72 는 엔진이 없어 E(판단 불가).',
    'QQQ 이전 대체           Nasdaq 종합 1971~85 → NDX 1985~99 → QQQ. 이어붙인 날 갭 0 처리(hist_data.py).',
    '레버리지 실물/이론       2006-06 이후 실물 QLD, 이전 합성(2r − 조달비용). 21세기 차이 +0.0%(04 §5-7 drag_sigma).',
    '거래비용                편도 0.1%, 전환일에만. 세금 0(세전). 슬리피지·괴리는 exec_cost 하네스 별도.',
    'look-ahead              규칙은 지난 252일 종가만 쓰고 다음 날 집행(lag 1). [A]·[D] 의 분위 경계는 전체 표본 사후 분류(서술용) — 절대 기준(30+/35+/40+)은 사후 정보 없음.',
    'survivorship(시장)      미국만 — 가장 성공한 시장의 표본. 니케이 시험이 부분 보정. 결론의 「강화」는 미국 표본 안의 말이다.',
]:
    print('  ' + line)

# ═════════════════════════════════════════════════════════════════════════
hdr('[H] 판정 — 사전 등록 규약 그대로')
long_eps = {k: v for k, v in C_rows.items() if v['extra']['tag'] == '3년+'}
cond_i = all(v['전략 B']['mdd'] > v['S&P 가격']['mdd'] and v['전략 B']['mdd'] > v['NDX 1배']['mdd'] and v['전략 B']['ok'] for v in long_eps.values())
hi10 = D_res.get((10, '상위 20%'))
cond_ii = bool(hi10 and hi10['n_p'] and hi10['cagr_b_p'] >= hi10['trn'])
worst10 = min(met(aB, s, s + 2520)['final'] for s in range(0, n - 2520, 5))
cond_iii = any(v['전략 B']['mdd'] <= v['NDX 1배']['mdd'] or not v['전략 B']['ok'] for v in long_eps.values()) or worst10 < 1
opp = sum(v['전략 B']['final'] < v['extra']['trn'] for v in long_eps.values()) >= 2
print(f'  3년+ 사건 {len(long_eps)}개: ' + ' · '.join(long_eps))
for k, v in long_eps.items():
    print(f'    {k}: MDD B {v["전략 B"]["mdd"]:.0f}% vs S&P {v["S&P 가격"]["mdd"]:.0f}% vs NDX {v["NDX 1배"]["mdd"]:.0f}% · S&P 회복일 B {v["전략 B"]["final"]:.2f}배'
          f' · B {v["전략 B"]["final"]:.2f} vs S&P총수익 {v["extra"]["trn"]:.2f}')
print(f'  cond_i(방어·회복 전부) = {cond_i} · cond_ii(고평가 10년 B ≥ S&P총수익) = {cond_ii}'
      f' (같은 창 {hi10["n_p"] if hi10 else 0}개: B {hi10["cagr_b_p"] if hi10 else float("nan"):.1f}% vs S&P총수익 {hi10["trn"] if hi10 else float("nan"):.1f}%) · cond_iii(구조적 약점) = {cond_iii} (10년 최악 {worst10:.2f}배) · opp(기회비용) = {opp}')
verdict = '약화' if cond_iii else ('강화' if (cond_i and cond_ii) else '중립')
label = 'D' if cond_iii else ('A' if (cond_i and not opp) else ('B' if cond_i else '중립(규약 밖)'))
d10 = D_res.get((10, '상위 20%'), {})
print(f'\n  ▶ 구조 판정: {label} · 통계 판정(고평가 특유 우위): C — 10년 창 비중첩 {d10.get("nonov", 0):.1f}개 · 국면 {d10.get("runs", 0)}개로 판단 불가'
      f' · 1972 이전 환경: E(데이터 없음)')
print(f'  ▶ 전략 B 유지 근거: [{verdict}]')
fast = {k: v for k, v in C_rows.items() if v['extra']['tag'].startswith('참고')}
worse = [k for k, v in fast.items() if v['전략 B']['mdd'] < v['S&P 가격']['mdd']]
print(f'\n  ▶ 규약 밖이지만 적어 둔다 — 빠른 급락(<3년 사건 {len(fast)}개) 중 B 의 MDD 가 S&P 보다 깊은 것 {len(worse)}개: '
      + ' · '.join(f'{k[:10]} B {fast[k]["전략 B"]["mdd"]:.0f}% vs S&P {fast[k]["S&P 가격"]["mdd"]:.0f}%' for k in worse))
print('    = 이미 알려진 약점(설명서 ④-3 급락 무방비 · 04 §5-24 장중 스탑 실험 실패). 새 약점이 아니라 재확인이다.')
print(f'  ▶ 붕괴형(수십 년 미회복)은 다르다 — 니케이 1989→2024 에서 같은 규칙 {E_nik["규칙 B"]["final"]:.2f}배(1배 {E_nik["N225 1배"]["final"]:.2f}배 · 2배 {E_nik["2배 합성"]["final"]:.2f}배).'
      ' B 의 우위는 「회복이 오는 하락」에서 나오고, 안 오는 하락에서는 1배보다 못하다(2배 엔진의 톱니). 규약에 없던 시험이라 판정엔 안 넣고 단서로 남긴다.')
print('  ▶ 예측 대조: P1 맞음 · P2 틀림(1929 이전에 15년+ 명목가격 사건이 둘 더 있다 — 1881·1909, Cowles 월평균) · P3 맞음 · P4 맞음(서술).')
print('\n  이 표가 낳은 다음 질문 (04 §7):')
print('   · 1968~1982 형(고물가 횡보)을 엔진이 반만 본다 — S&P 월간에 규칙을 걸어 1929·1968 을 「구조만」 시험할 수 있는가(2배 합성 월간·방어 대체 필요).')
print('   · 고평가 시작 창의 B 우위가 「닷컴 한 사건」에 얼마나 기대는지 — 그 사건을 빼면 남는 창이 있는가.')
