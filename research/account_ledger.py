"""Research-only cash/cost-basis ledger; NOT exact Korean ETF taxation.

Preregistered in STRATEGY_RESEARCH_2026-09-05.md section 10 (0530932).
Targets already include execution lag. Fees are per bought/sold amount, not
the older proportional-wealth/half-L1 convention. Tax is positive economic
gain per asset, without loss offsets, tax-base NAV or income surtax. A basket
input remains a proxy: its internal trades are not magically accounted for.
No files, data feeds, broker access, or live strategy decisions here.
"""
import numpy as np
from research.rebalance_accounting import _inputs


def _rate(value, name):
    if not np.isscalar(value) or not np.isfinite(value) or not 0 <= value < 1:
        raise ValueError(name+' must be finite in [0, 1)')
    return float(value)


def rebalance(held, basis, cash, targets, fee=.001, tax_rate=.154):
    """Batch of independent fully invested, post-fee/post-tax target trades.

    Inputs held/basis/targets are accounts x assets; cash is accounts. Solve
    N + fee*sum(abs(N*p-held)) + sale_tax(N) = held.sum()+cash.
    Sale-tax cash raising is part of that SAME solution, not a later free sale.
    Average basis includes acquisition fees; disposal fees reduce realized gain.
    Each iteration expands the selling-asset set; at most K+1 sets are needed.
    """
    fee, tax_rate = _rate(fee, 'fee'), _rate(tax_rate, 'tax_rate')
    h, b, p = (np.asarray(x, float) for x in (held, basis, targets))
    c = np.asarray(cash, float)
    if (h.ndim != 2 or not h.size or b.shape != h.shape or p.shape != h.shape or
            c.shape != (len(h),)):
        raise ValueError('inconsistent nonempty account/asset shapes')
    if any(not np.isfinite(x).all() or (x < 0).any() for x in (h, b, c, p)):
        raise ValueError('holdings, basis, cash and targets must be finite nonnegative')
    if not np.allclose(p.sum(axis=1), 1., rtol=0, atol=1e-12):
        raise ValueError('targets must sum to one')
    value = h.sum(axis=1)
    wealth = value+c
    exact_no_trade = (c == 0) & np.all(h == wealth[:, None]*p, axis=1)
    basis_fraction = np.divide(b, h, out=np.zeros_like(h), where=h > 0)
    positive_gain = np.maximum(1-fee-basis_fraction, 0.)
    selling = h > wealth[:, None]*p
    for _ in range(h.shape[1]+3):
        sell_value = np.sum(np.where(selling, h, 0.), axis=1)
        sell_weight = np.sum(np.where(selling, p, 0.), axis=1)
        gain_value = np.sum(np.where(selling, positive_gain*h, 0.), axis=1)
        gain_weight = np.sum(np.where(selling, positive_gain*p, 0.), axis=1)
        net = ((wealth + fee*value - 2*fee*sell_value - tax_rate*gain_value) /
               (1+fee*(1-2*sell_weight)-tax_rate*gain_weight))
        net = np.where(exact_no_trade, wealth, np.clip(net, 0., wealth))
        # Net wealth cannot increase as omitted selling charges are added.
        # Preserve this monotone active set at floating-point breakpoints;
        # otherwise a zero-size sale can alternate between two equivalent sets.
        next_selling = selling | (h > net[:, None]*p)
        if np.array_equal(selling, next_selling):
            break
        selling = next_selling
    else:
        raise ArithmeticError('selling-set solution did not converge')
    # Unchanged holdings must not generate tiny "sales" from cancellation in
    # the formula. This exact identity is not a discretionary trade threshold.
    target_value = np.where(exact_no_trade[:, None], h, net[:, None]*p)
    sold = np.maximum(h-target_value, 0.)
    bought = np.maximum(target_value-h, 0.)
    fraction = np.divide(sold, h, out=np.zeros_like(h), where=h > 0)
    realized = sold*(1-fee)-fraction*b
    taxes = tax_rate*np.maximum(realized, 0.).sum(axis=1)
    fees = fee*(sold+bought).sum(axis=1)
    # Worthless positions have no value to retain or transfer to a new purchase.
    new_basis = np.where(h > 0, b*(1-fraction), 0.)+bought*(1+fee)
    residual = wealth-target_value.sum(axis=1)-taxes-fees
    if not np.all(np.abs(residual) <= 1e-10*np.maximum(wealth, 1.)):
        raise ArithmeticError('trade does not conserve cash')
    return dict(held=target_value, basis=new_basis, cash=np.zeros(len(h)),
                taxes=taxes, fees=fees, sold=sold, bought=bought, realized=realized)


