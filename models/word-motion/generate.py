"""Generate a short CMU-domain movement from a supported action description."""

import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PHRASES = {
    "walk": "walk",
    "walking": "walk",
    "run": "run",
    "running": "run",
    "run/jog": "run",
    "jog": "run",
    "jogging": "run",
}


def action_for(text):
    if not isinstance(text, str):
        return None
    return PHRASES.get(text.strip().lower())


def time_features():
    t = np.linspace(0.0, 1.0, 25, dtype=np.float32)
    fs = [t]
    for cycles in range(1, 5):
        angle = t * np.float32(2 * np.pi * cycles)
        fs.extend((np.sin(angle), np.cos(angle)))
    return np.stack(fs, axis=1)


def output_packet(action, y):
    pos = y[:, :54].reshape(25, 18, 3)
    return {
        "action": action,
        "rateHz": 40,
        "positionsMm": pos.tolist(),
        "rootMm": y[:, -3:].tolist(),
    }


def predict(action, w):
    a = w["tokens"].index(action)
    token = np.asarray(w["embedding"][a], dtype=np.float32)
    x = np.concatenate([np.tile(token, (25, 1)), time_features()], axis=1)
    for layer in w["layers"]:
        x = x @ np.asarray(layer["weight"], dtype=np.float32).T + np.asarray(
            layer["bias"], dtype=np.float32
        )
        if layer["activation"] == "tanh":
            x = np.tanh(x)
    y = x * np.float32(w["scaleMm"]) + np.asarray(w["centreMm"], dtype=np.float32)
    y[:, -3:] = y[:, -3:] - y[0, -3:]
    return y


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("words")
    p.add_argument("--weights", type=Path, default=HERE / "weights.json")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    action = action_for(args.words)
    if action is None:
        p.error("Choose walk, walking, run, running, jog, jogging or run/jog.")
    w = json.loads(args.weights.read_text())
    output = json.dumps(
        output_packet(action, predict(action, w)),
        separators=(",", ":"),
        allow_nan=False,
    )
    if args.out:
        args.out.write_text(output + "\n")
    else:
        print(output)


if __name__ == "__main__":
    main()
