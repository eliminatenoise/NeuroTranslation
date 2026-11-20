"""Synthetic boundary and input-independence regressions; reserve recordings are unnecessary."""
import copy
import unittest
import numpy as np
import wtrack as w


def fixture():
    ts = np.arange(6101.,6106.,.03)
    return dict(trial=81,start=6100.,stop=6106.,ts=ts,frame=np.arange(len(ts)),
                xy=np.column_stack([ts,ts*2]),spikes=[np.array([6102.,6102.25,6102.5,6102.75,6103.,6103.001])]*72)


class TestWindows(unittest.TestCase):
    def test_half_open_spikes(self):
        d=fixture()
        bins=w.counts(d["spikes"],6103.)
        np.testing.assert_array_equal(bins,np.ones((4,72)))

    def test_future_does_not_change_inputs(self):
        d=fixture()
        old,_=w.history(d,6103.)
        alt=copy.deepcopy(d)
        alt["xy"][alt["ts"]>6103.]=np.nan
        alt["spikes"]=[s[s<=6103.] for s in alt["spikes"]]
        new,_=w.history(alt,6103.)
        for k in ["motion","spike","clocks","prior_frame","prior_s"]:
            np.testing.assert_array_equal(old[k],new[k])
        self.assertEqual(w.measured_target(alt,6103.,new)[1],"nonfinite_xy")

    def test_callback_on_missing_history(self):
        d=fixture()
        self.assertEqual(w.history(d,6101.,)[1],"missing_history")
        d["ts"][67:]+=0.2
        a=d["ts"][66]+.1
        self.assertEqual(w.history(d,a)[1],"stale_history")

    def test_source_refuses_other_roles(self):
        for role,i in [("test",91),("reserve",92),("test",55),("train",79)]:
            with self.assertRaises(ValueError):
                w.load_trial("/nonexistent",role,i)

    def test_ridge_rebuilds_control(self):
        rng=np.random.default_rng(0)
        motion=rng.normal(size=(100,4,5)); spike=rng.poisson(2,(100,4,72))
        d=w.Samples(np.repeat(np.arange(10),10),np.arange(6100.),motion,spike,np.zeros((100,2)),
                    np.zeros((100,5)),np.zeros((100,5)),np.zeros(100),np.zeros(100),motion[:,-1,:2])
        fit=w.fit_ridge(d,"motion",.3)
        np.testing.assert_array_equal(w.predict_ridge(fit,d.motion,d.clocks,d.spike),d.y)
        np.testing.assert_array_equal(w.predict_ridge(fit,d.motion,d.clocks,d.spike+6),d.y)


if __name__=="__main__":
    unittest.main()
