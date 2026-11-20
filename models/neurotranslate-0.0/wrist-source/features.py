"""Build the four differential EMG amplitudes and the paired encoder rows."""
from dataclasses import dataclass, fields
import numpy as np

OFFSETS = np.array([384, 512, 640, 768, 896, 1024])
HISTORY = np.arange(-383,-127)
ANCHOR_LEAD = 128
VELOCITY_LEAD = 64
BIN_COUNT = BIN_WIDTH = 16

@dataclass(frozen=True)
class Rows:
    bins: np.ndarray
    anchor: np.ndarray
    past: np.ndarray
    target: np.ndarray
    slot: np.ndarray
    person: np.ndarray
    block: np.ndarray
    trial: np.ndarray

    @classmethod
    def join(cls, runs):
        return cls(**{
            field.name: np.concatenate([getattr(run, field.name) for run in runs])
            for field in fields(cls)
        })


def collect_rows(eeg, captured_emg, angles, valid, cues, returns, person, block):
    targets = cues[:, None] + OFFSETS
    histories = targets[:, :, None] + HISTORY
    bounded = ((histories[:, :, 0] >= cues[:, None]) &
               (targets < returns[:, None]) & (targets < len(angles))).all(axis=1)
    trial = np.flatnonzero(bounded)
    target_ticks = targets[trial]
    support = histories[trial]
    encoder_valid = valid[target_ticks].all(axis=(1, 2)) & valid[support].all(axis=(1, 2, 3))
    eeg_valid = np.isfinite(eeg[support]).all(axis=(1, 2, 3))
    emg_valid = np.isfinite(captured_emg[support]).all(axis=(1, 2, 3))
    keep = encoder_valid & eeg_valid & emg_valid
    target_ticks = target_ticks[keep].ravel()
    kept_trial = trial[keep]
    input_ticks = support[keep].reshape(len(target_ticks), len(HISTORY))
    anchor = angles[target_ticks - ANCHOR_LEAD]
    past = angles[target_ticks - ANCHOR_LEAD - VELOCITY_LEAD]
    motion = angles[input_ticks].reshape(-1, BIN_COUNT, BIN_WIDTH, 2).mean(axis=2)
    scalp = eeg[input_ticks].reshape(-1, BIN_COUNT, BIN_WIDTH, 8).mean(axis=2, dtype=np.float64)
    emg = captured_emg[input_ticks].astype(np.float64).reshape(-1, BIN_COUNT, BIN_WIDTH, 4, 2)
    differential = emg[..., 0] - emg[..., 1]
    rms = np.sqrt(np.mean(np.square(differential), axis=2))
    bins = np.concatenate((motion - anchor[:, None, :], rms, scalp), axis=2)
    if not np.isfinite(bins).all():
        raise ValueError("Nonfinite feature on eligible support")
    support_emg = captured_emg[np.unique(input_ticks)]
    at_rail = (support_emg == -32768) | (support_emg == 32767)
    exclusions = {
        "recorded": len(cues),
        "eligible": len(kept_trial),
        "outside_window": int((~bounded).sum()),
        "invalid_encoder": int((~encoder_valid).sum()),
        "nonfinite_eeg": int((~eeg_valid).sum()),
        "nonfinite_emg": int((~emg_valid).sum()),
        "invalid_on_bounded_joint_support": int((~keep).sum()),
        "emg_unique_feature_ticks": len(support_emg),
        "emg_rail_ticks_by_channel": at_rail.sum(axis=0).tolist(),
    }
    return Rows(
        bins, anchor, past, angles[target_ticks], np.tile(np.arange(len(OFFSETS)), len(kept_trial)),
        np.full(len(target_ticks), person), np.full(len(target_ticks), block),
        np.repeat(kept_trial, len(OFFSETS)),
    ), exclusions


