"""Score the four frozen networks on a qualified assessment NPZ; emit only cohort summaries."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from network import decode_state, predict
from records import donors, sha, subset
from report import describe, errors

HERE = Path(__file__).resolve().parent
METRICS = ("heel_mm", "force_N", "X_bias_mm", "Y_bias_mm", "Z_bias_mm", "force_bias_N")


def assess(source):
    seal = json.loads((HERE / "PRETEST-SHA256.json").read_text())
    reference = json.loads((HERE / "aggregate.json").read_text())
    populations = seal["qualified_assessment_npz_sha256"]
    partition = next((k for k, digest in populations.items() if digest == sha(source)), None)
    if partition is None:
        raise ValueError("Select a verified original-assessment or later-repeats NPZ from the source reader.")
    with np.load(source, allow_pickle=False) as arrays:
        d = {k: arrays[k] for k in ("person", "repeat", "offset", "marker_mm", "emg_uv", "heel_delta_mm", "force_n")}
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    forecasts = {}
    for kind in ("joint", "heel", "force", "marker"):
        name = kind + "-model.json"
        if sha(HERE / name) != seal["task_trained_weights"][name]:
            raise ValueError("Weight file differs from the frozen fit: " + name)
        model = json.loads((HERE / name).read_text())
        state = decode_state(model)
        forecasts[kind] = predict(state, d, model["norm"], kind)
        if kind == "joint":
            take, donor = donors(d)
            matched = subset(d, take)
            matched["emg_uv"] = d["emg_uv"][donor]
            wrong = np.full((len(d["person"]), 4), np.nan)
            wrong[take] = predict(state, matched, model["norm"], kind)
            forecasts["wrong_emg"] = wrong
    error = {k: errors(d, forecast) for k, forecast in forecasts.items()}
    models = {k: {metric: describe(d, e[:, i]) for i, metric in enumerate(METRICS)}
              for k, e in error.items()}
    paired = {k: {metric: describe(d, error["joint"][:, i] - e[:, i]) for i, metric in enumerate(METRICS[:2])}
              for k, e in error.items() if k != "joint"}
    expected = reference[partition]
    exact = (all(models[k] == expected["models"][k] for k in models)
             and all(paired[k] == expected["joint_minus"][k] for k in paired))
    return {"partition": partition, "models": models, "joint_minus": paired,
            "exact_reference_floats": exact}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qualified_npz", type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.qualified_npz), indent=2, allow_nan=False))
