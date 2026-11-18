import unittest

import numpy as np

from baseline import Design, Trial, evaluate, windows


DESIGN = Design(0.05, 0.04, 0.0015, 49, 0.01)


def recording(subject, identity, *, target=None, nframes=100):
    emg_times = np.arange(8 * nframes) / 1000
    emg = np.arange(len(emg_times), dtype=float)
    targets = np.linspace(0, 40, nframes) if target is None else target
    return Trial(
        subject, "s1", "HM:1", identity, ("surface_emg",), emg_times, emg[:, None],
        np.arange(nframes) / 125, targets,
    )


class ReferenceTests(unittest.TestCase):
    def test_exact_bound_and_no_future_feature(self):
        trial = recording("HS01", "source1")
        output = windows(trial, DESIGN)
        self.assertEqual(output.target_rows[0], 12)
        self.assertEqual(output.last_emg_rows[0], 56)
        np.testing.assert_allclose(output.features[0, 0], np.sqrt(np.mean(np.arange(6, 57) ** 2)))
        trial.emg[57:, :] += 1e5
        self.assertEqual(windows(trial, DESIGN).features[0, 0], output.features[0, 0])
        np.testing.assert_allclose(output.label_times - output.last_emg_times, 0.04)

    def test_missing_target_and_warmup_are_disjoint(self):
        target = np.zeros(100)
        target[[0, 12]] = np.nan
        output = windows(recording("HS01", "source1", target=target), DESIGN)
        self.assertEqual(output.missing_label_rows, 2)
        self.assertEqual(output.unavailable_history_rows, 11)
        self.assertEqual(len(output.labels), 87)
        self.assertEqual(output.target_rows[0], 13)

    def test_gapped_history_does_not_create_a_feature(self):
        trial = recording("HS01", "source1")
        keep = np.arange(len(trial.emg_seconds)) != 25
        gapped = Trial(
            trial.subject, trial.session, trial.trial, trial.source_trial, trial.channel_names,
            trial.emg_seconds[keep], trial.emg[keep], trial.target_seconds, trial.target,
        )
        self.assertGreater(windows(gapped, DESIGN).target_rows[0], 12)

    def test_split_clamps_only_to_training_template(self):
        train = recording("HS01", "source1")
        dev = recording("HS02", "source2", nframes=105)
        report = evaluate([train, dev], ["HS01"], ["HS02"], DESIGN, 125)
        self.assertEqual(report["training_rows"], 88)
        self.assertEqual(report["onset_template_frame_range"], [12, 99])
        self.assertEqual(report["reference_in_sample"]["pooled_errors"]["onset_only"]["mae"], 0)
        self.assertEqual(report["development_held_out_subject"]["onset_template_clamped_rows"], 5)
        dev.emg[:] += 1e5
        dev.target[:] -= 1e5
        distorted = evaluate([train, dev], ["HS01"], ["HS02"], DESIGN, 125)
        self.assertEqual(report["reference_in_sample"], distorted["reference_in_sample"])
        self.assertNotEqual(report["development_held_out_subject"], distorted["development_held_out_subject"])

    def test_duplicate_source_or_subject_overlap_fails(self):
        train = recording("HS01", "source1")
        dev = recording("HS02", "source1")
        with self.assertRaisesRegex(ValueError, "duplicate trial"):
            evaluate([train, dev], ["HS01"], ["HS02"], DESIGN, 125)
        with self.assertRaisesRegex(ValueError, "disjoint"):
            evaluate([train, dev], ["HS01"], ["HS01", "HS02"], DESIGN, 125)


if __name__ == "__main__":
    unittest.main()
