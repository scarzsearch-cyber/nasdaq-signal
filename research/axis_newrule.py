# -*- coding: utf-8 -*-
"""
[v41] -16/-16 · -16/-11 을 능가하는 규칙이 있는가 — 올바른 문턱으로 재탐색

v40 에서 "8번 해봤으니 충분"이 틀린 논리임을 확인했다. 진짜 제약은 시도 횟수가
아니라 **독립 위기 19회**라는 표본이다. 위기 하나를 빼면 결과가 크게 움직인다:

    최종배수     ±18.6%p (2σ = 37.2%p)   <- 복리로 증폭돼 둔하다
    **Calmar     ±5.1%p  (2σ = 10.2%p)**  <- 가장 예민한 지표
    20년창 중앙  ±21.6%p (2σ = 43.2%p)
    20년창 5분위 ±12.3%p (2σ = 24.7%p)

**Calmar 로 재면 10%p 만 넘어도 판별된다.** 최종배수로 재던 이전 기준(70%p)은
너무 둔해서 진짜 개선을 놓쳤을 수 있다. 그래서 다시 훑는다.

[탐색 축 — 이번엔 넓게]
  1  진입x복귀 격자를 촘촘히 (2%p 간격 -> 1%p, 범위도 확장)
  2  룩백 (126 / 189 / 252 / 378 / 504일)
  3  쿨다운 복귀 (최소 N일 방어 유지)
  4  저점대비 반등 복귀 (V자 조기 복귀)
  5  방어 바스켓 재조정 주기 (월/분기/없음)

[이미 기각된 것 — 반복하지 말 것]
  부분비중·사다리(v18/v19/v22) · 방어자산 동적선택(v27) · 매크로 지표(v30/v31)
  · 변동성 가드(v32) · 낙폭 매수(v40)

판정: Calmar 개선 10.2%p(2σ) 초과 + 좌측꼬리 비악화 + 워크포워드 통과.
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_data as H
import hist_defensive as DF
from axis_lib import rule_w
from axis_defmix import materials, mix_monthly_from, sim_def
from research_kit import dist, verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

THR_CALMAR = 0.102          # 2σ (v41 §0 에서 실측)
THR_FINAL = 0.372


def dd_from(px_all, lb, eval_idx=None):
    """절단 전 가격 이력에서 낙폭을 만든 뒤 평가 구간만 자른다."""
    px_all = pd.Series(px_all, copy=False).astype(float)
    dd = px_all / px_all.rolling(lb, min_periods=lb).max() - 1
    if eval_idx is not None:
        missing = pd.Index(eval_idx).difference(px_all.index)
        if len(missing):
            raise ValueError(f'평가일 {len(missing)}개가 전체 가격 이력에 없다.')
        dd = dd.reindex(eval_idx)
    return dd.fillna(0.0).values


def path_key(values):
    """완전히 같은 결과 경로를 같은 후보로 세기 위한 정확한 키."""
    a = np.ascontiguousarray(values, dtype=np.float64)
    return (a.shape, a.tobytes())


def adoption_gate_state(calmar_pass, tail_pass, accum_kr_pass=None, wfa_pass=None):
    """v41의 네 필수 관문. 미측정(None)은 채택할 수 없게 실패-폐쇄한다."""
    checks = {
        'calmar': bool(calmar_pass),
        'tail': bool(tail_pass),
        'accum_kr': accum_kr_pass is not None and bool(accum_kr_pass),
        'wfa': wfa_pass is not None and bool(wfa_pass),
    }
    checks['adopt'] = all(checks.values())
    return checks


def _selfcheck_contracts():
    # 평가 시작 전에 있던 고점이 첫 평가일 낙폭에 반드시 남아야 한다.
    ix = pd.date_range('2000-01-03', periods=6, freq='B')
    px = pd.Series([100.0, 120.0, 90.0, 80.0, 85.0, 90.0], index=ix)
    got = dd_from(px, 3, ix[3:])
    expected = (px / px.rolling(3, min_periods=3).max() - 1).reindex(ix[3:]).values
    naive = dd_from(px.reindex(ix[3:]), 3)
    assert np.allclose(got, expected)
    assert got[0] < -0.30 and naive[0] == 0.0

    # 이미 방어 중인 추가 하락은 최초 진입 뒤의 쿨다운 시계를 되감지 않는다.
    dd = np.array([-0.10, -0.17, -0.18, -0.17, -0.15])
    assert np.array_equal(cool_w(dd, -0.16, -0.16, 3), [1, 0, 0, 0, 1])
    assert np.array_equal(cool_w(dd, -0.16, -0.16, 0), rule_w(dd, -0.16, -0.16))

    # 중복 경로는 행 수를 부풀리지 않고, 미측정 후속 관문은 채택을 막는다.
    assert len({path_key([1, 0]), path_key([1, 0]), path_key([1, 1])}) == 2
    assert not adoption_gate_state(True, True)['adopt']
    assert adoption_gate_state(True, True, True, True)['adopt']


def met(c):
    a = np.asarray(c)
    n = len(a)
    g = a[-1] ** (252 / n) - 1
    m = (a / np.maximum.accumulate(a) - 1).min()
    return dict(final=float(a[-1]), cagr=g, mdd=float(m), calmar=g / abs(m))


def roll(c, yrs=20, step=63):
    a = np.asarray(c)
    L = yrs * 252
    if len(a) <= L:
        return np.array([np.nan])
    return np.array([a[s + L] / a[s] for s in range(0, len(a) - L, step)])


def cool_w(ddv, enter, exit_, cool):
    """쿨다운 복귀 — 방어 진입 후 최소 cool 거래일은 유지."""
    n = len(ddv)
    w = np.empty(n)
    cur = 1.0
    since = 10 ** 9
    for i in range(n):
        if cur >= 1.0:
            if ddv[i] <= enter:
                cur = 0.0; since = 0
        else:
            since += 1
            if ddv[i] > exit_ and since >= cool:
                cur = 1.0
        w[i] = cur
    return w


def vshape_w(ddv, enter, exit_, bounce):
    """저점대비 반등 복귀 — 도피 중 저점에서 bounce %p 회복하면 조기 복귀."""
    n = len(ddv)
    w = np.empty(n)
    cur = 1.0
    lo = 0.0
    for i in range(n):
        if cur >= 1.0:
            if ddv[i] <= enter:
                cur = 0.0; lo = ddv[i]
        else:
            lo = min(lo, ddv[i])
            if ddv[i] > exit_ or (ddv[i] - lo >= bounce and ddv[i] > enter):
                cur = 1.0
        w[i] = cur
    return w


def main():
    _selfcheck_contracts()
    D = DF.build('chain')
    idx, px, ddq = D['idx'], D['px'], D['ddv']
    proxy_r, _ = H.qqq_proxy()
    px_all = (1 + proxy_r).cumprod()
    if not np.allclose(px_all.reindex(idx).values, px.values, rtol=1e-12, atol=1e-12):
        raise AssertionError('전체 이력 가격과 평가 구간 가격이 일치하지 않는다.')
    if not np.allclose(dd_from(px_all, 252, idx), ddq, rtol=0.0, atol=1e-14):
        raise AssertionError('252일 전체-이력 낙폭이 기준 엔진과 일치하지 않는다.')

    base_w = rule_w(ddq, -0.16, -0.16)
    for bounce in (0.03, 0.05, 0.08, 0.10, 0.15, 0.20):
        assert np.array_equal(vshape_w(ddq, -0.16, -0.16, bounce), base_w)
    assert not np.array_equal(vshape_w(ddq, -0.16, -0.11, 0.05), base_w)

    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    base_curve = sim_def(D, base_w, defr)
    base_key = path_key(base_curve)
    B = met(base_curve)
    rb = roll(base_curve)
    print(f"기준선 B(-16/-16): {B['final']:,.0f}배  Calmar {B['calmar']:.3f}  MDD {B['mdd']*100:.2f}%")
    print(f"판별 문턱(2σ): Calmar {THR_CALMAR*100:.1f}%p  최종배수 {THR_FINAL*100:.1f}%p\n")

    best = []
    best_keys = set()
    evaluated_keys = []
    group_counts = {}

    def report(tag, rows, top=6):
        group_counts[tag] = len(rows)
        for nm, m, rr, c in rows:
            key = path_key(c)
            evaluated_keys.append(key)
            dc = m['calmar'] / B['calmar'] - 1
            if dc > THR_CALMAR and key not in best_keys:
                best.append((tag, nm, m, rr, dc))
                best_keys.add(key)
        rows.sort(key=lambda r: -r[1]['calmar'])
        print(f"  {'':<22}{'최종배수':>12}{'Calmar':>9}{'현행대비':>10}{'MDD':>9}{'20년5분위':>11}")
        for nm, m, rr, c in rows[:top]:
            dc = m['calmar'] / B['calmar'] - 1
            mark = ' ***' if dc > THR_CALMAR else ''
            duplicate = '  (=기준선 중복)' if path_key(c) == base_key else ''
            p5 = np.percentile(rr, 5) if np.isfinite(rr).all() else np.nan
            print(f"  {nm:<22}{m['final']:>12,.0f}{m['calmar']:>9.3f}{dc*100:>9.1f}%"
                  f"{m['mdd']*100:>8.2f}%{p5:>10.2f}{mark}{duplicate}")
        print()

    # ---------------------------------------------------------------- 1 격자
    print("=" * 86)
    print("1. 진입 x 복귀 격자 — 1%p 간격, 범위 확장")
    print("=" * 86)
    rows = []
    for e in np.arange(-0.24, -0.09, 0.01):
        for x in np.arange(e, -0.03, 0.01):
            w = rule_w(ddq, round(e, 2), round(x, 2))
            c = sim_def(D, w, defr)
            rows.append((f'{e*100:.0f}/{x*100:.0f}', met(c), roll(c), c))
    report('격자', rows, 8)

    # ---------------------------------------------------------------- 2 룩백
    print("=" * 86)
    print("2. 룩백 — 252일이 최적인가")
    print("=" * 86)
    rows = []
    for lb in (63, 126, 189, 252, 378, 504, 756):
        dv = dd_from(px_all, lb, idx)
        for e, x in ((-0.16, -0.16), (-0.16, -0.11), (-0.12, -0.12), (-0.20, -0.20)):
            w = rule_w(dv, e, x)
            c = sim_def(D, w, defr)
            rows.append((f'{lb}일 {e*100:.0f}/{x*100:.0f}', met(c), roll(c), c))
    report('룩백', rows, 8)

    # ---------------------------------------------------------------- 3 쿨다운
    print("=" * 86)
    print("3. 쿨다운 복귀 — 최소 N일 방어 유지")
    print("=" * 86)
    rows = []
    for cool in (0, 21, 42, 63, 126, 189, 252):
        for e, x in ((-0.16, -0.16), (-0.16, -0.11)):
            w = cool_w(ddq, e, x, cool)
            c = sim_def(D, w, defr)
            rows.append((f'쿨{cool}일 {e*100:.0f}/{x*100:.0f}', met(c), roll(c), c))
    report('쿨다운', rows, 8)

    # ---------------------------------------------------------------- 4 V자
    print("=" * 86)
    print("4. 저점대비 반등 복귀 — V자 조기 복귀")
    print("=" * 86)
    rows = []
    for b in (0.03, 0.05, 0.08, 0.10, 0.15, 0.20):
        for e, x in ((-0.16, -0.16), (-0.16, -0.11)):
            w = vshape_w(ddq, e, x, b)
            c = sim_def(D, w, defr)
            rows.append((f'반등{b*100:.0f}%p {e*100:.0f}/{x*100:.0f}', met(c), roll(c), c))
    report('V자', rows, 8)

    # ---------------------------------------------------------------- 5 재조정
    print("=" * 86)
    print("5. 방어 바스켓 재조정 주기")
    print("=" * 86)
    from axis_defmix import sim_hold
    rows = []
    W = rule_w(ddq, -0.16, -0.16)
    for reb, nm in ((None, '재조정 없음'), ('M', '월 1회'), ('Q', '분기 1회')):
        c = sim_hold(D, W, comp, {'div': .4, 'ust5': .4, 'gold': .2}, rebal=reb)
        rows.append((nm, met(c), roll(c), c))
    report('재조정', rows, 3)

    # ---------------------------------------------------------------- 판정
    print("=" * 86)
    print("판정")
    print("=" * 86)
    total = sum(group_counts.values())
    distinct = len(set(evaluated_keys))
    baseline_dupes = sum(k == base_key for k in evaluated_keys)
    print(f"  평가행 {total}개 · 서로 다른 결과경로 {distinct}개 · 기준선 중복행 {baseline_dupes}개")
    print("  " + " + ".join(f"{tag} {n}개" for tag, n in group_counts.items()))
    best.sort(key=lambda r: -r[4])
    if not best:
        print(f"  **문턱(Calmar +{THR_CALMAR*100:.1f}%p)을 넘은 후보 없음.**")
        print(f"  현행 -16/-16 이 여전히 최선이다.")
    else:
        print(f"  문턱을 넘은 서로 다른 후보경로 {len(best)}개 — 정밀검증 필요:")
        for tag, nm, m, rr, dc in best:
            p5b = np.percentile(rb, 5)
            p5 = np.percentile(rr, 5)
            gates = adoption_gate_state(dc > THR_CALMAR, p5 >= p5b,
                                        accum_kr_pass=None, wfa_pass=None)
            v = verdict(f'{tag} {nm}', [
                (f'Calmar +{THR_CALMAR*100:.0f}%p 초과', gates['calmar'], f'{dc*100:+.1f}%'),
                ('좌측꼬리 비악화', gates['tail'], f'{p5:.2f} vs {p5b:.2f}'),
                ('적립식·원화 관문', gates['accum_kr'], '미도달'),
                ('워크포워드 관문', gates['wfa'], '미도달'),
            ])
            assert v['adopt'] == gates['adopt']
            print(v['text']); print()
            print(f"  참고(필수 관문 아님): MDD {m['mdd']*100:.2f}% vs {B['mdd']*100:.2f}%\n")


if __name__ == '__main__':
    main()
