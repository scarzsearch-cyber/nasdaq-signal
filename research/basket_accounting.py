"""F4-A binary-strategy, four-asset research ledger; protocol bbcc607.

Not live orders, exact UI orders, actual ETF NAV taxation, or a T4 simulator.
Returns include distributions already. Fractional units and economic-gain tax.
"""
import numpy as np
from research.account_ledger import _rate, rebalance


def review_schedule(dates, eligible, anchors, rule='monthly'):
    """Calendar checks on eligible valuation rows; anchors are known signal days.

    dates are the KR opening-clock dates represented by each valuation row.
    An anchor < 0 means attack. A delayed/holiday check rolls to the next
    eligible row; same-anchor payments do not reset its thirty-day clock.
    The caller maps actual KR openings to the coarser US valuation grid.
    """
    dates, a, m = np.asarray(dates), np.asarray(anchors), np.asarray(eligible)
    if (dates.ndim != 1 or not len(dates) or dates.dtype.kind != 'M' or
            np.isnat(dates).any() or (dates[1:] < dates[:-1]).any() or
            a.shape != dates.shape or a.dtype.kind not in 'iu' or
            m.shape != dates.shape or m.dtype.kind != 'b'):
        raise ValueError('invalid ordered dates, integer anchors or boolean eligibility')
    if rule not in ('monthly', 'signal30'):
        raise ValueError('unknown review rule')
    day = dates.astype('datetime64[D]').astype(np.int64)
    if ((a >= 0) & (a > day)).any():
        raise ValueError('defense anchor is in the future')
    month = dates.astype('datetime64[M]').astype(np.int64)
    out = np.zeros(len(dates), bool)
    last_month, last_anchor, last_cycle = month[0], a[0], 0
    if a[0] >= 0:
        last_cycle = (day[0]-a[0])//30
    for i in range(1, len(day)):
        if not m[i]:
            continue
        if rule == 'monthly':
            out[i] = month[i] != last_month and a[i] >= 0
            last_month = month[i]
        else:
            cycle = (day[i]-a[i])//30 if a[i] >= 0 else 0
            prior = last_cycle if a[i] == last_anchor else 0
            out[i] = a[i] >= 0 and cycle >= 1 and cycle > prior
            last_anchor, last_cycle = a[i], cycle
    return out


