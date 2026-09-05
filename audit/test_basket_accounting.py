"""Independent scalar-unit checks for F4-A; no market or personal data."""
import unittest
import numpy as np
from research import basket_accounting as B
from research import account_ledger as L
from audit.test_account_ledger import trade_reference


def units_reference(w, r, mask, review, start, end, ds, pay, initial,
                    fee=.001, rate=0., dist=None, threshold=0.):
    prices = np.ones(4)
    units = initial*np.array([w[start], .4*(1-w[start]), .4*(1-w[start]), .2*(1-w[start])])
    basis = units.copy()
    cash = fees = taxes = 0.
    payments = {}
    for d, x in zip(ds, pay):
        payments[int(d)] = payments.get(int(d), 0.)+float(x)
    dist = np.zeros_like(r) if dist is None else dist
    paths, traded_dates = [initial], []
    for day in range(start+1, end+1):
        values = units*prices
        total = float(sum(values)+cash)
        target = np.array([w[day], .4*(1-w[day]), .4*(1-w[day]), .2*(1-w[day])])
        gap = max(abs(values/total-target)) if total else 0.
        switch = w[day] != w[day-1]
        check = not w[day] and review[day] and gap > threshold
        if mask[day] and total and (switch or cash > 0 or check):
            nh, nb, f, t = trade_reference(values, basis, cash, target, fee, rate)
            if sum(abs(nh-values)) > total*1e-12:
                traded_dates.append(day)
            units, basis = nh/prices, nb
            cash = 0.; fees += f; taxes += t
        prices *= 1+r[day]
        dividend = units*prices*dist[day]
        withholding = dividend*rate
        units -= withholding/prices
        basis += dividend-withholding
        taxes += sum(withholding)
        cash += payments.get(day, 0.)
        paths.append(sum(units*prices)+cash)
    return dict(wealth=sum(units*prices)+cash, held=units*prices, basis=basis,
                cash=cash, fees=fees, taxes=taxes, paths=np.array(paths),
                trade_count=len(traded_dates), traded_dates=traded_dates)


