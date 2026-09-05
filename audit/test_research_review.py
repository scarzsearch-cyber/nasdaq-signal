"""Research-review regressions: hand-calculated tax paths and cache integrity.

Run: python audit/test_research_review.py (offline; real ledgers are read-only).
"""
import contextlib
import ast
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))

import numpy as np
import pandas as pd
import tax_us_direct as tax
import hist_fetch as fetch
import exec_cost


class ReviewContext(unittest.TestCase):
    @staticmethod
    def sources():
        paths = ('AGENTS.md', 'CLAUDE.md', 'guide.html', 'signal.html', 'notes.html',
                 'research/tax_us_direct.py')
        return {p: (ROOT / p).read_text(encoding='utf-8') for p in paths}

    def test_current_context_contracts(self):
        from verify_all import _review_context_checks
        checks = _review_context_checks(self.sources())
        self.assertTrue(all(checks.values()), [name for name, passed in checks.items() if not passed])

    def test_removed_context_is_detected_without_changing_real_files(self):
        from verify_all import _review_context_checks
        original = self.sources()
        self.assertTrue(all(_review_context_checks(original).values()))
        mutations = (
            ('AGENTS.md', lambda _: '# AGENTS.md\n' + '옛 규칙 사본\n' * 200),
            ('CLAUDE.md', lambda _: ''),
            ('guide.html', lambda s: s.replace('보장은 없습니다', '항상 유리합니다')),
            ('guide.html', lambda s: s + '<p>54년 성과는 약 15배</p>'),
            ('signal.html', lambda s: s.replace('5년 납입 · 20년 결과', '20년 결과')),
            ('notes.html', lambda s: s.replace('rel="icon"', 'rel="missing-icon"')),
            ('research/tax_us_direct.py', lambda s: s + '\n# 146.1 대 146.6 동률\n'),
        )
        for path, mutate in mutations:
            with self.subTest(file=path):
                changed = dict(original)
                changed[path] = mutate(changed[path])
                self.assertFalse(all(_review_context_checks(changed).values()))

    def test_html_comment_does_not_replace_visible_warning(self):
        from verify_all import _review_context_checks
        changed = self.sources()
        self.assertTrue(all(_review_context_checks(changed).values()))
        changed['guide.html'] = changed['guide.html'].replace(
            '보장은 없습니다', '<!-- 보장은 없습니다 -->')
        self.assertFalse(all(_review_context_checks(changed).values()))


class TaxAccounting(unittest.TestCase):
    def test_tax_funding_sale_carries_gain_to_next_year(self):
        # Deposit 100 at t=21, rise to 200, switch, then rise to 300.
        # Year tax=20; the sale realizes 20-20*200/300=20/3.
        # Remaining holding realizes 280-560/3=280/3 at liquidation.
        # Next tax=(20/3+280/3)*20%=20, leaving exactly 260.
        a = np.ones(42)
        a[22:29] = 2
        a[29:] = 3
        years = np.r_[np.full(30, 2020), np.full(12, 2021)]
        value, paid = tax.accum_US(a, [23], years, 0, 41, 100,
                                    rate=.2, deduct=0, cost=0)
        self.assertEqual(paid, 100)
        self.assertAlmostEqual(value, 260)

    def test_zero_tax_accumulation_matches_cashflow_identity(self):
        a = np.cumprod(1 + np.sin(np.arange(106)) * .02)
        years = np.r_[np.full(53, 2020), np.full(53, 2021)]
        switches = [28, 53, 84]
        expected = sum(100 * a[-1] / a[t] for t in range(21, 106, 21))
        domestic, paid, _ = tax.accum_B(a, switches, years, 0, 105, 100,
                                        r_isa=0, r_gen=0, total_cap=250)
        overseas, overseas_paid = tax.accum_US(a, switches, years, 0, 105,
                                              100, rate=0)
        self.assertEqual(paid, 500)
        self.assertEqual(overseas_paid, paid)
        self.assertAlmostEqual(domestic, expected)
        self.assertAlmostEqual(overseas, expected)

    def test_one_deposit_equals_lump_sum_with_same_execution_cost(self):
        a = np.ones(42)
        a[22:29] = 2
        a[29:] = 3
        sw = [23]
        years = np.r_[np.full(30, 2020), np.full(12, 2021)]
        # Accumulation accepts the already cost-bearing sim2 curve.
        a[23:] *= 1 - tax.COST
        pre = tax.strip_switch_cost(a, sw)
        expected_us = 100 * tax.after_us(pre, sw, years, 21, 41, rate=.2)
        expected_gen = 100 * tax.after_gen(pre, sw, 21, 41, rate=.2)
        actual_us, _ = tax.accum_US(a, sw, years, 0, 41, 100, rate=.2, deduct=0)
        actual_gen, _, _ = tax.accum_B(a, sw, years, 0, 41, 100,
                                       r_gen=.2, total_cap=0)
        self.assertAlmostEqual(actual_us, expected_us)
        self.assertAlmostEqual(actual_gen, expected_gen)


