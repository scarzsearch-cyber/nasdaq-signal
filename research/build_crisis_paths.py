# -*- coding: utf-8 -*-
"""
[v127 항목20] 위기 타임머신 데이터 — data/crisis_paths.json 생성 (로컬 수동 실행)

signal.html 의 위기 궤적(trajectories)은 낙폭%만 담아 계좌가치를 못 그린다.
이 스크립트는 각 위기 고점 이후 400거래일에 대해 두 계좌가치 지수(시작=1.0)를 만든다:
  strategy       — 전략 B(−16/−16, 방어 40/40/20) 적용
  leveraged_hold — 2배 그냥 보유

**새 엔진 로직 0줄 원칙**: deploy/build_stats.py 의 sc_us_2000() 레시피를 그대로 재현
(reentry_lib.build → DA.mix_monthly(MIX_V23) → reentry_lib.run)한 뒤, 위기 구간을
잘라 시작값으로 나누기만 한다. 위기 고점일은 deploy/update_signal.py 의 CRISES 를
import 로 읽는다(deploy/* 무수정). 내장 검증:
  ① 재생성한 전체 곡선의 final 이 data/strategy_stats.json us_2000 B.final 과 일치
  ② 닷컴·GFC(느린 약세장)에서 전략이 그냥 보유보다 덜 빠지고 높게 끝남 (01 §4-1 정합)
  ③ 두 시계열 길이 일치·전부 유한·시작 1.0

자동화 파이프라인에 편입하지 않는다 — build_stats.py 와 같은 「데이터 갱신 시 수동
재실행」 포지션이다.  실행:  python research/build_crisis_paths.py
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/build_crisis_paths.py` 가 import 와 data/ 경로를 못 찾는다.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import datetime
import json
import os
import sys

import numpy as np
import pandas as pd

try:                                   # 윈도우 콘솔 cp949 대비
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_defasset as DA             # noqa: E402
import reentry_lib as RL               # noqa: E402
from reentry_lib import run            # noqa: E402

# 위기 고점일 — deploy/update_signal.py 의 정의를 그대로 읽는다 (수정 아님, 참조만)
_sys.path.insert(0, os.path.join(_ROOT, 'deploy'))
from update_signal import CRISES       # noqa: E402

DAYS = 400                             # trajectories(days=400) 와 같은 창
OUT = os.path.join('data', 'crisis_paths.json')
STATS = os.path.join('data', 'strategy_stats.json')
LADDER_B = [(('dd', -0.16), 1.0, 0)]   # build_stats.STRATS['B'] 와 동일
# 검증 ② 대상 — 느린 약세장에서는 전략이 그냥 보유보다 나아야 한다 (01 §4-1).
# [2026-09-04 코드리뷰] 종전엔 `if name in ('닷컴 2000','GFC 2007')` 로 이름을
# 코드 안에 박아 뒀다. 이 이름의 주인은 deploy/update_signal.py 이고 여기는 읽기만
# 하므로, 거기서 라벨을 바꾸면 이 검사는 **아무 말 없이 안 돈다**(v148: 「검사를
# 추가했다」와 「검사가 돈다」는 다르다). 이름이 사라지면 알아채도록 아래에서 검증한다.
SLOW_BEAR = ('닷컴 2000', 'GFC 2007')


def main():
    # ---- 엔진 곡선 재생성 — build_stats.sc_us_2000('mix') 와 동일 호출 ----
    D = dict(RL.build())
    D['schdr'] = DA.mix_monthly(D['idx'], DA.MIX_V23, D['schdr'])
    curve, w, turn = run(D, LADDER_B, enter=-0.16)

    # 2배 그냥 보유 — build_stats.bench_pack('lev') 와 같은 재료(qldr)로 같은 구간 누적
    lo = int(D['idx'].searchsorted(curve.index[0]))
    rr = np.nan_to_num(np.asarray(D['qldr'][lo:lo + len(curve)], dtype=float)).copy()
    rr[0] = 0.0
    hold = pd.Series(np.cumprod(1 + rr), index=curve.index)

    # ---- 검증 ① 엔진 동치: 전체 곡선 final == 공표 수치 ----
    with open(STATS, encoding='utf-8') as f:
        stats = json.load(f)
    sc = next(s for s in stats['scenarios'] if s['key'] == 'us_2000')
    pub = float(sc['strategies']['B']['final'])
    got = float(curve.iloc[-1])
    if abs(got - pub) > 0.005 + 1e-9:                     # 공표값은 3자리 반올림
        raise SystemExit(f'[실패] 엔진 동치 검증: 재생성 final {got:.3f} != 공표 {pub:.3f}')
    print(f'[검증①] 전체 곡선 final {got:.3f} == strategy_stats us_2000 B {pub:.3f}  OK')

    out = {'_meta': {
        'basis': 'us_2000 달러 — deploy/build_stats.py sc_us_2000 과 동일 재료·규약 '
                 '(reentry_lib.run, 방어 40/40/20 월간 재조정, 세전)',
        'days': DAYS,
        'engine_check': f'전체 곡선 final {got:.3f} == strategy_stats us_2000 B.final {pub:.3f}',
        'generated': datetime.date.today().isoformat(),
        'note': '과거 재현이다 — 예측이 아니다. 갱신은 research/build_crisis_paths.py 수동 실행.',
    }}

    # [코드리뷰] 검증 ② 가 겨누는 이름이 실제로 CRISES 에 있는지 먼저 확인한다.
    # 없으면 그 검사는 조용히 사라진 것이므로 여기서 멈춘다.
    _names = {n for n, _ in CRISES}
    _gone = [n for n in SLOW_BEAR if n not in _names]
    if _gone:
        raise SystemExit(f'[실패] 검증 ② 대상 {_gone} 가 update_signal.CRISES 에 없다 — '
                         f'라벨이 바뀌었다면 SLOW_BEAR 를 같이 고쳐라 (현재 목록: {sorted(_names)})')

    print(f'{"위기":<12} {"일수":>4} {"전략 최저":>9} {"보유 최저":>9} {"전략 최종":>9} {"보유 최종":>9}')
    for name, peak in CRISES:
        i0 = int(curve.index.searchsorted(pd.Timestamp(peak)))
        seg_s = curve.iloc[i0:i0 + DAYS]
        seg_h = hold.iloc[i0:i0 + DAYS]
        # [2026-09-04 코드리뷰] 종전엔 20일 하한만 봤다. 고점이 자료 끝에서 400일
        # 안쪽이면 짧은 배열이 그대로 json 에 실리고, 화면(trajPanel)은 400일 창을
        # 전제로 스크러버를 그리므로 잘린 궤적이 조용히 나간다. 길이를 못 박는다.
        if len(seg_s) != DAYS:
            raise SystemExit(f'[실패] {name}: {DAYS}일이 아니라 {len(seg_s)}일이다 '
                             f'(고점 {peak} 이후 자료가 모자란다 — 자료를 늘리거나 '
                             f'이 위기를 CRISES 에서 빼라)')
        s = (seg_s / seg_s.iloc[0]).values
        h = (seg_h / seg_h.iloc[0]).values
        # ---- 검증 ③ 형식 ----
        assert len(s) == len(h) and np.isfinite(s).all() and np.isfinite(h).all()
        assert abs(s[0] - 1.0) < 1e-12 and abs(h[0] - 1.0) < 1e-12
        print(f'{name:<12} {len(s):>4} {s.min():>9.3f} {h.min():>9.3f} {s[-1]:>9.3f} {h[-1]:>9.3f}')
        # ---- 검증 ② 느린 약세장 정합 (01 §4-1: 닷컴·GFC 는 전략이 덜 빠져야 한다) ----
        if name in SLOW_BEAR:
            if not (s.min() > h.min() and s[-1] > h[-1]):
                raise SystemExit(f'[실패] {name}: 전략이 그냥 보유보다 못하다 — 공표 서술과 모순')
        out[name] = {
            'peak': peak,
            'strategy': [round(float(v), 4) for v in s],
            'leveraged_hold': [round(float(v), 4) for v in h],
        }

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'[완료] {OUT}  ({os.path.getsize(OUT):,} bytes)')


if __name__ == '__main__':
    main()
