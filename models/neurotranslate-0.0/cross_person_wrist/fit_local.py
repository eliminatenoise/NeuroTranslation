"""Fit exclusively to a caller-selected chronological development recording in local JSONL."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from .forecast import inputs
from .reference import ROLES
from .ridge import fit_heads
from .temporal import HORIZONS, MODES
from .training import fit_partition, partition
from .weights import write


def read_rows(path):
    records = []
    previous = None
    identity = None
    with Path(path).open(encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            data = json.loads(line)
            if not isinstance(data, dict) or set(data) != {"case", "future_by_name"}:
                raise ValueError(f"Training line {number} needs case and future_by_name.")
            case = data["case"]
            names, sample, donor = inputs(case)
            current_id = (case["implant_side"], case["annotated_wrist"])
            first = sample.indices[-1] + 1
            if donor is not None or (identity is not None and identity != current_id):
                raise ValueError("Supply one recording without attached donors. Recent eligible donors are determined in order.")
            if previous is not None and (first - previous < 900 or first // 3600 <= previous // 3600):
                raise ValueError("Training events require at least 900 frames of spacing and strictly increasing blocks.")
            previous, identity = first, current_id
            future = data["future_by_name"]
            if not isinstance(future, dict) or set(future) != {n[0] for n in names}:
                raise ValueError("Training outcomes require the two named wrist tracks.")
            targets = {}
            for role, group in zip(ROLES, names):
                raw = future[group[0]]
                if not isinstance(raw, list) or len(raw) != len(HORIZONS):
                    raise ValueError("Each wrist needs +8 and +15 image-plane targets.")
                for xy in raw:
                    if (not isinstance(xy, list) or len(xy) != 2
                            or any(v is not None and (type(v) not in (int,float) or abs(v)>1e8
                                                      or not np.isfinite(float(v))) for v in xy)):
                        raise ValueError("Use finite detector pixel pairs or null coordinates for absent outcomes.")
                targets[role] = np.asarray(raw, dtype=np.float64)
            records.append((sample, targets))
    return records


def fit(training, path, source, threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    count = len(training)
    x = np.full((count, 15, 6, 2), np.nan)
    y = np.full((count, 2, 2, 2), np.nan)
    for i, (sample, target) in enumerate(training):
        if sample.frame is None:
            continue
        for s, role in enumerate(ROLES):
            if role in sample.arms:
                x[i, :, 3*s:3*s+3] = sample.arms[role] * sample.frame.width
            y[i, :, s] = sample.frame.encode(target[role]) * sample.frame.width
    transport, log, counts = {}, {}, {}
    for label, matched, modes in (("full", False, ("intact", "blocked")), ("matched", True, MODES)):
        use, donors = partition(x, y, np.arange(count), matched)
        if not len(use):
            raise ValueError("No eligible training events for the " + label + " ensemble.")
        counts[label] = len(use)
        fit_partition(x, y, use, donors, modes, "cpu", label, transport, log)
    write(path, transport, fit_heads(training), source)
    return {"training_series": count, "eligible_training_events": counts,
            "fitted_networks": len(log), "updates_per_network": 60,
            "largest_torch_numpy_error_arm_lengths": max(v["max_native_numpy_normalized"] for v in log.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--threads", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    print(json.dumps(fit(read_rows(args.training), args.output, "local", args.threads), indent=2))
