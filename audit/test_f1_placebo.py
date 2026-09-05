"""Synthetic falsification-method checks; no market files or random study run."""
import unittest
import numpy as np
import pandas as pd
from research.strategy_f1_placebo import (annual_permutations, holm_adjust, tail_probability,
    gross_batch, units_reference, make_positions, random_intervals)
from research.account_ledger import account_windows


class PermutationMethod(unittest.TestCase):
    def test_unequal_year_blocks_preserve_every_row_and_internal_order(self):
        dates = pd.to_datetime(['2019-12-31','2020-01-02','2020-01-03','2021-01-04','2021-01-05','2021-01-06'])
        rows, orders, years, counts = annual_permutations(dates, 5, np.random.default_rng(91))
        self.assertEqual(counts, [1,2,3])
        self.assertEqual(len({tuple(p) for p in orders}), 5)
        self.assertNotIn((0,1,2), {tuple(p) for p in orders})
        for row, order in zip(rows, orders):
            np.testing.assert_array_equal(np.sort(row), np.arange(6))
            want = np.concatenate([np.flatnonzero(dates.year == years[k]) for k in order])
            np.testing.assert_array_equal(row, want)
        with self.assertRaises(ValueError):
            annual_permutations(dates, 6, np.random.default_rng(91))

    def test_probability_includes_observation_and_ties(self):
        self.assertEqual(tail_probability(2., [0., 1.]), 1/3)
        self.assertEqual(tail_probability(1., [1., 1.]), 1.)
        self.assertEqual(tail_probability(1., [0., 1.]), 2/3)

    def test_holm_and_resolution_are_not_an_impossible_gate(self):
        np.testing.assert_allclose(holm_adjust([.01,.04,.03]), [.03,.06,.06])
        self.assertGreater(holm_adjust(np.full(24, 1/201)).min(), .05)
        self.assertLess(holm_adjust(np.full(24, 1/1000)).max(), .05)
        with self.assertRaises(ValueError):
            holm_adjust([np.nan])

    def test_random_intervals_are_reproducible_complete_calendar_months(self):
        dates = pd.bdate_range('2000-01-03','2026-08-28')
        one = random_intervals(dates, 5000, np.random.default_rng(20260905))
        two = random_intervals(dates, 5000, np.random.default_rng(20260905))
        for a, b in zip(one, two):
            np.testing.assert_array_equal(a, b)
        s, e, months = one
        self.assertTrue(np.all((s < e) & (e < len(dates)) & (months >= 36) & (months <= 180)))
        for j in range(20):
            self.assertEqual(e[j], dates.searchsorted(dates[s[j]]+pd.DateOffset(months=int(months[j]))))


class BatchMoneyPaths(unittest.TestCase):
    def test_batch_matches_single_account_and_independent_units(self):
        rng = np.random.default_rng(87)
        w = rng.uniform(0., 1., (45, 7))
        r = rng.uniform(-.15, .15, (45, 4)); mask = rng.random(45) < .5
        for name in ('B','T4-tb','T4-mix','Hold1'):
            for fee in (0., .001, .02):
                curves, _, _ = gross_batch(w, name, r, mask, fee)
                for j in range(7):
                    p = np.array([make_positions([x], name)[0] for x in w[:, j]])
                    single = account_windows(p,r,mask,[0],[44],np.empty((0,1),int),[],1.,fee=fee,record_paths=True)
                    np.testing.assert_allclose(curves[:,j],single['paths'][:,0],rtol=1e-12,atol=1e-12)
                    np.testing.assert_allclose(curves[:,j],units_reference(w[:,j],name,r,mask,fee),rtol=1e-12,atol=1e-12)

    def test_constant_controls_are_identical_and_closed_days_do_not_rebalance(self):
        r = np.array([[0.,0.,0.,0.],[1.,0.,0.,0.],[-.5,0.,0.,0.]])
        mask = np.array([False,True,False])
        c, t, _ = gross_batch(np.full((3,4),.5),'B',r,mask,fee=0.)
        np.testing.assert_allclose(c[:,0],[1.,1.5,1.])
        np.testing.assert_array_equal(c,np.broadcast_to(c[:,:1],c.shape))
        np.testing.assert_array_equal(t,0.)
        for name in ('Hold1','Hold2'):
            c,t,_ = gross_batch(np.ones((3,5)),name,r,mask)
            np.testing.assert_array_equal(c,np.broadcast_to(c[:,:1],c.shape))
            np.testing.assert_array_equal(t,0.)

    def test_invalid_paths_fail_closed(self):
        with self.assertRaises(ValueError):
            gross_batch(np.ones((3,2)), 'B', np.zeros((3,4)), [0,1,1])
        with self.assertRaises(ValueError):
            gross_batch(np.full((3,2),1.1), 'B', np.zeros((3,4)), [False,True,True])


if __name__ == '__main__':
    unittest.main()
