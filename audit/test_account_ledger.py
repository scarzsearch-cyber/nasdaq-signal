"""Independent monetary/bisection checks for research.account_ledger."""
import unittest
import numpy as np
from research.account_ledger import rebalance, account_windows


def trade_reference(h, basis, cash, weights, fee, rate):
    """Scalar cash-budget bisection, deliberately not the production active set."""
    h, basis, weights = (np.asarray(x, float) for x in (h, basis, weights))
    total = float(h.sum()+cash)
    if cash == 0 and np.array_equal(h, total*weights):
        return h.copy(), np.where(h > 0, basis, 0.), 0., 0.
    def charges(value):
        sold, bought, gains, new_basis = [], [], [], []
        for asset in range(len(h)):
            target = value*weights[asset]
            sale = max(h[asset]-target, 0.)
            buy = max(target-h[asset], 0.)
            released = basis[asset]*sale/h[asset] if h[asset] else 0.
            gains.append(max(sale*(1-fee)-released, 0.))
            sold.append(sale); bought.append(buy)
            kept = basis[asset]-released if h[asset] else 0.
            new_basis.append(kept+buy*(1+fee))
        costs = fee*(sum(sold)+sum(bought))
        taxes = rate*sum(gains)
        return costs, taxes, np.array(new_basis)
    low, high = 0., total
    for _ in range(65):
        mid = (low+high)/2
        costs, taxes, _ = charges(mid)
        if mid+costs+taxes > total:
            high = mid
        else:
            low = mid
    value = (low+high)/2
    costs, taxes, new_basis = charges(value)
    return value*weights, new_basis, costs, taxes


def path_reference(p, r, mask, start, end, days, payments, initial, fee, rate, dist):
    """Single account, scalar dates and independent trade/cash recurrence."""
    funding = {}
    for day, amount in zip(days, payments):
        funding[int(day)] = funding.get(int(day), 0.)+float(amount)
    h = initial*p[start].copy()
    basis, cash = h.copy(), 0.
    total_fee = total_tax = 0.
    path = [initial]
    for day in range(start+1, end+1):
        if mask[day] and h.sum()+cash > 0:
            h, basis, paid_fee, paid_tax = trade_reference(h, basis, cash, p[day], fee, rate)
            cash = 0.; total_fee += paid_fee; total_tax += paid_tax
        for asset in range(len(h)):
            h[asset] *= 1+r[day, asset]
            if not h[asset]:
                basis[asset] = 0.
            distributed = h[asset]*dist[day, asset]
            withheld = distributed*rate
            h[asset] -= withheld
            basis[asset] += distributed-withheld
            total_tax += withheld
        cash += funding.get(day, 0.)
        path.append(h.sum()+cash)
    return dict(held=h, basis=basis, cash=cash, fees=total_fee, taxes=total_tax,
                wealth=h.sum()+cash, paths=np.array(path))


