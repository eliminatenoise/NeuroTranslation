# SPDX-License-Identifier: CC0-1.0
"""One causal feature packet for the five-sensor movement decoder."""
import numpy as np

TOKEN_LAGS = np.array([-120, -80, -40, 0])
WINDOW = 160

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


def packet(counts_280_by_46, digit, phase, elapsed_ms):
    """One invented or observed packet; columns 0..59 cue, 60..151 band powers."""
    counts = np.asarray(counts_280_by_46)
    if counts.shape != (280, 46) or not np.isfinite(counts).all():
        raise ValueError("Expected 280 finite amplifier-count rows from 46 ordered contacts")
    windows = np.stack([counts[i:i+WINDOW] for i in (0, 40, 80, 120)])
    cue = cue_basis(digit, phase, (elapsed_ms + TOKEN_LAGS)/1000)
    return np.concatenate([cue, band_features(windows)], axis=-1)
