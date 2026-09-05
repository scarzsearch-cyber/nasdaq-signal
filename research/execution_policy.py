"""F3 research-only, cash-first band policy (preregistered d6f5bde section 16).

No live orders, files, data access, or parameter search. Monetary fees, basis
and sale taxes reuse account_ledger.rebalance. A zero band is its exact daily
execution control, not a numerical approximation to a positive band.
"""
import numpy as np
from research.account_ledger import _rate, rebalance
from research.rebalance_accounting import _inputs


def _bands(band, count):
    b = np.asarray(band, float)
    if b.ndim == 0:
        b = np.full(count, float(b))
    if b.shape != (count,) or not np.isfinite(b).all() or (b < 0).any() or (b >= 1).any():
        raise ValueError('band must be scalar or one finite [0,1) value per account')
    return b


def _attack_index(value, assets):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or not 0 <= value < assets:
        raise ValueError('attack_index must identify one asset')
    return int(value)


def _exposure_gap(held, cash, targets, attack_index):
    """Actual total-wealth weights; idle cash is an extra zero-target asset."""
    total = held.sum(axis=1)+cash
    weights = np.divide(held, total[:, None], out=np.zeros_like(held), where=total[:, None] > 0)
    idle = np.divide(cash, total, out=np.zeros_like(cash), where=total > 0)
    gap = (np.abs(weights-targets).sum(axis=1)+idle)/2
    return weights[:, attack_index], np.where(total > 0, gap, 0.)


def policy_trade(held, basis, cash, targets, fee=.001, tax_rate=0., band=.10, attack_index=0):
    """One eligible execution event, possibly a no-sale cash-only purchase.

    The hypothetical cash purchase is only a trigger calculation. A full
    rebalance starts from ORIGINAL holdings/basis/cash, never double-charged.
    The supplied parent's exact zero attack target overrides a positive band.
    No forced full-attack override exists. Does not mutate input arrays.
    """
    fee, tax_rate = _rate(fee, 'fee'), _rate(tax_rate, 'tax_rate')
    h, b, p = (np.asarray(x, float) for x in (held, basis, targets))
    c = np.asarray(cash, float)
    if (h.ndim != 2 or not h.size or b.shape != h.shape or p.shape != h.shape or c.shape != (len(h),)):
        raise ValueError('inconsistent nonempty account/asset shapes')
    if any(not np.isfinite(x).all() or (x < 0).any() for x in (h, b, c, p)):
        raise ValueError('holdings, basis, cash and targets must be finite nonnegative')
    if not np.allclose(p.sum(axis=1), 1., rtol=0, atol=1e-12):
        raise ValueError('targets must sum to one')
    bands = _bands(band, len(h))
    attack_index = _attack_index(attack_index, h.shape[1])
    wealth = h.sum(axis=1)+c
    amount = c/(1+fee)
    net = h.sum(axis=1)+amount
    deficit = np.maximum(net[:, None]*p-h, 0.)
    total_deficit = deficit.sum(axis=1)
    if np.any((amount > 0) & (total_deficit <= 0)):
        raise ArithmeticError('positive deposit has no purchase deficit')
    proportion = np.divide(deficit, total_deficit[:, None], out=np.zeros_like(h),
                           where=total_deficit[:, None] > 0)
    bought = amount[:, None]*proportion
    hypothetical = h+bought
    _, hypothetical_gap = _exposure_gap(hypothetical, np.zeros(len(h)), p, attack_index)
    forced = (p[:, attack_index] == 0) & (h[:, attack_index] > 0)
    full = (bands == 0) | (hypothetical_gap > bands) | forced
    q = dict(held=hypothetical, basis=np.where(h > 0, b, 0.)+bought*(1+fee),
             cash=np.zeros(len(h)), taxes=np.zeros(len(h)), fees=fee*bought.sum(axis=1),
             sold=np.zeros_like(h), bought=bought, realized=np.zeros_like(h))
    if full.any():
        selected = rebalance(h[full], b[full], c[full], p[full], fee, tax_rate)
        for key in q:
            q[key][full] = selected[key]
    residual = wealth-q['held'].sum(axis=1)-q['cash']-q['fees']-q['taxes']
    if not np.all(np.abs(residual) <= 1e-10*np.maximum(wealth, 1.)):
        raise ArithmeticError('policy trade does not conserve cash')
    moved = (q['sold']+q['bought']).sum(axis=1)
    q.update(full_rebalance=full, forced_defense=forced, hypothetical_gap=hypothetical_gap,
             traded=moved > wealth*1e-12,
             turnover=np.divide(moved, 2*wealth, out=np.zeros(len(h)), where=wealth > 0))
    return q


