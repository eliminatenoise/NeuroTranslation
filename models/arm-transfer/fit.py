"""Fixed S1–S7 fits. Training requires NumPy and PyTorch. Prediction uses NumPy alone."""

import numpy as np
import torch
from predict import CHANNELS, CUES, HORIZONS, batch, design, features, tokens
from torch import nn


def balance(groups):
    """Equal people, runs within person, represented cues within run, trials within cue."""
    weight = np.ones(len(groups))
    parents = [np.arange(len(groups))]
    for column in range(3):
        children = []
        for rows in parents:
            labels = groups[rows, column]
            unique = np.unique(labels)
            weight[rows] /= len(unique)
            children.extend(rows[labels == label] for label in unique)
        parents = children
    for rows in parents:
        weight[rows] /= len(rows)
    return weight


def moments(a, w):
    mean = np.average(a, weights=w, axis=0)
    sd = np.sqrt(np.average((a - mean) ** 2, weights=w, axis=0))
    return mean, sd


def safe(sd):
    return np.where(sd < 1e-8, 1.0, sd)


def scalers(bins, targets, w):
    t, a = tokens(bins)
    tm, ts = moments(t.reshape(-1, 6), np.repeat(w / 4, 4))
    am, ass = moments(a, w)
    ym, ys = moments(targets.reshape(-1, 9), w)
    return {
        "token_mean": tm.tolist(),
        "token_sd": safe(ts).tolist(),
        "anchor_mean": am.tolist(),
        "anchor_sd": safe(ass).tolist(),
        "target_mean": ym.tolist(),
        "target_sd": safe(ys).tolist(),
        "constant_targets": (ys < 1e-8).tolist(),
        "raw_min": bins.min(axis=0).tolist(),
        "raw_max": bins.max(axis=0).tolist(),
    }


class Transformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.project = nn.Linear(6, 8)
        self.anchor = nn.Linear(3, 8)
        self.cue = nn.Embedding(8, 8)
        self.position = nn.Parameter(torch.empty(5, 8))
        nn.init.normal_(self.position, std=0.02)
        self.q = nn.Linear(8, 8)
        self.k = nn.Linear(8, 8)
        self.v = nn.Linear(8, 8)
        self.attn_out = nn.Linear(8, 8)
        self.norm1 = nn.LayerNorm(8)
        self.ff1 = nn.Linear(8, 12)
        self.ff2 = nn.Linear(12, 8)
        self.norm2 = nn.LayerNorm(8)
        self.head = nn.Linear(8, 9)

    def forward(self, z, anchor, cue):
        first = self.cue(cue) + self.anchor(anchor)
        h = torch.cat([first[:, None, :], self.project(z)], dim=1) + self.position
        q, k, v = [
            p(h).reshape(-1, 5, 2, 4).transpose(1, 2) for p in (self.q, self.k, self.v)
        ]
        attention = torch.softmax(q @ k.transpose(-1, -2) / 2, dim=-1)
        context = (attention @ v).transpose(1, 2).reshape(-1, 5, 8)
        h = self.norm1(h + self.attn_out(context))
        h = self.norm2(h + self.ff2(torch.tanh(self.ff1(h))))
        return self.head(h[:, 0, :])


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer = nn.Linear(34, 18)
        self.head = nn.Linear(18, 9)

    def forward(self, d):
        return self.head(torch.tanh(self.layer(d)))


def fit_network(method, z, a, cue, target, w, device, steps=80):
    torch.manual_seed(20713)
    is_attention = method.startswith("transformer")
    net = (Transformer() if is_attention else MLP()).to(device)
    initial = {name: p.detach().cpu().clone() for name, p in net.named_parameters()}

    def tensor(v):
        return torch.as_tensor(v, dtype=torch.float32, device=device)

    if is_attention:
        inputs = [
            tensor(z),
            tensor(a),
            torch.as_tensor(cue, dtype=torch.long, device=device),
        ]
    else:
        inputs = [tensor(design(z, a, cue))]
    target, w = tensor(target), tensor(w)
    opt = torch.optim.AdamW(net.parameters(), lr=0.01, weight_decay=0.01)
    first = None
    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        error = net(*inputs) - target
        loss = (w * error.square().mean(dim=1)).sum()
        if first is None:
            first = float(loss.detach().cpu())
        loss.backward()
        opt.step()
    with torch.no_grad():
        prediction = net(*inputs)
        loss = float((w * (prediction - target).square().mean(dim=1)).sum().cpu())
    if not np.isfinite(loss):
        raise ArithmeticError("The optimizer returned a nonfinite loss.")
    weights = {name: p.detach().cpu().tolist() for name, p in net.named_parameters()}
    change = {
        name: float((p.detach().cpu() - initial[name]).norm())
        for name, p in net.named_parameters()
    }
    note = {
        "updates": steps,
        "parameters": sum(p.numel() for p in net.parameters()),
        "initial_loss": first,
        "final_loss": loss,
        "update_l2_by_tensor": change,
    }
    return weights, note, prediction.detach().cpu().numpy()


def fit(x, y, g, device="cpu"):
    people = sorted(set(map(int, g[:, 0])))
    if min(people) < 1 or max(people) > 7:
        raise ValueError("Only S1–7 may fit the checkpoint.")
    weight = balance(g)
    model = {
        "format": "cued-arm-transfer-v1",
        "cues": list(CUES),
        "channels": list(CHANNELS),
        "horizons_s": list(HORIZONS),
        "fitting_people": people,
        "fitting_trials": len(x),
        "fits": {},
        "scales": scalers(x, y, weight),
    }
    s = model["scales"]
    z, a = features(model, x)
    flat = y.reshape(-1, 9)
    target = (flat - s["target_mean"]) / s["target_sd"]
    cue = g[:, 2]
    means = []
    for i in range(7):
        keep = cue == i
        if not np.any(keep):
            raise ValueError("A fitting cue is absent.")
        means.append(np.average(flat[keep], weights=weight[keep], axis=0).tolist())
    model["fits"]["cue"] = {"mean": means}
    diagnostics = {}
    for mode in (
        "ridge",
        "ridge_no_cue",
        "mlp",
        "mlp_no_cue",
        "transformer",
        "transformer_no_cue",
    ):
        ids = np.full(len(cue), 7, dtype=int) if mode.endswith("_no_cue") else cue
        if mode.startswith("ridge"):
            d = design(z, a, ids)
            mean, sd = moments(d, weight)
            d = (d - mean) / safe(sd)
            bias = np.average(target, weights=weight, axis=0)
            coef = np.linalg.solve(
                d.T @ (weight[:, None] * d) + 0.2 * np.eye(d.shape[1]),
                d.T @ (weight[:, None] * (target - bias)),
            )
            model["fits"][mode] = {
                "mean": mean.tolist(),
                "sd": safe(sd).tolist(),
                "coef": coef.tolist(),
                "bias": bias.tolist(),
            }
        else:
            q, note, native = fit_network(mode, z, a, ids, target, weight, device)
            model["fits"][mode] = q
            replay = (batch(model, x, cue, mode).reshape(-1, 9) - s["target_mean"]) / s[
                "target_sd"
            ]
            note["portable_max_abs_scaled_difference"] = float(
                np.max(np.abs(replay - native))
            )
            if not np.allclose(replay, native, rtol=1e-4, atol=1e-4):
                raise ArithmeticError(
                    "Portable replay differs from the native fitted model."
                )
            diagnostics[mode] = note
    return model, diagnostics
