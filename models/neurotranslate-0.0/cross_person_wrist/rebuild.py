"""Rebuild the public checkpoint exclusively from the invented camera series."""
import argparse
import json
from pathlib import Path

import numpy as np

from .forecast import inputs, predict
from .reference import ROLES
from .fit_local import fit
from .simulate import stream
from .weights import validate


def training_data():
    return [(inputs(case)[1], targets) for case, targets in stream(347, 60)]


def evaluate(state):
    values = {}
    previous = None
    for case, targets in stream(1729, 16, "R"):
        if previous is not None:
            case["earlier_donor"] = previous
        previous = {k: case[k] for k in ("frame_indices","prior_by_name")}
        forecasts = predict(case, state)
        if "earlier_donor" not in case:
            continue
        truth = np.stack([targets[role] for role in ROLES], axis=1)
        for label, data in forecasts["methods"].items():
            e = np.linalg.norm(np.asarray(data["endpoint_native_px"]) - truth, axis=-1)
            values.setdefault(label, []).append(e)
    return {"domain": "synthetic held sequences only", "common_events": 15, "units": "invented detector pixels",
            "axes": ["horizon 8 then 15", "contralateral then ipsilateral"],
            "mean_endpoint_error": {label: np.mean(errors, axis=0).tolist() for label, errors in values.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New JSON file. Existing files are preserved.")
    parser.add_argument("--threads", type=int, choices=(1,2), default=2)
    args = parser.parse_args()
    result = fit(training_data(), args.output, "synthetic", args.threads)
    result["evaluation"] = evaluate(validate(json.loads(args.output.read_bytes())))
    print(json.dumps(result, indent=2, allow_nan=False))