class BasketTests(unittest.TestCase):
    def toy(self, w, r, review=None, mask=None, fee=0., tax_rate=0., threshold=0.,
            starts=None, ends=None, ds=None, pay=None, initial=100., dist=None):
        n = len(w)
        mask = np.ones(n, bool) if mask is None else mask
        review = np.zeros(n, bool) if review is None else review
        starts = np.array([0], int) if starts is None else starts
        ends = np.array([n-1], int) if ends is None else ends
        ds = np.empty((0, len(starts)), int) if ds is None else ds
        pay = [] if pay is None else pay
        return B.account_windows(w, r, mask, review, starts, ends, ds, pay, initial,
                                 fee, tax_rate, dist, threshold, True)

    def test_no_free_daily_rebalance(self):
        r = np.zeros((3, 4)); r[1, 1] = 1.; r[2, 1] = -.5
        a = self.toy(np.zeros(3), r)
        np.testing.assert_allclose(a['paths'][:, 0], [100., 140., 100.])
        self.assertEqual(a['trade_count'][0], 0)

    def test_review_changes_holdings(self):
        r = np.zeros((3, 4)); r[1, 1] = 1.; r[2, 1] = -.5
        a = self.toy(np.zeros(3), r, np.array([False, False, True]))
        self.assertAlmostEqual(a['wealth'][0], 112.)
        self.assertEqual(a['review_trade_count'][0], 1)

    def test_threshold_is_strict(self):
        # Pin the exact computed boundary, then one float below it: >, not >=.
        r = np.zeros((3, 4)); r[1] = [0., .5, 0., 0.]
        boundary = float(np.max(abs(np.array([0., 60., 40., 20.])/120.-[0., .4, .4, .2])))
        at = self.toy(np.zeros(3), r, np.array([False, False, True]), threshold=boundary)
        below = self.toy(np.zeros(3), r, np.array([False, False, True]),
                         threshold=np.nextafter(boundary, 0.))
        self.assertEqual(at['trade_count'][0], 0)
        self.assertEqual(below['trade_count'][0], 1)

    def test_deposit_after_return_and_holiday(self):
        r = np.zeros((5, 4)); r[:, 0] = .1
        a = self.toy(np.ones(5), r, mask=np.array([False, True, False, True, True]),
                     ds=np.array([[1], [4]]), pay=[50., 20.], initial=0.)
        self.assertAlmostEqual(a['wealth'][0], 80.5)
        self.assertEqual(a['cash'][0], 20.)
        self.assertEqual(a['trade_count'][0], 1)

    def test_binary_switch_mandatory_with_high_threshold(self):
        a = self.toy(np.array([1., 0., 0., 1.]), np.zeros((4, 4)), threshold=.9)
        self.assertEqual(a['switch_trade_count'][0], 2)

    def test_attack_only_reduces_to_old_ledger(self):
        rng = np.random.default_rng(20260905)
        w = np.ones(70); r = rng.normal(.002, .02, (70, 4))
        mask = np.arange(70) % 5 != 2
        ds, pay = np.array([[5, 10], [40, 50]]), [11., 17.]
        a = self.toy(w, r, mask=mask, starts=np.array([0, 7]), ends=np.array([60, 69]),
                     ds=ds, pay=pay, fee=.002, tax_rate=.154)
        p = np.column_stack([w, w*0, w*0, w*0])
        old = L.account_windows(p, r, mask, [0, 7], [60, 69], ds, pay, 100., .002, .154, record_paths=True)
        for k in ('wealth', 'held', 'basis', 'cash', 'fees', 'taxes', 'paths'):
            np.testing.assert_allclose(a[k], old[k], rtol=2e-12, atol=1e-12)

    def test_tax_aggregation_counterexample(self):
        # Sale to cash-like third asset: +20 and -20 are not cross-asset netted.
        split = L.rebalance([[120., 80., 0.]], [[100., 100., 0.]], [0.], [[0., 0., 1.]], 0., .154)
        aggregate = L.rebalance([[200., 0.]], [[200., 0.]], [0.], [[0., 1.]], 0., .154)
        self.assertAlmostEqual(split['taxes'][0], 3.08)
        self.assertEqual(aggregate['taxes'][0], 0.)

    def test_total_return_distribution_not_added_twice(self):
        r = np.zeros((2, 4)); r[1, 1] = .1
        dist = np.zeros_like(r); dist[1, 1] = .02
        a = self.toy(np.zeros(2), r, tax_rate=.154, dist=dist)
        self.assertAlmostEqual(a['wealth'][0], 104.-44.*.02*.154)
        self.assertAlmostEqual(a['basis'][0].sum(), 100.+44.*.02*(1-.154))

    def test_independent_random_windows(self):
        rng = np.random.default_rng(43020260905)
        for trial in range(12):
            n = 125
            mask = rng.random(n) > .2
            w = np.ones(n)
            for d in range(1, n):
                w[d] = 1-w[d-1] if mask[d] and rng.random() < .08 else w[d-1]
            review = mask & (np.arange(n) % 11 == 0)
            r = rng.normal(.001, .035, (n, 4))
            dist = np.zeros_like(r); dist[:, 1] = .025/252
            s, e = np.array([0, 11, 25]), np.array([88, 116, 124])
            ds = np.array([s+10, s+45, e]); pay = np.array([11., 23., 7.])
            fee, rate, threshold = .002, .154, [0., .02][trial % 2]
            a = self.toy(w, r, review, mask, fee, rate, threshold, s, e, ds, pay,
                         initial=np.array([0., 100., 311.]), dist=dist)
            for j in range(3):
                ref = units_reference(w, r, mask, review, s[j], e[j], ds[:, j], pay,
                                      [0., 100., 311.][j], fee, rate, dist, threshold)
                for k in ('wealth', 'held', 'basis', 'cash', 'fees', 'taxes', 'trade_count'):
                    np.testing.assert_allclose(a[k][j], ref[k], rtol=2e-11, atol=1e-10)
                np.testing.assert_allclose(a['paths'][:e[j]-s[j]+1, j], ref['paths'], rtol=2e-11)
                np.testing.assert_allclose(a['paths'][e[j]-s[j]:, j], ref['wealth'], rtol=2e-11)
                self.assertTrue(all(mask[d] for d in ref['traded_dates']))

    def test_overlapping_triggers_charge_once(self):
        w = np.array([1., 1., 0.]); r = np.zeros((3, 4))
        review = np.array([False, False, True])
        a = self.toy(w, r, review, fee=.002, ds=np.array([[1]]), pay=[10.])
        b = self.toy(w, r, fee=.002, ds=np.array([[1]]), pay=[10.])
        for k in ('wealth', 'held', 'basis', 'fees', 'taxes', 'trade_count'):
            np.testing.assert_array_equal(a[k], b[k])
        self.assertEqual(a['trade_count'][0], 1)
        for k in ('review_trade_count', 'cash_trade_count', 'switch_trade_count'):
            self.assertEqual(a[k][0], 1)

    def test_duplicate_deposit_dates_accumulate(self):
        a = self.toy(np.ones(3), np.zeros((3, 4)), initial=0.,
                     ds=np.array([[1], [1], [2]]), pay=[10., 20., 7.])
        self.assertEqual(a['wealth'][0], 37.)
        self.assertEqual(a['held'][0, 0], 30.)
        self.assertEqual(a['cash'][0], 7.)
        self.assertEqual(a['contributions'][0], 37.)

    def test_fresh_defense_window_keeps_known_calendar(self):
        dates = np.arange('2026-01-29', '2026-03-31', dtype='datetime64[D]')
        ordinal = dates.astype(int); mask = ((ordinal+3) % 7) < 5
        anchor = np.full(len(dates), np.datetime64('2026-01-01', 'D').astype(int))
        review = B.review_schedule(dates, mask, anchor, 'signal30')
        np.testing.assert_array_equal(dates[review],
                                      np.array(['2026-02-02', '2026-03-02'], dtype='datetime64[D]'))

    def test_review_clocks_monthend_holiday_and_reentry(self):
        dates = np.arange('2026-01-29', '2026-04-12', dtype='datetime64[D]')
        ordinal = dates.astype(int)
        mask = ((ordinal+3) % 7) < 5
        anchor = np.full(len(dates), ordinal[0], int)
        month = B.review_schedule(dates, mask, anchor, 'monthly')
        thirty = B.review_schedule(dates, mask, anchor, 'signal30')
        self.assertEqual(dates[month][0], np.datetime64('2026-02-02'))
        self.assertEqual(dates[thirty][0], np.datetime64('2026-03-02'))
        self.assertEqual(dates[thirty][1], np.datetime64('2026-03-30'))
        anchor[dates >= np.datetime64('2026-03-10')] = -1
        anchor[dates >= np.datetime64('2026-03-12')] = np.datetime64('2026-03-12', 'D').astype(int)
        fresh = B.review_schedule(dates, mask, anchor, 'signal30')
        self.assertEqual(int(fresh.sum()), 1)  # New due date Apr 11, a Saturday; Apr 13 not present.

    def test_invalid_inputs_fail_closed(self):
        for bad in [np.array([1., .5]), np.array([1., np.nan])]:
            with self.assertRaises(ValueError): self.toy(bad, np.zeros((2, 4)))
        with self.assertRaises(ValueError):
            self.toy(np.array([1., 0.]), np.zeros((2, 4)), mask=np.zeros(2, bool))
        with self.assertRaises(ValueError):
            self.toy(np.ones(2), np.zeros((2, 4)), np.ones(2, bool), np.zeros(2, bool))
        with self.assertRaises(ValueError):
            B.review_schedule(np.array(['2026-01-01'], dtype='datetime64[D]'), [True], [30000])


if __name__ == '__main__':
    unittest.main()
