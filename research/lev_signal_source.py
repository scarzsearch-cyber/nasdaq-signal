# -*- coding: utf-8 -*-
"""
[빈칸 채우기] 고배율판에서 **신호를 무엇의 낙폭으로 내는가** — QQQ 1배 vs 레버리지 상품 자체.

발단 (2026-09-03): 소유자 질문 「그 3배는 현행 B 를 그대로 적용한 거야, TQQQ 전용으로
개량한 버전이야?」. 코드로 확인하니 **현행 B 그대로**다 —
    wB = rule_dd(px, -0.16, -0.16)   # px 는 QQQ 1배 지수
    lev_r(D, k) = k*pxr - (k-1)*c_daily   # 공격 다리만 k 배
즉 문턱·룩백·방어 바스켓이 전부 동일하고 바뀌는 것은 공격 다리 하나뿐이다.
`lev_th.py` 는 「배율이 오르면 문턱을 바꿔야 하나」를 답했고(모든 k 에서 -16 이 봉우리),
그 파일은 스스로 **「신호는 항상 QQQ 1배 지수 낙폭(현행 구조)」**이라고 축을 못박았다.
→ **「신호 원천을 레버리지 상품 자체로 바꾸면?」은 한 번도 안 쟀다.** 그 빈칸.

★ 사전 등록 예측 (결과 보기 전):
    P1 TQQQ 자체 낙폭 -16 게이트는 얕은 문턱과 같아져 -16@QQQ 에 크게 진다. -> 맞음 (948배 차)
    P2 TQQQ 낙폭을 QQQ 낙폭으로 환산하면 -16@QQQ 는 -45% 근처다.            -> 맞음 (-46.1%)
    P3 따라서 이것은 새 규칙이 아니라 **같은 규칙의 다른 표기법**이다.         -> 맞음

판정: **채택 후보 아님 · 전략 무접촉.** 새 축이 아니라 단위 변환이었다.
  -48@TQQQ 가 -16@QQQ 와 거의 같은 칸을 가리키고(환산 -46.1%), 그 근처에서
  최종배수 2.69M/Calmar 0.441 vs 현행 3.10M/0.398 로 **격자 이웃 잡음 안**이다.
  (v210 자료 재실행 2026-09-05: -48 칸 2.20M/0.438 vs 현행 3.22M/0.403 · 환산 -45.8% — 결론 동일)
  ⚠ 정확히 같지는 않다 — 일일 리셋 탓에 레버리지 낙폭은 기초 낙폭의 함수가 아니다
  (같은 QQQ -16% 라도 가는 길에 따라 TQQQ 낙폭이 다르다). 그래서 표기법을 바꾸면
  **의도치 않게 경로 의존을 규칙에 들여오게 된다** — 그것만으로도 안 바꿀 이유가 된다.
  ★ -48 칸은 **내가 손으로 고른 칸**이라 §-1 ⓑ 대상이다. 채택 제안이 아니므로
  반증을 돌리지 않았고, 따라서 **이 표를 근거로 -48 을 권고하지 마라.**

⚠ 이 문서 계열 전체가 「미국 진출 시」 가정이다 — 국내는 2배 상한·동결(§2).
  합성 잣대 주의는 LEVERAGE_US.md §1 그대로(k>2 에 비용 과대 부과 = 보수적).

실행: python research/lev_signal_source.py [k]      기본 k=3.0
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

import eng_common as EC                                  # noqa: E402
from axis_lib import lev_r                               # noqa: E402

LB = 252


def met(c):
    yrs = len(c) / 252.0
    d = c / np.maximum.accumulate(c) - 1
    cagr = c[-1] ** (1 / yrs) - 1
    W = 5040                                             # 20년
    return (c[-1], 100 * cagr, 100 * d.min(),
            cagr / abs(d.min()), float(np.quantile(c[W:] / c[:-W], 0.05)))


def main():
    k = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    G, X = EC.selfcheck()
    idx = G.idx
    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    px = pd.Series(G.D['px'], index=idx)
    levr = np.asarray(lev_r(G.D, k), float)
    lev_px = pd.Series(np.cumprod(1 + np.nan_to_num(levr)), index=idx)

    def gate(series, th):
        dd = (series / series.rolling(LB, min_periods=LB).max() - 1).fillna(0)
        return (dd.values > th).astype(float)

    def run(w):
        return np.asarray(EC.sim2(np.asarray(w, float), levr, MIXR), float)

    print('신호 원천 비교 (k=%.1f · 방어 mix 동일 · 대칭 문턱 · 룩백 %d)' % (k, LB))
    hdr = '%-26s %12s %7s %8s %8s %8s' % (
        '신호 원천 / 문턱', '최종배수', 'CAGR', 'MDD', 'Calmar', 'p05')
    print(hdr); print('-' * len(hdr))
    print('%-26s %12.0f %7.2f %8.1f %8.3f %8.1f'
          % ('QQQ 1배 낙폭 -16 (현행)', *met(run(gate(px, -0.16)))))
    for th in (-0.16, -0.20, -0.30, -0.40, -0.48, -0.55):
        print('%-26s %12.0f %7.2f %8.1f %8.3f %8.1f'
              % ('%.0fx 자체 낙폭 %.0f' % (k, 100 * th), *met(run(gate(lev_px, th)))))
    print()

    dd1 = (px / px.rolling(LB, min_periods=LB).max() - 1).fillna(0).values
    ddk = (lev_px / lev_px.rolling(LB, min_periods=LB).max() - 1).fillna(0).values
    b1 = (dd1 <= -0.155) & (dd1 >= -0.165)
    bk = (ddk <= -0.155) & (ddk >= -0.165)
    print('[환산 — 두 단위는 서로 몇 %에 대응하나]')
    print('  QQQ 낙폭 -16%% 인 날의 %.0fx 낙폭   중앙 %.1f%%  (사분위 %.1f ~ %.1f)'
          % (k, 100 * np.median(ddk[b1]),
             100 * np.percentile(ddk[b1], 25), 100 * np.percentile(ddk[b1], 75)))
    print('  %.0fx 낙폭 -16%% 인 날의 QQQ 낙폭   중앙 %.1f%%' % (k, 100 * np.median(dd1[bk])))
    print('  => %.0fx -16 게이트는 QQQ 로 치면 격자의 얕은 끝(-10) 바깥이다.' % k)
    print('  => 사분위 폭이 넓다는 것이 곧 **경로 의존**이다 — 단위 변환이 1:1 이 아니다.')
    print()
    print('[이 측정이 낳은 질문]')
    print('  Q-a 표기법을 바꾸면 경로 의존이 규칙에 들어온다 — 현행이 기초지수를')
    print('      보는 것은 그 자체로 설계 결정이었나, 아니면 우연인가?')
    print('      (01 § 판정 정의는 QQQ 종가 기준 — 상품이 무엇이든 신호가 같다는')
    print('       것은 TIGER 418660 이 바뀌어도 규칙이 산다는 뜻이다. 설계 결정 쪽.)')
    print('  Q-b -48@%.0fx 칸은 손으로 고른 칸이다 — 권고로 쓰려면 §-1 ⓑ 무작위 반증 필요.' % k)


if __name__ == '__main__':
    main()