def account_windows(positions, asset_returns, trade_days, starts, ends,
                    deposit_days, deposits, initial, fee=.001, tax_rate=0.,
                    distribution_rates=None, record_paths=False, band=.10, attack_index=0):
    """Fresh independent F3 accounts, not ratios of an inherited-state curve.

    Funding/valuation order exactly follows account_ledger.account_windows.
    Cash arrives after valuation/distribution; only the next eligible event
    invests it. Initial assets are already invested, no entry or terminal fee.
    Diagnostics refer to actual pre-return holdings; internal basket trades,
    whole-share rounding and distribution reinvestment orders are not counted.
    """
    p, r = _inputs(positions, asset_returns)
    if (r <= -1.).any():
        raise ValueError('positive asset values required; liquidation is out of scope')
    fee, tax_rate = _rate(fee, 'fee'), _rate(tax_rate, 'tax_rate')
    mask = np.asarray(trade_days)
    if mask.shape != (len(p),) or mask.dtype.kind != 'b':
        raise ValueError('trade_days must be a same-length boolean array')
    s, e, d = np.asarray(starts), np.asarray(ends), np.asarray(deposit_days)
    if (s.ndim != 1 or not len(s) or e.shape != s.shape or s.dtype.kind not in 'iu' or
            e.dtype.kind not in 'iu' or (s < 0).any() or (e < s).any() or (e >= len(p)).any()):
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
    bands = _bands(band, len(s))
    attack_index = _attack_index(attack_index, p.shape[1])
    span = int(np.max(e-s))
    pay = np.zeros((span+1, len(s)))
    cols = np.broadcast_to(np.arange(len(s)), d.shape)
    np.add.at(pay, ((d-s).ravel(), cols.ravel()), money.ravel())
    h = initial[:, None]*p[s]
    b, cash = h.copy(), np.zeros(len(s))
    taxes, fees = np.zeros(len(s)), np.zeros(len(s))
    days, turns, exposure, maxgap = (np.zeros(len(s)) for _ in range(4))
    forced_violations, cash_violations = np.zeros(len(s), int), np.zeros(len(s), int)
    paths = np.empty((span+1, len(s))) if record_paths else None
    if paths is not None:
        paths[0] = initial
    for offset in range(1, span+1):
        active = s+offset <= e
        day = np.minimum(s+offset, e)
        eligible = active & mask[day] & ((h.sum(axis=1)+cash) > 0)
        if eligible.any():
            q = policy_trade(h[eligible], b[eligible], cash[eligible], p[day[eligible]],
                             fee, tax_rate, bands[eligible], attack_index)
            h[eligible], b[eligible], cash[eligible] = q['held'], q['basis'], q['cash']
            taxes[eligible] += q['taxes']; fees[eligible] += q['fees']
            days[eligible] += q['traded']; turns[eligible] += q['turnover']
            forced_violations[eligible] += (p[day[eligible], attack_index] == 0) & (q['held'][:, attack_index] != 0)
            cash_violations[eligible] += q['cash'] != 0
        attack, gap = _exposure_gap(h, cash, p[day], attack_index)
        exposure += np.where(active, attack, 0.)
        maxgap = np.maximum(maxgap, np.where(active, gap, 0.))
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
                contributions=money.sum(axis=0), paths=paths, trade_days=days,
                turnover=turns, mean_attack_exposure=exposure/np.maximum(e-s, 1),
                max_target_gap=maxgap, forced_defense_violations=forced_violations,
                uninvested_cash_violations=cash_violations,
                closed_day_trade_violations=np.zeros(len(s), int))


def gross_batch(weights, returns, trade_days, fee=.001, band=.10, attack_index=0, safe_index=1):
    """Parallel no-deposit/no-tax paths with real holdings; band scalar/vector.

    weights: dates x paths; all non-attack weight goes to safe_index. First
    return is zero, exactly as the existing F1 monetary gross diagnostic.
    """
    w, r, mask = np.asarray(weights, float), np.asarray(returns, float), np.asarray(trade_days)
    fee = _rate(fee, 'fee')
    if (w.ndim != 2 or not w.size or r.ndim != 2 or len(r) != len(w) or not r.shape[1] or
            mask.shape != (len(w),) or mask.dtype.kind != 'b' or not np.isfinite(w).all() or
            (w < 0).any() or (w > 1).any() or not np.isfinite(r).all() or (r <= -1).any()):
        raise ValueError('invalid gross batch inputs')
    attack_index = _attack_index(attack_index, r.shape[1])
    safe_index = _attack_index(safe_index, r.shape[1])
    if safe_index == attack_index:
        raise ValueError('distinct attack and safe assets required')
    bands = _bands(band, w.shape[1])
    def positions(row):
        p = np.zeros((w.shape[1], r.shape[1]))
        p[:, attack_index] = row; p[:, safe_index] = 1-row
        return p
    h = positions(w[0])
    curves = np.ones(w.shape)
    cash = np.zeros(w.shape[1])
    days, turns, exposure, maxgap = (np.zeros(w.shape[1]) for _ in range(4))
    forced_violations = np.zeros(w.shape[1], int)
    for t in range(1, len(w)):
        p = positions(w[t])
        if mask[t]:
            q = policy_trade(h, h, cash, p, fee, 0., bands, attack_index)
            h = q['held']
            turns += q['turnover']; days += q['traded']
            forced_violations += (p[:, attack_index] == 0) & (h[:, attack_index] != 0)
        attack, gap = _exposure_gap(h, cash, p, attack_index)
        exposure += attack; maxgap = np.maximum(maxgap, gap)
        h *= 1+r[t]
        curves[t] = h.sum(axis=1)
    if not np.isfinite(curves).all() or (curves <= 0).any():
        raise ArithmeticError('invalid gross path')
    return dict(curves=curves, turnover=turns, trade_days=days,
                mean_attack_exposure=exposure/max(len(w)-1, 1), max_target_gap=maxgap,
                forced_defense_violations=forced_violations,
                uninvested_cash_violations=np.zeros(w.shape[1], int),
                closed_day_trade_violations=np.zeros(w.shape[1], int))
