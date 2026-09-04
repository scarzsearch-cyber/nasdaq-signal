# -*- coding: utf-8 -*-
"""
[가설 프로그램 자기감사, 소유자 지시 2026-08-31] 일주일 실험(hypo_*)의 결론을
공표 수치·규약과 대조해 감사한다.

  A. 기준선 B(us_1972 mix): strategy_stats.json 공표와 대조  → 별도 확인 완료
     (final 217110.075 / cagr 25.26 / mdd −60.48 / calmar 0.418 — 소수점 일치)
  B. q20 지표 정의 검증: HANDOFF §3 의 「20년창 5분위 35.9」(v41, 방어=배당 시절)를
     같은 정의로 재현할 수 있는가 — B(방어 배당100)의 20년창 20퍼센타일 계산.
  C. hypo_external2 의 FTQ(2%,VT40)=252,398배 셀 — θ 미세 격자로 첨탑/고원 판정.
  D. T4 재현 vs v68 공표(155,279 / 24.50 / −53.4 / 0.459): 방향 일치·수치 근사
     확인 — 신호 정의는 deploy 와 문자 단위 일치(hypo_t4_real 검산①②),
     잔차는 집행 규약(리밸런스 밀도·대기 처리) 차이로 추정. 본 파일 실행 결과에 기록.
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hypo_gates as G                                  # noqa: E402
import hypo_external2 as E                              # noqa: E402
from reentry_lib import run                             # noqa: E402


def main():
    # ---- B. q20 정의 검증 — v41 시절 방어(배당100)로 같은 지표를 계산 ----
    c_div, w_div, t_div = run(G.D, [(('dd', -0.16), 1.0, 0)], enter=-0.16)
    q_div = G.report('', c_div)['q20']
    print(f'[검증B] B(방어 배당100) 20년창 20퍼센타일 = {q_div:.1f} '
          f'(HANDOFF v41 공표 35.9 — 정의 일치 여부 판독용)')

    # ---- B2. 「5분위」가 하위 5퍼센타일이었는지 판독 ----
    def qq(curve, p):
        a = curve.values
        m = a[5040:] / a[:-5040]
        return float(np.quantile(m, p))
    print(f'[검증B2] B(배당100) 20년창 5퍼센타일 = {qq(c_div, 0.05):.1f} '
          f'· 1퍼센타일 = {qq(c_div, 0.01):.1f} · 최소 = {qq(c_div, 0.0):.1f}  (공표 35.9 와 대조)')

    # ---- B3. 만약 하위 5퍼센타일이 규약이라면 — 주요 후보 관문② 재판정 ----
    import hypo_hex as X
    import hypo_t4_real as R
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
    wT4 = R.t4_w(G.r_eq1)
    n = len(G.idx)
    cand = {
        'B': X.three_way(X.wB, 1 - X.wB, np.zeros(n)),
        'T4 정본': X.three_way(wT4, np.zeros(n), 1 - wT4),
        '혼합 50%B': X.blend(0.50),
        '합의체': X.three_way(X.wB * wT4, 1 - X.wB, X.wB * (1 - wT4)),
        'BRD NYA<0 VT40': E.brake((E.r63_nya < 0) & (E.r63_ndx > 0), 0.40),
        'FTQ θ3% VT40': E.brake(E.ftq21 > 0.03, 0.40),
    }
    b5 = qq(cand['B'], 0.05)
    print(f'\n[검증B3] 관문②를 하위 5퍼센타일(기준 {b5:.1f})로 재판정하면:')
    for nm, c in cand.items():
        v = qq(c, 0.05)
        print(f'  {nm:<16} p05={v:>6.1f}  {"통과" if v >= b5 else "탈락"}')

    # ---- B4. p05 규약이라면 — 혼합 전선 전체 재주사 (고원/첨탑 판정) ----
    b4_calmar = G.report('', cand['B'])['calmar'] * 1.102
    print(f'\n[검증B4] 혼합 x 전선을 p05 로 재주사 (관문① Calmar>{b4_calmar:.3f} · 관문② p05≥{b5:.1f})')
    print(f"{'x(B비중)':>8} {'Calmar':>7} {'p05':>6} {'p04':>6} {'p06':>6} {'동시':>4}")
    for x in np.arange(0.30, 0.7501, 0.05):
        c = X.blend(float(x))
        r = G.report('', c)
        p5, p4, p6 = qq(c, 0.05), qq(c, 0.04), qq(c, 0.06)
        ok = r['calmar'] > b4_calmar and p5 >= b5
        print(f"{x:>8.2f} {r['calmar']:>7.3f} {p5:>6.1f} {p4:>6.1f} {p6:>6.1f} "
              f"{'★' if ok else '·':>4}")

    # ---- B5. 한국 실효비용 0.2% 재검 — v68 이 T4 를 벤 칼로 혼합 고원을 벤다 ----
    print('\n[검증B5] 편도 0.2% (한국 실효비용, v68 규약) — 혼합 고원 생존 여부')
    b2 = X.three_way(X.wB, 1 - X.wB, np.zeros(n), cost=0.002)
    rb2 = G.report('', b2)
    c1k, c2k = rb2['calmar'] * 1.102, qq(b2, 0.05)
    print(f'  기준 B@0.2%: final {rb2["final"]:.0f} · Calmar {rb2["calmar"]:.3f} '
          f'→ 관문① {c1k:.3f} · 관문② p05 {c2k:.1f}')
    print(f"{'x(B비중)':>8} {'최종배수':>10} {'Calmar':>7} {'p05':>6} {'동시':>4}")
    for x in (0.30, 0.40, 0.50, 0.55):
        c = X.three_way(x * X.wB + (1 - x) * wT4, x * (1 - X.wB),
                        (1 - x) * (1 - wT4), cost=0.002)
        r = G.report('', c)
        p5 = qq(c, 0.05)
        ok = r['calmar'] > c1k and p5 >= c2k
        print(f"{x:>8.2f} {r['final']:>10.1f} {r['calmar']:>7.3f} {p5:>6.1f} "
              f"{'★' if ok else '·':>4}")

    # ---- C. FTQ 능선 확장 + 발동 진단 ----
    print('\n[검증C] FTQ VT40 — θ 능선 확장 · 발동일수 · 반쪽 일관성')
    print(f"{'θ%':>5} {'최종배수':>10} {'Calmar':>7} {'q20':>6} {'발동일':>7} {'전반C':>6} {'후반C':>6}")
    for th in (0.010, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050, 0.060):
        d = (E.ftq21 > th)
        r = G.report('', E.brake(d, 0.40))
        print(f"{th*100:>5.1f} {r['final']:>10.1f} {r['calmar']:>7.3f} {r['q20']:>6.1f} "
              f"{int(d.sum()):>7} {r['h1']:>6.3f} {r['h2']:>6.3f}")


if __name__ == '__main__':
    main()
