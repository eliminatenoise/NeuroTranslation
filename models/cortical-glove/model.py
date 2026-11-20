# SPDX-License-Identifier: CC0-1.0
"""Retrospective FingerFlex forecast from four causal, recorded time tokens."""
from pathlib import Path

import numpy as np

TOKEN_LAGS = np.array([-120, -80, -40, 0])
WINDOW = 160
GLOVE = slice(0, 5)
CUE = slice(5, 65)
BRAIN = slice(65, 157)
FEATURES = {
    'cue': CUE, 'motion': GLOVE, 'motion_cue': slice(0, 65),
    'aligned': slice(0, 157), 'earlier_fit': slice(0, 157),
}


def band_features(counts):
    """Input (...,160,46) in amplifier counts; output (...,92), ordered band first."""
    counts = np.asarray(counts)
    if counts.shape[-2:] != (WINDOW, 46):
        raise ValueError('Expected 160 consecutive 1 kHz samples from 46 ordered contacts')
    uv = counts.astype(np.float64) * 0.0298
    uv -= uv.mean(axis=-1, keepdims=True)
    uv -= uv.mean(axis=-2, keepdims=True)
    taper = np.hanning(WINDOW)
    fft = np.fft.rfft(uv * taper[:, None], axis=-2)
    power = np.square(np.abs(fft)) * (2 / (WINDOW * np.square(taper).sum()))
    # Both bands contain only interior positive-frequency bins.
    hz = np.fft.rfftfreq(WINDOW, 0.001)
    masks = [(hz >= 12) & (hz <= 32),
             (hz >= 70) & (hz <= 150) & ((hz < 113.75) | (hz > 126.25))]
    return np.concatenate([np.log1p(power[..., m, :].sum(axis=-2)) for m in masks], axis=-1)


def cue_basis(digit, phase, seconds):
    """Source digits 1..5. Phase 0 is a visible cue; phase 1 is following blank."""
    s = np.asarray(seconds, dtype=np.float64)
    if digit not in range(1, 6) or phase not in (0, 1) or np.any(s < 0):
        raise ValueError('Expected a known digit and nonnegative time in the current phase')
    basis = np.zeros((*s.shape, 60))
    start = 6 * (phase * 5 + digit - 1)
    basis[..., start:start+6] = np.stack([np.ones_like(s), s] + [np.maximum(s-k, 0) for k in (0.4, 0.8, 1.2, 1.6)], axis=-1)
    return basis


def tokens_from_history(counts_280_by_46, glove_4_by_5, digit, phase, elapsed_ms):
    """One cutoff: ECoG [-279,0] ms; glove [-120,-80,-40,0] ms; current cue age."""
    counts = np.asarray(counts_280_by_46)
    glove = np.asarray(glove_4_by_5, dtype=np.float64)
    if counts.shape != (280, 46) or glove.shape != (4, 5) or not np.isfinite(glove).all() or not np.isfinite(counts).all():
        raise ValueError('Expected finite cortical count history (280,46) and glove history (4,5)')
    windows = np.stack([counts[i:i+WINDOW] for i in (0,40,80,120)])
    return np.concatenate([glove, cue_basis(digit, phase, (elapsed_ms + TOKEN_LAGS)/1000), band_features(windows)], axis=-1)


def standardize_fit(x):
    sd = x.std(axis=0)
    return x.mean(axis=0), np.where(sd < 1e-8, 1., sd)


def ridge_fit(tokens, y, name):
    x = tokens[..., FEATURES[name]].reshape(len(tokens), -1)
    mean, sd = standardize_fit(x)
    z = (x-mean)/sd
    residual = y if name == 'cue' else y-tokens[:, -1, GLOVE]
    intercept = residual.mean(axis=0)
    gram = z.T @ z
    gram.flat[::len(gram)+1] += 0.05 * len(x)
    weights = np.linalg.solve(gram, z.T @ (residual-intercept))
    return dict(mean=mean, sd=sd, intercept=intercept, weights=weights)


def ridge_predict(tokens, name, checkpoint):
    x = tokens[..., FEATURES[name]].reshape(len(tokens), -1)
    prediction = (x-checkpoint['mean'])/checkpoint['sd'] @ checkpoint['weights'] + checkpoint['intercept']
    if name != 'cue':
        prediction += tokens[:, -1, GLOVE]
    return prediction


def encoder():
    import torch
    from torch import nn

    class TemporalEncoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.project = nn.Linear(157, 24)
            self.pos = nn.Parameter(torch.zeros(4, 24))
            self.layer = nn.TransformerEncoderLayer(24, 2, 48, dropout=0., activation='gelu', batch_first=True)
            self.out = nn.Linear(24, 5)

        def forward(self, x):
            return self.out(self.layer(self.project(x) + self.pos)[:, -1])

    return TemporalEncoder()


def encoder_input(tokens, norm, aligned):
    import torch
    x = ((tokens-norm['mean'])/norm['sd']).astype(np.float32)
    if not aligned:
        x[..., BRAIN] = 0
    return torch.from_numpy(x)


def encoder_fit(tokens, y, aligned):
    import torch
    torch.manual_seed(319)
    net = encoder()
    residual = y-tokens[:, -1, GLOVE]
    # Per-feature normalization across all observed training tokens.
    mean, sd = standardize_fit(tokens.reshape(-1, tokens.shape[-1]))
    ym, ys = standardize_fit(residual)
    norm = dict(mean=mean, sd=sd, ym=ym, ys=ys)
    x = encoder_input(tokens, norm, aligned)
    target = torch.tensor((residual-ym)/ys, dtype=torch.float32)
    opt = torch.optim.AdamW(net.parameters(), lr=.001, weight_decay=.01)
    generator = torch.Generator().manual_seed(319)
    for _ in range(24):
        for idx in torch.randperm(len(x), generator=generator).split(128):
            opt.zero_grad(set_to_none=True)
            loss = torch.nn.functional.mse_loss(net(x[idx]), target[idx])
            loss.backward()
            opt.step()
    return {**norm, **{f'param.{k}': v.detach().cpu().numpy() for k,v in net.state_dict().items()}}


def encoder_predict(tokens, aligned, checkpoint):
    import torch
    net = encoder()
    net.load_state_dict({k[6:]: torch.from_numpy(v.copy()) for k,v in checkpoint.items() if k.startswith('param.')})
    net.eval()
    with torch.inference_mode():
        x = encoder_input(tokens, checkpoint, aligned)
        vec = torch.cat([net(chunk) for chunk in x.split(128)]).numpy()
    return tokens[:, -1, GLOVE] + vec * checkpoint['ys'] + checkpoint['ym']


def load_checkpoint(path):
    with np.load(Path(path), allow_pickle=False) as archive:
        return {k: archive[k] for k in archive.files}
