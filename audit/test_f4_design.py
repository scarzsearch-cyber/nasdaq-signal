"""F4 fixed-scope and calendar/legacy-basket reductions; synthetic inputs only."""
import unittest
import numpy as np
import pandas as pd
from research.strategy_f4_basket import VARIANTS, monthly_units_reference, schedule_reference
from research.basket_accounting import review_schedule
from hist_defasset import mix_monthly_parts


class FrozenF4Design(unittest.TestCase):
    def check_legacy(self, fee):
        rng = np.random.default_rng(420260905)
        idx = pd.bdate_range('2024-11-19', periods=470)
        raw = rng.normal(.0002, .025, (len(idx), 3))
        # Both functions deliberately mark the first return zero after setting
        # initial holdings, including the first-row price update convention.
        parts = dict(zip(('div', 'bond', 'gold'), raw.T))
        old = mix_monthly_parts(idx, dict(div=.4, bond=.4, gold=.2), parts, cost=fee)
        new = monthly_units_reference(idx, raw, fee)
        np.testing.assert_allclose(new, old, rtol=0., atol=2e-14)

    def test_zero_cost_legacy_basket_reduction(self):
        self.check_legacy(0.)

    def test_nonzero_cost_legacy_basket_reduction(self):
        for fee in (.0005, .002):
            self.check_legacy(fee)

    def test_calendar_reference_random_closures_and_reentries(self):
        rng = np.random.default_rng(43020260905)
        dates = np.arange('2024-12-19', '2026-08-29', dtype='datetime64[D]')
        ordinal = dates.astype(int)
        for _ in range(24):
            mask = (((ordinal+3) % 7) < 5) & (rng.random(len(dates)) > .12)
            anchors = np.empty(len(dates), int)
            anchor = int(ordinal[0]-43)  # Already defensive at the fresh start.
            for i in range(len(dates)):
                if mask[i] and rng.random() < .035:
                    anchor = int(ordinal[i]) if anchor < 0 else -1
                anchors[i] = anchor
            for rule in ('monthly', 'signal30'):
                np.testing.assert_array_equal(review_schedule(dates, mask, anchors, rule),
                                              schedule_reference(dates, mask, anchors, rule))

    def test_fixed_variants_are_accounting_sensitivities(self):
        self.assertEqual(VARIANTS, {'C1': ('monthly', 0.), 'C2': ('signal30', 0.),
                                    'C3': ('signal30', .02)})


if __name__ == '__main__':
    unittest.main()
