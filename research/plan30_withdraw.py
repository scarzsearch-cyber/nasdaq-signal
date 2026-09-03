# -*- coding: utf-8 -*-
"""
[조건부 설계] 소유자의 실제 계획으로 다시 재기 — 지평 30년 · 5년 무인출 · 7년차부터 인출 · 10년차부터 생활 (2026-09-03)

소유자: 「내 지평은 30년이야. 사실 그 이상 해도 되지만 **돈을 계속 빼서 쓸 거야**, 어느 정도 양의 복리가 된다면.
        처음 5년은 빼내지 않고 무조건 투자 / 그 이후엔 결과에 따라 (7년차쯤부터) / 10년이 되면 반드시 빼내면서 생활.」

⚠ **전략 무접촉.** 이 파일은 「목표가 인출이면 순위가 바뀌는가」만 잰다. 채택은 소유자 결정.

★ **먼저 정정** (소유자가 §5-35 표를 「현금 20% > SCHD 20%」로 읽을 수 있다): 그 표는 **MDD −50% 를 맞추는 지점**이라
  비중이 서로 다르다 — 현금은 **20%** 로 −49.4% 에 닿지만 **배당은 32% 를 넣어야** −49.3% 에 닿는다.
  **SCHD 20% 는 −53.7% 라 애초에 그 표의 제약을 만족하지 못한다**(§5-32). 같은 낙폭에서 비교하면 배당 32%(p05 27.5)와 현금 20%(27.1)는 **거의 같다.**

무엇을 재나: 30년 창(**모든 시작일**)에서 소유자 인출 일정을 그대로 태운다.
  · 1~5년차 인출 0 · 6년차 0 · **7~9년차: 목표 인출액의 50%** · **10년차부터 100%**
  · 인출 규칙 두 가지 — (a) **평가액 비율**(초기 4%/년, 매년 그해 평가액 기준 → 소유자의 「양의 복리면 뺀다」에 가깝다)
                       (b) **정액**(초기 자산의 4%/년 고정, 물가 미반영 — 이 저장소에 실질 인출 계열이 없다는 §withdraw 한계 그대로)
  · 월 1회 인출(생활비는 매달 나간다). 인출은 **그 시점 포트폴리오에서 비례 매도**.
후보: 현행 B · 배당 20% · 배당 32% · 현금 20% · 금 20% · 헤지6/4(배당 40%) · 배율 1.55배.

**판정 기준 (결과 전 등록)**: 인출이 목적이면 잣대는 최종배수가 아니다 —
  ① **30년 총 인출액**(실제로 쓴 돈, 중앙) ② **최악 연간 인출액**(소득 붕괴 · §withdraw 가 「진짜 위험」이라 한 것)
  ③ **소진 확률** ④ 30년 말 잔액. **①과 ②가 함께 높은 것**이 답이고, 셋 다 창 분포(모든 시작일)로 본다.

예측 (결과 전 · 틀리면 그대로 적는다 §-1 ⑦):
  P1 평가액 비율 인출에서는 **소진이 구조적으로 불가능**(항상 남는 비율만 뺀다)하므로 소진 확률은 전부 0.
  P2 **총 인출액은 현행 B 가 1위** — 인출액이 평가액에 비례하므로 부가 큰 쪽이 이긴다.
  P3 그러나 **최악 연간 인출액에서는 순위가 뒤집혀** 배합 쪽이 앞선다(변동성이 낮아 바닥 소득이 덜 무너진다).
  P4 정액 인출에서는 현행 B 의 소진 확률이 배합보다 **높다**(sequence risk).
  P5 30년 창의 비중첩 수는 1.8개뿐이라 **확률이 아니라 경향**으로만 읽어야 한다.

실행: python research/plan30_withdraw.py   (약 60초 · 네트워크 0 · 파일 쓰기 0)
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

L = '=' * 124
RATE = 0.04            # 연 4%
H = 30                 # 지평 30년


def schedule(month):
    """0-기준 월 인덱스 → 그 달의 인출 배율 (소유자 일정)."""
    y = month / 12.0
    if y < 6:
        return 0.0
    if y < 9:
        return 0.5
    return 1.0


def simulate(curve_m, mode):
    """월간 곡선(수익률 곱) 위에서 인출. 반환: (총인출, 연간인출 시계열, 말잔액, 소진여부)"""
    n = len(curve_m) - 1
    r = curve_m[1:] / curve_m[:-1] - 1
    bal = 1.0
    base = RATE / 12.0
    draws = np.zeros(n)
    for t in range(n):
        bal *= (1 + r[t])
        if bal <= 0:
            bal = 0.0
        f = schedule(t)
        d = (bal * base * f) if mode == 'pct' else (base * f)   # 비율형 / 정액형(초기 1.0 기준)
        d = min(d, bal)
        bal -= d
        draws[t] = d
    yearly = draws.reshape(-1, 12).sum(axis=1) if n % 12 == 0 else None
    return draws.sum(), yearly, bal, bool(bal <= 1e-9)


def main():
    print(L); print('소유자 계획으로 다시 재기 — 30년 · 5년 무인출 · 7년차 절반 · 10년차 전액 (전략 무접촉)'); print(L)
    with contextlib.redirect_stdout(io.StringIO()):
        D = dict(DF.build('chain'))
    idx = pd.DatetimeIndex(D['idx'])
    qldr = np.asarray(D['qldr'], float); divr = np.asarray(D['schdr'], float)
    px = pd.Series(D['px'], index=idx).astype(float)
    rq = np.nan_to_num(px.pct_change().values)
    cday = 2 * rq - np.nan_to_num(qldr)
    basket = np.asarray(defensive_r(idx, divr, 'mix'), float)
    gold = np.asarray(DA.gold_r(idx), float)
    tb = np.asarray(DA._short_rate(idx), float) / 252.0

    def runB(att):
        Dx = dict(D); Dx['qldr'] = np.asarray(att, float); Dx['schdr'] = basket
        with contextlib.redirect_stdout(io.StringIO()):
            c, _, _ = RL.run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'])
        return np.asarray(c, float)

    def blend(w, other):
        return DA.mix_monthly_parts(idx, {'a': w, 'b': 1 - w}, {'a': qldr, 'b': np.nan_to_num(other)})

    CANDS = {
        '현행 B (공격 100%)': runB(qldr),
        '배당 20% (QLD 80)': runB(blend(0.8, divr)),
        '배당 32% (QLD 68)': runB(blend(0.68, divr)),
        '현금 20% (QLD 80)': runB(blend(0.8, tb)),
        '금 20% (QLD 80)': runB(blend(0.8, gold)),
        '헤지6/4 (배당 40%)': runB(blend(0.6, divr)),
        '배율 1.55배': runB(1.55 * rq - 0.775 * cday),
    }
    monthly = {k: pd.Series(v, index=idx).resample('MS').last().values for k, v in CANDS.items()}
    mlen = len(next(iter(monthly.values())))
    W = H * 12
    starts = list(range(0, mlen - W))
    print(f'  30년 창: 시작 {len(starts)}개월 (비중첩 {len(starts)/W:.1f}개) · 인출률 연 {RATE*100:.0f}% · 월 1회 비례 매도')

    for mode, lab in (('pct', '평가액 비율 인출 (그해 잔액의 4%/년 — 「양의 복리면 뺀다」에 가깝다)'),
                      ('fix', '정액 인출 (초기 자산의 4%/년 고정 · 물가 미반영)')):
        print('\n' + L); print(f'[{lab}]'); print(L)
        print(f"  {'후보':<22}{'총인출 중앙':>12}{'총인출 최악5%':>14}{'최악 연인출':>12}{'말잔액 중앙':>12}"
              f"{'말잔액 최악5%':>14}{'소진':>7}{'인출 변동성':>12}")
        res = {}
        for nm, mc in monthly.items():
            tot, worst, endb, ruin, ivol = [], [], [], 0, []
            for s in starts:
                seg = mc[s:s + W + 1]
                if len(seg) < W + 1 or not np.isfinite(seg).all():
                    continue
                seg = seg / seg[0]
                t, y, b, rn = simulate(seg, mode)
                tot.append(t); endb.append(b); ruin += rn
                if y is not None and len(y) >= 21:
                    live = y[9:]                  # 10년차부터 전액 인출 구간
                    worst.append(live.min()); ivol.append(live.std() / max(live.mean(), 1e-9))
            tot = np.array(tot); endb = np.array(endb); worst = np.array(worst); ivol = np.array(ivol)
            res[nm] = (np.median(tot), np.quantile(tot, .05), np.median(worst), np.median(endb),
                       np.quantile(endb, .05), ruin / max(len(tot), 1), np.median(ivol))
        for nm, v in sorted(res.items(), key=lambda t: -t[1][0]):
            print(f'  {nm:<22}{v[0]:>11.2f}배{v[1]:>13.2f}배{v[2]*100:>11.2f}%{v[3]:>11.2f}배'
                  f'{v[4]:>13.2f}배{v[5]*100:>6.0f}%{v[6]:>11.2f}')
        print('  ※ 총인출·말잔액은 시작 자산 1.0 기준. 「최악 연인출」은 10년차 이후 연간 인출액의 최소(시작 자산 대비 %).')

    print('\n' + L); print('참고 — 인출 없는 30년 창(같은 시작일)에서의 순위'); print(L)
    print(f"  {'후보':<22}{'30년 중앙':>11}{'30년 최악5%':>13}{'MDD 중앙':>10}")
    for nm, mc in monthly.items():
        rs, ds = [], []
        for s in starts:
            seg = mc[s:s + W + 1]
            if len(seg) < W + 1 or not np.isfinite(seg).all():
                continue
            seg = seg / seg[0]
            rs.append(seg[-1])
            ds.append(float((pd.Series(seg) / pd.Series(seg).cummax() - 1).min()) * 100)
        print(f'  {nm:<22}{np.median(rs):>10.1f}배{np.quantile(rs, .05):>12.1f}배{np.median(ds):>9.1f}%')

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 30년 창의 비중첩 수는 1.8개다 — 순위는 경향이고 확률이 아니다(§5-32 E 와 같은 한정).')
    print('  Q-b 물가가 빠져 있다(§withdraw 한계 그대로). 정액 인출은 실질로는 더 가혹하다 — 여기 숫자는 낙관 쪽이다.')
    print('  Q-c 인출기 설계 요건(1년치 현금 완충)은 이 표 밖이다 — MEASUREMENT_AUDIT · 설명서 §⑥ 참조.')


if __name__ == '__main__':
    main()
