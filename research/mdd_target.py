# -*- coding: utf-8 -*-
"""
[조건부 설계] 「MDD 를 50% 까지 낮춰야 한다면 전략은 어떻게 바뀌나」 — 소유자 질문 (2026-09-03)

⚠ **이것은 후보 탐색이 아니라 「목표가 바뀌었을 때의 설계」다.** 현행 B 는 최종배수(부)를 잣대로 고른 규칙이고,
  MDD 상한을 제약으로 걸면 **다른 답이 나오는 것이 정상**이다. 04 §7 Q6 이 예고한 「잣대를 바꾸면 답이 바뀐다」의 실행판.
  **전략 B 는 이 파일로 바뀌지 않는다.** 소유자가 목표를 바꾸겠다고 결정할 때만 의미가 있는 표다.

제약: **54년 전 구간 MDD ≥ −50%** (현행 B 는 −60.5%). 각 경로에서 제약을 **간신히 만족하는 지점**을 찾아
      그때의 부·수익·지평 성과를 비교한다. **같은 제약을 가장 싸게 사는 경로는 무엇인가.**

경로 5개 (전부 저장소가 이미 아는 축 · 새 규칙을 만들지 않는다):
  ① 공격 다리 배합 — QLD w + X(1−w), X ∈ {배당 · 금 · 국채 · 방어바스켓 · 현금}, 월 1회 재조정 (§5-32·§5-34)
  ② 배율 낮추기 — 2배 → k배 (k = 2.0~1.0, synth2x 와 같은 규약 k·r − c). 규칙·방어 그대로
  ③ 문턱 얕게 — −16 → 더 얕은 대칭 문턱 (§5-22·§5-23 이 이미 잰 축 · 여기선 MDD 제약을 만족하는 지점만)
  ④ 방어 비중 — 「전량 전환」 대신 방어 시 일부만 남기기(공격 상태에서 방어자산 상시 x%) = §1 v47 계열
  ⑤ ①+② 조합 — 배율을 낮추고 배합도 하는 절충

각 경로에서 보고: MDD · CAGR · 최종배수 · 20년 p05 · 10년 중앙/최악5% · 연변동성 · 전환 횟수.
**판정 기준(사전)**: 제약을 만족하는 지점들 중 **20년 p05(부의 바닥)가 가장 높은 경로**가 답이다 —
  MDD 를 낮추라는 요구의 뜻이 「최악을 견디게」이므로, 비교도 최악 지표로 한다. 최종배수는 같이 적되 기준으로 쓰지 않는다.

예측 (결과 전 · 틀리면 그대로 적는다 §-1 ⑦):
  P1 **배율 낮추기(②)가 가장 싸다** — 낙폭은 배율에 거의 비례하는데 톱니 비용이 안 늘기 때문.
  P2 문턱 얕게(③)는 −50% 에 도달조차 못 하거나, 도달해도 부가 가장 많이 깎인다(전환이 늘어 톱니가 커진다).
  P3 금 배합(①)은 MDD 는 잘 낮추지만 20년 p05 에서 진다(§5-34 반증과 같은 이유).
  P4 조합(⑤)이 단일 경로보다 크게 낫지는 않다 — 두 축이 같은 일(노출 축소)을 한다.

실행: python research/mdd_target.py   (약 40초 · 네트워크 0 · 파일 쓰기 0)
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
_sys.path.insert(0, _os.path.join(_ROOT, 'deploy'))

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
import hist_defasset as DA                                # noqa: E402
import hist_defensive as DF                               # noqa: E402
import reentry_lib as RL                                  # noqa: E402
from build_stats import STRATS, defensive_r               # noqa: E402

L = '=' * 126
TARGET = -50.0


def evaluate(c, idx, w=None):
    c = np.asarray(c, float)
    m = EC.fullmet(c, idx=idx)
    r = pd.Series(c, index=idx).pct_change()
    s = pd.Series(c, index=idx)
    q10 = (s / s.shift(2520)).dropna()
    return dict(mdd=m['mdd'], cagr=m['cagr'], final=m['final'], calmar=m['calmar'],
                vol=float(r.std(ddof=1) * np.sqrt(252) * 100), p05_20=EC.p05_20y(c),
                med10=float(q10.median()) if len(q10) else np.nan,
                p05_10=float(q10.quantile(0.05)) if len(q10) else np.nan,
                sw=int(np.sum(np.abs(np.diff(w)))) if w is not None else None)


def main():
    print(L); print(f'「MDD 를 {abs(TARGET):.0f}% 까지 낮춰야 한다면」 — 경로별 비용 비교 (조건부 설계 · 전략 B 무변경)'); print(L)
    with contextlib.redirect_stdout(io.StringIO()):
        D = dict(DF.build('chain'))
    idx = pd.DatetimeIndex(D['idx'])
    qldr = np.asarray(D['qldr'], float)
    divr = np.asarray(D['schdr'], float)
    px = pd.Series(D['px'], index=idx).astype(float)
    rq = np.nan_to_num(px.pct_change().values)
    cday = np.nan_to_num(np.asarray(D.get('c_daily', np.zeros(len(idx))), float))
    if not cday.any():                      # c_daily 가 없으면 2배 합성 규약에서 역산
        cday = 2 * rq - np.nan_to_num(qldr)
    basket = np.asarray(defensive_r(idx, divr, 'mix'), float)
    ust = np.asarray(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE), float)
    gold = np.asarray(DA.gold_r(idx), float)
    tb = np.asarray(DA._short_rate(idx), float) / 252.0

    def runB(att, defr=None, th=-0.16):
        Dx = dict(D); Dx['qldr'] = np.asarray(att, float)
        Dx['schdr'] = np.asarray(defr if defr is not None else basket, float)
        lad = STRATS['B']['ladder'] if th == -0.16 else [(('dd', th), 1.0, 0)]
        with contextlib.redirect_stdout(io.StringIO()):
            c, w, t = RL.run(Dx, lad, enter=(th if th != -0.16 else STRATS['B']['enter']))
        return np.asarray(c, float), np.asarray(w, float)

    base_c, base_w = runB(qldr)
    base = evaluate(base_c, idx, base_w)
    print(f"  기준 = 현행 B: MDD {base['mdd']:.1f}% · CAGR {base['cagr']:.2f}% · 최종 {base['final']:,.0f}배 · "
          f"20년 p05 {base['p05_20']:.1f}배 · 10년 중앙 {base['med10']:.1f}배 · 변동성 {base['vol']:.1f}% · 전환 {base['sw']}회")
    print(f'  목표: MDD ≥ {TARGET:.0f}%  (즉 {abs(TARGET):.0f}% 보다 얕게)')

    rows = []

    def scan(label, maker, grid, fmt):
        """제약을 만족하는 첫 지점(가장 공격적인 쪽)을 찾는다."""
        found = None
        for g in grid:
            c, w = maker(g)
            e = evaluate(c, idx, w)
            if e['mdd'] >= TARGET:
                found = (g, e); break
        if found:
            rows.append((label + ' ' + fmt(found[0]), found[1]))
        else:
            rows.append((label + ' (도달 불가)', None))

    # ① 공격 다리 배합
    grid_w = [round(1 - 0.02 * i, 2) for i in range(0, 26)]
    for nm, asset in (('배합 · 배당', divr), ('배합 · 금', gold), ('배합 · 국채', ust),
                      ('배합 · 방어바스켓', basket), ('배합 · 현금', tb)):
        def mk(w, a=asset):
            att = DA.mix_monthly_parts(idx, {'a': w, 'b': 1 - w}, {'a': qldr, 'b': np.nan_to_num(a)})
            return runB(att)
        scan(nm, mk, grid_w, lambda g: f'QLD {g*100:.0f}%')

    # ② 배율 낮추기
    def mk_lev(k):
        return runB(k * rq - (k - 1.0) * cday)
    scan('배율 낮추기', mk_lev, [round(2.0 - 0.05 * i, 2) for i in range(0, 21)], lambda g: f'{g:.2f}배')

    # ③ 문턱 얕게
    def mk_th(th):
        return runB(qldr, th=th)
    scan('문턱 얕게', mk_th, [round(-0.16 + 0.005 * i, 3) for i in range(0, 25)], lambda g: f'{g*100:.1f}%')

    # ④ 공격 상태에서도 방어자산 상시 보유 (= §1 v47 계열)
    def mk_always(x):
        att = DA.mix_monthly_parts(idx, {'a': 1 - x, 'b': x}, {'a': qldr, 'b': basket})
        return runB(att)
    scan('상시 방어 혼합', mk_always, [round(0.02 * i, 2) for i in range(0, 26)], lambda g: f'방어 {g*100:.0f}%')

    # ⑤ 조합 — 배율 1.7배 + 배당 배합
    def mk_combo(w):
        lev = 1.7 * rq - 0.70 * cday
        att = DA.mix_monthly_parts(idx, {'a': w, 'b': 1 - w}, {'a': lev, 'b': divr})
        return runB(att)
    scan('조합 1.7배 + 배당', mk_combo, grid_w, lambda g: f'레버 {g*100:.0f}%')

    print('\n' + L); print(f'제약(MDD ≥ {TARGET:.0f}%)을 **간신히** 만족하는 지점 — 같은 낙폭을 가장 싸게 사는 경로는?'); print(L)
    print(f"  {'경로':<28}{'MDD':>8}{'CAGR':>8}{'최종배수':>13}{'vs현행':>8}{'20년 p05':>10}{'vs현행':>9}"
          f"{'10년중앙':>10}{'10년최악5%':>11}{'변동성':>8}{'전환':>6}")
    # ★ 기준 행에도 실제 숫자를 넣는다 — 「기준」·「—」 같은 단어를 숫자 칸에 넣지 않는다(소유자 지시 2026-09-03)
    print(f"  {'현행 B (제약 위반)':<28}{base['mdd']:>7.1f}%{base['cagr']:>7.2f}%{base['final']:>13,.0f}{1.00:>7.2f}배"
          f"{base['p05_20']:>9.1f}배{1.00:>7.2f}배{base['med10']:>9.1f}배{base['p05_10']:>10.1f}배{base['vol']:>7.1f}%{base['sw']:>6}")
    ok = [(nm, e) for nm, e in rows if e]
    for nm, e in sorted(ok, key=lambda t: -t[1]['p05_20']):
        print(f"  {nm:<28}{e['mdd']:>7.1f}%{e['cagr']:>7.2f}%{e['final']:>13,.0f}{e['final']/base['final']:>7.2f}배"
              f"{e['p05_20']:>9.1f}배{e['p05_20']/base['p05_20']:>8.2f}배{e['med10']:>9.1f}배{e['p05_10']:>10.1f}배"
              f"{e['vol']:>7.1f}%{e['sw']:>6}")
    for nm, e in rows:
        if e is None:
            print(f'  {nm:<28} — 이 축만으로는 목표에 못 간다')

    if ok:
        best = max(ok, key=lambda t: t[1]['p05_20'])
        print(f"\n  **사전 판정 기준(20년 p05 최대) 적용 → {best[0]}**  ·  부의 바닥 {best[1]['p05_20']:.1f}배 "
              f"(현행 {base['p05_20']:.1f}배의 {best[1]['p05_20']/base['p05_20']:.2f}배) · 최종배수는 현행의 {best[1]['final']/base['final']:.2f}배")

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 「MDD 50%」는 54년 전 구간 기준이다. 소유자의 지평이 10~20년이면 제약도 그 창에서 걸어야 한다 — 창이 짧으면 MDD 자체가 작아진다.')
    print('  Q-b 낙폭을 낮추는 대가가 부의 바닥(20년 p05)에서 나가는지 중앙값에서 나가는지는 경로마다 다르다 — 위 표의 두 열을 같이 볼 것.')


if __name__ == '__main__':
    main()
