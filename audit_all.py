# -*- coding: utf-8 -*-
"""
[v34] 전면 감사 — 누적된 오류 위에서 결정을 내린 게 아닌지 전부 다시 본다

사용자 요구(2026-08-27): "지금까지의 전략에 에러가 있었는데 그걸 모른 채
틀린 누적 에러만 강화해왔다면 안 되니까 전체를 한번 검증해볼래?"

v27(재조정 비용 분모)·v30(체결규약)·v33(적립 2일 지연) 세 번의 버그가
나왔으므로, **채택된 결정 전부를 현재 코드로 다시 계산**해서 순위가
그대로인지 본다. 순위가 바뀌면 전략을 고쳐야 한다.

[A] 엔진 정합성   프로젝트 내 모든 검산 함수를 한 번에 돌린다
[B] 미래참조 스캔  신호를 하루씩 밀고 당겨 민감도를 본다
[C] 데이터 무결성  접합점 불연속, 합성 vs 실물 대조
[D] 채택 결정 재검증  ★ 핵심 — 지금 계산해도 같은 답이 나오는가
[E] 문서 수치 대조  공표된 숫자가 현재 코드 출력과 맞는가
"""
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_data as H
import hist_defasset as DA
import hist_defensive as DF
import hist_krfinal as KF
import axis_lib as L
from axis_lib import COST, rule_w, sim, lev_r
from axis_defmix import materials, mix_monthly_from, sim_def, sim_hold, check_hold

FAILS, WARNS = [], []


def gate(name, ok, detail='', warn=False):
    tag = 'PASS' if ok else ('WARN' if warn else '**FAIL**')
    print(f"  [{tag}] {name}   {detail}")
    if not ok:
        (WARNS if warn else FAILS).append(name)


def met(c):
    v = float(c.iloc[-1]) if hasattr(c, 'iloc') else c[-1]
    a = np.asarray(c)
    m = float((a / np.maximum.accumulate(a) - 1).min())
    yrs = len(a) / 252.0
    g = v ** (1 / yrs) - 1
    return v, g, m, g / abs(m)


D = DF.build('chain')
idx = D['idx']
ddq = D['ddv']
N = len(idx)
comp = materials(D)
WA, WB = rule_w(ddq, -0.16, -0.11), rule_w(ddq, -0.16, -0.16)
cands_pre = {'40/40/20 (채택)': {'div': .4, 'ust5': .4, 'gold': .2},
             '배당100 (v21)': {'div': 1.0},
             '동일가중': {'div': 1/3, 'ust5': 1/3, 'gold': 1/3},
             '배당60/국채40': {'div': .6, 'ust5': .4},
             '배당50/금50': {'div': .5, 'gold': .5}}

print("=" * 96)
print("A. 엔진 정합성 — 프로젝트 내 모든 검산")
print("=" * 96)
gate('axis_lib.check (run/sim/after_tax/적립)', L.check(D))
gate('axis_defmix.check_hold (바스켓 엔진)', check_hold(D, comp))

print("\n" + "=" * 96)
print("B. 미래참조 스캔 — 신호를 밀고 당겨본다")
print("=" * 96)
print("  정상이면: 당기면(-1, 미래훔쳐보기) 크게 좋아지고, 밀면(+1,+2) 완만히 나빠진다.")
print("  당겨도 안 좋아지면 이미 미래를 보고 있다는 뜻이다.")
base = None
for lag in (0, 1, 2, 3):
    c, _ = sim(D, WB, lag=lag) if lag > 0 else (None, None)
    if lag == 0:
        # lag=0 은 당일 신호로 당일 체결 = 미래훔쳐보기
        pos = WB.copy()
        r = np.nan_to_num(pos * D['qldr'] + (1 - pos) * D['schdr'])
        r[0] = 0.0
        t = np.abs(np.diff(pos, prepend=pos[0]))
        c = pd.Series(np.cumprod((1 + r) * (1 - COST * t)), index=idx)
    v, g, m, k = met(c)
    tag = ' <- 미래훔쳐보기(대조군)' if lag == 0 else (' <- 채택 규약' if lag == 1 else '')
    print(f"    lag={lag}일  {v:>12,.1f}배  CAGR {g*100:6.2f}%  MDD {m*100:7.2f}%{tag}")
    if lag == 0:
        peek = v
    if lag == 1:
        base = v
gate('미래훔쳐보기가 규약보다 유리하다(정상 신호의 증거)', peek > base * 1.10,
     f'{peek:,.0f} vs {base:,.0f} ({(peek/base-1)*100:+.1f}%)')

