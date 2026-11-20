"""Score the sealed training weights on the fixed held-person partition."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from extract import TEST, path_for
from predict import MODELS, predict
from study_data import load_set, samples


def forecast_many(rows, weights, method):
    return np.concatenate([predict(rows[i:i + 256], weights, method) for i in range(0, len(rows), 256)])


def scores(trial, weights):
    errors = {}
    for model in MODELS:
        pred = forecast_many(trial.x, weights, model)
        errors[model] = np.abs(pred - trial.y).mean(axis=0).tolist()
    # Keep the knees, labels and tested anchors fixed. Move hip/ankle histories by
    # half the ordered eligible windows. This is a retrospective mismatch control.
    shifted = trial.x.copy()
    shift_cols = [0, 1, 4, 5]
    shifted[:, :, shift_cols] = np.roll(trial.x[:, :, shift_cols], len(shifted) // 2, axis=0)
    for model in ("all_ridge", "transformer"):
        pred = forecast_many(shifted, weights, model)
        errors[model + "_mismatched_hips_ankles"] = np.abs(pred - trial.y).mean(axis=0).tolist()
    i = len(trial.x) // 2
    cut = trial.anchors[i]
    alt = trial.degrees.copy()
    alt[cut + 1:] += 123.0
    x2, y2, anchors = samples(alt, trial.frame)
    if anchors[i] != cut or not np.array_equal(trial.x[i], x2[i]) or not np.allclose(y2[i] - trial.y[i], 123):
        raise ValueError("Later-angle perturbation reached input or missed label")
    deltas = {m: float(np.max(np.abs(predict(x2[i], weights, m) - predict(trial.x[i], weights, m)))) for m in MODELS}
    if any(deltas.values()):
        raise ValueError("A future-angle perturbation changed a prediction")
    return errors, dict(eligible_anchor_index=i, frame=float(trial.frame[cut]), changed_future_degrees=123,
                        delta_prediction_each_method=deltas)


def quantiles(a):
    return np.quantile(a, [.025, .975]).tolist()


def summarize(per_person):
    names = list(next(iter(per_person.values())))
    resamples = np.random.default_rng(21301).integers(len(per_person), size=(10_000, len(per_person)))
    out, paired = {}, {}
    for method in names:
        by_limb = np.array([person[method] for person in per_person.values()])
        person = by_limb.mean(axis=1)
        out[method] = dict(equal_person_mean_mae_degrees=float(person.mean()), right_left_mae_degrees=by_limb.mean(axis=0).tolist(),
                           median_person_mae_degrees=float(np.median(person)), person_range_degrees=[float(person.min()),float(person.max())],
                           bootstrap95_mean_mae_degrees=quantiles(person[resamples].mean(axis=1)))
    for method in ("transformer", "all_ridge"):
        compared = [n for n in MODELS if n != method] + [method + "_mismatched_hips_ankles"]
        for baseline in compared:
            delta = np.array([np.mean(row[baseline]) - np.mean(row[method]) for row in per_person.values()])
            paired[f"{method}_vs_{baseline}"] = dict(baseline_minus_model_mae_degrees=float(delta.mean()),
                                                      bootstrap95_degrees=quantiles(delta[resamples].mean(axis=1)),
                                                      participant_wins=int((delta > 0).sum()), ties=int((delta == 0).sum()),
                                                      participants=len(delta))
    return out, paired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("weights", type=Path)
    parser.add_argument("train_receipt", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("sources", type=Path)
    parser.add_argument("private_receipt", type=Path)
    args = parser.parse_args()
    train = json.loads(args.train_receipt.read_text())
    whash = hashlib.sha256(args.weights.read_bytes()).hexdigest()
    if whash != train["weights_sha256"] or train["updates"] != 700:
        raise ValueError("Expected the sealed 700-update training fit")
    train_info = train["training_trials"]
    known = [x["angle_sha256"] for x in train_info]
    held, dropped = load_set(args.cache, TEST, known)
    weights = json.loads(args.weights.read_text())
    per_person, anti_leak = {}, {}
    for ident, t in held.items():
        per_person[ident], anti_leak[ident] = scores(t, weights)
    out, paired = summarize(per_person)
    trainwin = sum(x["windows"] for x in train_info)
    testwin = sum(len(t.x) for t in held.values())
    results = dict(format="gait-knees-results-1", archive_version="1.0.0", source="https://doi.org/10.13026/r0ea-7161",
                   weights_sha256=whash, train_people=len(train_info), test_people=len(held),
                   train_windows=trainwin, test_windows=testwin, measurement="Offline Xsens-derived bilateral knee flexion/extension, degrees, +15 stored frames at 0.5 m/s.",
                   weighting="Within participant mean absolute error over both knees and all eligible cutoffs; arithmetic mean across people. Right/left scores also equal-person.",
                   uncertainty="Paired percentile bootstrap across held participants, 10000 resamples seed 21301. Overlapping frames do not enter as independent draws.",
                   split_exclusions={"source_lists_missing_training":[24],"duplicate_train":train["dropped"],"duplicate_test":dropped},
                   error_summary=out, paired_differences=paired,
                   mismatch="Retrospective control: keep knee histories, cyclically move complete bilateral hip and ankle histories by half the ordered eligible windows within each held trial. Same weights; no refit.",
                   causal_input_check="Every model returned identical values when all later six-joint values were increased 123 degrees, with the future endpoint also increasing 123 degrees. One interior cutoff per scored participant. Six trial headers report whole-record HD processing and 45 report Live. Actual per-frame availability was not measured.",
                   longer_history_comparison="A prior-stride copy with 240 available frames beats the 25-frame-span Transformer in 10 of 12 people on their common cutoffs. See phase-results.json for both errors and the paired interval.")
    test_info = [t.info for t in held.values()]
    sources = {"format":"gait-knees-sources-1","archive_url":"https://physionet.org/files/multimodal-gait-dataset/1.0.0/Dataset/IMU_Data/IMU.tar.gz",
               "archive_sha256":"70ebdfee244c78c5726ec99be7864b99629c0b1eb02a66a558a625fd095b06b2",
               "columns":train_info[0]["column_headers"], "frame_column":train_info[0]["frame_header"], "members":[]}
    for split, entries in (("train",train_info),("test",test_info)):
        for r in entries:
            if r["column_headers"] != sources["columns"] or r["frame_header"] != sources["frame_column"]:
                raise ValueError("Source headers vary; release a per-file column mapping before use.")
            sources["members"].append({"path":path_for(r["subject"]), "subject":r["subject"], "split":split, "sha256":r["file_sha256"],
                                       "rows":r["rows"], "eligible_windows":r["windows"]})
    private = dict(test_quality=test_info, per_person_right_left_mae_degrees=per_person, perturbation_checks=anti_leak, dropped_test=dropped)
    for path, obj in ((args.results, results), (args.sources, sources), (args.private_receipt, private)):
        path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
