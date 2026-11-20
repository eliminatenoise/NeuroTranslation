"""Replay a saved Poisson model using only the Python standard library.

Input JSON is an array of examples, each containing five completed 20 ms bins,
oldest first. A bin holds mean force, mean actuator position, finite backward
force and position rates, and the completed-bin spike count in that order.
"""

import argparse
import json
import math
from pathlib import Path


def predict_count(tokens, params):
    if len(tokens) != 5 or any(len(row) != 5 for row in tokens):
        raise ValueError("Expected five bins with five channels each")
    if any(not math.isfinite(v) for row in tokens for v in row):
        raise ValueError("Nonfinite input")
    if any(row[4] < 0 or int(row[4]) != row[4] for row in tokens):
        raise ValueError("Completed spike counts must be nonnegative integers")
    if params.get("zero_boundary"):
        return 0.0
    eta = params["intercept"]
    for row, coefficients in zip(tokens, params["coefficients"], strict=True):
        for local, channel in enumerate(params["fields"]):
            standardized = (row[channel] - params["mean"][local]) / params["scale"][
                local
            ]
            eta += coefficients[local] * min(10.0, max(-10.0, standardized))
    return math.exp(eta)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coefficients", type=Path)
    parser.add_argument("windows", type=Path)
    parser.add_argument(
        "--held", choices=("0", "1", "4", "aff004", "aff015", "aff017"), required=True
    )
    parser.add_argument(
        "--mode",
        choices=("history", "mechanics", "force", "position", "all"),
        default="all",
    )
    args = parser.parse_args()
    params = json.loads(args.coefficients.read_text())["folds"][args.held]["modes"][
        args.mode
    ]
    windows = json.loads(args.windows.read_text())
    print(
        json.dumps(
            [predict_count(window, params) for window in windows], allow_nan=False
        )
    )
