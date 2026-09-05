"""Independent cash/units/bisection reference for the preregistered F3 policy."""
import unittest
import numpy as np
from audit.test_account_ledger import trade_reference
from research import account_ledger as L
from research import execution_policy as P


def policy_reference(held, basis, cash, target, fee, rate, band, attack_index=0):
    """Scalar deficits and trigger; full trades use independent budget bisection."""
    h, b, p = (np.asarray(x, float) for x in (held, basis, target))
    spend = cash/(1+fee)
    deficits = [max((sum(h)+spend)*float(t)-float(v), 0.) for t, v in zip(p, h)]
    denom = sum(deficits)
    buys = np.array([spend*x/denom if denom else 0. for x in deficits])
    hypothetical = h+buys
    value = float(sum(hypothetical))
    gap = sum(abs(float(v)/value-float(t)) for v, t in zip(hypothetical, p))/2 if value else 0.
    force = p[attack_index] == 0 and h[attack_index] > 0
    if band == 0 or gap > band or force:
        new, basis_out, fees, taxes = trade_reference(h, b, cash, p, fee, rate)
    else:
        new, basis_out = hypothetical, np.where(h > 0, b, 0.)+buys*(1+fee)
        fees, taxes = fee*float(sum(buys)), 0.
    moved = float(sum(abs(new-h)))
    wealth = float(sum(h)+cash)
    return dict(held=new, basis=basis_out, cash=0., fees=fees, taxes=taxes,
                traded=moved > wealth*1e-12, turnover=moved/(2*wealth) if wealth else 0.)


def units_reference(p, r, mask, start, end, days, payments, initial, fee, rate, dist,
                    band, attack_index=0):
    """Scalar shares valued at changing prices, no production policy/recurrence."""
    price = np.ones(r.shape[1])
    units = initial*p[start].copy()
    basis, cash = units.copy(), 0.
    funding = {}
    for day, amount in zip(days, payments):
        funding[int(day)] = funding.get(int(day), 0.)+float(amount)
    fees = taxes = turnover = exposure = maxgap = 0.
    path, trade_dates = [initial], []
    force_violations = cash_violations = 0
    for day in range(start+1, end+1):
        held = units*price
        if mask[day] and sum(held)+cash > 0:
            q = policy_reference(held, basis, cash, p[day], fee, rate, band, attack_index)
            units = q['held']/price
            basis, cash = q['basis'], q['cash']
            fees += q['fees']; taxes += q['taxes']; turnover += q['turnover']
            if q['traded']:
                trade_dates.append(day)
            force_violations += int(p[day, attack_index] == 0 and units[attack_index] != 0)
            cash_violations += int(cash != 0)
        held = units*price
        value = float(sum(held)+cash)
        if value:
            exposure += held[attack_index]/value
            gap = (sum(abs(held/value-p[day]))+cash/value)/2
            maxgap = max(maxgap, gap)
        for a in range(len(units)):
            price[a] *= 1+r[day, a]
            held_value = units[a]*price[a]
            if not held_value:
                basis[a] = 0.
            dividend = held_value*dist[day, a]
            withheld = dividend*rate
            units[a] -= withheld/price[a]
            basis[a] += dividend-withheld
            taxes += withheld
        cash += funding.get(day, 0.)
        path.append(units@price+cash)
    return dict(held=units*price, basis=basis, cash=cash, fees=fees, taxes=taxes,
                wealth=units@price+cash, paths=np.array(path), trade_days=len(trade_dates),
                turnover=turnover, mean_attack_exposure=exposure/max(end-start, 1),
                max_target_gap=maxgap, forced_defense_violations=force_violations,
                uninvested_cash_violations=cash_violations,
                closed_day_trade_violations=sum(not mask[t] for t in trade_dates))