class AtomicHistoryCache(unittest.TestCase):
    def test_failed_replace_preserves_old_cache(self):
        with tempfile.TemporaryDirectory(prefix='research-review-') as folder:
            path = Path(folder) / 'cache.csv'
            frame = pd.DataFrame({'Date': pd.date_range('2020-01-01', periods=10),
                                  'Close': np.arange(10) + 10.0})
            frame.to_csv(path, index=False)
            before = path.read_bytes()
            newer = pd.concat([frame, pd.DataFrame({'Date': [pd.Timestamp('2020-01-11')],
                                                    'Close': [20.]})], ignore_index=True)
            with patch.object(fetch.os, 'replace', side_effect=OSError('injected')):
                with self.assertRaises(OSError):
                    fetch.save_guarded(str(path), newer, 'test')
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(folder).iterdir()), [path])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(fetch.save_guarded(str(path), frame.iloc[-2:], 'test'))
                self.assertTrue(fetch.save_guarded(str(path), newer, 'test'))
            self.assertEqual(len(pd.read_csv(path)), 11)


class WalkForwardContinuity(unittest.TestCase):
    def test_splitting_at_pending_switch_preserves_cost(self):
        for name in ('hyst_wfa.py', 'hyst_sigwfa.py'):
            with self.subTest(file=name):
                # Execute only path(), not the script's report/export top level.
                tree = ast.parse((ROOT / 'research' / name).read_text(encoding='utf-8-sig'))
                fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'path')
                ns = dict(np=np, COST=.001, ENTER=-.16,
                          ddv=np.array([0., -.2, -.2, 0., 0.]),
                          qldr=np.zeros(5), schdr=np.zeros(5))
                exec(compile(ast.Module(body=[fn], type_ignores=[]), name, 'exec'), ns)
                args = [-.16] if name == 'hyst_wfa.py' else [ns['ddv'], -.16, -.16]
                whole, _ = ns['path'](*args, 0, 5)
                left, pending, held = ns['path'](*args, 0, 2, return_position=True)
                right, _ = ns['path'](*args, 2, 5, w0=pending, prev_pos=held)
                self.assertAlmostEqual(whole[-1], .999 ** 2)
                self.assertAlmostEqual(left[-1] * right[-1], whole[-1])

    def test_calmar_includes_first_day_loss(self):
        for name in ('hyst_wfa.py', 'hyst_sigwfa.py'):
            with self.subTest(file=name):
                tree = ast.parse((ROOT / 'research' / name).read_text(encoding='utf-8-sig'))
                fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'calmar')
                ns = {'np': np}
                exec(compile(ast.Module(body=[fn], type_ignores=[]), name, 'exec'), ns)
                self.assertAlmostEqual(ns['calmar'](np.full(252, .8)), -1)


class ExecutionSample(unittest.TestCase):
    def test_script_selfcheck(self):
        exec_cost.selfcheck()

    def test_partial_and_weekend_nav_do_not_fill_sample(self):
        with tempfile.TemporaryDirectory(prefix='research-nav-test-') as folder:
            path = Path(folder) / 'nav.csv'
            rows = [dict(as_of=d, code=c, nav=100, dev_pct=.1)
                    for d in ('2026-09-01', '2026-09-02', '2026-09-05')
                    for c in exec_cost.LEGS]
            rows[4]['nav'] = float('nan')
            pd.DataFrame(rows).to_csv(path, index=False)
            _, days, lookup = exec_cost.nav_stats(path)
            self.assertEqual(days, ['2026-09-01'])
            self.assertNotIn(('2026-09-05', '418660'), lookup)

    def test_invalid_fill_invalidates_same_day(self):
        trades = [dict(d='2026-09-01', code='418660', side='buy', qty=1, px=100),
                  dict(d='2026-09-01', code='458730', side='sell', qty='bad', px=100)]
        got = exec_cost.analyse_trades(trades, {('2026-09-01', '418660'): 100})
        self.assertEqual(got['event_costs'], [])
        self.assertEqual(got['incomplete_dates'], ['2026-09-01'])


