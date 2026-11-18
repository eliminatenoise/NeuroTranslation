"""Exercise the two run roles and check the residual fit independently."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import h5py
import numpy as np
from threadpoolctl import threadpool_limits

import run


def write_trial_fixture(path, seed, counts, missing_tail=False):
    rng = np.random.default_rng(seed)
    clock = np.arange(-300, 901, 10, dtype=np.float64)
    with h5py.File(path, "w") as handle:
        out = handle.create_group("OUT")
        columns = {
            name: out.create_dataset(name, (counts, 1), dtype=h5py.ref_dtype)
            for name in run.cohort.FIELDS
        }
        for index in range(counts):
            palm = (index + 1) * np.sin(clock / 110) + rng.normal(scale=0.5, size=len(clock))
            if missing_tail and index == counts - 1:
                palm[clock == 600] = np.nan
            values = {
                "EEG": rng.normal(size=(len(clock), 3)),
                "t_ms": clock[None, :],
                "x_mm": palm[:, None],
                "lm_trial": [[index]],
                "eeg_seg_idx": [[index + 1]],
            }
            for name, data in values.items():
                columns[name][index, 0] = handle.create_dataset(f"{index}/{name}", data=data).ref


class FitTest(unittest.TestCase):
    def test_regularized_normal_equations_match_explicit_design(self):
        design, _, model = run.study_files()
        rng = np.random.default_rng(41)
        features = rng.normal(size=(21, 9, 8))
        with threadpool_limits(limits=1):
            for method in design["baseline"]["methods"]:
                with self.subTest(method=method):
                    base = model["models"][method]
                    unchanged = copy.deepcopy(base)
                    X = (features[..., base["feature_indices"]] - base["center"]) / base["scale"]
                    z = X.reshape(-1, X.shape[-1])
                    n, p = z.shape
                    residual = (z @ np.linspace(-1, 1, p)).reshape(21, 9) + np.arange(9) / 3
                    target = run.cohort.predict(features, base) + residual
                    record = run.cohort.Recording(features, target, {})
                    got = run.fit_correction(record, base, design["ridge_lambda"])
                    time = np.tile(np.eye(9), (21, 1))
                    lhs = np.column_stack((time, z)) / np.sqrt(n)
                    penalty = np.column_stack((np.zeros((p, 9)), np.eye(p))) * np.sqrt(design["ridge_lambda"])
                    rhs = np.concatenate((residual.ravel() / np.sqrt(n), np.zeros(p)))
                    expected = np.linalg.lstsq(np.vstack((lhs, penalty)), rhs, rcond=None)[0]
                    np.testing.assert_allclose(got["ridge_delta_intercepts_mm"], expected[:9], atol=1e-11, rtol=0)
                    np.testing.assert_allclose(got["ridge_delta_slopes"], expected[9:], atol=1e-11, rtol=0)
                    np.testing.assert_allclose(got["timing_only_intercepts_mm"], residual.mean(axis=0))
                    self.assertAlmostEqual(got["bias_mm"], float(residual.mean()))
                    self.assertEqual(base, unchanged)


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cross run ")
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name)
        self.source_path = self.stage / "SOURCE.json"
        self.state_path = self.stage / "state.json"
        self.scores = self.stage / "result.json"
        self.source = {"release_commit": run.study_files()[0]["dataset"]["release_commit"], "participants": []}
        for role, run_no in (("CALIBRATION", "01"), ("EVALUATION", "02")):
            stage = self.stage / role
            stage.mkdir()
            for subject in range(13, 16):
                stem = f"sub-{subject}"
                path = stage / f"{stem}_task-ihc_run-{run_no}_eeg_leap_R{int(run_no)}.mat"
                number = subject - 8
                write_trial_fixture(path, 100 * int(run_no) + subject, number, role == "EVALUATION")
                self.source["participants"].append({
                    "subject": stem, "role": role, "run": run_no, "basename": path.name,
                    "released_trials": number,
                    "asset_bytes": path.stat().st_size, "asset_sha256": run.cohort.sha(path), "n_channels": 3,
                    "channels": [
                        {"name": name, "type": "EEG", "index_zero_based": idx}
                        for idx, name in enumerate(("C3", "Cz", "C4"))
                    ],
                })
        self.write_source()

    def write_source(self):
        self.source_path.write_text(json.dumps(self.source), encoding="utf-8")

    def invoke(self, command, role, output, *extra):
        script = """import sys