class CashFirstPolicy(unittest.TestCase):
    def test_exact_band_boundary_is_no_trade(self):
        args = ([[62.5, 37.5]], [[50., 50.]], [0.], [[.5, .5]])
        q = P.policy_trade(*args, fee=0., band=.125)
        self.assertFalse(q['traded'][0])
        np.testing.assert_array_equal(q['held'], args[0])
        q = P.policy_trade(*args, fee=0., band=np.nextafter(.125, 0.))
        self.assertTrue(q['traded'][0])
        np.testing.assert_array_equal(q['held'], [[50., 50.]])

    def test_cash_purchase_reduces_gap_without_sale(self):
        q = P.policy_trade([[60., 40.]], [[20., 35.]], [10.1], [[.5, .5]],
                           fee=.01, tax_rate=.2, band=.10)
        np.testing.assert_allclose(q['held'], [[60., 50.]])
        np.testing.assert_allclose(q['basis'], [[20., 45.1]])
        self.assertAlmostEqual(q['fees'][0], .1)
        self.assertEqual(q['taxes'][0], 0.)
        self.assertEqual(q['sold'].sum(), 0.)
        self.assertFalse(q['full_rebalance'][0])
        self.assertEqual(q['cash'][0], 0.)

    def test_full_trade_uses_original_cash_and_charges_once(self):
        args = ([[90., 10.]], [[20., 7.]], [10.1], [[.5, .5]])
        q = P.policy_trade(*args, fee=.01, tax_rate=.2, band=.1)
        expected = L.rebalance(*args, fee=.01, tax_rate=.2)
        for key in expected:
            np.testing.assert_array_equal(q[key], expected[key])
        self.assertTrue(q['full_rebalance'][0])

    def test_full_defense_override_even_inside_band(self):
        q = P.policy_trade([[.01, 99.99]], [[.005, 99.99]], [0.], [[0., 1.]], band=.99)
        self.assertEqual(q['held'][0, 0], 0.)
        self.assertTrue(q['forced_defense'][0])

    def test_partial_parent_target_and_full_attack_have_no_override(self):
        q = P.policy_trade([[20., 80.], [99., 1.]], [[20., 80.], [99., 1.]],
                           [0., 0.], [[.15, .85], [1., 0.]], band=.1)
        np.testing.assert_array_equal(q['held'], [[20., 80.], [99., 1.]])
        self.assertFalse(q['forced_defense'].any())
        self.assertFalse(q['traded'].any())

    def test_zero_initial_cash_only_purchase_and_zero_account(self):
        q = P.policy_trade([[0., 0.], [0., 0.]], [[9., 8.], [0., 0.]],
                           [101., 0.], [[.6, .4], [.6, .4]], fee=.01)
        np.testing.assert_allclose(q['held'], [[60., 40.], [0., 0.]])
        np.testing.assert_allclose(q['basis'], [[60.6, 40.4], [0., 0.]])
        np.testing.assert_array_equal(q['traded'], [True, False])

    def test_random_policy_matches_scalar_budget_and_conserves_cash(self):
        rng = np.random.default_rng(3901)
        for assets in (2, 4, 7):
            h = rng.uniform(0, 10000, (40, assets)); h[rng.random(h.shape) < .15] = 0
            b = h*rng.uniform(0., 2., h.shape)
            cash = rng.uniform(0, 1000, len(h)); cash[:10] = 0
            p = rng.dirichlet(np.ones(assets), len(h))
            bands = rng.uniform(.05, .4, len(h)); bands[:5] = 0
            original = [a.copy() for a in (h, b, cash, p)]
            for fee, rate in ((0., 0.), (.001, .154), (.1, .7)):
                q = P.policy_trade(h, b, cash, p, fee, rate, bands)
                for j in range(len(h)):
                    ref = policy_reference(h[j], b[j], cash[j], p[j], fee, rate, bands[j])
                    for key in ('held', 'basis', 'cash', 'fees', 'taxes', 'traded', 'turnover'):
                        np.testing.assert_allclose(q[key][j], ref[key], rtol=2e-11, atol=1e-8)
                np.testing.assert_allclose(q['held'].sum(axis=1)+q['fees']+q['taxes'],
                                           h.sum(axis=1)+cash, rtol=1e-12, atol=1e-10)
            for arr, before in zip((h, b, cash, p), original):
                np.testing.assert_array_equal(arr, before)

    def test_invalid_trade_inputs_fail_closed(self):
        args = ([[1., 1.]], [[1., 1.]], [0.], [[.5, .5]])
        for kwargs in ({'band': -1.}, {'band': 1.}, {'band': np.nan}, {'band': [0., .1]},
                       {'attack_index': True}, {'attack_index': 2}, {'attack_index': .5},
                       {'fee': 1.}, {'tax_rate': np.inf}):
            with self.assertRaises(ValueError):
                P.policy_trade(*args, **kwargs)
        for bad in (([[1, -1]], args[1], args[2], args[3]),
                    (args[0], args[1], [-1], args[3]),
                    (args[0], args[1], args[2], [[.5, .4]])):
            with self.assertRaises(ValueError):
                P.policy_trade(*bad)


