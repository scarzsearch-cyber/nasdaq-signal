# -*- coding: utf-8 -*-
"""
[v88 부록2] 보유기간별 원금손실 확률 — "믿고 따라도 되는가"의 지평 조건부 답

소유자 질문 (2026-08-30): "T4 확정 없이도, B 를 믿고 따라도 손해는 안 본다는
확신이 있는가?" — 답은 무조건이 아니라 **보유기간 조건부**다. 이 스크립트가
그 표를 재현한다 (54.5년 · 달러 · 현행 방어 40/40/20 · 편도 0.2% · lag=1 · 세전).

주의: 표본이 말하는 확률이지 보증이 아니다 (전제: 나스닥 장기 우상향 — I10 감시).
원화·세후 규약에서는 수치가 다르되 구조(지평이 길수록 손실 확률 소멸)는 같다.
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from axis_lib import sim
from axis_t4_shadow import build
from axis_defmix import materials, mix_monthly_from

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def calendar_month_starts(idx):
    """각 달의 첫 거래행. 21거래일 보폭은 달을 중복·누락하므로 쓰지 않는다."""
    months = pd.DatetimeIndex(idx).to_period('M')
    return np.flatnonzero(np.r_[True, months[1:] != months[:-1]])


def main():
    D, wT, wB, votes, rv = build('tbill')
    comp = materials(D)
    D = dict(D)
    D['schdr'] = mix_monthly_from(
        {k: comp[k] for k in ('div', 'ust5', 'gold')},
        {'div': .4, 'ust5': .4, 'gold': .2}, D['idx'])
    c, _ = sim(D, wB, cost=0.002)
    lg = np.log(c.values)
    n = len(lg)
    # 최소 반례: 1월 거래일 수가 21이 아니어도 2월을 정확히 한 번만 뽑는다.
    probe = pd.DatetimeIndex(['2000-01-03', '2000-01-31', '2000-02-01', '2000-03-02'])
    assert calendar_month_starts(probe).tolist() == [0, 2, 3]
    mstart = calendar_month_starts(D['idx'])
    print('전략 B(−16/−16·방어40/40/20) 보유기간별 롤링 창 — 달러 · 0.2% · 세전 (각 달 첫 거래일 시작)')
    print('%-6s %6s %10s %10s %10s %10s' % ('기간', '창수', '원금손실%', '중앙배수', '5분위', '최악'))
    for y in (1, 3, 5, 10, 15, 20):
        L = 252 * y
        st = mstart[mstart + L <= n]
        base = np.zeros(len(st), dtype=float)
        nz = st > 0
        base[nz] = lg[st[nz] - 1]
        f = np.exp(lg[st + L - 1] - base)
        print('%-5d년 %6d %9.1f%% %9.1f배 %9.1f배 %9.2f배'
              % (y, len(f), (f < 1).mean() * 100, np.median(f),
                 np.percentile(f, 5), f.min()))


if __name__ == '__main__':
    main()
