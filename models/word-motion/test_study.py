"""Metric, split and fitted-output regressions, including invented numeric inputs."""

import json
import unittest

import numpy as np
from acquire import HERE, manifest
from assess import aggregate, metrics
from generate import action_for, predict


class StudyTests(unittest.TestCase):
    def test_split_subjects_and_pins(self):
        rows = manifest()["clips"]
        self.assertEqual(len({r["id"] for r in rows}), len(rows))
        groups = {}
        for r in rows:
            self.assertEqual(groups.setdefault(r["subject"], r["split"]), r["split"])
        pins = json.loads((HERE / "source-hashes.json").read_text())
        self.assertEqual(set(pins), {r["id"] for r in rows if r["split"] != "reserve"})

    def test_errors_on_invented_translation(self):
        real = np.zeros((25, 57))
        predicted = real.copy()
        predicted[:, :54:3] = 3
        predicted[:, 1:54:3] = 4
        predicted[:, -2] = np.arange(25)
        a = metrics(real, predicted)
        self.assertEqual(a["bodyMm"], 5)
        self.assertEqual(a["pelvisPathMm"], 12)
        self.assertEqual(a["signedForwardEndMm"], 24)
        self.assertEqual(a["absoluteMeanBodySpeedDifferenceMmS"], 0)

    def test_subject_weighting(self):
        rows = [
            {"subject": s, "errors": {"e": e}}
            for s, e in [("1", 0), ("1", 0), ("2", 4)]
        ]
        self.assertEqual(aggregate(rows)["equalSubject"]["e"], 2)

    def test_runtime(self):
        weights = json.loads((HERE / "weights.json").read_text())
        self.assertIsNone(action_for("do not run"))
        self.assertEqual(action_for(" RUN/JOG "), "run")
        for action in ("walk", "run"):
            y = predict(action, weights)
            packet = json.loads((HERE / (action + ".json")).read_text())
            self.assertEqual(y.shape, (25, 57))
            np.testing.assert_array_equal(y[0, -3:], [0, 0, 0])
            np.testing.assert_allclose(
                y[:, :54].reshape(25, 18, 3), packet["positionsMm"], atol=0.002
            )
            np.testing.assert_allclose(y[:, -3:], packet["rootMm"], atol=0.002)


if __name__ == "__main__":
    unittest.main()