class PartialWeightAccounting(unittest.TestCase):
    def test_constant_half_weight_is_rebalanced(self):
        tree = ast.parse((ROOT / 'research/axis_dca.py').read_text(encoding='utf-8-sig'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'dca')
        ns = dict(np=np, PAY_MONTHS=60, COST=.001)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'axis_dca.py', 'exec'), ns)
        # Deposit 1 half/half, then two +100% risky days: 1.5*1.5=2.25,
        # not drifting 0.5*4+0.5=2.5.
        _, values, _ = ns['dca']({}, np.array([0., 0., 1., 1.]), np.zeros(4),
                                np.full(4, .5), 0, 4, pay=1, cost=0,
                                months=np.array([0, 1, 1, 1]))
        self.assertAlmostEqual(values[-1], 2.25)


class BinaryWeightValidity(unittest.TestCase):
    def test_nonfinite_weights_rejected_by_cash_and_tax_engines(self):
        import axis_lib as axis
        idx = pd.date_range('2020-01-30', periods=6)
        D = dict(idx=idx, px=pd.Series(np.ones(6), index=idx), qldr=np.zeros(6),
                 schdr=np.zeros(6), ddv=np.zeros(6), c_daily=0.)
        for bad in (np.nan, np.inf, -np.inf):
            w = np.array([1., 1., bad, 0., 0., 1.])
            actions = {
                'accumulate': lambda: axis.accumulate(D, 2., w, 0, 6),
                'tax_per_switch': lambda: axis.after_tax(D, 2., w, .154, True),
                'tax_annual': lambda: axis.after_tax_annual(D, 2., w),
            }
            for name, action in actions.items():
                with self.subTest(value=str(bad), engine=name):
                    with self.assertRaises(ValueError):
                        action()

    def test_binary_guard_retains_rounding_tolerance_and_window_scope(self):
        import axis_lib as axis
        w = np.array([np.nan, 0., 1., 1e-12, 1 - 1e-12, np.nan])
        axis._need_binary(w, 1, 5, 'valid test slice')
        with self.assertRaises(ValueError):
            axis._need_binary(np.array([0., .5, 1.]), 0, 3, 'fractional test')