def account_windows(attack, asset_returns, trade_days, review_days, starts, ends,
                    deposit_days, deposits, initial, fee=.001, tax_rate=0.,
                    distribution_rates=None, review_threshold=0., record_paths=False):
    """Fresh binary B windows with separately held attack/dividend/bond/gold.

    Full rebalance on a changed executed state or cash investment. Otherwise
    review only while defensive and max absolute component deviation strictly
    exceeds threshold. This threshold is NOT the UI's per-leg integer orders.
    Deposits follow valuation, invest on next eligible row, and do not move
    the review clock. No terminal liquidation or initial purchase charge.
    """
    w, r = np.asarray(attack, float), np.asarray(asset_returns, float)
    if (w.ndim != 1 or not len(w) or r.shape != (len(w), 4) or
            not np.isfinite(w).all() or not np.isin(w, [0., 1.]).all() or
            not np.isfinite(r).all() or (r <= -1).any()):
        raise ValueError('requires binary attack and finite positive four-asset returns')
    mask, review = np.asarray(trade_days), np.asarray(review_days)
    if any(x.shape != w.shape or x.dtype.kind != 'b' for x in (mask, review)):
        raise ValueError('trade/review masks must be same-length boolean arrays')
    if (review & ~mask).any() or ((w[1:] != w[:-1]) & ~mask[1:]).any():
        raise ValueError('state changes and reviews require an eligible row')
    fee, tax_rate = _rate(fee, 'fee'), _rate(tax_rate, 'tax_rate')
    threshold = _rate(review_threshold, 'review_threshold')
    s, e, d = np.asarray(starts), np.asarray(ends), np.asarray(deposit_days)
    if (s.ndim != 1 or not len(s) or e.shape != s.shape or
            s.dtype.kind not in 'iu' or e.dtype.kind not in 'iu' or
            (s < 0).any() or (e < s).any() or (e >= len(w)).any()):
        raise ValueError('invalid integer window endpoints')
    if d.ndim != 2 or d.shape[1] != len(s) or d.dtype.kind not in 'iu':
        raise ValueError('deposit days must be integer payments x windows')
    if not np.all((d > s) & (d <= e)):
        raise ValueError('deposit outside its window')
    money = np.asarray(deposits, float)
    if money.ndim == 1 and money.shape == (len(d),):
        money = np.broadcast_to(money[:, None], d.shape)
    if money.shape != d.shape or not np.isfinite(money).all() or (money < 0).any():
        raise ValueError('invalid nonnegative deposits')
    initial = np.broadcast_to(np.asarray(initial, float), s.shape)
    if not np.isfinite(initial).all() or (initial < 0).any():
        raise ValueError('invalid initial value')
    dist = np.zeros_like(r) if distribution_rates is None else np.asarray(distribution_rates, float)
    if dist.shape != r.shape or not np.isfinite(dist).all() or (dist < 0).any() or (dist >= 1).any():
        raise ValueError('invalid distribution rates')
    p = np.column_stack([w, (1-w)*.4, (1-w)*.4, (1-w)*.2])
    span = int(np.max(e-s))
    pay = np.zeros((span+1, len(s)))
    cols = np.broadcast_to(np.arange(len(s)), d.shape)
    np.add.at(pay, ((d-s).ravel(), cols.ravel()), money.ravel())
    h = initial[:, None]*p[s]
    b, cash = h.copy(), np.zeros(len(s))
    fees, taxes = np.zeros(len(s)), np.zeros(len(s))
    counts = {k: np.zeros(len(s), int) for k in ('trade_count', 'review_trade_count',
               'cash_trade_count', 'switch_trade_count')}
    paths = np.empty((span+1, len(s))) if record_paths else None
    if paths is not None:
        paths[0] = initial
    for offset in range(1, span+1):
        active = s+offset <= e
        day = np.minimum(s+offset, e)
        total = h.sum(axis=1)+cash
        weights = np.divide(h, total[:, None], out=np.zeros_like(h), where=total[:, None] > 0)
        gap = np.max(np.abs(weights-p[day]), axis=1)
        changed = w[day] != w[day-1]
        checked = (w[day] == 0) & review[day] & (gap > threshold)
        funded = cash > 0
        do = active & mask[day] & (total > 0) & (changed | funded | checked)
        if do.any():
            q = rebalance(h[do], b[do], cash[do], p[day[do]], fee, tax_rate)
            traded = (q['sold']+q['bought']).sum(axis=1) > total[do]*1e-12
            counts['trade_count'][do] += traded
            counts['review_trade_count'][do] += traded & checked[do]
            counts['cash_trade_count'][do] += traded & funded[do]
            counts['switch_trade_count'][do] += traded & changed[do]
            h[do], b[do], cash[do] = q['held'], q['basis'], q['cash']
            fees[do] += q['fees']; taxes[do] += q['taxes']
        h *= 1+np.where(active[:, None], r[day], 0.)
        gross_dist = np.where(active[:, None], h*dist[day], 0.)
        due = gross_dist*tax_rate
        h -= due; b += gross_dist-due
        taxes += due.sum(axis=1)
        cash += pay[offset]
        if paths is not None:
            paths[offset] = h.sum(axis=1)+cash
    wealth = h.sum(axis=1)+cash
    if not np.isfinite(wealth).all():
        raise ArithmeticError('nonfinite account wealth')
    return dict(wealth=wealth, held=h, basis=b, cash=cash, fees=fees, taxes=taxes,
                contributions=money.sum(axis=0), paths=paths, **counts)
