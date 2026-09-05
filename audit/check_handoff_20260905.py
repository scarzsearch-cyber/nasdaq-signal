"""Independent numerical audit of the handoff; offline and read-only.

Shares raw-material builders, NOT eng_common/reentry/OOS/tax simulators.
This checks the specified model, not data provenance or actual tax law.
Run from repository: python audit/check_handoff_20260905.py
"""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'research'))
import hist_defensive as source
import hist_defasset as defensive
import hist_data


def path(signal, attack, defense, fee=.001):
    wealth, previous, out = 1., int(signal[0]), [1.]
    for day in range(1, len(signal)):
        position = int(signal[day-1])
        wealth *= (1-fee*abs(position-previous))
        wealth *= 1 + (attack[day] if position else defense[day])
        previous = position
        out.append(wealth)
    return np.array(out)


def drawdown(values):
    peak, worst = values[0], 0.
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value/peak-1)
    return worst


def annual_tax(gross, signal, years, start, end):
    # Independent daily ledger: year-end tax first, then any next-session switch.
    value, basis, realized = 1., 1., 0.
    for day in range(start, end+1):
        if day > start:
            value *= gross[day]/gross[day-1]
        if day == end:
            realized += value-basis
            value -= .22*max(realized, 0.)
            break
        if years[day] != years[day+1]:
            tax = .22*max(realized, 0.)
            sold_basis = basis*tax/value
            value -= tax
            basis -= sold_basis
            realized = tax-sold_basis
        if signal[day] != signal[day-1] and day >= 1:
            value *= .999
            realized += value-basis
            basis = value
    return value


