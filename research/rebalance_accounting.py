"""Daily, fully-invested target portfolios: one-way turnover after price drift.

Pure accounting; no feeds, signals, account tax, deposits or file I/O. Callers
supply execution-day targets (apply signal lag beforehand). The first row is
already funded with no return/entry fee. Fees use the existing proportional
wealth deduction, cost * half-L1 turnover, not an exact per-order broker fee.
"""
import numpy as np


def daily_turnover(positions, asset_returns):
    """Turnover from pre-trade holdings to today's target, not target-to-target.

    Every day is rebalanced. Proportional fees preserve target weight ratios,
    so yesterday's target and return determine today's actual weights. Callers
    must net identical instruments (e.g. multiple T-bill sleeves). A zero-wealth
    path stays zero in the caller's cumprod; its undefined weights incur no fee.
    """
    p = np.asarray(positions, float)
    r = np.asarray(asset_returns, float)
    if p.ndim != 2 or not len(p) or not p.shape[1] or r.shape != p.shape:
        raise ValueError('positions and returns must be equal nonempty N x K arrays')
    if (not np.isfinite(p).all() or (p < -1e-12).any() or
            not np.allclose(p.sum(axis=1), 1., rtol=0., atol=1e-9)):
        raise ValueError('positions must be finite, nonnegative and sum to one')
    if not np.isfinite(r).all() or (r < -1.).any():
        raise ValueError('asset returns must be finite and at least -100%')
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
