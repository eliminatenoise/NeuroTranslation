"""Fit a linear correction and a Transformer correction on 39 training people."""
import argparse
import json
import os
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn

from extract import TRAIN
from predict import normalize, predictions
from trials import HERE, PROTOCOL_SHA256, digest, load_trial, save, series_hash


SEED = 81327
STEPS = 1600


class KneeTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.project = nn.Linear(11, 24)
        self.position = nn.Parameter(torch.empty(9, 24))
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
        qkv = self.qkv(self.attention_norm(z)).reshape(len(z), 9, 3, 4, 6)
        q, k, v = qkv.permute(2, 0, 3, 1, 4).unbind(0)
        attention = torch.softmax((q @ k.transpose(-1, -2)) / 6 ** .5, dim=-1)
        mixed = (attention @ v).transpose(1, 2).reshape(len(z), 9, 24)
        z = z + self.attention_out(mixed)
        z = z + self.ff_out(torch.relu(self.ff_in(self.ff_norm(z))))
        return self.readout(self.last_norm(z[:, -1]))


def ridge(zs, ys):
    rows = [z.reshape(len(z), -1) for z in zs]
    center = np.mean([z.mean(axis=0) for z in rows], axis=0)
    intercept = np.mean([y.mean(axis=0) for y in ys], axis=0)
    gram, cross = np.zeros((99, 99)), np.zeros((99, 2))
    for z, y in zip(rows, ys, strict=True):
        z = z - center
        gram += (z.T @ z) / len(z) / len(rows)
        cross += (z.T @ (y - intercept)) / len(z) / len(rows)
    coef = np.linalg.solve(gram + .001 * np.eye(99), cross)
    return dict(center=center.tolist(), coef=coef.tolist(), intercept=intercept.tolist())


def train(cache, output, receipt, threads, benchmark):
    if output.exists() or receipt.exists() or output.resolve() == receipt.resolve():
        raise ValueError("Give the fit fresh, distinct output and receipt paths")
    started = time.perf_counter()
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)
    people = (1,) if benchmark else TRAIN
    trials = [load_trial(cache, p) for p in people]
    if len({t.join["knee_series_sha256_le_f8"] for t in trials}) != len(trials):
        raise ValueError("Duplicate knee trace. Stop for source review.")
    mean = np.mean([t.tokens.mean(axis=(0, 1)) for t in trials], axis=0)
    variance = np.mean([((t.tokens - mean) ** 2).mean(axis=(0, 1)) for t in trials], axis=0)
    scale = np.sqrt(variance).clip(1e-6)
    zs = [normalize(t.tokens, mean, scale) for t in trials]
    ys = [t.target - t.stride for t in trials]
    fitted_ridge = ridge(zs, ys)
    x = torch.from_numpy(np.concatenate(zs).astype("f4"))
    y = torch.from_numpy((np.concatenate(ys) / 10).astype("f4"))
    lengths = np.array([len(z) for z in zs])
    starts = np.r_[0, np.cumsum(lengths)[:-1]]
    model = KneeTransformer()
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0015, weight_decay=.001, foreach=False)
    losses = []
    training_start = time.perf_counter()
    for _ in range(20 if benchmark else STEPS):
        persons = rng.integers(len(people), size=128)
        idx = torch.from_numpy(starts[persons] + rng.integers(lengths[persons]))
        optimizer.zero_grad(set_to_none=True)
        loss = nn.functional.smooth_l1_loss(model(x[idx]), y[idx], beta=.3)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    train_seconds = time.perf_counter() - training_start
    weights = dict(format="two-knee-stride-weights-1", mean=mean.tolist(), scale=scale.tolist(), ridge=fitted_ridge,
                   transformer={key: value.detach().tolist() for key, value in model.state_dict().items()})
    errors = []
    for t, z in zip(trials, zs, strict=True):
        ix = np.linspace(0, len(z) - 1, 11, dtype=int)
        with torch.no_grad():
            native = t.stride[ix] + 10 * model(torch.from_numpy(z[ix].astype("f4"))).numpy()
        packaged = predictions(t.tokens[ix], t.stride[ix], weights)["transformer_residual"]
        errors.append(float(np.max(np.abs(packaged - native))))
    if max(errors) > .001 or not np.isfinite(losses).all():
        raise ValueError("Numerical export or training-loss check failed")
    with output.open("x") as stream:
        json.dump(weights, stream, separators=(",", ":"), allow_nan=False)
        stream.write("\n")
    save(receipt, dict(benchmark=benchmark, seed=SEED, updates=len(losses), final_loss=losses[-1], first_loss=losses[0],
                       loss_sha256=series_hash(losses,"<f8"), train_cutoffs=int(lengths.sum()),
                       trained_members=[t.join for t in trials], protocol_sha256=PROTOCOL_SHA256,
                       weights_sha256=digest(output), source_sha256={n:digest(HERE/n) for n in
                       ("fit.py","trials.py","predict.py","extract.py","source-members.json","protocol.json")},
                       parity_max_degrees=max(errors), parity_probes=len(trials)*11,
                       parameters=sum(v.numel() for v in model.parameters()), numpy=np.__version__,
                       torch=str(torch.__version__), gpu_available=torch.cuda.is_available(),
                       intraop=torch.get_num_threads(), interop=torch.get_num_interop_threads(),
                       blas_threads=os.getenv("OPENBLAS_NUM_THREADS"), training_seconds=train_seconds,
                       total_seconds=time.perf_counter()-started))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("weights", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--threads", type=int, choices=[1, 2], default=2)
    parser.add_argument("--benchmark", action="store_true", help="S1 only, 20 updates, for timing")
    a = parser.parse_args()
    train(a.cache, a.weights, a.receipt, a.threads, a.benchmark)
