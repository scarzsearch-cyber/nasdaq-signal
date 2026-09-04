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
        paths = ('AGENTS.md', 'CLAUDE.md', 'guide.html', 'signal.html',
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
