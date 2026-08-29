# -*- coding: utf-8 -*-
"""
[v88 부록2] 보유기간별 원금손실 확률 — "믿고 따라도 되는가"의 지평 조건부 답

소유자 질문 (2026-08-30): "T4 확정 없이도, B 를 믿고 따라도 손해는 안 본다는
확신이 있는가?" — 답은 무조건이 아니라 **보유기간 조건부**다. 이 스크립트가
그 표를 재현한다 (54.5년 · 달러 · T-bill 방어 · 편도 0.2% · lag=1 · 세전).

주의: 표본이 말하는 확률이지 보증이 아니다 (전제: 나스닥 장기 우상향 — I10 감시).
원화·세후 규약에서는 수치가 다르되 구조(지평이 길수록 손실 확률 소멸)는 같다.
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np

from axis_lib import sim
from axis_t4_shadow import build

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def main():
    D, wT, wB, votes, rv = build('tbill')
    c, _ = sim(D, wB, cost=0.002)
    lg = np.log(c.values)
    n = len(lg)
    print('B(−16/−16) 보유기간별 롤링 창 — 달러 · T-bill · 0.2% · 세전 (월 단위 시작)')
    print('%-6s %6s %10s %10s %10s %10s' % ('기간', '창수', '원금손실%', '중앙배수', '5분위', '최악'))
    for y in (1, 3, 5, 10, 15, 20):
        L = 252 * y
        st = np.arange(1, n - L, 21)
        f = np.exp(lg[st + L - 1] - lg[st - 1])
        print('%-5d년 %6d %9.1f%% %9.1f배 %9.1f배 %9.2f배'
              % (y, len(f), (f < 1).mean() * 100, np.median(f),
                 np.percentile(f, 5), f.min()))


if __name__ == '__main__':
    main()