from pathlib import Path
import run
run.SOURCE_PATH = Path(sys.argv[1])
run.SOURCE_SHA = sys.argv[2]
sys.exit(run.main(sys.argv[3:]))
"""
        return subprocess.run(
            [sys.executable, "-B", "-c", script, str(self.source_path), run.cohort.sha(self.source_path),
             command, "--input", str(self.stage / role), "--output", str(output), *extra],
            capture_output=True, text=True, check=False, cwd=self.stage,
            env={**os.environ, "PYTHONPATH": str(run.ROOT)},
        )

    def calibrate(self):
        proc = self.invoke("calibrate", "CALIBRATION", self.state_path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return run.cohort.sha(self.state_path)

    def test_roles_scores_and_state_hash(self):
        state_sha = self.calibrate()
        state_args = "--state", str(self.state_path), "--state-sha256", state_sha
        wrong_hash = self.invoke("evaluate", "EVALUATION", self.scores, *state_args[:-1], "0" * 64)
        self.assertEqual(wrong_hash.returncode, 2)
        self.assertIn("SHA-256 mismatch", wrong_hash.stderr)
        self.assertFalse(self.scores.exists())
        wrong_role = self.invoke("evaluate", "CALIBRATION", self.scores, *state_args)
        self.assertEqual(wrong_role.returncode, 2)
        self.assertFalse(self.scores.exists())
        ok = self.invoke("evaluate", "EVALUATION", self.scores, *state_args)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        outputs = json.loads(self.scores.read_text(encoding="utf-8"))
        self.assertEqual(outputs["calibration_state_sha256"], state_sha)
        self.assertEqual(run.cohort.sha(self.state_path), state_sha)
        self.assertEqual(outputs["counts"]["calibration"], {"released_trials": 18, "eligible_trials": 18, "scored_rows": 162})
        self.assertEqual(outputs["counts"]["evaluation"], {"released_trials": 18, "eligible_trials": 15, "scored_rows": 135})
        per_subject = outputs["metrics"]["per_person"]
        method = "time_palm_eeg_ridge"
        equal_person = np.sqrt(np.mean([row[method]["rmse_mm"] ** 2 for row in per_subject.values()]))
        pooled = np.sqrt(np.average(
            [row[method]["rmse_mm"] ** 2 for row in per_subject.values()], weights=[4, 5, 6],
        ))
        self.assertAlmostEqual(outputs["metrics"]["equal_person"][method]["rmse_mm"], equal_person)
        self.assertAlmostEqual(outputs["metrics"]["pooled"][method]["rmse_mm"], pooled)
        result_sha = run.cohort.sha(self.scores)
        repeat = self.invoke("evaluate", "EVALUATION", self.scores, *state_args)
        self.assertEqual(repeat.returncode, 2)
        self.assertIn("Refusing to replace", repeat.stderr)
        self.assertEqual(run.cohort.sha(self.scores), result_sha)

    def test_source_gate_rejects_duplicated_asset_and_corruption(self):
        records = self.source["participants"]
        original = records[-1]["asset_sha256"]
        records[-1]["asset_sha256"] = records[0]["asset_sha256"]
        self.write_source()
        proc = self.invoke("calibrate", "CALIBRATION", self.state_path)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Incorrect run or channel binding", proc.stderr)
        self.assertFalse(self.state_path.exists())
        records[-1]["asset_sha256"] = original
        self.write_source()
        boundary = self.stage / "CALIBRATION" / records[0]["basename"]
        with boundary.open("ab") as file:
            file.write(b"x")
        proc = self.invoke("calibrate", "CALIBRATION", self.state_path)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Input identity mismatch", proc.stderr)
        self.assertFalse(self.state_path.exists())


if __name__ == "__main__":
    unittest.main()
