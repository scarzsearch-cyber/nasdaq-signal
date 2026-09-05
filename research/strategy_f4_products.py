"""F4-B read-only real-price/proxy bridge; protocol 655173a, not a forecast.

KR opening prices versus last knowable foreign close are NOT synchronous quotes.
Returns are already distribution-adjusted; no second ETF expense deduction.
"""
import contextlib
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'research'), str(ROOT/'deploy')]
import numpy as np
import pandas as pd
from research import basket_accounting as B
from research import strategy_f4_basket as F4
from research.account_ledger import account_windows as aggregate_windows
from audit.test_account_ledger import trade_reference

CODES = ['418660', '458730', '305080', '411060']
POLICIES = {'C2': 0., 'C3': .02}
START, END = '2023-06-20', '2026-08-28'
WATCHED = list(dict.fromkeys(F4.WATCHED+['research/strategy_f4_products.py',
    'audit/test_f4_products.py', 'hist_tiger.py', 'hist_krreal.py']))


def dates_checked(values):
    d = pd.DatetimeIndex(values)
    if not len(d) or d.hasnans or not d.is_unique or not d.is_monotonic_increasing:
        raise ValueError('requires unique ordered finite dates')
    return d


def adjusted_prices(frame):
    """Validate before adjustment; two explicitly different local CSV schemas."""
    dates_checked(frame.index)
    cols = ['Open', 'Close', 'AdjClose'] if 'AdjClose' in frame else ['Open', 'Close', 'Raw']
    if not all(k in frame for k in cols):
        raise ValueError('unknown price-adjustment schema')
    values = frame[cols].to_numpy(float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError('nonfinite/nonpositive price')
    if 'AdjClose' in frame:
        factor, close = frame.AdjClose/frame.Close, frame.AdjClose
    else:
        factor, close = frame.Close/frame.Raw, frame.Close
    out = pd.DataFrame(dict(open=frame.Open*factor, close=close), index=frame.index)
    if not np.isfinite(out.to_numpy()).all() or (out.to_numpy() <= 0).any():
        raise ValueError('nonfinite/nonpositive adjusted price')
    return out


def known_sources(foreign_dates, openings):
    """Strictly earlier date, never same-date US close at the KR opening."""
    foreign_dates, openings = dates_checked(foreign_dates), dates_checked(openings)
    out = foreign_dates.searchsorted(openings, side='left')-1
    if (out < 0).any():
        raise ValueError('no earlier known foreign observation')
    # Independent forward walk, not another searchsorted expression.
    forward, j = [], -1
    for d in openings:
        while j+1 < len(foreign_dates) and foreign_dates[j+1] < d:
            j += 1
        forward.append(j)
    np.testing.assert_array_equal(out, forward)
    return out


def target(w):
    return np.array([w, .4*(1-w), .4*(1-w), .2*(1-w)])


def calendar_discrepancy(price_dates, calendar_dates, diagnostic=False):
    """A missing index observation is not proof of an exchange holiday.

    Strict mode remains failed. Diagnostic mode reports, never certifies, the
    same preselected common product-price dates without mutating raw inputs.
    """
    price_dates, calendar_dates = dates_checked(price_dates), dates_checked(calendar_dates)
    extra = price_dates.difference(calendar_dates)
    if len(extra) and not diagnostic:
        raise ValueError('product price dates absent from reference calendar: '+str(extra))
    missing = calendar_dates.difference(price_dates)
    if len(missing) and not diagnostic:
        raise ValueError('reference-calendar dates absent from product prices: '+str(missing))
    return [str(d.date()) for d in extra]


def forward_units(prices, w, review, fee, threshold):
    """Trade at opening j, then mark at opening j+1. No final-opening order."""
    units = target(w[0])/prices[0]
    basis = target(w[0]); curve = [1.]; traded = []; fees = 0.
    for j in range(len(prices)-1):
        values = units*prices[j]; total = float(sum(values))
        gap = max(abs(values/total-target(w[j])))
        if j and (w[j] != w[j-1] or (not w[j] and review[j] and gap > threshold)):
            nh, basis, f, tax = trade_reference(values, basis, 0., target(w[j]), fee, 0.)
            assert tax == 0
            if sum(abs(nh-values)) > total*1e-12:
                traded.append(j)
            units = nh/prices[j]; fees += f
        curve.append(float(sum(units*prices[j+1])))
    return np.array(curve), traded, fees


def evaluate(prices, dates, w, review, fee=.001, threshold=0.):
    prices, w, review = np.asarray(prices, float), np.asarray(w, float), np.asarray(review)
    if prices.shape != (len(dates), 4) or len(dates) < 2:
        raise ValueError('four prices per date and at least two observations required')
    dates = dates_checked(dates)
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError('invalid positive prices')
    if w.shape != (len(dates),) or not np.isin(w, [0., 1.]).all():
        raise ValueError('binary weights required')
    if review.shape != w.shape or review.dtype.kind != 'b':
        raise ValueError('boolean review mask required')
    # End-labelled open-to-open returns belong to the preceding opening state.
    r = np.vstack([np.zeros(4), prices[1:]/prices[:-1]-1])
    eff = np.r_[w[0], w[:-1]]
    checks = np.r_[False, review[:-1]]
    out = B.account_windows(eff, r, np.ones(len(dates), bool), checks,
          [0], [len(dates)-1], np.empty((0, 1), int), [], 1., fee=fee,
          review_threshold=threshold, record_paths=True)
    ref, traded, fees = forward_units(prices, w, review, fee, threshold)
    curve = out['paths'][:, 0]
    error = float(np.max(abs(curve/ref-1)))
    assert error < 2e-11
    assert len(traded) == out['trade_count'][0]
    np.testing.assert_allclose(out['fees'][0], fees, rtol=2e-11, atol=1e-14)
    if len(curve) == 2:
        # One return cannot estimate sample volatility (ddof=1). Do not turn
        # an undefined statistic into zero or let NaN leak into evidence JSON.
        years = (dates[-1]-dates[0]).days/365.25
        result = dict(cagr_pct=float((curve[-1]**(1/years)-1)*100),
            mdd_pct=float(np.min(curve/np.maximum.accumulate(curve)-1)*100),
            volatility_pct=None, volatility_unavailable_reason='only one return',
            trade_days_per_year=float(len(traded)/years),
            curve_sha256=F4.F.digest(curve), final=float(curve[-1]))
    else:
        result = F4.summarize(curve, dates, len(traded))
    result.update(independent_max_relative_error=error,
        fees=float(fees), actual_trade_dates=[str(dates[j].date()) for j in traded],
        terminal_signal_change_not_traded=bool(w[-1] != w[-2]))
    return result, curve


def material(diagnostic_calendar=False):
    logs = io.StringIO()
    with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
        import hist_krreal as R
        import hist_korea as K
        import hist_defasset as DA
        m = F4.load_material()
        _, fullidx, lo, _, _, _, close, _, _, _, _ = F4.F.load_material()
        signal, _ = R.signals(-.16)
        raw = {code: pd.read_csv(ROOT/f'data/hist/kr_{code}_KS.csv', parse_dates=['Date']).set_index('Date')
               for code in CODES}
        real = {code: adjusted_prices(frame) for code, frame in raw.items()}
        dates = real[CODES[0]].index
        for code in CODES[1:]:
            dates = dates.intersection(real[code].index)
        dates = dates[(dates >= START) & (dates <= END)]
        expected = K.kr_caldays(); expected = expected[(expected >= START) & (expected <= END)]
        missing = {code: [str(d.date()) for d in expected.difference(real[code].index)] for code in CODES}
        extra = calendar_discrepancy(dates, expected, diagnostic_calendar)
        pp = np.cumprod(1+m['returns'], axis=0)
        ps = known_sources(m['dates'], dates)
        proxy = pp[ps]/pp[ps[0]]
        sources = known_sources(signal.index, dates)
        w = signal.to_numpy()[sources]
        anchor = -1; known = []
        for d, state in signal.items():
            if state: anchor = -1
            elif anchor < 0: anchor = int(d.to_datetime64().astype('datetime64[D]').astype(int))
            known.append(anchor)
        anchors = np.asarray(known)[sources]
        review = B.review_schedule(dates.to_numpy(), np.ones(len(dates), bool), anchors, 'signal30')
        np.testing.assert_array_equal(review, F4.schedule_reference(dates, np.ones(len(dates), bool), anchors, 'signal30'))
        original = close['B'][known_sources(fullidx, dates), 0]
        different = np.flatnonzero(original != w)
        prices = {basis: np.column_stack([real[c][basis].reindex(dates).to_numpy() for c in CODES])
                  for basis in ('open', 'close')}
        prices = {k: v/v[0] for k, v in prices.items()}
        # Independent legacy C0 reduction, including original internal basket fee.
        oldcurve, oldhold, _ = R.run_real(-.16, start=START, slip=0., cost=0., defmix=True)
        ki, rl, rd = R.legs_real(START, True)
        oldr = np.column_stack([rl.reindex(dates).to_numpy(), rd.reindex(dates).to_numpy()])
        p = np.column_stack([np.r_[w[0], w[:-1]], 1-np.r_[w[0], w[:-1]]])
        out = aggregate_windows(p, oldr, np.ones(len(dates), bool), [0], [len(dates)-1],
                                np.empty((0, 1), int), [], 1., fee=0., record_paths=True)
        np.testing.assert_array_equal(oldhold.reindex(dates).to_numpy(), w)
        reduction = float(np.max(abs(out['paths'][:, 0]/oldcurve.reindex(dates).to_numpy()-1)))
        assert reduction < 2e-11
        # Explicit schema bridge to the existing real-open loaders.
        for code in CODES:
            np.testing.assert_allclose(real[code]['open'].reindex(dates), DA.kr_tr_open(code).reindex(dates), rtol=0, atol=0)
    return dict(dates=dates, proxy=proxy, real=prices, w=w, review=review,
        signal_sources=signal.index[sources], price_sources=m['dates'][ps],
        missing=missing, product_dates_absent_from_reference_calendar=extra,
        signal_disagreements=[str(dates[j].date()) for j in different],
        legacy_reduction_error=reduction, logs=logs.getvalue())


def leg_diagnostics(real, proxy, dates):
    a, b = real[1:]/real[:-1]-1, proxy[1:]/proxy[:-1]-1
    diff = a-b; years = (dates[-1]-dates[0]).days/365.25
    annual = []
    for year in sorted(set(dates.year)):
        sel = np.flatnonzero(dates.year == year); begin = max(0, sel[0]-1); end = sel[-1]
        ar, br = real[end]/real[begin]-1, proxy[end]/proxy[begin]-1
        annual.append(dict(year=int(year), partial=bool(year in (dates[0].year, dates[-1].year)),
            start=str(dates[begin].date()), end=str(dates[end].date()), real_return=float(ar), proxy_return=float(br)))
    top = np.argsort(abs(diff))[-10:][::-1]
    return dict(real_cagr_pct=float((real[-1]**(1/years)-1)*100),
        proxy_cagr_pct=float((proxy[-1]**(1/years)-1)*100),
        final_real_to_proxy=float(real[-1]/proxy[-1]),
        nonsynchronous_residual_volatility_pct=float(np.std(diff, ddof=1)*np.sqrt(252)*100),
        daily_correlation=float(np.corrcoef(a, b)[0, 1]),
        residual_abs_over_5pp_count=int(np.count_nonzero(abs(diff) > .05)), annual=annual,
        largest_residuals=[dict(date=str(dates[j+1].date()), real=float(a[j]), proxy=float(b[j]), residual=float(diff[j])) for j in top])


def hashes():
    names = WATCHED+['qqq_us_d.csv', 'qld_us_d.csv', 'schd_us_d.csv']
    names += [str(p.relative_to(ROOT)).replace('\\', '/') for p in sorted((ROOT/'data/hist').glob('*.csv'))]
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names}


