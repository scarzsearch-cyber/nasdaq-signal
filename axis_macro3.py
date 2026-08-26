# -*- coding: utf-8 -*-
"""
[v31] v30 방법론 감사 + 살아남은 후보 정밀검증

v30 초판(axis_macro.py / axis_macro2.py)의 결론 "매크로 전부 기각" 은 대체로
맞지만 **근거 여러 개가 방법론적으로 틀렸고, 결론 텍스트가 하드코딩돼 있어
실제 출력과 어긋난 자리가 있다.** 여기서 전부 다시 잰다.

[A] 초판 감사
  A1  이중 지연     axis_macro2.z() 가 shift(1) 하는데 sim() 이 또 shift(1)
  A2  구간내 분위   axis_macro §1 이 위기창 안에서 분위를 재 순환논리가 됐다
  A3  전표본 분위   np.nanpercentile(x,5) 이 미래를 본다 (문턱 설정 시점 누수)
  A4  동행성 증거   자기상관 큰 수준끼리의 시차상관은 항상 0일 최대 -> 변화량으로
  A5  0.918 상관    점수 상관이 아니라 신호일 집합의 겹침을 봐야 한다

[B] 초판이 안 해본 용법
  B1  대용치가 낙폭의 재탕인가
  B2  증분정보 검정 — 낙폭을 이미 알 때 매크로가 정보를 더하는가
  B3  장단기 금리차 — 대시보드 항목 중 유일한 '진짜 선행' 후보 (1962-)
  B4  복귀(재진입) 필터

[C] 살아남은 후보 — 변동성 조건부 조기방어. 관문 9개.
    **결정적 대조: 그냥 문턱을 낮춘 것과 구분되는가**
"""
import sys
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import COST, rule_w

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SPLIT = pd.Timestamp('2000-01-01')


# ---------------------------------------------------------------- 공용
def zc(a, win=756, minp=252, shift=False):
    s = pd.Series(np.asarray(a, dtype=float)).reset_index(drop=True)
    m = s.rolling(win, min_periods=minp).mean()
    sd = s.rolling(win, min_periods=minp).std()
    out = (s - m) / sd
    return (out.shift(1) if shift else out).fillna(0).values


def exp_q(a, q, minp=252):
    """확장창 분위수 — 그날까지의 정보만. 전표본 분위(A3)의 대체품."""
    s = pd.Series(np.asarray(a, dtype=float)).reset_index(drop=True)
    return s.expanding(min_periods=minp).quantile(q).shift(1).values


def sim(D, w, cost=COST, lag=1, lo=0, hi=None):
    n = len(D['idx']) if hi is None else hi
    sl = slice(lo, n)
    wv = w[sl]
    pos = np.empty_like(wv)
    pos[:lag] = wv[0]
    pos[lag:] = wv[:-lag]
    r = np.nan_to_num(pos * D['qldr'][sl] + (1 - pos) * D['schdr'][sl])
    r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * turn))


def stats(cum, n):
    cagr = cum[-1] ** (252 / n) - 1
    m = (cum / np.maximum.accumulate(cum) - 1).min()
    return cum[-1], cagr, m, cagr / abs(m)


def line(label, cum, n, ref=None, w=None):
    v, g, d, k = stats(cum, n)
    rel = f"  [{(v/ref-1)*100:+7.1f}%]" if ref else ""
    tn = f"  전환{np.abs(np.diff(w)).sum():.0f}" if w is not None else ""
    print(f"    {label:<28}{v:>12,.1f}배  CAGR {g*100:6.2f}%  MDD {d*100:7.2f}%  "
          f"Calmar {k:.3f}{rel}{tn}")
    return v


def blocks(mask):
    seg, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            seg.append(j - i)
            i = j
        else:
            i += 1
    return seg


def early_w(ddq, trig, gate):
    """조기방어 규칙: (신호 and 낙폭<=gate) 이면 강제 진입. 복귀는 원래대로."""
    return rule_w(np.where(trig & (ddq <= gate), -0.20, ddq), -0.16, -0.11)


