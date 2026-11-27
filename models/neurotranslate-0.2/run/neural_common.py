"""Features, shards and counts of the neural part of P2 (spikes and field groups, plus the shared groups).

Step clock as in common.py: step k covers [20k, 20k + 20) ms of a recording and becomes available at its
end; a sample at time t belongs to step floor(t / 0.02). Every feature uses samples inside or before
its step.

Groups and features (PROTOCOL.json representation.features):
  spikes 1 feature : count of spike events of the unit (or electrode) inside the step; raw counts
  field  9 features: causal log band power over the trailing 100 ms and the trailing 200 ms in
                     4-8, 8-13, 13-30 and 70-150 Hz (eight features: bp100_* then bp200_*), and the last
                     value of a causal 10 Hz low-pass (lp10_last). Band-pass and low-pass filters are
                     4th-order Butterworth sections run forward only (scipy sosfilt), started from the
                     first sample of each finite run. The power is the mean of the squared filtered
                     signal over the samples inside (step end - W, step end]; its natural log is stored.
                     The 70-150 Hz features are masked where the sampling rate is below 400 Hz. A field
                     value is present only if every sample it uses is finite and its window starts at
                     least WARMUP_S after the start of the finite run (filter settling). The inner folds
                     choose 100 or 200 ms later; both are stored.
  emg, kin, force  : as in common.py.
Field values are stored as float16 (natural-log power and microvolt-scale low-pass values; the
quantisation step is at most 2^-11 of the value, below 0.008 for |value| < 16) unless a dataset module sets
GROUP_DTYPES (a dataset whose stored scale puts values in the float16 subnormal range keeps float32); every
other group is stored as float32. The writer reports, per feature, the float16 error over each channel's SD. Shards are compressed .npz files; masks are per step, channel and feature.
"""
import json
import math
import os
from pathlib import Path

import numpy as np

import common

STEP_S = common.STEP_S
WINDOW_STEPS = common.WINDOW_STEPS
BANDS = [("theta", 4.0, 8.0), ("alpha", 8.0, 13.0), ("beta", 13.0, 30.0), ("high", 70.0, 150.0)]
FIELD_WINDOWS_S = [0.1, 0.2]
WARMUP_S = 0.5
HIGH_BAND_MIN_FS = 400.0
FIELD_FEATURES = ["bp%d_%s" % (int(w * 1000), b[0]) for w in FIELD_WINDOWS_S for b in BANDS] + ["lp10_last"]
GROUP_FEATURES = dict(common.GROUP_FEATURES)
GROUP_FEATURES.update({"spikes": ["count"], "field": FIELD_FEATURES})
GROUP_DTYPES = {"field": np.float16}
GROUP_ORDER = ["spikes", "field", "emg", "kin", "force"]

_SOS = {}


def _sos(kind, fs, f1=None, f2=None, order=4):
    from scipy.signal import butter
    key = (kind, float(fs), f1, f2, order)
    if key not in _SOS:
        if kind == "band":
            _SOS[key] = butter(order, [f1, f2], btype="bandpass", output="sos", fs=fs)
        else:
            _SOS[key] = butter(order, f1, btype="lowpass", output="sos", fs=fs)
    return _SOS[key]


def _finite_runs(fin):
    d = np.diff(np.concatenate([[0], fin.astype(np.int8), [0]]))
    return np.where(d == 1)[0], np.where(d == -1)[0]


def causal_sos(x, sos):
    """Forward-only filtering of each column, restarted at every finite run (state from its first sample)."""
    from scipy.signal import sosfilt, sosfilt_zi
    zi = sosfilt_zi(sos)
    x = np.asarray(x, np.float64)
    out = np.full_like(x, np.nan)
    fin = np.isfinite(x)
    if fin.all():
        z = zi[:, :, None] * x[0][None, None, :]
        out, _ = sosfilt(sos, x, axis=0, zi=z)
        return out
    for c in range(x.shape[1]):
        for s, e in zip(*_finite_runs(fin[:, c])):
            seg = x[s:e, c]
            y, _ = sosfilt(sos, seg, zi=zi * seg[0])
            out[s:e, c] = y
    return out


def run_start_index(fin):
    """For each sample, the index of the first sample of its finite run (or -1 if not finite). [n, C]"""
    n, C = fin.shape
    out = np.full((n, C), -1, np.int64)
    for c in range(C):
        for s, e in zip(*_finite_runs(fin[:, c])):
            out[s:e, c] = s
    return out


