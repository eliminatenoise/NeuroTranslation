"""Check the distributed forecast clock, reference numbers and coordinate geometry."""
import json
import unittest

import numpy as np

from forecast import HERE, forecast, load_weights


class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tagged = load_weights(HERE / "conditional.json")
        cls.blind = load_weights(HERE / "history-only.json")

    def test_examples(self):
        for action in ("walk", "run"):
            ex = json.loads((HERE / f"example-{action}.json").read_text())
            x, times = ex["history"]["positionsMm"], ex["history"]["timesS"]
            p = forecast(x, times, action, self.tagged)
            np.testing.assert_allclose(p["positionsMm"], ex["forecast"]["positionsMm"], atol=1e-6)
            np.testing.assert_allclose(p["pelvisMm"], np.mean(np.array(p["positionsMm"])[:, 2:4], axis=1), atol=1e-7)
            np.testing.assert_allclose(p["timesS"], times[-1] + np.arange(1, 13)/20)
            a = forecast(x, times, None, self.blind)
            b = forecast(x, times, "run", self.blind)
            np.testing.assert_array_equal(a["positionsMm"], b["positionsMm"])

    def test_yaw_translation_and_clock(self):
        ex = json.loads((HERE / "example-walk.json").read_text())
        x = np.array(ex["history"]["positionsMm"])
        times = np.array(ex["history"]["timesS"])
        yaw = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        shift = np.array([500., 250., -128.])
        orig = forecast(x, times, "walk", self.tagged)
        moved = forecast(x @ yaw + shift, times + 7., "walk", self.tagged)
        np.testing.assert_allclose(moved["positionsMm"], np.asarray(orig["positionsMm"]) @ yaw + shift, atol=1e-7)
        np.testing.assert_allclose(moved["timesS"], np.asarray(orig["timesS"])+7., atol=1e-10)
        for problem in ("nan", "collapsed", "tag", "clock"):
            h = x.copy()
            t = times.copy()
            action = "walk"
            if problem == "nan":
                h[0, 8, 1] = np.nan
            elif problem == "collapsed":
                h[-1, 3] = h[-1, 2]
            elif problem == "tag":
                action = "jump"
            else:
                t[-1] += .04
            with self.assertRaises(ValueError):
                forecast(h, t, action, self.tagged)


if __name__ == "__main__":
    unittest.main()