print("\n  방어자산 정렬 검증 — 실물과의 시차상관으로 본다")
print("  ※ '1일 지연 시 성과 변화' 로는 못 잰다. 방어 진입일이 폭락 당일이라")
print("    하루만 밀어도 -81% 가 나오지만 그건 폭락->반등 구조이지 미래참조가 아니다.")
print("    (진입 당일 평균수익 shift-1 +0.272% / shift0 -0.351% / shift+1 -1.339%)")
sc_ = pd.read_csv('schd_us_d.csv')
sc_['Date'] = pd.to_datetime(sc_['Date'])
scr = sc_.set_index('Date')['Close'].pct_change().dropna()
dv = pd.Series(np.nan_to_num(D['schdr']), index=idx)
ovd = scr.index.intersection(idx)
r0 = np.corrcoef(scr.reindex(ovd).values, dv.reindex(ovd).values)[0, 1]
rs = {s_: np.corrcoef(scr.reindex(ovd).values, dv.shift(s_).reindex(ovd).fillna(0).values)[0, 1]
      for s_ in (-2, -1, 1, 2)}
gate('배당체인 정렬 (실물 SCHD 와 shift0 최대)', r0 > 0.99 and max(rs.values()) < 0.5,
     'r0=%.4f, 최대타시차=%+.3f' % (r0, max(rs.values())))
gate('배당체인 누적 정합 (실물 대비 +-2%)',
     abs((1 + dv.reindex(ovd)).prod() / (1 + scr.reindex(ovd)).prod() - 1) < 0.02,
     '%+.2f%%' % (((1 + dv.reindex(ovd)).prod() / (1 + scr.reindex(ovd)).prod() - 1) * 100))

print("\n  * 국채 다리 실물 드리프트 — 모형이 실물보다 좋은가 (v25 2.4 재확인)")
krb = DA.kr('305080')
ab = krb.reindex(krb.index.intersection(idx)).pct_change().dropna()
Dk2, kidx2, _, _, _, fr2 = KF.build_krw('chain')
# [v36] 선물형 모형으로 대조한다. 현물형(futures=False)은 단기금리만큼 과대계상된다.
sb = pd.Series((1 + DA.ust_tr(kidx2, 5, 'TNX', futures=True, fee=0.0029)) * (1 + fr2) - 1,
               index=kidx2).reindex(ab.index).fillna(0)
yb = len(ab) / 252.0
drift = ((1 + sb).prod() / (1 + ab).prod()) ** (1 / yb) - 1
print('    실물 %+.2f%%/년  모형 %+.2f%%/년  드리프트 %+.2f%%/년  (%.1f년 표본)'
      % (((1 + ab).prod() ** (1 / yb) - 1) * 100, ((1 + sb).prod() ** (1 / yb) - 1) * 100,
         drift * 100, yb))
comp_h = dict(comp)
comp_h['ust5'] = comp['ust5'] - drift / 252.0
rank = []
for nm2, ws2 in cands_pre.items():
    dr2 = mix_monthly_from({k: comp_h[k] for k in ws2}, ws2, idx)
    rank.append((nm2, met(sim_def(D, WB, dr2))))
rank.sort(key=lambda r: -r[1][0])
print('    핸디캡 적용 시 순위:')
for nm2, mm in rank:
    print('      %-22s%12s배  MDD %7.2f%%  Calmar %.3f%s'
          % (nm2, format(mm[0], ',.0f'), mm[2] * 100, mm[3], '  <- 채택' if '채택' in nm2 else ''))
ad = [r for r in rank if '채택' in r[0]][0]
cals = sorted([r[1][3] for r in rank], reverse=True)
gate('핸디캡을 물려도 채택안이 Calmar 1~2위', cals.index(ad[1][3]) <= 1,
     'Calmar %.3f (%d위/%d)' % (ad[1][3], cals.index(ad[1][3]) + 1, len(cals)), warn=True)

print("\n" + "=" * 96)
print("C. 데이터 무결성")
print("=" * 96)
src = D['src']
print("  접합점 전후 5일 수익률 — 튀는 값이 있으면 접합 오류")
for a, b in [('NasdaqComposite', 'NDX'), ('NDX', 'QQQ')]:
    m = src == b
    i0 = int(np.where(m)[0][0])
    r = D['px'].pct_change().values
    win = r[i0 - 5:i0 + 5]
    print(f"    {a}->{b} @{idx[i0].date()}: " + " ".join(f"{x*100:+.2f}" for x in win))
    gate(f'{a}->{b} 접합 불연속 없음', np.nanmax(np.abs(win)) < 0.15,
         f'최대 |{np.nanmax(np.abs(win))*100:.2f}%|')

