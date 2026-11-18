import hashlib
from pathlib import Path
import tempfile
import unittest

import h5py
import numpy as np

import run


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sampling = run.read_frozen_design()["sampling"]

    def test_exact_event_grid_and_strict_history_bins(self):
        clock = np.arange(-200, 520, 10)
        (target, feature_bins, origin), reason = run.clock_indices(clock, self.sampling, False)
        self.assertIsNone(reason)
        self.assertEqual(origin, 0)
        np.testing.assert_array_equal(clock[target], np.arange(100, 501, 50))
        np.testing.assert_array_equal(clock[feature_bins[0]][0], [0, 10, 20, 30, 40])
        np.testing.assert_array_equal(clock[feature_bins[1]][0], [50, 60, 70, 80, 90])
        np.testing.assert_array_equal(target - feature_bins[1][:, -1], 1)

    def test_native_anchor_uses_first_nonnegative_source_row(self):
        clock = np.arange(-205, 525, 10)
        self.assertEqual(
            run.clock_indices(clock, self.sampling, False)[1], "clock_not_continuous_on_selected_grid"
        )
        (target, feature_bins, origin), reason = run.clock_indices(clock, self.sampling, True)
        self.assertIsNone(reason)
        self.assertEqual(origin, 5)
        np.testing.assert_array_equal(clock[target], np.arange(105, 506, 50))
        np.testing.assert_array_equal(clock[target] - clock[feature_bins[1][:, -1]], 10)

    def test_clock_and_trial_boundary_fail_closed(self):
        cases = (
            (np.arange(0, 550, 10), True, "no_native_anchor_bracketing_event"),
            (np.r_[np.arange(-200, 120, 10), np.arange(130, 550, 10)], True, "clock_not_continuous_on_selected_grid"),
            (np.arange(-200, 500, 10), False, "analysis_time_support_unavailable"),
            (np.r_[np.arange(-200, 120, 10), 110, np.arange(130, 550, 10)], True, "clock_nonfinite_or_nonincreasing"),
        )
        for clock, native, expected in cases:
            with self.subTest(clock=clock[:5], native=native, expected=expected):
                self.assertEqual(run.clock_indices(clock, self.sampling, native)[1], expected)

    def test_target_row_and_future_eeg_cannot_change_first_prediction_features(self):
        clock = np.arange(-200, 520, 10)
        indices, reason = run.clock_indices(clock, self.sampling, False)
        self.assertIsNone(reason)
        target, feature_bins, _ = indices
        eeg = np.ones((len(clock), 3))
        palm = clock * 2.0
        (first, y), reason = run.materialize_window(eeg, palm, target, feature_bins)
        self.assertIsNone(reason)
        eeg[target[0] :, :] *= 1000
        (changed, y2), reason = run.materialize_window(eeg, palm, target, feature_bins)
        self.assertIsNone(reason)
        np.testing.assert_array_equal(first[0], changed[0])
        self.assertTrue(np.any(first[1:] != changed[1:]))
        np.testing.assert_array_equal(y, y2)

    def test_nonfinite_support_and_leap_target_stay_distinct(self):
        eeg = np.ones((3, 3))
        palm = np.array([2.0, np.nan, 4.0])
        args = (np.array([1]), [np.array([[0]])])
        self.assertEqual(run.materialize_window(eeg, palm, *args)[1], "nonfinite_target")
        eeg[0, 0] = np.nan
        self.assertEqual(run.materialize_window(eeg, palm, *args)[1], "nonfinite_feature")

    def test_train_only_model_and_template(self):
        train_x = np.arange(72, dtype=float).reshape(4, 3, 6)
        train_y = np.arange(12, dtype=float).reshape(4, 3)
        train = (train_x, train_y, {})
        dev = (train_x + 25, train_y - 80, {})
        changed_dev = (train_x - 2500, train_y * -80, {})
        first = run.score(train, dev, 10)
        second = run.score(train, changed_dev, 10)
        self.assertEqual(first["TRAIN"], second["TRAIN"])
        expected = np.sqrt(np.mean((train_y.mean(axis=0) - dev[1]) ** 2))
        self.assertAlmostEqual(first["DEV"]["metrics"]["train_time_template"]["rmse_mm"], expected)
        dev_ridge = run.predict_ridge(dev[0], run.fit_ridge(train_x, train_y, 10))
        shifted = np.roll(dev_ridge, -1, axis=0)
        expected = np.sqrt(np.mean((shifted - dev[1]) ** 2))
        self.assertAlmostEqual(first["DEV"]["metrics"]["ridge_shifted_dev_trials"]["rmse_mm"], expected)

    def test_input_file_bound_to_expected_role(self):
        with tempfile.TemporaryDirectory(dir=run.ROOT) as directory:
            path = Path(directory) / "expected.mat"
            path.write_bytes(b"fixture")
            digest = hashlib.sha256(b"fixture").hexdigest()
            design = {"roles": {"TRAIN": {"basename": path.name, "sha256": digest}}}
            run.verify_assets(design, {"TRAIN": path})
            path.write_bytes(b"changed")
            with self.assertRaises(run.GateError):
                run.verify_assets(design, {"TRAIN": path})

    def test_hdf5_axes_and_zero_based_ids(self):
        with h5py.File("non_persistent_fixture.h5", "w", driver="core", backing_store=False) as file:
            out = file.create_group("OUT")
            arrays = {
                "EEG": np.zeros((40, 28)),
                "t_ms": np.zeros((1, 40)),
                "x_mm": np.zeros((40, 1)),
                "lm_trial": np.zeros((1, 1)),
                "eeg_seg_idx": np.ones((1, 1)),
            }
            for field, row in arrays.items():
                dataset = file.create_dataset(field, data=row)
                column = out.create_dataset(field, (1, 1), dtype=h5py.ref_dtype)
                column[0, 0] = dataset.ref
            trial = next(run.trials(file))
            self.assertEqual(run.matrix_shape(trial), (40, 28))
            self.assertEqual(run.source_index(trial["lm_trial"], minimum=0), 0)
            with self.assertRaises(run.GateError):
                run.source_index(trial["lm_trial"], minimum=1)
            trial["EEG"] = file.create_dataset("transpose", (28, 40), dtype="f")
            with self.assertRaises(run.GateError):
                run.matrix_shape(trial)


if __name__ == "__main__":
    unittest.main()
