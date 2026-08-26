# -*- coding: utf-8 -*-
"""
한국 실전 맞춤 ③ — 세금·계좌를 반영한 A(-16/-11) vs B(-16/-16)

[왜 이게 필요한가]
지금까지의 모든 비교는 세전이었다. 그런데 국내 상장 해외 ETF는 **매도할 때마다**
매매차익에 배당소득세가 원천징수되고, 배당소득은 **손실 통산이 안 된다**.
즉 전환이 잦을수록(=B) 실현과세가 늘고, 방어자산 체류가 길수록(=A) 분배금 과세가 는다.
두 방향이 상쇄되므로 부호를 계산으로 확인해야 한다.

[모형]  ※ 세율·과세방식은 사용자가 반드시 최신 규정으로 확인할 것. 아래는 가정이다.
  - 전량 전환이므로 포트폴리오 = 단일 포지션. 매도 시 (매도평가액 - 취득원가)가 양수면
    그 차익에 rate 를 원천징수하고, 음수면 0 (손실 이월·통산 없음).
  - 재매수 시 취득원가는 세후 잔액으로 리셋된다.
  - 분배금: 사용하는 가격은 수정주가(분배금 재투자)라 분배금이 이미 섞여 있다.
    방어자산 보유 기간에만 연 div_yield 만큼 분배가 났다고 보고 그 세액을 일할로 뺀다.
    레버리지(합성) 상품은 분배가 사실상 없어 0 으로 둔다.
  - 과세이연 계좌(연금저축/IRP/ISA)는 rate=0 과 같다(인출 시 과세는 별도).

[한계]
  - 실제로는 '매매차익'과 '과표기준가 증가분' 중 작은 쪽에 과세된다. 합성 레버리지는
    과표기준가가 가격과 어긋날 수 있어 실제 세부담은 이 모형보다 낮을 수 있다.
    즉 이 계산은 B 에게 보수적(불리)이다.
  - 금융소득종합과세(연 2천만원 초과 누진)는 rate 민감도로만 다룬다.
"""
import numpy as np, pandas as pd
import hist_korea as K, hist_krfinal as KF
from reentry_lib import met

RATE = 0.154            # 배당소득세 (지방소득세 포함)
DIV_YIELD = 0.030       # 방어자산(TIGER 미국배당다우존스) 연 분배율 가정
COST, SLIP = 0.001, 0.001


def run_tax(D, idx, qr, sr, S, krdays, rate=RATE, div_yield=0.0,
            offset=False, start=KF.ST):
    """K.run_kr 과 같은 체결 규칙 + 매도 시 실현과세 + 방어자산 분배금 과세."""
    ddv = D['ddv']
    n = len(idx)
    lo = idx.searchsorted(pd.Timestamp(start))
    enter, exit_ = S['enter'], S['ladder'][0][0][1]

    w = np.full(n, np.nan); cur = 1.0
    for i in range(lo, n):
        d = ddv[i]
        if cur >= 1.0:
            if d <= enter: cur = 0.0
        else:
            if d <= enter: cur = 0.0
            elif d > exit_: cur = 1.0
        w[i] = cur

    em = K.kr_exec_map(idx, krdays)
    pos = np.full(n, np.nan); pos[lo] = 1.0
    for i in range(lo, n):
        j = em[i]
        if lo <= j < n: pos[j] = w[i]
    pos[lo] = 1.0
    pos = pd.Series(pos).ffill().values

    p = pos[lo:]
    rq, rs = qr[lo:], sr[lo:]
    r = np.nan_to_num(p * rq + (1 - p) * rs); r[0] = 0.0

    v = 1.0; basis = 1.0; carry = 0.0
    out = np.empty(len(p)); tax_paid = 0.0; n_sell = 0
    dtax = div_yield * rate / 252.0
    for i in range(len(p)):
        v *= (1 + r[i])
        if p[i] < 0.5:                       # 방어자산 보유 중 분배금 과세 (일할)
            v *= (1 - dtax)
        if i > 0 and p[i] != p[i - 1]:       # 전환 = 전량 매도 후 재매수
            v *= (1 - (COST + SLIP))
            gain = v - basis
            if offset:
                gain += carry
                if gain < 0: carry, gain = gain, 0.0
                else: carry = 0.0
            else:
                gain = max(0.0, gain)
            t = gain * rate
            v -= t; tax_paid += t; basis = v; n_sell += 1
        out[i] = v
    return pd.Series(out, index=idx[lo:]), tax_paid, n_sell


def table():
    D, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    krd = K.kr_caldays()
    from hyst_core import A, B
    rows = []
    cases = [
        ('과세이연 (연금저축·IRP·ISA)', 0.0, 0.0, False),
        ('일반계좌 15.4% (손실통산 X)', RATE, 0.0, False),
        ('  + 방어자산 분배금 과세', RATE, DIV_YIELD, False),
        ('  + 손실통산 허용시(참고)', RATE, DIV_YIELD, True),
        ('종합과세 구간 22% 가정', 0.22, DIV_YIELD, False),
    ]
    for lab, rate, dy, off in cases:
        for S, nm in ((B, '−16/−16'), (A, '−16/−11')):
            c, tax, ns = run_tax(D, idx, lev2, dfk, S, krd, rate=rate, div_yield=dy, offset=off)
            m = met(c)
            rows.append(dict(case=lab if S is B else '', 전략=nm, 최종배수=m['final'],
                             CAGR=m['cagr'] * 100, MDD=m['mdd'] * 100, Calmar=m['calmar'],
                             Sortino=m['sortino'], 전환=ns))
    df = pd.DataFrame(rows)
    print('원화 · 환노출2배 · 한국거래일 체결 · 슬리피지 0.1%  (1997-01 ~ 2026-08)')
    print(df.to_string(index=False, float_format=lambda x: f'{x:,.3f}'))
    return df


if __name__ == '__main__':
    df = table()
    print('\n[B/A 최종배수 비율]')
    f = df['최종배수'].values
    for i in range(0, len(f), 2):
        print('  %-28s  B/A = %+6.1f%%' % (df['case'].values[i], (f[i] / f[i + 1] - 1) * 100))
