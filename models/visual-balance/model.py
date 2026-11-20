"""Eight-token walking forecast. Source axes are ML, SI, AP; sacrum then head."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

MODES = ("full", "no_scalp")
SIGNALS = ("nuisance_mean_uv", "nuisance_rms_uv", "eeg_mean_uv", "eeg_rms_uv")
INPUTS = ("motion_mm", "direction", *SIGNALS, "eeg_good", "nuisance_good")
SCHEDULE_SEED = 3407
BATCH_SIZE = 96
UPDATES = 240


def write_json(path, value, *, compact=False):
    Path(path).write_text(json.dumps(value, allow_nan=False, indent=None if compact else 2,
                                     separators=(",", ":") if compact else None) + "\n")


def subset(d, idx):
    return {k: v[idx] for k, v in d.items()}


def load_data(path):
    with np.load(path, allow_pickle=False) as f:
        d = dict(f)
    validate_inputs(d)
    n = len(d["direction"])
    if d["future_delta_mm"].shape != (n, 2, 3) or not np.isfinite(d["future_delta_mm"]).all():
        raise ValueError("Expected finite two-marker target")
    keys = list(zip(d["person"], d["event"]))
    if len(set(keys)) != n or any(d[k].shape != (n,) for k in ("person", "event", "cutoff", "block")):
        raise ValueError("Duplicated event or invalid index")
    if not np.isin(d["block"], [0, 1, 2]).all():
        raise ValueError("Invalid session part")
    return d


def validate_inputs(d):
    n = len(d["direction"])
    if d["direction"].shape != (n,) or not np.isin(d["direction"], [-1, 1]).all():
        raise ValueError("Expected direction ±1")
    m = d["motion_mm"]
    if m.shape != (n, 160, 2, 3) or not np.isfinite(m).all() or np.any(np.abs(m[:, -1]) > 1e-5):
        raise ValueError("Expected finite cutoff-relative motion [N,160,2,3]")
    for group, channels in (("eeg", 128), ("nuisance", 13)):
        mask = d[group + "_good"]
        if mask.shape != (n, channels) or mask.dtype != np.bool_:
            raise ValueError("Expected Boolean availability mask: " + group)
        for stat in ("mean", "rms"):
            v = d[group + "_" + stat + "_uv"]
            if v.shape != (n, 8, channels):
                raise ValueError("Invalid signal dimensions: " + group)
            good = np.where(mask[:, None], v, 0)
            if not np.isfinite(good).all() or (stat == "rms" and (good < 0).any()):
                raise ValueError("Invalid observed voltage: " + group)


def skip(motion):
    return (motion[:, -1] - motion[:, -33]).reshape(-1, 6).astype(np.float64)


def motion_features(motion):
    bins = motion.astype(np.float64).reshape(-1, 8, 20, 6)
    return np.concatenate((bins[:, :, -1], bins[:, :, -1] - bins[:, :, 0]), axis=-1)


def signal(d, name):
    mask = d[name.split("_")[0] + "_good"]
    x = np.where(mask[:, None], d[name], 0).astype(np.float64)
    return (np.log1p(x) if "_rms_" in name else x), mask


def scale(x, mask, people, floor):
    """Average each supplying participant's observed first and second moments."""
    count = np.zeros(x.shape[-1])
    first, second = np.zeros_like(count), np.zeros_like(count)
    for person in sorted(set(people)):
        ids = np.flatnonzero(people == person)
        good = mask[ids]
        values = np.where(good[:, None], x[ids], 0)
        denom = good.sum(axis=0) * x.shape[1]
        count += denom > 0
        first += values.sum(axis=(0, 1)) / np.maximum(denom, 1)
        second += (values * values).sum(axis=(0, 1)) / np.maximum(denom, 1)
    mean = first / np.maximum(count, 1)
    sd = np.maximum(floor, np.sqrt(np.maximum(0, second / np.maximum(count, 1) - mean * mean)))
    return {"mean": mean.tolist(), "sd": sd.tolist(), "seen": (count > 0).tolist()}


def normalizer(d):
    people = d["person"]
    motion = motion_features(d["motion_mm"])
    residual = d["future_delta_mm"].reshape(-1, 6) - skip(d["motion_mm"])
    out = {}
    for name, x in (("motion", motion), ("residual", residual[:, None, :])):
        available = np.ones((len(x), x.shape[-1]), bool)
        out[name] = scale(x, available, people, 1.0)
    for name in SIGNALS:
        x, mask = signal(d, name)
        out[name] = scale(x, mask, people, .1 if "_rms_" in name else 1.)
    return out


def standardized(x, mask, stat):
    observed = mask & np.asarray(stat["seen"])
    normalized = np.clip((x - stat["mean"]) / stat["sd"], -6., 6.)
    return np.where(observed[:, None], normalized, 0), observed


def scalp_scores(x, mask):
    x = x.reshape(-1, 8, 4, 32)
    mask = mask.reshape(-1, 4, 32)
    fields = []
    for k in (0, 1):
        cosine = np.cos(np.pi * k * (np.arange(32) + .5) / 32.)
        denominator = np.sqrt((mask * cosine**2).sum(axis=-1))
        projected = (x * cosine).sum(axis=-1)
        fields.append(np.divide(projected, denominator[:, None], out=np.zeros_like(projected),
                                where=denominator[:, None] > 0))
    return np.stack(fields, axis=-1).reshape(-1, 8, 8)


