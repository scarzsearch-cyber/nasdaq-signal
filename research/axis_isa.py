# -*- coding: utf-8 -*-
"""
[v29] ISA(중개형·서민형) 기준 세후 판정 — 계좌가 규칙보다 크다

사용자 계좌 조건 (2026-08-27 확인):
  · 납입한도  연 2,000만원 / 5년 누적 1억원 (미납분 이월 가능)
  · 비과세    순이익 400만원까지 (서민형)
  · 초과분    9.9% 분리과세 (금융소득종합과세 제외)
  · 계좌 안에서는 매매차익·분배금 모두 **과세이연** — 해지 시 한 번 정산

[왜 이 축이 필요한가]
  이 전략은 원화 기준 연 2.1회 **전량 전환**한다. 일반계좌에서는 전환할 때마다
  매매차익에 15.4% 가 원천징수되고 **손실 통산이 안 된다**(국내 상장 해외 ETF 는
  매매차익이 배당소득으로 과세된다). 즉 이 전략은 세금 구조에 특히 민감하다.

[분해] ISA 이득이 어디서 오는가를 4단계로 나눠 잰다
  ① 일반계좌      전환마다 15.4%
  ② 이연만        해지 시 한 번 15.4%          -> 과세이연의 값
  ③ 이연 + 9.9%   해지 시 한 번 9.9%           -> 세율 인하의 값
  ④ ISA 서민형    ③ + 순이익 400만원 비과세    -> 비과세 한도의 값

[규약] 납입은 연 2,000만원(월 1,666,667원)씩 5년 = 1억. ISA 한도상 거치식이 불가능하다.
  그 뒤는 추가 납입 없이 보유. 방어자산은 채택안 40/40/20.

실행:  python axis_isa.py            # 표
       python axis_isa.py --emit     # data/isa_stats.json 생성
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import json
import sys

import numpy as np
import pandas as pd

import hist_defasset as DA
import hist_defensive as DF
import hist_korea as K
import hist_krfinal as KF
from axis_lib import rule_w

MONTHLY = 20_000_000 / 12.0          # 연 2,000만원 납입한도
YEARS_PAY = 5                        # 5년 -> 누적 1억
EXEMPT = 4_000_000                   # 서민형 비과세 한도
ISA_RATE = 0.099                     # 초과분 분리과세
GEN_RATE = 0.154                     # 일반계좌 배당소득세
DIV_YIELD = 0.013                    # 방어 바스켓 혼합 분배율 (배당40% x 3.3%)
COST = 0.001                         # 편도 수수료
SLIP = 0.001                         # 슬리피지
FX_START = pd.Timestamp('1981-04-13')


def accum_tax(rr, dfr, w, lo, hi, mode, cost=COST + SLIP):
    """월 정액 적립 + 세금. 반환 (총납입, 세전평가, 세후평가, 낸세금, 전환횟수).

    mode: 'pre' 세전 / 'gen' 일반계좌 / 'defer' 이연만 / 'defer99' 이연+9.9%
          / 'isa' 이연+9.9%+400만 비과세
    """
    R = C = paid = 0.0
    basis = 0.0
    tax = 0.0
    nsw = 0
    mi = 0                                                 # 월 카운터 (납입 5년 제한용)
    settled = 0.0                                          # isa3: 직전 정산 시점 평가액
    nextset = lo + 3 * 252                                 # isa3: 3년마다 정산
    prev = w[lo]
    dtax = DIV_YIELD * GEN_RATE / 252.0 if mode == 'gen' else 0.0
    for i in range(lo, hi):
        # [v33 정정] 전환을 **그날 수익 적용 전에** 한다.
        # 기존 순서(수익 -> 전환)는 전일 종가 신호가 하루 더 늦게 반영되는
        # 실질 2일 지연이었다. 프로젝트 규약은 pos = w.shift(1) = 1일 지연이고
        # reentry_lib.run / axis_lib.sim 이 그렇게 돈다.
        # 검산: 납입 1회(mp=1) 로 두면 거치식 sim() 과 오차 0 이어야 한다.
        pos = w[i - 1] if i > lo else w[lo]

        if pos != prev:                                    # 전량 전환
            v = (R + C) * (1 - cost)
            if mode == 'gen':
                g = max(0.0, v - basis)
                t = g * GEN_RATE
                v -= t
                tax += t
                basis = v
            if pos >= 1:
                R, C = v, 0.0
            else:
                R, C = 0.0, v
            prev = pos
            nsw += 1

        R *= (1 + rr[i])
        C *= (1 + dfr[i])
        if dtax and C > 0:
            C *= (1 - dtax)

        if i > lo and MONTH[i] != MONTH[i - 1]:             # 월초 납입
            mi += 1
            if mi <= YEARS_PAY * 12:
                a = MONTHLY
                paid += a
                basis += a
                if pos >= 1:
                    R += a
                else:
                    C += a

        if mode == 'isa3' and i >= nextset:                 # 3년마다 해지 -> 정산
            v = R + C
            g = max(0.0, v - paid - settled)
            t = max(0.0, g - EXEMPT) * ISA_RATE
            v -= t
            tax += t
            settled = v - paid
            if pos >= 1:
                R, C = v, 0.0
            else:
                R, C = 0.0, v
            nextset = i + 3 * 252

    v = R + C
    pre = v
    if mode == 'isa3':
        g = max(0.0, v - paid - settled)
        t = max(0.0, g - EXEMPT) * ISA_RATE
        v -= t
        tax += t
    if mode in ('defer', 'defer99', 'isa'):
        net = max(0.0, v - paid)
        if mode == 'defer':
            t = net * GEN_RATE
        elif mode == 'defer99':
            t = net * ISA_RATE
        else:
            t = max(0.0, net - EXEMPT) * ISA_RATE
        v -= t
        tax += t
    return paid, pre, v, tax, nsw


MODES = [('pre', '세전 (참고)'), ('gen', '① 일반계좌 15.4% 매번'),
         ('defer', '② 이연만 · 해지시 15.4%'), ('defer99', '③ 이연 + 9.9%'),
         ('isa', '④ ISA 서민형 — 만기 연장해 끝까지 보유'),
         ('isa3', '⑤ ISA 3년마다 해지·재가입')]


def rolling(rr, dfr, w, years, step=126):
    n = len(IDX)
    span = int(years * 252)
    first = int(IDX.searchsorted(FX_START))
    starts = list(range(first, n - span, step))
    out = {}
    for key, lab in MODES:
        vals, taxes = [], []
        for lo in starts:
            paid, pre, post, tax, nsw = accum_tax(rr, dfr, w, lo, lo + span, key)
            if paid > 0:
                vals.append(post)
                taxes.append(tax / max(pre - paid, 1.0))
        out[key] = dict(label=lab, median=float(np.median(vals)),
                        q10=float(np.quantile(vals, .10)),
                        worst=float(min(vals)),
                        eff=float(np.median(taxes)) * 100, n=len(vals))
    return out, len(starts)


def show(res, years, paid):
    print()
    print('  [%d년 창 · 납입 %s원(연 2천만 x 5년) · 창 %d개]' % (years, f'{paid:,.0f}', res[1]))
    print('  %-28s %16s %16s %16s %9s'
          % ('계좌', '중앙 세후평가액', '10%분위', '최악', '실효세율'))
    r = res[0]
    base = r['gen']['median']
    for key, lab in MODES:
        d = r[key]
        mark = '' if key in ('pre', 'gen') else '  (%+.1f%% vs ①)' % ((d['median'] / base - 1) * 100)
        print('  %-28s %16s %16s %16s %8.1f%%%s'
              % (lab, f"{d['median']:,.0f}", f"{d['q10']:,.0f}",
                 f"{d['worst']:,.0f}", d['eff'], mark))


if __name__ == '__main__':
    D = DF.build('chain')
    IDX = D['idx']
    MONTH = pd.Series(IDX).dt.to_period('M').values
    Dk, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    parts = {'div': dfk,
             'ust5': (1 + DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE)) * (1 + fr) - 1,
             'gold': (1 + DA.gold_r(idx)) * (1 + fr) - 1}
    mix = DA.mix_monthly_parts(idx, DA.MIX_V23, parts)
    wB = rule_w(D['ddv'], -0.16, -0.16)

    print('ISA 중개형·서민형 기준 세후 판정 — 원화 · 환노출 2배 · 방어 40/40/20')
    print('납입 연 2,000만원 x 5년 = 1억 (ISA 한도상 거치식 불가). 편도 0.1% + 슬리피지 0.1%.')
    print('구간 %s ~ %s' % (FX_START.date(), IDX[-1].date()))

    emit = {}
    for y in (10, 15, 20):
        res = rolling(lev2, mix, wB, y)
        paid = min(YEARS_PAY * 12, y * 12) * MONTHLY
        show((res[0], res[1]), y, paid)
        emit['y%d' % y] = dict(paid=paid, windows=res[1],
                               modes={k: res[0][k] for k, _ in MODES})

    print()
    print('===== 분해 — ISA 이득이 어디서 오는가 (20년 창 중앙값) =====')
    r = rolling(lev2, mix, wB, 20)[0]
    g, d1, d2, isa = (r['gen']['median'], r['defer']['median'],
                      r['defer99']['median'], r['isa']['median'])
    tot = isa / g - 1
    print('  %-30s %+8.1f%%   (전체의 %.0f%%)' % ('과세이연 (①->②)', (d1 / g - 1) * 100,
                                                100 * (d1 / g - 1) / tot))
    print('  %-30s %+8.1f%%   (전체의 %.0f%%)' % ('세율 15.4%->9.9% (②->③)', (d2 / d1 - 1) * 100,
                                                100 * (d2 / d1 - 1) / tot))
    print('  %-30s %+8.1f%%   (전체의 %.0f%%)' % ('400만원 비과세 (③->④)', (isa / d2 - 1) * 100,
                                                100 * (isa / d2 - 1) / tot))
    print('  %-30s %+8.1f%%' % ('합계 ISA vs 일반계좌', tot * 100))
    print()
    print('  ※ 과세이연이 압도적이다. 이 전략이 연 2.1회 전량 전환하기 때문이다 —')
    print('    일반계좌는 전환할 때마다 복리의 원금이 깎인다.')
    emit['decomp'] = dict(defer=(d1 / g - 1) * 100, rate=(d2 / d1 - 1) * 100,
                          exempt=(isa / d2 - 1) * 100, total=tot * 100)

    if '--emit' in sys.argv:
        emit['params'] = dict(monthly=MONTHLY, years_pay=YEARS_PAY, exempt=EXEMPT,
                              isa_rate=ISA_RATE, gen_rate=GEN_RATE)
        with open('data/isa_stats.json', 'w', encoding='utf-8') as f:
            json.dump(emit, f, ensure_ascii=False, indent=1)
        print('\n-> data/isa_stats.json')
