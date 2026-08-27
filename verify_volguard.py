# -*- coding: utf-8 -*-
"""
[검증] v32 변동성 가드 관련 수치의 독립 재현 및 오류 점검

이번 세션에서 이미 세 번 틀렸다:
  (1) v31 이 격자 단면을 잘못 봐 '첨탑' 오판
  (2) 적립식 MDD 를 초기 잔고(1단위) 등락까지 세어 -69~75% 로 부풀림
  (3) 중앙값 대신 최악 창 값을 인용

그래서 결론 수치를 **처음부터 다시** 만들고, 프로젝트 자체 엔진과 대조한다.
통과 기준을 먼저 못박고, 하나라도 실패하면 FAIL 을 찍는다.

  G1  내 sim() 이 reentry_lib.run() 을 오차 0 으로 재현하는가
  G2  verify.py 의 공표 수치(140.0배 / MDD -46.6%)를 재현하는가
  G3  가드 신호에 미래참조가 없는가 (신호를 하루 더 늦춰도 결과가 크게 안 변해야)
  G4  적립식 함수가 axis_isa / axis_accum2 규약과 같은가
  G5  MDD 정의별 수치 (초기허수 포함 / 납입후 / 원금대비)
  G6  최종 결론표 재산출 + 중앙값·최악값 라벨 확인
"""
import sys
import numpy as np
import pandas as pd

import hist_defasset as DA
import hist_defensive as DF
import hist_krfinal as KF
from axis_lib import COST, rule_w
from axis_defmix import mix_monthly_from
import axis_volguard as V

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

FAILS = []


def gate(name, ok, detail=''):
    tag = 'PASS' if ok else '**FAIL**'
    print(f"  [{tag}] {name}   {detail}")
    if not ok:
        FAILS.append(name)


# ================================================================= 준비
D = DF.build('chain')
idx = D['idx']
ddq = D['ddv']
Dk, kidx, lev2, lev1, dfk, fr = KF.build_krw('chain')
kcomp = {'div': np.asarray(dfk, dtype=float),
         'ust5': (1 + DA.ust_tr(kidx, 5, 'TNX', futures=True, fee=DA.UST_FEE)) * (1 + fr) - 1,
         'gold': (1 + DA.gold_r(kidx)) * (1 + fr) - 1}
kdefr = mix_monthly_from(kcomp, V.W4020, kidx)
MONTH = pd.Series(kidx).dt.to_period('M').values
FXS = int(kidx.searchsorted(pd.Timestamp('1981-04-13')))
CT = 0.002

BW = {'A': rule_w(ddq, -0.16, -0.11), 'B': rule_w(ddq, -0.16, -0.16)}
SET = {'(14,p90,-2%)': (14, 0.90, -0.02), '(10,p92.5,-3%)': (10, 0.925, -0.03)}
GW = {}
for nm, (lb, q, g) in SET.items():
    r_ = V.zc(D['px'].pct_change().rolling(lb, min_periods=lb).std().values)
    t_ = r_ >= V.exp_q(r_, q)
    GW[nm] = {'A': V.guard_w(ddq, t_, -0.16, -0.11, gate=g),
              'B': V.guard_w(ddq, t_, -0.16, -0.16, gate=g),
              'trig': t_, 'gate': g}


print("=" * 92)
print("G1. 내 sim() vs 프로젝트 엔진 reentry_lib.run()")
print("=" * 92)
from axis_lib import check as lib_check
ok = lib_check(D)
gate('axis_lib.check (run vs sim 오차 0)', ok)

# 내 V.sim 이 axis_lib.sim 과 같은가
from axis_lib import sim as lib_sim
for rule, w in BW.items():
    c1, _ = lib_sim(D, w)                       # 방어=schdr(배당체인)
    c2 = V.sim(D['qldr'], D['schdr'], w)
    err = abs(float(c1.iloc[-1]) / c2[-1] - 1)
    gate(f'V.sim == axis_lib.sim (규칙 {rule})', err < 1e-12, f'오차 {err:.1e}')


print("\n" + "=" * 92)
print("G2. verify.py 공표 수치 재현 (실물 QQQ/QLD/SCHD, 2000-, 방어=SCHD)")
print("=" * 92)


def load(p, c='Close'):
    d = pd.read_csv(p)
    d['Date'] = pd.to_datetime(d['Date'])
    return d.set_index('Date')[c].sort_index()


