"""Exercise sensor identity, future-row alignment, isolation and inference using invented signals."""
from dataclasses import replace
import unittest
import numpy as np
import torch
from train import PARTS, PARENT_NAMES, collect, moments, optimizer_for, update
from model import Events, make_model, source
from predict import parse_record


def fake_record(part):
    return {"body_part":part, "samples":[[1,2,3] for _ in range(16)], "timestamps_ms":list(range(0,640,40))}


class LimbTests(unittest.TestCase):
    def setUp(self):
        raw = np.arange(125*15, dtype=float).reshape(125,15)
        self.data = collect([(PARENT_NAMES[0], raw)])
        self.ds = self.data["left_leg"]

    def test_columns_and_row_index(self):
        for i, p in enumerate(PARTS):
            ds = self.data[p]
            x, y = ds.histories[0], ds.events.values[0]
            np.testing.assert_array_equal(x[-1], np.arange(3)+225+3*i)
            np.testing.assert_array_equal(y, np.arange(3)+270+3*i)
            self.assertEqual(ds.cutoffs[0],15)
            self.assertEqual(ds.events.rows[0],18)

    def test_wrong_target_placement_rejected(self):
        ds = replace(self.ds, events=replace(self.ds.events,part="left_arm"))
        with self.assertRaises(ValueError):
            ds.batch(np.array([0]))

    def test_shifted_label_rejected(self):
        ds = replace(self.ds, events=replace(self.ds.events,rows=self.ds.events.rows+1))
        with self.assertRaises(ValueError):
            ds.batch(np.array([0]))

    def test_switched_member_rejected(self):
        ds = replace(self.ds, events=replace(self.ds.events,members=(PARENT_NAMES[1],)*7))
        with self.assertRaises(ValueError):
            ds.batch(np.array([0]))

    def test_held_people_blocked(self):
        for person in ("p5", "p6", "p7", "p8"):
            with self.assertRaises(ValueError):
                collect([(f"data/a09/{person}/s01.txt", np.ones((125,15)))])

    def test_shared_update_and_placement_gating(self):
        torch.set_num_threads(1)
        model = make_model(moments(self.data), [PARENT_NAMES[0]]).train()
        shared = next(model.temporal.parameters())
        old_shared = shared.detach().clone()
        old_arm = model.encoders[model.source_keys[source("right_arm")]][0].weight.detach().clone()
        opt = optimizer_for(model)
        update(model, opt, "left_leg", self.ds.batch(np.array([0,1])))
        self.assertFalse(torch.equal(old_shared,shared))
        self.assertTrue(torch.equal(old_arm,model.encoders[model.source_keys[source("right_arm")]][0].weight))
        with self.assertRaises(ValueError):
            update(model,opt,"left_arm",self.ds.batch(np.array([0,1])))

    def test_bad_input(self):
        rec = fake_record("right_arm")
        with self.assertRaises(ValueError):
            parse_record(rec, "left_arm")
        rec["timestamps_ms"][9] += 1
        with self.assertRaises(ValueError):
            parse_record(rec, "right_arm")
        rec = fake_record("torso")
        rec["samples"][9] = [1,2]
        with self.assertRaises(ValueError):
            parse_record(rec, "torso")


if __name__ == "__main__":
    unittest.main()
