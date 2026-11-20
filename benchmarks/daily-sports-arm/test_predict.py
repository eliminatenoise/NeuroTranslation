"""Release checks on artificial data only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from predict import HERE, read_history


class InferenceTests(unittest.TestCase):
    def call(self, path):
        return subprocess.run([sys.executable, "-B", str(HERE / "predict.py"), str(path)],
                              text=True, capture_output=True)

    def test_sample_through_cli(self):
        run = self.call(HERE / "example.json")
        self.assertEqual(run.returncode, 0, run.stderr)
        output = json.loads(run.stdout)
        self.assertEqual(output["lead_ms"], 120)
        self.assertEqual(output["axis_order"], ["X", "Y", "Z"])
        self.assertEqual(output["units"], "native sensor units")
        preds = output["forecasts"]
        self.assertEqual(set(preds), {"persistence", "ridge", "transformer"})
        self.assertEqual(preds["persistence"], [2.25, -0.2, 8.7])
        np.testing.assert_allclose(preds["ridge"], [2.56523439, 1.53920336, 9.32458168], atol=1e-7, rtol=0)
        np.testing.assert_allclose(preds["transformer"], [4.16441058, 2.39884822, 7.92764771], atol=3e-5, rtol=0)

    def test_malformed_file_through_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("[[1, 2, 3]]", encoding="utf-8")
            run = self.call(path)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
        self.assertIn("16 consecutive", run.stderr)

    def test_bad_measurements(self):
        cases = [[0, 0], ["1", 0, 0], [True, 0, 0], [float("nan"), 0, 0], [float("inf"), 0, 0]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for row in cases:
                with self.subTest(row=row):
                    path.write_text(json.dumps([row] * 16), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        read_history(path)


if __name__ == "__main__":
    unittest.main()
