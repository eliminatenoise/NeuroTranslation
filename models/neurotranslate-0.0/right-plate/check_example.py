"""Check all six forecasts and the public input format with the invented example."""
import copy
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from predict import predict_record
from right_plate import COMBINED


def rejects(record):
    try:
        predict_record(record)
    except ValueError:
        return
    raise AssertionError("Accepted an invalid input")


def main():
    example = json.loads((HERE / "example.json").read_text())
    expected = json.loads((HERE / "example-results.json").read_text())
    for mode, reference in expected.items():
        record = copy.deepcopy(example)
        record["mode"] = mode
        if mode not in COMBINED:
            del record["emg_uV"], record["emg_valid"]
        actual = predict_record(record)
        assert np.isclose(actual["right_vertical_plate_force_N"], reference["right_vertical_plate_force_N"],
                          rtol=0, atol=1e-8)
        assert {k: v for k, v in actual.items() if k != "right_vertical_plate_force_N"} == {
            k: v for k, v in reference.items() if k != "right_vertical_plate_force_N"
        }

    for field, invalid in (("offset_frames", 25), ("offset_frames", True),
                           ("mode", "untrained"), ("emg_valid", [[1] * 7] * 4)):
        rejects({**example, field: invalid})
    for field, value in (("markers_m", True), ("markers_m", float("nan")),
                         ("emg_uV", -1), ("emg_valid", 2)):
        record = copy.deepcopy(example)
        record[field][0][0] = value
        rejects(record)
    invalid = copy.deepcopy(example)
    invalid["emg_valid"][0][0] = 0
    invalid["emg_uV"][0][0] = 1
    rejects(invalid)
    invalid["emg_uV"][0][0] = 0
    assert np.isfinite(predict_record(invalid)["right_vertical_plate_force_N"])
    rejects({**example, "mode": "marker_shared"})
    rejects({**example, "future_force": 100})
    print("All six example forecasts and input checks passed.")


if __name__ == "__main__":
    main()
