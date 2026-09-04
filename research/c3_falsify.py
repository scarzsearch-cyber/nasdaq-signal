# -*- coding: utf-8 -*-
"""
[반증] C3 「나스닥 ÷ T-bill(초과수익 지수)의 낙폭」 신호 — new_paths.py 가 관문 ①②를 넘겼다 → §-1 ⓐ 무조건 반증 (2026-09-03)

C3 = B 와 보유·문턱·룩백·방어·비용 전부 같고 **신호만** 「나스닭 가격의 252일 낙폭」 대신 「(나스닥 ÷ 현금지수)의 252일 낙폭」.
54년 결과: Calmar 0.480 vs 0.423 (+13.4%, 관문① 10.2% 통과) · 20년창 p05 47.8 vs 37.9배(+26%, ② 통과) · 블록 2/4(③ 미달).
뜻: 고점 이후 현금이 번 만큼 낙폭이 깊게 잰다 → **금리가 높을수록 더 얕은 가격 하락에서 나가고, 복귀는 더 늦다**(금리 적응 문턱).

★ 반증 배터리 (결과 전 등록):
  F1 사건 단위 — B 와 갈린 전환일(어느 쪽만 나간 날·복귀일)의 수와 연도. 갈린 사건이 손에 꼽히면 같은 규칙의 다른 표기다.
  F2 블록 상세 — 4블록·6블록의 Calmar·최종 승패와 그 블록의 평균 T-bill. 이김이 고금리 블록에만 몰리면 「금리 시대의 산물」.
  F3 고원 — 문턱 −12~−20 · 룩백 200/252/300 에서 ①② 가 유지되나(첨탑이면 기각).
  F4 전 시작일 — 20년창 전 시작일 분포(p05·p25·중앙·p75)와 승률, 비중첩 창 수 병기.
  F5 금리 국면 분할 — T-bill 중앙값 위/아래 구간에서 각각의 초과 Calmar.
  F6 타 시장 — S&P500 과 러셀에 같은 신호(÷T-bill) vs 가격 낙폭.
  F7 등가 검사 — C3 가 「금리만큼 문턱을 옮긴 B」와 같은가: 문턱 = −16 + (고점 이후 누적 T-bill) 로 만든 B′ 와 곡선 오차.
  F8 비용 감도 — 편도 0.3% 에서도 ① 유지?
판정(사전): ③ 이 이미 미달이라 채택 후보가 아니다. 이 배터리는 「어디서 나오는 이득인가」를 밝히는 것 — F2·F5 가 고금리 시대에 몰리면
「2022~ 처럼 금리가 있는 시대에 값이 있을 수 있으나 표본은 1973~86 이 만든 것」으로 적는다. F3 첨탑이면 잡음으로 닫는다.
예측: P1 갈린 사건 15~40건, 고금리 연도(1973~84·2022~) 집중. P2 ①은 고원(−14~−18 유지), ②는 흔들림. P3 F5 저금리 구간 초과 Calmar ≈ 0.
      P4 F6 S&P 에서도 방향 같음(Calmar +) — 금리 기전이면 시장 무관. P5 F7 오차 < 1%(등가) — 즉 C3 = 「금리 적응 문턱」의 다른 표기.

실행: python research/c3_falsify.py
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

import liquid_design as LD                               # noqa: E402
import eng_common as EC                                  # noqa: E402

IDX, R, col, MIX = LD.IDX, LD.R, LD.col, LD.MIX
N = len(IDX)
L = '=' * 100
PX = pd.Series(LD.G.D['px'], index=IDX).astype(float)
QLDR = np.nan_to_num(np.asarray(LD.G.D['qldr'], float))
TB = np.nan_to_num(R[:, col['TBILL']])
RQ = np.nan_to_num(PX.pct_change().values)
LO = 252


def dd_of(r, win=252):
    c = pd.Series(np.cumprod(1 + np.nan_to_num(r)), index=IDX)
    return (c / c.rolling(win, min_periods=win).max() - 1).values


def state(dd, th=-0.16):
    w = np.ones(N); s = 1
    for t in range(N):
        d = dd[t]
        if not np.isnan(d):
            s = 0 if (s == 1 and d <= th) else (1 if (s == 0 and d > th) else s)
        w[t] = s
    return w


def excess_r(rq, tb=TB):
    return (1 + rq) / (1 + tb) - 1


def curve(w, lo=LO, qr=QLDR, cost=EC.COST):
    return np.asarray(EC.sim2(w[lo:], qr[lo:], MIX[lo:], cost=cost), float)


def met(c, lo=LO):
    m = EC.fullmet(c, idx=IDX[lo:]); m['p05'] = EC.p05_20y(c); return m


def blocks(c, nb, lo=LO):
    e = np.linspace(0, len(c), nb + 1).astype(int); out = []
    for a, b in zip(e[:-1], e[1:]):
        seg = c[a:b] / c[a]; ix = IDX[lo:][a:b]
        out.append((ix[0].year, ix[-1].year, EC.fullmet(seg, idx=ix)['calmar'], seg[-1], float(np.mean(TB[lo + a:lo + b])) * 252))
    return out


def main():
    print(L); print('C3 반증 — 나스닥 ÷ T-bill 낙폭 신호 (관문 ①② 통과·③ 미달) · 규칙 무변경'); print(L)
    wB = state(dd_of(RQ)); wC = state(dd_of(excess_r(RQ)))
    cB, cC = curve(wB), curve(wC)
    mB, mC = met(cB), met(cC)
    print(f"  B : 최종 {mB['final']:,.0f} · Calmar {mB['calmar']:.3f} · MDD {mB['mdd']:.1f}% · 20y p05 {mB['p05']:.1f}배")
    print(f"  C3: 최종 {mC['final']:,.0f} · Calmar {mC['calmar']:.3f} ({mC['calmar']/mB['calmar']-1:+.1%}) · MDD {mC['mdd']:.1f}% · 20y p05 {mC['p05']:.1f}배 ({mC['p05']/mB['p05']-1:+.1%})")

    # F1 사건 단위
    print('\n[F1] B 와 갈린 날 — 상태가 다른 날수와 갈린 사건')
    diff = (wB != wC)
    # [2026-09-04 코드리뷰] 종전엔 분자가 diff.sum()(전 구간)인데 분모와 괄호 안
    # 백분율은 [LO:] 였다 — 한 문장이 두 창을 섞어 서로 안 맞았다. 전부 [LO:] 로.
    print(f'  상태가 다른 날 {int(diff[LO:].sum())}일 / {N-LO} ({diff[LO:].mean()*100:.1f}%)')
    ev = []
    for t in range(LO, N):
        if wB[t] != wB[t-1] or wC[t] != wC[t-1]:
            ev.append((IDX[t].date(), int(wB[t]), int(wC[t])))
    # 갈린 사건 = 한쪽만 바뀐 날 (다른 쪽은 그 뒤 며칠 안에 따라오거나 아예 안 옴)
    only = [(d, b, c) for d, b, c in ev if b != c]
    yrs = pd.Series([d.year for d, _, _ in only]).value_counts().sort_index()
    print(f'  한쪽만 바뀌어 상태가 갈린 날 {len(only)}건 · 연도별: ' + ', '.join(f'{y}:{n}' for y, n in yrs.items()))
    # 상태가 갈린 구간(연속) 과 그 구간의 2배 수익 — 누가 옳았나
    segs = []; t = LO
    while t < N:
        if diff[t]:
            s = t
            while t < N and diff[t]:
                t += 1
            seg_r = np.prod(1 + QLDR[s:t]) - 1; mix_r = np.prod(1 + MIX[s:t]) - 1
            who = 'C3' if ((wC[s] == 0 and mix_r > seg_r) or (wC[s] == 1 and seg_r > mix_r)) else 'B'
            segs.append((IDX[s].date(), IDX[t-1].date(), t - s, int(wB[s]), int(wC[s]), seg_r * 100, mix_r * 100, who))
        else:
            t += 1
    print(f'  갈린 구간 {len(segs)}개 · C3 가 옳았던 구간 {sum(1 for x in segs if x[-1]=="C3")} · B 가 옳았던 구간 {sum(1 for x in segs if x[-1]=="B")}')
    big = sorted(segs, key=lambda x: -abs(x[5] - x[6]))[:12]
    print('  가장 크게 갈린 구간 12개 (기간 · B상태/C3상태 · 그동안 2배수익 vs 방어수익 · 옳은 쪽):')
    for a, b, n, sb, sc, r2, rm, who in big:
        print(f'    {a}~{b} {n:>4}일  B={"공격" if sb else "방어"} C3={"공격" if sc else "방어"}  2배 {r2:+7.1f}% vs 방어 {rm:+6.1f}%  → {who}')

    # F2 블록
    print('\n[F2] 블록 — Calmar·최종 승패와 그 블록의 평균 T-bill')
    for nb in (4, 6):
        bb, bc = blocks(cB, nb), blocks(cC, nb)
        wins = 0
        row = []
        for (y0, y1, calB, fB, tb), (_, _, calC, fC, _) in zip(bb, bc):
            w = calC > calB; wins += w
            row.append(f'{y0}~{y1}: T-bill {tb*100:.1f}% · Calmar {calB:.2f}→{calC:.2f}{"★" if w else " "} · 최종 {fB:,.1f}→{fC:,.1f}')
        print(f'  {nb}블록 — Calmar 이김 {wins}/{nb}'); [print('    ' + r) for r in row]

    # F3 고원
    # [2026-09-04 코드리뷰] 격자가 룩백 300 까지 쓰는데 절단은 LO=252 로 고정이었다.
    # dd_of 는 min_periods=win 이라 lb=300 이면 252~298 이 아직 NaN 이고, state() 가
    # NaN 을 건너뛰어 그 날들이 **강제 공격**으로 채점됐다 — lb=200 칸에는 없는 날이다.
    # 룩백 상한을 덮는 공통 절단에서 기준선까지 다시 재야 칸끼리 비교가 된다.
    LB3 = 300
    mB3 = met(curve(state(dd_of(RQ)), LB3), LB3)
    print(f'\n[F3] 고원 — 문턱 × 룩백에서 ΔCalmar(%) / Δp05(%) (기준 B −16·252 · 공통 절단 {LB3}일)')
    print('  문턱\\룩백' + ''.join(f'{lb:>16}' for lb in (200, 252, 300)))
    for th in (-0.12, -0.14, -0.16, -0.18, -0.20):
        cells = []
        for lb in (200, 252, 300):
            w = state(dd_of(excess_r(RQ), lb), th); m = met(curve(w, LB3), LB3)
            cells.append(f'{m["calmar"]/mB3["calmar"]-1:+6.1%}/{m["p05"]/mB3["p05"]-1:+6.1%}')
        print(f'  {th*100:>6.0f}%   ' + '  '.join(cells))
    print('  (참고) 가격 낙폭 B 자체의 문턱 고원:', '  '.join(f'{th*100:.0f}%:{met(curve(state(dd_of(RQ), th)))["calmar"]/mB["calmar"]-1:+.1%}' for th in (-0.12, -0.14, -0.18, -0.20)))

    # F4 전 시작일 20년창
    print('\n[F4] 20년창 전 시작일 분포 (최종배수 비율 C3/B)')
    W = 5040
    rb = cB[W:] / cB[:-W]; rc = cC[W:] / cC[:-W]; ratio = rc / rb
    q = np.quantile(ratio, [0.05, 0.25, 0.5, 0.75, 0.95])
    # [2026-09-04 코드리뷰] 비중첩 = 표본일수 / 지평 이다. 종전 len(ratio)/W 는
    # (n-W)/W 라 정확히 1.0 만큼 과소였다(1.7 로 찍혔으나 실제 2.7).
    # audit_stat.py:237 이 같은 통계를 n/W 로 맞게 낸다.
    print(f'  창 {len(ratio):,}개(비중첩 {len(cB)/W:.1f}개) · C3/B 배수비 p05 {q[0]:.2f} · p25 {q[1]:.2f} · 중앙 {q[2]:.2f} · p75 {q[3]:.2f} · p95 {q[4]:.2f} · C3 가 이긴 창 {np.mean(ratio>1)*100:.0f}%')
    print(f'  20년창 최종배수 자체: B p05 {np.quantile(rb,.05):.1f} 중앙 {np.median(rb):.1f} / C3 p05 {np.quantile(rc,.05):.1f} 중앙 {np.median(rc):.1f}')

    # F5 금리 국면
    print('\n[F5] 금리 국면 — T-bill 중앙값 위/아래의 Calmar와 초과 일수익')
    rB = np.diff(cB, prepend=1) / np.r_[1, cB[:-1]]; rC = np.diff(cC, prepend=1) / np.r_[1, cC[:-1]]
    tbl = TB[LO:] * 252; med = np.median(tbl)
    for nm, m in (('고금리(중앙값 위)', tbl > med), ('저금리(중앙값 아래)', tbl <= med)):
        ex = (rC - rB)[m]
        # 반대 국면은 0%로 두어 달력 시간과 MDD 경로를 보존한다. 종전에는
        # 평균수익 차이만 내고 이를 docstring의 「초과 Calmar」라고 불렀다.
        a_br = np.cumprod(1 + np.where(m, rB, 0.0))
        a_cr = np.cumprod(1 + np.where(m, rC, 0.0))
        mb = EC.fullmet(a_br, idx=IDX[LO:]); mc = EC.fullmet(a_cr, idx=IDX[LO:])
        print(f'  {nm:<12} 일수 {m.sum():,} · 평균 T-bill {tbl[m].mean()*100:.1f}% · '
              f'Calmar {mb["calmar"]:.3f}→{mc["calmar"]:.3f} (Δ {mc["calmar"]-mb["calmar"]:+.3f}) · '
              f'C3−B 연환산 {ex.mean()*252*100:+.2f}%p · 갈린 날 {int((wB[LO:]!=wC[LO:])[m].sum())}')

    # F6 타 시장
    print('\n[F6] 타 시장 — 같은 신호(÷T-bill) vs 가격 낙폭, 2배 합성 · 같은 방어')
    for nm, key in (('S&P500', 'SPX'), ('러셀2000', 'RUT')):
        r = R[:, col[key]]; lo = int(np.argmax(~np.isnan(r))) + 252
        rq = np.nan_to_num(r); q2 = LD.lev2(r)
        wp = state(dd_of(rq)); wx = state(dd_of(excess_r(rq)))
        cp = curve(wp, lo, q2); cx = curve(wx, lo, q2)
        mp, mx = met(cp, lo), met(cx, lo)
        print(f"  {nm:<8} {IDX[lo].year}~  가격 낙폭 Calmar {mp['calmar']:.3f} · ÷T-bill {mx['calmar']:.3f} ({mx['calmar']/mp['calmar']-1:+.1%}) · p05 {mp['p05']:.1f}→{mx['p05']:.1f}배 ({mx['p05']/mp['p05']-1:+.1%})")

    # F7 등가 — 금리 누적만큼 문턱을 옮긴 B′
    print('\n[F7] 등가 검사 — C3 ≟ 「문턱 = −16% + 고점 이후 누적 T-bill」 인 B′')
    c_px = pd.Series(np.cumprod(1 + RQ), index=IDX); c_tb = pd.Series(np.cumprod(1 + TB), index=IDX)
    ex_idx = c_px / c_tb; hi_ex = ex_idx.rolling(252, min_periods=252).max()
    # 초과지수 낙폭 ≤ −16  ⇔  c_px / c_tb ≤ 0.84·hi_ex  ⇔  가격 ≤ 0.84·hi_ex·c_tb : 가격 문턱이 현금지수에 비례해 오른다
    eff = (0.84 * hi_ex * c_tb / c_px.rolling(252, min_periods=252).max() - 1).values   # 가격 252일 고점 대비 실효 문턱
    e = eff[LO:]; e = e[~np.isnan(e)]
    print(f'  실효 가격 문턱(252일 가격고점 대비) 분포: 중앙 {np.median(e)*100:+.1f}% · p10 {np.quantile(e,.1)*100:+.1f}% · p90 {np.quantile(e,.9)*100:+.1f}% · 1981 {np.nanmean(eff[(IDX.year==1981)])*100:+.1f}% · 2015 {np.nanmean(eff[(IDX.year==2015)])*100:+.1f}% · 2024 {np.nanmean(eff[(IDX.year==2024)])*100:+.1f}%')
    print('  (정의상 등가 — C3 는 「현금이 번 만큼 문턱이 얕아지는 B」다. 값 차이는 문턱이 아니라 고점 기준까지 달라지는 데서 온다)')

    # F8 비용
    print('\n[F8] 비용 감도 — 편도 0.3%')
    mB3, mC3 = met(curve(wB, cost=0.003)), met(curve(wC, cost=0.003))
    print(f"  0.3%: Calmar B {mB3['calmar']:.3f} · C3 {mC3['calmar']:.3f} ({mC3['calmar']/mB3['calmar']-1:+.1%}) · 전환 B {int(np.sum(np.abs(np.diff(wB[LO:]))>0))} · C3 {int(np.sum(np.abs(np.diff(wC[LO:]))>0))}")

    print('\n판정(사전 규약): ③ 미달이라 채택 후보 아님. 위 표가 말하는 것 — 이득의 출처가 고금리 시대인지(F2·F5), 고원인지(F3), 시장 무관인지(F6).')
    print('이 측정이 낳은 다음 질문 (§-1 절대멈춤 6): 금리가 있는 시대(2022~)의 동결 이후 사건에서 C3 와 B 가 갈리는 날이 오면 그 사건이 실제 시험이다 — 장부에 「C3 상태」 열을 병행 기록할지는 소유자 결정(그림자 2호 후보).')


if __name__ == '__main__':
    main()