qqq, qld, schd = load('qqq_us_d.csv'), load('qld_us_d.csv'), load('schd_us_d.csv')
# verify.py 규약 그대로 재현한다. 두 가지를 빼먹으면 안 된다:
#  (a) QLD 는 2006-06 상장이라 그 이전을 2xQQQ - 합성비용 으로 **연장**한다
#  (b) SCHD 는 2011-10 상장이라 그 이전을 현금 CASH_RATE 로 대용한다
# 처음에 (a)를 빼먹어 93.6배, (b)만 고쳐 96.4배가 나왔다 — 둘 다 하네스 오류였다.
CASH_RATE = 0.02
qqq_r = qqq.pct_change().dropna()
y = qld.pct_change().dropna()
ov = qqq_r.index.intersection(y.index)
c_daily = (2 * qqq_r.reindex(ov) - y.reindex(ov)).mean()
pre = qqq_r.index[qqq_r.index < pd.Timestamp('2006-06-22')]
synth = (2 * qqq_r.reindex(pre) - c_daily).dropna()
full = pd.concat([synth, y])
full = full[~full.index.duplicated()].sort_index()
qld_ext = (1 + full).cumprod()
ix = qqq.index.intersection(qld_ext.index).sort_values()
ix = ix[ix >= pd.Timestamp('2000-01-03')]
qqq2 = qqq.reindex(ix)
dd2 = (qqq2 / qqq2.rolling(252, min_periods=60).max() - 1).fillna(0).values
qldr2 = qld_ext.reindex(ix).pct_change().fillna(0).values
scr = schd.reindex(ix).pct_change().fillna(CASH_RATE / 252).values
w2 = rule_w(dd2, -0.16, -0.11)
c2 = V.sim(qldr2, scr, w2, cost=0.001)
m2 = (c2 / np.maximum.accumulate(c2) - 1).min()
print(f"  재현: 최종 {c2[-1]:.1f}배  MDD {m2*100:.1f}%   (공표 140.0배 / -46.6%)")
gate('verify.py 최종배수 재현 (±3%)', abs(c2[-1] / 140.0 - 1) < 0.03, f'{c2[-1]:.1f}배')
gate('verify.py MDD 재현 (±1.5%p)', abs(abs(m2) * 100 - 46.6) < 1.5, f'{m2*100:.1f}%')


print("\n" + "=" * 92)
print("G3. 미래참조 점검 — 가드 신호를 하루 더 늦춰본다")
print("=" * 92)
print("  진짜 신호면 하루 늦춰도 방향이 유지된다. 미래를 봤다면 여기서 무너진다.")
for nm in SET:
    t_ = GW[nm]['trig']
    g = GW[nm]['gate']
    t_lag = np.r_[False, t_[:-1]]                    # 하루 더 지연
    for rule in ('A', 'B'):
        e, x = (-0.16, -0.11) if rule == 'A' else (-0.16, -0.16)
        c0 = V.sim(lev2, kdefr, BW[rule], lo=FXS)
        c1 = V.sim(lev2, kdefr, GW[nm][rule], lo=FXS)
        c2_ = V.sim(lev2, kdefr, V.guard_w(ddq, t_lag, e, x, gate=g), lo=FXS)
        m0 = (c0 / np.maximum.accumulate(c0) - 1).min()
        m1 = (c1 / np.maximum.accumulate(c1) - 1).min()
        m2_ = (c2_ / np.maximum.accumulate(c2_) - 1).min()
        print(f"    {rule} {nm}: MDD 기준 {m0*100:.2f}% / 가드 {m1*100:.2f}% / 하루지연 {m2_*100:.2f}%")
        gate(f'{rule} {nm} 하루지연에도 MDD 개선 유지',
             abs(m2_) < abs(m0), f'{-(abs(m2_)-abs(m0))*100:+.2f}p')


print("\n" + "=" * 92)
print("G4. 적립식 함수 규약 검산")
print("=" * 92)


def path(w, lo, hi, mp=60, cost=CT):
    """[v33 정정] 전환을 그날 수익 적용 전에. 규약 pos = w.shift(1)."""
    R = C = P = 0.0
    prev = w[lo]
    v, p = [], []
    mi = -1
    for i in range(lo, hi):
        pos = w[i - 1] if i > lo else w[lo]
        if pos != prev:
            if pos >= 1:
                R += C * (1 - cost); C = 0.0
            else:
                C += R * (1 - cost); R = 0.0
            prev = pos
        R *= (1 + lev2[i]); C *= (1 + kdefr[i])
        if i > lo and MONTH[i] != MONTH[i - 1]:
            mi += 1
            if mi < mp:
                P += 1.0
                if pos >= 1:
                    R += 1.0
                else:
                    C += 1.0
        v.append(R + C); p.append(P)
    return np.array(v), np.array(p)


