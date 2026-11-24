"""Use measured walking histories to forecast new loads and heel movement."""

import argparse
import json
from pathlib import Path

from paired_plates import DELAYS_MS, attention_readouts, numeric, require, shape, sigmoid, vector


HERE = Path(__file__).resolve().parent
ARMS = {
    "force_motion": (True, True, False),
    "force_motion_cold": (True, True, False),
    "force": (True, False, False),
    "motion": (False, True, False),
    "force_motion_muscle": (True, True, True),
    "force_motion_earlier_muscle": (True, True, True),
}
SIDES = ["left", "right"]
FIELDS = ("vertical_force_n", "plate_state_by_bin", "heel_xyz_mm", "relative_muscle_activity")


def numeric_samples(history, key, count, width):
    series = history[key]
    shape(series, 2, count, key)
    for side in series:
        if width is not None:
            shape(side, count, width, key)
            side = [value for sample in side for value in sample]
        require(all(numeric(value) for value in side), f"{key} needs complete finite measurements.")
    return series


def read_windows(history, arm):
    require(history["side_order"] == SIDES, "Give histories in left, right order.")
    times = history["bin_end_ms"]
    require(isinstance(times, list) and all(type(value) is int for value in times), "Use integer bin end times in milliseconds.")
    count = len(times)
    earlier = 50 if arm == "force_motion_earlier_muscle" else 0
    require(count >= 35 + earlier and all(k - j == 20 for j, k in zip(times, times[1:])),
            f"Use at least {35 + earlier} bins, with every bin end 20 ms after the previous one.")
    use_force, use_heel, use_muscle = ARMS[arm]
    force = numeric_samples(history, FIELDS[0], count, None) if use_force else None
    states = history[FIELDS[1]] if use_force else None
    if use_force:
        shape(states, 2, count, FIELDS[1])
        require(all(type(value) is int and 0 <= value <= 3 for side in states for value in side),
                "Use a whole number from 0 to 3 for each plate state.")
    heel = numeric_samples(history, FIELDS[2], count, 3) if use_heel else None
    muscle = numeric_samples(history, FIELDS[3], count, 2) if use_muscle else None
    if use_muscle:
        require(all(value >= 0. for side in muscle for row in side for value in row), "Use nonnegative relative muscle activity.")
    histories = []
    for side in range(2):
        windows = []
        for delay in DELAYS_MS:
            end = count - 1 - delay // 20
            window = [0.] * 73
            if use_force:
                window[:23] = vector(force[side][end - 9:end + 1], states[side][end])
            if use_heel:
                tail = heel[side][end - 9:end + 1]
                window[23:53] = [value - tail[-1][axis] for axis, axis_values in enumerate(zip(*tail))
                                 for value in axis_values]
            if use_muscle:
                last = end - earlier
                window[53:] = [value for electrode in zip(*muscle[side][last - 9:last + 1]) for value in electrode]
            windows.append(window)
        histories.append(windows)
    return times[-1], histories


def forecast(checkpoint, history, arm):
    require(arm in ARMS and checkpoint["format"] == "aligned_walk_v1" and checkpoint["lags_ms"] == DELAYS_MS,
            "The checkpoint or walking option uses a different layout.")
    issue_ms, windows = read_windows(history, arm)
    weights = checkpoint["models"][arm]
    enabled = [active for active, count in zip(ARMS[arm], (23, 30, 20)) for _ in range(count)]
    # In training, unused signals were set to zero after scaling. Zero their weight
    # columns here so the shared attention can use the original input scales.
    weights = weights | {key: [[value if active else 0. for active, value in zip(enabled, row)] for row in weights[key]]
                         for key in ("own.weight", "other.weight")}
    outputs = attention_readouts(windows, checkpoint["normalizers"], weights)
    center, scale = checkpoint["target_center"], checkpoint["target_scale"]
    estimates = []
    for side, raw in zip(SIDES, outputs):
        impulse, x, y, z = [value * spread + mean for value, mean, spread in zip(raw[1:], center, scale)]
        estimates.append({"side": side, "new_load_probability": sigmoid(raw[0]), "signed_impulse_newton_seconds": impulse,
                          "heel_displacement_xyz_millimetres": [x, y, z]})
    return {"arm": arm, "issue_time_ms": issue_ms, "forecast_horizon_ms": 100, "predictions": estimates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Read a prepared walking history JSON file.")
    parser.add_argument("--arm", choices=tuple(ARMS), default="force_motion")
    args = parser.parse_args()
    try:
        checkpoint = json.loads((HERE / "walking-heads.json").read_text(encoding="utf-8"))
        history = json.loads((args.input or HERE / "example-walking.json").read_text(encoding="utf-8"))
        result = forecast(checkpoint, history, args.arm)
        result["input_kind"] = "user supplied" if args.input else "invented example"
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, IndexError, KeyError, OverflowError) as error:
        parser.exit(2, f"Unable to forecast. {error}\n")


if __name__ == "__main__":
    main()
