"""Print four right-arm accelerometer forecasts from a 16-sample history."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from scoring import HORIZONS, direct

HERE = Path(__file__).resolve().parent
CHECKPOINT = "3dfa030f11c171b14ea59580b8cc7442326e95acc7089877f30d4b50889706f7"


def parse_history(value):
    if value.get("body_part") != "right_arm":
        raise ValueError("Select history from the right-arm sensor")
    times = value.get("timestamps_ms")
    if not isinstance(times, list) or len(times) != 16 or any(type(t) is not int for t in times):
        raise ValueError("Supply 16 integer sample times in milliseconds")
    if any(b - a != 40 for a, b in zip(times, times[1:])):
        raise ValueError("Expected consecutive samples spaced 40 milliseconds apart")
    samples = value.get("samples")
    if not isinstance(samples, list) or len(samples) != 16 or any(
            not isinstance(row, list) or len(row) != 3 or any(type(n) not in (int, float) for n in row)
            for row in samples):
        raise ValueError("Supply a list of 16 rows of three numeric sensor values each")
    data = np.array(samples, dtype=np.float64)
    if not np.isfinite(data).all():
        raise ValueError("Every XYZ reading must be finite")
    return times[-1], data[None, ...]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history", type=Path, nargs="?", default=HERE / "example.json")
    args = parser.parse_args()
    checkpoint = HERE / "ridge.npz"
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != CHECKPOINT:
        parser.error("The checkpoint differs from the tested four-horizon model")
    try:
        last, x = parse_history(json.loads(args.history.read_text()))
    except (ValueError, TypeError, AttributeError, OSError) as exc:
        parser.error(str(exc))
    with np.load(checkpoint, allow_pickle=False) as fitted:
        forecasts = direct(x, {k: fitted[k] for k in fitted.files})[0]
    print(json.dumps({"body_part": "right_arm", "units": "sensor-native XYZ acceleration",
                      "last_observation_ms": last, "forecasts": [
                          {"lead_ms": 40*h, "target_ms": last + 40*h, "xyz": xyz.tolist()}
                          for h, xyz in zip(HORIZONS, forecasts)]}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