def field_features(x, fs, t0, n_steps):
    """field group for uniformly sampled x [n, C] (sample i at t0 + i/fs seconds). Returns val [S, C, 9]
    (float32, cast to float16 when the shard is written) and msk [S, C, 9]."""
    x = np.asarray(x, np.float64)
    n, C = x.shape
    S = n_steps
    F = len(FIELD_FEATURES)
    val = np.zeros((S, C, F), np.float32)
    msk = np.zeros((S, C, F), bool)
    if n == 0 or S == 0:
        return val, msk
    k = np.arange(1, S + 1, dtype=np.float64)
    t_end = k * STEP_S
    hi = np.clip(np.ceil((t_end - t0) * fs - 1e-6).astype(np.int64), 0, n)  # exclusive end sample of each step
    fin = np.isfinite(x)
    allfin = bool(fin.all())
    rs = None if allfin else run_start_index(fin)
    warm = int(math.ceil(WARMUP_S * fs))
    for bi, (bname, f1, f2) in enumerate(BANDS):
        if f2 >= fs / 2.0 or (bname == "high" and fs < HIGH_BAND_MIN_FS):
            continue
        y = causal_sos(x, _sos("band", fs, f1, f2))
        p = np.where(np.isfinite(y), y * y, 0.0)
        cs = np.vstack([np.zeros((1, C)), np.cumsum(p, axis=0)])
        cbad = np.vstack([np.zeros((1, C), np.int64), np.cumsum(~np.isfinite(y), axis=0)])
        for wi, W in enumerate(FIELD_WINDOWS_S):
            lo = np.clip(np.ceil((t_end - W - t0) * fs - 1e-6).astype(np.int64), 0, n)
            cnt = (hi - lo)
            ok_n = (cnt > 0) & (t_end - W - t0 >= -1e-9)
            m = (cs[hi] - cs[lo]) / np.maximum(cnt, 1)[:, None]
            bad = (cbad[hi] - cbad[lo]) > 0
            idx_last = np.clip(hi - 1, 0, n - 1)
            if allfin:
                warm_ok = (lo >= warm)[:, None]
            else:
                start = rs[idx_last]  # run start of the last sample in the window
                warm_ok = (start >= 0) & (lo[:, None] - start >= warm)
            ok = ok_n[:, None] & ~bad & warm_ok & (m > 0)
            fi = wi * len(BANDS) + bi
            val[:, :, fi] = np.where(ok, np.log(np.maximum(m, 1e-30)), 0.0)
            msk[:, :, fi] = ok
    lp = causal_sos(x, _sos("low", fs, 10.0))
    idx_last = hi - 1
    has = idx_last >= 0
    v = lp[np.clip(idx_last, 0, n - 1)]
    if allfin:
        warm_ok = (idx_last >= warm)[:, None]
    else:
        start = rs[np.clip(idx_last, 0, n - 1)]
        warm_ok = (start >= 0) & (idx_last[:, None] - start >= warm)
    ok = has[:, None] & np.isfinite(v) & warm_ok
    val[:, :, -1] = np.where(ok, v, 0.0)
    msk[:, :, -1] = ok
    # values outside the float16 range are masked rather than stored as infinity
    big = np.abs(val) > 60000.0
    if big.any():
        msk[big] = False
        val[big] = 0.0
    return val, msk


def spike_counts(times_list, n_steps, t0):
    """spikes group: counts per step for each unit's spike times (seconds on the recording clock with the
    recording origin t0). Spikes outside [t0, t0 + 0.02 S) are dropped. val [S, U, 1], msk [S, U, 1]."""
    U = len(times_list)
    val = np.zeros((n_steps, U, 1), np.float32)
    for u, t in enumerate(times_list):
        t = np.asarray(t, np.float64)
        k = np.floor((t - t0) / STEP_S + 1e-12).astype(np.int64)
        k = k[(k >= 0) & (k < n_steps)]
        if len(k):
            val[:, u, 0] = np.bincount(k, minlength=n_steps)[:n_steps]
    msk = np.ones((n_steps, U, 1), bool)
    return val, msk


class Rec:
    """Tokens of one recording: groups[g] = (val [S, C_g, F_g], msk). Channel lists may differ between
    recordings of different units for groups with per-recording rows (spikes); `channels` holds them."""

    def __init__(self, rec_id, unit, n_steps, meta=None):
        self.rec_id, self.unit, self.n_steps = rec_id, unit, int(n_steps)
        self.meta = dict(meta or {})
        self.groups = {}

    def put(self, group, val, msk):
        assert val.shape[0] >= self.n_steps and val.shape == msk.shape, (group, val.shape, msk.shape)
        assert val.shape[2] == len(GROUP_FEATURES[group])
        self.groups[group] = (val[:self.n_steps], msk[:self.n_steps])

    def step_present(self):
        p = np.zeros(self.n_steps, bool)
        for v, m in self.groups.values():
            p |= m.any(axis=(1, 2))
        return p


