"""Compact family M1 (three-pass recurrent model) with its secondary arms C4, S1, S2, S3, S4 and S6.

Ported from the published compact training code (learned.py, inputs.py; sha256 in PROTOCOL.json).
Gate G0 checks that train() reproduces the sealed 12-person checkpoints tensor for tensor.
Runtime A: CPython 3.13.15, torch 2.14.1+cpu, numpy 2.5.3, safetensors 0.8.0. One thread per fit.
"""
import hashlib
import json
import math
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from compact import compact_inputs, history_features, participant_weights, take, training_table  # noqa: F401

WIDTH = 24
RECIPE = {'width': 24, 'updates': 900, 'batch_rows': 128, 'learning_rate': 0.002, 'weight_decay': 0.001}


def setup_runtime():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


# ----------------------------------------------------------------------------------------- model
class RecordedForecast(nn.Module):
    def __init__(self, width, passes=3):
        super().__init__()
        self.passes = passes
        self.conv = nn.Conv1d(5, width, 3)
        if passes is None:
            self.recurrent = nn.LSTM(width, width, batch_first=True)
        else:
            self.recurrent = nn.GRU(width, width, batch_first=True)
            self.shared_step = nn.GRUCell(width, width)
        self.out = nn.Linear(width, 2)

    def forward(self, inputs):
        encoded = F.silu(self.conv(F.pad(inputs.transpose(1, 2), (2, 0)))).transpose(1, 2)
        steps, _ = self.recurrent(encoded)
        summary = steps[:, -1]
        if self.passes is not None:
            state = summary
            for _ in range(self.passes):
                state = self.shared_step(summary, state)
            summary = state
        return self.out(summary)


class TrainingBatch:
    """Published sampling and loss weights. Rows without impulse support are never drawn."""

    def __init__(self, table):
        person, member, tick = table['participant_index'], table['member_index'], table['issue_tick']
        event_mass = participant_weights(person, member, tick, table['event_supported'])
        impulse_mass = participant_weights(person, member, tick, table['impulse_supported'])
        if not (np.isclose(impulse_mass.sum(), 1.) and np.isclose(event_mass.sum(), 1.)):
            raise ValueError('outcome weights must each sum to one over their support')
        prior = float(event_mass @ table['event'])
        if not 0. < prior < 1.:
            raise ValueError('the event support needs both outcomes')
        self.prior = prior
        self.log_odds = math.log(prior / (1. - prior))
        self.rows = len(person)
        self.impulse_rows = int(table['impulse_supported'].sum())
        self.event_only_rows = int((table['event_supported'] & ~table['impulse_supported']).sum())
        self.x = torch.from_numpy(table['x'])
        residual = np.where(table['impulse_supported'], table['impulse'] - table['persistence'], 0.)
        self.target = torch.from_numpy(np.column_stack((table['event'], residual)).astype(np.float32))
        ratio = np.divide(event_mass, impulse_mass, out=np.zeros_like(event_mass), where=impulse_mass > 0)
        self.event_weight = torch.from_numpy(ratio.astype(np.float32))
        self.sampling_mass = torch.from_numpy(impulse_mass)


def train(batch, seed, *, width=WIDTH, updates=900, readout_only=False, passes=3, options=RECIPE):
    """Published recipe. readout_only=True is control C4 (convolution and recurrent layers frozen)."""
    started = time.perf_counter()
    torch.manual_seed(seed)
    model = RecordedForecast(width, passes).float()
    generator = torch.Generator().manual_seed(seed + 300)
    if readout_only:
        for name, parameter in model.named_parameters():
            parameter.requires_grad_(name.startswith('out.'))
        trainable = list(model.out.parameters())
    else:
        trainable = list(model.parameters())
    optimizer = torch.optim.AdamW(trainable, lr=options['learning_rate'], weight_decay=options['weight_decay'])
    rows = torch.multinomial(batch.sampling_mass, updates * options['batch_rows'], replacement=True,
                             generator=generator).reshape(updates, options['batch_rows'])
    loss = torch.tensor(float('nan'))
    for chosen in rows:
        estimate = model(batch.x[chosen])
        event = F.binary_cross_entropy_with_logits(estimate[:, 0] + batch.log_odds, batch.target[chosen, 0],
                                                   reduction='none')
        impulse = F.smooth_l1_loss(estimate[:, 1], batch.target[chosen, 1])
        loss = .5 * (impulse + (event * batch.event_weight[chosen]).mean())
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
    if not bool(torch.isfinite(loss)):
        raise FloatingPointError('nonfinite loss')
    return model, float(loss.detach()), time.perf_counter() - started


def epoch_matched_updates(rows_n, rows_12):
    """S1 and S3: round(900 x rows_N / rows_12), rows = impulse-supported training rows."""
    return int(round(900 * rows_n / rows_12))


# ------------------------------------------------------------------------------------ checkpoints
def state_tensors(model):
    return {k: v.detach().contiguous() for k, v in model.state_dict().items()}


def tensor_digest(tensors):
    h = hashlib.sha256()
    for name in sorted(tensors):
        t = tensors[name].detach().cpu().contiguous()
        h.update(name.encode() + b'\0' + str(t.dtype).encode() + b'\0' + json.dumps(list(t.shape)).encode() + b'\0')
        h.update(t.numpy().tobytes())
    return h.hexdigest()


def save(model, path):
    """safetensors without metadata: identical bytes in every process."""
    from safetensors.torch import save_file
    tensors = state_tensors(model)
    save_file(tensors, str(path))
    return tensor_digest(tensors)


def load(path, width=WIDTH, passes=3):
    from safetensors.torch import load_file
    model = RecordedForecast(width, passes).float().eval()
    model.load_state_dict(load_file(str(path), device='cpu'), strict=True)
    return model


def forecast(model, x, persistence, prior, *, chunk=4096):
    """New-load probability and impulse (N s), issued in one fixed batch order."""
    model.eval()
    out = []
    with torch.inference_mode():
        for start in range(0, len(x), chunk):
            out.append(model(torch.from_numpy(np.ascontiguousarray(x[start:start + chunk]))).numpy())
    raw = np.concatenate(out) if out else np.zeros((0, 2), dtype=np.float32)
    log_odds = math.log(prior / (1 - prior)) + raw[:, 0].astype(np.float64)
    probability = 1 / (1 + np.exp(-log_odds))
    return probability, persistence + raw[:, 1].astype(np.float64)
