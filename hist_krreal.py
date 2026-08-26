# -*- coding: utf-8 -*-
"""
과제 ③ 실물검증 — TIGER 3종이 모두 상장된 구간에서 '실제 시가 체결'로 돌린다.
소급 없음: 세 상품 모두 존재하는 2023-06-20 이후만 사용.
신호는 QQQ 미국 종가 DD(252일). 체결은 그 다음 한국 거래일 시가(실제 Open).
"""
import numpy as np, pandas as pd
import hist_data as H, hist_tiger as TT, hist_korea as K, hist_defasset as DA
from reentry_lib import met

LB, ENTER = 252, -0.16
COST = 0.001                      # 편도 거래비용
SLIP = 0.001                      # 제미나이.md 규약: 최소 0.1% 슬리피지 강제


def signals(exit_):
    qqq = H._stooq('qqq_us_d.csv')
    dd = (qqq / qqq.rolling(LB, min_periods=LB).max() - 1).dropna()
    w, cur = {}, 1.0
    for d, v in dd.items():
        if cur >= 1.0:
            if v <= ENTER: cur = 0.0
        else:
            if v <= ENTER: cur = 0.0
            elif v > exit_: cur = 1.0
        w[d] = cur
    return pd.Series(w), dd


def run_real(exit_, start='2023-06-20', slip=SLIP, cost=COST, defmix=False):
    """defmix=True 면 방어자산을 전략_v23 채택안(배당50 / ACE KRX금현물50)으로 바꾼다."""
    w, dd = signals(exit_)
    lev, div = TT.T['lev']['open'], TT.T['div']['open']
    kr = lev.index.intersection(div.index)
    extra = {}
    if defmix:
        # 채택안 3다리를 전부 국내 실물 시가로 잡는다 (전부 환노출)
        for leg in DA.MIX_LEGS:
            if leg['kind'] == 'div':
                continue
            g = DA.kr_tr_open(leg['code'])
            kr = kr.intersection(g.index)
            extra[leg['kind']] = g
    kr = kr[kr >= start]
    rl = lev.reindex(kr).pct_change().fillna(0)      # 시가->시가 (분배금 조정)
    rd = div.reindex(kr).pct_change().fillna(0)
    if defmix:
        parts = {'div': rd.values}
        for k, g in extra.items():
            parts[k] = g.reindex(kr).pct_change().fillna(0).values
        rd = pd.Series(DA.mix_monthly_parts(kr, DA.MIX_V23, parts), index=kr)
    pos, cur = [], 1.0
    for d in kr:
        s = w.loc[:d - pd.Timedelta(days=1)]         # d 개장 전에 확정된 마지막 신호
        if len(s): cur = float(s.iloc[-1])
        pos.append(cur)
    hold = pd.Series(pos, index=kr)            # hold[d] = 그날 시가에 잡아 보유하는 비중
    eff = hold.shift(1).fillna(1.0)            # 수익 귀속: open(d-1)->open(d) 구간은 hold[d-1]
    r = eff * rl + (1 - eff) * rd
    turn = eff.diff().abs().fillna(0)
    g = (1 + r) * (1 - (cost + slip) * turn)
    return pd.Series(np.cumprod(g), index=kr), hold, dd.reindex(dd.index[dd.index >= start])


if __name__ == '__main__':
    for lab, ex in [('A  -16/-11', -0.11), ('B  -16/-16', -0.16)]:
        c, pos, dd = run_real(ex)
        m = met(c); sw = int((pos.diff().abs() > 0).sum())   # pos = 실제 체결일 기준
        print('%-11s 실물 TIGER 시가체결  최종 %6.3f배  CAGR %6.2f%%  MDD %7.2f%%  전환 %d회'
              % (lab, m['final'], m['cagr'] * 100, m['mdd'] * 100, sw))
        ch = pos[pos.diff().abs() > 0]
        for d, v in ch.items():
            print('        %s 시가 체결  ->  %s' % (d.date(), 'TIGER레버리지' if v > 0.5 else 'TIGER배당다우존스'))
    kr = TT.T['lev']['open'].index.intersection(TT.T['div']['open'].index)
    kr = kr[kr >= '2023-06-20']
    for nm, s in [('TIGER레버리지 계속보유', TT.T['lev']['close']), ('TIGER배당 계속보유', TT.T['div']['close']),
                  ('TIGER나스닥100 계속보유', TT.T['nasdaq100']['close'])]:
        v = s.reindex(kr).ffill(); r = v.pct_change().fillna(0)
        m = met(pd.Series(np.cumprod(1 + r), index=kr))
        print('%-24s 최종 %6.3f배  CAGR %6.2f%%  MDD %7.2f%%' % (nm, m['final'], m['cagr']*100, m['mdd']*100))
    print('\n신호 구간 내 QQQ 최저 DD = %.2f%%  (진입선 -16%% 도달 여부가 이 구간 검증력을 좌우)'
          % (dd.min() * 100))
