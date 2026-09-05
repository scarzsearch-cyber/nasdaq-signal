"""Synthetic timing, source, schema and unit-account checks for F4-B."""
import unittest
import json
import warnings
import numpy as np
import pandas as pd
from research.strategy_f4_products import adjusted_prices, known_sources, evaluate, calendar_discrepancy, POLICIES, START, END


class ProductBridgeTests(unittest.TestCase):
    def test_calendar_strict_failure_and_explicit_diagnostic(self):
        prices = pd.to_datetime(['2026-08-27', '2026-08-28', '2026-08-31'])
        incomplete = prices.delete(1)
        with self.assertRaisesRegex(ValueError, 'absent from reference calendar'):
            calendar_discrepancy(prices, incomplete)
        self.assertEqual(calendar_discrepancy(prices, incomplete, True), ['2026-08-28'])
        self.assertEqual(calendar_discrepancy(prices, prices), [])

    def test_missing_product_date_is_not_a_strict_pass(self):
        calendar = pd.to_datetime(['2026-08-27', '2026-08-28', '2026-08-31'])
        with self.assertRaisesRegex(ValueError, 'absent from product prices'):
            calendar_discrepancy(calendar.delete(1), calendar)
        self.assertEqual(calendar_discrepancy(calendar.delete(1), calendar, True), [])

    def test_same_date_foreign_close_is_not_known(self):
        foreign = pd.to_datetime(['2026-01-02', '2026-01-05', '2026-01-06'])
        kr = pd.to_datetime(['2026-01-05', '2026-01-06', '2026-01-07'])
        np.testing.assert_array_equal(known_sources(foreign, kr), [0, 1, 2])

    def test_us_holiday_kr_holiday_forward_mapping(self):
        foreign = pd.to_datetime(['2023-06-16', '2023-06-20', '2023-06-21', '2023-06-22'])
        kr = pd.to_datetime(['2023-06-19', '2023-06-20', '2023-06-23'])
        np.testing.assert_array_equal(known_sources(foreign, kr), [0, 0, 3])

    def test_unavailable_or_unsorted_source_fails(self):
        for f, k in [(['2026-01-05'], ['2026-01-05']),
                     (['2026-01-02', '2026-01-01'], ['2026-01-03']),
                     (['2026-01-01', '2026-01-01'], ['2026-01-03'])]:
            with self.assertRaises(ValueError): known_sources(pd.to_datetime(f), pd.to_datetime(k))

    def test_two_price_schemas_same_adjusted_values(self):
        idx = pd.bdate_range('2026-01-01', periods=3)
        x = pd.DataFrame(dict(Open=[90., 100., 110.], Close=[100., 110., 120.], AdjClose=[80., 88., 96.]), index=idx)
        y = pd.DataFrame(dict(Open=x.Open, Close=x.AdjClose, Raw=x.Close), index=idx)
        pd.testing.assert_frame_equal(adjusted_prices(x), adjusted_prices(y))
        np.testing.assert_allclose(adjusted_prices(x).open, [72., 80., 88.])

    def test_bad_prices_and_unknown_schema_fail(self):
        for value in [0., -1., np.nan, np.inf]:
            x = pd.DataFrame(dict(Open=[10.], Close=[value], AdjClose=[10.]), index=pd.to_datetime(['2026-01-01']))
            with self.assertRaises(ValueError): adjusted_prices(x)
        with self.assertRaises(ValueError):
            adjusted_prices(pd.DataFrame(dict(Open=[10.], Close=[10.]), index=pd.to_datetime(['2026-01-01'])))

    def test_new_opening_signal_does_not_earn_previous_night(self):
        idx = pd.bdate_range('2026-01-01', periods=4)
        p = np.ones((4, 4)); p[:, 0] = [1., .5, .1, .2]
        row, curve = evaluate(p, idx, [1., 0., 0., 1.], np.zeros(4, bool), fee=0.)
        np.testing.assert_allclose(curve, [1., .5, .5, .5])
        self.assertEqual(row['actual_trade_dates'], [str(idx[1].date())])
        self.assertTrue(row['terminal_signal_change_not_traded'])

    def test_initial_signal_not_charged_terminal_not_executed(self):
        idx = pd.bdate_range('2026-01-01', periods=2)
        with warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            row, curve = evaluate(np.ones((2, 4)), idx, [0., 1.], np.zeros(2, bool), fee=.1)
        np.testing.assert_array_equal(curve, [1., 1.])
        self.assertEqual(row['fees'], 0.)
        self.assertEqual(row['actual_trade_dates'], [])
        self.assertIsNone(row['volatility_pct'])
        self.assertEqual(row['volatility_unavailable_reason'], 'only one return')
        json.dumps(row, allow_nan=False)

    def test_review_uses_opening_before_next_return(self):
        idx = pd.bdate_range('2026-01-01', periods=3)
        p = np.ones((3, 4)); p[:, 1] = [1., 2., 1.]
        _, curve = evaluate(p, idx, np.zeros(3), np.array([False, True, False]), fee=0.)
        np.testing.assert_allclose(curve, [1., 1.4, 1.12])

    def test_random_unit_references_with_price_scale(self):
        rng = np.random.default_rng(44020260905)
        idx = pd.bdate_range('2025-01-01', periods=240)
        for _ in range(20):
            p = np.cumprod(1+rng.normal(.001, .02, (len(idx), 4)), axis=0)
            p *= rng.uniform(.5, 100., 4)
            w = rng.integers(0, 2, len(idx)).astype(float)
            for threshold in [0., .02]:
                result, _ = evaluate(p, idx, w, rng.random(len(idx)) < .15, .002, threshold)
                self.assertLess(result['independent_max_relative_error'], 2e-11)

    def test_fixed_scope_not_optimized(self):
        self.assertEqual(POLICIES, {'C2': 0., 'C3': .02})
        self.assertEqual((START, END), ('2023-06-20', '2026-08-28'))


if __name__ == '__main__':
    unittest.main()