class MultiAssetRebalance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Extract the pure accounting function: no reports, cache writes or feeds.
        tree = ast.parse((ROOT / 'research/liquid_design.py').read_text(encoding='utf-8-sig'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'sim_multi')
        ns = dict(np=np, COST=.001)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'liquid_design.py', 'exec'), ns)
        cls.sim = staticmethod(ns['sim_multi'])

    @staticmethod
    def reference(W, R, rebalance, cost):
        # Independent currency accounts, not the vectorized target-return formula.
        held = [float(w) for w in W[0]]
        cash = 1.0 - sum(held)
        out = [1.0]
        for i in range(1, len(W)):
            total = sum(held) + cash
            if rebalance[i - 1]:
                wanted = [total * float(w) for w in W[i - 1]]
                wanted_cash = total - sum(wanted)
                traded = (sum(abs(a - b) for a, b in zip(wanted, held))
                          + abs(wanted_cash - cash)) / 2
                remaining = total - cost * traded
                held = [remaining * float(w) for w in W[i - 1]]
                cash = remaining - sum(held)
            held = [h * (1 + float(r)) for h, r in zip(held, R[i])]
            out.append(sum(held) + cash)
        return out

    def test_monthly_hold_does_not_reset_weights_each_day(self):
        W = np.full((3, 2), .5)
        R = np.array([[0., 0.], [1., 0.], [-.5, 0.]])
        # One asset round trips within the month; no intermediate sale occurs.
        actual = self.sim(W, R, cost=.001, rebalance=[True, False, False])
        np.testing.assert_allclose(actual, [1., 1.5, 1.], rtol=0, atol=1e-12)

    def test_daily_rebalance_charges_actual_drift(self):
        W = np.full((3, 2), .5)
        R = np.array([[0., 0.], [1., 0.], [-.5, 0.]])
        # Before the final day, weights are 2/3 and 1/3; trade 1/6 of wealth.
        actual = self.sim(W, R, cost=.001)
        self.assertAlmostEqual(actual[-1], 1.5 * (1 - .001 / 6) * .75)

    def test_close_signal_is_executed_only_next_day(self):
        W = np.array([[1., 0.], [0., 1.], [0., 1.]])
        R = np.array([[0., 0.], [.1, .9], [.2, .3]])
        np.testing.assert_allclose(self.sim(W, R, cost=.001),
                                   [1., 1.1, 1.1 * .999 * 1.3], rtol=0, atol=1e-12)

    def test_binary_B_reduces_to_original_two_asset_engine(self):
        rng = np.random.default_rng(20260905)
        w = rng.integers(0, 2, 200).astype(float)
        R = rng.uniform(-.1, .1, size=(len(w), 2))
        pos = np.r_[w[0], w[:-1]]
        returns = pos * R[:, 0] + (1 - pos) * R[:, 1]
        returns[0] = 0
        for cost in (0., .001, .003):
            expected = np.cumprod((1 + returns) * (1 - cost * np.abs(np.diff(pos, prepend=pos[0]))))
            actual = self.sim(np.column_stack([w, 1 - w]), R, cost=cost)
            np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)

    def test_random_cash_portfolios_match_independent_accounts(self):
        rng = np.random.default_rng(37)
        for cost in (0., .001, .02):
            for scheduled in ('never', 'daily', 'irregular'):
                with self.subTest(cost=cost, schedule=scheduled):
                    weights = rng.dirichlet(np.ones(4), size=100)
                    W = weights[:, :3]  # The fourth weight is cash.
                    R = rng.uniform(-.1, .1, size=W.shape)
                    mask = (np.zeros(100, bool) if scheduled == 'never' else
                            np.ones(100, bool) if scheduled == 'daily' else rng.random(100) < .15)
                    expected = self.reference(W, R, mask, cost)
                    actual = self.sim(W, R, cost=cost, rebalance=mask)
                    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)

    def test_invalid_accounting_inputs_are_rejected(self):
        W = np.full((3, 2), .5)
        R = np.zeros_like(W)
        for weights in (np.empty((0, 2)), np.ones(3), -W, W * 1.1,
                        np.array([[np.inf, 0.], [1., 0.], [1., 0.]])):
            with self.subTest(weights=str(weights)):
                with self.assertRaises(ValueError):
                    self.sim(weights, R)
        with self.assertRaises(ValueError):
            self.sim(W, R, rebalance=[True])
        with self.assertRaises(ValueError):
            self.sim(W, R, cost=-.01)

    def test_schedule_keeps_month_end_even_with_unchanged_targets(self):
        tree = ast.parse((ROOT / 'research/liquid_design.py').read_text(encoding='utf-8-sig'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'rebalance_events')
        ns = dict(np=np)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'liquid_design.py', 'exec'), ns)
        W = np.array([[.5, .5], [.5, .5], [.5, .5], [.7, .3], [.7, .3]])
        mask = ns['rebalance_events'](W, [False, False, True, False, False])
        np.testing.assert_array_equal(mask, [True, False, True, True, False])