def main(diagnostic_calendar=False):
    before = hashes(); m = material(diagnostic_calendar); dates = m['dates']
    results, curves = {}, {}
    def run(name, prices, fee, threshold):
        results[name], curves[name] = evaluate(prices, dates, m['w'], m['review'], fee, threshold)
    for condition, fee in [('base', .001), ('cost2', .002)]:
        for policy, threshold in POLICIES.items():
            run(condition+'_'+policy+'_proxy', m['proxy'], fee, threshold)
            run(condition+'_'+policy+'_real_open', m['real']['open'], fee, threshold)
    for j, code in enumerate(CODES):
        prices = m['proxy'].copy(); prices[:, j] = m['real']['open'][:, j]
        run('base_C2_only_'+code+'_real', prices, .001, 0.)
    run('base_C2_real_close', m['real']['close'], .001, 0.)
    for row in results.values():
        row['relative_to_base_C2_proxy_final'] = row['final']/results['base_C2_proxy']['final']
    assert before == hashes(), 'inputs changed during run'
    output = dict(protocol_commit='655173a', start=str(dates[0].date()), end=str(dates[-1].date()),
        rows=len(dates), source_sha256=before, missing_KR_dates=m['missing'],
        calendar_addendum_commit='d0d7ed6', diagnostic_calendar=diagnostic_calendar,
        product_dates_absent_from_reference_calendar=m['product_dates_absent_from_reference_calendar'],
        coverage_complete=not (any(m['missing'].values()) or m['product_dates_absent_from_reference_calendar']),
        signal_disagreements=m['signal_disagreements'],
        legacy_zero_external_cost_reduction_error=m['legacy_reduction_error'],
        source_price_age_calendar_days=dict(minimum=int((dates-m['price_sources']).days.min()),
            maximum=int((dates-m['price_sources']).days.max())),
        signal_dates_strictly_before_open=bool((m['signal_sources'] < dates).all()),
        price_dates_strictly_before_open=bool((m['price_sources'] < dates).all()),
        price_sources_sha256=F4.F.digest(m['price_sources'].to_numpy().astype('int64')),
        signal_sha256=F4.F.digest(m['w']), results=results,
        legs={code: leg_diagnostics(m['real']['open'][:, j], m['proxy'][:, j], dates) for j, code in enumerate(CODES)},
        actual_orders=False, limitations=['Non-synchronous foreign-close versus KR-opening residual, not a fee/official tracking-error estimate.',
          'Three-year overlap is not seven/ten-year real-product evidence or new OOS.',
          'Fractional adjusted units, not cash distribution settlement/tax NAV/integer broker orders.',
          'Diagnostic calendar mode does not resolve missing reference-calendar observations or certify prior account results.',
          'Missing observations can hide intragap drawdowns and trade opportunities; sqrt252 volatility/correlation use observed intervals, not a complete daily-price record.',
          'No calibration of historical proxy, frozen rule, personal funding plan or future return.'],
        next_question='Which residual comes from price timing/data adjustment versus product exposure before extrapolating goal values?')
    print('RESULT_JSON'+json.dumps(output, ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--diagnostic-calendar', action='store_true',
        help='Report calendar discrepancies on the preregistered product intersection; not a validation pass.')
    main(ap.parse_args().diagnostic_calendar)