class TradeCashConservation(unittest.TestCase):
    def test_full_sale_hand_ledger(self):
        got = rebalance([[200., 0.]], [[100., 0.]], [0.], [[0., 1.]], fee=.01, tax_rate=.2)
        # Sale proceeds 198, gain 98, tax 19.6; remaining 178.4 funds buy+1% fee.
        want = 178.4/1.01
        self.assertAlmostEqual(got['held'][0, 1], want)
        self.assertAlmostEqual(got['taxes'][0], 19.6)
        self.assertAlmostEqual(got['basis'][0, 1], 178.4)
        self.assertAlmostEqual(got['fees'][0], 2.+want*.01)

    def test_partial_sale_includes_extra_sale_to_pay_tax(self):
        got = rebalance([[200., 0.]], [[100., 0.]], [0.], [[.5, .5]], fee=0., tax_rate=.2)
        # N = 200 - .1*(200 - N/2), not 190 with a later untracked tax sale.
        net = 180/.95
        self.assertAlmostEqual(got['held'].sum(), net)
        self.assertAlmostEqual(got['basis'][0, 0], net/4)
        self.assertAlmostEqual(got['basis'][0, 1], net/2)
        self.assertGreater(got['sold'][0, 0], 100.)

    def test_no_loss_offset_and_retained_basis(self):
        got = rebalance([[80., 100., 0.]], [[100., 50., 0.]], [0.], [[0., 0., 1.]], fee=0., tax_rate=.2)
        self.assertAlmostEqual(got['taxes'][0], 10.)  # Loss in first asset cannot offset second.
        loss = rebalance([[80., 0.]], [[100., 0.]], [0.], [[.5, .5]], fee=0., tax_rate=.2)
        np.testing.assert_allclose(loss['basis'], [[50., 40.]])
        self.assertEqual(loss['taxes'][0], 0.)

    def test_existing_cash_buys_without_forced_sale(self):
        got = rebalance([[50., 0.]], [[20., 0.]], [50.], [[.5, .5]], fee=0., tax_rate=.2)
        np.testing.assert_array_equal(got['sold'], [[0., 0.]])
        np.testing.assert_array_equal(got['basis'], [[20., 50.]])
        self.assertEqual(got['taxes'][0], 0.)

    def test_random_trades_match_independent_budget_solution(self):
        rng = np.random.default_rng(9215)
        for k in (1, 2, 4, 9):
            n = 25
            h = rng.uniform(0., 1e7, (n, k)); h[rng.random(h.shape) < .2] = 0.
            b = h*rng.uniform(0., 2., h.shape)
            c = rng.uniform(0., 1e6, n); c[:5] = 0.
            p = rng.dirichlet(np.ones(k), n)
            for fee, rate in ((0., 0.), (.001, .154), (.2, .7)):
                got = rebalance(h, b, c, p, fee, rate)
                for j in range(n):
                    rh, rb, rf, rt = trade_reference(h[j], b[j], c[j], p[j], fee, rate)
                    for actual, expected in ((got['held'][j], rh), (got['basis'][j], rb),
                                             (got['fees'][j], rf), (got['taxes'][j], rt)):
                        np.testing.assert_allclose(actual, expected, rtol=1e-11, atol=1e-7)

    def test_invalid_inputs_fail_closed(self):
        args = ([[1., 1.]], [[1., 1.]], [0.], [[.5, .5]])
        for fee, rate in ((-.1, 0.), (1., 0.), (.001, float('nan'))):
            with self.assertRaises(ValueError):
                rebalance(*args, fee=fee, tax_rate=rate)
        with self.assertRaises(ValueError):
            rebalance([[1.]], [[-1.]], [0.], [[1.]])

    def test_exact_unchanged_holdings_have_zero_tax_and_fees(self):
        for value in (12345678.9012345, 3e8, 1e12):
            h, basis, p = [value, 0.], [100., 0.], [1., 0.]
            got = rebalance([h], [basis], [0.], [p])
            np.testing.assert_array_equal(got['held'][0], h)
            np.testing.assert_array_equal(got['basis'][0], basis)
            self.assertEqual(got['taxes'][0], 0.)
            self.assertEqual(got['fees'][0], 0.)
            _, _, fee, tax = trade_reference(h, basis, 0., p, .001, .154)
            self.assertEqual(fee, 0.)
            self.assertEqual(tax, 0.)

    def test_near_target_boundary_converges_at_doubled_fees(self):
        rng = np.random.default_rng(215)
        p = rng.dirichlet(np.ones(4), 100)
        h = rng.uniform(1e6, 1e10, 100)[:, None]*p
        h[::2, 0] = np.nextafter(h[::2, 0], np.inf)
        basis = h*.6
        for fee in (.001, .002, .2):
            got = rebalance(h, basis, np.zeros(100), p, fee, .154)
            for j in range(100):
                rh, rb, rf, rt = trade_reference(h[j], basis[j], 0., p[j], fee, .154)
                np.testing.assert_allclose(got['held'][j], rh, rtol=1e-12, atol=1e-6)
                np.testing.assert_allclose(got['basis'][j], rb, rtol=1e-12, atol=1e-6)
                self.assertLess(abs(got['fees'][j]-rf), 1e-5)
                self.assertLess(abs(got['taxes'][j]-rt), 1e-5)


