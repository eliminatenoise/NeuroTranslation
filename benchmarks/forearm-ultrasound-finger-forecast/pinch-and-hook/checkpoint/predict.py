"""Forecast four finger angles eight frames ahead with frozen pinch-and-hook models."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

if __name__ == "__main__":
    # Configure CPU math libraries before NumPy or Torch loads them.
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[variable] = "1"

import numpy as np
from safetensors.torch import load_file
import torch
from torch import nn
from torch.nn import functional as F


ROOT = Path(__file__).resolve().parent
FRAMES, CHANNELS, WIDTH = 101, 20, 24
# Preserve the matrix shapes used by the original CPU issuer's floating-point kernels.
ISSUE_BATCH = 512
ARMS = {"angle": slice(0, 4), "ultrasound": slice(4, 20), "joint": slice(0, 20)}
SEEDS = (20261126, 20261127)


class FingerForecast(nn.Module):
    """Native checkpoint layout, with the same summary reused for three GRU updates."""

    def __init__(self):
        super().__init__()
        self.conv = nn.Conv1d(CHANNELS, WIDTH, 3)
        self.recurrent = nn.GRU(WIDTH, WIDTH, batch_first=True)
        self.shared_step = nn.GRUCell(WIDTH, WIDTH)
        self.out = nn.Linear(WIDTH, 4)

    def forward(self, inputs):
        padded = F.pad(inputs.transpose(1, 2), (2, 0))
        encoded = F.silu(self.conv(padded)).transpose(1, 2)
        steps, _ = self.recurrent(encoded)
        summary = steps[:, -1]
        state = summary
        for _ in range(3):
            state = self.shared_step(summary, state)
        return self.out(state)


def read_history(record):
    if not isinstance(record, dict) or set(record) != {"history"}:
        raise ValueError("Supply one JSON object with a history field.")
    rows = record["history"]
    if not isinstance(rows, list) or len(rows) != FRAMES:
        raise ValueError("Supply 101 consecutive history rows, earliest first.")
    if not isinstance(rows[0], list) or len(rows[0]) not in (4, CHANNELS):
        raise ValueError("Each row needs four angles or four angles followed by 16 logged ultrasound tiles.")
    columns = len(rows[0])
    for row in rows:
        if not isinstance(row, list) or len(row) != columns:
            raise ValueError("Every history row must have the same width.")
        if any(type(v) not in (int, float) for v in row):
            raise ValueError("Every history value must be a finite JSON number.")
    values = np.asarray(rows, dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("Every history value must be finite.")
    return values


def check_file(name, manifest):
    path = ROOT / name
    if sha256(path.read_bytes()).hexdigest() != manifest["sha256"][name]:
        raise ValueError(f"Checkpoint file failed its SHA-256 check: {name}")
    return path


@torch.inference_mode()
def forecast(record):
    """Return one absolute angle per finger for each available method."""
    history = read_history(record)
    manifest = json.loads((ROOT / "MODEL.json").read_text(encoding="utf-8"))
    with np.load(check_file("CALIBRATION.npz", manifest), allow_pickle=False) as data:
        cal = {key: data[key] for key in data.files}
    with np.errstate(over="raise", invalid="raise"):
        latest = history[-1, :4]
        recent = history[None, -5:, :4]
        offsets = np.arange(-2., 3.)
        slope = np.einsum("t,ntf->nf", offsets, recent) / (offsets @ offsets)
        trend_change = recent.mean(axis=1) + 10 * slope - latest
        estimates = {"past_angle_trend": latest + trend_change[0]}
        centered = history.copy()
        centered[:, 4:] -= history[0, 4:]
        observed_arms = ("angle",) if history.shape[1] == 4 else ARMS
        for arm in observed_arms:
            columns = ARMS[arm]
            batch = np.zeros((ISSUE_BATCH, FRAMES, CHANNELS), dtype=np.float32)
            batch[0, :, columns] = (centered[:, columns] - cal["mean"][columns]) / cal["scale"][columns]
            flat = batch[..., columns].reshape(ISSUE_BATCH, -1)
            ridge = cal[arm][0] + flat @ cal[arm][1:]
            estimates[arm + "_ridge"] = latest + ridge[0]
            inputs = torch.from_numpy(batch)
            network = FingerForecast().float().eval()
            changes = []
            for seed in SEEDS:
                file = check_file(f"seed-{seed}/{arm}.safetensors", manifest)
                network.load_state_dict(load_file(file, device="cpu"), strict=True)
                scaled = network(inputs)[0].numpy() * cal["target_scale"]
                changes.append(scaled)
            estimates[arm + "_recurrent"] = latest + .5 * (changes[0] + changes[1])
    if not all(np.isfinite(a).all() for a in estimates.values()):
        raise ValueError("The forecast exceeds the model's numerical range.")
    return {name: angles.tolist() for name, angles in estimates.items()}


def invented_example():
    t = np.arange(FRAMES)[:, None]
    angles = 28. + 14. * np.sin(t * np.array([.13, .09, .11, .16]))
    tiles = 4. + .2 * np.cos(t * (.08 + np.arange(16) / 150.))
    return {"history": np.column_stack((angles, tiles)).tolist()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("input", nargs="?", help="JSON input file, or - for standard input")
    source.add_argument("--example", action="store_true", help="forecast an invented angle and ultrasound history")
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    try:
        if args.example:
            record = invented_example()
        elif args.input == "-":
            record = json.load(sys.stdin)
        else:
            record = json.loads(Path(args.input).read_text(encoding="utf-8"))
        print(json.dumps(forecast(record), allow_nan=False))
    except (OSError, ValueError, OverflowError, FloatingPointError) as exc:
        parser.exit(2, f"Forecast error: {exc}\n")


if __name__ == "__main__":
    main()
