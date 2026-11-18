"""Calibrate a frozen scalp-EEG/palm model on R1 and score on distinct R2."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from threadpoolctl import threadpool_limits

from frozen_cohort import run as cohort


ROOT = Path(__file__).resolve().parent
DESIGN_SHA = "d621ee2859bc8e8e2f16f553e332f63b4fdf890fbc52a38c6684e86839b578cd"
SOURCE_PATH = ROOT / "SOURCE.json"
SOURCE_SHA = "a8068a70b4ae0fe11184d5d49741b38d49cd3f368faff9b96799dc09d0ec719c"
RMSE_TOLERANCE_MM = 1e-12
STUDY_ID = "iackd-right-hand-cross-run-last-head-v1"


def load_json(path, wanted_sha):
    if cohort.sha(path) != wanted_sha:
        raise cohort.GateError(f"SHA-256 mismatch for {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def study_files():
    design = load_json(ROOT / "DESIGN.json", DESIGN_SHA)
    expected = design["baseline"]
    if cohort.sha(ROOT / "frozen_cohort" / "run.py") != expected["runner_sha256"]:
        raise cohort.GateError("Frozen cohort extractor identity changed")
    protocol = cohort.load_design()
    model = load_json(ROOT / "frozen_cohort" / "MODEL-STATE.json", expected["model_sha256"])
    if (
        cohort.DESIGN_SHA != expected["design_sha256"]
        or model["model_id"] != expected["model_id"]
        or model["release_commit"] != design["dataset"]["release_commit"]
        or model["roles"] != {"TRAIN": expected["train"], "DEV": expected["prior_dev"]}
        or model["design_sha256"] != expected["design_sha256"]
        or model["runner_sha256"] != expected["runner_sha256"]
    ):
        raise cohort.GateError("Frozen state and design disagree")
    return design, protocol, model


def input_bindings(source, dataset):
    if source["release_commit"] != dataset["release_commit"]:
        raise cohort.GateError("Input release differs from the study")
    expected = {
        (subject, role)
        for subject in dataset["participants"]
        for role in dataset["roles"]
    }
    bindings = {}
    checksums = set()
    for row in source["participants"]:
        identity = row["subject"], row["role"]
        if identity not in expected or identity in bindings:
            raise cohort.GateError("Unexpected or repeated source identity")
        subject, role = identity
        run = dataset["roles"][role]
        basename = f"{subject}_task-ihc_run-{run}_eeg_leap_R{int(run)}.mat"
        channels = row["channels"]
        columns = [channel["index_zero_based"] for channel in channels]
        digest = row["asset_sha256"]
        if (
            row["run"] != run
            or row["basename"] != basename
            or row["asset_bytes"] <= 0
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or digest in checksums
            or [channel["name"] for channel in channels] != ["C3", "Cz", "C4"]
            or any(channel["type"] != "EEG" for channel in channels)
            or len(set(columns)) != 3
            or any(type(idx) is not int or idx not in range(row["n_channels"]) for idx in columns)
        ):
            raise cohort.GateError(f"Incorrect run or channel binding for {subject} {role}")
        bindings[identity] = row
        checksums.add(digest)
    if set(bindings) != expected:
        raise cohort.GateError("Some required R1/R2 identities are absent")
    return bindings


def read_role(input_dir, dataset, bindings, protocol, role):
    paths = {}
    for subject in dataset["participants"]:
        binding = bindings[subject, role]
        path = input_dir / binding["basename"]
        if path.stat().st_size != binding["asset_bytes"] or cohort.sha(path) != binding["asset_sha256"]:
            raise cohort.GateError(f"Input identity mismatch for {subject} {role}")
        paths[subject] = path
    recordings = {}
    minimum = protocol["eligibility"]["minimum_eligible_trials_per_participant"]
    for subject, path in paths.items():
        binding = bindings[subject, role]
        rec = cohort.read_recording(path, binding, protocol)
        if rec.custody["released_trials"] != binding["released_trials"]:
            raise cohort.GateError(f"Source trial count differs for {subject} {role}")
        if rec.custody["eligible_trials"] < minimum:
            raise cohort.GateError(
                f"{subject} {role} has {rec.custody['eligible_trials']} eligible trials; "
                f"{minimum} are required. Custody: {json.dumps(rec.custody, sort_keys=True)}"
            )
        recordings[subject] = rec
    return recordings


def standardized(features, model):
    return (features[..., model["feature_indices"]] - model["center"]) / model["scale"]


def fit_correction(recording, model, penalty):
    z = standardized(recording.features, model)
    residual = recording.target - cohort.predict(recording.features, model)
    z_mean = z.mean(axis=0)
    residual_mean = residual.mean(axis=0)
    x = (z - z_mean).reshape(-1, z.shape[-1])
    y = (residual - residual_mean).ravel()
    gram = x.T @ x / len(y)
    moments = x.T @ y / len(y)
    slopes = np.linalg.solve(gram + penalty * np.eye(x.shape[1]), moments)
    return {
        "bias_mm": float(residual_mean.mean()),
        "timing_only_intercepts_mm": residual_mean.tolist(),
        "ridge_delta_slopes": slopes.tolist(),
        "ridge_delta_intercepts_mm": (residual_mean - z_mean @ slopes).tolist(),
    }


def provenance(design, source_sha):
    return {
        "study": STUDY_ID,
        "design_sha256": DESIGN_SHA,
        "runner_sha256": cohort.sha(Path(__file__)),
        "source_sha256": source_sha,
        "frozen_model_id": design["baseline"]["model_id"],
        "frozen_model_sha256": design["baseline"]["model_sha256"],
        "release_commit": design["dataset"]["release_commit"],
        "terminology_registry": design["terminology_registry"],
    }


def recording_summary(recording, binding):
    return {
        **recording.custody,
        "scored_rows": int(recording.target.size),
        "basename": binding["basename"],
        "asset_sha256": binding["asset_sha256"],
    }


def calibrate(design, base, source_sha, bindings, recordings):
    return {
        "kind": "R1_subject_specific_last_head_corrections",
        **provenance(design, source_sha),
        "ridge_lambda": design["ridge_lambda"],
        "participants": {
            subject: {
                "calibration": recording_summary(recording, bindings[subject, "CALIBRATION"]),
                "corrections": {
                    name: fit_correction(recording, base["models"][name], design["ridge_lambda"])
                    for name in design["baseline"]["methods"]
                },
            }
            for subject, recording in recordings.items()
        },
    }


def verified_state(path, state_sha, design, source_sha, bindings):
    state = load_json(path, state_sha)
    expected = provenance(design, source_sha)
    if any(state[key] != value for key, value in expected.items()):
        raise cohort.GateError("Calibration state provenance disagrees with the active study")
    if (
        state["kind"] != "R1_subject_specific_last_head_corrections"
        or state["ridge_lambda"] != design["ridge_lambda"]
        or set(state["participants"]) != set(design["dataset"]["participants"])
    ):
        raise cohort.GateError("Unexpected R1 calibration state")
    for subject, calibrated in state["participants"].items():
        returned = calibrated["calibration"]
        binding = bindings[subject, "CALIBRATION"]
        if any(returned[key] != binding[key] for key in ("basename", "asset_sha256")):
            raise cohort.GateError(f"Calibration source changed for {subject}")
    return state


def predict_all(features, methods, models, corrections):
    predictions = {}
    for name in methods:
        model = models[name]
        correction = corrections[name]
        frozen = cohort.predict(features, model)
        predictions[f"{name}_frozen"] = frozen
        predictions[f"{name}_bias"] = frozen + correction["bias_mm"]
        predictions[f"{name}_timing"] = frozen + correction["timing_only_intercepts_mm"]
        predictions[f"{name}_ridge"] = ridge_prediction(features, model, correction)

    rotated = np.concatenate((features[..., :2], np.roll(features[..., 2:], -1, axis=0)), axis=2)
    model = models["time_palm_eeg"]
    predictions["time_palm_eeg_ridge_rotated"] = ridge_prediction(
        rotated, model, corrections["time_palm_eeg"]
    )
    return predictions


def ridge_prediction(features, model, correction):
    z = standardized(features, model)
    delta = z @ correction["ridge_delta_slopes"] + correction["ridge_delta_intercepts_mm"]
    return cohort.predict(features, model) + delta


def paired_trials(candidate, reference):
    return {
        "n_trials": len(candidate),
        **cohort.trial_comparison(candidate, reference),
    }


def summaries(residuals, offsets):
    subjects = list(residuals)
    methods = tuple(residuals[subjects[0]])
    pooled = {
        method: np.concatenate([residuals[subject][method] for subject in subjects])
        for method in methods
    }
    per_person = {
        subject: {method: cohort.metrics(residual) for method, residual in rows.items()}
        for subject, rows in residuals.items()
    }
    per_person_offsets = {
        subject: {
            str(offset): {method: cohort.metrics(rows[method][:, idx]) for method in methods}
            for idx, offset in enumerate(offsets)
        }
        for subject, rows in residuals.items()
    }
    equal_person = {
        method: cohort.balanced([per_person[subject][method] for subject in subjects])
        for method in methods
    }
    return {
        "per_person": per_person,
        "per_person_by_offset": per_person_offsets,
        "equal_person": equal_person,
        "equal_person_by_offset": {
            str(offset): {
                method: cohort.balanced([per_person_offsets[subject][str(offset)][method] for subject in subjects])
                for method in methods
            }
            for offset in offsets
        },
        "pooled": {method: cohort.metrics(values) for method, values in pooled.items()},
        "pooled_by_offset": {
            str(offset): {method: cohort.metrics(pooled[method][:, idx]) for method in methods}
            for idx, offset in enumerate(offsets)
        },
    }, pooled


def direction(delta):
    if delta < -RMSE_TOLERANCE_MM:
        return "lower"
    if delta > RMSE_TOLERANCE_MM:
        return "higher"
    return "tie"


def paired_comparison(candidate, reference, metrics, residuals, pooled):
    def delta(summary):
        return summary[candidate]["rmse_mm"] - summary[reference]["rmse_mm"]

    per_person = metrics["per_person"]
    leave_one_out = {
        subject: delta({
            method: cohort.balanced([per_person[other][method] for other in per_person if other != subject])
            for method in (candidate, reference)
        })
        for subject in per_person
    }
    differences = {subject: delta(values) for subject, values in per_person.items()}
    cohort_difference = delta(metrics["equal_person"])
    return {
        "candidate": candidate,
        "reference": reference,
        "equal_person_candidate_minus_reference_rmse_mm": cohort_difference,
        "equal_person_candidate_direction": direction(cohort_difference),
        "pooled_candidate_minus_reference_rmse_mm": delta(metrics["pooled"]),
        "per_person_candidate_minus_reference_rmse_mm": differences,
        "per_person_candidate_direction": {subject: direction(value) for subject, value in differences.items()},
        "leave_one_person_out_candidate_minus_reference_rmse_mm": leave_one_out,
        "leave_one_person_out_range_mm": [min(leave_one_out.values()), max(leave_one_out.values())],
        "per_person_paired_trials": {
            subject: paired_trials(rows[candidate], rows[reference]) for subject, rows in residuals.items()
        },
        "pooled_paired_trials": paired_trials(pooled[candidate], pooled[reference]),
    }


def evaluate(design, protocol, base, source_sha, state_sha, bindings, state, recordings):
    residuals = {}
    custody = {}
    for subject, rec in recordings.items():
        calibrated = state["participants"][subject]
        pred = predict_all(rec.features, design["baseline"]["methods"], base["models"], calibrated["corrections"])
        residuals[subject] = {name: value - rec.target for name, value in pred.items()}
        custody[subject] = {
            "calibration": calibrated["calibration"],
            "evaluation": recording_summary(rec, bindings[subject, "EVALUATION"]),
        }
    metrics, pooled = summaries(residuals, protocol["anchor"]["score_offsets_ms"])
    return {
        "kind": "R2_same_person_held_out_accuracy",
        **provenance(design, source_sha),
        "calibration_state_sha256": state_sha,
        "prediction_error_sign": "prediction_minus_observed",
        "trial_support": custody,
        "counts": {
            role: {
                key: sum(person[role][key] for person in custody.values())
                for key in ("released_trials", "eligible_trials", "scored_rows")
            }
            for role in ("calibration", "evaluation")
        },
        "metrics": metrics,
        "comparisons": {
            name: paired_comparison(candidate, reference, metrics, residuals, pooled)
            for name, (candidate, reference) in design["comparisons"].items()
        },
        "scope": "Offline archival generalization across these three distinct same-person recordings only.",
    }


def run(options):
    design, protocol, base = study_files()
    source = load_json(SOURCE_PATH, SOURCE_SHA)
    bindings = input_bindings(source, design["dataset"])
    if options.output.exists():
        raise cohort.GateError(f"Refusing to replace existing output {options.output.name}")
    if options.command == "calibrate":
        data = read_role(options.input, design["dataset"], bindings, protocol, "CALIBRATION")
        result = calibrate(design, base, SOURCE_SHA, bindings, data)
    else:
        state = verified_state(options.state, options.state_sha256, design, SOURCE_SHA, bindings)
        data = read_role(options.input, design["dataset"], bindings, protocol, "EVALUATION")
        result = evaluate(
            design, protocol, base, SOURCE_SHA, options.state_sha256, bindings, state, data
        )
    cohort.emit(options.output, result)
    print(f"{options.output}  sha256={cohort.sha(options.output)}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("calibrate", "Fit corrections using only the three R1 recordings"),
        ("evaluate", "Score saved corrections using only the three R2 recordings"),
    ):
        command_parser = commands.add_parser(command, help=help_text)
        command_parser.add_argument("--input", required=True, type=Path, help="Directory of pinned MAT files")
        command_parser.add_argument("--output", required=True, type=Path, help="New output JSON file")
        if command == "evaluate":
            command_parser.add_argument("--state", required=True, type=Path, help="Saved R1 coefficient state")
            command_parser.add_argument("--state-sha256", required=True, help="SHA-256 logged at calibration")
    options = parser.parse_args(argv)
    try:
        with threadpool_limits(limits=1):
            run(options)
    except (OSError, ValueError, KeyError, TypeError, np.linalg.LinAlgError) as error:
        print(f"Cross-run study stopped: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
