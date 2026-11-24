"""Recalculate the published estimates from the three original DANDI files."""

from argparse import ArgumentParser
from hashlib import file_digest
import json
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
PAIRS = (
    ("published_blend", "stay_put"), ("published_blend", "constant_velocity"),
    ("published_blend", "constant_acceleration"), ("equal_blend", "constant_velocity"),
    ("equal_blend", "published_blend"),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(filename):
    with filename.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def with_distance(delta):
    return np.concatenate((delta, np.linalg.norm(delta, axis=-1, keepdims=True)), axis=-1)


def positions(filename, source, trial, issue, target, settings):
    require(filename.stat().st_size == source["bytes"] and digest(filename) == source["sha256"],
            f"{filename.name} differs from the published DANDI file.")
    offsets = np.asarray(settings["history_offsets_ms"])
    history = issue[None] - offsets[:, None]
    with h5py.File(filename, "r") as archive:
        hand = archive[settings["path"]]
        data = hand["data"]
        clock = hand["timestamps"][:]
        conversion = float(data.attrs["conversion"])
        require(conversion == .001 and data.attrs["unit"] in (b"meters", "meters") and
                hand["reference_frame"][()] in (b"screen center", "screen center") and
                data.shape == (len(clock), 2), "Unexpected hand scale or coordinates.")
        require(np.isfinite(clock).all() and np.all(np.diff(clock) > 0) and
                history.min() >= 0 and target.max() < len(clock), "Unexpected hand timestamps.")
        tolerance = settings["timestamp_tolerance_s"]
        require(np.all(np.abs(clock[issue][None] - clock[history] - offsets[:, None] / 1000) <= tolerance) and
                np.all(np.abs(clock[target] - clock[issue] - settings["horizon_ms"] / 1000) <= tolerance),
                "The history and target positions do not match the forecast clock.")
        trials = archive["intervals/trials"]
        ids = trials["id"][:]
        order = np.argsort(ids)
        offsets_in_trials = np.searchsorted(ids[order], trial)
        require(np.all(offsets_in_trials < len(ids)), "Missing forecast trial IDs.")
        trial_rows = order[offsets_in_trials]
        require(np.array_equal(ids[trial_rows], trial) and
                np.all(trials["start_time"][:][trial_rows] <= clock[history[0]]) and
                np.all(trials["stop_time"][:][trial_rows] > clock[target]), "Forecasts leave their recorded trials.")
        indices = np.concatenate((history, target[None]), axis=0)
        selected, reverse = np.unique(indices.ravel(), return_inverse=True)
        values = np.concatenate([data[selected[at:at + 512]] for at in range(0, len(selected), 512)])
        require(np.isfinite(values).all(), "The archive supplies a missing hand position.")
    return values.astype(np.float64)[reverse].reshape((*indices.shape, 2)) * conversion * 1000


def predictions(original, neural, historical, ratio):
    first, second, current = historical
    recent = current - second
    earlier = second - first
    velocity = ratio * recent
    acceleration = velocity + .5 * ratio * (ratio + 1) * (recent - earlier)
    return {
        "original": original,
        "published_blend": neural,
        "stay_put": np.zeros((1, len(current), 3)),
        "constant_velocity": with_distance(velocity)[None],
        "constant_acceleration": with_distance(acceleration)[None],
        "equal_blend": with_distance((neural[:, :, :2] + velocity[None]) * .5),
    }, np.linalg.norm(recent, axis=1)


def score(forecasts, measured, trial, settings):
    trial_ids, which, counts = np.unique(trial, return_inverse=True, return_counts=True)
    support = {"rows": len(trial), "trials": len(trial_ids)}
    if not len(trial_ids):
        return support
    per_trial = {}
    for method, forecast in forecasts.items():
        position = np.linalg.norm(forecast[:, :, :2] - measured[None, :, :2], axis=2)
        distance = np.abs(forecast[:, :, 2] - measured[None, :, 2])
        per_trial[method] = np.column_stack([
            np.bincount(which, weights=error.mean(axis=0)) / counts for error in (position, distance)
        ])
    rng = np.random.default_rng(settings["bootstrap_seed"])
    gains = np.stack([per_trial[reference] - per_trial[method] for method, reference in PAIRS])
    n_draws = settings["bootstrap_draws"]
    sample = np.empty((len(PAIRS), n_draws, 2))
    for start in range(0, n_draws, 100):
        size = min(n_draws - start, 100)
        draws = rng.integers(len(trial_ids), size=(size, len(trial_ids)))
        sample[:, start:start + size] = gains[:, draws].mean(axis=2)
    return {
        **support,
        "error_mm": {method: values.mean(axis=0).tolist() for method, values in per_trial.items()},
        "paired_gain_mm": {
            method + "_over_" + reference: {
                "mean": gain.mean(axis=0).tolist(), "paired_95": np.quantile(draw, [.025, .975], axis=0).T.tolist(),
            }
            for (method, reference), gain, draw in zip(PAIRS, gains, sample, strict=True)
        },
    }


def check_score(got, expected):
    require(got.keys() == expected.keys(), "Result fields differ from the published data.")
    require(got["rows"] == expected["rows"] and got["trials"] == expected["trials"],
            "The replay found different trial or forecast counts.")
    deltas = [0.]
    for method, errors in got.get("error_mm", {}).items():
        deltas.extend(abs(np.array(errors) - expected["error_mm"][method]))
    for key, comparison in got.get("paired_gain_mm", {}).items():
        for field, values in comparison.items():
            deltas.extend(abs(np.array(values) - expected["paired_gain_mm"][key][field]).ravel())
    return float(max(deltas))


def replay(report, bundle, day, folder):
    prefix = day.replace("-", "") + "_"
    trial, issue, target = (bundle[prefix + key] for key in ("trial", "issue_index", "target_index"))
    original, neural = (bundle[prefix + key] for key in ("original", "published_blend"))
    require(original.shape == neural.shape == (len(report["frozen_seeds"]), len(trial), 3) and
            np.isfinite(original).all() and np.isfinite(neural).all(), "Invalid frozen neural forecasts.")
    settings = report["measurement"]
    source = report["dataset"]["sources"][day]
    first, second, current, finish = positions(folder / source["filename"], source, trial, issue, target, settings)
    measured = with_distance(finish - current)
    forecast, recent = predictions(original, neural, (first, second, current),
                                   settings["horizon_ms"] / settings["history_offsets_ms"][1])
    scoring = report["scoring"]
    overall = score(forecast, measured, trial, scoring)
    previous = recent < scoring["past_movement_threshold_mm"]
    strata = {"past_under_1_mm": previous, "past_at_least_1_mm": ~previous}
    limits = [*scoring["future_distance_bands_mm"], np.inf]
    for low, high in zip(limits[:-1], limits[1:], strict=True):
        strata[f"future_{low}_to_{high}_mm"] = (measured[:, 2] >= low) & (measured[:, 2] < high)
    published = report["recordings"][day]
    differences = [check_score(overall, published["overall"])]
    for band, use in strata.items():
        metrics = score({key: row[:, use] for key, row in forecast.items()}, measured[use], trial[use], scoring)
        differences.append(check_score(metrics, published["strata"][band]))
    difference = max(differences)
    require(difference < 1e-9, f"The replay differs from the published results by {difference} mm.")
    return {"rows": overall["rows"], "trials": overall["trials"],
            "mean_error_mm": overall["error_mm"], "maximum_replay_difference_mm": difference}


def main():
    report = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("recording_folder", type=Path, help="Folder containing the downloaded original NWB files")
    parser.add_argument("--day", action="append", choices=tuple(report["recordings"]),
                        help="Verify one day. Repeat to select multiple days. Default is all three.")
    arguments = parser.parse_args()
    packet = HERE / report["forecast_packet"]["filename"]
    require(digest(packet) == report["forecast_packet"]["sha256"], "The neural forecast packet checksum differs.")
    with np.load(packet, allow_pickle=False) as bundle:
        verified = {day: replay(report, bundle, day, arguments.recording_folder)
                    for day in (arguments.day or report["recordings"])}
    print(json.dumps(verified, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
