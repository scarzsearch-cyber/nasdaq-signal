"""No market execution; F2 target mixing and distribution invariants."""
import unittest
import numpy as np
from research.strategy_f2_mix import mixture, random_alphas
from research.strategy_f1_placebo import gross_batch, units_reference, holm_adjust


class FixedMixtures(unittest.TestCase):
    def test_endpoints_average_and_broadcast(self):
        b=np.array([0.,1.,0.,1.]); t=np.array([0.,.75,.5,.25])
        np.testing.assert_array_equal(mixture(b,t,1),b)
        np.testing.assert_array_equal(mixture(b,t,0),t)
        np.testing.assert_array_equal(mixture(b,t,.5),[0.,.875,.25,.625])
        np.testing.assert_array_equal(mixture(b[:,None],t[:,None],[0.,.5,1.]),
                                      np.column_stack([t,(b+t)/2,b]))

    def test_invalid_weights_fail_closed(self):
        for bad in (-.01,1.01,np.nan,np.inf):
            with self.assertRaises(ValueError):
                mixture([0.,1.],[.5,.5],bad)

    def test_random_distribution_is_reproducible_not_a_selected_optimum(self):
        x=random_alphas()
        self.assertEqual(len(x),200)
        np.testing.assert_array_equal(x,random_alphas())
        self.assertTrue(((x>0)&(x<1)).all())
        self.assertGreater(x.max()-x.min(),.9)
        self.assertLess(holm_adjust(np.full(36,1/1000)).max(),.05)

    def test_mixture_ledger_endpoint_and_nonendpoint_reductions(self):
        rng=np.random.default_rng(104)
        b=rng.integers(0,2,35); t=rng.uniform(0,1,35)
        w=mixture(b[:,None],t[:,None],[0.,.25,.5,.75,1.])
        r=rng.uniform(-.1,.1,(35,4)); mask=rng.random(35)>.3
        curves,_,_=gross_batch(w,'T4-mix',r,mask)
        for k in range(5):
            np.testing.assert_allclose(curves[:,k],units_reference(w[:,k],'T4-mix',r,mask),
                                       rtol=1e-12,atol=1e-12)
        for k,path in [(0,t),(4,b)]:
            direct,_,_=gross_batch(path[:,None],'T4-mix',r,mask)
            np.testing.assert_array_equal(curves[:,k],direct[:,0])


if __name__ == '__main__':
    unittest.main()
