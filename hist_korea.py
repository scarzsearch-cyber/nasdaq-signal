# -*- coding: utf-8 -*-
"""
과제 ③ — 한국 실전 운용 (TIGER ETF / 원화 / 다음 한국 거래일 시가 체결)

[체결 시각 정합 — 이 연구의 핵심 확인 사항]
  미국 종가 16:00 ET = 한국시간 익일 05:00~06:00.
  한국 개장 09:00 KST 는 그로부터 3시간 뒤 → 신호를 알고 나서 거래한다.
  미국 당일(t+1) 정규장은 한국시간 t+1일 22:30 에 시작하므로,
  한국 t+1일 09:00 에 잡은 포지션은 '미국 t+1 세션 수익률'을 온전히 먹는다.
  reentry_lib 의 pos = w.shift(1) 이 바로 그 정의다.
  => 한국 시가 체결 규칙은 기존 백테스트 규약과 경제적으로 동일하다.
     오히려 미국 투자자가 종가 동시호가에 체결해야 하는 것보다 현실적이다.

[한국 고유 마찰 — 이번에 새로 반영]
  (1) 한국 휴장일: t+1 이 한국 휴장이면 실제 체결은 그 다음 한국 거래일 시가.
      그 사이의 미국 세션 수익률을 놓친다(= 그 전환만 lag 2). KOSPI 실거래일로 정확히 매핑.
  (2) 원달러: TIGER 3종 모두 환노출(Unhedged) → 원화 수익률 = (1+자산)(1+환율)-1
  (3) 시초가 갭 + 스프레드: 제미나이.md 규약대로 편도 0.1% 슬리피지 강제 주입
"""
import warnings

import numpy as np, pandas as pd
import hist_data as H, hist_defensive as DF
from reentry_lib import met
from hyst_core import A, B, switches

FX = 'data/hist/fred_DEXKOUS.csv'
KOSPI = 'data/hist/kr__5EKS11.csv'
TIGER = {'nasdaq100': ('133690.KS', 'data/hist/kr_133690_KS.csv', 'TIGER 미국나스닥100'),
         'lev':       ('418660.KS', 'data/hist/kr_418660_KS.csv', 'TIGER 미국나스닥100레버리지(합성)'),
         'div':       ('458730.KS', 'data/hist/kr_458730_KS.csv', 'TIGER 미국배당다우존스')}


def _kr(path):
    d = pd.read_csv(path, parse_dates=['Date'])
    return d.set_index('Date').sort_index()


def fx(idx):
    """USD/KRW 일간 (원/달러). idx 위로 ffill.

    [코드리뷰 2026-09-04] 원자료(DEXKOUS)는 1981-04 부터다. 그 이전은 ffill 로도
    채울 수 없어 NaN 으로 남고, 쓰는 쪽이 pct_change().fillna(0.0) 을 걸면
    '환율이 하루도 안 움직인 세계'가 되어 환노출 2배 모형의 전제가 조용히 무력화된다.
    지금 호출부는 전부 1997 이후 또는 lo=FXS 로 잘라 쓰지만, 그 안전이 호출부
    규율에만 걸려 있으므로 함수가 직접 말하게 한다. (값·동작은 종전과 같다.)
    """
    f = H._fred(FX, 'DEXKOUS')
    out = f.reindex(idx.union(f.index)).ffill().reindex(idx)
    miss = int(out.isna().sum())
    if miss:
        warnings.warn('hist_korea.fx: 환율 원자료가 %s 부터라 그 이전 %d일(%.1f%%)은 값이 없다 - '
                      '그 구간을 포함해 원화 수치를 내지 마라(환변동 0%% 으로 계산된다).'
                      % (str(f.index[0].date()), miss, 100.0 * miss / len(out)),
                      RuntimeWarning, stacklevel=2)
    return out


def kr_caldays():
    return pd.DatetimeIndex(_kr(KOSPI).index)


def kr_exec_map(idx, krdays):
    """
    미국 신호일 i -> 그 신호가 실제로 적용되기 시작하는 미국 세션 인덱스.
    = 첫 '한국 거래일 > idx[i]' 이후의 첫 미국 거래일.
    """
    n = len(idx); out = np.full(n, n, dtype=int)
    kv = krdays.values
    for i in range(n):
        k = np.searchsorted(kv, idx[i].to_datetime64(), side='right')
        if k >= len(kv):
            break
        out[i] = idx.searchsorted(pd.Timestamp(kv[k]), side='left')
    return out


def run_kr(D, S, cost=0.001, slip=0.0, start=None, end=None,
           krdays=None, use_fx=False, fxs=None, w0=1.0):
    """reentry_lib.run 과 동일하되 체결 인덱스를 한국 거래일 규칙으로 대체."""
    ddv, qldr, schdr, idx = D['ddv'], D['qldr'], D['schdr'], D['idx']
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    enter, exit_ = S['enter'], S['ladder'][0][0][1]

    w = np.full(n, np.nan); cur = w0
    for i in range(lo, hi):
        d = ddv[i]
        if cur >= 1.0:
            if d <= enter: cur = 0.0
        else:
            if d <= enter: cur = 0.0
            elif d > exit_: cur = 1.0
        w[i] = cur

    pos = np.full(n, np.nan)
    if krdays is None:
        pos[lo + 1:hi] = w[lo:hi - 1]; pos[lo] = w0
    else:
        em = kr_exec_map(idx, krdays)
        pos[lo] = w0
        for i in range(lo, hi):
            j = em[i]
            if lo <= j < hi:
                pos[j] = w[i]
        pos[lo] = w0
        pos = pd.Series(pos).ffill().values
    seg = slice(lo, hi)
    p = pos[seg]
    r = p * qldr[seg] + (1 - p) * schdr[seg]
    if use_fx:
        fr = fxs.pct_change().fillna(0.0).values[seg]
        r = (1 + r) * (1 + fr) - 1
    r = np.nan_to_num(r); r[0] = 0.0
    turn = np.abs(np.diff(p, prepend=p[0]))
    g = (1 + r) * (1 - (cost + slip) * turn)
    return pd.Series(np.cumprod(g), index=idx[seg]), pd.Series(w[seg], index=idx[seg]), turn


