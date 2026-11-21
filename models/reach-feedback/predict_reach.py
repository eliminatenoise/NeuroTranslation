"""Forecast the arm path and later cortical counts from the same 200 ms of history."""
import argparse
import json
from pathlib import Path
import numpy as np

from motor.forecast import SEEDS, history_tokens, load_model, predict as motor_predict
from cortex.count_model import predict as count_predict

HERE = Path(__file__).resolve().parent


def forecast(pose, spikes, cue, unit_guide, family="transformer", seed=17):
    """Return batched displacements, augmented counts and direct counts in source order."""
    if family not in ("transformer", "regression") or seed not in SEEDS:
        raise ValueError("Choose a fitted family and seed 17, 41 or 73")
    raw = history_tokens(pose, spikes, cue)
    if len(raw) == 0:
        raise ValueError("Supply at least one complete reach")
    motor_id = "ridge" if family == "regression" else str(seed)
    model = load_model(HERE / "motor/weights" / f"full-{motor_id}.npz")
    motion = motor_predict(raw, model, unit_guide)
    inputs = dict(pose=pose, spikes=spikes, cue=cue)
    counts = {}
    for arm in ("direct", "full"):
        name = f"glm-{arm}" if family == "regression" else f"transformer-{arm}-{seed}"
        with np.load(HERE / "cortex/weights" / (name + ".npz"), allow_pickle=False) as head:
            if not np.array_equal(unit_guide, head["unit_guide"]):
                raise ValueError("The count head requires the fitted electrode channel and sort order")
            counts[arm] = count_predict(head, **inputs, movement=motion)
    return motion, counts["full"], counts["direct"]


def single(record, family, seed):
    values = [np.asarray(record[name])[None] for name in ("pose", "spikes", "cue")]
    motion, augmented, direct = forecast(*values, np.asarray(record["unit_guide"]), family, seed)
    return {"family": family, "seed": seed if family == "transformer" else None,
            "unit_guide": record["unit_guide"],
            "displacement_hand_xyz_m_elbow_xyz_m_handle_xy_cm": motion[0].tolist(),
            "expected_count_with_forecast": augmented[0].tolist(),
            "expected_count_direct": direct[0].tolist()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("record", type=Path, nargs="?", default=HERE / "examples/within.json",
                   help="One JSON record with pose, spikes, cue and unit_guide")
    p.add_argument("--family", choices=("transformer", "regression"), default="transformer")
    p.add_argument("--seed", type=int, choices=SEEDS, default=None, help="Transformer initialization (default 17)")
    p.add_argument("--output", type=Path, help="Write ten forecast displacements and two 10 × 23 count arrays")
    args = p.parse_args()
    if args.seed is not None and args.family != "transformer":
        p.error("The two regression fits use a fixed solution. Omit --seed.")
    record = json.loads(args.record.read_bytes())
    result = single(record, args.family, args.seed or 17)
    if args.output:
        args.output.write_text(json.dumps(result, allow_nan=False, indent=2) + "\n")
    end = np.asarray(result["displacement_hand_xyz_m_elbow_xyz_m_handle_xy_cm"])[-1]
    print("Predicted endpoint displacement, 100 ms after the last measured sample")
    print("Hand XYZ (mm)       ", np.round(end[:3] * 1000, 3))
    print("Elbow marker XYZ (mm)", np.round(end[3:6] * 1000, 3))
    print("Handle XY (cm)      ", np.round(end[6:], 3))
    print("\nExpected spikes from 100 to 200 ms after cutoff")
    print("channel sort    direct   with predicted motion")
    direct = np.sum(result["expected_count_direct"], axis=0)
    augmented = np.sum(result["expected_count_with_forecast"], axis=0)
    for (channel, code), a, b in zip(result["unit_guide"], direct, augmented, strict=True):
        print(f"{channel:7d} {code:4d} {a:9.3f} {b:22.3f}")


if __name__ == "__main__":
    main()
