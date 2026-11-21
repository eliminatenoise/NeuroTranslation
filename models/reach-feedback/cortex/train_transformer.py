"""Fit matched softplus count Transformers using training originals only."""
import argparse
import io
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from count_model import ARMS, SEEDS, normalizers, original_weights, patches, transformer
from study_io import BASE, HERE, arm_input, dump, load_inputs, npz, sha


class CountTransformer(nn.Module):
    def __init__(self, mean):
        super().__init__()
        self.hist = nn.Linear(5 * 42, 16)
        self.path = nn.Linear(5 * 8, 16)
        self.position = nn.Parameter(torch.randn(1, 7, 16) * .04)
        self.norm1 = nn.LayerNorm(16)
        self.qkv = nn.Linear(16, 48)
        self.project = nn.Linear(16, 16)
        self.norm2 = nn.LayerNorm(16)
        self.ff1 = nn.Linear(16, 32)
        self.ff2 = nn.Linear(32, 16)
        self.read_norm = nn.LayerNorm(16)
        self.read = nn.Linear(16, 230)
        with torch.no_grad():
            nn.init.normal_(self.read.weight, std=.01)
            self.read.bias.copy_(torch.from_numpy(np.tile(np.log(np.expm1(mean)), 10)).float())

    def forward(self, hist, future):
        token = hist.new_zeros(len(hist), 1, 16)
        x = torch.cat((token, self.hist(hist), self.path(future)), dim=1) + self.position
        q, k, v = self.qkv(self.norm1(x)).reshape(len(hist), 7, 3, 2, 8).permute(2, 0, 3, 1, 4)
        a = ((q @ k.transpose(-1, -2)) * (8 ** -.5)).softmax(dim=-1)
        z = (a @ v).transpose(1, 2).reshape(len(hist), 7, 16)
        x = x + self.project(z)
        x = x + self.ff2(F.relu(self.ff1(self.norm2(x))))
        return (F.softplus(self.read(self.read_norm(x[:, 0]))) + 1e-6).reshape(-1, 10, 23)


def pooled(y, w):
    return ((y * w[:, None, None]).sum(axis=(0, 1)) + .5) / (10 * w.sum() + 1.)


def fit(data, arm, seed, device, steps, prefix=False):
    start = time.monotonic()
    torch.manual_seed(seed)
    w = original_weights(data["original"])
    raw = arm_input(data, arm, None if prefix else data["forecast"][SEEDS.index(seed)])
    norm = normalizers(arm, raw, w)
    h, f = patches(norm, raw)
    y = data["delayed"]
    net = CountTransformer(pooled(y, w)).to(device)
    h_native, f_native, y_native, w_native = [
        torch.as_tensor(x, dtype=torch.float32, device=device)
        for x in (h, f, y, w / w.sum())
    ]
    opt = torch.optim.AdamW(net.parameters(), lr=.003, weight_decay=.01, foreach=False)
    losses = []
    first_step_time = None
    for i in range(steps):
        opt.zero_grad(set_to_none=True)
        rate = net(h_native, f_native)
        loss = ((rate - y_native * torch.log(rate)).mean(dim=(1, 2)) * w_native).sum()
        if i == 0:
            losses.append(float(loss.detach().cpu()))
        loss.backward()
        opt.step()
        if i == 0:
            if device == "cuda":
                torch.cuda.synchronize()
            first_step_time = time.monotonic() - start
    with torch.no_grad():
        rate = net(h_native, f_native)
        final_loss = ((rate - y_native * torch.log(rate)).mean(dim=(1, 2)) * w_native).sum()
        losses.append(float(final_loss.detach().cpu()))
        native = rate.cpu().numpy()
        gradient = max(float(p.grad.detach().abs().max().cpu()) for p in net.parameters() if p.grad is not None)
    weights = {k: t.detach().cpu().numpy() for k, t in net.state_dict().items()}
    weights.update(norm, family=np.array("transformer"), seed=np.array(seed), unit_guide=data["unit_guide"])
    port = transformer(weights, h, f)
    if not np.isfinite(losses).all() or not np.isfinite(gradient) or not np.isfinite(native).all() or (native <= 0).any():
        raise ValueError("Non-finite fit")
    np.testing.assert_allclose(port, native, rtol=5e-5, atol=2e-6)
    stats = {"initial_nll": losses[0], "final_nll": losses[-1], "steps": steps,
             "final_gradient_max": gradient, "parity_max_abs": float(np.max(np.abs(port - native))),
             "originals": len(np.unique(data["original"])), "windows": len(y),
             "parameters": sum(p.numel() for p in net.parameters()), "first_step_s": first_step_time}
    return weights, stats, native


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--prefix", action="store_true")
    a = ap.parse_args()
    start = time.monotonic()
    torch.set_num_interop_threads(1)
    torch.set_num_threads(a.threads)
    torch.set_float32_matmul_precision("highest")
    if a.prefix:
        with np.load(BASE / "source" / "train.npz") as z:
            rows = np.flatnonzero(z["fold"] > 0)
            data = {k: z[k][rows] for k in ("pose", "spikes", "cue", "delayed", "original")}
            data.update(unit_guide=z["unit_guide"], movement=None)
        weights, stats, native = fit(data, "direct", 17, a.device, 4, prefix=True)
        # Include export costs on the complete identical prefix.
        b = io.BytesIO()
        np.savez_compressed(b, **weights)
        key = a.device + "-" + str(a.threads)
        np.save(HERE / ("prefix-" + key + ".npy"), native)
        stats.update(elapsed_s=time.monotonic()-start, thread_count=torch.get_num_threads(),
                     interop=torch.get_num_interop_threads(), device=a.device, hip=torch.version.hip,
                     adapter=torch.cuda.get_device_name(0) if a.device == "cuda" else None,
                     torch=torch.__version__, serialized_bytes=b.tell(), affinity=list(os.sched_getaffinity(0)))
        dump(HERE / ("prefix-" + key + ".json"), stats)
        print(key, json.dumps(stats), flush=True)
        return
    data = load_inputs("train", fit=True)
    target = HERE / "weights"
    target.mkdir(exist_ok=True)
    if (HERE / "fit-lock.json").exists():
        raise RuntimeError("Heads already sealed")
    for arm in ARMS:
        for seed in SEEDS:
            path = target / f"transformer-{arm}-{seed}.npz"
            done = HERE / f"fit-transformer-{arm}-{seed}.json"
            if done.exists():
                if sha(path) != json.loads(done.read_text())["weight_sha256"]:
                    raise RuntimeError("Partial checkpoint mismatch")
                continue
            at = time.monotonic()
            weights, stats, _ = fit(data, arm, seed, a.device, 64)
            npz(path, weights)
            stats.update(arm=arm, seed=seed, elapsed_s=time.monotonic()-at, weight_sha256=sha(path),
                         device=a.device, threads=a.threads, torch=torch.__version__)
            dump(done, stats)
            print(arm, seed, round(stats["elapsed_s"], 2), round(stats["final_nll"], 5), flush=True)


if __name__ == "__main__":
    main()