def hdr(t):
    print('\n===== %s =====' % t)
    print('%-42s %-11s %12s %7s %8s %7s %6s' %
          ('시나리오', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar', '전환'))


def row(lab, S, c, turn):
    m = met(c)
    print('%-42s %-11s %12s %6.2f%% %7.2f%% %7.2f %6d' %
          (lab, S['name'], f"{m['final']:,.1f}", m['cagr'] * 100, m['mdd'] * 100,
           m['calmar'], int(np.sum(turn > 0))))
    return m


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    D = DF.build('cash2')                 # 기존 기준 규약
    Dc = DF.build('chain')                # 자율규약2 배당체인
    idx = D['idx']
    krd = kr_caldays()
    fxs = fx(idx)
    ST = '1997-01-02'                     # KOSPI 달력 시작 이후

    # ---------- 1) 체결 정합 검증
    em = kr_exec_map(idx, krd)
    base = np.arange(len(idx)) + 1
    sub = idx.searchsorted(pd.Timestamp(ST))
    diff = em[sub:-1] - base[sub:-1]
    print('== 한국 거래일 체결 매핑 (1997-01 ~) ==')
    print('미국 신호일 %d 일 중' % len(diff))
    for k in sorted(set(diff.tolist())):
        print('   체결지연 %+d 거래일 : %5d 일 (%.2f%%)' % (k, int((diff == k).sum()),
                                                     (diff == k).mean() * 100))
    print('  * 0 = 기존 백테스트(pos=w.shift(1))와 완전 동일')

    # 실제 전환일이 한국 휴장에 걸린 횟수
    for S in (A, B):
        c0, w0s, t0 = run_kr(D, S, start=ST)
        sw = [d for d, a, b in switches(w0s)]
        n_del = sum(1 for d in sw if em[idx.searchsorted(d)] - idx.searchsorted(d) != 1)
        print('  %s : 전환신호 %d 회 중 한국휴장으로 하루 밀린 건 %d 회 (%.1f%%)'
              % (S['name'], len(sw), n_del, 100 * n_del / max(len(sw), 1)))

    # ---------- 2) 달러 기준 vs 한국 체결 vs 원화 기준
    for lab, DD in [('방어자산=연2%현금(기존)', D), ('방어자산=배당체인(자율2)', Dc)]:
        hdr('%s   1997-01 ~ 2026-08' % lab)
        for S in (A, B):
            c, w, t = run_kr(DD, S, start=ST); row('① 미국ETF·달러 (기존 규약)', S, c, t)
        for S in (A, B):
            c, w, t = run_kr(DD, S, start=ST, krdays=krd)
            row('② +한국거래일 시가체결 매핑', S, c, t)
        for S in (A, B):
            c, w, t = run_kr(DD, S, start=ST, krdays=krd, slip=0.001)
            row('③ +편도 0.1% 슬리피지 강제', S, c, t)
        for S in (A, B):
            c, w, t = run_kr(DD, S, start=ST, krdays=krd, slip=0.001, use_fx=True, fxs=fxs)
            row('④ +원화환산(환노출) = 실전 근사', S, c, t)
        cq = pd.Series(np.cumprod(1 + DD['qldr'][idx.searchsorted(pd.Timestamp(ST)):]),
                       index=idx[idx.searchsorted(pd.Timestamp(ST)):])
        frr = fxs.pct_change().fillna(0).values[idx.searchsorted(pd.Timestamp(ST)):]
        cqk = pd.Series(np.cumprod((1 + DD['qldr'][idx.searchsorted(pd.Timestamp(ST)):]) * (1 + frr)),
                        index=cq.index)
        for nm, cc in [('QLD 계속보유 (달러)', cq), ('QLD 계속보유 (원화)', cqk)]:
            m = met(cc)
            print('%-42s %-11s %12s %6.2f%% %7.2f%% %7.2f' %
                  (nm, '-', f"{m['final']:,.1f}", m['cagr'] * 100, m['mdd'] * 100, m['calmar']))

    # ---------- 3) 환율 자체의 위기 완충 효과
    print('\n== 위기 구간 원달러 변동 (환노출이 원화 MDD를 얼마나 줄였나) ==')
    CR = [('1997 IMF', '1997-07-01', '1998-06-30'), ('2000-02 닷컴', '2000-03-10', '2002-10-09'),
          ('2007-09 금융위기', '2007-10-31', '2009-03-09'), ('2020 코로나', '2020-02-19', '2020-03-23'),
          ('2022 인플레', '2021-11-19', '2022-12-28')]
    ql = pd.Series(D['qldr'], index=idx)
    for nm, s0, s1 in CR:
        f0, f1 = fxs.loc[:s0].iloc[-1], fxs.loc[:s1].iloc[-1]
        qd = np.prod(1 + ql.loc[s0:s1]) - 1
        qk = (1 + qd) * (f1 / f0) - 1
        print('%-14s 원달러 %6.0f -> %6.0f (%+6.1f%%)   QLD 달러 %+7.1f%%  원화 %+7.1f%%  완충 %+5.1f%%p'
              % (nm, f0, f1, (f1 / f0 - 1) * 100, qd * 100, qk * 100, (qk - qd) * 100))
