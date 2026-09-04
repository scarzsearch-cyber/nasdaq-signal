# -*- coding: utf-8 -*-
"""
[팩트체크, 소유자 요청 2026-09-01] 외부 강연 슬라이드(2026 싱글파이어 머니쇼)의
QLD 장기투자 주장 5건을 이 저장소의 데이터·엔진으로 대조한다.

★ 판정·채택 아님 · 전략 무변경 · 제안 없음. **외부 주장의 사실 여부만 잰다.**
   (§2: 전략 규칙·비중·수익률 개선 제안 금지. 이 파일은 그 어느 것도 하지 않는다.)

검증 대상:
  ① 「최적 레버리지 ≈ 2.3배(1971~2009) / 2.67배(1971~2026)」  — 포물선 꼭짓점
  ② 「1971년 초 100만원 거치 → 현재 313억」                    — 배수 검산
  ③ 「QLD 10년단위 백테스트 11,427일 / 20년단위 8,907일」      — 표본의 정체
  ④ 「25년단위: 원금 이하 단 하루도 없음 · 중앙값 45배」        — 유효표본
  ⑤ 「매년 반복되는 단기 조정」 표                              — 어느 지수인가

재현: python research/factcheck_qld_talk.py
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                 # noqa: E402
from axis_lib import lev_r                              # noqa: E402

G, _ = EC.selfcheck()
D, idx = G.D, G.idx
n = len(idx)
yrs = (idx[-1] - idx[0]).days / 365.25
pxr = np.nan_to_num(D['px'].pct_change().values)        # 기초지수 일간수익
print('\n' + '=' * 74)
print('데이터: %s ~ %s · %d거래일 · %.2f년' % (idx[0].date(), idx[-1].date(), n, yrs))
print('=' * 74)


def curve(k, cost=True, lo=0, hi=None):
    """k배 거치식 누적곡선. cost=False 면 변동성 드래그만(차입비용 0)."""
    hi = n if hi is None else hi
    r = (k * pxr - (k - 1) * D['c_daily']) if cost else (k * pxr)
    return float(np.prod(1.0 + np.asarray(r, float)[lo + 1:hi]))


def cagr(mult, years):
    return (mult ** (1.0 / years) - 1.0) * 100.0


def peak(lo, hi, cost):
    """0.01 간격으로 꼭짓점을 찾는다 (슬라이드가 소수 둘째 자리까지 말한다)."""
    ks = np.arange(0.5, 4.001, 0.01)
    y = (hi if hi is not None else n) - 1
    years = (idx[min(y, n - 1)] - idx[lo]).days / 365.25
    cg = [cagr(curve(float(k), cost, lo, hi), years) for k in ks]
    i = int(np.argmax(cg))
    return float(ks[i]), cg[i], years


# ── ① 최적 레버리지 꼭짓점 ────────────────────────────────────────────────
print('\n[①] 최적 레버리지 꼭짓점 — 슬라이드: 2009년까지 2.3배 / 2026년까지 2.67배')
i2009 = int(idx.searchsorted('2009-12-31'))
for lab, hi in (('~2009 (슬라이드 2.3배)', i2009), ('~2026 (슬라이드 2.67배)', None)):
    kc, gc, yc = peak(0, hi, True)
    kn, gn, _ = peak(0, hi, False)
    print('  %-22s %.1f년 | 비용반영 k*=%.2f (CAGR %.2f%%) | 비용0 k*=%.2f (CAGR %.2f%%)'
          % (lab, yc, kc, gc, kn, gn))

print('\n  k별 CAGR (전 구간, 비용반영) — 꼭짓점이 실제로 있는가')
for k in (1.0, 1.5, 2.0, 2.3, 2.5, 2.67, 3.0, 3.5, 4.0):
    m = curve(k)
    print('    k=%.2f  CAGR %5.2f%%   최종배수 %s' % (k, cagr(m, yrs), format(int(m), ',')))

# ── ② 100만원 → 313억 ────────────────────────────────────────────────────
print('\n[②] 1971년 초 100만원 거치 -> 313억 (= 31,300배) 검산')
# 100만원 = 1e6원, 1억 = 1e8원 -> 억원 환산은 배수/100 이다.
for k in (2.0, 2.3, 2.67, 3.0):
    mc, mn = curve(k), curve(k, cost=False)
    print('    k=%.2f | 비용반영 %9s배 = %7.1f억원 | 차입비용0 %9s배 = %7.1f억원'
          % (k, format(int(mc), ','), mc / 100, format(int(mn), ','), mn / 100))
print('    슬라이드 313억 = 31,300배 -> **비용반영과 비용0 사이**에 있다.')
print('    ※ 이 저장소 데이터는 1972-02 시작 · 세전 · 달러 기준(슬라이드는 1971-02).')

# ── ③④ 롤링 창 — 표본의 정체와 유효표본 ──────────────────────────────────
print('\n[③④] 롤링 창 — 슬라이드는 「QLD 백테스트」라고 부른다')
qld = np.nan_to_num(np.asarray(D['qldr'], float))       # 실물 체인 포함 2배
cum = np.cumprod(1.0 + qld)
TH = [1, 5, 10, 20, 30, 50, 100, 200, 500]
for yw, shown in ((10, 11427), (20, 8907), (25, None)):
    w = int(round(yw * 252))
    cnt = n - w
    if cnt <= 0:
        continue
    mult = cum[w:] / cum[:-w]
    row = ' '.join('%s배%5.2f%%' % (t, (mult >= t).mean() * 100) for t in TH[:6])
    print('  %2d년 창: 시작점 %s개 (슬라이드 %s) · 비중첩 %.1f개 · 중앙 %.1f배'
          % (yw, format(cnt, ','), format(shown, ',') if shown else '—',
             n / w, float(np.median(mult))))
    print('      %s' % row)

print('\n  ※ 표본의 정체: 슬라이드의 11,427 + 2,520(10년) = 13,947,')
print('     8,907 + 5,040(20년) = 13,947 — **둘이 같은 총량**을 가리킨다.')
print('     13,947거래일 ≈ 55년. 그런데 **QLD 상장은 2006-06**이다(실물 약 5,000일).')
syn = np.abs(EC.synth2x(pxr, D['c_daily']) - qld) <= 1e-10
print(f'     즉 이 저장소 체인의 **{syn.mean():.0%}** ({int(syn.sum()):,}/{len(syn):,}일)는 '
      '**합성 2배**이고, 나머지가 실물 QLD다.')

# ── ⑤ 연간 최대낙폭 표는 어느 지수인가 ────────────────────────────────────
print(chr(10) + '[⑤] 「매년 반복되는 단기 조정」 표 — 어느 지수를 잰 것인가')
import pandas as pd                                     # noqa: E402
s = pd.Series(np.asarray(D['px'], float), index=idx)
SLIDE = {2001: -29, 2002: -33, 2003: -14, 2008: -48, 2009: -27, 2010: -16,
         2011: -19, 2015: -12, 2018: -19, 2020: -34, 2022: -23, 2023: -18,
         2024: -10, 2025: -18}
print('    연도  슬라이드   나스닥100(이 저장소)   차이')
gap = []
for y in sorted(SLIDE):
    w = s[s.index.year == y]
    if len(w) < 50:
        continue
    mdd = float((w / w.cummax() - 1).min()) * 100
    gap.append(mdd - SLIDE[y])
    print('    %d   %5d%%       %6.1f%%           %+.1f%%p' % (y, SLIDE[y], mdd, gap[-1]))
print('    닷컴·2022 처럼 **기술주가 특히 아팠던 해**에서만 크게 벌어진다')
print('    (2001 -29 vs -58 · 2002 -33 vs -52 · 2022 -23 vs -35) —')
print('    이 패턴은 슬라이드 표가 **S&P500** 이라는 뜻이다. 파는 물건은 2배 나스닥인데')
print('    고통은 더 순한 지수로 보여주는 셈이다(2배면 다시 그 두 배).')