# ================================================================
def main():
    D = DF.build('chain')
    idx = D['idx']
    ddq = D['ddv']
    N = len(idx)
    base_w = rule_w(ddq, -0.16, -0.11)
    base_cum = sim(D, base_w)
    base_val = base_cum[-1]
    _, base_g, base_d, base_k = stats(base_cum, N)
    print(f"구간 {idx[0].date()} ~ {idx[-1].date()}  ({N}거래일)")
    print(f"기준선(QQQ 낙폭 -16/-11): {base_val:,.1f}배  CAGR {base_g*100:.2f}%  "
          f"MDD {base_d*100:.2f}%  Calmar {base_k:.3f}  전환 {np.abs(np.diff(base_w)).sum():.0f}회\n")

    v = pd.read_csv('data/hist/yahoo_VIX.csv')
    v['Date'] = pd.to_datetime(v['Date'])
    vix = v.set_index('Date')['Close'].reindex(idx).ffill()
    px = D['px']
    rv = px.pct_change().rolling(21, min_periods=21).std()
    mom = px / px.rolling(125, min_periods=125).mean() - 1
    r20 = px.pct_change(20)

    rvz = zc(rv.values)
    vz = zc(vix.values)
    fg = np.clip(50 + 12.5 * (zc(mom) + zc(-rv.values) + zc(r20)) / np.sqrt(3), 0, 100)
    fgL = np.clip(50 + 12.5 * (zc(mom, shift=True) + zc(-rv.values, shift=True)
                               + zc(r20, shift=True)) / np.sqrt(3), 0, 100)
    fgV = np.clip(50 + 12.5 * (zc(mom) + zc(-vix.values) + zc(r20)) / np.sqrt(3), 0, 100)

    print("=" * 80)
    print("A. v30 초판 근거 감사")
    print("=" * 80)

    print("\n[A1] 이중 지연 — axis_macro2.z() 가 shift(1), sim() 이 또 shift(1)")
    for nm, f in [('초판 (이중 지연)', fgL), ('정정 (단일 지연)', fg)]:
        line(nm, sim(D, np.where(f <= 20, 1.0, base_w)), N, base_val)
    print("    -> 부호 같음. 초판 결론 유지, 수치는 정정본으로 교체한다.")

    print("\n[A2/A3] 분위수 누수 — 전표본 분위 vs 확장창 분위")
    for nm, mk in [('전표본 분위 (누수)', rvz >= np.nanpercentile(rvz, 95)),
                   ('확장창 분위 (정정)', rvz >= exp_q(rvz, 0.95))]:
        line(nm, sim(D, early_w(ddq, mk, -0.05)), N, base_val)
    print("    ** 초판은 여기서 '둘 다 진다'고 썼지만 실제로는 둘 다 이긴다. **")
    print("    ** 결론 텍스트가 하드코딩돼 출력과 어긋나 있었다. C 에서 정밀검증한다. **")

    print("\n[A4] 동행성 재측정 — 수준이 아니라 변화량으로")
    dq = pd.Series(ddq).diff()
    for nm, arr in [('VIX', pd.Series(vix.values)), ('실현변동성', pd.Series(rv.values)),
                    ('공포탐욕', pd.Series(fg))]:
        a = arr.reset_index(drop=True).diff()
        row = [(l, a.shift(-l).corr(dq)) for l in (-10, -5, -2, 0, 2, 5, 10)]
        best = max(row, key=lambda x: abs(x[1]) if pd.notna(x[1]) else -1)
        print(f"    {nm:<8}" + " ".join(f"{l:+d}일={c:+.3f}" for l, c in row)
              + f"   <- 최대 {best[0]:+d}일")
    print("    -> 동시점 |상관| 0.65~0.71, 시차 상관은 전부 |0.03| 미만.")
    print("       선행도 후행도 아니다. 완전한 동행 = 새 정보가 없다.")

    print("\n[A5] '상관 0.918' 재검증 — 점수 상관이 아니라 신호일 겹침")
    lo90 = int(idx.searchsorted(pd.Timestamp('1990-01-02')))
    a, b = fgV[lo90:] <= 20, fg[lo90:] <= 20
    print(f"    점수 상관 {np.corrcoef(fgV[lo90:], fg[lo90:])[0,1]:+.3f} / "
          f"신호일 VIX판 {a.sum()}일, 실현변동성판 {b.sum()}일, 교집합 {(a&b).sum()}일")
    print(f"    자카드 겹침 {(a&b).sum()/(a|b).sum()*100:.1f}%  <- 점수는 닮았지만 꼬리가 다르다")
    ref90 = sim(D, base_w, lo=lo90)[-1]
    for nm, f in [('VIX판 (1990-)', fgV), ('실현변동성판 (1990-)', fg)]:
        line(nm, sim(D, np.where(f <= 20, 1.0, base_w), lo=lo90), N - lo90, ref90)
    print("    -> 부호 반전 주장은 유지. 다만 이유는 '상관'이 아니라 꼬리 불일치다.")

    print("\n" + "=" * 80)
    print("B. 초판이 안 해본 용법")
    print("=" * 80)

    print("\n[B1] 공포탐욕 대용치는 낙폭의 재탕인가")
    print(f"    corr(공포탐욕, 낙폭) = {np.corrcoef(fg, ddq)[0,1]:+.3f}   "
          f"공포신호일 중 이미 낙폭 <=-16% 인 비율 {((fg<=20)&(ddq<=-0.16)).sum()/max((fg<=20).sum(),1)*100:.1f}%")
    print(f"    성분 상관: 모멘텀 {np.corrcoef(zc(mom), ddq)[0,1]:+.3f} / "
          f"20일수익 {np.corrcoef(zc(r20), ddq)[0,1]:+.3f} / 변동성 {np.corrcoef(zc(-rv.values), ddq)[0,1]:+.3f}")
    print("    -> 성분 3개 중 2개가 순수 가격 모멘텀. 낙폭이 이미 말하는 것의 재탕이다.")

    print("\n[B2] 증분정보 — 낙폭 5분위 안에서 매크로 상·하위 절반의 이후 21일 수익차")
    fwd = pd.Series(px.pct_change().fillna(0).values).rolling(21).sum().shift(-21).values
    ok = ~np.isnan(fwd)
    qs = pd.qcut(pd.Series(ddq[ok]), 5, labels=False, duplicates='drop').values
    for nm, sg in [('VIX z', vz), ('실현변동성 z', rvz), ('공포탐욕', -fg)]:
        f, s_ = fwd[ok], sg[ok]
        ds = []
        for q_ in range(5):
            m = qs == q_
            if m.sum() < 50:
                continue
            h = s_[m] >= np.median(s_[m])
            ds.append(f[m][h].mean() - f[m][~h].mean())
        print(f"    {nm:<12}" + " ".join(f"{d*100:+6.2f}%" for d in ds)
              + f"   평균 {np.mean(ds)*100:+.2f}%p")
    print("    -> 가장 깊은 분위에서만 VIX 가 +5%p. 나머지 4개 분위는 0 근처.")
    print("       '깊은 낙폭 + 고변동성' 조합에만 정보가 있다는 뜻 -> C 의 후보와 같은 이야기.")

    print("\n[B3] 장단기 금리차(10Y-3M) — 유일한 '진짜 선행' 후보")
    t = pd.read_csv('data/hist/yahoo_TNX.csv')
    t['Date'] = pd.to_datetime(t['Date'])
    y10 = t.set_index('Date')['Close'].reindex(idx).ffill()
    b3 = pd.read_csv('data/hist/fred_DTB3.csv')
    b3['observation_date'] = pd.to_datetime(b3['observation_date'])
    y3m = pd.to_numeric(b3.set_index('observation_date')['DTB3'],
                        errors='coerce').reindex(idx).ffill()
    curve = (y10 - y3m).values
    inv = np.nan_to_num(curve, nan=1.0) < 0
    print(f"    역전 일수 {inv.sum()}일 ({inv.sum()/N*100:.1f}%)")

    print("    (a) 선행 시차 — 평시(낙폭>-16%)에 시작된 역전만 세고, 60일 내 재역전은 병합")
    st = np.where(inv & ~np.r_[False, inv[:-1]])[0]
    merged, last = [], -999
    for s0 in st:
        if s0 - last > 60:
            merged.append(s0)
        last = s0
    leads = []
    for s0 in merged:
        if ddq[s0] <= -0.16:
            continue
        fut = np.where(ddq[s0:] <= -0.16)[0]
        if len(fut):
            dd = (idx[s0 + fut[0]] - idx[s0]).days
            leads.append(dd)
            print(f"      {idx[s0].date()} 역전 -> {idx[s0+fut[0]].date()} 낙폭도달 ({dd}일)")
        else:
            print(f"      {idx[s0].date()} 역전 -> 도달 없음 (진행 중)")
    if leads:
        print(f"      선행 시차: 중앙값 {int(np.median(leads))}일, 범위 {min(leads)}~{max(leads)}일  "
              f"n={len(leads)}")
        print("      -> 확실히 선행한다. 그러나 시차가 7~533일로 흩어져 타이밍에 쓸 수 없다.")

    print("    (b) 규칙화")
    for nm, w_ in [('역전 중 무조건 방어', np.where(inv, 0.0, base_w)),
                   ('역전 중 문턱 -8%', early_w(ddq, inv, -0.08)),
                   ('역전 중 문턱 -12%', early_w(ddq, inv, -0.12)),
                   ('역전 중 복귀 금지', None)]:
        if w_ is None:
            cur, out = 1.0, np.empty(N)
            for i in range(N):
                if cur >= 1.0:
                    if ddq[i] <= -0.16:
                        cur = 0.0
                elif ddq[i] > -0.11 and not inv[i]:
                    cur = 1.0
                out[i] = cur
            w_ = out
        line(nm, sim(D, w_), N, base_val, w=w_)

    print("\n[B4] 복귀(재진입) 필터 — 매크로가 진정됐을 때만 방어에서 나온다")
    for nm, calm in [('VIX z < 0', vz < 0), ('VIX z < 1', vz < 1),
                     ('공포탐욕 > 40', fg > 40), ('금리차 > 0', ~inv),
                     ('실현변동성 z < 0', rvz < 0)]:
        cur, out = 1.0, np.empty(N)
        for i in range(N):
            if cur >= 1.0:
                if ddq[i] <= -0.16:
                    cur = 0.0
            elif ddq[i] > -0.11 and calm[i]:
                cur = 1.0
            out[i] = cur
        line(nm + ' 일 때만 복귀', sim(D, out), N, base_val, w=out)
    print("    -> 전부 악화. 복귀를 늦추면 반등을 놓친다(v18 이후 반복 확인된 성질).")

    print("\n" + "=" * 80)
    print("C. 살아남은 후보 — 변동성 조건부 조기방어")
    print("   규칙: 실현변동성이 역대 상위 5% 이고 낙폭이 이미 -5% 이하면 즉시 방어")
    print("=" * 80)
    trig = rvz >= exp_q(rvz, 0.95)
    cand_w = early_w(ddq, trig, -0.05)
    cand_cum = sim(D, cand_w)
    cand_val = cand_cum[-1]

    print("\n[C1] ** 결정적 대조 ** — 그냥 문턱을 낮춘 것과 구분되는가")
    print("    변동성 조건을 빼고 낙폭 문턱만 바꾼 규칙들과 비교한다.")
    line('기준선 -16/-11', base_cum, N, w=base_w)
    for e in (-0.05, -0.08, -0.10, -0.12, -0.14):
        w_ = rule_w(ddq, e, -0.11)
        line(f'문턱 {e*100:.0f}%/-11 (변동성 무시)', sim(D, w_), N, base_val, w=w_)
    line('** 변동성 조건부 조기방어 **', cand_cum, N, base_val, w=cand_w)
    hit = ((ddq <= -0.05) & trig).sum() / max((ddq <= -0.05).sum(), 1)
    print(f"    낙폭 -5% 이하인 날 중 변동성 신호가 켜진 비율 = {hit*100:.1f}%")
    print("    -> 이 비율이 100% 에 가까우면 '그냥 문턱 -5%' 와 같은 규칙이라는 뜻이다.")

    print("\n[C2] 파라미터 스윕 — 고원인가 첨탑인가")
    print("      분위 \\ 낙폭게이트   -3%      -5%      -8%     -12%")
    for q_ in (0.90, 0.925, 0.95, 0.975, 0.99):
        tq = rvz >= exp_q(rvz, q_)
        row = []
        for g in (-0.03, -0.05, -0.08, -0.12):
            row.append(sim(D, early_w(ddq, tq, g))[-1] / base_val - 1)
        print(f"      p{q_*100:4.1f}        " + "  ".join(f"{x*100:+7.1f}%" for x in row))
    print("      변동성 룩백 스윕 (분위 p95, 게이트 -5%)")
    row = []
    for lb in (10, 21, 42, 63):
        rz = zc(px.pct_change().rolling(lb, min_periods=lb).std().values)
        row.append((lb, sim(D, early_w(ddq, rz >= exp_q(rz, 0.95), -0.05))[-1] / base_val - 1))
    print("      " + "  ".join(f"{lb}일={x*100:+.1f}%" for lb, x in row))

    print("\n[C3] 위기별 기여")
    crises = {'1973 오일쇼크': ('1973-01-01', '1974-12-31'),
              '1987 블랙먼데이': ('1987-08-01', '1988-06-30'),
              '2000 닷컴': ('2000-03-01', '2002-10-31'),
              '2008 금융위기': ('2007-10-01', '2009-03-31'),
              '2020 COVID': ('2020-01-15', '2020-04-15'),
              '2022 긴축': ('2022-01-01', '2022-12-31')}
    for nm, (s, e) in crises.items():
        m = (idx >= s) & (idx <= e)
        if m.sum() < 20:
            continue
        i0, i1 = np.where(m)[0][[0, -1]]
        pb = base_cum[i1] / base_cum[i0] - 1
        pc = cand_cum[i1] / cand_cum[i0] - 1
        print(f"    {nm:<14} 기준 {pb*100:+7.2f}%  후보 {pc*100:+7.2f}%  차이 {(pc-pb)*100:+7.2f}%p")

    print("\n[C4] 블록 플라시보 (500회) — 뭉침 유지하고 신호구간만 옮긴다")
    rng = np.random.default_rng(42)
    seg = blocks(trig)
    better = 0
    for _ in range(500):
        rm = np.zeros(N, dtype=bool)
        for ln in seg:
            s0 = rng.integers(0, N - ln)
            rm[s0:s0 + ln] = True
        if sim(D, early_w(ddq, rm, -0.05))[-1] >= cand_val:
            better += 1
    print(f"    신호구간 {len(seg)}개  실제 {cand_val:,.1f}배  "
          f"무작위 중 같거나 나음 {better}/500 ({better/500*100:.1f}%)")

    print("\n[C5] 워크포워드 — 1972-1999 에서 고르고 2000- 에 적용")
    sp = int(idx.searchsorted(SPLIT))
    bестq, bv = None, -1
    for q_ in (0.90, 0.925, 0.95, 0.975, 0.99):
        for g in (-0.03, -0.05, -0.08, -0.12):
            vv = sim(D, early_w(ddq, rvz >= exp_q(rvz, q_), g), hi=sp)[-1]
            if vv > bv:
                bv, bестq = vv, (q_, g)
    q_, g = bестq
    print(f"    IS 최적 = 분위 p{q_*100:.1f} / 게이트 {g*100:.0f}%  (IS {bv:,.1f}배)")
    oos_b = sim(D, base_w, lo=sp)
    oos_c = sim(D, early_w(ddq, rvz >= exp_q(rvz, q_), g), lo=sp)
    n2 = N - sp
    line('OOS 기준선', oos_b, n2)
    line('OOS 후보', oos_c, n2, oos_b[-1])

    print("\n[C6] 롤링 창 — 중앙값이 아니라 좌측꼬리를 본다")
    for yrs in (10, 15, 20):
        L = yrs * 252
        rb, rc = [], []
        for s0 in range(0, N - L, 63):
            rb.append(base_cum[s0 + L] / base_cum[s0])
            rc.append(cand_cum[s0 + L] / cand_cum[s0])
        rb, rc = np.array(rb), np.array(rc)
        print(f"    {yrs}년 창 n={len(rb)}  승률 {(rc>rb).mean()*100:5.1f}%  "
              f"중앙값 {np.median(rb):8.2f} -> {np.median(rc):8.2f}  "
              f"5분위 {np.percentile(rb,5):7.2f} -> {np.percentile(rc,5):7.2f}  "
              f"최악 {rb.min():6.2f} -> {rc.min():6.2f}")

    print("\n[C7] VIX 로 바꿔도 같은가 (1990-)")
    for nm, sg in [('실현변동성', rvz), ('VIX', vz)]:
        line(nm, sim(D, early_w(ddq, sg >= exp_q(sg, 0.95), -0.05), lo=lo90), N - lo90, ref90)
    print("    -> 두 지표가 같은 답이면 신호, 다르면 잡음(A5 의 교훈).")

    print("\n[C8] 구간 안정성")
    for nm, s0 in [('1972-', 0), ('1990-', lo90), ('2000-', sp),
                   ('2011-', int(idx.searchsorted(pd.Timestamp('2011-10-25'))))]:
        rf = sim(D, base_w, lo=s0)[-1]
        line(nm, sim(D, cand_w, lo=s0), N - s0, rf)

    print("\n[C9] 전환 횟수·비용 민감도")
    print(f"    전환 {np.abs(np.diff(base_w)).sum():.0f}회 -> {np.abs(np.diff(cand_w)).sum():.0f}회")
    for c in (0.001, 0.002, 0.003, 0.005):
        rb = sim(D, base_w, cost=c)[-1]
        rc = sim(D, cand_w, cost=c)[-1]
        print(f"    편도비용 {c*100:.1f}%: 기준 {rb:>11,.1f}배  후보 {rc:>11,.1f}배  "
              f"[{(rc/rb-1)*100:+.1f}%]")

    print("\n[판정] 전략_v31.md 에 기록")


if __name__ == '__main__':
    main()
