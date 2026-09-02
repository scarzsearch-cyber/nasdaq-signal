# -*- coding: utf-8 -*-
"""
[연구 Q2] 대체품이 환헤지(H)면 방어가 얼마나 약해지나 — 04 §7 Q2 (2026-09-02, 소유자 「연구만, 반영 금지」)

배경: 공격 자산 418660(TIGER 미국나스닥100레버리지 합성)은 **환노출 2배**다. 상장폐지 등으로 갈아탈 때의
      후보 409820(KODEX 미국나스닥100레버리지 합성 H)은 **환헤지**다. §5-5 는 전략 전체의 원화 MDD 차이
      10.9%p 만 쟀고 「공격 다리만 헤지했을 때」는 안 쟀다(04 Q2). 그 빈칸을 잰다.

방법: hist_krfinal.build_krw 의 원화 1997~ 시나리오(채택 방어 배당40/국채40/금20 · 한국 거래일 체결 ·
      슬리피지 0.1%)를 그대로 쓰되 **공격 다리만** 둘로 만든다.
        환노출 2배(현행)  lev2  = 2·((1+r_ndx)(1+r_fx) − 1) − c
        환헤지 2배(409820형) lev2h = 2·r_ndx − c + carry
      carry = (한국 3개월 금리 − 미국 3개월 금리)/252 — 커버드 금리평가: 원화 투자자가 달러 자산을 헤지하면
      금리차만큼 받거나(원화 금리가 높을 때) 낸다(달러 금리가 높을 때). 한국 3개월: FRED IR3TIB01KRM156N(월간,
      1991~, 일별 ffill). 스왑 비용·괴리는 모형 밖 → 감도 −0.5%/년 을 따로 본다.

★ 사전 등록 (결과를 보기 전에 적는다 — CLAUDE.md §-1):
  · 판정이 아니다. 관문 없음. 산출물은 「갈아타면 낙폭·수익이 얼마나 바뀌나」의 숫자표 하나.
  · 예측 P1: 헤지형은 **원화 MDD 가 더 깊다**(2008·2020·2022 처럼 달러가 오르는 위기에서 환노출이 완충).
    크기 예측: 전체 MDD 5~15%p 악화.
  · 예측 P2: 1997~ 최종배수·CAGR 은 헤지형이 낮다(원화 약세 30년 + 금리차 carry 는 2022 이후 음수).
  · 예측 P3: 위기 4창(2000·2008·2020·2022) 중 3창 이상에서 헤지형 낙폭이 더 깊다.
  · 「틀리면 무엇이 참인가」: P1 이 틀리면(헤지형 MDD 가 얕다) 환노출은 완충이 아니라 소음이고 §5-5 의
    해석을 다시 써야 한다. 맞으면 「갈아탈 때 방어력이 X%p 약해진다」가 04 Q2 의 답이 된다.
  · 어느 쪽이든 **규칙·상품 변경 없음** — 418660 이 살아 있는 한 할 일이 없다(AUM 감시가 방아쇠).

실행: python research/q2_hedged_attack.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import csv
import io
import sys
import urllib.request
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_korea as K                                   # noqa: E402
import hist_krfinal as KF                                # noqa: E402
import hist_defasset as DA                               # noqa: E402
import eng_common as EC                                  # noqa: E402

STRAT_B = dict(enter=-0.16, exit=-0.16, name='−16 / −16', ladder=[(('dd', -0.16), 1.0, 0)])
KR3M = _os.path.join('data', 'hist', 'kr_3m_rate.csv')      # 정규화 캐시: date,rate,source (출처 무관)
SRC_FRED = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=IR3TIB01KRM156N'
SRC_OECD = ('https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/'
            'KOR.M.IR3TIB.PA.....?format=csvfilewithlabels&startPeriod=1991-01')
WINDOWS = [('닷컴 2000', '2000-03-01', '2002-12-31'), ('금융위기 2008', '2007-10-01', '2009-06-30'),
           ('코로나 2020', '2020-02-01', '2020-06-30'), ('금리 2022', '2021-11-01', '2022-12-31'),
           ('IMF 1997', '1997-06-01', '1998-12-31')]


def _fetch(url, timeout):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'replace')


def kr_3m(idx):
    """한국 3개월 금리(연, 소수), 월간 → 일별 ffill.
    ★ 출처 보험 (2026-09-03 소유자 지시 — FRED 가 이틀째 타임아웃):
       ① FRED IR3TIB01KRM156N (30초) → ② OECD SDMX DSD_STES@DF_FINMARK KOR·IR3TIB (같은 원천 OECD, 2026-08 까지
       실측 · 2026-06 = 2.91 로 FRED 와 일치) → ③ 지난 실행이 남긴 캐시 data/hist/kr_3m_rate.csv (낡아도 씀)
       → ④ None (호출부가 ±1.5%p 감도로 범위를 낸다 — 숫자를 지어내지 않는다).
       ①②가 성공하면 캐시를 갱신한다 — 다음엔 네트워크 없이도 돈다(저장소에 커밋)."""
    s, src = None, None
    try:
        txt = _fetch(SRC_FRED, 30)
        if not txt.startswith('observation_date'):
            raise RuntimeError('응답 형식 아님')
        d = pd.read_csv(io.StringIO(txt)); d.columns = ['date', 'v']
        s = pd.to_numeric(d.set_index(pd.to_datetime(d['date']))['v'], errors='coerce').dropna(); src = 'FRED'
    except Exception as e:
        print(f'[출처] FRED 실패({type(e).__name__}) → OECD SDMX 시도')
    if s is None:
        try:
            rows = [r for r in csv.DictReader(io.StringIO(_fetch(SRC_OECD, 45))) if r.get('OBS_VALUE')]
            s = pd.Series({pd.Timestamp(r['TIME_PERIOD'] + '-01'): float(r['OBS_VALUE']) for r in rows}).sort_index()
            src = 'OECD SDMX'
        except Exception as e:
            print(f'[출처] OECD SDMX 실패({type(e).__name__}) → 캐시 시도')
    if s is not None and len(s) > 100:
        pd.DataFrame({'date': s.index.strftime('%Y-%m-%d'), 'rate': s.values, 'source': src}).to_csv(KR3M, index=False)
        print(f'[출처] {src} · {s.index[0].date()} ~ {s.index[-1].date()} ({len(s)}개월) · 캐시 저장 {KR3M}')
    else:
        try:
            d = pd.read_csv(KR3M)
            s = pd.Series(d['rate'].values, index=pd.to_datetime(d['date'])).sort_index()
            src = f"캐시({d['source'].iloc[-1]} · ~{s.index[-1].date()})"
            print(f'[출처] {src}')
        except Exception:
            print('[경고] 한국 3개월 금리 — 출처 셋 모두 실패 · carry 는 상수 감도로 대신한다')
            return None
    s = s.reindex(idx.union(s.index)).ffill().reindex(idx)
    return s.values / 100.0


def mdd(a):
    a = np.asarray(a, float)
    return float(np.min(a / np.maximum.accumulate(a) - 1)) * 100


def window_stats(curve, lo, hi):
    seg = curve.loc[lo:hi]
    if len(seg) < 20:
        return np.nan, np.nan
    return mdd(seg.values), (seg.values[-1] / seg.values[0] - 1) * 100


def run(Dx, qr, sr, krd):
    Dx = dict(Dx); Dx['qldr'] = qr; Dx['schdr'] = sr
    c, w, t = K.run_kr(Dx, STRAT_B, cost=0.001, slip=0.001, start=KF.ST, krdays=krd)
    c = pd.Series(np.asarray(c, float), index=(c.index if hasattr(c, 'index') else None))
    return c, np.asarray(t, float)


def main():
    D, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    krd = K.kr_caldays()
    rq = np.nan_to_num(D['px'].pct_change().values)
    c_d = D['c_daily']
    us3 = DA._short_rate(idx)                      # 미국 단기금리(연, 소수)
    kr3 = kr_3m(idx)
    if kr3 is not None:
        carry = (kr3 - us3) / 252.0
        carry_lab = 'carry=한−미 3개월 금리차(실측)'
    else:                                          # 계열 미확보 — 상수 범위로 답한다 (숫자를 지어내지 않는다)
        kr3 = np.full(len(idx), np.nan)
        carry = np.zeros(len(idx))
        carry_lab = 'carry=0 (금리 계열 미확보 · 아래 ±1.5%p 감도로 범위)'
    lev2h = 2 * rq - c_d + carry                   # 환헤지 2배 (carry 반영)
    lev2h0 = 2 * rq - c_d + 0.015 / 252.0          # 감도: 원화 금리가 연 1.5%p 높을 때 (1997~2021 형)
    lev2hc = 2 * rq - c_d - 0.015 / 252.0          # 감도: 달러 금리가 연 1.5%p 높을 때 (2022~ 형)
    # 채택 방어(배당40/국채40/금20, 원화) — build_stats.sc_kr_1997 과 같은 조립
    raw = {'div': np.asarray(dfk, float),
           'ust5': DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE),
           'gold': DA.gold_r(idx)}
    parts = {k: (raw[k] if k == 'div' else (1 + raw[k]) * (1 + fr) - 1) for k in DA.MIX_V23}
    sr = DA.mix_monthly_parts(idx, DA.MIX_V23, parts)

    lo = idx.searchsorted(pd.Timestamp(KF.ST))
    yrs = (idx[-1] - idx[lo]).days / 365.25
    print('=' * 96)
    print('Q2 공격 다리 환헤지(409820형) vs 환노출(418660, 현행) — 원화 1997~ · 채택 방어 · 규칙 −16/−16 · 규칙 무변경')
    print('=' * 96)
    ok = float(np.isfinite(kr3[lo:]).mean())
    if ok > 0:
        print(f'표본 {idx[lo].date()} ~ {idx[-1].date()} ({yrs:.1f}년) · {carry_lab} · 결측 {100*(1-ok):.1f}% · '
              f'금리차(한−미) 평균 {np.nanmean(kr3[lo:]-us3[lo:])*100:+.2f}%p/년 · 최근 1년 {np.nanmean((kr3-us3)[-252:])*100:+.2f}%p')
    else:
        print(f'표본 {idx[lo].date()} ~ {idx[-1].date()} ({yrs:.1f}년) · {carry_lab}')

    rows = []
    for nm, qr in [('환노출 2배 (현행 418660)', lev2), (f'환헤지 2배 (409820형, {carry_lab.split(" ")[0]})', lev2h),
                   ('환헤지 2배 (감도: carry +1.5%p/년)', lev2h0), ('환헤지 2배 (감도: carry −1.5%p/년)', lev2hc)]:
        c, t = run(D, qr, sr, krd)
        m = EC.fullmet(c.values, idx=c.index)
        m['p05'] = EC.p05_20y(c.values)
        m['sw'] = int(np.nansum(t))
        rows.append((nm, c, m))
    print(f"\n  {'공격 다리':<34}{'최종배수':>10}{'CAGR':>8}{'MDD':>9}{'Calmar':>8}{'20년p05':>9}{'전환':>6}")
    base = rows[0][2]
    for nm, c, m in rows:
        print(f"  {nm:<34}{m['final']:>10,.1f}{m['cagr']:>7.2f}%{m['mdd']:>8.1f}%{m['calmar']:>8.3f}"
              f"{m['p05']:>8.2f}배{m['sw']:>6d}")
    h = rows[1][2]
    print(f"\n  → 갈아타면(carry 반영): 최종배수 {h['final']/base['final']:.2f}배 · CAGR {h['cagr']-base['cagr']:+.2f}%p · "
          f"MDD {h['mdd']-base['mdd']:+.1f}%p · Calmar {h['calmar']/base['calmar']-1:+.1%} · 20년p05 {h['p05']/base['p05']-1:+.1%}")

    print('\n  위기 창별 (전략 곡선 · 창 안 MDD / 창 수익)          환노출        환헤지        Δ MDD')
    worse = 0; n_w = 0
    for wn, a, b in WINDOWS:
        m0, r0 = window_stats(rows[0][1], a, b); m1, r1 = window_stats(rows[1][1], a, b)
        if np.isnan(m0) or np.isnan(m1):
            continue
        n_w += 1; worse += (m1 < m0 - 0.5)
        print(f'  {wn:<14} {a}~{b}   {m0:>6.1f}% / {r0:>+6.1f}%   {m1:>6.1f}% / {r1:>+6.1f}%   {m1-m0:>+6.1f}%p')
    # 맨몸 보유(전환 없음)에서의 환 완충 — 전략을 빼고 본 순수 환 효과
    hold0 = pd.Series(np.cumprod(1 + lev2[lo:]), index=idx[lo:])
    hold1 = pd.Series(np.cumprod(1 + lev2h[lo:]), index=idx[lo:])
    print('\n  참고 — 전환 없이 2배 맨몸 보유(원화):   환노출 MDD %.1f%% · 환헤지 MDD %.1f%%  (환 완충의 순수 크기 %+.1f%%p)'
          % (mdd(hold0.values), mdd(hold1.values), mdd(hold1.values) - mdd(hold0.values)))

    print('\n사전 등록 대조:')
    print(f"  P1 (헤지형 MDD 더 깊다, 5~15%p): {'맞음' if h['mdd'] < base['mdd'] else '틀림'} — Δ {h['mdd']-base['mdd']:+.1f}%p")
    print(f"  P2 (최종배수·CAGR 낮다): {'맞음' if h['final'] < base['final'] else '틀림'} — {h['final']/base['final']:.2f}배")
    print(f"  P3 (위기창 3/4+ 에서 더 깊다): {'맞음' if worse >= 3 else '틀림'} — {worse}/{n_w}")
    print('\n이 측정이 낳은 다음 질문 (§-1 절대멈춤 6):')
    print('  · 갈아탈 날이 오면 「환헤지 2배」와 「환노출 1배(133690 같은 비레버리지)+…」 중 무엇이 덜 나쁜가는 안 쟀다 — 그날의 질문.')
    print('  · carry 는 한국 3개월 금리로 근사했다(실제 헤지는 1개월 롤·스왑 비용) — 상품 실측 괴리로 보정할 자료가 없다.')


if __name__ == '__main__':
    main()
