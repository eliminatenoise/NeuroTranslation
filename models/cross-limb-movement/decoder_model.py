"""Shared temporal Transformer with either study-specific or time-interpolated path maps."""
import copy
import json
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from interface import MUSCLES
from network import INPUT_KEYS, WIDTH, SharedNet, check_event, predict_arrays


class PathMapNet(SharedNet):
    def __init__(self, kind):
        super().__init__()
        if kind not in ('separate', 'matched'):
            raise ValueError('Unknown path map')
        self.kind = kind
        self.path_alt = copy.deepcopy(self.path_out)

    def forward(self, batch):
        # Preserve the source network's operation order up to the final path readout.
        d, mask, r, pose, age, past, pose_context, direction = batch
        amplitude = torch.log1p(r).unsqueeze(-1)
        named = F.relu(self.names.weight + amplitude * self.slope)
        pooled = (named * mask[:, None, :, None]).sum(2) / mask.sum(1)[:, None, None]
        context = torch.stack((pose_context, direction, d.float()), dim=1)[:, None, :].expand(-1, 20, -1)
        x = self.patch(torch.cat((pooled, pose, age.unsqueeze(-1) * 500, context), dim=-1))
        x = x + self.time.weight + self.segment(d)[:, None, :]
        q, k, v = self.qkv(x).reshape(len(d), 20, 3, 2, 8).permute(2, 0, 3, 1, 4).unbind(0)
        score = torch.softmax(q @ k.transpose(-2, -1) / 8**.5, dim=-1)
        mixed = (score @ v).transpose(1, 2).reshape(len(d), 20, WIDTH)
        x = self.norm1(x + self.attn_out(mixed))
        h = self.norm2(x + self.ff2(F.relu(self.ff1(x))))[:, -1]
        rmsh = F.relu(self.rms_state(h)[:, None, :] + self.names.weight)
        rms = (past + self.rms_out(rmsh).squeeze(-1)).clamp_min(0) * mask
        ph = F.relu(self.path_state(h)[:, None, :] + self.path_time.weight)
        u = torch.arange(1, 33, device=d.device, dtype=pose.dtype) / 32
        interval = 1 / 32 + age[:, -2] - age[:, -1]
        linear = (pose[:, -1] - pose[:, -2]) * (.125 / interval[:, None])
        first, second = self.path_out(ph), self.path_alt(ph)
        if self.kind == 'separate':
            residual = torch.where(d[:, None, None] == 0, first, second)
        else:
            phase = torch.arange(32, device=d.device, dtype=pose.dtype) / 31
            residual = first + phase[None, :, None] * (second - first)
        return rms, u[None, :, None] * (linear[:, None, :] + residual)


def create(kind, seed):
    torch.manual_seed(seed)
    return SharedNet() if kind == 'original' else PathMapNet(kind)


def export(model, scales):
    return dict(format='cross-limb-path-map-v1', kind=model.kind, scales=scales, muscles=MUSCLES,
                state={k: t.detach().cpu().tolist() for k, t in model.state_dict().items()})


def predict_event(weights, event):
    """Return native RMS and millimetre path arrays for a validated synthetic or recorded input."""
    if isinstance(weights, (str, Path)):
        weights = json.loads(Path(weights).read_text())
    if weights['format'] != 'cross-limb-path-map-v1' or weights['muscles'] != MUSCLES:
        raise ValueError('Incompatible path-map weights or anatomy')
    check_event(event)
    model = PathMapNet(weights['kind'])
    model.load_state_dict({k: torch.tensor(v, dtype=torch.float32) for k, v in weights['state'].items()})
    rows = {k: np.asarray([event[k]]) for k in INPUT_KEYS}
    rms, path = predict_arrays(model.eval(), rows, weights['scales'])
    return dict(rms=[float(x) if keep else None for x, keep in zip(rms[0], event['muscle_mask'])],
                path_mm=path[0].tolist())
