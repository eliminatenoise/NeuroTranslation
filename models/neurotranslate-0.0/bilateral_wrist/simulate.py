"""Generate the public wrist examples and fit all demo weights on simulated events."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

import demo_math as math
from export_case import SIDES, MODALITIES, TREATMENTS, make_package, pack_case


def generate(count, seed):
    rng = np.random.default_rng(seed)
    camera_t = np.arange(-14, 16, dtype=np.float64) / 30
    signal_t = np.arange(-250, 0, dtype=np.float64) / 500 + 1 / 60
    pose, volts = [], []
    for _ in range(count):
        phase = rng.uniform(-np.pi, np.pi, 3)
        freq = rng.uniform(.10, .49, 3)
        def oscillation(t):
            return np.sin(2 * np.pi * t[:, None] * freq + phase)
        joints = []
        latent = oscillation(camera_t)
        for side in (0, 1):
            sign = 1 - 2 * side
            x = 16 * sign + .9 * latent[:, 2]
            y = -4 + 1.1 * latent[:, 0]
            shoulder = np.stack((x, y), axis=1)
            upper = .85 + (.48 if side == 0 else .32) * latent[:, side]
            lower = -.35 + .78 * latent[:, 1 - side] + .18 * latent[:, 2]
            elbow = shoulder + 27 * np.stack((sign * np.cos(upper), np.sin(upper)), axis=1)
            wrist = elbow + 24 * np.stack((sign * np.cos(lower), np.sin(lower)), axis=1)
            joints.extend([wrist, elbow, shoulder])
        pose.append(np.stack(joints, axis=1) + rng.normal(0, .08, (30, 6, 2)))
        trace = oscillation(signal_t)
        channels = []
        for ch in range(8):
            envelope = 3 + 1.2 * trace[:, ch % 3]
            wave = np.sin(2 * np.pi * (8 + 3 * ch) * signal_t + phase[ch % 3])
            channels.append(4.5 * trace[:, (ch + 1) % 3] + envelope * wave + rng.normal(0, .18, 250))
        volts.append(np.stack(channels, axis=1))
    p = np.stack(pose)
    data = {"ecog_uv": np.array(volts), "prior_pose_px": p[:, :15]}
    future = p[:, [22, 29]][:, :, [0, 3]]
    return data, future


def train(data, future):
    w = {}
    for s, side in enumerate(SIDES):
        allowed = np.ones(len(future), bool)
        x, y, v, mask, _, stats = math.head_data(data, future, allowed, s)
        prefix = "main__" + side + "__"
        w.update({prefix + key: val for key, val in stats.items()})
        for modality in MODALITIES:
            token = x.copy()
            if modality == "pose":
                token[:, :, 10:] = 0
            for treatment in TREATMENTS:
                target = math.targets(y, v, mask, stats, treatment)
                fitted, _, _ = math.fit_net(token, target, mask, 17, treatment, "cpu")
                stem = prefix + f"transformer_{treatment}_{modality}_s17__"
                w.update({stem + key: val for key, val in fitted.items()})
    return w


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_json", type=Path, help="A new wrist-forecast-v1 JSON file")
    parser.add_argument("--threads", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    data, future = generate(64, 19037)
    weights = train(data, future)
    examples, _ = generate(4, 33117)
    cases = [pack_case(e, p) for e, p in zip(examples["ecog_uv"], examples["prior_pose_px"])]
    result = make_package(weights, cases)
    text = json.dumps(result, separators=(",", ":"), allow_nan=False)
    with args.output_json.open("x", encoding="utf-8") as output:
        output.write(text + "\n")


if __name__ == "__main__":
    main()
