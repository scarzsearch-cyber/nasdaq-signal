"""Read-only F4-A B basket materials and gross diagnostics (bbcc607).

No new signal, optimizer, live data update, personal inputs or broker writes.
The three split ledgers are accounting sensitivities, not promoted strategies.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'research'), str(ROOT/'deploy')]
import numpy as np
import pandas as pd
import strategy_f1_placebo as F
from research import basket_accounting as B
from audit.test_basket_accounting import units_reference

VARIANTS = {'C1': ('monthly', 0.), 'C2': ('signal30', 0.), 'C3': ('signal30', .02)}
WATCHED = ['research/basket_accounting.py', 'research/strategy_f4_basket.py',
           'audit/test_basket_accounting.py', 'audit/test_account_ledger.py',
           'research/account_ledger.py', 'research/strategy_f1_placebo.py',
           'research/strategy_f1_kr.py', 'research/strategy_f1_screen.py',
           'research/eng_common.py', 'research/hypo_gates.py', 'research/hypo_t4_real.py',
           'research/hypo_t4wide.py', 'deploy/build_stats.py', 'deploy/oos_log.py',
           'hist_data.py', 'hist_defensive.py', 'hist_krfinal.py', 'hist_korea.py',
           'hist_defasset.py', 'reentry_lib.py']


def source_hashes():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in WATCHED}


def monthly_units_reference(idx, parts, fee):
    """Independent units/price reconstruction of the existing synthetic basket.

    Keeps its legacy wealth-times-L1 cost convention for a reduction ONLY.
    New split account trades instead use the exact cash budget in account_ledger.
    """
    frac = np.array([.4, .4, .2])
    prices, units = np.ones(3), frac.copy()
    out = np.zeros(len(idx))
    previous_month = idx[0].month
    for d in range(len(idx)):
        total = float(np.dot(prices, units))
        if d and idx[d].month != previous_month:
            traded = sum(abs(prices*units-total*frac))
            units = (total-fee*traded)*frac/prices
        prices *= 1+parts[d]
        out[d] = np.dot(prices, units)/total-1
        previous_month = idx[d].month
    out[0] = 0.
    return out


def schedule_reference(clock, eligible, anchors, rule):
    """Enumerate calendar due dates, then find eligible rows, not cycle changes."""
    clock = pd.DatetimeIndex(clock)
    eligible_rows = np.flatnonzero(eligible)
    out = np.zeros(len(clock), bool)
    if rule == 'monthly':
        first = clock[0].to_period('M').start_time+pd.offsets.MonthBegin(1)
        for due in pd.date_range(first, clock[-1], freq='MS'):
            hits = eligible_rows[clock[eligible_rows] >= due]
            if len(hits) and anchors[hits[0]] >= 0:
                out[hits[0]] = True
    else:
        bounds = np.r_[0, np.flatnonzero(anchors[1:] != anchors[:-1])+1, len(anchors)]
        for begin, end in zip(bounds[:-1], bounds[1:]):
            anchor = int(anchors[begin])
            if anchor < 0: continue
            start = pd.Timestamp(np.datetime64(anchor, 'D'))
            due = start+pd.Timedelta(days=30)
            rows = eligible_rows[(eligible_rows >= max(begin, 1)) & (eligible_rows < end)]
            while due <= clock[end-1]:
                if due > clock[0]:
                    hits = rows[clock[rows] >= due]
                    if len(hits): out[hits[0]] = True
                due += pd.Timedelta(days=30)
    return out


def load_material(delay=0, gold_fee=0.):
    D, idx, lo, _, _, old, close, _, _, _, logs = F.load_material()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import hist_defasset as DA
        import hist_korea as K
        fx = K.fx(idx).pct_change().fillna(0.).to_numpy()
        parts = np.column_stack([(1+D['schdr'])*(1+fx)-1,
                 (1+DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE))*(1+fx)-1,
                 (1+DA.gold_r(idx, fee=gold_fee))*(1+fx)-1])
        kr = K.kr_caldays()
    source, eligible = F.execution_events(idx, kr, lo, delay)
    w = close['B'][source, 0]
    known_anchor = np.full(len(idx), -1, int)
    anchor = -1
    for i, risk in enumerate(close['B'][:, 0]):
        if risk:
            anchor = -1
        elif anchor < 0:
            anchor = int(idx[i].to_datetime64().astype('datetime64[D]').astype(int))
        known_anchor[i] = anchor
    anchors = known_anchor[source]
    opening = kr.searchsorted(idx[lo:], side='right')-1-delay
    assert (opening >= 0).all()
    clock = kr[opening].to_numpy(dtype='datetime64[D]')
    # The first row is an already funded initial state, not a claimed trade.
    clock[0] = max(clock[0], idx[lo].to_datetime64().astype('datetime64[D]'))
    if clock[1] < clock[0]:
        clock[0] = clock[1]
    reviews = {rule: B.review_schedule(clock, eligible, anchors, rule)
               for rule in ('monthly', 'signal30')}
    for rule, mask in reviews.items():
        np.testing.assert_array_equal(mask, schedule_reference(clock, eligible, anchors, rule))
    raw = np.column_stack([old[:, 0], parts[lo:]])
    reference = monthly_units_reference(idx, parts, .0005)[lo:]
    if gold_fee == 0:
        np.testing.assert_allclose(reference, old[:, 1], rtol=0, atol=2e-14)
    r = old.copy()
    if gold_fee:
        r[:, 1] = reference
    dist = np.zeros_like(raw); dist[:, 1] = .0325/252
    return dict(dates=idx[lo:], attack=w, returns=raw, trade_days=eligible, reviews=reviews,
                aggregate_returns=r, aggregate_positions=close['B'][source],
                distribution_rates=dist, clock=clock, anchors=anchors,
                basket_reduction_max_abs_error=float(np.max(abs(reference-old[:, 1]))) if gold_fee == 0 else None,
                logs=logs)


def summarize(curve, dates, count):
    years = (dates[-1]-dates[0]).days/365.25
    daily = curve[1:]/curve[:-1]-1
    return dict(cagr_pct=float((curve[-1]**(1/years)-1)*100),
                mdd_pct=float(np.min(curve/np.maximum.accumulate(curve)-1)*100),
                volatility_pct=float(np.std(daily, ddof=1)*np.sqrt(252)*100),
                trade_days_per_year=float(count/years),
                curve_sha256=F.digest(curve), final=float(curve[-1]))


def gross_diagnostics(material, fee=.001):
    from research.account_ledger import account_windows
    m = material; n = len(m['attack']); empty = np.empty((0, 1), int)
    common = dict(starts=[0], ends=[n-1], deposit_days=empty, deposits=[], initial=1.,
                  fee=fee, record_paths=True)
    old = account_windows(m['aggregate_positions'], m['aggregate_returns'], m['trade_days'], **common)
    # Cash-free binary C0 trades only on executed state changes. Its synthetic
    # basket's internal monthly costs are already in returns, not ledger orders.
    switches = m['attack'][1:] != m['attack'][:-1]
    assert not (switches & ~m['trade_days'][1:]).any()
    rows = {'C0': summarize(old['paths'][:, 0], m['dates'], int(switches.sum()))}
    references = []
    for name, (rule, threshold) in VARIANTS.items():
        out = B.account_windows(m['attack'], m['returns'], m['trade_days'], m['reviews'][rule],
                                review_threshold=threshold, **common)
        ref = units_reference(m['attack'], m['returns'], m['trade_days'], m['reviews'][rule],
                              0, n-1, [], [], 1., fee, threshold=threshold)
        error = float(np.max(abs(out['paths'][:, 0]/ref['paths']-1)))
        assert error < 2e-10
        rows[name] = summarize(out['paths'][:, 0], m['dates'], int(out['trade_count'][0]))
        references.append(dict(name=name, max_relative_error=error,
                          closed_day_trade_violations=sum(not m['trade_days'][d] for d in ref['traded_dates'])))
    return rows, references


def main():
    before = source_hashes()
    rows, checks = {}, []
    for name, fee, delay, gold in [('base', .001, 0, 0.), ('cost2', .002, 0, 0.),
                                  ('delay1', .001, 1, 0.), ('gold019', .001, 0, .0019)]:
        m = load_material(delay, gold)
        rows[name], refs = gross_diagnostics(m, fee)
        checks += [dict(condition=name, **x) for x in refs]
    assert before == source_hashes()
    print('RESULT_JSON'+json.dumps(dict(protocol_commit='bbcc607', rows=rows, references=checks,
                                      source_sha256=before), ensure_ascii=False))


if __name__ == '__main__':
    main()
