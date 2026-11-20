"""Use the untouched CPU predict.py to build an oracle from invented inputs only."""
import argparse
import copy
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "public"))
from export_weights import verified_inputs

MODES = ["motion", "emg", "full"]
OFFSETS = [384, 512, 640, 768, 896, 1024]


def windows(offset):
    def constant(anchor, angles, emg, eeg):
        return {"anchor_deg": anchor, "mean_angles_deg": [angles.copy() for _ in range(16)],
                "emg_rms_uv": [emg.copy() for _ in range(16)],
                "eeg_mean_uv": [eeg.copy() for _ in range(16)],
                "target_offset_after_cue_ticks": offset}
    yield "zero", constant([0, 0], [0, 0], [0] * 4, [0] * 8)
    yield "flat", constant([10, -5], [10, -5], [20, 45, 15, 14], [-1, 2, 1, 0, 2, 3, 2, -4])
    wave = constant([-6.3, 3.1], [0, 0], [0] * 4, [0] * 8)
    for t in range(16):
        wave["mean_angles_deg"][t] = [8.1 * math.sin(t / 4) - 12, 4.4 * math.cos(t / 5) + 1]
        wave["emg_rms_uv"][t] = [3 + 9 * (j + 1) * (1 + math.sin((t - j) / 7)) for j in range(4)]
        wave["eeg_mean_uv"][t] = [19 * math.sin(t / 5 + .4 * j) + 2 * (j - 3) for j in range(8)]
    yield "wave", wave
    # Each perturbation changes only one feature during one bin, at different times.
    for name, field, bin_id, channel, delta in [
        ("motion-pulse", "mean_angles_deg", 15, 0, 20),
        ("emg-pulse", "emg_rms_uv", 8, 2, 100),
        ("eeg-pulse", "eeg_mean_uv", 0, 6, -75),
    ]:
        changed = copy.deepcopy(wave)
        changed[field][bin_id][channel] += delta
        yield name, changed


def main(study, destination):
    verified_inputs(study)
    sys.path.insert(0, str(study.resolve()))
    from broader_learner import configure_cpu_runtime
    from predict import predict
    configure_cpu_runtime(1, 1, True)
    cases = []
    for offset in OFFSETS:
        for kind, payload in windows(offset):
            cases.append({"name": f"{kind}-{offset}", "payload": payload,
                          "expected": {m: predict(payload, m) for m in MODES}})
    destination.write_text(json.dumps(cases, separators=(",", ":"), allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    main(args.study, args.destination)
