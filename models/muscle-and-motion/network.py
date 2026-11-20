"""Paired leg-voltage and sacrum forecasts. All times are sampled at 256 Hz."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn


def sha256(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, allow_nan=False, separators=(",", ":")) + "\n")


def read_events(path):
    with np.load(path, allow_pickle=False) as bundle:
        return {key: bundle[key] for key in bundle.files}


def raw_features(leg, sacrum, posture, direction):
    leg = np.asarray(leg, dtype=np.float64)
    sacrum = np.asarray(sacrum, dtype=np.float64)
    n = len(leg)
    if leg.shape != (n, 160, 8) or sacrum.shape != (n, 160, 3):
        raise ValueError("Provide 160 observed samples with eight muscle and three marker channels")
    if not (np.isfinite(leg).all() and np.isfinite(sacrum).all()
            and np.isin(posture, [0, 1]).all() and np.isin(direction, [-1, 1]).all()):
        raise ValueError("Histories must be finite; use posture 0/1 and visual direction -1/+1")
    lv = leg.reshape(n, 20, 8, 8)
    xyz = (sacrum - sacrum[:, -1:]).reshape(n, 20, 8, 3)
    tokens = np.concatenate([np.log1p(np.sqrt((lv**2).mean(2))), xyz.mean(2),
                             xyz[:, :, -1] - xyz[:, :, 0],
                             np.broadcast_to(np.asarray(posture)[:, None, None], (n, 20, 1)),
                             np.broadcast_to(np.asarray(direction)[:, None, None], (n, 20, 1))], axis=2)
    hold = np.sqrt((leg[:, -32:]**2).mean(1))
    velocity = (sacrum[:, -1] - sacrum[:, -17]) / 16
    return [a.astype("float32") for a in (tokens, hold, velocity)]


def inputs(data):
    return raw_features(*(data[k] for k in ("leg_uv", "sacrum_mm", "posture", "direction")))


def calibration(arrays, data, indices):
    t = arrays[0][indices, :, :14].astype("float64")
    rms = data["future_rms_uv"][indices].astype("float64")
    path = data["future_path_mm"][indices].astype("float64")
    return dict(mean=t.mean((0, 1)).tolist(), sd=np.maximum(t.std((0, 1)), .0001).tolist(),
                rms_mean=rms.mean(0).tolist(), rms_scale=max(.001, float(rms.mean())),
                path_scale=max(.001, float(np.linalg.norm(path, axis=2).mean())))


def prepare(arrays, scale, device):
    t, hold, vel = arrays
    t = t.copy()
    t[:, :, :14] = (t[:, :, :14] - np.asarray(scale["mean"])) / np.asarray(scale["sd"])
    return [torch.from_numpy(a).to(device) for a in (t, hold, vel)]


class Forecast(nn.Module):
    def __init__(self, task):
        super().__init__()
        if task not in {"joint", "muscle", "path"}:
            raise ValueError(task)
        self.task = task
        self.inp = nn.Linear(16, 24)
        self.pos = nn.Parameter(torch.empty(20, 24))
        nn.init.normal_(self.pos, std=.05)
        self.norm1 = nn.LayerNorm(24)
        self.qkv = nn.Linear(24, 72)
        self.mix = nn.Linear(24, 24)
        self.norm2 = nn.LayerNorm(24)
        self.ff1 = nn.Linear(24, 48)
        self.ff2 = nn.Linear(48, 24)
        self.outnorm = nn.LayerNorm(24)
        # Draw both heads in the same order, then retain only those being fitted.
        muscle, path = nn.Linear(24, 8), nn.Linear(24, 12)
        for head in (muscle, path):
            nn.init.normal_(head.weight, std=.01)
            nn.init.zeros_(head.bias)
        if task != "path":
            self.muscle = muscle
        if task != "muscle":
            self.path = path

    def forward(self, toks, hold, vel, scale):
        h = self.inp(toks) + self.pos
        q, k, v = self.qkv(self.norm1(h)).reshape(len(h), 20, 3, 2, 12).permute(2, 0, 3, 1, 4).unbind(0)
        attn = torch.softmax((q @ k.transpose(-2, -1)) / (12**.5), dim=-1)
        ctx = (attn @ v).transpose(1, 2).reshape(len(h), 20, 24)
        h = h + self.mix(ctx)
        h = h + self.ff2(torch.relu(self.ff1(self.norm2(h))))
        out = self.outnorm(h[:, -1])
        rms = path = None
        if self.task != "path":
            base = hold + .05 * hold.new_tensor(scale["rms_mean"])
            rms = base * torch.exp(self.muscle(out).clamp(-3, 3))
        if self.task != "muscle":
            anchors = self.path(out).reshape(-1, 4, 3) * scale["path_scale"]
            anchors = torch.cat([anchors.new_zeros((len(out), 1, 3)), anchors], 1)
            disp = anchors[:, 1:] - anchors[:, :-1]
            frac = torch.arange(1, 9, dtype=out.dtype, device=out.device) / 8
            correction = anchors[:, :-1, None] + disp[:, :, None] * frac[None, None, :, None]
            path = correction.reshape(-1, 32, 3) + vel[:, None] * torch.arange(1, 33, device=out.device)[None, :, None]
        return rms, path


def export(model):
    return {name: p.detach().cpu().numpy().tolist() for name, p in model.state_dict().items()}


def restore(weights, task, device="cpu"):
    model = Forecast(task)
    model.load_state_dict({k: torch.tensor(v, dtype=torch.float32) for k, v in weights.items()})
    return model.to(device).eval()


@torch.inference_mode()
def predictions(model, prepared, scale):
    result = [[], []]
    for i in range(0, len(prepared[0]), 128):
        outputs = model(*[x[i:i+128] for x in prepared], scale)
        for j, value in enumerate(outputs):
            if value is not None:
                result[j].append(value.cpu().numpy())
    return tuple(np.concatenate(parts) if parts else None for parts in result)


def configure(threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.use_deterministic_algorithms(True)
