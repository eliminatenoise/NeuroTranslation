"""Extract just the numeric weights needed by the five fixed knee moment estimators."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

SOURCE_SHA = "7a0c17c66049fba7812d0acf1392af21829c3c6528ace3667202c8091f97f8b4"
HERE = Path(__file__).resolve().parent

def export(checkpoint):
    with np.load(checkpoint, allow_pickle=False) as state:
        config = json.loads(str(state["configuration"]))
        assert (config["heads"], config["layers"], config["knee_moment"]["history_frames"]) == (4, 1, 400)
        names = sorted(k for k in state if k == "position" or k.startswith(("project.", "blocks.", "last_norm.")))
        rng = np.random.default_rng(4281)
        weights = {m: {} for m in ("shared", "scrambled", "trained")}
        for name in names:
            original = state[name].ravel()
            weights["shared"][name] = original.tolist()
            weights["scrambled"][name] = rng.permutation(original).tolist()
            weights["trained"][name] = state["load.trained." + name].ravel().tolist()
        for key in ("readout.weight", "readout.bias"):
            weights["trained"][key] = state["load.trained." + key].ravel().tolist()
        weights["stats"] = {
            k.removeprefix("load."): state[k].ravel().tolist()
            for k in sorted(state) if k.startswith("load.") and not k.startswith("load.trained.")
        }
    payload = {"format": 1, "checkpoint_sha256": SOURCE_SHA, **weights}
    encoded = (json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n").encode()
    if hashlib.sha256(encoded).hexdigest() != "b4062509f2cdf4cbe7e5ce968ebac54d9dcc47e9edf1978fdf9f3b51364c9884":
        raise ValueError("The knee moment export differs from its released checkpoint.")
    return payload

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=HERE / "src/weights.json")
    args = parser.parse_args()
    args.output.write_text(json.dumps(export(args.checkpoint), separators=(",", ":"), allow_nan=False) + "\n")