def write_shard(path, unit, recs, channel_counts, dtypes=None):
    """One compressed .npz per individual. channel_counts[g] = number of channels of group g for this unit
    (every recording of the unit has the same channel list per group). Missing groups are all-masked."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    offs = np.zeros(len(recs) + 1, np.int64)
    for i, r in enumerate(recs):
        offs[i + 1] = offs[i] + r.n_steps
    arrays = {"rec_offsets": offs, "rec_ids": np.array([r.rec_id for r in recs]), "unit": np.array(unit)}
    quant = {}
    for g in GROUP_ORDER:
        C = channel_counts.get(g, 0)
        if not C:
            continue
        F = len(GROUP_FEATURES[g])
        dt = (dtypes if dtypes is not None else GROUP_DTYPES).get(g, np.float32)
        val = np.zeros((offs[-1], C, F), dt)
        msk = np.zeros((offs[-1], C, F), bool)
        for i, r in enumerate(recs):
            if g in r.groups:
                v, m = r.groups[g]
                assert v.shape[1] == C, (g, v.shape, C)
                val[offs[i]:offs[i + 1]] = v.astype(dt)
                msk[offs[i]:offs[i + 1]] = m
        if dt == np.float16:
            bad = ~np.isfinite(val)
            if bad.any():
                msk[bad] = False
                val[bad] = 0
            quant[g] = float16_error(recs, g, val, msk, offs)
        val[~msk] = 0
        arrays[g + "_val"] = val
        arrays[g + "_msk"] = msk
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez_compressed(tmp, **arrays)
    os.replace(tmp, path)
    return common.sha256_file(path), path.stat().st_size, quant


def float16_error(recs, g, val16, msk, offs):
    """Storage check of a float16 group: per feature, the largest over channels of RMS(float16 - float32)
    divided by the channel's standard deviation over its present values (both over this unit's steps)."""
    out = []
    F = val16.shape[2]
    v32 = np.zeros(val16.shape, np.float32)
    for i, r in enumerate(recs):
        if g in r.groups:
            v32[offs[i]:offs[i + 1]] = r.groups[g][0]
    for f in range(F):
        worst = 0.0
        for c in range(val16.shape[1]):
            m = msk[:, c, f]
            if m.sum() < 2:
                continue
            a = v32[m, c, f].astype(np.float64)
            b = val16[m, c, f].astype(np.float64)
            sd = a.std()
            if sd > 0:
                worst = max(worst, float(np.sqrt(np.mean((a - b) ** 2)) / sd))
        out.append(worst)
    return out


def count_rec(r, chan_kinds, spikes_group="spikes"):
    """Counts used by MIXTURE-MANIFEST.json for one recording."""
    present = r.step_present()
    windows = r.n_steps // WINDOW_STEPS
    full = sum(1 for w in range(windows) if present[w * WINDOW_STEPS:(w + 1) * WINDOW_STEPS].all())
    chs = {}
    spikes = 0
    for g, (v, m) in r.groups.items():
        anyf = m.any(axis=2)
        for kind, idx in chan_kinds.get(g, {}).items():
            if len(idx):
                chs[g + ":" + kind] = float(anyf[:, idx].sum()) * STEP_S
        if g == spikes_group:
            spikes += int(round(float(v[..., 0].astype(np.float64).sum())))
    return {"steps": r.n_steps, "steps_with_data": int(present.sum()), "windows": windows,
            "windows_all_steps_with_data": full, "channel_seconds": chs, "spikes": spikes}


def kinds_of(channel_list):
    d = {}
    for i, c in enumerate(channel_list):
        d.setdefault(c.get("kind", "x"), []).append(i)
    return d


def time_blocks(t_start, t_stop, n_blocks=5, gap_s=1.0):
    """The protocol's time-block rule: [t_start, t_stop) cut into n equal blocks in time order; a gap of
    gap_s seconds is dropped at each internal boundary (half on each side). Returns [(fold, a, b)]."""
    edges = [t_start + (t_stop - t_start) * i / n_blocks for i in range(n_blocks + 1)]
    out = []
    for b in range(n_blocks):
        a = edges[b] + (gap_s / 2 if b > 0 else 0.0)
        e = edges[b + 1] - (gap_s / 2 if b < n_blocks - 1 else 0.0)
        out.append((b, a, e))
    return out


def json_safe(obj):
    return json.loads(json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
