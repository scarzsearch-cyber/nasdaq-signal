# -*- coding: utf-8 -*-
"""
[하이브리드 탐색] VR(밸류리밸런싱) 밴드 리밸런싱을 리스크온 구간에 얹으면 이득인가

배경 (대화 중 사용자 요청 — quantstack.app 의 무한매수법/VR 5.0 과 이 전략을 비교한 뒤,
"장점만 섞을 수 있는가"를 검증해 달라는 요청):

  기존 채택안: QQQ 252일 낙폭 <= -16% 면 방어자산 100%, > -16% 면 QLD(2배) 100%.
  리스크온 구간은 항상 이진(0%/100%)이고 그 안에서 아무 조정도 하지 않는다.

  VR 5.0 은 "목표평가액 V" 를 공식으로 그려두고 평가금이 V 대비 ±15% 벗어나면
  리밸런싱한다(넘으면 팔아 Pool 에 편입, 못미치면 Pool 로 되사되 한도 이내).
  G 가 클수록 V 성장이 느려지고 평균 현금비중이 커진다(quantstack 실측: G=/10 -> 13.2%,
  G=/40 -> 31.8%).

하이브리드 가설: 리스크온 구간에서는 지금처럼 100% 고정 노출로 두지 말고, VR 식 밴드
리밸런싱으로 Pool 을 일부 들고 있다가 그 Pool 로 눌림목에 되사고 급등엔 덜어내면
(1) 변동성/MDD 가 줄고 (2) 특히 이 전략의 최대 약점인 톱니장(1987-10~1988-12 형,
전략_v20.md §6) 에서 이진 스위치보다 덜 다친다 — 는 것.

경계할 것 (v22 §반복 결론): "낙폭에 맞춰 사고파는 행위(QLD Dip Alert 형)의 기여는
실측상 정확히 0" 이었다. VR 밴드도 본질은 "떨어지면 사고 오르면 판다"라 같은 함정에
걸릴 수 있다. 직관으로 "장점만 남는다"고 가정하지 않고 반드시 실측으로 확인한다.

[구현 규약]
  - 위기 진입/탈출(방어자산 전환)은 기존 채택안(B, -16/-16)과 완전히 동일한 로직.
    다른 것은 오직 "리스크온 상태에서 무엇을 하는가" 뿐이다.
  - VR 사이클은 10거래일(약 2주, 원 방법론과 동일 주기)마다 판정.
  - 리스크온 재진입 시 V 를 그 시점 평가금으로 리셋하고 Pool=0 에서 다시 시작한다
    (원 방법론의 "사이클 시작"과 동일한 취급 — 낙폭 신호가 방어 전환에 이미 쓰이므로
    도피 국면을 VR 의 "한 사이클"로 보는 것이 자연스럽다).
  - 신호는 전부 전일 종가까지의 정보만 쓴다(lag=1). 판정일 당일 체결이 아니라
    "판정 다음날 체결"을 실행 규약으로 삼는다 — reentry_lib.run() 의 lag=1 과 동일 정신.
  - 비용은 거래된 금액의 비율(turnover)에 COST 를 곱해 차감한다. 국면전환은 turnover=1.0
    (전량 이동)으로, 밴드 리밸런싱은 실제 거래액/총자산 비율로 계산한다.
  - Pool 은 유휴 현금이 아니라 방어자산과 같은 수익률(schdr)을 번다고 가정한다
    (실제로는 그보다 낮을 수 있음 — 하이브리드에 유리한 방향의 가정이므로 결과가
    나쁘면 그대로 신뢰하고, 좋으면 이 가정부터 의심해야 한다).

실행:  python axis_vrhybrid.py
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys

try:                       # [코드리뷰 2026-09-04] 이 파일은 콘솔에 표를 찍는다.
    _sys.stdout.reconfigure(encoding='utf-8')   # cp949 콘솔에서 em-dash 로 죽지 않게
except Exception:
    pass
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

import reentry_lib as R
import hist_data as H

COST = 0.001


# --------------------------------------------------------------- 엔진
def vr_hybrid(D, G=10, band=0.15, pool_cap=0.5, cycle=10,
              enter=-0.16, exit_=-0.16, cost=COST, start=None, end=None):
    """
    리스크온 구간엔 VR 밴드 리밸런싱, 도피 구간엔 기존 이진 스위치를 얹은 하이브리드.
    반환: (정규화곡선, QLD비중경로, 일별회전율)
    """
    idx, ddv, qldr, schdr = D['idx'], D['ddv'], D['qldr'], D['schdr']
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    m = hi - lo

    regime = 'ON'
    Q, P, Dcash = 1.0, 0.0, 0.0
    V = 1.0
    cyc = 0
    pending = None

    curve = np.empty(m)
    wpath = np.empty(m)
    turns = np.empty(m)

    for j, i in enumerate(range(lo, hi)):
        turnover = 0.0

        if pending == 'to_off':
            tot = Q + P
            turnover = 1.0
            tot *= (1 - cost * turnover)
            Dcash, Q, P = tot, 0.0, 0.0
            regime = 'OFF'
            pending = None
        elif pending == 'to_on':
            turnover = 1.0
            v = Dcash * (1 - cost * turnover)
            Q, P, V, cyc, Dcash = v, 0.0, v, 0, 0.0
            regime = 'ON'
            pending = None
        elif isinstance(pending, tuple):
            target_Q = pending[1]
            tot = Q + P
            traded = abs(target_Q - Q)
            turnover = (traded / tot) if tot > 0 else 0.0
            tot = tot * (1 - cost * turnover)
            frac = (target_Q / (Q + P)) if (Q + P) > 0 else 0.0
            frac = min(max(frac, 0.0), 1.0)
            Q, P = tot * frac, tot * (1 - frac)
            pending = None

        if regime == 'ON':
            Q *= (1 + qldr[i])
            P *= (1 + schdr[i])
            total = Q + P
        else:
            Dcash *= (1 + schdr[i])
            total = Dcash

        curve[j] = total
        wpath[j] = (Q / total) if (regime == 'ON' and total > 0) else 0.0
        turns[j] = turnover
        cyc += 1

        d = ddv[i]
        if regime == 'ON' and d <= enter:
            pending = 'to_off'
        elif regime == 'OFF' and d > exit_:
            pending = 'to_on'
        elif regime == 'ON' and cyc >= cycle:
            Vn = V + P / G
            upper, lower = Vn * (1 + band), Vn * (1 - band)
            if total > upper:
                pending = ('reb', Vn)
            elif total < lower:
                need = Vn - total
                buy = min(need, P * pool_cap)
                pending = ('reb', Q + buy)
            V = Vn
            cyc = 0

    curve = pd.Series(curve, index=idx[lo:hi])
    curve = curve / curve.iloc[0]
    return curve, pd.Series(wpath, index=idx[lo:hi]), turns


def baseline(D, enter=-0.16, exit_=-0.16, cost=COST, start=None, end=None):
    """기존 채택안(B, -16/-16) — 리스크온 100% 고정."""
    ladder = [(('dd', exit_), 1.0, 0)]
    c, w, t = R.run(D, ladder, enter=enter, cost=cost, start=start, end=end)
    return c, w, t


# --------------------------------------------------------------- 검증
def check():
    """VR 사이클이 한 번도 발동하지 않는 조건(cycle이 구간 길이보다 김 + 낙폭신호도
    안 걸리는 짧은 순구간)에서 하이브리드가 baseline 과 기계정밀도로 일치하는지 확인."""
    D = R.build()
    s, e = '2003-06-01', '2004-06-01'          # 이 구간엔 -16% 낙폭 없음(순수 상승)
    h, w, t = vr_hybrid(D, G=10, band=0.15, pool_cap=0.5, cycle=100000, start=s, end=e)
    b2, _, _ = baseline(D, start=s, end=e)
    err = abs(h.iloc[-1] / b2.iloc[-1] - 1)
    print('검산  cycle=100000(사실상 리밸런싱 없음)  hybrid=%.6f  baseline=%.6f  오차=%.2e'
          % (h.iloc[-1], b2.iloc[-1], err))
    assert err < 1e-9, '검산 실패 — 거래가 없는 조건에서도 baseline 과 어긋난다'
    print('검산 통과\n')


# --------------------------------------------------------------- 1) 메인 그리드
def main_grid(D, label, start=None, end=None):
    ref_qqq = pd.Series(np.cumprod(1 + np.nan_to_num(D['px'].pct_change().values)), index=D['idx'])
    b, bw, bt = baseline(D, start=start, end=end)
    rows = []
    m = R.met(b)
    bsw = int((np.abs(np.diff(bw.values)) > 1e-9).sum())
    rows.append(dict(설정='기존안(이진 100%)', 최종배수=m['final'], CAGR=m['cagr'] * 100,
                     MDD=m['mdd'] * 100, Calmar=m['calmar'], Sharpe=m['sharpe'], 전환=bsw))
    for G in (10, 15, 20, 30, 40):
        for band in (0.10, 0.15, 0.20):
            c, w, t = vr_hybrid(D, G=G, band=band, start=start, end=end)
            mm = R.met(c)
            sw = int((t > 1e-9).sum())
            rows.append(dict(설정='VR하이브리드 G=/%d band=%.0f%%' % (G, band * 100),
                             최종배수=mm['final'], CAGR=mm['cagr'] * 100, MDD=mm['mdd'] * 100,
                             Calmar=mm['calmar'], Sharpe=mm['sharpe'], 전환=sw))
    df = pd.DataFrame(rows)
    print('\n===== 1) 메인 그리드 — %s =====' % label)
    print(df.to_string(index=False, float_format=lambda x: format(x, ',.2f')))
    return df


# --------------------------------------------------------------- 2) 이웃평균 (평지 확인)
def neighbor_avg(D, label, start=None, end=None):
    Gs = (10, 15, 20, 25, 30, 35, 40)
    bands = (0.10, 0.125, 0.15, 0.175, 0.20)
    grid = np.empty((len(Gs), len(bands)))
    for gi, G in enumerate(Gs):
        for bi, band in enumerate(bands):
            c, _, _ = vr_hybrid(D, G=G, band=band, start=start, end=end)
            grid[gi, bi] = R.met(c)['final']
    print('\n===== 2) G x 밴드폭 이웃평균 확인 — %s (셀=최종배수) =====' % label)
    hdr = '%-8s' + ''.join('%10.1f%%' for _ in bands)
    print(hdr % (('G\\밴드',) + tuple(b * 100 for b in bands)))
    for gi, G in enumerate(Gs):
        print(('/%-6d' + ''.join('%11.2f' for _ in bands)) % ((G,) + tuple(grid[gi])))
    # 3x3 이웃평균으로 스파이크 여부 확인 (중앙값 근방)
    smooth = grid.copy()
    for gi in range(1, len(Gs) - 1):
        for bi in range(1, len(bands) - 1):
            smooth[gi, bi] = grid[gi - 1:gi + 2, bi - 1:bi + 2].mean()
    spike = np.abs(grid[1:-1, 1:-1] - smooth[1:-1, 1:-1]) / smooth[1:-1, 1:-1]
    print('최대 원값-이웃평균 괴리 = %.1f%%  (20%% 넘으면 스파이크 의심)' % (spike.max() * 100))
    return grid


# --------------------------------------------------------------- 3) 비용 민감도
def cost_gate(D, G=15, band=0.15, label=''):
    print('\n===== 3) 검증관문 : 편도 거래비용 민감도 — %s (G=/%d, band=%.0f%%) =====' % (label, G, band * 100))
    print('%-14s %12s %12s %12s %12s %12s' % ('', '0.05%', '0.10%', '0.20%', '0.35%', '0.50%'))
    costs = (0.0005, 0.001, 0.002, 0.0035, 0.005)
    hv = [vr_hybrid(D, G=G, band=band, cost=c)[0].iloc[-1] for c in costs]
    bv = [baseline(D, cost=c)[0].iloc[-1] for c in costs]
    print(('%-14s' + '%12s' * 5) % ('하이브리드', *[format(x, ',.1f') for x in hv]))
    print(('%-14s' + '%12s' * 5) % ('기존안', *[format(x, ',.1f') for x in bv]))
    print(('%-14s' + '%12s' * 5) % ('비율', *['%.3f' % (h / b) for h, b in zip(hv, bv)]))


# --------------------------------------------------------------- 4) 하위구간 안정성
SEGS = [('1972-1985', '1972-02-07', '1985-12-31'),
        ('1986-1999', '1986-01-01', '1999-12-31'),
        ('2000-2009', '2000-01-03', '2009-12-31'),
        ('2010-2026', '2010-01-01', '2026-08-24')]

CRISES = {'닷컴 00-02': ('2000-03-10', '2002-10-09'),
          'GFC 07-09': ('2007-10-31', '2009-03-09'),
          '87블랙먼데이 톱니': ('1987-08-25', '1988-12-31'),
          '73-74오일': ('1973-01-11', '1974-10-03'),
          '코로나20': ('2020-02-19', '2020-03-23'),
          '2022베어': ('2022-01-03', '2022-12-31')}


def seg_stability(D, G=15, band=0.15):
    print('\n===== 4) 하위구간 안정성 (1972-2026 확장데이터, G=/%d band=%.0f%%) =====' % (G, band * 100))
    rows = []
    for nm, s, e in SEGS:
        h, _, _ = vr_hybrid(D, G=G, band=band, start=s, end=e)
        b, _, _ = baseline(D, start=s, end=e)
        mh, mb = R.met(h), R.met(b)
        rows.append(dict(구간=nm, 하이브리드배수=mh['final'], 기존안배수=mb['final'],
                         비율=mh['final'] / mb['final'],
                         하이브리드MDD=mh['mdd'] * 100, 기존안MDD=mb['mdd'] * 100))
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda x: format(x, ',.3f')))
    return df


def crisis_table(D, G=15, band=0.15):
    print('\n===== 5) 위기·톱니 구간별 낙폭 비교 (G=/%d band=%.0f%%) — [핵심] 87블랙먼데이가 가설의 시험대 =====' % (G, band * 100))
    rows = []
    for nm, (s, e) in CRISES.items():
        h, _, _ = vr_hybrid(D, G=G, band=band, start=s, end=e)
        b, _, _ = baseline(D, start=s, end=e)
        mh, mb = R.met(h), R.met(b)
        rows.append(dict(구간=nm, 하이브리드수익=(h.iloc[-1] - 1) * 100, 기존안수익=(b.iloc[-1] - 1) * 100,
                         하이브리드MDD=mh['mdd'] * 100, 기존안MDD=mb['mdd'] * 100,
                         MDD개선폭=(mh['mdd'] - mb['mdd']) * 100))
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda x: format(x, ',.2f')))
    return df


# --------------------------------------------------------------- 5) 롤링윈도우 승률
def rolling_win(D, G=15, band=0.15):
    print('\n===== 6) 롤링윈도우 승률 (하이브리드 vs 기존안, 1972-2026) =====')
    h, _, _ = vr_hybrid(D, G=G, band=band)
    b, _, _ = baseline(D)
    rs = R.rolling_stats(h, b)
    for w, v in rs.items():
        print('%2d년창(n=%3d)  하이브리드 승률=%5.1f%%  초과CAGR중앙값=%+6.2f%%p  최악초과=%+6.2f%%p'
              % (w, v['n'], v['win'], v['ex_med'], v['ex_worst']))


if __name__ == '__main__':
    check()

    D26 = R.build()
    main_grid(D26, '2000-2026 (26.6년)')
    neighbor_avg(D26, '2000-2026')
    cost_gate(D26, label='2000-2026')

    D54 = H.build_ext()
    seg_stability(D54)
    crisis_table(D54)
    rolling_win(D54)
