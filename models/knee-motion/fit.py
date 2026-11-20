"""Fit the prespecified models on training participants only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn

from extract import TRAIN
from predict import CHANNELS, LAGS
from study_data import load_set

SEED = 81037


def ridge(trials, knees_only):
    rows, outputs = [], []
    for trial in trials.values():
        x = trial.x[:, :, 2:4] if knees_only else trial.x
        rows.append(x.reshape(len(x), -1))
        outputs.append(trial.y - trial.x[:, -1, 2:4])
    mean = np.mean([x.mean(axis=0) for x in rows], axis=0)
    scale = np.sqrt(np.mean([np.mean((x - mean) ** 2, axis=0) for x in rows], axis=0)).clip(.000001)
    offset = np.mean([y.mean(axis=0) for y in outputs], axis=0)
    size = len(mean)
    gram, cross = np.zeros((size, size)), np.zeros((size, 2))
    for x, y in zip(rows, outputs):
        z = (x - mean) / scale
        gram += (z.T @ z) / len(z) / len(rows)
        cross += (z.T @ (y - offset)) / len(z) / len(rows)
    beta = np.linalg.solve(gram + .001 * np.eye(size), cross)
    return {k: v.tolist() for k, v in dict(mean=mean, scale=scale, coef=beta, intercept=offset).items()}


class GaitTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.project = nn.Linear(6, 24)
        self.position = nn.Parameter(torch.empty(5, 24))
        nn.init.normal_(self.position, std=.02)
        self.attention_norm = nn.LayerNorm(24)
        self.qkv = nn.Linear(24, 72)
        self.attention_out = nn.Linear(24, 24)
        self.ff_norm = nn.LayerNorm(24)
        self.ff_in = nn.Linear(24, 48)
        self.ff_out = nn.Linear(48, 24)
        self.last_norm = nn.LayerNorm(24)
        self.readout = nn.Linear(24, 2)
        nn.init.zeros_(self.readout.weight)
        nn.init.zeros_(self.readout.bias)

    def forward(self, history):
        z = self.project(history) + self.position
        qkv = self.qkv(self.attention_norm(z)).reshape(len(z), 5, 3, 4, 6)
        q, k, v = qkv.permute(2, 0, 3, 1, 4).unbind(0)
        attention = torch.softmax((q @ k.transpose(-1, -2)) / 6 ** .5, dim=-1)
        mixed = (attention @ v).transpose(1, 2).reshape(len(z), 5, 24)
        z = z + self.attention_out(mixed)
        z = z + self.ff_out(torch.relu(self.ff_in(self.ff_norm(z))))
        return self.readout(self.last_norm(z[:, -1]))


def transformer(trials, steps):
    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)
    inputs = [a.x for a in trials.values()]
    mean = np.mean([x.mean(axis=(0, 1)) for x in inputs], axis=0)
    scale = np.sqrt(np.mean([((x - mean) ** 2).mean(axis=(0, 1)) for x in inputs], axis=0)).clip(.000001)
    x = torch.from_numpy(np.concatenate([(inp - mean) / scale for inp in inputs]).astype("f4"))
    y = torch.from_numpy(np.concatenate([(a.y - a.x[:, -1, 2:4]) / 20 for a in trials.values()]).astype("f4"))
    lengths = np.array([len(t) for t in inputs])
    starts = np.r_[0, np.cumsum(lengths)[:-1]]
    model = GaitTransformer()
    optimizer = torch.optim.AdamW(model.parameters(), lr=.002, weight_decay=.001, foreach=False)
    losses = []
    for _ in range(steps):
        persons = rng.integers(len(lengths), size=128)
        ix = torch.from_numpy(starts[persons] + rng.integers(lengths[persons]))
        optimizer.zero_grad(set_to_none=True)
        loss = torch.nn.functional.mse_loss(model(x[ix]), y[ix])
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    state = {k: tensor.detach().tolist() for k, tensor in model.state_dict().items()}
    return dict(mean=mean.tolist(), scale=scale.tolist(), state=state), losses, model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--benchmark", action="store_true", help="20-update training-only timing; output is a probe")
    args = parser.parse_args()
    if args.output.exists() or args.receipt.exists():
        parser.error("Use fresh output and receipt paths")
    started = time.perf_counter()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    trials, dropped = load_set(args.cache, TRAIN if not args.benchmark else (1,))
    weights = dict(format="gait-knees-1", features=CHANNELS, lags_frames=LAGS, future_frames=15)
    weights["knee_ridge"] = ridge(trials, True)
    weights["all_ridge"] = ridge(trials, False)
    transform_start = time.perf_counter()
    weights["transformer"], losses, model = transformer(trials, 20 if args.benchmark else 700)
    # Compare actual training graph and portable NumPy graph before freezing the output.
    from predict import predict
    probe = next(iter(trials.values())).x[:64]
    x = (probe - weights["transformer"]["mean"]) / weights["transformer"]["scale"]
    reference = probe[:, -1, 2:4] + 20 * model(torch.from_numpy(x.astype("f4"))).detach().numpy()
    diff = float(np.max(np.abs(reference - predict(probe, weights))))
    if diff > .001 or not np.isfinite(losses).all():
        raise ValueError(f"Training/export parity or finite-loss check failed: {diff}")
    args.output.write_text(json.dumps(weights, allow_nan=False, separators=(",", ":")) + "\n")
    report = dict(training_trials=[a.info for a in trials.values()], dropped=dropped, updates=len(losses),
                  seed=SEED, optimizer="AdamW", total_windows=sum(len(a.x) for a in trials.values()),
                  first_loss=losses[0], final_loss=losses[-1], loss_sha256=hashlib.sha256(np.array(losses, dtype="<f8").tobytes()).hexdigest(),
                  portable_max_error_degrees=diff, torch=str(torch.__version__), numpy=np.__version__,
                  threads=torch.get_num_threads(), interop=torch.get_num_interop_threads(),
                  env={k:os.getenv(k) for k in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS")},
                  affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None,
                  cpu_only=not torch.cuda.is_available(), weights_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  transformer_stage_seconds=time.perf_counter() - transform_start, whole_job_seconds=time.perf_counter() - started)
    args.receipt.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