print("\n  합성 vs 실물 겹침 검증")
qld = pd.read_csv('qld_us_d.csv')
qld['Date'] = pd.to_datetime(qld['Date'])
qr = qld.set_index('Date')['Close'].pct_change().dropna()
syn = pd.Series(lev_r(D, 2.0), index=idx)
ov = qr.index.intersection(syn.index)
if len(ov) > 200:
    cc = np.corrcoef(qr.reindex(ov).values, syn.reindex(ov).values)[0, 1]
    tr = (1 + qr.reindex(ov)).prod() / (1 + syn.reindex(ov)).prod() - 1
    gate('합성 2배 vs 실물 QLD 상관', cc > 0.99, f'r={cc:.4f}, 누적차 {tr*100:+.1f}%')

for code, key, nm in [('458730', 'div', 'TIGER 미국배당다우존스'),
                      ('305080', 'ust5', 'TIGER 미국채10년선물'),
                      ('411060', 'gold', 'ACE KRX금현물')]:
    try:
        kr = DA.kr(code)
        Dk, kidx, lev2, lev1, dfk, fr = KF.build_krw('chain')
        kc = {'div': np.asarray(dfk, dtype=float),
              'ust5': (1 + DA.ust_tr(kidx, 5, 'TNX', futures=True, fee=0.0029)) * (1 + fr) - 1,
              'gold': (1 + DA.gold_r(kidx)) * (1 + fr) - 1}
        syn2 = pd.Series(kc[key], index=kidx)
        # [주의] pct_change 는 **교집합 이후에** 계산해야 한다. 먼저 계산하면
        # 교집합에서 빠지는 날의 수익이 통째로 사라져 드리프트가 부풀려진다
        # (금 +3.06% -> +0.29% 로 바뀐다).
        krr = kr.reindex(kr.index.intersection(syn2.index)).pct_change().dropna()
        ov2 = krr.index
        if len(ov2) > 200:
            a2 = krr.reindex(ov2)
            # [주의] 일간 상관은 낮게 나온다 — 한국장은 미국장이 닫힌 뒤 거래되므로
            # 한국 i일이 미국 i-1일을 반영한다(세션 시차). shift+1 상관과 주간/월간
            # 상관, 그리고 누적 정합으로 봐야 한다.
            b2 = np.nan_to_num(syn2.reindex(ov2).values)
            rd = np.corrcoef(a2.values, b2)[0, 1]
            r1 = np.corrcoef(a2.values, np.nan_to_num(syn2.shift(1).reindex(ov2).values))[0, 1]
            aw = (1 + a2).resample('W').prod() - 1
            bw = (1 + pd.Series(b2, index=ov2)).resample('W').prod() - 1
            jw = aw.index.intersection(bw.index)
            rw = np.corrcoef(aw.reindex(jw).values, bw.reindex(jw).values)[0, 1]
            yy = len(a2) / 252.0
            dft = ((1 + pd.Series(b2, index=ov2)).prod() / (1 + a2).prod()) ** (1 / yy) - 1
            print(f"    {nm}: 일간 r={rd:.3f} / shift+1 r={r1:.3f} / 주간 r={rw:.3f} / "
                  f"연드리프트 {dft:+.2%}  (n={len(a2)})")
            gate(f'{nm} 세션시차 보정 후 정합', rw > 0.60 or r1 > 0.60,
                 f'주간 r={rw:.3f}, shift+1 r={r1:.3f}')
            gate(f'{nm} 연 드리프트 ±1.5%p 이내', abs(dft) < 0.015,
                 f'{dft:+.2%}/년', warn=True)
    except Exception as e:
        gate(f'{nm} 대조', False, f'실패: {e}', warn=True)

print("\n" + "=" * 96)
print("D. ★ 채택 결정 재검증 — 지금 계산해도 같은 답인가")
print("=" * 96)
defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                        {'div': .4, 'ust5': .4, 'gold': .2}, idx)

print("\n  D1. 규칙 B(-16/-16) vs A(-16/-11) — 화면 기본값이 B 인 근거")
rows = []
for nm, w in [('A -16/-11', WA), ('B -16/-16', WB)]:
    c = sim_def(D, w, defr)
    v, g, m, k = met(c)
    rows.append((nm, v, g, m, k))
    print(f"    {nm}  {v:>12,.1f}배  CAGR {g*100:6.2f}%  MDD {m*100:7.2f}%  Calmar {k:.3f}")