class FractionalTurnoverAccounting(unittest.TestCase):
    @staticmethod
    def extracted(path, names, extra):
        tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = dict(np=np, pd=pd, COST=.1, **extra)
        # The helper is optional only so the original five implementations can
        # fail on the hand-calculated fixture before the production fix exists.
        if (ROOT / 'research/rebalance_accounting.py').exists():
            from research.rebalance_accounting import daily_turnover
            ns['daily_turnover'] = daily_turnover
        exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), ns)
        return ns

    def paths(self, w, risky, safe, cost=.1):
        from types import SimpleNamespace
        idx = pd.date_range('2020-01-01', periods=len(w))
        zero = np.zeros(len(w))
        extra = dict(n=len(w), idx=idx, QLDR=risky, MIXR=safe, tb=safe, TB=safe,
                     EC=SimpleNamespace(COST=cost), G=SimpleNamespace(COST=cost),
                     t4_w=lambda _: w)
        ns = self.extracted('axis_defmix.py', ['sim_def'], extra)
        yield 'sim_def', np.asarray(ns['sim_def'](dict(idx=idx, qldr=risky), w, safe, cost=cost))
        ns = self.extracted('research/eng_common.py', ['sim2'], extra)
        yield 'sim2', np.asarray(ns['sim2'](w, risky, safe, cost=cost))
        ns = self.extracted('research/t4_lev_post.py', ['sim'], extra)
        yield 't4_lev', np.asarray(ns['sim'](w, risky))
        ns = self.extracted('research/hypo_hex.py', ['_lag1', '_one_way_turnover', 'three_way'], extra)
        yield 'three_way', np.asarray(ns['three_way'](w, zero, 1-w, cost=cost))
        ns = self.extracted('research/hypo_t4_real.py', ['multi_t4'], extra)
        yield 'multi_t4', np.asarray(ns['multi_t4']([(risky, risky)], cost=cost))

    def test_all_five_paths_charge_unchanged_target_drift(self):
        w = np.array([0., .5, .5, .5])
        risky = np.array([0., 0., 1., 0.])
        # Same initial purchase: .95, then 50/50 return doubles only the
        # risky holding: 1.425. Restore 50/50, trading 1/6 -> 1.40125.
        for name, actual in self.paths(w, risky, np.zeros(4)):
            with self.subTest(engine=name):
                np.testing.assert_allclose(actual, [1., 1., 1.425, 1.40125], rtol=0, atol=1e-12)

    def test_fractional_initial_position_has_no_unrequested_initial_fee(self):
        for name, actual in self.paths(np.full(3, .5), np.array([9., 1., 0.]), np.zeros(3)):
            with self.subTest(engine=name):
                np.testing.assert_allclose(actual, [1., 1.5, 1.475], rtol=0, atol=1e-12)

    def test_target_change_that_matches_drift_does_not_trade(self):
        w = np.array([.5, 2/3, 2/3])
        for name, actual in self.paths(w, np.array([0., 1., 0.]), np.zeros(3)):
            with self.subTest(engine=name):
                self.assertAlmostEqual(actual[-1], 1.5)

    def test_binary_and_zero_cost_cases_match_original_formula(self):
        rng = np.random.default_rng(20260905)
        for kind in ('binary', 'fractional'):
            w = rng.integers(0, 2, 80).astype(float) if kind == 'binary' else rng.random(80)
            w[0] = 0.  # Original multi_t4 started in cash.
            risky, safe = rng.uniform(-.2, .2, (2, 80))
            pos = np.r_[w[0], w[:-1]]
            returns = pos*risky + (1-pos)*safe
            returns[0] = 0.
            for cost in ((0., .001, .1) if kind == 'binary' else (0.,)):
                expected = np.cumprod((1+returns)*(1-cost*np.abs(np.diff(pos, prepend=pos[0]))))
                for name, actual in self.paths(w, risky, safe, cost):
                    with self.subTest(kind=kind, engine=name, cost=cost):
                        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)

    def test_random_fractional_paths_match_currency_ledger(self):
        rng = np.random.default_rng(391)
        for cost in (0., .001, .03):
            w = rng.random(101)
            R = rng.uniform(-.3, .3, (101, 2))
            expected = MultiAssetRebalance.reference(
                np.column_stack([w, 1-w]), R, np.ones(101, bool), cost)
            for name, actual in self.paths(w, R[:, 0], R[:, 1], cost):
                with self.subTest(engine=name, cost=cost):
                    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)

    def test_lag_and_window_restart_use_matching_holdings(self):
        idx = pd.date_range('2020-01-01', periods=12)
        w = np.linspace(.1, .9, 12)
        risky, safe = np.sin(np.arange(12))*.1, np.cos(np.arange(12))*.01
        ns = self.extracted('axis_defmix.py', ['sim_def'], {})
        for lag in (0, 1, 2, 20):
            ws = w[2:10]
            pos = ws.copy()
            if lag:
                pos[:lag] = ws[0]
                pos[lag:] = ws[:-lag]
            R = np.column_stack([risky[2:10], safe[2:10]])
            # Currency reference expects close-day targets and applies lag=1.
            ref_w = np.r_[pos[1:], pos[-1]]
            W = np.column_stack([ref_w, 1-ref_w])
            W[0] = [pos[0], 1-pos[0]]
            if lag == 0:
                # Explicit direct ledger for the look-ahead diagnostic path.
                held = [float(pos[0]), float(1-pos[0])]
                expected = [1.]
                for i in range(1, len(pos)):
                    value = sum(held)
                    value *= 1-.1*abs(pos[i]-held[0]/value)
                    held = [value*pos[i]*(1+R[i, 0]), value*(1-pos[i])*(1+R[i, 1])]
                    expected.append(sum(held))
            else:
                expected = MultiAssetRebalance.reference(W, R, np.ones(8, bool), .1)
            actual = ns['sim_def'](dict(idx=idx, qldr=risky), w, safe, cost=.1,
                                   lag=lag, start=idx[2], end=idx[9])
            np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)

    def test_turnover_rejects_invalid_weights_and_returns(self):
        from research.rebalance_accounting import daily_turnover
        W = np.full((3, 2), .5)
        R = np.zeros_like(W)
        for bad in (np.empty((0, 2)), np.ones(3), W*2, -W,
                    np.array([[.5, .5], [np.nan, .5], [.5, .5]])):
            with self.subTest(weights=str(bad)), self.assertRaises(ValueError):
                daily_turnover(bad, R)
        for bad in (np.full_like(R, -1.01), np.full_like(R, np.inf), np.full_like(R, np.nan)):
            with self.subTest(returns=str(bad)), self.assertRaises(ValueError):
                daily_turnover(W, bad)
        np.testing.assert_array_equal(daily_turnover(W[:1], R[:1]), [0.])
        R[1] = -1.
        np.testing.assert_array_equal(daily_turnover(W, R), [0., 0., 0.])

    def test_multileg_netting_and_drift_match_currency_ledger(self):
        from types import SimpleNamespace
        idx = pd.date_range('2020-01-01', periods=5)
        # Two risk legs share one T-bill. Opposite target changes must not
        # charge fictitious transfers between identical T-bill sleeves.
        signals = [np.array([0., 1., 0., .5, .5]), np.array([0., 0., 1., .5, .5])]
        returns = np.array([[0., 0.], [0., 0.], [1., -.5], [0., 0.], [-.2, .3]])
        W = np.column_stack(signals) / 2
        W = np.column_stack([W, 1-W.sum(axis=1)])
        R = np.column_stack([returns, np.zeros(5)])
        ns = self.extracted('research/hypo_t4_real.py', ['multi_t4'], dict(
            idx=idx, tb=np.zeros(5), G=SimpleNamespace(COST=.1), t4_w=lambda x: x))
        actual = ns['multi_t4'](list(zip(signals, returns.T)), cost=.1)
        expected = MultiAssetRebalance.reference(W, R, np.ones(5, bool), .1)
        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