class FundingCashLedger(unittest.TestCase):
    def test_no_returns_cash_is_conserved_with_end_day_deposit(self):
        p = np.tile([1., 0.], (4, 1)); r = np.zeros_like(p)
        got = account_windows(p, r, [False, True, False, True], [0], [3],
                              [[1], [3]], [100., 100.], 100., fee=0., tax_rate=.154, record_paths=True)
        np.testing.assert_array_equal(got['paths'][:, 0], [100., 200., 200., 300.])
        self.assertEqual(got['cash'][0], 100.)
        self.assertEqual(got['taxes'][0], 0.)

    def test_holiday_cash_cannot_earn_asset_return(self):
        p = np.ones((4, 1)); r = np.array([[0.], [0.], [1.], [.1]])
        got = account_windows(p, r, [False, True, False, True], [0], [3], [[1]], [100.],
                              0., fee=0., record_paths=True)
        np.testing.assert_allclose(got['paths'][:, 0], [0., 100., 100., 110.])

    def test_zero_cost_no_deposits_reduces_to_scheduled_gross(self):
        from research.rebalance_accounting import scheduled_path
        rng = np.random.default_rng(92)
        p = rng.dirichlet(np.ones(4), 80); r = rng.uniform(-.1, .1, p.shape)
        mask = rng.random(80) < .5
        got = account_windows(p, r, mask, [0], [79], np.empty((0, 1), int), [],
                              100., fee=0., record_paths=True)
        expected, _ = scheduled_path(p, r, mask, cost=0.)
        np.testing.assert_allclose(got['paths'][:, 0], 100*expected, rtol=1e-12)

    def test_total_return_distribution_is_not_double_added(self):
        p = np.ones((2, 1)); r = np.array([[0.], [.1]])
        dist = np.array([[0.], [10/110]])
        got = account_windows(p, r, [False, True], [0], [1], np.empty((0, 1), int), [],
                              100., fee=0., tax_rate=.2, distribution_rates=dist)
        self.assertAlmostEqual(got['wealth'][0], 108.)
        self.assertAlmostEqual(got['basis'][0, 0], 108.)
        self.assertAlmostEqual(got['taxes'][0], 2.)

    def test_many_windows_match_independent_cash_ledgers(self):
        rng = np.random.default_rng(9216)
        p = rng.dirichlet(np.ones(3), 35); r = rng.uniform(-.12, .12, p.shape)
        mask = rng.random(35) < .6; dist = rng.uniform(0., .002, p.shape)
        starts, ends = np.array([0, 2, 5, 10]), np.array([25, 30, 25, 32])
        days = starts+np.array([[2], [6], [12]])
        payments = np.array([100., 300., 500.])
        for fee, rate in ((0., 0.), (.001, .154), (.02, .4)):
            got = account_windows(p, r, mask, starts, ends, days, payments, 1000., fee, rate,
                                  distribution_rates=dist, record_paths=True)
            for j, (s, e) in enumerate(zip(starts, ends)):
                ref = path_reference(p, r, mask, s, e, days[:, j], payments, 1000., fee, rate, dist)
                for name in ('held', 'basis', 'cash', 'fees', 'taxes', 'wealth'):
                    np.testing.assert_allclose(got[name][j], ref[name], rtol=1e-11, atol=1e-8)
                np.testing.assert_allclose(got['paths'][:e-s+1, j], ref['paths'], rtol=1e-11)

    def test_bad_funding_or_calendars_rejected(self):
        p, r = np.ones((3, 1)), np.zeros((3, 1))
        for days, money in (([[0]], [10.]), ([[3]], [10.]), ([[1]], [-1.])):
            with self.assertRaises(ValueError):
                account_windows(p, r, [False, True, True], [0], [2], days, money, 1.)

    def test_liquidated_asset_is_not_silently_recapitalized(self):
        with self.assertRaises(ValueError):
            account_windows(np.ones((3, 1)), np.array([[0.], [-1.], [1.]]),
                            [False, True, True], [0], [2], [[1]], [100.], 100.)


if __name__ == '__main__':
    unittest.main()
