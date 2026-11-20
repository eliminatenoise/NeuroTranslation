"""Fit tagged and history-only causal gait models and a weighted linear baseline."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(48)
        self.qkv = nn.Linear(48, 144)
        self.out = nn.Linear(48, 48)
        self.ln2 = nn.LayerNorm(48)
        self.ff1 = nn.Linear(48, 96)
        self.ff2 = nn.Linear(96, 48)

    def forward(self, x):
        b, t, _ = x.shape
        q, k, v = [u.reshape(b, t, 4, 12).transpose(1, 2) for u in self.qkv(self.ln1(x)).chunk(3, dim=-1)]
        a = torch.softmax(q @ k.transpose(-2, -1) / 12**.5, dim=-1)
        x = x + self.out((a @ v).transpose(1, 2).reshape(b, t, 48))
        return x + self.ff2(torch.relu(self.ff1(self.ln2(x))))


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.input = nn.Linear(57, 48)
        self.action = nn.Embedding(2, 48)
        self.position = nn.Parameter(torch.randn(11, 48) * .05)
        self.blocks = nn.Sequential(Block(), Block())
        self.final = nn.LayerNorm(48)
        self.readout = nn.Linear(48, 6 * 57)

    def forward(self, x, token):
        h = self.input(x) + self.position + self.action(token)[:, None]
        a = self.readout(self.final(self.blocks(h)[:, -1])).reshape(-1, 6, 57)
        prev = torch.cat((torch.zeros_like(a[:, :1]), a[:, :-1]), dim=1)
        return torch.stack(((prev + a) / 2, a), dim=2).reshape(-1, 12, 57)


def mass(subjects, ids):
    weights = np.empty(len(ids))
    groups = np.unique(subjects)
    for group in groups:
        clips = np.unique(ids[subjects == group])
        for clip in clips:
            where = ids == clip
            weights[where] = 1 / (len(groups) * len(clips) * np.sum(where))
    return weights


def loss_value(pred, target):
    body = pred[..., :54].reshape(-1, 12, 18, 3)
    body = body - body[:, :, 2:4].mean(dim=2, keepdim=True)
    body_error = body.flatten(-2) - target[..., :54]
    root_error = pred[..., 54:] - target[..., 54:]
    return body_error.square().mean() + root_error.square().mean()


def train(data, mode, updates):
    torch.manual_seed(2511)
    rng = np.random.default_rng(34211)
    x = torch.tensor(data["x"], dtype=torch.float32)
    y = torch.tensor(data["y"], dtype=torch.float32)
    tokens = torch.from_numpy(data["token"].astype(np.int64)) if mode == "conditional" else torch.zeros(len(x), dtype=torch.long)
    m = Model()
    opt = torch.optim.AdamW(m.parameters(), lr=.001, weight_decay=.001)
    p = mass(data["subject"], data["id"])
    started = time.perf_counter()
    for _ in range(updates):
        idx = rng.choice(len(x), size=48, replace=True, p=p)
        opt.zero_grad()
        loss = loss_value(m(x[idx], tokens[idx]), y[idx])
        loss.backward()
        opt.step()
    with torch.no_grad():
        probe = m(x[:4], tokens[:4]).numpy().copy()
    return m, probe, {"updates": updates, "lastMinibatchLoss": loss.item(), "fitSeconds": time.perf_counter() - started}


def fit_ridge(data, output):
    x = data["x"].reshape(len(data["x"]), -1)
    y = data["y"].reshape(len(x), -1)
    weight = mass(data["subject"], data["id"])
    mean_x, mean_y = weight @ x, weight @ y
    centre = x - mean_x
    gram = centre.T @ (centre * weight[:, None])
    gram.flat[::gram.shape[0] + 1] += .002
    coef = np.linalg.solve(gram, centre.T @ ((y - mean_y) * weight[:, None]))
    np.savez_compressed(output / "ridge.npz", coef=coef.astype("f4"), bias=(mean_y - mean_x @ coef).astype("f4"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("local", type=Path)
    p.add_argument("--trial", action="store_true")
    p.add_argument("--threads", type=int, choices=[1, 2], required=True)
    args = p.parse_args()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    data = dict(np.load(args.local / "train.npz"))
    modes = ["conditional"] if args.trial else ["conditional", "history-only"]
    if not args.trial:
        if (args.local / "lock.json").exists():
            raise ValueError("Fits already sealed; use a fresh output directory for reproduction")
        fit_ridge(data, args.local)
    for mode in modes:
        m, probe, info = train(data, mode, 32 if args.trial else 850)
        info.update(mode=mode, intraop=torch.get_num_threads(), interop=torch.get_num_interop_threads(), nParams=sum(v.numel() for v in m.parameters()))
        if args.trial:
            name = f"trial-{args.threads}"
        else:
            name = mode
            payload = {"format": "stride-attention-1", "mode": mode, "weights": {k: v.detach().numpy().tolist() for k, v in m.state_dict().items()}}
            (args.local / (mode + ".json")).write_text(json.dumps(payload, separators=(",", ":")) + "\n")
        np.save(args.local / (name + "-probe.npy"), probe)
        (args.local / (name + "-fit.json")).write_text(json.dumps(info, indent=2) + "\n")
        print(info, flush=True)


if __name__ == "__main__":
    main()