# 검산 1: 수익률 0 + 전환 0회 이면 최종 = 납입액
zero = np.zeros(len(kidx))
sav_l, sav_d = lev2.copy(), kdefr.copy()
try:
    lev2, kdefr = zero, zero
    flat = np.ones(len(ddq))                              # 전환이 없는 비중경로
    v, p = path(flat, FXS, FXS + 20 * 252)
    gate('수익률0·전환0 이면 최종 == 납입액', abs(v[-1] - p[-1]) < 1e-9,
         f'{v[-1]:.6f} vs {p[-1]:.1f}')
    # 전환이 있으면 전환비용만큼 줄어야 한다(줄어드는 게 정상)
    v2, p2 = path(BW['B'], FXS, FXS + 20 * 252)
    nsw = int(np.abs(np.diff(BW['B'][FXS:FXS + 20 * 252])).sum())
    gate('수익률0·전환 있으면 납입액보다 작다', v2[-1] < p2[-1],
         f'{v2[-1]:.2f} < {p2[-1]:.0f} (전환 {nsw}회)')
finally:
    lev2, kdefr = sav_l, sav_d

# 검산 2: 납입 1회(mp=1)면 그 시점부터의 거치식과 **오차 0** 이어야 한다
v, p = path(BW['B'], FXS, FXS + 20 * 252, mp=1)
k = int(np.where(p > 0)[0][0])
c = V.sim(lev2, kdefr, BW['B'], cost=CT, lo=FXS + k, hi=FXS + 20 * 252)
err = abs((v[-1] / v[k]) / (c[-1] / c[0]) - 1)
gate('납입 1회 == 거치식 (오차 0)', err < 1e-9,
     f'{v[-1]/v[k]:.4f} vs {c[-1]/c[0]:.4f}  오차 {err:.1e}')


print("\n" + "=" * 92)
print("G5. MDD 정의별 수치 — 어느 것을 인용하느냐로 -23% 도 -75% 도 된다")
print("=" * 92)
L = 20 * 252
print(f"  {'':<22}{'①초기포함(허수)':>16}{'②납입후':>12}{'③원금대비':>12}")
for rule in ('A', 'B'):
    for nm in ['기준'] + list(SET):
        W = BW[rule] if nm == '기준' else GW[nm][rule]
        a, b, c_ = [], [], []
        for s in range(FXS, len(kidx) - L, 126):
            v, p = path(W, s, s + L)
            vv = v[v > 0]
            a.append(float((vv / np.maximum.accumulate(vv) - 1).min()))
            k = np.searchsorted(p, 60.0, side='left')
            w2_ = v[k:]
            b.append(float((w2_ / np.maximum.accumulate(w2_) - 1).min()))
            ok_ = p > 0
            c_.append(float((v[ok_] / p[ok_] - 1).min()))
        lab = f"{rule} {nm}" if nm == '기준' else f"{rule} +{nm}"
        print(f"  {lab:<22}{np.median(a)*100:15.1f}%{np.median(b)*100:11.1f}%{np.median(c_)*100:11.1f}%")
print("  ※ ①과 ②가 같으면 초기 허수가 중앙값에는 영향이 없다는 뜻(최악값에만 영향)")


print("\n" + "=" * 92)
print("G6. 최종 결론표 재산출 (독립 계산)")
print("=" * 92)
print(f"  적립식 20년 창 · 원화 · 월 정액 60개월 · 편도비용 {CT*100:.1f}%")
print(f"  {'':<22}{'중앙':>9}{'차이':>9}{'승률':>8}{'5분위':>8}{'최악':>8}{'납입후MDD':>11}{'원금대비':>10}")
res = {}
for rule in ('A', 'B'):
    store = {}
    for nm in ['기준'] + list(SET):
        W = BW[rule] if nm == '기준' else GW[nm][rule]
        f, m, pr = [], [], []
        for s in range(FXS, len(kidx) - L, 126):
            v, p = path(W, s, s + L)
            f.append(v[-1] / p[-1])
            k = np.searchsorted(p, 60.0, side='left')
            vv = v[k:]
            m.append(float((vv / np.maximum.accumulate(vv) - 1).min()))
            ok_ = p > 0
            pr.append(float((v[ok_] / p[ok_] - 1).min()))
        store[nm] = (np.array(f), np.array(m), np.array(pr))
    b = store['기준'][0]
    for nm in ['기준'] + list(SET):
        f, m, pr = store[nm]
        lab = f"{rule} {nm}" if nm == '기준' else f"{rule} +{nm}"
        d = f"{(np.median(f)/np.median(b)-1)*100:+8.1f}%" if nm != '기준' else f"{'-':>9}"
        wr = f"{(f>b).mean()*100:7.1f}%" if nm != '기준' else f"{'-':>8}"
        print(f"  {lab:<22}{np.median(f):9.2f}{d}{wr}{np.percentile(f,5):8.2f}{f.min():8.2f}"
              f"{np.median(m)*100:10.1f}%{np.median(pr)*100:9.1f}%")
    res[rule] = store
    print()

print("=" * 92)
if FAILS:
    print(f"** 실패 {len(FAILS)}건 **")
    for f_ in FAILS:
        print(f"   - {f_}")
else:
    print("모든 관문 통과. 위 표의 수치는 프로젝트 엔진과 정합한다.")
print("=" * 92)
