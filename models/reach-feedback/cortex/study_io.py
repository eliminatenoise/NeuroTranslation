"""Study input and output contracts. No numerical held-split access before release."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from count_model import SEEDS

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
import sys
sys.path.insert(0, str(BASE))
IDENTITY = ("original", "block", "ordinal", "k", "fold")


def sha(path):
    return hashlib.file_digest(Path(path).open("rb"), "sha256").hexdigest()


def dump(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    os.replace(temp, path)


def npz(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("wb") as stream:
        np.savez_compressed(stream, **data)
    os.replace(temp, path)


def require_stage(split):
    from freeze import verify_stage
    verify_stage(BASE, "test" if split in ("within", "transfer") else split)


def load_inputs(split, fit=False):
    require_stage(split)
    if fit and split != "train":
        raise ValueError("Training uses only train")
    source_path = BASE / "source" / (split + ".npz")
    motor_path = BASE / "motor" / ("oof.npz" if split == "train" else split + "-predictions.npz")
    with np.load(source_path) as src, np.load(motor_path) as motor:
        for key in IDENTITY:
            np.testing.assert_array_equal(src[key], motor[key])
        np.testing.assert_array_equal(SEEDS, motor["seeds"])
        mask = src["fold"] > 0 if split == "train" else np.ones(len(src["original"]), bool)
        if split == "train":
            np.testing.assert_array_equal(mask, motor["supported"])
            if not np.isnan(motor["full"][:, ~mask]).all() or not np.isnan(motor["ridge_full"][~mask]).all():
                raise ValueError("Expected empty warmup forecasts")
        rows = np.flatnonzero(mask)
        arrays = {k: src[k][mask] for k in (*IDENTITY, "pose", "spikes", "cue", "movement")}
        if fit:
            arrays["delayed"] = src["delayed"][mask]
        arrays["unit_guide"] = src["unit_guide"]
        if arrays["unit_guide"].shape != (23, 2):
            raise ValueError("Expected 23 sorted unit identities")
        arrays["source_row"] = rows
        arrays["forecast"] = motor["full"][:, mask]
        arrays["ridge"] = motor["ridge_full"][mask]
        if arrays["forecast"].shape != (3, len(rows), 10, 8) or arrays["ridge"].shape != (len(rows), 10, 8):
            raise ValueError("Unexpected forecast dimensions")
        if not np.isfinite(arrays["forecast"]).all() or not np.isfinite(arrays["ridge"]).all():
            raise ValueError("Missing expected forecast")
        # Compare independently reconstructed donors with the extractor's full-row donor ledger.
        donor = source_donors(arrays)
        source_donor = src["donor"][rows]
        backward = np.full(len(mask), -1, int)
        backward[rows] = np.arange(len(rows))
        admitted = source_donor >= 0
        expected = np.full(len(rows), -1, int)
        expected[admitted] = backward[source_donor[admitted]]
        np.testing.assert_array_equal(donor, expected)
        arrays["donor"] = donor
    return arrays


def source_donors(arrays):
    n = len(arrays["original"])
    donor = np.full(n, -1, int)
    seen = {}
    for i in np.argsort(arrays["k"], kind="stable"):
        group = (arrays["block"][i], arrays["ordinal"][i])
        old = seen.get(group)
        if old is not None:
            if arrays["k"][old] >= arrays["k"][i] or arrays["original"][old] >= arrays["original"][i]:
                raise ValueError("Invalid source chronology for the paired movement control")
            donor[i] = old
        seen[group] = i
    return donor


def arm_input(data, arm, forecast):
    return {"pose": data["pose"], "cue": data["cue"], "spikes": data["spikes"],
            "movement": data["movement"] if arm == "privileged" else forecast}
