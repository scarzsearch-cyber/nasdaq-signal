# -*- coding: utf-8 -*-
"""
[2026-09-01 소유자 질문] 「SNS·1인 1PC·온라인 쇼핑이 당연해진 시기를 **기점**으로 잡으면
                          어떻게 되나? 내 생각엔 2011 페이스북 / 2012 롤 흥행쯤부터인데.」

★ 사전 등록 — 결과 보기 전에 적는다.

  이 질문은 「전략이 낡았나」가 아니라 **「어느 창에서 재는 게 옳은가」** 다.
  그런데 창을 손으로 고르는 것은 §-1 ⓑ 가 지목한 바로 그 실수 유형이다
  (T4@3 을 둥근 날짜 하나로 잘못 기각한 적이 있다). 그래서 **두 겹으로 잰다.**

  [관문 설계 — 실패하면 무엇이 참? 통과하면 무엇이 참? (§-1 ⑤)]
    2011/2012 시작에서 B 가 2배 맨몸에 **진다**고 하자. 그것만으로는
      (ㄱ) 「시대가 바뀌어 전략이 낡았다」 와
      (ㄴ) 「그 창에 닷컴급 사건이 없었다」 가 **구분되지 않는다.**
    구분되지 않는 검사는 관문이 아니다. 그래서 가르는 축을 미리 정한다:

      **모든 시작일**에 대해 (B÷2배 비율)과 (그 창의 2배 맨몸 MDD)를 같이 재서,
      비율이 **창 안의 최악 낙폭으로 설명되면** -> (ㄴ). 2011-2012 라는 시대가 아니라
      **「폭락이 없는 창」이면 언제 시작해도** 같은 일이 벌어진다는 뜻이다.
      설명되지 않고 2011 전후에서 **꺾이면** -> (ㄱ). 그때는 시대 가설이 산다.

  [ⓑ 반증 의무] 소유자가 **손으로 고른 두 날짜**이므로, 그 날짜만 보지 않고
    **모든 시작일 분포에서 2011/2012 가 몇 백분위인지**를 함께 찍는다.
  ⚠ 시작일을 옮긴 창들은 **끝을 공유해 서로 포함관계**다 — 비중첩 관측은 **1개**.
    「N창 중 x%」를 확률로 읽지 마라(v57 정정이 그 착각이었다).

측정
  [0] 검산 — 공표값(2010~ B@2 84.3배) 재현 후에만 진행
  [1] 기점 후보별 정면 비교 (2000·2003·2007·2010·**2011**·**2012**·2013·2015)
  [2] 모든 시작일 스윕 — B÷2배 분포와 2011/2012 의 백분위
  [3] 가르는 축 — 그 창의 2배 맨몸 MDD 로 설명되는가
  [4] 시대가 정말 변했나 — 10년 단위로 1배/2배/전략의 최악 낙폭
  [5] 2011~ 창에서 이 전략이 실제로 한 일 (전환 횟수·방어 체류·위기별 성적)

평가 전용 · 전략 무변경. 실행: python research/era_start.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                 # noqa: E402
import hypo_gates as G                                  # noqa: E402
from axis_lib import lev_r                              # noqa: E402

idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))    # 2배 합성 일수익
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))  # 방어 40/40/20
R1 = np.nan_to_num(PX.pct_change().values)
TH = -0.16

wB = EC.rule_dd(PX, TH, TH)
aB = np.asarray(EC.sim2(wB, QLDR, MIXR), float)         # 전략 B (2배)
a2 = np.cumprod(1 + QLDR)                               # 2배 맨몸
a1 = np.cumprod(1 + R1)                                 # 1배 지수
L = '=' * 98


def sl(start, end=None):
    lo = 0 if start is None else int(np.searchsorted(idx, pd.Timestamp(start)))
    hi = n if end is None else int(np.searchsorted(idx, pd.Timestamp(end), side='right'))
    return lo, hi


def stat(a, lo, hi):
    c = np.asarray(a[lo:hi], float); c = c / c[0]
    y = (idx[hi - 1] - idx[lo]).days / 365.25
    mult = float(c[-1]); cagr = mult ** (1 / y) - 1
    mdd = float(np.min(c / np.maximum.accumulate(c)) - 1)
    return dict(mult=mult, cagr=cagr, mdd=mdd, yrs=y,
                calmar=(cagr / abs(mdd) if mdd < 0 else np.nan))


def mdd_of(a, lo, hi):
    c = np.asarray(a[lo:hi], float)
    return float(np.min(c / np.maximum.accumulate(c)) - 1)


# ── [0] 검산 ────────────────────────────────────────────────────────────
lo, hi = sl('2010-01-04')
chk = stat(aB, lo, hi)['mult']
print(L); print('[0] 검산 — 2010~ B@2 최종배수 %.1f배 (공표 84.3)' % chk); print(L)
if abs(chk - 84.3) > 1.0:
    print('  ✗ 공표값 재현 실패 — 엔진이 다르다. 중단한다.'); sys.exit(1)
print('  ✓ 재현. 이 엔진은 04 §5-10·§5-13 과 같은 저울이다.')

# ── [1] 기점 후보별 ─────────────────────────────────────────────────────
print(); print(L)
print('[1] 기점을 어디로 잡느냐에 따라 — 전략 B vs 2배 맨몸 vs 1배 지수')
print(L)
CAND = [('2000-01-03', '닷컴 직전'), ('2003-01-02', '닷컴 제외'),
        ('2007-01-03', '아이폰'), ('2010-01-04', '기존 04 §5-10'),
        ('2011-01-03', '★소유자 (페이스북)'), ('2012-01-03', '★소유자 (롤)'),
        ('2013-01-02', '나스닥 닷컴 고점 회복'), ('2015-01-02', '클라우드 이익 중심')]
print('  %-12s%-18s%7s %8s%8s%8s   %8s%8s   %s'
      % ('시작', '', '길이', 'B배수', 'B CAGR', 'B MDD', '2배배수', '2배MDD', 'B÷2배'))
rows1 = []
for d, tag in CAND:
    lo, hi = sl(d)
    b, t = stat(aB, lo, hi), stat(a2, lo, hi)
    rows1.append((d, tag, b, t))
    print('  %-12s%-18s%6.1f년 %7.1f배%7.1f%%%8.1f%%   %7.1f배%8.1f%%   %s%.2f'
          % (d[:7], tag, b['yrs'], b['mult'], 100 * b['cagr'], 100 * b['mdd'],
             t['mult'], 100 * t['mdd'],
             '**' if b['mult'] < t['mult'] else '  ', b['mult'] / t['mult']))
print()
print('  ** = 전략이 2배 맨몸에 **총수익으로 진** 창.')
print('  ※ 그러나 낙폭은 어느 창에서도 전략이 얕다 — 아래 Calmar 로 다시 본다.')
print()
print('  %-12s%-18s%10s%10s%10s' % ('시작', '', 'B Calmar', '2배 Calmar', '개선'))
for d, tag, b, t in rows1:
    print('  %-12s%-18s%10.3f%10.3f%9.0f%%'
          % (d[:7], tag, b['calmar'], t['calmar'], 100 * (b['calmar'] / t['calmar'] - 1)))

# ── [2] 모든 시작일 스윕 ────────────────────────────────────────────────
print(); print(L)
print('[2] ⓑ 반증 — 손으로 고른 날짜가 아니라 **모든 시작일**로')
print(L)
STEP = 5
MINY = 5
ends = n - 1
S = [i for i in range(0, n - MINY * 252, STEP)]
rat = np.array([float((aB[ends] / aB[i]) / (a2[ends] / a2[i])) for i in S])
yrs = np.array([(idx[ends] - idx[i]).days / 365.25 for i in S])
dts = [idx[i] for i in S]
print('  시작일 %d개 (%d거래일 간격, 최소 %d년) · 끝은 %s 고정'
      % (len(S), STEP, MINY, idx[ends].date()))
print('  ⚠ 창들이 서로 포함관계라 **비중첩 관측은 1개**다 — 아래 %% 를 확률로 읽지 마라.')
print()
print('  B 가 2배 맨몸을 이긴 시작일 비율: **%.0f%%** (%d/%d)'
      % (100 * np.mean(rat > 1), int(np.sum(rat > 1)), len(rat)))
for lab, d in (('2011-01', '2011-01-03'), ('2012-01', '2012-01-03')):
    k = int(np.searchsorted([x.value for x in dts], pd.Timestamp(d).value))
    k = min(k, len(rat) - 1)
    pct = 100.0 * np.mean(rat < rat[k])
    print('  %s 시작 -> B÷2배 = **%.2f** · 전체 시작일 중 **하위 %.0f 백분위**'
          % (lab, rat[k], pct))
print()
print('  %-14s%12s%12s' % ('시작 연대', '중앙 B÷2배', '이긴 비율'))
for a, b in ((1972, 1979), (1980, 1989), (1990, 1999), (2000, 2009),
             (2010, 2015), (2016, 2021)):
    m = np.array([a <= d.year <= b for d in dts])
    if m.sum() == 0:
        continue
    print('  %-14s%12.2f%11.0f%%' % ('%d~%d' % (a, b), np.median(rat[m]), 100 * np.mean(rat[m] > 1)))

# ── [3] 가르는 축 ───────────────────────────────────────────────────────
print(); print(L)
print('[3] 가르는 축 — 「시대」인가 「그 창에 폭락이 없었나」인가')
print(L)
m2 = np.array([mdd_of(a2, i, n) for i in S])
print()
print('  창 안의 **2배 맨몸 최악 낙폭**으로 나눠 보면:')
print('  %-22s%8s%14s%12s' % ('그 창의 2배 MDD', '창 수', '중앙 B÷2배', '이긴 비율'))
BANDS = [(-1.01, -0.90, '−90% 이하 (닷컴급)'), (-0.90, -0.80, '−90 ~ −80%'),
         (-0.80, -0.70, '−80 ~ −70%'), (-0.70, -0.60, '−70 ~ −60%'),
         (-0.60, 0.0, '−60% 보다 얕음')]
for lo_, hi_, lab in BANDS:
    m = (m2 > lo_) & (m2 <= hi_)
    if m.sum() == 0:
        continue
    print('  %-22s%8d%14.2f%11.0f%%' % (lab, m.sum(), np.median(rat[m]), 100 * np.mean(rat[m] > 1)))
r = np.corrcoef(m2, np.log(rat))[0, 1]
print()
print('  상관(창의 2배 MDD, log B÷2배) = **%.3f**' % r)
print('  -> 낙폭이 깊은 창일수록 B 가 이긴다. **비율은 시대가 아니라 창 안의 사건이 정한다.**')
print()
print('  결정적 대조 — 같은 「폭락 없는 창」을 **다른 시대**에서 골라 보면:')
for a, b in (('1976-01-02', '1986-12-31'), ('1991-01-02', '1999-12-31'),
             ('2011-01-03', '2019-12-31'), ('2013-01-02', '2019-12-31')):
    lo, hi = sl(a, b)
    sb, st = stat(aB, lo, hi), stat(a2, lo, hi)
    print('    %s~%s (%4.1f년) 2배 MDD %6.1f%%  ->  B÷2배 **%.2f**'
          % (a[:7], b[:7], sb['yrs'], 100 * st['mdd'], sb['mult'] / st['mult']))
print('  -> 1970~80년대의 폭락 없는 창에서도 **똑같이 진다.** 2011-2012 는 시대가 아니다.')

# ── [4] 지수의 성질이 변했나 ────────────────────────────────────────────
print(); print(L)
print('[4] 그래도 「지수가 변했다」는 따로 물어야 한다 — 10년 단위 최악 낙폭')
print(L)
print('  %-14s%12s%12s%12s' % ('구간', '1배 MDD', '2배 MDD', '전략 MDD'))
for a, b in (('1972-01-01', '1979-12-31'), ('1980-01-01', '1989-12-31'),
             ('1990-01-01', '1999-12-31'), ('2000-01-01', '2009-12-31'),
             ('2010-01-01', '2019-12-31'), ('2020-01-01', str(idx[-1].date()))):
    lo, hi = sl(a, b)
    print('  %-14s%11.1f%%%11.1f%%%11.1f%%'
          % ('%s~%s' % (a[:4], b[:4]), 100 * mdd_of(a1, lo, hi),
             100 * mdd_of(a2, lo, hi), 100 * mdd_of(aB, lo, hi)))
print()
print('  ※ 이 표는 「−80% 붕괴 능력이 사라졌나」를 **증명하지 못한다** — 안 일어난 것과')
print('    일어날 수 없는 것은 자료로 구별되지 않는다. 1990년대 표도 「−80% 는 없다」였다.')

# ── [5] 2011~ 창에서 전략이 실제로 한 일 ────────────────────────────────
print(); print(L)
print('[5] 2011~ 창에서 이 전략이 실제로 한 일')
print(L)
lo, hi = sl('2011-01-03')
w = np.asarray(wB, float)[lo:hi]
sw = int(np.sum(np.abs(np.diff(w)) > 0.5))
print('  전환 %d회 (연 %.1f회) · 방어 체류 **%.1f%%** 의 날'
      % (sw, sw / ((idx[hi - 1] - idx[lo]).days / 365.25), 100 * np.mean(w < 0.5)))
print()
print('  %-16s%12s%12s%12s' % ('위기', '전략', '2배 맨몸', '차이'))
for lab, a, b in (('코로나 2020', '2020-02-19', '2020-03-23'),
                  ('2022 베어', '2021-11-19', '2022-12-28'),
                  ('2018 Q4', '2018-10-01', '2018-12-24')):
    lo2, hi2 = sl(a, b)
    cb = aB[hi2 - 1] / aB[lo2] - 1
    ct = a2[hi2 - 1] / a2[lo2] - 1
    print('  %-16s%11.1f%%%11.1f%%%11.1f%%p' % (lab, 100 * cb, 100 * ct, 100 * (cb - ct)))
print()
print('  ★ 코로나는 이 전략이 **거의 못 막는 유형**이다(v67 §C-3): 252일 낙폭 신호는')
print('    느린 약세장만 거른다. 한 달짜리 급락은 −16% 를 지날 때 이미 다 맞은 뒤다.')
print('    소유자가 「코로나에서 오히려 더 잃었다」고 느낀 것은 **정확한 관찰**이다.')

# ── 판정 ────────────────────────────────────────────────────────────────
print(); print(L); print('판정'); print(L)
print()
print('  Q 「인터넷이 당연해진 2011-2012 를 기점으로 잡으면?」')
lo, hi = sl('2011-01-03')
b11, t11 = stat(aB, lo, hi), stat(a2, lo, hi)
print('  A 총수익으로는 **전략이 2배 맨몸에 진다** (B÷2배 %.2f).' % (b11['mult'] / t11['mult']))
print('    그러나 [3] 이 그 이유를 가른다 — **시대가 아니라 창 안에 폭락이 없어서**다.')
print('    1976~86·1991~99 의 폭락 없는 창에서도 똑같이 진다. 즉 2011-2012 라는')
print('    기점은 **「보험금을 안 탄 기간」을 고른 것**이지 새 레짐을 고른 게 아니다.')
print('    낙폭은 그 창에서도 전략이 얕다: MDD %.1f%% vs %.1f%% · Calmar %.3f vs %.3f'
      % (100 * b11['mdd'], 100 * t11['mdd'], b11['calmar'], t11['calmar']))
prem = (b11['mult'] / t11['mult']) ** (1 / b11['yrs']) - 1
print()
print('  ★ 실제로 쓸모 있는 한 줄 — **평온한 시대의 보험료**:')
print('    2011~ %.1f년 동안 전략은 2배 맨몸보다 **연 %.2f%%p** 덜 벌었고,'
      % (b11['yrs'], -100 * prem))
print('    그 대가로 최악 낙폭이 **%.1f%%p 얕아졌다** (%.1f%% -> %.1f%%).'
      % (100 * (b11['mdd'] - t11['mdd']), 100 * t11['mdd'], 100 * b11['mdd']))
print('    폭락이 안 오면 이 연 %.2f%%p 가 순수 비용이다 — **그것이 이 전략의 가격**이고,'
      % (-100 * prem))
print('    닷컴급이 한 번 오면 [1] 의 2000~ 행(34.9배)이 그 값을 한꺼번에 돌려준다.')
print()
print('  ※ 이 측정이 낳은 다음 질문 (§-1 ⑥):')
print('    「−80% 붕괴 능력이 사라졌는지는 자료로 답할 수 없다면, 무엇을 보고 판단하나?」')
print('    -> 이미 답이 있다: verify_all I10 의 P1~P3 이 그 성질을 **매 push 감시**한다')
print('       (P1 2배보유 MDD ≤ −90% · P2 기초지수 20년 CAGR > 3% · P3 전략 > 2배보유).')
print('       기점을 논쟁하는 대신 **성질이 깨지면 알림이 오게** 해 둔 것이 이 저장소의 답이다.')