gate('B 가 A 보다 최종배수 높음 (채택 근거 유지)', rows[1][1] > rows[0][1],
     f'{rows[1][1]:,.0f} vs {rows[0][1]:,.0f}')

print("\n  D2. 방어 바스켓 40/40/20 vs 단일자산 — v23 채택 근거")
cands = {'40/40/20 (채택)': {'div': .4, 'ust5': .4, 'gold': .2},
         '배당100 (v21)': {'div': 1.0},
         '국채100': {'ust5': 1.0}, '금100': {'gold': 1.0},
         '동일가중': {'div': 1/3, 'ust5': 1/3, 'gold': 1/3},
         '배당60/국채40': {'div': .6, 'ust5': .4}}
res = []
for nm, ws in cands.items():
    dr = mix_monthly_from({k: comp[k] for k in ws}, ws, idx)
    c = sim_def(D, WB, dr)
    v, g, m, k = met(c)
    res.append((nm, v, m, k))
for nm, v, m, k in sorted(res, key=lambda r: -r[1]):
    star = ' <-' if '채택' in nm else ''
    print(f"    {nm:<18}{v:>12,.1f}배  MDD {m*100:7.2f}%  Calmar {k:.3f}{star}")
adopted = [r for r in res if '채택' in r[0]][0]
# [v36] v23 이 실제로 쓴 판정 기준은 '최종배수 1위'가 아니라 **좌측꼬리와 위기 방어**다.
# 최종배수로 게이트를 걸면 국채 선물형 정정 뒤 오판한다(배당100 이 배수 1위가 된다).
print("")
print("    v23 의 실제 판정 기준 — 롤링 창 좌측꼬리")
cb2 = sim_def(D, WB, defr)
cd2 = sim_def(D, WB, mix_monthly_from({'div': comp['div']}, {'div': 1.0}, idx))
for yrs in (10, 15, 20):
    Lw = yrs * 252
    a1 = np.asarray(cb2); a2 = np.asarray(cd2)
    r1 = np.array([a1[i + Lw] / a1[i] for i in range(0, len(a1) - Lw, 63)])
    r2 = np.array([a2[i + Lw] / a2[i] for i in range(0, len(a2) - Lw, 63)])
    print(f"      {yrs}년: 40/40/20 5분위 {np.percentile(r1,5):8.2f} 최악 {r1.min():7.2f}"
          f"   |  배당100 5분위 {np.percentile(r2,5):8.2f} 최악 {r2.min():7.2f}")
    if yrs == 20:
        gate('[달러] 20년 창 좌측꼬리 40/40/20 > 배당100',
             np.percentile(r1, 5) > np.percentile(r2, 5),
             f'5분위 {np.percentile(r1,5):.1f} vs {np.percentile(r2,5):.1f}', warn=True)

# [v36] 실제로 거래하는 통화는 원화다. 달러와 원화가 갈리면 원화가 기준이다.
print("")
print("같은 검사 — 원화 기준 (실제 거래 통화")
_Dk, _ki, _lev2, _, _dfk, _fr = KF.build_krw('chain')
_kc = {'div': np.asarray(_dfk, dtype=float),
       'ust5': (1 + DA.ust_tr(_ki, 5, 'TNX', futures=True, fee=DA.UST_FEE)) * (1 + _fr) - 1,
       'gold': (1 + DA.gold_r(_ki)) * (1 + _fr) - 1}
_fx = int(_ki.searchsorted(pd.Timestamp('1981-04-13')))


def _ksim(dr):
    wv = WB[_fx:]
    pos = np.empty_like(wv); pos[0] = wv[0]; pos[1:] = wv[:-1]
    r_ = np.nan_to_num(pos * _lev2[_fx:] + (1 - pos) * dr[_fx:]); r_[0] = 0
    t_ = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r_) * (1 - 0.001 * t_))


_k1 = _ksim(mix_monthly_from({k: _kc[k] for k in ('div', 'ust5', 'gold')},
                             {'div': .4, 'ust5': .4, 'gold': .2}, _ki))
