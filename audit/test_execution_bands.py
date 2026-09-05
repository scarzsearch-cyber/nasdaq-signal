"""Offline regressions for real holdings in legacy execution diagnostics."""
import ast
import contextlib
import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from research.band_accounting import banded_path
from research.rebalance_accounting import scheduled_path


def functions_only(file, names, namespace):
    """Load reviewed function bodies without importing their market-data jobs."""
    tree = ast.parse((ROOT/file).read_text(encoding='utf-8-sig'))
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in body} != set(names):
        raise AssertionError('test function selection is incomplete')
    exec(compile(ast.Module(body=body, type_ignores=[]), file, 'exec'), namespace)
    return namespace


def units_reference(p, r, mask, cost, band, asset=None, inclusive=False):
    """Independent price/share ledger; no production accounting helper calls."""
    prices = np.ones(p.shape[1])
    shares = p[0].copy()
    wealth, turnover = [1.], [0.]
    for t in range(1, len(p)):
        value = shares*prices
        total = sum(float(x) for x in value)
        weights = value/total
        distance = sum(abs(float(a-b)) for a, b in zip(p[t], weights))/2
        trigger = distance if asset is None else abs(float(p[t, asset]-weights[asset]))
        traded = mask[t] and (trigger >= band if inclusive else trigger > band)
        charge = total*cost*distance if traded else 0.
        if traded:
            shares = p[t]*(total-charge)/prices
        prices *= 1+r[t]
        wealth.append(sum(float(x) for x in shares*prices))
        turnover.append(distance if traded else 0.)
    return np.array(wealth), np.array(turnover)


