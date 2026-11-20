"""Export the six fixed fitted models; measured nonlinear training landmarks stay in their original data."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
METHODS = ("ridge", "transformer")
MODES = ("markers", "emg", "combined")
DENSE = ("embed", "qkv", "out", "ff1", "ff2", "head", "n1", "n2", "n3")
SOURCES = HERE / "src" / "source-sha256.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(models, assessment):
    pins = json.loads(SOURCES.read_text())
    weights = {k: {} for k in METHODS}
    for method in METHODS:
        for mode in MODES:
            name = f"{method}-{mode}.npz"
            path = models / "weights" / name
            if sha(path) != pins[name]:
                raise ValueError(f"Unexpected fitted file: {name}")
            with np.load(path, allow_pickle=False) as w:
                center, scale = w["center"].tolist(), w["scale"].tolist()
                if len(center) != 40 or len(scale) != 40 or min(scale) <= 0:
                    raise ValueError("Unexpected scaler")
                if "center" in weights and (weights["center"] != center or weights["scale"] != scale):
                    raise ValueError("These fits do not share a scaler")
                weights["center"], weights["scale"] = center, scale
                params = {"coef", "bias"} if method == "ridge" else {
                    f"{layer}.{part}" for layer in DENSE for part in ("weight", "bias")} | {"pos"}
                if set(w.files) != params | {"center","scale"}:
                    raise ValueError(f"Unexpected parameter set in {name}")
                weights[method][mode] = {k: w[k].tolist() for k in sorted(params)}
    if sha(assessment) != pins["assessment"]:
        raise ValueError("Unexpected assessment result")
    scores = json.loads(assessment.read_text())
    # Only aggregate tables are needed for this view.
    keys = ("held_people","held_trials","held_anchors","metrics","target_strata",
            "incremental_EMG_comparisons","incremental_EMG_gate_passed")
    return {"weights":weights,"assessment":{k:scores[k] for k in keys},"signatures":pins}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("models",type=Path)
    p.add_argument("assessment",type=Path)
    args = p.parse_args()
    (HERE/"src"/"bundle.json").write_text(json.dumps(export(args.models,args.assessment),
        ensure_ascii=False,allow_nan=False,separators=(",",":"))+"\n")
