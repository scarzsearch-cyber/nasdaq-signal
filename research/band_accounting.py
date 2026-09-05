"""Legacy proportional-cost execution, with actual holdings between trades.

This repairs old execution diagnostics. It is NOT the F1/F2 exact monetary
fee/account engine. Targets must already be execution-lagged. No market data,
signals, tax, deposits, file writes, or operational strategy changes here.
"""
import numpy as np

from research.rebalance_accounting import _inputs


def banded_path(positions, asset_returns, trade_days, cost=.001, band=0.,
                trigger_asset=None, inclusive=False):
    """Hold quantities until an eligible target-distance trigger fires.

    Default distance is half-L1 across all actual asset weights. An explicit
    trigger_asset preserves an old attack-weight-only trigger; the OTHER assets
    also remain held between trades. At a trigger the full target is restored.
    Fees retain the legacy wealth * cost * half-L1 convention. Row zero is
    already funded, earns no return and incurs no entry fee. Zero wealth is
    absorbing. This routine never silently replaces missing returns with zero.
    """
    p, r = _inputs(positions, asset_returns)
    mask = np.asarray(trade_days)
    if mask.shape != (len(p),) or mask.dtype.kind != 'b':
        raise ValueError('trade_days must be a same-length boolean array')
    if not np.isfinite(cost) or not 0 <= cost < 1:
        raise ValueError('cost must be in [0, 1)')
    if not np.isfinite(band) or not 0 <= band <= 1:
        raise ValueError('band must be in [0, 1]')
    if not isinstance(inclusive, (bool, np.bool_)):
        raise ValueError('inclusive must be boolean')
    if trigger_asset is not None and (isinstance(trigger_asset, (bool, np.bool_)) or
            not isinstance(trigger_asset, (int, np.integer)) or
            not 0 <= trigger_asset < p.shape[1]):
        raise ValueError('trigger_asset must be a valid integer asset index')
    held = p[0].copy()
    out, turn, gap = np.ones(len(p)), np.zeros(len(p)), np.zeros(len(p))
    actual = np.zeros_like(p)
    actual[0] = held
    for i in range(1, len(p)):
        wealth = float(held.sum())
        if not np.isfinite(wealth):
            raise ValueError('nonfinite portfolio value')
        if wealth <= 0:
            out[i:] = 0.
            break
        weights = held / wealth
        full_distance = .5 * float(np.abs(p[i] - weights).sum())
        gap[i] = (full_distance if trigger_asset is None else
                  abs(float(p[i, trigger_asset] - weights[trigger_asset])))
        hit = gap[i] >= band if inclusive else gap[i] > band
        if mask[i] and hit:
            turn[i] = full_distance
            held = p[i] * (wealth * (1 - cost * turn[i]))
        actual[i] = held / held.sum()
        held *= 1 + r[i]
        out[i] = held.sum()
    if not np.isfinite(out).all():
        raise ValueError('nonfinite portfolio value')
    return dict(wealth=out, turnover=turn, positions=actual, gap=gap,
                trade_days=turn > 1e-12)
