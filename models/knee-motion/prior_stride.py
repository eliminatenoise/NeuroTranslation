"""Reproduce the longer-history stride control on the same held-out cutoffs."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from assess import forecast_many
from extract import TEST
from study_data import load_trial


def prior_stride(trial):
    """Compare recent knees to earlier knees without seeing the future target."""
    knee = trial.degrees[:, 2:4]
    anchors = trial.anchors
    if len(knee) < 240:
        return np.zeros(len(anchors), bool), np.empty((0, 2))
    good = np.isfinite(knee).all(axis=1)
    step_ok = good[1:] & good[:-1] & (np.diff(trial.frame) == 1)
    contiguous = np.lib.stride_tricks.sliding_window_view(step_ok, 239).all(axis=1)
    eligible = np.r_[np.zeros(239, dtype=bool), contiguous][anchors]
    cut = anchors[eligible]
    periods = np.arange(45, 181)
    cost = []
    for p in periods:
        delta = knee[p:] - knee[:-p]
        error = np.nan_to_num(np.sum(delta ** 2, axis=1))
        sums = np.r_[0., np.cumsum(error)]
        cost.append(sums[cut - p + 1] - sums[cut - p - 59])
    period = periods[np.argmin(cost, axis=0)]
    return eligible, knee[cut + 15 - period]


def compare(cache, weights_file, source_file):
    source = json.loads(source_file.read_text())
    weights = json.loads(weights_file.read_text())
    averages = []
    count = 0
    for entry in source["members"]:
        if entry["split"] != "test":
            continue
        if entry["subject"] not in TEST:
            raise ValueError("Unexpected test identity in sources file")
        trial = load_trial(cache, entry["subject"])
        if trial.info["file_sha256"] != entry["sha256"]:
            raise ValueError(f"Source hash mismatch for {entry['path']}")
        eligible, stride = prior_stride(trial)
        reference = trial.y[eligible]
        pred = forecast_many(trial.x[eligible], weights, "transformer")
        averages.append([np.abs(pred - reference).mean(), np.abs(stride - reference).mean()])
        count += int(eligible.sum())
    a = np.asarray(averages)
    delta = a[:,0] - a[:,1]
    sample = np.random.default_rng(21301).integers(len(a), size=(10000,len(a)))
    return dict(weight_sha256=hashlib.sha256(weights_file.read_bytes()).hexdigest(),
                test_people=len(a), eligible_cutoffs=count, prior_stride_mean_mae_degrees=float(a[:,1].mean()),
                transformer_mean_mae_degrees=float(a[:,0].mean()), transformer_minus_stride_mae_degrees=float(delta.mean()),
                prior_stride_wins=int((delta > 0).sum()), transformer_wins=int((delta < 0).sum()),
                ties=int((delta == 0).sum()), paired_person_bootstrap_ci95=np.quantile(delta[sample].mean(axis=1), [.025,.975]).tolist())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--weights", type=Path, default=Path(__file__).with_name("weights.json"))
    parser.add_argument("--sources", type=Path, default=Path(__file__).with_name("sources.json"))
    args = parser.parse_args()
    print(json.dumps(compare(args.cache, args.weights, args.sources), indent=2))
