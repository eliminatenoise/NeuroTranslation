"""Synthetic acceptance cases for the frozen offline comparison."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import h5py
import numpy as np
from numpy.testing import assert_allclose, assert_array_equal

import run


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.protocol = run.load_design()

    def test_clock_selects_exact_native_rows_and_cutoff(self):
        clock = np.arange(-196.0, 615.0, 10.0)
        palm = np.where(clock < 4.0, np.nan, clock)
        (cue, anchor, target, past, eeg), issue = run.clock_rows(clock, self.protocol, palm)
        self.assertIsNone(issue)
        self.assertEqual(cue, anchor)
        self.assertEqual(clock[anchor], 4.0)
        assert_array_equal(clock[target], [204, 254, 304, 354, 404, 454, 504, 554, 604])
        assert_array_equal(clock[past[0]], [104, 54])
        assert_array_equal(clock[eeg[0]], [[14, 24, 34, 44, 54], [64, 74, 84, 94, 104]])
        assert_array_equal(clock[target] - clock[past[:, 0]], np.full(9, 100))
        assert_array_equal(clock[target] - clock[eeg[:, -1, -1]], np.full(9, 100))

    def test_clock_rejects_missing_gap_duplicate_and_missing_support(self):
        clock = np.arange(-196.0, 715.0, 10.0)
        for altered, minimum, reason in (
            (clock[clock >= 0], 0, "no_native_anchor_bracketing_event"),
            (np.delete(clock, 5), 0, "clock_gapped_or_off_lattice"),
            (np.insert(clock, 5, clock[5]), 0, "clock_nonfinite_or_nonincreasing"),
            (clock, 715, "no_finite_palm_at_or_after_native_cue"),
            (clock, 180, "required_time_support_unavailable"),
        ):
            with self.subTest(reason=reason):
                palm = np.where(altered < minimum, np.nan, altered)
                self.assertEqual(run.clock_rows(altered, self.protocol, palm), (None, reason))

    def test_availability_ignores_pre_cue_finite_samples_and_values(self):
        clock = np.arange(-196.0, 715.0, 10.0)
        palm = np.where((clock > 0.0) & (clock < 44.0), np.nan, clock)
        rows, _ = run.clock_rows(clock, self.protocol, palm)
        changed, _ = run.clock_rows(clock, self.protocol, -palm * 50)
        self.assertEqual(clock[rows[0]], 4.0)
        self.assertEqual(clock[rows[1]], 44.0)
        assert_array_equal(clock[rows[2]], np.arange(244, 645, 50))
        for before, after in zip(rows, changed, strict=True):
            assert_array_equal(before, after)

    def test_no_current_target_in_same_row_and_joint_missingness(self):
        clock = np.arange(-196.0, 615.0, 10.0)
        palm = 3.0 * clock / 1000
        rows, _ = run.clock_rows(clock, self.protocol, palm)
        eeg = np.column_stack([clock, 2 * clock, 3 * clock])
        original, _ = run.materialize(palm, eeg, rows, self.protocol)
        assert_allclose(original[0][0], [.312, 3, 34, 68, 102, 84, 168, 252], atol=1e-13)
        target_index = rows[2][0]
        palm[target_index] += 123.0
        changed, _ = run.materialize(palm, eeg, rows, self.protocol)
        assert_array_equal(original[0][0], changed[0][0])
        self.assertAlmostEqual(changed[1][0] - original[1][0], 123.0)
        for series, key, index in (
            (palm, "nonfinite_target", target_index),
            (palm, "nonfinite_past_palm", rows[3][0, 1]),
            (eeg, "nonfinite_eeg", rows[4][0, 0, 0]),
        ):
            altered = series.copy()
            altered[index] = np.nan
            result = run.materialize(
                altered if series is palm else palm,
                altered if series is eeg else eeg,
                rows, self.protocol,
            )
            self.assertEqual(result, (None, key))

    def test_named_channel_columns_are_reordered_and_trial_identity_gates(self):
        clock = np.arange(-196.0, 615.0, 10.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.mat"
            with h5py.File(path, "w") as handle:
                group = handle.create_group("OUT")
                raw = {
                    "EEG": np.column_stack([clock, 2 * clock, 3 * clock, 4 * clock]),
                    "t_ms": clock[None],
                    "x_mm": clock[:, None],
                    "lm_trial": np.array([[0]]),
                    "eeg_seg_idx": np.array([[1]]),
                }
                for field, array in raw.items():
                    refs = group.create_dataset(field, shape=(1, 1), dtype=h5py.ref_dtype)
                    refs[0, 0] = handle.create_dataset("trial_" + field, data=array).ref
            binding = {"n_channels": 4, "channels": [{"index_zero_based": idx} for idx in (3, 0, 2)]}
            record = run.read_recording(path, binding, self.protocol)
            self.assertEqual(record.custody["eligible_trials"], 1)
            assert_allclose(record.features[0, 0, 2:], [136, 34, 102, 336, 84, 252])
            with h5py.File(path, "r+") as handle:
                handle["trial_eeg_seg_idx"][0, 0] = 0
            with self.assertRaises(run.GateError):
                run.read_recording(path, binding, self.protocol)

    def synthetic(self, trials, seed):
        rng = np.random.default_rng(seed)
        features = rng.normal(size=(trials, 9, 8))
        target = np.arange(9)[None] + features[..., 0] * 2 + features[..., 3] * 4
        return run.Recording(features, target, {"eligible_trials": trials})

    def test_fit_matches_direct_weighted_augmented_least_squares(self):
        recordings = [self.synthetic(trials, seed) for seed, trials in enumerate((5, 7, 9))]
        models, mean = run.fit_models(recordings, 0.01)
        x = np.concatenate([r.features.reshape(-1, 8) for r in recordings])
        y = np.concatenate([r.target.ravel() for r in recordings])
        weights = np.concatenate([np.full(r.target.size, 1 / (3 * r.target.size)) for r in recordings])
        centers = np.average(x, axis=0, weights=weights)
        scales = np.sqrt(np.average((x - centers) ** 2, axis=0, weights=weights))
        times = np.tile(np.eye(9), (len(y) // 9, 1))
        self.assertAlmostEqual(mean, np.average(y, weights=weights))
        for key, inds in run.FEATURE_SUBSETS.items():
            full_design = np.column_stack((times, ((x - centers) / scales)[:, inds]))
            regularizer = np.c_[np.zeros((len(inds), 9)), np.eye(len(inds)) * 0.1]
            matrix = np.vstack((full_design * np.sqrt(weights[:, None]), regularizer))
            outcomes = np.r_[y * np.sqrt(weights), np.zeros(len(inds))]
            independent = np.linalg.lstsq(matrix, outcomes, rcond=None)[0]
            assert_allclose(models[key]["intercepts_mm"], independent[:9], atol=1e-12)
            assert_allclose(models[key]["coefficients"], independent[9:], atol=1e-12)

    def test_train_only_and_synthetic_incremental_information(self):
        train = [self.synthetic(trials, seed) for seed, trials in enumerate((5, 7, 9))]
        dev = self.synthetic(12, 12)
        models, mean = run.fit_models(train, 0.01)
        with patch.object(run, "fit_models", side_effect=AssertionError("DEV must never refit")):
            report, residuals = run.score_recording(dev, models, mean, self.protocol)
        self.assertEqual(report["frames"], 108)
        self.assertLess(report["metrics"]["time_palm_eeg"]["rmse_mm"], 0.2)
        self.assertGreater(report["metrics"]["time_palm"]["rmse_mm"], 2)
        self.assertGreater(report["metrics"]["time_palm_eeg_rotated"]["rmse_mm"], 2)
        for values in residuals.values():
            self.assertEqual(values.shape, dev.target.shape)
        rotated_eeg = np.roll(dev.features[..., 2:], -1, axis=0)
        expected = run.predict(np.concatenate((dev.features[..., :2], rotated_eeg), axis=2), models["time_palm_eeg"])
        assert_allclose(residuals["time_palm_eeg_rotated"] + dev.target, expected, atol=1e-12)

    def test_equal_participant_weighting_not_equal_trial_weighting(self):
        a = run.Recording(np.zeros((4, 9, 8)), np.zeros((4, 9)), {})
        b = run.Recording(np.zeros((8, 9, 8)), np.full((8, 9), 12.0), {})
        models, mean = run.fit_models([a, b], 0.01)
        self.assertAlmostEqual(mean, 6.0)
        assert_allclose(models["time"]["intercepts_mm"], 6.0, atol=1e-12)
        assert_allclose(models["time_palm_eeg"]["intercepts_mm"], 6.0, atol=1e-12)
        assert_allclose(models["time_palm_eeg"]["scale"], 1.0, atol=1e-12)

    def test_input_hash_and_role_enforcement(self):
        import json
        roles = self.protocol["dataset"]["roles"]
        subjects = [name for part in roles.values() for name in part]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "SOURCE.json"
            lock_path = root / "PRESCORE-LOCK.json"
            runs = {}
            for subject in subjects:
                filename = f"{subject}_task-ihc_run-01_eeg_leap_R1.mat"
                fake_asset = root / filename
                fake_asset.write_bytes(b"test asset")
                runs[subject] = {
                    "basename": filename, "asset_bytes": 10, "asset_sha256": run.sha(fake_asset),
                    "channels": [
                        {"name": name, "type": "EEG", "index_zero_based": index}
                        for index, name in enumerate(["C3", "Cz", "C4"])
                    ],
                    "n_channels": 3,
                }
            source = {
                "release_commit": self.protocol["dataset"]["release_commit"], "roles": roles,
                "status": "supported_for_named_central_rows", "runs": runs,
            }
            def bind():
                path.write_text(json.dumps(source))
                lock_path.write_text(json.dumps({
                    "design_sha256": run.DESIGN_SHA, "source_sha256": run.sha(path),
                    "runner_sha256": run.sha(Path(run.__file__)),
                }))
            bind()
            with patch.object(run, "ROOT", root):
                self.assertEqual(set(run.load_source(self.protocol, root, subjects)[1]), set(subjects))
                (root / runs["sub-07"]["basename"]).write_bytes(b"changed by")
                with self.assertRaisesRegex(run.GateError, "Asset identity mismatch"):
                    run.load_source(self.protocol, root, subjects)
                source["roles"] = {"TRAIN": roles["DEV"], "DEV": roles["TRAIN"]}
                bind()
                with self.assertRaisesRegex(run.GateError, "roles"):
                    run.load_source(self.protocol, root, subjects)


if __name__ == "__main__":
    unittest.main()
