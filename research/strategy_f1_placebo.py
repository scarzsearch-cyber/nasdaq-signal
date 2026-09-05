"""Preregistered F1 timing falsification, not an investment recommendation.

Protocol section 12: a1604ec, corrected BEFORE results in eacb47a (999 draws).
P1 permutes close-day target schedules; P2 permutes raw signal returns and
rebuilds signals. Asset returns and the KR execution calendar stay fixed.
No portfolio inputs, broker access, files written, or operational rule changes.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'research'), str(ROOT/'deploy')]
os.chdir(ROOT)
import numpy as np
import pandas as pd
from research.account_ledger import rebalance, account_windows
from strategy_f1_kr import execution_events
from strategy_f1_screen import targets
from audit.test_account_ledger import trade_reference

SEED, DRAWS, RANDOM_WINDOWS = 20260905, 999, 5000
FAMILIES = ['B', 'A', 'T4-tb', 'T4-mix', 'MA200-mix', 'MOM252-mix']
NAMES = FAMILIES+['Hold1', 'Hold2']


def digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def annual_permutations(dates, count, rng):
    """Whole blocks, no resizing/padding; each source row appears exactly once."""
    dates = pd.DatetimeIndex(dates)
    if not len(dates) or dates.hasnans or not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError('unique ordered finite dates required')
    years = np.unique(dates.year)
    blocks = [np.flatnonzero(dates.year == y) for y in years]
    if len(blocks) < 2 or isinstance(count, bool) or int(count) != count or count < 1:
        raise ValueError('at least two year blocks and a positive whole draw count required')
    # Avoid an endless sampler on tiny test calendars.
    capacity = 1
    for k in range(2, len(blocks)+1):
        capacity *= k
        if capacity > count:
            break
    if count >= capacity:
        raise ValueError('not enough distinct nonidentity year permutations')
    identity = tuple(range(len(blocks)))
    seen, orders, rows = {identity}, [], []
    while len(orders) < count:
        perm = tuple(int(x) for x in rng.permutation(len(blocks)))
        if perm in seen:
            continue
        seen.add(perm)
        row = np.concatenate([blocks[k] for k in perm])
        np.testing.assert_array_equal(np.sort(row), np.arange(len(dates)))
        orders.append(perm); rows.append(row)
    return np.array(rows, dtype=np.int32), np.array(orders, dtype=np.int32), years, [len(b) for b in blocks]


def holm_adjust(pvalues):
    p = np.asarray(pvalues, float)
    if p.ndim != 1 or not len(p) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError('finite nonempty probability vector required')
    order = np.argsort(p, kind='stable')
    adjusted = np.minimum(1., np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    result = np.empty_like(p); result[order] = adjusted
    return result


def tail_probability(observed, null):
    null = np.asarray(null, float)
    if null.ndim != 1 or not len(null) or not np.isfinite(null).all() or not np.isfinite(observed):
        raise ValueError('finite observation and nonempty finite null required')
    return float((1+np.count_nonzero(null >= observed))/(len(null)+1))


def make_positions(weights, name):
    """Rows are paths, not time. The scalar is attack exposure except Hold1."""
    w = np.asarray(weights, float)
    p = np.zeros((len(w), 4))
    risk = 3 if name == 'Hold1' else 0
    safe = 2 if name == 'T4-tb' else 1
    p[:, risk] = w; p[:, safe] = 1-w
    return p


def gross_batch(weights, name, returns, trade_days, fee=.001):
    """No-deposit/no-tax parallel accounts; same monetary fee as section 10.

    weights are N dates x P paths, already execution-lagged. Closed dates hold
    real asset values, not target ratios. This is NOT a new tax implementation.
    """
    w, r, trade = np.asarray(weights, float), np.asarray(returns, float), np.asarray(trade_days)
    if (w.ndim != 2 or not w.size or r.shape != (len(w), 4) or trade.shape != (len(w),) or
            trade.dtype.kind != 'b' or not np.isfinite(w).all() or (w < 0).any() or (w > 1).any() or
            not np.isfinite(r).all() or (r <= -1.).any() or not np.isfinite(fee) or not 0 <= fee < 1):
        raise ValueError('invalid batch inputs')
    if name not in NAMES:
        raise ValueError('not an F1 candidate')
    h = make_positions(w[0], name)
    out = np.ones(w.shape)
    turnover = np.zeros(w.shape[1]); days = np.zeros(w.shape[1], int)
    cash = np.zeros(w.shape[1])
    for t in range(1, len(w)):
        if trade[t]:
            total = h.sum(axis=1)
            # Basis is irrelevant at tax_rate=0, so no artificial tax state is
            # carried in this pure gross diagnostic. rebalance still conserves cash.
            q = rebalance(h, h, cash, make_positions(w[t], name), fee, 0.)
            moved = (q['sold']+q['bought']).sum(axis=1)
            turnover += moved/(2*total)
            days += moved > total*1e-12
            h = q['held']
        h *= 1+r[t]
        out[t] = h.sum(axis=1)
    if not np.isfinite(out).all() or (out <= 0).any():
        raise ArithmeticError('invalid monetary path')
    return out, turnover, days


def units_reference(weights, name, returns, trade, fee=.001):
    """Independent units valued at cumulative prices + bisection trade budget."""
    gross = 1+returns.copy(); gross[0] = 1.
    prices = np.cumprod(gross, axis=0)
    units = make_positions([weights[0]], name)[0]
    out = np.ones(len(weights))
    for t in range(1, len(weights)):
        if trade[t]:
            held = units*prices[t-1]
            desired = make_positions([weights[t]], name)[0]
            new, _, _, _ = trade_reference(held, held, 0., desired, fee, 0.)
            units = new/prices[t-1]
        out[t] = units@prices[t]
    return out


def window_metrics(curves, dates):
    result = {}
    for years in (7, 10):
        s = np.arange(len(dates))
        e = dates.searchsorted(dates+pd.DateOffset(years=years))
        s, e = s[e < len(dates)], e[e < len(dates)]
        if not len(s):
            raise ValueError('complete horizon required')
        values = curves[e]/curves[s]
        count, last = 0, -1
        for first, end in zip(s, e):
            if first >= last:
                count += 1; last = end
        result[years] = dict(median=np.median(values, axis=0), lower5=np.quantile(values, .05, axis=0),
                             starts=len(s), nonoverlap=count)
    return result


def score(curves, dates, baseline_lower5):
    years = (dates[-1]-dates[0]).days/365.25
    cagr = (curves[-1]/curves[0])**(1/years)-1
    mdd = np.min(curves/np.maximum.accumulate(curves, axis=0)-1, axis=0)
    if (mdd >= 0).any():
        raise ValueError('Calmar undefined without a drawdown')
    wm = window_metrics(curves, dates)
    weak = np.minimum(*[np.log(wm[y]['lower5']/baseline_lower5[y]) for y in (7, 10)])
    return dict(calmar=cagr/(-mdd), weak_tail=weak, cagr=cagr, mdd=mdd,
                median7=wm[7]['median'], lower5_7=wm[7]['lower5'],
                median10=wm[10]['median'], lower5_10=wm[10]['lower5'])


def random_intervals(dates, count, rng):
    months = rng.integers(36, 181, count)
    starts, ends = np.empty(count, int), np.empty(count, int)
    for duration in np.unique(months):
        all_end = dates.searchsorted(dates+pd.DateOffset(months=int(duration)))
        valid = np.flatnonzero(all_end < len(dates))
        if not len(valid):
            raise ValueError('calendar too short for preregistered interval range')
        chosen = np.flatnonzero(months == duration)
        starts[chosen] = rng.choice(valid, len(chosen))
        ends[chosen] = all_end[starts[chosen]]
    return starts, ends, months


def load_material():
    logs = io.StringIO()
    with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
        import build_stats as bs
        import eng_common as E
        import hypo_gates as G
        import hypo_t4_real as T
        D, idx, attack, _, div, fx = bs.KF.build_krw('chain')
        defense = bs.kr_basket(idx, div, fx, 'mix')
        krdays = bs.K.kr_caldays()
    lo = int(idx.searchsorted(pd.Timestamp('2000-01-03')))
    source, trade = execution_events(idx, krdays, lo)
    r = np.column_stack([attack, defense, (1+G.tb)*(1+fx)-1, (1+D['rq'])*(1+fx)-1])[lo:]
    close = targets(pd.Series(D['px'], index=idx), T.t4_w(G.r_eq1), E.rule_dd)
    return D, idx, lo, source-lo, trade, r, close, G, E, T, logs.getvalue()


def main():
    # Mechanical testability check, before generating ANY random results.
    assert 24/(DRAWS+1) < .05, 'Holm gate impossible at this Monte Carlo resolution'
    watched = ['research/strategy_f1_placebo.py', 'research/account_ledger.py',
        'research/strategy_f1_kr.py', 'research/strategy_f1_screen.py', 'research/eng_common.py',
        'research/hypo_gates.py', 'research/hypo_t4_real.py', 'research/hypo_t4wide.py',
        'deploy/build_stats.py', 'deploy/oos_log.py', 'hist_data.py', 'hist_korea.py',
        'hist_krfinal.py', 'hist_defasset.py', 'audit/test_account_ledger.py']
    before = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in watched}
    D, idx, lo, source, trade, returns, close, G, E, T, logs = load_material()
    dates = idx[lo:]
    seq_perm, seq_window = np.random.SeedSequence(SEED).spawn(2)
    rows, orders, years, lengths = annual_permutations(dates, DRAWS, np.random.default_rng(seq_perm))
    original = {n: close[n][lo:, 3 if n == 'Hold1' else 0] for n in NAMES}
    # Identity reconstruction before the input-placebo distribution.
    raw = np.asarray(G.r_eq1, float)
    if not np.isfinite(raw).all() or (raw <= -1.).any():
        raise ValueError('signal input contains invalid return observations')
    identity = targets(pd.Series(np.cumprod(1+raw), index=idx), T.t4_w(raw), E.rule_dd)
    identity_errors = {}
    for name in NAMES:
        error = float(np.max(np.abs(identity[name][lo:]-close[name][lo:])))
        identity_errors[name] = error
        assert error < 2e-11, (name, error)
        if name in ('B', 'A', 'MA200-mix', 'MOM252-mix', 'Hold1', 'Hold2'):
            np.testing.assert_array_equal(identity[name][lo:], close[name][lo:])
    # Unique decision inputs only. T4-mix and T4-tb share the same attack scalar.
    unique = ['B', 'A', 'T4-tb', 'MA200-mix', 'MOM252-mix']
    raw_weights = {n: np.empty((DRAWS+1, len(dates))) for n in unique}
    for name in unique:
        raw_weights[name][0] = original[name]
    for i, row in enumerate(rows, 1):
        fake = raw.copy(); fake[lo:] = raw[lo:][row]
        w = targets(pd.Series(np.cumprod(1+fake), index=idx), T.t4_w(fake), E.rule_dd)
        for name in unique:
            raw_weights[name][i] = w[name][lo:, 0]
        if i % 100 == 0:
            print(f'raw-input rebuild {i}/{DRAWS}', file=sys.stderr, flush=True)
    actual = {}
    baseline, _, _ = gross_batch(original['B'][source, None], 'B', returns, trade)
    bw = window_metrics(baseline, dates)
    lower5 = {y: float(bw[y]['lower5'][0]) for y in (7, 10)}
    intervals = random_intervals(dates, RANDOM_WINDOWS, np.random.default_rng(seq_window))
    results, testing, check_errors = {}, [], []
    for mode in ('P1_target_blocks', 'P2_raw_return_blocks'):
        results[mode] = {}
        for name in NAMES:
            stamp = time.monotonic()
            if name in ('Hold1', 'Hold2'):
                x = np.ones((DRAWS+1, len(dates)))
            elif mode.startswith('P1'):
                x = np.vstack([original[name], original[name][rows]])
            else:
                x = raw_weights['T4-tb' if name == 'T4-mix' else name]
            executed = x[:, source].T
            # Bound transient allocations, while retaining every original curve.
            curves = np.empty(executed.shape)
            turns, ndays = np.empty(DRAWS+1), np.empty(DRAWS+1)
            for first in range(0, DRAWS+1, 200):
                last = min(first+200, DRAWS+1)
                c, tv, tc = gross_batch(executed[:, first:last], name, returns, trade)
                curves[:, first:last], turns[first:last], ndays[first:last] = c, tv, tc
            if name not in actual:
                actual[name] = curves[:, 0].copy()
            else:
                np.testing.assert_array_equal(curves[:, 0], actual[name])
            if name in ('Hold1', 'Hold2'):
                np.testing.assert_array_equal(curves, np.broadcast_to(curves[:, :1], curves.shape))
            # Reduction to the existing single-account implementation.
            p = np.array([make_positions([v], name)[0] for v in executed[:, 0]])
            single = account_windows(p, returns, trade, [0], [len(dates)-1],
                np.empty((0, 1), int), [], 1., fee=.001, record_paths=True)['paths'][:, 0]
            np.testing.assert_allclose(curves[:, 0], single, rtol=2e-12, atol=1e-12)
            for draw in (0, 1):
                ref = units_reference(executed[:, draw], name, returns, trade)
                error = float(np.max(np.abs(curves[:, draw]/ref-1)))
                check_errors.append(error)
                assert error < 2e-10, (mode, name, draw, error)
            stats = score(curves, dates, lower5)
            summary = {}
            for label, values in stats.items():
                null = values[1:]
                summary[label] = dict(observed=float(values[0]), null_min=float(null.min()),
                    null_p05=float(np.quantile(null, .05)), null_median=float(np.median(null)),
                    null_p95=float(np.quantile(null, .95)), null_max=float(null.max()),
                    null_score_sha256=digest(null), tail=tail_probability(values[0], null))
                if name in FAMILIES and label in ('calmar', 'weak_tail'):
                    testing.append(dict(mode=mode, name=name, metric=label, raw_p=summary[label]['tail']))
            results[mode][name] = dict(scores=summary, curve_matrix_sha256=digest(curves),
                original_trade_days_per_year=float(ndays[0]/((dates[-1]-dates[0]).days/365.25)),
                original_turnover_per_year=float(turns[0]/((dates[-1]-dates[0]).days/365.25)),
                original_close_mean_weight=float(x[0].mean()),
                null_close_mean_weight_range=[float(x[1:].mean(axis=1).min()), float(x[1:].mean(axis=1).max())],
                constant_control=name in ('Hold1', 'Hold2'))
            print(f'{mode} {name}: {DRAWS} paths checked ({time.monotonic()-stamp:.1f}s)', file=sys.stderr, flush=True)
    adjusted = holm_adjust([x['raw_p'] for x in testing])
    for row, padj in zip(testing, adjusted):
        row['holm_p'] = float(padj)
    surviving = {name: all(t['holm_p'] < .05 for t in testing if t['name'] == name) for name in FAMILIES}
    s, e, months = intervals
    random_summary = {}
    bvalues = actual['B'][e]/actual['B'][s]
    for name, c in actual.items():
        ratio = (c[e]/c[s])/bvalues
        random_summary[name] = dict(median_ratio=float(np.median(ratio)), lower5_ratio=float(np.quantile(ratio, .05)),
            upper95_ratio=float(np.quantile(ratio, .95)), fraction_above_B=float(np.mean(ratio > 1)),
            ratios_sha256=digest(ratio))
    after = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in watched}
    if before != after:
        raise RuntimeError('input code changed during run; mixed-version result cannot be interpreted')
    output = dict(protocol_commit='eacb47a', seed=SEED, draws=DRAWS, start=str(dates[0].date()), end=str(dates[-1].date()),
        year_blocks=[dict(year=int(y), rows=int(n)) for y, n in zip(years, lengths)],
        permutation_orders_sha256=digest(orders), permutation_rows_sha256=digest(rows),
        asset_returns_sha256=digest(returns), signal_returns_sha256=digest(raw), source_code_sha256=before,
        identity_signal_max_errors=identity_errors, max_units_reference_relative_error=max(check_errors),
        independent_reference_paths=len(check_errors), rolling_windows={str(y):dict(starts=bw[y]['starts'], nonoverlap=bw[y]['nonoverlap']) for y in (7,10)},
        results=results, family_tests=testing, timing_diagnostic_survives=surviving,
        random_intervals=dict(count=RANDOM_WINDOWS, minimum_months=36, maximum_months=180,
            pairs_sha256=digest(np.column_stack(intervals)), counts_by_month={str(m):int(np.count_nonzero(months == m)) for m in np.unique(months)}, rows=random_summary),
        limitations=['Conditional placebo assuming year-block exchangeability; regimes and stitching limit inference.',
          'P1 preserves close-target distribution, not necessarily executed exposure after KR-calendar collisions.',
          'P2 rebuilds signals so exposure distribution can change as well as timing.',
          'Gross full-history slices retain existing state; not fresh-start personal deposit/tax windows.',
          'No new OOS, future probabilities, past-500-search correction, account recommendation or operational change.'],
        next_questions=['Does a surviving timing mechanism improve the actual funding objective?',
                        'Can a limited preregistered combination exploit complementary timing without adding excessive turnover?'],
        diagnostics=logs)
    print('RESULT_JSON')
    print(json.dumps(output, ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
