"""Fit the frozen word decoder and matched controls using the training split only."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from acquire import digest, manifest
from generate import time_features
from torch import nn

ACTIONS = ["walk", "run"]


class Decoder(nn.Module):
    def __init__(self, centre):
        super().__init__()
        self.embedding = nn.Embedding(2, 8)
        self.hidden1 = nn.Linear(17, 48)
        self.hidden2 = nn.Linear(48, 48)
        self.output = nn.Linear(48, 57)
        self.register_buffer("time", torch.from_numpy(time_features()))
        self.register_buffer("centre", centre)

    def forward(self, tokens):
        batch = len(tokens)
        words = self.embedding(tokens)[:, None, :].expand(-1, 25, -1)
        x = torch.cat([words, self.time[None].expand(batch, -1, -1)], dim=2)
        x = self.hidden1(x).tanh()
        x = self.hidden2(x).tanh()
        y = self.output(x) * 100.0 + self.centre
        return torch.cat([y[:, :, :-3], y[:, :, -3:] - y[:, :1, -3:]], dim=-1)

    def export(self):
        ls = [self.hidden1, self.hidden2, self.output]
        return {
            "version": 1,
            "tokens": ACTIONS,
            "scaleMm": 100,
            "centreMm": self.centre.tolist(),
            "embedding": self.embedding.weight.tolist(),
            "layers": [
                {
                    "weight": l.weight.tolist(),
                    "bias": l.bias.tolist(),
                    "activation": "linear" if i == 2 else "tanh",
                }
                for i, l in enumerate(ls)
            ],
        }


def write(path, data):
    path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")


def fit_model(tokens, targets, steps):
    torch.manual_seed(3429)
    m = Decoder(targets.mean((0, 1)))
    opt = torch.optim.Adam(m.parameters(), lr=0.006)
    losses = []
    for step in range(1, steps + 1):
        opt.zero_grad()
        pred = m(tokens)
        loss = ((pred - targets) / 100.0).square().mean()
        loss.backward()
        opt.step()
        if step == 1 or step % 100 == 0 or step == steps:
            losses.append({"step": step, "preUpdateLoss": float(loss.detach())})
    return m.eval(), losses


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local", type=Path, required=True)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--benchmark", action="store_true")
    args = p.parse_args()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    d = args.local
    rows = {r["id"]: r for r in manifest()["clips"] if r["split"] == "train"}
    with np.load(d / "train" / "targets.npz") as data:
        ids, y = data["ids"].tolist(), data["y"]
    tokens = np.array([ACTIONS.index(rows[uid]["action"]) for uid in ids])
    target = torch.from_numpy(y)
    if args.benchmark:
        start = time.perf_counter()
        model, loss = fit_model(torch.from_numpy(tokens), target, 32)
        print(
            json.dumps(
                {
                    "threads": torch.get_num_threads(),
                    "interop": torch.get_num_interop_threads(),
                    "seconds": time.perf_counter() - start,
                    "loss": loss[-1]["preUpdateLoss"],
                }
            )
        )
        return
    out = d / "fit"
    out.mkdir(exist_ok=True)
    if (out / "lock.json").exists():
        p.error(
            "Use a fresh local folder for a new experiment; existing fit is sealed."
        )
    np.savez(
        out / "means.npz",
        globalMean=y.mean(0),
        byAction=np.stack([y[tokens == i].mean(0) for i in (0, 1)]),
    )
    if len(set(tokens)) != 2:
        raise ValueError("Both actions are required")
    shuffled = np.random.default_rng(11273).permutation(tokens)
    results = {
        "eligibleTrainIds": ids,
        "requestedTerms": tokens.tolist(),
        "shuffledTerms": shuffled.tolist(),
        "torch": str(torch.__version__),
        "threads": torch.get_num_threads(),
        "interop": torch.get_num_interop_threads(),
        "fits": {},
    }
    for name, t in [
        ("conditional", tokens),
        ("constant", np.zeros_like(tokens)),
        ("shuffled", shuffled),
    ]:
        start = time.perf_counter()
        model, losses = fit_model(torch.from_numpy(t), target, 500)
        write(out / (name + ".json"), model.export())
        with torch.no_grad():
            predictions = model(
                torch.tensor([0, 0] if name == "constant" else [0, 1])
            ).numpy()
        np.save(out / (name + "-prediction.npy"), predictions)
        results["fits"][name] = {
            "seconds": time.perf_counter() - start,
            "loss": losses,
            "parameters": sum(p.numel() for p in model.parameters()),
        }
    write(out / "fit.json", results)
    files = sorted(out.iterdir())
    write(
        out / "lock.json",
        {f.name: digest(f.read_bytes()) for f in files if f.is_file()},
    )
    print(json.dumps(results["fits"]))


if __name__ == "__main__":
    main()
