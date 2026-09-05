"""Preregistered F1 currency/calendar bridge; NOT an ISA/account forecast.

Read-only historical proxies on US valuation dates; no live orders or exports.
Protocol: STRATEGY_RESEARCH_2026-09-05.md section 8, commit 5f94d55.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'research'), str(ROOT/'deploy')]
os.chdir(ROOT)
import numpy as np
import pandas as pd
from research.rebalance_accounting import scheduled_path, daily_turnover
from strategy_f1_screen import targets, metrics, windows


def execution_events(idx, krdays, lo=0, extra_days=0):
    """Forward mapping: US close -> first later KR opening -> US valuation row.

    Multiple signals mapped to one execution row use the newest known signal.
    No new signal/trade event is created on a Korean holiday. Row zero is funded.
    """
    idx, krdays = pd.DatetimeIndex(idx), pd.DatetimeIndex(krdays)
    for name, dates in [('idx', idx), ('krdays', krdays)]:
        if not len(dates) or not dates.is_monotonic_increasing or not dates.is_unique or dates.hasnans:
            raise ValueError(name+' must be unique ordered nonempty finite dates')
    if isinstance(extra_days, bool) or int(extra_days) != extra_days or extra_days < 0:
        raise ValueError('extra_days must be a nonnegative whole KR trading-day count')
    extra_days = int(extra_days)
    if not 0 <= lo < len(idx) or krdays[-1] < idx[-1]:
        raise ValueError('invalid start or incomplete KR calendar coverage')
    source = np.full(len(idx)-lo, -1, int)
    openings = krdays.searchsorted(idx, side='right') + extra_days
    valid = openings < len(krdays)
    destinations = np.full(len(idx), len(idx), int)
    destinations[valid] = idx.searchsorted(krdays[openings[valid]])
    for signal in range(lo, len(idx)):
        row = int(destinations[signal])
        if lo < row < len(idx):
            source[row-lo] = signal
    trade = source >= 0
    source[0] = lo
    for i in range(1, len(source)):
        if source[i] < 0:
            source[i] = source[i-1]
    return source, trade


def inverse_sources(idx, krdays, lo=0, extra_days=0):
    """Independent inverse map: latest knowable US close at eligible KR opening."""
    last_open = krdays.searchsorted(idx[lo:], side='right')-1-extra_days
    if (last_open < 0).any():
        raise ValueError('insufficient earlier KR openings')
    known = idx.searchsorted(krdays[last_open], side='left')-1
    known = np.maximum(known, lo)
    known[0] = lo
    return known


def held_units_reference(p, r, trade, cost):
    """Independent blockwise share-count valuation between execution dates.

    Does not use scheduled_path/daily_turnover. Prices are arbitrary cumulative
    indices; each rebalance determines units, held until the next event.
    """
    gross = 1+r.copy()
    gross[0] = 1.
    price = np.cumprod(gross, axis=0)
    if (price <= 0).any():
        raise ValueError('reference requires strictly positive asset prices')
    units = p[0].copy()
    out = np.ones(len(p))
    boundaries = sorted(set([1, len(p), *(np.flatnonzero(trade[1:])+1).tolist()]))
    for begin, end in zip(boundaries[:-1], boundaries[1:]):
        values = units*price[begin-1]
        total = float(values.sum())
        if trade[begin]:
            cash_traded = .5*float(np.abs(total*p[begin]-values).sum())
            units = (total-cost*cash_traded)*p[begin]/price[begin-1]
        out[begin:end] = np.sum(price[begin:end]*units, axis=1)
    return out


def main():
    logs = io.StringIO()
    with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
        import build_stats as bs
        import eng_common as E
        import hypo_gates as G
        import hypo_t4_real as T
        D, idx, attack, _, div, fx = bs.KF.build_krw('chain')
        defense = bs.kr_basket(idx, div, fx, 'mix')
        krdays = bs.K.kr_caldays()
    assert idx.equals(G.idx)
    lo = int(idx.searchsorted(pd.Timestamp('2000-01-03')))
    dates = idx[lo:]
    W = targets(pd.Series(D['px'], index=idx), T.t4_w(G.r_eq1), E.rule_dd)
    usd = np.column_stack([G.D['qldr'], G.Dm['schdr'], G.tb, G.r_eq1])[lo:]
    krw = np.column_stack([attack, defense, (1+G.tb)*(1+fx)-1,
                           (1+D['rq'])*(1+fx)-1])[lo:]
    assert np.isfinite(usd).all() and np.isfinite(krw).all()
    kr_source, kr_trade = execution_events(idx, krdays, lo)
    np.testing.assert_array_equal(kr_source, inverse_sources(idx, krdays, lo))
    late_source, late_trade = execution_events(idx, krdays, lo, 1)
    np.testing.assert_array_equal(late_source, inverse_sources(idx, krdays, lo, 1))
    us_source = np.r_[lo, np.arange(lo, len(idx)-1)]
    us_trade = np.r_[False, np.ones(len(dates)-1, bool)]
    runs, identities = {}, {}
    maxerr, no_trade_rows = 0., int(np.count_nonzero(~kr_trade[1:]))
    configs = [('USD_US', usd, us_source, us_trade, .002),
               ('USD_KR', usd, kr_source, kr_trade, .002),
               ('KRW_US', krw, us_source, us_trade, .002),
               ('KRW_KR', krw, kr_source, kr_trade, .002),
               ('KRW_KR_cost2', krw, kr_source, kr_trade, .004),
               ('KRW_KR_delay1', krw, late_source, late_trade, .002)]
    for label, R, sources, trade, cost in configs:
        curves, rows = {}, {}
        for name, weights in W.items():
            p = weights[sources]
            a, t = scheduled_path(p, R, trade, cost)
            ref = held_units_reference(p, R, trade, cost)
            err = float(np.max(np.abs(a/ref-1)))
            maxerr = max(maxerr, err)
            assert err < 2e-11, (label, name, err)
            assert np.count_nonzero(t[~trade]) == 0
            curves[name], rows[name] = a, metrics(a, dates, t)
            if label in ('USD_KR', 'KRW_KR') and name in ('B', 'A'):
                # Existing binary engine with exactly the same return materials.
                Dx = dict(D, qldr=np.r_[np.zeros(lo), R[:, 0]], schdr=np.r_[np.zeros(lo), R[:, 1]])
                legacy, _, turns = bs.K.run_kr(Dx, bs.STRATS[name], cost=cost,
                                                start=dates[0], krdays=krdays)
                np.testing.assert_array_equal(t, turns)
                identities[label+'/'+name] = float(np.max(np.abs(a/legacy.values-1)))
                assert identities[label+'/'+name] < 1e-12
                if label == 'KRW_KR' and name == 'B':
                    # The private funding plan uses this 1997-start public
                    # recipe. Only slice/rebase it; do not compare 1997 CAGR
                    # with the current 2000-start CAGR as if code degraded it.
                    personal, _, _ = bs.K.run_kr(dict(D, qldr=attack, schdr=defense),
                        bs.STRATS['B'], cost=.001, slip=.001, start=bs.KF.ST, krdays=krdays)
                    segment = personal.loc[dates[0]:]
                    assert segment.index.equals(dates)
                    rebased = segment.values/segment.iloc[0]
                    error = float(np.max(np.abs(a/rebased-1)))
                    identities['personal_B_1997_curve_slice_2000'] = error
                    assert error < 1e-12
            if label == 'KRW_KR' and name.startswith('T4'):
                # Deliberately flawed calendar use: lag targets, but rebalance
                # every US valuation day even when Korea has no opening.
                wrong_t = daily_turnover(p, R)
                daily = np.sum(p*R, axis=1); daily[0] = 0.
                wrong = np.cumprod((1+daily)*(1-cost*wrong_t))
                rows[name]['phantom_holiday_comparison'] = dict(
                    correct_to_daily_reset_final_ratio=float(a[-1]/wrong[-1]),
                    phantom_trade_rows=int(np.count_nonzero((wrong_t > 1e-10) & ~trade)))
        runs[label] = dict(rows=rows, windows={str(y): windows(curves, dates, y) for y in (7, 10)})
    print(json.dumps(dict(protocol_commit='5f94d55', start=str(dates[0].date()), end=str(dates[-1].date()),
        scope='Historical KRW product proxy and KR-calendar bridge; no deposits or account tax',
        price_rows=len(dates), rows_without_KR_trade_opportunity=no_trade_rows,
        inverse_map_exact=True, max_relative_units_reference_error=maxerr,
        binary_legacy_identities=identities, runs=runs,
        limitations=['US valuation grid collapses intra-US-holiday Korean sessions and intermediate FX moves',
          'T4-tb KRW is a theoretical unhedged T-bill proxy, not an ISA-eligible product certification',
          'T4 volatility signal remains USD underlying, not KRW realized volatility targeting',
          'No deposits, tax, whole shares, settlement, actual broker fills or account recommendations',
          'Historical reuse and overlapping windows; not fresh OOS or future probabilities'],
        next_questions=['Do income tax and monthly deposits change A/T4 ordering?',
                        'Does block-shuffle falsification support timing rather than exposure alone?'],
        diagnostics=logs.getvalue()), ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