class IndependentWindows(unittest.TestCase):
    @staticmethod
    def material():
        rng = np.random.default_rng(3992)
        n = 73
        p = rng.dirichlet([2., 3., 1.], n)
        p[12:15] = [0., .7, .3]; p[31:40] = [1., 0., 0.]
        r = rng.normal(.001, .035, (n, 3))
        mask = np.arange(n) % 4 != 2
        s, e = np.array([0, 5, 20, 30]), np.array([72, 51, 65, 60])
        d = np.vstack([s+1, s+8, e])
        money = np.array([[500., 0., 320., 110.], [230., 480., 0., 570.], [300., 360., 920., 40.]])
        initial = np.array([10000., 0., 7700., 2200.])
        dist = np.full_like(r, .00015)
        return p, r, mask, s, e, d, money, initial, dist

    def test_zero_band_exact_reduction_all_existing_account_outputs(self):
        p, r, mask, s, e, d, money, initial, dist = self.material()
        for fee, rate in ((0., 0.), (.001, .154), (.002, 0.)):
            args = (p, r, mask, s, e, d, money, initial, fee, rate, dist, True)
            got, old = P.account_windows(*args, band=0.), L.account_windows(*args)
            for key in old:
                np.testing.assert_array_equal(got[key], old[key])

    def test_all_bands_match_independent_units_cash_and_tax(self):
        p, r, mask, s, e, d, money, initial, dist = self.material()
        for bands in (np.zeros(4), np.array([.05, .1, .15, .3])):
            for fee, rate in ((0., 0.), (.001, .154), (.002, .154)):
                got = P.account_windows(p, r, mask, s, e, d, money, initial, fee, rate, dist, True, bands)
                for j in range(len(s)):
                    ref = units_reference(p, r, mask, int(s[j]), int(e[j]), d[:, j], money[:, j],
                                          initial[j], fee, rate, dist, bands[j])
                    for key, value in ref.items():
                        actual = got[key][:int(e[j]-s[j])+1, j] if key == 'paths' else got[key][j]
                        np.testing.assert_allclose(actual, value, rtol=2e-11, atol=1e-8)
                for key in ('forced_defense_violations', 'uninvested_cash_violations', 'closed_day_trade_violations'):
                    self.assertEqual(got[key].sum(), 0)

    def test_funding_after_return_waits_next_eligible_and_end_cash_stays_cash(self):
        p = np.tile([1., 0.], (5, 1)); r = np.array([[0., 0.], [1., 0.], [1., 0.], [1., 0.], [1., 0.]])
        mask = np.array([True, True, False, True, True])
        q = P.account_windows(p, r, mask, [0], [4], np.array([[1], [4]]), [100., 80.],
                              0., fee=0., record_paths=True)
        np.testing.assert_array_equal(q['paths'][:, 0], [0., 100., 100., 200., 480.])
        self.assertEqual(q['cash'][0], 80.)
        self.assertEqual(q['trade_days'][0], 1)

    def test_defense_override_waits_for_actual_trade_day(self):
        p = np.array([[1., 0.], [0., 1.], [0., 1.]])
        r = np.array([[0., 0.], [-.5, 0.], [.8, 0.]])
        q = P.account_windows(p, r, np.array([True, False, True]), [0], [2],
                              np.empty((0, 1), int), [], 100., fee=0., band=.99, record_paths=True)
        np.testing.assert_array_equal(q['paths'][:, 0], [100., 50., 50.])
        self.assertEqual(q['held'][0, 0], 0.)
        self.assertEqual(q['max_target_gap'][0], 1.)

    def test_total_returns_do_not_double_add_distribution(self):
        p = np.tile([.5, .5], (3, 1)); r = np.zeros_like(p)
        dist = np.full_like(p, .1)
        q = P.account_windows(p, r, np.ones(3, bool), [0], [2], np.empty((0, 1), int), [],
                              100., fee=0., tax_rate=.2, distribution_rates=dist)
        self.assertAlmostEqual(q['wealth'][0], 100*.98**2)
        self.assertAlmostEqual(q['taxes'][0], 100*(1-.98**2))
        self.assertAlmostEqual(q['basis'].sum(), 100+100*.08+98*.08)

    def test_start_zero_no_deposit_reduces_to_gross_and_fresh_slice_differs(self):
        p, r, mask, _, _, _, _, _, _ = self.material()
        # F3's four parents all use attack plus the same aggregate defense asset.
        p[:, 1] = 1-p[:, 0]; p[:, 2] = 0.
        w = p[:, :1]
        batch = P.gross_batch(w, r, mask, band=.10)
        q = P.account_windows(p, r, mask, [0], [72], np.empty((0, 1), int), [],
                              1., record_paths=True, band=.10)
        np.testing.assert_array_equal(q['paths'], batch['curves'])
        for key in ('trade_days', 'turnover', 'mean_attack_exposure', 'max_target_gap'):
            np.testing.assert_array_equal(q[key], batch[key])
        fresh = P.account_windows(p, r, mask, [4], [17], np.empty((0, 1), int), [], 1., band=.10)
        self.assertGreater(abs(fresh['wealth'][0]-batch['curves'][17, 0]/batch['curves'][4, 0]), 1e-6)

    def test_zero_length_and_duplicate_payment_dates(self):
        p = np.tile([.6, .4], (3, 1)); r = np.zeros_like(p); mask = np.ones(3, bool)
        q = P.account_windows(p, r, mask, [1], [1], np.empty((0, 1), int), [], 13., record_paths=True)
        self.assertEqual(q['wealth'][0], 13.)
        self.assertEqual(q['paths'].shape, (1, 1))
        q = P.account_windows(p, r, mask, [0], [2], np.array([[1], [1]]), [7., 9.], 0., fee=0.)
        self.assertAlmostEqual(q['wealth'][0], 16.)
        self.assertEqual(q['contributions'][0], 16.)

    def test_gross_batched_bands_match_single_and_constant_hold(self):
        p, r, mask, *_ = self.material()
        bands = np.array([0., .05, .10, .15])
        w = np.tile(p[:, :1], (1, 4))
        q = P.gross_batch(w, r, mask, band=bands)
        for j, band in enumerate(bands):
            single = P.gross_batch(w[:, j:j+1], r, mask, band=band)
            for key in q:
                np.testing.assert_array_equal(q[key][:, j] if key == 'curves' else q[key][j],
                                              single[key][:, 0] if key == 'curves' else single[key][0])
        hold = P.gross_batch(np.ones_like(w), r, mask, band=bands)
        expected = np.cumprod(np.r_[1., 1+r[1:, 0]])
        np.testing.assert_allclose(hold['curves'], np.tile(expected[:, None], (1, 4)), rtol=1e-14)
        self.assertEqual(hold['trade_days'].sum(), 0)

    def test_bad_windows_and_batches_fail_closed(self):
        p, r, mask, s, e, d, money, initial, dist = self.material()
        with self.assertRaises(ValueError):
            P.account_windows(p, r, mask.astype(int), s, e, d, money, initial)
        with self.assertRaises(ValueError):
            P.account_windows(p, r, mask, s, e, d-100, money, initial)
        with self.assertRaises(ValueError):
            P.account_windows(p, r, mask, s, e, d, -money, initial)
        with self.assertRaises(ValueError):
            P.account_windows(p, r, mask, s, e, d, money, initial, distribution_rates=dist+1)
        with self.assertRaises(ValueError):
            P.gross_batch(p[:, :1], r, mask, safe_index=0)
        with self.assertRaises(ValueError):
            P.gross_batch(p[:, :1]+1, r, mask)


if __name__ == '__main__':
    unittest.main()