def main():
    data = source.build('chain')
    dates = pd.DatetimeIndex(data['idx'])
    px = np.asarray(data['px'], float)
    defense = np.nan_to_num(defensive.mix_monthly(dates, defensive.MIX_V23, data['schdr']))
    attack = np.nan_to_num(data['qldr'])
    signal = np.array([float(px[i]/max(px[max(0, i-251):i+1])-1 > -.16)
                       for i in range(len(px))])
    b = path(signal, attack, defense)
    hold = np.cumprod(1+attack)
    protocol = json.loads((ROOT/'data/oos_protocol_b.json').read_text(encoding='utf-8'))
    fp = hashlib.sha256(json.dumps({k:v for k,v in protocol.items() if k != 'fingerprint'},
                           sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()[:16]
    assert fp == protocol['fingerprint'] == '74387a5c73c0fc06'
    previous, rows = -10**9, []
    for i in range(1, len(px)):
        if signal[i-1] and not signal[i]:
            independent = i-previous > 252
            previous = i
            if i+252 < len(px) and dates[i] < pd.Timestamp(protocol['applies_to']['oos_start']):
                lo, hi = max(0, i-63), i+252
                rows.append((independent, drawdown(b[lo:hi+1]), drawdown(hold[lo:hi+1]),
                             (b[hi]/b[lo])/(hold[hi]/hold[lo])-1))
    premiums = np.array([r[3] for r in rows])
    disasters = [r for r in rows if r[0] and r[2] <= -.5]
    rolling = b[756:]/b[:-756]/(hold[756:]/hold[:-756])-1
    oos = dict(independent=int(sum(r[0] for r in rows)), events=len(rows), disasters=len(disasters),
               paid=int(sum(r[1] > r[2] for r in disasters)), premium_p05=float(np.quantile(premiums,.05)),
               premium_min=float(min(premiums)), rolling_p05=float(np.quantile(rolling,.05)),
               rolling_min=float(min(rolling)), fingerprint=fp)
    assert (oos['independent'], oos['events'], oos['disasters'], oos['paid']) == (21,69,8,8)
    np.testing.assert_allclose([oos[k] for k in ('premium_p05','premium_min','rolling_p05','rolling_min')],
                               [-.293,-.411,-.331,-.493], rtol=0, atol=.0005)
    ws = [min(b[p+252::252]/b[p:-252:252]-1) for p in range(252)]
    market = dict(worst=min(ws), median=float(np.median(ws)), best=max(ws))
    np.testing.assert_allclose(list(market.values()), [-.536,-.374,-.160],rtol=0,atol=.0005)

    fx = hist_data._fred('data/hist/fred_DEXKOUS.csv', 'DEXKOUS')
    fx = fx.reindex(dates.union(fx.index)).ffill().reindex(dates)
    fr = np.nan_to_num(fx.pct_change().to_numpy())
    returns = np.r_[0., px[1:]/px[:-1]-1]
    defense_krw = (1+defense)*(1+fr)-1
    dom = path(signal, 2*((1+returns)*(1+fr)-1)-data['c_daily'], defense_krw)
    us_return = (1+3*returns-.00021170)*(1+fr)-1
    us = path(signal, us_return, defense_krw)
    us_gross = path(signal, us_return, defense_krw, fee=0.)
    start = int(np.flatnonzero(dates.year >= 2000)[0])
    value = dom[-1]/dom[start]
    isa = value-.099*max(value-1,0.)
    direct = annual_tax(us_gross, signal, dates.year, start, len(dates)-1)
    taxes = dict(isa=isa, direct3=direct, ratio=direct/isa,
                 isa_pretax_mdd=drawdown(dom[start:]), direct_pretax_mdd=drawdown(us[start:]))
    np.testing.assert_allclose([isa,direct], [161.5,283.9],rtol=0,atol=.05)
    print(json.dumps(dict(oos=oos, market_only=market, tax_model=taxes), indent=2))
    check_nextgen()


def check_nextgen():
    import axis_nextgen as ng
    d, wt, wb, votes, rv = ng.build('tbill')
    r, _ = hist_data.qqq_proxy()
    px = (1+r).cumprod().reindex(d['idx'])
    candidates = ng.make_candidates(wb, wt, votes, rv, d['ddv'], px)
    maximum, count = 0., 0
    for name, signal in candidates.items():
        for lag, start, end, cost in ((1,None,None,.002), (2,None,None,.002),
                                      (1,None,'2000-01-01',.002),
                                      (1,'2000-01-01',None,.002), (1,None,None,.001)):
            curve, turnover = ng.execution_path(d, signal, lag=lag, start=start, end=end, cost=cost)
            lo, hi = d['idx'].get_indexer([curve.index[0], curve.index[-1]])
            weights = signal[lo:hi+1]
            held = np.array([weights[0], 1-weights[0]])
            values, turns = [1.], [0.]
            for j in range(1,len(weights)):
                target = np.array([weights[max(0,j-lag)], 1-weights[max(0,j-lag)]])
                total = held.sum()
                # Currency amounts independently produce the same proportional fee.
                traded = abs(target*total-held).sum()/2
                turns.append(traded/total)
                held = target*(total-cost*traded)
                held *= 1+np.array([d['qldr'][lo+j], d['schdr'][lo+j]])
                values.append(held.sum())
            error = float(np.max(np.abs(curve.to_numpy()/values-1)))
            maximum = max(maximum,error)
            np.testing.assert_allclose(curve,values,rtol=5e-12,atol=1e-12)
            np.testing.assert_allclose(turnover,turns,rtol=0,atol=1e-12)
            count += 1
            if name == 'MIX(0.50)' and lag == 1 and start is None and end is None and cost == .002:
                old, _ = ng.legacy_sim(d,signal,cost=cost)
                years = (curve.index[-1]-curve.index[0]).days/365.25
                print('MIX50 comparison:', json.dumps(dict(old_final=old.iloc[-1],
                      new_final=curve.iloc[-1], relative=curve.iloc[-1]/old.iloc[-1]-1,
                      old_turn=np.abs(np.diff(signal)).sum()/years, new_turn=turnover.sum()/years)))
    print('nextgen independent paths:',count,'maximum relative error:',maximum)


if __name__ == '__main__':
    main()