def features(d, norm, mode):
    if mode not in MODES:
        raise ValueError("Unknown weight branch")
    raw_motion = motion_features(d["motion_mm"])
    motion = standardized(raw_motion, np.ones((len(raw_motion), 12), bool), norm["motion"])[0]
    nuisance = [standardized(*signal(d, key), norm[key])[0] for key in SIGNALS[:2]]
    direction = np.broadcast_to(d["direction"][:, None, None], (len(motion), 8, 1))
    slots = np.concatenate((motion, nuisance[0][:, :, :4]), axis=-1)
    if mode == "full":
        fields = [scalp_scores(*standardized(*signal(d, key), norm[key])) for key in SIGNALS[2:]]
        slots += .35 * np.concatenate(fields, axis=-1)
    return np.concatenate((motion, *nuisance, direction, slots), axis=-1).astype(np.float32)


class Forecast(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Linear(55, 24)
        self.position = nn.Parameter(torch.empty(8, 24))
        nn.init.normal_(self.position, std=.02)
        self.qkv = nn.Linear(24, 72)
        self.attn_out = nn.Linear(24, 24)
        self.norm1 = nn.LayerNorm(24)
        self.hidden = nn.Linear(24, 48)
        self.project = nn.Linear(48, 24)
        self.norm2 = nn.LayerNorm(24)
        self.readout = nn.Linear(24, 6)
        self.motion_readout = nn.Linear(96, 6, bias=False)

    def forward(self, x):
        h = self.embed(x) + self.position
        q, k, v = (a.reshape(-1, 8, 3, 8).transpose(1, 2) for a in self.qkv(h).chunk(3, -1))
        attention = (q[:, :, -1:] @ k.transpose(-1, -2) / (8**.5)).softmax(-1)
        mixed = (attention @ v).reshape(-1, 24)
        z = self.norm1(h[:, -1] + self.attn_out(mixed))
        shared = self.norm2(z + self.project(self.hidden(z).tanh()))
        return self.readout(shared) + self.motion_readout(x[:, :, :12].reshape(-1, 96))


def tensor(x, device="cpu"):
    return torch.as_tensor(x, device=device, dtype=torch.float32)


def train_model(d, norm, mode, device="cpu", updates=UPDATES):
    torch.manual_seed(9721)
    net = Forecast().to(device)
    x = tensor(features(d, norm, mode), device)
    residual = d["future_delta_mm"].reshape(-1, 6) - skip(d["motion_mm"])
    y = tensor((residual - norm["residual"]["mean"]) / norm["residual"]["sd"], device)
    groups = [np.flatnonzero(d["person"] == p) for p in sorted(set(d["person"]))]
    rng = np.random.default_rng(SCHEDULE_SEED)
    optimizer = torch.optim.AdamW(net.parameters(), lr=.0025, weight_decay=.01, foreach=False)
    trunk = [p for k, p in net.named_parameters() if "readout" not in k]
    flatten = lambda params: torch.cat([p.detach().flatten() for p in params])
    start = flatten(trunk).clone()
    proof = {"steps": updates, "parameters": sum(p.numel() for p in net.parameters())}
    for step in range(updates):
        persons = rng.integers(len(groups), size=BATCH_SIZE)
        local = rng.integers([len(groups[i]) for i in persons])
        idx = torch.as_tensor([groups[i][j] for i, j in zip(persons, local)], device=device)
        optimizer.zero_grad(set_to_none=True)
        per_marker = (net(x[idx]) - y[idx]).square().reshape(-1, 2, 3).mean((0, 2))
        if step == 0:
            proof["shared_gradient_norm_sacrum_head"] = [
                flatten(torch.autograd.grad(loss, trunk, retain_graph=True)).norm().item()
                for loss in per_marker]
        per_marker.mean().backward()
        optimizer.step()
    proof["trunk_change_norm"] = (flatten(trunk) - start).norm().item()
    return {"mode": mode, "norm": norm,
            "state": {k: v.detach().cpu().tolist() for k, v in net.state_dict().items()}}, proof


def predict(d, bundle):
    net = Forecast()
    net.load_state_dict({k: tensor(v) for k, v in bundle["state"].items()})
    norm = bundle["norm"]
    with torch.inference_mode():
        output = net(tensor(features(d, norm, bundle["mode"]))).double().numpy()
    physical = output * norm["residual"]["sd"] + norm["residual"]["mean"] + skip(d["motion_mm"])
    if not np.isfinite(physical).all():
        raise ArithmeticError("Nonfinite prediction")
    return physical.reshape(-1, 2, 3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forecast one visual-rotation event from JSON.")
    parser.add_argument("weights")
    parser.add_argument("event")
    args = parser.parse_args()
    raw = json.loads(Path(args.event).read_text())
    d = {k: np.asarray([raw[k]]) for k in INPUTS}
    validate_inputs(d)
    models = json.loads(Path(args.weights).read_text())
    torch.set_num_threads(1)
    print(json.dumps({k: predict(d, models[k])[0].tolist() for k in MODES}, indent=2))