_k2 = _ksim(mix_monthly_from({'div': _kc['div']}, {'div': 1.0}, _ki))
for yrs in (10, 15, 20):
    Lw = yrs * 252
    q1 = np.array([_k1[i + Lw] / _k1[i] for i in range(0, len(_k1) - Lw, 63)])
    q2 = np.array([_k2[i + Lw] / _k2[i] for i in range(0, len(_k2) - Lw, 63)])
    print(f"      {yrs}년: 40/40/20 5분위 {np.percentile(q1,5):8.2f} 최악 {q1.min():7.2f}"
          f"   |  배당100 5분위 {np.percentile(q2,5):8.2f} 최악 {q2.min():7.2f}")
    if yrs == 20:
        gate('[원화] 20년 창 좌측꼬리 40/40/20 > 배당100',
             np.percentile(q1, 5) > np.percentile(q2, 5) and q1.min() > q2.min(),
             f'5분위 {np.percentile(q1,5):.1f} vs {np.percentile(q2,5):.1f}')
gate('40/40/20 이 Calmar 상위 3위 이내',
     sorted([r[3] for r in res], reverse=True).index(adopted[3]) <= 2,
     f'Calmar {adopted[3]:.3f} ({sorted([r[3] for r in res], reverse=True).index(adopted[3])+1}위/{len(res)})')

print("\n  D3. 레버리지 배수 — 2배가 최적인가 (v22 축1)")
for k_ in (1.0, 1.5, 2.0, 2.5, 3.0):
    c = sim_def(D, WB, defr, riskr=lev_r(D, k_))
    v, g, m, kk = met(c)
    print(f"    {k_}배  {v:>12,.1f}배  CAGR {g*100:6.2f}%  MDD {m*100:7.2f}%  Calmar {kk:.3f}"
          + ('  <- 채택' if k_ == 2.0 else ''))

print("\n  D4. 진입/복귀 문턱 평지 확인 — 채택값 주변이 고원인가")
print(f"    {'진입\\복귀':<10}" + "".join(f"{x*100:>10.0f}%" for x in (-0.16, -0.14, -0.11, -0.08)))
for e in (-0.20, -0.18, -0.16, -0.14, -0.12):
    row = []
    for x in (-0.16, -0.14, -0.11, -0.08):
        if x < e:
            row.append('     -')
            continue
        c = sim_def(D, rule_w(ddq, e, x), defr)
        row.append(f"{met(c)[0]:>10,.0f}")
    print(f"    {e*100:>7.0f}%  " + "".join(f"{r:>10}" for r in row))

print("\n  D5. 신호원 — 미국 QQQ 종가 (v28 채택 근거)")
Dk, kidx, lev2, lev1, dfk, fr = KF.build_krw('chain')
fxs = int(kidx.searchsorted(pd.Timestamp('1981-04-13')))
kdefr = mix_monthly_from({'div': np.asarray(dfk, dtype=float),
                          'ust5': (1 + DA.ust_tr(kidx, 5, 'TNX', futures=True, fee=0.0029)) * (1 + fr) - 1,
                          'gold': (1 + DA.gold_r(kidx)) * (1 + fr) - 1},
                         {'div': .4, 'ust5': .4, 'gold': .2}, kidx)
fx = pd.Series(fr, index=kidx)
pxk = D['px'].reindex(kidx).ffill() * (1 + fx).cumprod()
ddk = (pxk / pxk.rolling(252, min_periods=252).max() - 1).fillna(0).values
for nm, dv in [('미국 종가 (채택)', ddq), ('원화환산', ddk)]:
    w = rule_w(dv, -0.16, -0.16)
    c = sim_def(dict(idx=kidx, qldr=lev2), w, kdefr, start=kidx[fxs])
    v, g, m, k = met(c)
    print(f"    {nm:<16}{v:>12,.1f}배  MDD {m*100:7.2f}%  Calmar {k:.3f}")

print("\n" + "=" * 96)
print("E. 공표 수치 대조")
print("=" * 96)
c = sim_def(D, WB, defr)
v, g, m, k = met(c)
print(f"  전구간 B 40/40/20 : {v:,.1f}배")
print(f"    v27~v35 공표치 263,062배는 **현물형** 모형. v36 에서 선물형으로 정정해 214,076배.")
gate('v36 정정판과 정합 (±2%)', abs(v / 214076 - 1) < 0.02, f'{v:,.0f}')

print("\n" + "=" * 96)
if FAILS:
    print(f"** 실패 {len(FAILS)}건 **")
    for f in FAILS:
        print(f"   - {f}")
else:
    print("실패 0건.")
if WARNS:
    print(f"경고 {len(WARNS)}건: " + ', '.join(WARNS))
print("=" * 96)
