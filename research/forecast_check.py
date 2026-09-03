# -*- coding: utf-8 -*-
"""
[사실 확인] 「미국 강세장 끝났다?」 — 골드만 3% vs JP모건 6.7% vs 야데니 11% 를 데이터로 심판 (2026-09-03, 소유자 요청)

소유자가 가져온 것: QQQ+SCHD 를 추종하는 유튜버의 작년 영상 요약. 골드만(코스틴) 향후 10년 S&P 연 3% · 아폴로(슬록) 포워드PE 21.8 → 3년 2.9% ·
JP모건 6.7% · 야데니 11%. 영상의 결론은 「예측은 동전던지기 · 대응보다 대비 · 장기 계획 유지」.

⚠ **전략 무접촉.** 이 파일은 주장의 **검증 가능한 부분만** 잰다. 어느 기관이 맞을지는 예측이고 이 저장소는 예측을 하지 않는다.
★ 이미 있는 것: 04 §5-26 이 CAPE 분위별 이후 수익(ρ −0.49)·장기 횡보 사건·그 구간의 B 성과를 이미 쟀다. **여기서는 그때 없던 두 가지만 더한다** —
  ⓐ **CAPE 의 예측력을 점추정이 아니라 산포로** (「연 3%」 같은 숫자에 오차막대가 얼마인가) · ⓑ **「저수익 10년」이 실제로 왔을 때 B 는 어땠나**(조건부 실측).

무엇을 재나:
  A. CAPE → 이후 10년 실질 총수익 회귀: R² · 잔차 표준편차 · **CAPE 38 에서의 예측구간** · 고평가 구간의 실제 산포(최소~최대).
  B. 「S&P 총수익 연 3% 이하인 10년」이 역사에 몇 번 있었나 · 그때 **엔진 표본(1972~)에서 B 는 얼마였나**.
  C. 「지난 100년 평균 11%」 · 「CAPE 38 = 상위 3%」 등 영상이 인용한 수치의 사실 확인.

사전 등록 예측 (결과 전 · 틀리면 그대로 적는다 §-1 ⑦):
  P1 CAPE 단독의 10년 실질 수익 설명력 R² 는 **0.2~0.45** — 방향은 맞지만 점추정을 낼 만큼은 아니다.
  P2 CAPE 38 근방의 95% 예측구간 폭은 **10%p 이상** — 「3%」와 「6.7%」가 **같은 구간 안**에 들어간다(즉 두 예측은 데이터로 구별되지 않는다).
  P3 S&P 10년 총수익 연 3% 이하 창은 명목 기준 드물다(<15%) — 실질로는 더 흔하다.
  P4 그런 저수익 10년에서도 B 의 CAGR 중앙은 S&P 보다 높다(§5-26 C 의 1973·2000·2007 사건과 같은 방향).

실행: python research/forecast_check.py   (약 10초 · 네트워크 0 · 파일 쓰기 0)
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

import eng_common as EC                                   # noqa: E402

L = '=' * 112


def main():
    sh = pd.read_csv('data/hist/shiller_sp500_monthly.csv', parse_dates=['Date']).set_index('Date')
    sh = sh.rename(columns={'SP500': 'P', 'Dividend': 'D', 'Consumer Price Index': 'CPI'})
    mp = pd.read_csv('data/hist/multpl_cape_monthly.csv', parse_dates=['Date']).set_index('Date')['cape']
    cpi2 = pd.read_csv('data/hist/datahub_cpi_us.csv', parse_dates=['Date']).set_index('Date')['Index']
    CAPE = sh.PE10.where(sh.PE10 > 0).dropna()
    CAPE = pd.concat([CAPE, mp[mp.index > CAPE.index[-1]]]).sort_index()
    CPIm = sh.CPI.where(sh.CPI > 0).dropna()
    CPIm = pd.concat([CPIm, cpi2[cpi2.index > CPIm.index[-1]]]).sort_index()
    trm = sh[['P', 'D']].copy()
    trm = trm[(trm.P > 0) & (trm.D > 0)]
    trm['tr'] = (trm.P + trm.D / 12) / trm.P.shift(1)
    trm.loc[trm.index[0], 'tr'] = 1.0
    TRn = trm.tr.cumprod()
    TRr = (TRn / CPIm.reindex(TRn.index)).dropna()

    print(L); print('「미국 강세장 끝났다?」 주장 검증 — 검증 가능한 부분만 (전략 무접촉 · 예측 안 함)'); print(L)
    print(f'  Shiller 총수익 {TRn.index[0].date()} ~ {TRn.index[-1].date()} · CAPE ~{CAPE.index[-1].date()} · CPI ~{CPIm.index[-1].date()}')

    # ── A. CAPE 의 예측력 — 점추정이 아니라 산포 ──────────────────────────────
    print('\n' + L); print('A. CAPE 는 10년 뒤를 얼마나 아는가 — 「연 3%」에 붙는 오차막대'); print(L)
    fwd = (TRr.shift(-120) / TRr) ** (1 / 10) - 1          # 이후 10년 실질 총수익 CAGR
    df = pd.concat([CAPE.rename('cape'), fwd.rename('fwd')], axis=1).dropna()
    x = np.log(df.cape.values); y = df.fwd.values * 100
    b, a = np.polyfit(x, y, 1)
    pred = a + b * x
    r2 = 1 - np.var(y - pred) / np.var(y)
    sd = float(np.std(y - pred, ddof=2))
    n_nonover = len(df) / 120
    print(f'  회귀: 이후 10년 실질 CAGR(%) = {a:.1f} {b:+.1f}×ln(CAPE) · 시작월 {len(df)}개 (비중첩 {n_nonover:.1f}개)')
    print(f'  **R² = {r2:.2f}** · 잔차 표준편차 **{sd:.1f}%p** — 즉 CAPE 를 알아도 10년 실질 수익의 {1-r2:.0%} 는 설명되지 않는다.')
    for c in (20, 30, 35, 38, 41.7):
        p = a + b * np.log(c)
        print(f'    CAPE {c:>4}: 중심 추정 {p:>5.1f}%  ·  95% 예측구간 **{p-1.96*sd:>5.1f}% ~ {p+1.96*sd:>5.1f}%**  (폭 {2*1.96*sd:.1f}%p)')
    print('\n  실제로 그 근방에서 나온 값들 (겹치는 창이라 독립 아님 — 국면 수를 같이 본다):')
    for lo, hi in ((25, 30), (30, 35), (35, 45)):
        s = df[(df.cape >= lo) & (df.cape < hi)]
        if not len(s):
            continue
        yrs = sorted(set(s.index.year))
        blocks = 1 + sum(1 for p, q in zip(yrs, yrs[1:]) if q - p > 1)
        print(f'    CAPE {lo}~{hi}: n={len(s):>4}개월 · 실질 10년 CAGR **최소 {s.fwd.min()*100:+.1f}% ~ 최대 {s.fwd.max()*100:+.1f}%** · '
              f'중앙 {s.fwd.median()*100:+.1f}% · **독립 국면 {blocks}개** ({yrs[0]}~{yrs[-1]})')
    print('\n  → 골드만 3%(명목)와 JP모건 6.7%(명목)의 차이는 3.7%p 다. 위 예측구간 폭보다 훨씬 좁다 —')
    print('    **두 예측은 이 데이터로는 구별되지 않는다.** 어느 쪽이 맞아도 CAPE 모형과 모순되지 않는다.')

    # ── B. 저수익 10년이 실제로 왔을 때 B 는 ─────────────────────────────────
    print('\n' + L); print('B. 「S&P 10년 연 3% 이하」가 실제로 왔을 때 B 는 어땠나 (엔진 표본 1972~)'); print(L)
    with contextlib.redirect_stdout(io.StringIO()):
        G, _ = EC.selfcheck()
    idx = pd.DatetimeIndex(G.idx)
    PX = pd.Series(G.D['px'], index=idx).astype(float)
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float)); MIX = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    cB = pd.Series(np.asarray(EC.sim2(EC.rule_dd(PX, -0.16, -0.16), QLDR, MIX), float), index=idx)
    c2 = pd.Series(np.cumprod(1 + QLDR), index=idx)
    Bm = cB.resample('MS').last(); NDm = PX.resample('MS').last(); L2m = c2.resample('MS').last()
    sp = TRn.copy()
    common = sp.index.intersection(Bm.index)
    sp10 = ((sp.shift(-120) / sp) ** (1 / 10) - 1).reindex(common)
    b10 = ((Bm.shift(-120) / Bm) ** (1 / 10) - 1).reindex(common)
    n10 = ((NDm.shift(-120) / NDm) ** (1 / 10) - 1).reindex(common)
    l10 = ((L2m.shift(-120) / L2m) ** (1 / 10) - 1).reindex(common)
    t = pd.concat([sp10.rename('sp'), b10.rename('B'), n10.rename('ndx'), l10.rename('x2')], axis=1).dropna()
    print(f'  겹치는 10년 창: {len(t)}개월 시작 ({t.index[0].date()} ~ {t.index[-1].date()} 시작 · 비중첩 {len(t)/120:.1f}개)')
    for lab, m in (('S&P 총수익 ≤ 3%/년', t.sp <= 0.03), ('≤ 5%/년', t.sp <= 0.05),
                   ('5~10%/년', (t.sp > 0.05) & (t.sp <= 0.10)), ('> 10%/년', t.sp > 0.10)):
        s = t[m]
        if not len(s):
            print(f'  {lab:<18} 해당 없음'); continue
        yrs = sorted(set(s.index.year))
        blocks = 1 + sum(1 for p, q in zip(yrs, yrs[1:]) if q - p > 1)
        print(f'  {lab:<18} 창 {len(s):>3}개월(국면 {blocks}) · S&P 중앙 {s.sp.median()*100:>5.1f}% · '
              f'NDX1배 {s.ndx.median()*100:>6.1f}% · 2배보유 {s.x2.median()*100:>6.1f}% · **B {s.B.median()*100:>5.1f}%** · '
              f'B 최소 {s.B.min()*100:>6.1f}% · B>S&P 비율 {(s.B > s.sp).mean():.0%}')
    print(f'\n  전체 창에서 S&P 10년 총수익이 3% 이하였던 비율: **{(t.sp <= 0.03).mean():.0%}** · 5% 이하 {(t.sp <= 0.05).mean():.0%}')

    # ── C. 인용 수치 사실 확인 ────────────────────────────────────────────────
    print('\n' + L); print('C. 영상이 인용한 수치 확인'); print(L)
    full = (TRn.iloc[-1] / TRn.iloc[0]) ** (1 / ((TRn.index[-1] - TRn.index[0]).days / 365.25)) - 1
    last100 = TRn[TRn.index >= TRn.index[-1] - pd.DateOffset(years=100)]
    c100 = (last100.iloc[-1] / last100.iloc[0]) ** (1 / ((last100.index[-1] - last100.index[0]).days / 365.25)) - 1
    r100 = TRr[TRr.index >= TRr.index[-1] - pd.DateOffset(years=100)]
    rr100 = (r100.iloc[-1] / r100.iloc[0]) ** (1 / ((r100.index[-1] - r100.index[0]).days / 365.25)) - 1
    print(f'  「지난 100년 평균 11%」 → 실측 명목 총수익 {c100*100:.1f}%/년 ({last100.index[0].date()}~{last100.index[-1].date()}) · '
          f'전체 {TRn.index[0].year}~ 는 {full*100:.1f}%/년')
    print(f'    ⚠ 같은 100년의 **실질**(물가 제외) 총수익은 {rr100*100:.1f}%/년 — 「11%」는 명목이다. 골드만의 3% 도 명목이므로 비교는 성립한다.')
    now = float(CAPE.iloc[-1])
    print(f'  「CAPE 38 = 상위 3%」 → 현재 CAPE {now:.1f}({CAPE.index[-1].date()}) = 1881~ 분포의 상위 {(CAPE >= now).mean()*100:.1f}% · '
          f'CAPE 38 기준이면 상위 {(CAPE >= 38).mean()*100:.1f}% · 역대 최고 {CAPE.max():.1f}({CAPE.idxmax().date()})')
    print(f'  「상위 10개가 S&P 40%」 → 이 저장소에 지수 구성 자료가 없어 **확인 불가**(외부 수치 그대로 인용 금지).')

    print('\n판정 (사전 등록 규약대로):')
    print(f'  P1 R² {r2:.2f} (예측 0.2~0.45) → {"맞음" if 0.20 <= r2 <= 0.45 else "틀림"}')
    print(f'  P2 예측구간 폭 {2*1.96*sd:.1f}%p (예측 10%p+) → {"맞음" if 2*1.96*sd >= 10 else "틀림"} — 골드만 3% 와 JP모건 6.7% 는 구별 불가')
    print(f'  P3 S&P 10년 ≤3% 창 비율 {(t.sp <= 0.03).mean():.0%} (예측 <15%) → {"맞음" if (t.sp <= 0.03).mean() < 0.15 else "틀림"}')
    s3 = t[t.sp <= 0.05]
    print(f'  P4 저수익(≤5%) 창에서 B 중앙 {s3.B.median()*100:.1f}% vs S&P {s3.sp.median()*100:.1f}% → '
          f'{"맞음" if len(s3) and s3.B.median() > s3.sp.median() else "틀림"}')

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 「저수익 10년에서 B 가 낫다」는 표본 안 사실이다 — 그 창의 국면 수가 적으면 경향이지 확률이 아니다(위 표의 국면 열).')
    print('  Q-b 영상의 조언(대응하지 말고 대비하라)은 이 저장소 규약과 같다 — 다만 그 유튜버는 **1배 무신호**이고 B 는 **2배+전환**이다.')
    print('      같은 조언이 같은 결과를 뜻하지 않는다: 04 §5-26 C 의 2000~2013 은 2배보유 0.07배 vs B 2.95배.')


if __name__ == '__main__':
    main()