class FixedCandidateScreen(unittest.TestCase):
    def test_candidates_are_causal_with_fixed_warmup(self):
        from strategy_f1_screen import targets
        tree = ast.parse((ROOT / 'research/eng_common.py').read_text(encoding='utf-8-sig'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'rule_dd')
        ns = dict(np=np)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'eng_common.py', 'exec'), ns)
        px = pd.Series(np.exp(np.arange(400)*.001))
        before = targets(px, np.full(400, .5), ns['rule_dd'])
        changed = px.copy()
        changed.iloc[300:] *= .1
        after = targets(changed, np.full(400, .5), ns['rule_dd'])
        self.assertEqual(len(before), 8)
        for name in before:
            np.testing.assert_array_equal(before[name][:300], after[name][:300])
        np.testing.assert_array_equal(before['MA200-mix'][:199, 0], 0.)
        self.assertEqual(before['MA200-mix'][199, 0], 1.)
        np.testing.assert_array_equal(before['MOM252-mix'][:252, 0], 0.)
        self.assertEqual(before['MOM252-mix'][252, 0], 1.)

    def test_screen_execution_and_lag_match_currency_reference(self):
        from strategy_f1_screen import execute, currency_reference
        rng = np.random.default_rng(17)
        W = rng.dirichlet(np.ones(4), size=101)
        R = rng.uniform(-.1, .1, size=W.shape)
        for lag in (1, 2, 200):
            actual, _ = execute(W, R, .002, lag)
            expected = currency_reference(W, R, .002, lag)
            np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
        for lag in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                execute(W, R, .001, lag)

    def test_rolling_calendar_windows_and_independent_counts(self):
        from strategy_f1_screen import windows
        idx = pd.date_range('2000-01-01', periods=121, freq='MS')
        result = windows({'B': np.ones(121), 'flat': np.ones(121)}, idx, 7)
        self.assertEqual(result['starts'], 37)
        self.assertEqual(result['nonoverlap_windows'], 1)
        self.assertEqual(result['last_start'], '2003-01-01')
        self.assertEqual(result['rows']['flat']['paired_tie_fraction_vs_B'], 1.)
        self.assertEqual(result['rows']['flat']['paired_win_fraction_vs_B'], 0.)
        self.assertEqual(result['rows']['B']['median_multiple'], 1.)


