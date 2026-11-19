"""Score fixed Random-task index forecasts on original Hyser N-DoF force files."""
import argparse
import json
from importlib import import_module
from itertools import product
from pathlib import Path

import numpy as np

from score_session import read_signal

PREDICTOR = import_module("whole-hand.finger_context")
BASE = Path(__file__).resolve().parent
ARMS = ("persistence", "index_only", "aligned_five", "aligned_summary")
INDEX_CUED = frozenset((1, 5, 6, 7, 9, 10, 11, 15))
COMBINATIONS = tuple(range(1, 16))
CONTRASTS = {
    "five_vs_index": ("aligned_five", "index_only"),
    "five_vs_compact": ("aligned_five", "aligned_summary"),
    "compact_vs_index": ("aligned_summary", "index_only"),
    "index_vs_last": ("index_only", "persistence"),
}


def weights():
    return json.loads((BASE / "whole-hand" / "WEIGHTS.json").read_text(encoding="utf-8"))


def trial_errors(frames, pooled):
    """Return the signed error for four forecasts, in volts at identical cutoffs."""
    frames = np.asarray(frames, dtype=float)
    if frames.shape != (2500, 5):
        raise ValueError("Expected 2,500 frames and five named finger sensors.")
    ticks = PREDICTOR.TICKS
    target = frames[ticks + PREDICTOR.HORIZON, 1]
    if not np.isfinite(target).all():
        raise ValueError("At least one scheduled future index reading is missing.")
    forecasts = [frames[ticks, 1]]
    forecasts.extend(PREDICTOR.predict(frames, ticks, pooled, arm) for arm in ARMS[1:])
    errors = np.column_stack(forecasts) - target[:, None]
    if not np.isfinite(errors).all():
        raise ValueError("Scheduled input windows must be complete for every forecast.")
    return errors


def score_conditions(errors_by_combination):
    """Pool all eligible windows before taking the square root for this person-day."""
    groups = {"all": list(errors_by_combination),
              "index_cued": [c for c in errors_by_combination if c in INDEX_CUED],
              "index_uncued": [c for c in errors_by_combination if c not in INDEX_CUED]}
    groups = {group: keys for group, keys in groups.items() if keys}
    result = {}
    for group, keys in groups.items():
        errors = np.concatenate([errors_by_combination[k] for k in keys])
        mae, rmse = np.abs(errors).mean(axis=0), np.sqrt(np.square(errors).mean(axis=0))
        result[group] = {"cutoffs": len(errors), "trials": len(keys),
                         "models": {arm: {"mae_v": float(mae[i]), "rmse_v": float(rmse[i])}
                                    for i, arm in enumerate(ARMS)}}
    return result


def score_session(folder, combinations=COMBINATIONS, repetition=1):
    """Open only the named N-DoF force pair for each selected combination."""
    pooled = weights()
    errors = {}
    for c in combinations:
        try:
            frames = read_signal(folder, "force", repetition, all_digits=True, combination=c)
            errors[c] = trial_errors(frames, pooled)
        except (OSError, ValueError) as err:
            raise ValueError(f"Could not score combination {c}, repetition {repetition}: {err}") from err
    return score_conditions(errors)


def summarize_people(person_days):
    """Aggregate two days per person. Input records remain local to the caller."""
    n = len(person_days)
    if n not in (4, 12) or any(set(days) != {1, 2} for days in person_days):
        raise ValueError("Expected two completed days for each of 12 fit or four development people.")
    draws = (np.array(list(product(range(n), repeat=n))) if n == 4 else
             np.random.default_rng(196233).integers(n, size=(10000, n)))
    result = {}
    for group in ("all", "index_cued", "index_uncued"):
        parts = [d[day][group] for d in person_days for day in (1, 2)]
        trials_per_day = {"all": 15, "index_cued": 8, "index_uncued": 7}[group]
        if any(p["trials"] != trials_per_day or p["cutoffs"] != trials_per_day * len(PREDICTOR.TICKS)
               for p in parts):
            raise ValueError(f"Incomplete prescribed data in the {group} group.")
        output = {"trials": sum(p["trials"] for p in parts),
                  "cutoffs": sum(p["cutoffs"] for p in parts), "time": {}}
        scores = np.array([[[[days[day][group]["models"][arm][metric] for metric in ("mae_v", "rmse_v")]
                             for arm in ARMS] for day in (1, 2)] for days in person_days])
        for name, data in (("day1", scores[:, 0]), ("day2", scores[:, 1]), ("both_days", scores.mean(axis=1))):
            models = {arm: dict(zip(("mae_v", "rmse_v"), map(float, data[:, i].mean(axis=0))))
                      for i, arm in enumerate(ARMS)}
            paired = {}
            for contrast, (focus, comparator) in CONTRASTS.items():
                differences = data[:, ARMS.index(comparator)] - data[:, ARMS.index(focus)]
                bounds = np.quantile(differences[draws].mean(axis=1), [.025, .975], axis=0, method="linear")
                paired[contrast] = {
                    metric: {"gain_v": float(differences[:, i].mean()),
                             "positive_people": int(np.sum(differences[:, i] > 0)),
                             "ties": int(np.sum(differences[:, i] == 0)),
                             "middle95_v": bounds[:, i].tolist()}
                    for i, metric in enumerate(("mae", "rmse"))}
            output["time"][name] = {"models": models, "paired": paired}
        result[group] = output
    return {"people": n, "days_per_person": 2, "groups": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="One original ndof_dataset/subjectNN_sessionD folder.")
    parser.add_argument("--combination", type=int, choices=COMBINATIONS,
                        help="Score a single combination. The default scores all 15.")
    parser.add_argument("--repetition", type=int, choices=(1, 2), default=1,
                        help="Repetition 1 matches the study protocol.")
    args = parser.parse_args()
    try:
        groups = score_session(args.folder, [args.combination] if args.combination else COMBINATIONS,
                               args.repetition)
    except (OSError, ValueError, ImportError, TypeError) as error:
        parser.exit(2, f"Could not score this session. {error}\n")
    print(json.dumps({"unit": "V", "task": "Hyser N-DoF", "repetition": args.repetition, "groups": groups},
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
