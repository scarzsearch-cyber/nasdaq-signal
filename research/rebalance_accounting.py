"""Fully-invested target portfolios: one-way turnover after price drift.

Pure accounting; no feeds, signals, account tax, deposits or file I/O. Callers
supply execution-day targets (apply signal lag beforehand). The first row is
already funded with no return/entry fee. Fees use the existing proportional
wealth deduction, cost * half-L1 turnover, not an exact per-order broker fee.
"""
import numpy as np


def _inputs(positions, asset_returns):
    """Validate only; do not fill unavailable asset returns or mutate callers."""
    p = np.asarray(positions, float)
    r = np.asarray(asset_returns, float)
    if p.ndim != 2 or not len(p) or not p.shape[1] or r.shape != p.shape:
        raise ValueError('positions and returns must be equal nonempty N x K arrays')
    if (not np.isfinite(p).all() or (p < -1e-12).any() or
            not np.allclose(p.sum(axis=1), 1., rtol=0., atol=1e-9)):
        raise ValueError('positions must be finite, nonnegative and sum to one')
    if not np.isfinite(r).all() or (r < -1.).any():
        raise ValueError('asset returns must be finite and at least -100%')
    return p, r


def daily_turnover(positions, asset_returns):
    """Turnover from pre-trade holdings to today's target, not target-to-target.

    Every day is rebalanced. Proportional fees preserve target weight ratios,
    so yesterday's target and return determine today's actual weights. Callers
    must net identical instruments (e.g. multiple T-bill sleeves). A zero-wealth
    path stays zero in the caller's cumprod; its undefined weights incur no fee.
    """
    p, r = _inputs(positions, asset_returns)
    before = p.copy()
    if len(p) > 1:
        held = p[:-1] * (1. + r[:-1])
        held[0] = p[0]  # Initial row return is deliberately not earned.
        wealth = held.sum(axis=1)
        if not np.isfinite(wealth).all():
            raise ValueError('nonfinite portfolio value')
        before[1:] = np.divide(held, wealth[:, None], out=p[1:].copy(),
                               where=wealth[:, None] > 0.)
    turn = .5 * np.abs(p - before).sum(axis=1)
    turn[0] = 0.
    return turn


def scheduled_path(positions, asset_returns, trade_days, cost=.001):
    """Return (wealth, one-way turnover) while holding between tradable rows.

    positions[t] is already the execution-day target, not a close-day signal.
    Only trade_days[t] permits a pre-return rebalance. The initial portfolio is
    positions[0], wealth 1, with row-zero return and entry fee both excluded.
    No deposits, distributions, withdrawals, tax or whole-share rounding here.
    """
    p, r = _inputs(positions, asset_returns)
    mask = np.asarray(trade_days)
    if mask.shape != (len(p),) or mask.dtype.kind != 'b':
        raise ValueError('trade_days must be a same-length boolean array')
    if not np.isfinite(cost) or not 0 <= cost < 1:
        raise ValueError('cost must be in [0, 1)')
    held = p[0].copy()
    out, turn = np.ones(len(p)), np.zeros(len(p))
    for i in range(1, len(p)):
        wealth = float(held.sum())
        if wealth <= 0:
            out[i:] = 0.
            break
        if mask[i]:
            turn[i] = .5 * float(np.abs(p[i]-held/wealth).sum())
            held = p[i] * (wealth*(1-cost*turn[i]))
        held *= 1+r[i]
        out[i] = held.sum()
    if not np.isfinite(out).all():
        raise ValueError('nonfinite portfolio value')
    return out, turn
