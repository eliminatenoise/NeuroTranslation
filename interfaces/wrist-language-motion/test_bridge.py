"""Negative controls for evidence, temporal alignment, text availability and masked measurements."""
from __future__ import annotations

import copy
from dataclasses import replace
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch
from aligned_forecast import validate_aligned_forecast
from broader_learner import ScientificFreeze, configure_cpu_runtime, fit_train_normalizer
from model_bridge import (
    SIM_INERTIA, SIM_STIFFNESS, oscillator, replay_contracts, replay_tensors, synthetic_check,
)
from wrist_bridge import (
    CHANNELS, CONTEXT, HISTORY, PAIR, PARENT, RATE, SOURCE_IDS,
    context_features, load_replay, modality_record, replay_sample,
)

PATH = Path(os.environ["WRIST_REPLAY"])


class ReplayChecks(unittest.TestCase):
    def test_source_cells_angles_and_alignment(self):
        clip = load_replay(PATH)
        w = replay_sample(PATH)
        self.assertEqual(w["origin"]["first_history_row"], 2812)
        self.assertEqual(w["origin"]["cutoff_row"], 2843)
        self.assertEqual(w["origin"]["actual_target_row"], 2971)
        for family, channels in CHANNELS.items():
            batch = w["observations"]["modalities"][family]
            self.assertEqual(batch["source_id"], SOURCE_IDS[family])
            for rowidx, features in enumerate(batch["values"][0]):
                source_i = 2812 + rowidx - clip["firstSourceRow"]
                self.assertEqual(features, [clip["series"][k][source_i] for k in channels])
                self.assertTrue(all(batch["observed"][0][rowidx]))
        self.assertEqual(w["target"]["record"]["values"][0][0], clip["forecastInput"]["measuredDegrees"][0])
        self.assertEqual(w["target"]["training_loss_weight"], 0)
        for missing in w["unobserved"].values():
            self.assertEqual(missing, {"observed": False, "training_loss_weight": 0})
        self.assertNotIn("physics_generated", w["observations"]["modalities"])

    def test_all_published_target_rows_stay_separate(self):
        clip = load_replay(PATH)
        for tick in clip["forecastInput"]["source"]["targetTicks"]:
            offset = tick - clip["cueSourceRow"]
            w = replay_sample(PATH, offset - 128, offset)
            self.assertEqual(w["origin"]["actual_target_row"], tick)
            self.assertGreater(min(w["query"]["times_s"][0]), max(w["observations"]["times_s"][0]))

    def test_protocol_and_cue_have_different_availability(self):
        a = replay_sample(PATH, -1)
        b = replay_sample(PATH, 0)
        self.assertEqual(a["observations"]["context_values"][0], [1, 1, 1, 1, 0, 0])
        self.assertEqual(b["observations"]["context_values"][0], [1, 1, 1, 1, 0, 1])
        self.assertEqual(b["observations"]["context_available_at_s"][0][-1], 2587 / RATE)
        self.assertFalse(a["events"][1]["available_to_model_by_cutoff"])
        self.assertFalse(a["annotation"]["model_conditioning"])
        self.assertEqual(len(CONTEXT), len(a["observations"]["context_values"][0]))
        with self.assertRaisesRegex(ValueError, "vocabulary"):
            context_features(a["annotation"]["text"], 2331, 2587, 2843, RATE)

    def test_future_can_change_without_changing_any_input(self):
        original = load_replay(PATH)
        changed = copy.deepcopy(original)
        rowidx = 2971 - changed["firstSourceRow"]
        changed["series"]["wristExtension_deg"][rowidx] += 10.0
        changed["forecastInput"]["measuredDegrees"][0][0] += 10.0
        changed["series"]["scalpC3_uV"][rowidx] += 2000
        with patch("wrist_bridge.load_replay", return_value=changed):
            b = replay_sample(PATH)
        a = replay_sample(PATH)
        self.assertEqual(a["observations"], b["observations"])
        self.assertNotEqual(a["target"]["record"]["values"], b["target"]["record"]["values"])

    def test_duplicate_missing_or_mismatched_source_label_is_rejected(self):
        for problem in ("duplicate", "missing", "bad angle"):
            with self.subTest(problem=problem):
                clip = load_replay(PATH)
                packet = clip["forecastInput"]
                if problem == "duplicate":
                    packet["source"]["targetTicks"][1] = 2971
                elif problem == "missing":
                    packet["source"]["targetTicks"][0] = 2972
                else:
                    packet["measuredDegrees"][0][0] += 10.0
                with patch("wrist_bridge.load_replay", return_value=clip), self.assertRaises(ValueError):
                    replay_sample(PATH)

    def test_rejects_changed_clip_or_absent_history_or_nonfuture(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "altered.json"
            path.write_bytes(PATH.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_replay(path)
        for cutoff, target in ((-256, 384), (384, 384), (512, 384), (0, 385)):
            with self.subTest(cutoff=cutoff, target=target), self.assertRaises(ValueError):
                replay_sample(PATH, cutoff, target)

    def test_model_alignment_rejects_wrong_subject_row_and_time(self):
        task, _ = replay_contracts()
        obs, query, targets = replay_tensors(PATH)
        spec = {"measured_motion": SOURCE_IDS["measured_motion"]}
        target = targets["measured_motion"]
        for error in (replace(target, rows=replace(target.rows, raw_parent_ids=("wrong-subject",))),
                      replace(target, event_times_s=target.event_times_s + 1 / RATE)):
            with self.assertRaises(ValueError):
                validate_aligned_forecast(task, obs, query, {"measured_motion": error}, spec)

    def test_real_dev_normalization_rejected_before_statistics(self):
        obs, _, _ = replay_tensors(PATH)
        task, sources = replay_contracts()
        freeze = ScientificFreeze(*(["synthetic-guard-check"] * 8), frozenset({"other"}),
                                  frozenset({PARENT}), frozenset({PAIR}))
        with self.assertRaisesRegex(ValueError, "partition"):
            fit_train_normalizer([obs], sources["neural"], task, freeze, "invalid-fit",
                                 1e-6, "float32")

    def test_absent_and_observed_zero_differ_and_nan_fails(self):
        r = modality_record("x", "p", "t", "s", [[None, 0.0]], [0.0])
        self.assertEqual(r["values"], [[[0.0, 0.0]]])
        self.assertEqual(r["observed"], [[[False, True]]])
        with self.assertRaisesRegex(ValueError, "finite"):
            modality_record("x", "p", "t", "s", [[math.nan, 0.0]], [0.0])


class AnalyticChecks(unittest.TestCase):
    def test_energy_and_restoring_torque(self):
        expected_energy = 0.5 * SIM_STIFFNESS * 0.2**2
        for i in range(65):
            q, v, torque = oscillator(i / 64, 0.2)
            energy = (SIM_INERTIA * v**2 + SIM_STIFFNESS * q**2) / 2
            self.assertAlmostEqual(energy, expected_energy, places=14)
            self.assertAlmostEqual(torque, -SIM_STIFFNESS * q, places=14)

    def test_model_receives_word_features(self):
        result = synthetic_check()
        self.assertTrue(result["finite"])
        self.assertEqual(result["prediction_shape"], [1, 1, 3])
        self.assertGreater(result["max_abs_change_removing_protocol_words_normalized"], 0)
        self.assertEqual(result["fitted_model_updates"], 0)


if __name__ == "__main__":
    configure_cpu_runtime(1, 1, True)
    unittest.main()
