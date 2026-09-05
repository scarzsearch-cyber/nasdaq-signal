"""F1 preregistered eight-way USD accounting screen, not a strategy verdict.

Protocol: STRATEGY_RESEARCH_2026-09-05.md, commit a6430f0. Uses existing feeds
read-only; no portfolio inputs, account tax, deposits, broker actions or exports.
Prints JSON. This stage does NOT satisfy the protocol's KRW/account gates.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'research')]
os.chdir(ROOT)
import numpy as np
import pandas as pd
from research.rebalance_accounting import daily_turnover


def targets(px, t4, rule_dd):
    """Fixed F1 definitions. Returns weights [2x, mix, T-bill, 1x]."""
    n = len(px)
    ma = (px > px.rolling(200, min_periods=200).mean()).to_numpy(float)
    mom = (px/px.shift(252) > 1).to_numpy(float)
    weights = dict(B=rule_dd(px, -.16, -.16), A=rule_dd(px, -.16, -.11),
                   **{'T4-tb': t4, 'T4-mix': t4, 'MA200-mix': ma, 'MOM252-mix': mom})
    out = {}
    for name, w in weights.items():
        W = np.zeros((n, 4))
        W[:, 0] = w
        W[:, 2 if name == 'T4-tb' else 1] = 1-w
        out[name] = W
    out['Hold1'] = np.tile([0., 0., 0., 1.], (n, 1))
    out['Hold2'] = np.tile([1., 0., 0., 0.], (n, 1))
    return out


def execute(W, R, cost, lag=1):
    """Daily targets, lag >= 1. Currency-neutral; asset construction is separate."""
    if isinstance(lag, bool) or int(lag) != lag or lag < 1:
        raise ValueError('lag must be a positive whole trading-day count')
    lag = int(lag)
    if not np.isfinite(cost) or not 0 <= cost < 1:
        raise ValueError('cost must be in [0, 1)')
    p = np.empty_like(W)
    p[:lag] = W[0]
    p[lag:] = W[:-lag]
    turn = daily_turnover(p, R)
    daily = np.sum(p*R, axis=1)
    daily[0] = 0.
    curve = np.cumprod((1+daily)*(1-cost*turn))
    if not np.isfinite(curve).all() or (curve <= 0).any():
        raise ValueError('nonpositive/nonfinite curve; inspect separately, not a valid CAGR')
    return curve, turn


def currency_reference(W, R, cost, lag=1):
    """Independent amount ledger, deliberately not using daily_turnover."""
    held = [float(x) for x in W[0]]
    out = [1.]
    for i in range(1, len(W)):
        desired = W[max(0, i-lag)]
        total = sum(held)
        trade = sum(abs(total*float(w)-h) for w, h in zip(desired, held))/2
        invest = total-cost*trade
        held = [invest*float(w)*(1+float(r)) for w, r in zip(desired, R[i])]
        out.append(sum(held))
    return np.array(out)


def metrics(a, idx, turn):
    years = (idx[-1]-idx[0]).days/365.25
    cagr = (a[-1]/a[0])**(1/years)-1
    dd = a/np.maximum.accumulate(a)-1
    daily = a[1:]/a[:-1]-1
    return dict(cagr_pct=float(cagr*100), mdd_pct=float(dd.min()*100),
                volatility_pct=float(np.std(daily, ddof=1)*np.sqrt(252)*100),
                trades_per_year=float(np.count_nonzero(turn > 1e-10)/years),
                oneway_turnover_per_year=float(turn.sum()/years),
                curve_sha256=hashlib.sha256(a.astype('<f8').tobytes()).hexdigest())


def windows(curves, idx, years):
    starts = np.arange(len(idx))
    ends = idx.searchsorted(idx + pd.DateOffset(years=years))
    valid = ends < len(idx)
    starts, ends = starts[valid], ends[valid]
    if not len(starts):
        raise ValueError('no complete windows')
    # Count disjoint calendar windows, not rounded total-years/window length.
    count, previous = 0, -1
    for start, end in zip(starts, ends):
        if start >= previous:
            count += 1
            previous = int(end)
    baseline = curves['B'][ends]/curves['B'][starts]
    out = {}
    for name, a in curves.items():
        mult = a[ends]/a[starts]
        ratio = mult/baseline
        out[name] = dict(median_multiple=float(np.median(mult)),
                        lower5_multiple=float(np.quantile(mult, .05)),
                        minimum_multiple=float(mult.min()),
                        paired_median_ratio_to_B=float(np.median(ratio)),
                        paired_lower5_ratio_to_B=float(np.quantile(ratio, .05)),
                        paired_win_fraction_vs_B=float(np.mean(ratio > 1)),
                        paired_tie_fraction_vs_B=float(np.mean(ratio == 1)))
    return dict(years=years, starts=len(starts), nonoverlap_windows=count,
                first_start=str(idx[starts[0]].date()), last_start=str(idx[starts[-1]].date()), rows=out)


def main():
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        import hypo_gates as G
        import hypo_t4_real as T
        import eng_common as E
        E.selfcheck()
    idx = G.idx
    px = pd.Series(G.D['px'], index=idx)
    W = targets(px, T.t4_w(G.r_eq1), E.rule_dd)
    R = np.column_stack([np.nan_to_num(G.D['qldr']), np.nan_to_num(G.Dm['schdr']),
                         np.asarray(G.tb), np.asarray(G.r_eq1)])
    assert np.isfinite(R).all()
    runs = {}
    maxerr = 0.
    for cost, lag in ((.001, 1), (.002, 1), (.001, 2)):
        lo = idx.searchsorted(pd.Timestamp('2000-01-03'))
        dates = idx[lo:]
        curves, rows = {}, {}
        for name, weights in W.items():
            a, t = execute(weights[lo:], R[lo:], cost, lag)
            ref = currency_reference(weights[lo:], R[lo:], cost, lag)
            err = float(np.max(np.abs(a/ref-1)))
            maxerr = max(maxerr, err)
            assert err < 2e-11, (name, err)
            curves[name] = a
            rows[name] = metrics(a, dates, t)
        runs[f'cost{cost}_lag{lag}'] = dict(start=str(dates[0].date()), end=str(dates[-1].date()),
             rows=rows, windows={str(y): windows(curves, dates, y) for y in (7, 10)})
    # Older decades are stress diagnostics only: no whole-history wealth multiple.
    stress = {}
    for name, weights in W.items():
        a, t = execute(weights, R, .001)
        stress[name] = dict(mdd_pct=float(np.min(a/np.maximum.accumulate(a)-1)*100))
    identities = {}
    lo = idx.searchsorted(pd.Timestamp('2000-01-03'))
    for name, safe in [('B', R[:, 1]), ('A', R[:, 1]), ('T4-tb', R[:, 2])]:
        a, _ = execute(W[name][lo:], R[lo:], .001)
        reference = E.sim2(W[name][lo:, 0], R[lo:, 0], safe[lo:])
        identities[name] = float(np.max(np.abs(a/reference-1)))
        assert identities[name] < 1e-12
    print(json.dumps(dict(protocol_commit='a6430f0', scope='USD gross lump sum; no KRW/account verdict',
         max_relative_currency_ledger_error=maxerr, two_asset_identities=identities,
         returns_sha256=hashlib.sha256(R.astype('<f8').tobytes()).hexdigest(),
         runs=runs, expanded_stress=stress,
         limitations=['All historical data reused, not fresh OOS',
             'Only eight fixed F1 comparisons; not all possible strategies',
             'Rolling windows overlap; fractions are not future probabilities',
             'No KR holidays, deposits, taxes, bid/ask microstructure or ISA product substitution',
             'T4 daily rebalancing may be operationally impractical; turnover is not number of orders',
             'Sources/proxies remain uncertain; Hold1 is the existing index proxy without a new fee model'],
         next_questions=['Do differences survive matched KRW trade calendars and account ledgers?',
                         'Do the high-frequency signals retain value after real execution and tax costs?',
                         'Do 200 year-block shuffles distinguish signal alignment from exposure alone?'],
         diagnostics=log.getvalue()), ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
