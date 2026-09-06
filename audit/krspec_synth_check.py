# -*- coding: utf-8 -*-
"""research/axis_krspec.py 추정기 합성 검사 (2026-09-06 · 감사 재현 도구 · CI 미등재 · 장부 audit/UNCLEAR34_2026-09-06.md §2).

왜: deploy/build_stats.py·deploy/update_signal.py docstring 이 「채택안 3종 전부 환노출(b2=0.8~1.0)」의 출처로 axis_krspec 을 든다.
    실측값을 재실행하지 않고, **순수 함수**(_ols · weekly · weekly_fx_only · strictly_prior)가 알려진 β 를 회복하는지만 본다.
    파일·원자료 무접촉(모듈 import 만 · 모듈 최상위는 상수·함수 정의뿐).
실행: python audit/krspec_synth_check.py [--root <저장소>]
기대: β1 ≈ 1.0 · β2 ≈ 0.8(±0.05) · 환헤지형 β2 ≈ 0 · strictly_prior 는 같은 날 관측을 제외하고 중복 인덱스는 마지막 값.
"""
import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=DEFAULT_ROOT)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    os.chdir(root)
    if root not in sys.path:
        sys.path.insert(0, root)
    spec = importlib.util.spec_from_file_location('axis_krspec_under_check', os.path.join(root, 'research', 'axis_krspec.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m._selfcheck()
    print('내장 _selfcheck OK (strictly_prior)')

    rng = np.random.default_rng(7)
    idx = pd.bdate_range('2015-01-01', periods=2000)
    rb = rng.normal(0, 0.01, len(idx))       # 기초자산 일수익
    rf = rng.normal(0, 0.004, len(idx))      # 환율 일수익
    noise = rng.normal(0, 0.001, len(idx))
    base = pd.Series(np.exp(np.cumsum(rb)), idx)
    fx = pd.Series(np.exp(np.cumsum(rf)), idx)
    etf = pd.Series(np.exp(np.cumsum(1.0 * rb + 0.8 * rf + noise)), idx)      # β1 = 1 · β2(환) = 0.8
    W = m.weekly(etf, base, fx)
    b, r2 = m._ols(W['e'].values, [W['b'].values, W['f'].values])
    print('주간 회귀 β1 %.3f β2 %.3f R² %.3f (기대 1.0 · 0.8)' % (b[1], b[2], r2))
    etf0 = pd.Series(np.exp(np.cumsum(1.0 * rb + noise)), idx)                # 환헤지형 β2 = 0
    W0 = m.weekly(etf0, base, fx)
    b0, _ = m._ols(W0['e'].values, [W0['b'].values, W0['f'].values])
    print('환헤지 합성 β2 %.3f (기대 0)' % b0[2])
    W1 = m.weekly_fx_only(etf, fx)
    b1, _ = m._ols(W1['e'].values, [W1['f'].values])
    print('환만 회귀 β %.3f (기초 생략 · 기초 수익이 잔차라 표준오차 ≈0.13 · 편향 아님)' % b1[1])
    assert abs(b[1] - 1.0) < 0.03 and abs(b[2] - 0.8) < 0.05 and abs(b0[2]) < 0.05, (b, b0)

    s = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(['2020-01-06', '2020-01-06', '2020-01-08']))
    v, d = m.strictly_prior(s, pd.to_datetime(['2020-01-06', '2020-01-07', '2020-01-08', '2020-01-09']))
    print('strictly_prior 중복·경계:', v.tolist(), [str(x)[:10] for x in d])
    assert np.isnan(v.iloc[0]) and v.iloc[1] == 2.0 and v.iloc[2] == 2.0 and v.iloc[3] == 3.0
    print('ALL OK')


if __name__ == '__main__':
    main()
