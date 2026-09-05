"""Fixed-candidate, count-extension and numerical-power checks for F3."""
import unittest
import numpy as np
from research.strategy_f3_execution import PARENTS, FIXED_BANDS, random_bands, parent_weights
from research.strategy_f3_placebo import DRAWS, MODES, METRICS, recovered_count
from research.strategy_f1_placebo import FAMILIES, holm_adjust
from research.strategy_f2_mix import FIXED


class FrozenF3Design(unittest.TestCase):
    def test_fixed_parents_and_neighbours_not_adaptive(self):
        self.assertEqual(PARENTS, ['T4-mix', 'BTmix25', 'BTmix50', 'BTmix75'])
        self.assertEqual(FIXED_BANDS, [0., .05, .10, .15])
        bands = random_bands()
        self.assertEqual(bands.shape, (200,))
        self.assertTrue(((bands > .05) & (bands < .15)).all())
        np.testing.assert_array_equal(bands, random_bands())
        reference = np.random.default_rng(np.random.SeedSequence(20260905).spawn(4)[3]).uniform(.05, .15, 200)
        np.testing.assert_array_equal(bands, reference)

    def test_parent_targets_use_same_basis_not_realized_curves(self):
        b, t = np.array([0., 1., 1.]), np.array([.4, .5, 0.])
        values = parent_weights(b, t)
        np.testing.assert_array_equal(values['T4-mix'], t)
        for n, x in FIXED.items():
            np.testing.assert_array_equal(values[n], b*x+t*(1-x))
            self.assertGreater(values[n][0], 0.)  # B=0 does not force a mixed parent to zero.

    def test_all52_tests_and_resolution_before_sampling(self):
        tests = {(mode, name, metric) for mode in MODES for name in
                 [*FAMILIES, *FIXED, *[p+'-E10' for p in PARENTS]] for metric in METRICS}
        self.assertEqual(len(tests), 52)
        self.assertEqual(DRAWS, 1999)
        self.assertGreaterEqual(52/1000, .05)
        self.assertLess(52/(DRAWS+1), .05)
        self.assertAlmostEqual(holm_adjust(np.full(52, 1/2000))[0], .026)

    def test_count_extension_exact_integer_not_rounded_p_value(self):
        for count in (0, 1, 5, 37, 500, 999):
            self.assertEqual(recovered_count((count+1)/1000, 999), count)
        for bad in (0., -.1, 1.1, .0025, np.nan, np.inf):
            with self.assertRaises((ValueError, OverflowError)):
                recovered_count(bad, 999)


if __name__ == '__main__':
    unittest.main()