class ScheduledMarketAccounting(unittest.TestCase):
    def test_closed_market_keeps_holdings_not_targets(self):
        from research.rebalance_accounting import scheduled_path
        p = np.full((3, 2), .5)
        r = np.array([[9., 9.], [1., 0.], [-.5, 0.]])
        a, turn = scheduled_path(p, r, [False, True, False], .001)
        np.testing.assert_allclose(a, [1., 1.5, 1.], rtol=0, atol=1e-12)
        np.testing.assert_array_equal(turn, 0.)
        p[2] = [0., 1.]  # An unexecutable target cannot change actual holdings.
        np.testing.assert_array_equal(scheduled_path(p, r, [False, True, False], .001)[0], a)

    def test_daily_schedule_reduces_to_corrected_daily_engine(self):
        from research.rebalance_accounting import scheduled_path, daily_turnover
        rng = np.random.default_rng(2026)
        p = rng.dirichlet(np.ones(4), size=70)
        r = rng.uniform(-.2, .2, size=p.shape)
        daily = np.sum(p*r, axis=1); daily[0] = 0.
        for cost in (0., .001, .03):
            a, turn = scheduled_path(p, r, np.ones(70, bool), cost)
            dt = daily_turnover(p, r)
            expected = np.cumprod((1+daily)*(1-cost*dt))
            np.testing.assert_allclose(a, expected, rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(turn, dt, rtol=1e-12, atol=1e-12)

    def test_irregular_schedule_matches_independent_held_units(self):
        from research.rebalance_accounting import scheduled_path
        from strategy_f1_kr import held_units_reference
        rng = np.random.default_rng(81)
        p = rng.dirichlet(np.ones(4), size=70)
        r = rng.uniform(-.2, .2, size=p.shape)
        for mask in (np.zeros(70, bool), rng.random(70) < .3, np.ones(70, bool)):
            a, t = scheduled_path(p, r, mask, .002)
            expected = held_units_reference(p, r, mask, .002)
            np.testing.assert_allclose(a, expected, rtol=1e-12, atol=1e-12)
            np.testing.assert_array_equal(t[~mask], 0.)

    def test_korean_holiday_drops_superseded_signal_and_never_uses_same_day_close(self):
        from strategy_f1_kr import execution_events, inverse_sources
        idx = pd.to_datetime(['2020-09-03', '2020-09-04', '2020-09-07', '2020-09-08', '2020-09-09', '2020-09-10'])
        kr = pd.to_datetime(['2020-09-02', '2020-09-03', '2020-09-04', '2020-09-08', '2020-09-09', '2020-09-10', '2020-09-11'])
        source, trade = execution_events(idx, kr)
        np.testing.assert_array_equal(source, [0, 0, 0, 2, 3, 4])
        np.testing.assert_array_equal(trade, [False, True, False, True, True, True])
        for lag in (0, 1):
            source, trade = execution_events(idx, kr, extra_days=lag)
            np.testing.assert_array_equal(source, inverse_sources(idx, kr, extra_days=lag))
            self.assertTrue(np.all(source[1:] < np.arange(1, len(idx))))

    def test_invalid_schedule_and_calendar_fail_closed(self):
        from research.rebalance_accounting import scheduled_path
        from strategy_f1_kr import execution_events
        p = np.full((3, 2), .5)
        r = np.zeros_like(p)
        for mask in ([True], [1, 0, 1], [0., np.nan, 1.]):
            with self.assertRaises(ValueError):
                scheduled_path(p, r, mask)
        for cost in (-.001, 1., np.inf):
            with self.assertRaises(ValueError):
                scheduled_path(p, r, [False, True, True], cost)
        idx = pd.bdate_range('2020-01-01', periods=5)
        with self.assertRaises(ValueError):
            execution_events(idx, idx[:-1])
        with self.assertRaises(ValueError):
            execution_events(idx[::-1], idx)
        with self.assertRaises(ValueError):
            execution_events(idx, idx, extra_days=.5)


class HistoricalCalendarIntegrity(unittest.TestCase):
    def test_fred_drops_blank_and_dot_quotes_without_using_another_column(self):
        import hist_data as history
        parsed = pd.read_csv(io.StringIO(
            'observation_date,NASDAQCOM,other\n'
            '1972-02-18,100,900\n'
            '1972-02-21,,901\n'
            '1972-02-22,.,902\n'
            '1972-02-23,101,903\n'))
        with patch.object(history.pd, 'read_csv', return_value=parsed):
            actual = history._fred('unused.csv', 'NASDAQCOM')
        self.assertEqual(list(actual.index), [pd.Timestamp('1972-02-18'), pd.Timestamp('1972-02-23')])
        np.testing.assert_array_equal(actual.to_numpy(), [100., 101.])

    def test_proxy_calendar_does_not_include_missing_price_as_zero_return(self):
        import hist_data as history
        frames = {
            'data/hist/fred_NASDAQCOM.csv': pd.read_csv(io.StringIO(
                'observation_date,NASDAQCOM\n1972-02-18,100\n1972-02-21,\n1972-02-22,101\n')),
            'data/hist/yahoo_NDX.csv': pd.DataFrame(dict(
                Date=pd.to_datetime(['1985-10-01', '1985-10-02']), Close=[100., 101.])),
            'qqq_us_d.csv': pd.DataFrame(dict(
                Date=pd.to_datetime(['1999-03-10', '1999-03-11']), Close=[100., 101.])),
        }
        with patch.object(history.pd, 'read_csv', side_effect=lambda path, **kw: frames[str(path)].copy()):
            returns, source = history.qqq_proxy()
        self.assertNotIn(pd.Timestamp('1972-02-21'), returns.index)
        self.assertEqual(len(returns), 6)
        self.assertAlmostEqual(returns.loc['1972-02-22'], .01)
        self.assertTrue(returns.index.equals(source.index))


class IsaDecomposition(unittest.TestCase):
    def test_static_isa_panel_matches_generated_account_values(self):
        import json
        import re
        data = json.loads((ROOT / 'data/isa_stats.json').read_text(encoding='utf-8'))
        source = (ROOT / 'signal.html').read_text(encoding='utf-8')
        panel = source.split('id="taxPanel"', 1)[1].split('id="t4Panel"', 1)[0]
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', panel, flags=re.S)[1:]
        for row, key in zip(rows, ('isa', 'isa3', 'gen', 'pre')):
            cells = re.findall(r'<td\b[^>]*>(.*?)</td>', row, flags=re.S)
            expected = [f"{data['y'+str(y)]['modes'][key]['median'] / data['y'+str(y)]['paid']:.2f}배"
                        for y in (10, 15, 20)]
            self.assertEqual(cells[1:4], expected, key)
        self.assertEqual(len(rows), 4)
        self.assertIn(f"+{data['decomp']['total']:.1f}%", panel)

    def test_components_use_one_denominator_and_sum_to_total(self):
        import axis_isa
        out = axis_isa.decompose(100., 150., 160., 170.)
        for key, expected in dict(defer=50., rate=10., exempt=10., total=70.).items():
            self.assertAlmostEqual(out[key], expected)
        self.assertAlmostEqual(sum(out[k] for k in ('defer', 'rate', 'exempt')), out['total'])
        self.assertEqual(axis_isa.decompose(100., 100., 100., 100.)['total'], 0.)

    def test_invalid_reference_cannot_produce_plausible_percentages(self):
        import axis_isa
        for base in (0., -1., float('nan'), float('inf')):
            with self.subTest(base=base), self.assertRaises(ValueError):
                axis_isa.decompose(base, 150., 160., 170.)


class HistoricalModelScope(unittest.TestCase):
    """Document current model boundaries, not their accuracy as forecasts."""

    def test_krw_attack_remains_synthetic_and_cost_sensitive_after_listing(self):
        import hist_krfinal as kf
        idx = pd.bdate_range('2023-07-03', periods=4)
        px = pd.Series([100., 110., 105., 108.], index=idx)
        fx = pd.Series([1300., 1310., 1290., 1305.], index=idx)

        def rebuild(cost, real_qld_return):
            data = dict(idx=idx, px=px, c_daily=cost,
                        qldr=np.full(len(idx), real_qld_return), schdr=np.zeros(len(idx)))
            with patch.object(kf.DF, 'build', return_value=data), patch.object(kf.K, 'fx', return_value=fx):
                return kf.build_krw('chain')

        cost = .033 / 252
        base = rebuild(cost, .5)
        rq = px.pct_change().fillna(0).to_numpy()
        fr = fx.pct_change().fillna(0).to_numpy()
        np.testing.assert_allclose(base[2], 2 * ((1+rq)*(1+fr)-1) - cost)
        # Changing the supplied real USD QLD path does not change KRW attack.
        np.testing.assert_array_equal(base[2], rebuild(cost, -.5)[2])
        np.testing.assert_allclose(rebuild(cost+.01/252, .5)[2] - base[2], -.01/252,
                                   rtol=0, atol=1e-16)

    def test_daily_double_compounding_has_path_drag_without_cost_residual(self):
        tree = ast.parse((ROOT / 'research/eng_common.py').read_text(encoding='utf-8-sig'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'synth2x')
        ns = dict(np=np)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'eng_common.py', 'exec'), ns)
        returns = np.array([.1, -1/11])
        self.assertAlmostEqual(np.prod(1+returns), 1.)
        synthetic = ns['synth2x'](returns, 0.)
        np.testing.assert_array_equal(2*returns - synthetic, 0.)
        self.assertAlmostEqual(np.prod(1+synthetic), 54/55)
        self.assertLess(np.prod(1+synthetic), 1.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