class BandedAccounting(unittest.TestCase):
    def test_round_trip_no_trade_cannot_create_rebalance_profit(self):
        p = np.tile([.5, .5], (3, 1))
        r = np.array([[0., 0.], [1., 0.], [-.5, 0.]])
        q = banded_path(p, r, np.ones(3, bool), 0., .2)
        np.testing.assert_array_equal(q['wealth'], [1., 1.5, 1.])
        np.testing.assert_array_equal(q['turnover'], [0., 0., 0.])
        np.testing.assert_allclose(q['positions'][2], [2/3, 1/3])

    def test_drift_not_target_change_triggers_trade_and_cost(self):
        p = np.tile([.5, .5], (3, 1))
        r = np.array([[0., 0.], [1., 0.], [0., 0.]])
        q = banded_path(p, r, np.ones(3, bool), .1, .1)
        self.assertAlmostEqual(q['turnover'][2], 1/6)
        self.assertAlmostEqual(q['wealth'][-1], 1.475)
        self.assertEqual(q['trade_days'].sum(), 1)

    def test_target_following_actual_drift_has_no_trade(self):
        p = np.array([[.5, .5], [.5, .5], [2/3, 1/3]])
        r = np.array([[0., 0.], [1., 0.], [0., 0.]])
        q = banded_path(p, r, np.ones(3, bool), .1)
        np.testing.assert_array_equal(q['turnover'], [0., 0., 0.])
        self.assertEqual(q['wealth'][-1], 1.5)

    def test_zero_band_reduces_to_existing_scheduled_ledger(self):
        rng = np.random.default_rng(610)
        p = rng.dirichlet(np.ones(4), 120)
        r = rng.uniform(-.08, .08, p.shape)
        mask = rng.random(len(p)) > .3
        for fee in (0., .001, .2):
            q = banded_path(p, r, mask, fee, 0.)
            a, b = scheduled_path(p, r, mask, fee)
            np.testing.assert_allclose(q['wealth'], a, rtol=2e-14, atol=0)
            np.testing.assert_allclose(q['turnover'], b, rtol=2e-14, atol=2e-15)

    def test_independent_shares_random_paths(self):
        rng = np.random.default_rng(611)
        for k in (2, 3, 4):
            for band in (0., .05, .2, 1.):
                p = rng.dirichlet(np.ones(k), 80)
                r = rng.uniform(-.15, .15, p.shape)
                mask = rng.random(len(p)) > .3
                for asset in (None, 0):
                    q = banded_path(p, r, mask, .002, band, asset, True)
                    a, b = units_reference(p, r, mask, .002, band, asset, True)
                    np.testing.assert_allclose(q['wealth'], a, rtol=2e-13, atol=0)
                    np.testing.assert_allclose(q['turnover'], b, rtol=2e-12, atol=2e-14)

    def test_closed_rows_hold_every_asset_and_cannot_charge_fee(self):
        p = np.array([[.5, .25, .25], [0., 1., 0.], [0., 0., 1.]])
        r = np.array([[9., 9., 9.], [1., .2, -.2], [0., 0., 0.]])
        q = banded_path(p, r, np.zeros(3, bool), .1)
        np.testing.assert_allclose(q['wealth'], [1., 1.5, 1.5])
        np.testing.assert_allclose(q['positions'][2], [2/3, .2, 2/15])
        self.assertEqual(q['trade_days'].sum(), 0)

    def test_boundary_conventions_are_explicit(self):
        p = np.array([[.5, .5], [.75, .25]])
        r, mask = np.zeros_like(p), np.ones(2, bool)
        a = banded_path(p, r, mask, .1, .25)
        b = banded_path(p, r, mask, .1, .25, inclusive=True)
        self.assertEqual(a['wealth'][-1], 1.)
        self.assertEqual(b['wealth'][-1], .975)

    def test_attack_only_trigger_does_not_hide_safe_leg_trades(self):
        p = np.array([[.5, .5, 0.], [.5, 0., .5], [.7, 0., .3]])
        q = banded_path(p, np.zeros_like(p), np.ones(3, bool), .1, .1, 0)
        np.testing.assert_array_equal(q['positions'][1], [.5, .5, 0.])
        self.assertEqual(q['turnover'][1], 0.)
        self.assertAlmostEqual(q['turnover'][2], .5)
        self.assertAlmostEqual(q['wealth'][-1], .95)

    def test_zero_wealth_is_absorbing(self):
        p = np.array([[1., 0.], [1., 0.], [0., 1.]])
        r = np.array([[0., 0.], [-1., 0.], [1., 1.]])
        q = banded_path(p, r, np.ones(3, bool), .1)
        np.testing.assert_array_equal(q['wealth'], [1., 0., 0.])

    def test_invalid_inputs_fail_closed_and_inputs_are_not_mutated(self):
        p = np.tile([.5, .5], (3, 1))
        r, mask = np.zeros_like(p), np.ones(3, bool)
        for kw in ({'band': -.1}, {'band': np.nan}, {'cost': 1.},
                   {'trigger_asset': 2}, {'trigger_asset': True}, {'inclusive': 1}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                banded_path(p, r, mask, **kw)
        for wrong in (np.full_like(r, np.nan), np.full_like(r, -1.01)):
            with self.assertRaises(ValueError):
                banded_path(p, wrong, mask)
        with self.assertRaises(ValueError):
            banded_path(p, r, [1, 1, 1])
        p0, r0, m0 = p.copy(), r.copy(), mask.copy()
        banded_path(p, r, mask)
        for a, b in ((p, p0), (r, r0), (mask, m0)):
            np.testing.assert_array_equal(a, b)


class LegacyAdapters(unittest.TestCase):
    def test_shadow_adapter_lag_and_round_trip(self):
        ns = functions_only('research/axis_t4_shadow.py', ['band_curve'],
                            dict(np=np, pd=pd, banded_path=banded_path))
        idx = pd.bdate_range('2020-01-01', periods=3)
        data = dict(idx=idx, qldr=np.array([0., 1., -.5]), schdr=np.zeros(3))
        curve, turnover = ns['band_curve'](data, np.full(3, .5), .2, 0.)
        np.testing.assert_array_equal(curve, [1., 1.5, 1.])
        self.assertEqual(turnover, 0.)
        curve, _ = ns['band_curve'](data, np.array([0., 1., 0.]), 0., 0.)
        np.testing.assert_array_equal(curve, [1., 1., .5])
        with self.assertRaises(ValueError):
            ns['band_curve'](data, np.full(3, .5), .2, 0., every=0)

    def test_audit_exec_weekly_phase_and_true_trade_days(self):
        n = 8
        r = np.zeros((n, 3)); r[2, 0] = 1.
        ns = functions_only('research/audit_exec.py', ['exec_path', 'stats_of'],
             dict(np=np, pd=pd, banded_path=banded_path, n=n,
                  X=SimpleNamespace(QLDR=r[:, 0], MIXR=r[:, 1], tb=r[:, 2]),
                  G=SimpleNamespace(idx=pd.bdate_range('2020-01-01', periods=n))))
        target = np.tile([.5, .5, 0.], (n, 1))
        curve, detail = ns['exec_path'](target, 'weekly', 0.)
        np.testing.assert_array_equal(np.flatnonzero(detail['trade_days']), [6])
        self.assertAlmostEqual(detail['turnover'][6], 1/6)
        self.assertAlmostEqual(ns['stats_of'](detail)[1], 252/n)
        self.assertEqual(curve.iloc[-1], 1.5)
        with self.assertRaises(ValueError):
            ns['exec_path'](target, 'weekli', 0.)
        with self.assertRaises(ValueError):
            ns['exec_path'](np.ones(n), 'daily', 0.)

    def test_d1_boundary_with_only_one_neighbor_is_not_a_plateau(self):
        bands = [0., .025, .05, .10, .15, .20]
        rows = [dict(band=b, final=10., calmar=.5, mdd=-.2, turn=9.) for b in bands]
        rows[0]['turn'] = 10.
        rows[-1].update(final=11., calmar=.6, turn=5.)
        def run(table):
            ns = functions_only('research/axis_t4_shadow.py', ['sec_d'],
                dict(sweep=lambda *a, **k: dict(table=pd.DataFrame(table), edge_axes=[], plateau=False),
                     band_curve=lambda *a, **k: (None, 1.),
                     met=lambda _: dict(final=1., mdd=-.2)))
            with contextlib.redirect_stdout(io.StringIO()):
                return ns['sec_d'](None, None)
        self.assertFalse(run(rows)[0][1])
        rows[3].update(final=11., calmar=.6, turn=5.)
        self.assertTrue(run(rows)[0][1])


if __name__ == '__main__':
    unittest.main()