def account_windows(positions, asset_returns, trade_days, starts, ends,
                    deposit_days, deposits, initial, fee=.001, tax_rate=0.,
                    distribution_rates=None, record_paths=False):
    """Batch independent windows; deposits arrive AFTER that day's valuation.

    Initial value is already invested at positions[start] and its basis equals
    that value. No start-row return/fee. Deposits wait in zero-interest cash
    until the next trade event. End-day deposits remain cash in market value.
    Total-return inputs ALREADY include distributions; only withholding is
    deducted and net reinvested distribution is added to asset cost basis.
    No terminal liquidation tax or ISA closure is applied.
    """
    p, r = _inputs(positions, asset_returns)
    if (r <= -1.).any():
        raise ValueError('account ledger requires positive asset values; handle liquidation separately')
    fee, tax_rate = _rate(fee, 'fee'), _rate(tax_rate, 'tax_rate')
    mask = np.asarray(trade_days)
    if mask.shape != (len(p),) or mask.dtype.kind != 'b':
        raise ValueError('trade_days must be a same-length boolean array')
    s, e = np.asarray(starts), np.asarray(ends)
    d = np.asarray(deposit_days)
    if (s.ndim != 1 or not len(s) or e.shape != s.shape or
            s.dtype.kind not in 'iu' or e.dtype.kind not in 'iu' or
            (s < 0).any() or (e < s).any() or (e >= len(p)).any()):
        raise ValueError('invalid integer window endpoints')
    if d.ndim != 2 or d.shape[1] != len(s) or d.dtype.kind not in 'iu':
        raise ValueError('deposit_days must be integer payments x windows')
    if not np.all((d > s) & (d <= e)):
        raise ValueError('deposit lies outside its window')
    money = np.asarray(deposits, float)
    if money.ndim == 1 and money.shape == (len(d),):
        money = np.broadcast_to(money[:, None], d.shape)
    if money.shape != d.shape or not np.isfinite(money).all() or (money < 0).any():
        raise ValueError('deposits must be nonnegative finite matching payments')
    initial = np.broadcast_to(np.asarray(initial, float), s.shape)
    if not np.isfinite(initial).all() or (initial < 0).any():
        raise ValueError('initial money must be finite nonnegative')
    dist = np.zeros_like(r) if distribution_rates is None else np.asarray(distribution_rates, float)
    if dist.shape != r.shape or not np.isfinite(dist).all() or (dist < 0).any() or (dist >= 1).any():
        raise ValueError('distribution rates must match returns and lie in [0,1)')
    span = int(np.max(e-s))
    pay = np.zeros((span+1, len(s)))
    cols = np.broadcast_to(np.arange(len(s)), d.shape)
    np.add.at(pay, ((d-s).ravel(), cols.ravel()), money.ravel())
    h = initial[:, None]*p[s]
    b, cash = h.copy(), np.zeros(len(s))
    taxes, fees = np.zeros(len(s)), np.zeros(len(s))
    paths = np.empty((span+1, len(s))) if record_paths else None
    if paths is not None:
        paths[0] = initial
    for offset in range(1, span+1):
        active = s+offset <= e
        day = np.minimum(s+offset, e)
        do_trade = active & mask[day] & ((h.sum(axis=1)+cash) > 0)
        if do_trade.any():
            q = rebalance(h[do_trade], b[do_trade], cash[do_trade], p[day[do_trade]], fee, tax_rate)
            h[do_trade], b[do_trade], cash[do_trade] = q['held'], q['basis'], q['cash']
            taxes[do_trade] += q['taxes']; fees[do_trade] += q['fees']
        h *= 1+np.where(active[:, None], r[day], 0.)
        b = np.where(h > 0, b, 0.)
        gross_dist = np.where(active[:, None], h*dist[day], 0.)
        due = gross_dist*tax_rate
        h -= due
        b += gross_dist-due
        taxes += due.sum(axis=1)
        cash += pay[offset]
        if paths is not None:
            paths[offset] = h.sum(axis=1)+cash
    wealth = h.sum(axis=1)+cash
    if not np.isfinite(wealth).all():
        raise ArithmeticError('nonfinite account wealth')
    return dict(wealth=wealth, held=h, basis=b, cash=cash, taxes=taxes, fees=fees,
                contributions=money.sum(axis=0), paths=paths)
