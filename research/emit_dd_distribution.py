# -*- coding: utf-8 -*-
"""
[v164] 낙폭 분포 백분위 → `data/dd_percentile.json`

무엇: 54년 검증 표본의 **252거래일 고점 대비 낙폭** 전 구간 분포에서
      1~99 백분위 경계값을 뽑아 저장한다. 화면이 「오늘의 낙폭이 역사에서
      어느 깊이인가」를 말할 때 쓰는 자(ruler)다.

★ 판정에 쓰지 않는다. 위치 정보일 뿐이고, 전환 여부는 −16% 게이트만 정한다.

성격: [v197] `monthly-stats.yml` 이 **원자료 연장 직후 매월 돌린다** (v164 는 「연 1회 수동」이었으나
      원자료 연장이 자동인데 파생물만 수동이면 조용히 낡는다 — v171 성과표와 같은 유형).
      같은 원자료면 산출도 같아 커밋 소음은 없다(1초). 로컬 수동 실행도 그대로 된다.

엔진: `hist_defensive.build('chain')` 의 `ddv` 를 **읽기 전용으로** 쓴다.
      엔진 파일(hist_*.py)은 수정하지 않는다.

실행:  python research/emit_dd_distribution.py
"""
import io
import json
import os
import sys

# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 (저장소 관행 3줄) -------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402
import hist_defensive as DF              # noqa: E402  (읽기 전용)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

OUT = os.path.join(_ROOT, 'data', 'dd_percentile.json')


def main():
    D = DF.build('chain')
    dd = np.asarray(D['ddv'], float) * 100.0        # % 단위 (엔진은 소수)
    idx = pd.DatetimeIndex(D['idx'])
    ok = np.isfinite(dd)
    dd = dd[ok]
    n = int(dd.size)
    if n < 1000:
        print('[dd] 표본이 너무 적다(%d) — 쓰지 않는다' % n, file=sys.stderr)
        return 1

    # 1~99 백분위 경계값. 오름차순(= 깊은 낙폭이 앞)
    ps = list(range(1, 100))
    edges = [round(float(np.percentile(dd, p)), 4) for p in ps]

    doc = {
        'note': '252거래일 고점 대비 낙폭(%)의 백분위 경계. 표시 전용 — 판정에 쓰지 않는다',
        'source': "hist_defensive.build('chain')['ddv']",
        'n': n,
        'start': str(idx[ok][0].date()),
        'end': str(idx[ok][-1].date()),
        'percentiles': ps,
        'edges': edges,          # edges[i] = (i+1) 백분위 값
        'min': round(float(dd.min()), 4),
        'max': round(float(dd.max()), 4),
        'median': round(float(np.median(dd)), 4),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')

    print('[dd] %s ~ %s · %d일' % (doc['start'], doc['end'], n))
    print('     최악 %.2f%% · 중앙 %.2f%% · 최대 %.2f%%' % (doc['min'], doc['median'], doc['max']))
    for p in (1, 5, 10, 25, 50, 75, 90, 99):
        print('     p%-2d = %8.2f%%' % (p, edges[p - 1]))
    # 상식 검산 — 화면이 쓸 방향(깊을수록 상위 몇 %)이 맞는지 여기서 확인해 둔다
    for probe in (-60.0, -16.0, -3.83, 0.0):
        deeper = float((dd <= probe).mean() * 100)
        print('     낙폭 %7.2f%% → 이보다 깊었던 날 %5.2f%%' % (probe, deeper))
    return 0


if __name__ == '__main__':
    sys.exit(main())
