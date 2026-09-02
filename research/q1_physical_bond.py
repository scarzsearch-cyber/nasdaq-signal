# -*- coding: utf-8 -*-
"""
[연구 Q1] 현물형 미국채 ETF 가 국내에 상장됐다 — 국채 다리를 갈아탈 값이 있나 (04 §7 Q1, 2026-09-02,
소유자 「연구만, 반영 금지」)

배경: 방어 국채 다리는 305080(TIGER 미국채10년선물 · 실효만기 5년 · **선물형** · 환노출). 선물형은 현물
      총수익에서 단기금리를 뺀 것만 받아 `def_bond.py` 실측으로 현물형 대비 **연 4.9%p** 뒤졌다(선물 ust5
      1.30% vs 현물 ust5 6.21%). 그때는 「살 수 없는 물건」이라 미결(Q1)로 뒀다. Q1 의 재개 조건은
      「미국채 + 현물 + (H) 아님」의 국내 상장이었고, **2026-09-02 네이버 ETF 목록(1,167종)에서 확인됐다**:
        0085P0 ACE 미국10년국채액티브       (현물·환노출) 시총 1,101억
        476760 ACE 미국30년국채액티브       (현물·환노출) 시총 3,622억
        464470 PLUS 미국채30년액티브        (현물·환노출) 시총   360억
        0046A0 TIGER 미국초단기(3개월이하)국채 (현물·환노출) 시총 3,476억
      (분류 규칙: 이름에 선물·합성·커버드콜·혼합·(H) 가 없는 것. 「액티브」= 채권 직접 보유.)

방법: `def_bond.py` 와 같은 엔진·같은 창(eng_common 54년 QQQ 체인 · 방어 배당40/국채40/금20 · 국채 다리만
      교체). 국채 다리 후보: 현물 5·7·10·20·30년(DA.ust_tr futures=False, 보수 0.10%) vs 현행 선물 ust5(보수 0.29%).
      20·30년은 TYX 고시(1977-02-15) 이후만 — 그 전을 채우면 지어낸 값이 된다(def_bond 와 같은 마스킹).
      원화 검사(관문 ③)는 hist_krfinal 1997~ 시나리오에서 국채 다리만 바꿔 같은 방향인지 본다.

★ 사전 등록 (결과를 보기 전에 적는다 — CLAUDE.md §-1):
  관문 (def_bond.py 와 동일, 문턱 동일):
    ① Calmar 상대 개선 > +10.2%   ② 20년창 p05 ≥ 현행   ③ 원화(1997~)에서도 ①②   ④ 고원(인접 만기도 개선)
  예측:
    P1: 현물 10년은 국채 다리 단독으로 연 +4~5%p 낫다(기지) → 전략 전체로는 Calmar +3~8%(관문① 미달), p05 소폭 개선.
    P2: 현물 30년은 2022형(금리 급등) 창에서 방어가 더 깊게 빠져 Calmar 가 현행보다 **낮다**.
    P3: 어느 후보도 ①을 못 넘는다 → 「갈아탈 값이 없다」. 넘는다면 그 후보는 10년 현물일 것이다.
  「실패하면 무엇이 참인가 / 통과하면 무엇이 참인가」:
    실패 = 쿠폰 4.9%p 는 방어 보유일(전체의 18%)에만 붙어 전략 전체 잣대에선 잡음 크기 → 305080 유지, Q1 닫힘.
    통과 = 국채 다리에 실제 여지가 있다 → **기록만**(동결). 갈아타기는 상품 실측(추적·괴리·AUM) 뒤 소유자 결정.
  어느 쪽이든 이 파일은 규칙·상품을 바꾸지 않는다.

실행: python research/q1_physical_bond.py
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

import hist_defasset as DA                               # noqa: E402
import hist_korea as K                                   # noqa: E402
import hist_krfinal as KF                                # noqa: E402
import eng_common as EC                                  # noqa: E402

GATE1, GATE2 = 0.102, 1.0
FEE_PHYS = 0.0010            # 현물 액티브 ETF 보수(0.05~0.15% 공시) — 0.10% 채택, 0.30% 감도 병기
TYX_START = pd.Timestamp('1977-02-15')
MATS = [5, 7, 10, 20, 30]
STRAT_B = dict(enter=-0.16, exit=-0.16, name='−16 / −16', ladder=[(('dd', -0.16), 1.0, 0)])
UNIVERSE = [('0085P0', 'ACE 미국10년국채액티브', 1101, 10), ('476760', 'ACE 미국30년국채액티브', 3622, 30),
            ('464470', 'PLUS 미국채30년액티브', 360, 30), ('0046A0', 'TIGER 미국초단기(3개월이하)국채', 3476, 0.25)]


def bond_parts(idx, fee=FEE_PHYS):
    out = {'ust5': DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE)}     # 현행(선물)
    for m in MATS:
        src = 'TNX' if m <= 10 else 'TYX'
        out[f'ust{m}_cash'] = DA.ust_tr(idx, m, src, futures=False, fee=fee)
        if m >= 20:
            out[f'ust{m}_cash'] = np.where(idx < TYX_START, np.nan, out[f'ust{m}_cash'])
    return out


def main():
    G, _ = EC.selfcheck()
    idx = G.idx
    D, wB = G.D, np.asarray(G.wB, float)
    QLDR = np.nan_to_num(np.asarray(D['qldr'], float))
    parts = bond_parts(idx)
    parts['div'] = np.asarray(D['schdr'], float)
    parts['gold'] = DA.gold_r(idx)

    def run_leg(key, i0=0, fee_parts=None):
        p = fee_parts or parts
        wts = dict(div=.40, gold=.20); wts[key] = .40
        mixr = DA.mix_monthly_parts(idx, wts, {k: np.nan_to_num(p[k]) for k in wts})
        a = EC.sim2(wB[i0:], QLDR[i0:], mixr[i0:])
        m = EC.fullmet(a, idx=idx[i0:]); m['p05'] = EC.p05_20y(a); m['curve'] = a
        return m

    print('=' * 96)
    print('Q1 현물형 미국채 ETF 상장 — 국채 다리 교체의 값 (엔진 54년 · 방어 배당40/국채40/금20 · 규칙 무변경)')
    print('=' * 96)
    print('  국내 상장 현물·환노출 미국채 ETF (2026-09-02 네이버 목록 실측):')
    for code, nm, aum, mat in UNIVERSE:
        print(f'    {code}  {nm:<34} 시총 {aum:>6,}억  만기 {mat}년')

    lo = int(np.argmax(~np.isnan(parts['ust30_cash'])))
    for i0, lab, keys in ((0, f'전구간 {idx[0].year}~ (20·30년 제외)', ['ust5', 'ust5_cash', 'ust7_cash', 'ust10_cash']),
                          (lo, f'공통창 {idx[lo].year}~ (30년 금리 고시 이후)', ['ust5'] + [f'ust{m}_cash' for m in MATS])):
        base = run_leg('ust5', i0)
        print(f'\n  ── {lab} ──')
        print(f"  {'국채 다리':<12}{'최종배수':>12}{'CAGR':>8}{'MDD':>9}{'Calmar':>8}{'ΔCalmar':>9}{'20년p05':>10}{'Δp05':>8}  관문")
        verdict = {}
        for k in keys:
            m = run_leg(k, i0)
            d1 = m['calmar'] / base['calmar'] - 1
            d2 = m['p05'] / base['p05'] - 1
            g1 = d1 > GATE1; g2 = m['p05'] >= base['p05'] * GATE2
            verdict[k] = (g1, g2, d1, d2)
            tag = ' ←현행' if k == 'ust5' else ('  ①' + ('통과' if g1 else '미달') + ' ②' + ('통과' if g2 else '미달'))
            print(f"  {k:<12}{m['final']:>12,.1f}{m['cagr']:>7.2f}%{m['mdd']:>8.1f}%{m['calmar']:>8.3f}"
                  f"{d1*100:>8.1f}%{m['p05']:>9.2f}배{d2*100:>7.1f}%{tag}")
        if i0 == lo:
            common = verdict

    # 보수 감도 — 0.30% 여도 결론이 같은가
    parts3 = bond_parts(idx, fee=0.0030); parts3['div'] = parts['div']; parts3['gold'] = parts['gold']
    base = run_leg('ust5', 0); m10 = run_leg('ust10_cash', 0, parts3)
    print(f"\n  보수 감도(0.30%, 전구간) — 현물 10년: ΔCalmar {m10['calmar']/base['calmar']-1:+.1%} · Δp05 {m10['p05']/base['p05']-1:+.1%}")

    # 방어 보유 구간에서만 본 국채 다리 차이 — 「왜 전체 잣대에선 작게 보이나」
    hold = (wB == 0)
    for k in ('ust5', 'ust10_cash', 'ust30_cash'):
        r = np.nan_to_num(parts[k]); seg = r[hold & ~np.isnan(parts[k])]
        yrs = seg.size / 252
        print(f"  방어 보유일에서만 국채 다리 연수익 — {k:<10} {((np.prod(1+seg))**(1/yrs)-1)*100:+.2f}%/년 (방어일 {seg.size:,}일)")

    # 관문 ③ 원화 1997~ — 국채 다리만 교체, 나머지는 sc_kr_1997 과 같은 조립
    print('\n  ── 관문 ③ 원화 1997~ (한국 거래일 체결 · 슬리피지 0.1%) ──')
    Dk, kidx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    krd = K.kr_caldays()
    kparts = bond_parts(kidx)
    res = {}
    for k in ('ust5', 'ust10_cash', 'ust30_cash'):
        raw = {'div': np.asarray(dfk, float), 'bond': np.nan_to_num(kparts[k]), 'gold': DA.gold_r(kidx)}
        pk = {'div': raw['div'], 'bond': (1 + raw['bond']) * (1 + fr) - 1, 'gold': (1 + raw['gold']) * (1 + fr) - 1}
        sr = DA.mix_monthly_parts(kidx, dict(div=.40, bond=.40, gold=.20), pk)
        Dx = dict(Dk); Dx['qldr'] = lev2; Dx['schdr'] = sr
        c, w, t = K.run_kr(Dx, STRAT_B, cost=0.001, slip=0.001, start=KF.ST, krdays=krd)
        a = np.asarray(c, float); ii = c.index if hasattr(c, 'index') else kidx[kidx.searchsorted(pd.Timestamp(KF.ST)):]
        m = EC.fullmet(a, idx=ii); m['p05'] = EC.p05_20y(a); res[k] = m
    b = res['ust5']
    for k, m in res.items():
        print(f"  {k:<12} 최종 {m['final']:>9,.1f}  CAGR {m['cagr']:>6.2f}%  MDD {m['mdd']:>6.1f}%  Calmar {m['calmar']:.3f} "
              f"(Δ {m['calmar']/b['calmar']-1:+.1%})  20년p05 {m['p05']:.2f}배 (Δ {m['p05']/b['p05']-1:+.1%})")

    # 판정 — 사전 등록 관문 그대로
    print('\n판정 (사전 등록 관문):')
    g10 = common.get('ust10_cash'); g30 = common.get('ust30_cash')
    print(f"  현물 10년: ① {'통과' if g10[0] else '미달'}({g10[2]:+.1%}) ② {'통과' if g10[1] else '미달'}({g10[3]:+.1%}) "
          f"③ 원화 ΔCalmar {res['ust10_cash']['calmar']/b['calmar']-1:+.1%}")
    print(f"  현물 30년: ① {'통과' if g30[0] else '미달'}({g30[2]:+.1%}) ② {'통과' if g30[1] else '미달'}({g30[3]:+.1%}) "
          f"③ 원화 ΔCalmar {res['ust30_cash']['calmar']/b['calmar']-1:+.1%}")
    any_pass = any(v[0] and v[1] for k, v in common.items() if k != 'ust5')
    print('  → ' + ('어느 후보도 ①② 를 동시에 못 넘는다 → 305080 유지 · Q1 닫힘(재개 조건 소진)' if not any_pass
                   else '통과 후보 있음 → 기록만(동결). 갈아타기는 상품 실측(추적·괴리·AUM) 뒤 소유자 결정'))
    print('\n사전 등록 대조:')
    print(f"  P1 (10년 현물 Calmar +3~8%, ① 미달): {'맞음' if (0 < g10[2] < GATE1) else '틀림'} — {g10[2]:+.1%}")
    print(f"  P2 (30년 현물 Calmar 현행보다 낮다): {'맞음' if g30[2] < 0 else '틀림'} — {g30[2]:+.1%}")
    print(f"  P3 (어느 후보도 ① 못 넘음): {'맞음' if not any(v[0] for k, v in common.items() if k != 'ust5') else '틀림'}")
    print('\n이 측정이 낳은 다음 질문 (§-1 절대멈춤 6):')
    print('  · 실물 0085P0 의 추적·괴리·환노출 베타는 모형 밖이다 — nav_history 에 같이 쌓기 시작해야 그날 잴 수 있다(제안만).')
    print('  · 30년 현물이 유리한 창(2000·2008)과 불리한 창(2022)이 갈린다면 만기 분산(10+30)은? — 방어 조합 재탐색은 04 §5-15 C 고원으로 닫힘, 재개 안 함.')


if __name__ == '__main__':
    main()
