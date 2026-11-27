"""Input adapter: decoded C3D walk -> history-only issue rows and, separately, their targets.

Protocol section 6. Ported from the earlier native-clock adapter and the six-name selected-column
reader of the Van Criekinge fit cache (read only; their sha256 values are in PROTOCOL.json). The
gate G1 checks this port bit for bit on the 36 earlier fit walks.

Issue ticks t = 199 + 20 k on the stored 1,000 Hz analog index, every t with a full 200 ms history.
Each tick gives one row for plate 1 and one for plate 2 (tick-major, plate-minor order).
Inputs use samples through t only (the earlier-EMG window ends at t - 500). Targets use samples after
t and are written to a separate array set, so an issuing process never needs to see them.
"""
import numpy as np

import c3dread

HZ = 1000
BIN = 20
HISTORY = 200
EARLY = 500
HORIZON = 100
DWELL = 20
UNLOAD_N = 10
LOAD_N = 20
UNKNOWN, UNLOADED, PENDING, LOADED = range(4)
GRID24_ROWS = 48

INPUT_FIELDS = {
    'member_index': ('int64', ()), 'issue_tick': ('int64', ()), 'plate': ('int64', ()),
    'emg_rms_v': ('float64', (10, 6)), 'early_emg_rms_v': ('float64', (10, 6)),
    'past_force_n': ('float64', (10,)), 'other_force_n': ('float64', (10,)),
    'emg_ok': ('bool', ()), 'early_emg_ok': ('bool', ()), 'past_force_ok': ('bool', ()),
    'other_force_ok': ('bool', ()), 'state_at_issue': ('int8', ()), 'grid24': ('bool', ()),
}
TARGET_FIELDS = {
    'member_index': ('int64', ()), 'issue_tick': ('int64', ()), 'plate': ('int64', ()),
    'event_new_load': ('float64', ()), 'signed_impulse_ns': ('float64', ()),
    'onset_tick': ('int64', ()), 'negative_issue_state': ('int8', ()),
}
KEYS = ('member_index', 'issue_tick', 'plate')


def read_walk(data, expanded_bytes=None):
    """Whitelist-parse a decoded walk, require class Q6, return six EMG streams (V) and plates 1-2 (N, up)."""
    buffer = memoryview(data)
    parsed = c3dread.parse(bytes(buffer[:65536 * 4]) if len(buffer) > 65536 * 4 else bytes(buffer))
    verdict, reasons, lay, _ = c3dread.layout(parsed, len(data) if expanded_bytes is None else expanded_bytes)
    if verdict != 'Q6':
        raise c3dread.ReadError('walk-not-Q6:' + ','.join(reasons))
    selected = c3dread.read_columns(buffer, lay, (*lay['emg_columns'], *lay['force_z_columns']))
    force = selected[:, 6:] * c3dread.plate_normal_z(lay)
    return selected[:, :6], force


def force_state(force, valid):
    """Per-sample plate state and confirmed (crossing, confirmation) pairs; causal by construction."""
    states = np.zeros(force.shape, dtype=np.int8)
    events = []
    for plate, (signal, good) in enumerate(zip(force.T, valid.T)):
        state, run, crossing = UNKNOWN, 0, -1
        column = []
        for tick, (value, ok) in enumerate(zip(signal.tolist(), good.tolist())):
            if not ok:
                state, run, crossing = UNKNOWN, 0, -1
            elif state == UNKNOWN or state == LOADED:
                run = run + 1 if -UNLOAD_N <= value <= UNLOAD_N else 0
                if run == DWELL:
                    state = UNLOADED
            elif state == UNLOADED:
                if value >= LOAD_N:
                    state, crossing = PENDING, tick
            elif value < LOAD_N:
                state, crossing = UNLOADED, -1
            elif tick - crossing == DWELL - 1:
                column.append((crossing, tick))
                state, run = LOADED, 0
            states[tick, plate] = state
        events.append(np.asarray(column, dtype=np.int64).reshape(-1, 2))
    return states, events


def history(values, valid, end, rms):
    chunks = values[end - HISTORY + 1:end + 1].reshape(HISTORY // BIN, BIN, values.shape[1])
    support = valid[end - HISTORY + 1:end + 1].reshape(chunks.shape).all(axis=1)
    safe = np.where(np.isfinite(chunks), chunks, 0.)
    average = np.sqrt(np.square(safe).mean(axis=1)) if rms else safe.mean(axis=1)
    return np.where(support, average, np.nan), support.all(axis=0)


def issue_ticks(n):
    return np.arange(HISTORY - 1, n, BIN, dtype=np.int64)


def grid24_ticks(n):
    """Published 24-position replay schedule; empty when the walk has fewer than 24 eligible ticks."""
    eligible = np.arange(199, n - 119, 20, dtype=np.int64)
    if len(eligible) < GRID24_ROWS // 2:
        return np.zeros(0, dtype=np.int64)
    starts = np.arange(8) * (len(eligible) - 3) // 7
    ranks = (starts[:, None] + np.arange(3)).ravel()
    if len(np.unique(ranks)) != 24 or ranks[0] != 0 or ranks[-1] != len(eligible) - 1:
        return np.zeros(0, dtype=np.int64)
    return eligible[ranks]


def issue_inputs(emg, force, member_index):
    """History-only rows. emg (n, 6) volts, force (n, 2) upward newtons on plates 1 and 2."""
    emg = np.asarray(emg, dtype=np.float64)
    force = np.asarray(force, dtype=np.float64)
    if emg.shape != (len(force), 6) or force.shape != (len(emg), 2):
        raise ValueError('expected six EMG streams and two plate streams on one clock')
    ev, fv = np.isfinite(emg), np.isfinite(force)
    ticks = issue_ticks(len(force))
    width = 2 * len(ticks)
    out = {k: np.zeros((width, *shape), dtype=dtype) for k, (dtype, shape) in INPUT_FIELDS.items()}
    for k in ('emg_rms_v', 'early_emg_rms_v', 'past_force_n', 'other_force_n'):
        out[k][:] = np.nan
    states, _ = force_state(force, fv)
    grid = set(grid24_ticks(len(force)).tolist())
    for i, tick in enumerate(ticks.tolist()):
        pair = slice(2 * i, 2 * i + 2)
        volts, names_ok = history(emg, ev, tick, True)
        means, plate_ok = history(force, fv, tick, False)
        out['emg_rms_v'][pair] = volts
        out['emg_ok'][pair] = names_ok.all()
        out['past_force_n'][pair] = means.T
        out['past_force_ok'][pair] = plate_ok
        out['other_force_n'][pair] = means.T[::-1]
        out['other_force_ok'][pair] = plate_ok[::-1]
        if tick >= HISTORY - 1 + EARLY:
            volts, names_ok = history(emg, ev, tick - EARLY, True)
            out['early_emg_rms_v'][pair] = volts
            out['early_emg_ok'][pair] = names_ok.all()
        out['state_at_issue'][pair] = states[tick]
        out['grid24'][pair] = tick in grid
    out['member_index'][:] = member_index
    out['issue_tick'][:] = np.repeat(ticks, 2)
    out['plate'][:] = np.tile([1, 2], len(ticks))
    return out


def issue_targets(force, member_index):
    """Signed 100 ms impulse (N s) and new-load label for every issue row; uses samples after t."""
    force = np.asarray(force, dtype=np.float64)
    ticks = issue_ticks(len(force))
    good = np.isfinite(force)
    states, events = force_state(force, good)
    shape = (len(ticks), 2)
    new = np.full(shape, np.nan)
    impulse = np.full(shape, np.nan)
    onset = np.full(shape, -1, dtype=np.int64)
    negative = np.full(shape, UNKNOWN, dtype=np.int8)
    for row, tick in enumerate(ticks.tolist()):
        start, stop = tick + 1, tick + HORIZON + 1
        if stop <= len(force):
            present = good[start:stop].all(axis=0)
            impulse[row, present] = force[start:stop, present].sum(axis=0) / HZ
        for plate, observed in enumerate(events):
            state = states[tick, plate]
            if state not in (LOADED, UNLOADED):
                continue
            candidate = observed[np.searchsorted(observed[:, 0], start):]
            if len(candidate) and candidate[0, 0] < stop:
                first, confirmation = candidate[0]
                if good[start:confirmation + 1, plate].all():
                    new[row, plate], onset[row, plate] = 1., first
            elif stop + DWELL - 1 <= len(force) and good[start:stop + DWELL - 1, plate].all():
                new[row, plate], negative[row, plate] = 0., state
    return {'member_index': np.full(2 * len(ticks), member_index, dtype=np.int64),
            'issue_tick': np.repeat(ticks, 2), 'plate': np.tile(np.array([1, 2], dtype=np.int64), len(ticks)),
            'event_new_load': new.ravel(), 'signed_impulse_ns': impulse.ravel(),
            'onset_tick': onset.ravel(), 'negative_issue_state': negative.ravel()}


def walk_arrays(data, member_index, expanded_bytes=None):
    emg, force = read_walk(data, expanded_bytes)
    return issue_inputs(emg, force, member_index), issue_targets(force, member_index), len(force)


def concat(parts, fields):
    return {k: np.concatenate([p[k] for p in parts]) for k in fields}


def supports(inputs, targets):
    """Common support masks (protocol section 6): identical for every method."""
    same = all(np.array_equal(inputs[k], targets[k]) for k in KEYS)
    if not same:
        raise ValueError('inputs and targets are not aligned on the issue keys')
    common = inputs['emg_ok'] & inputs['past_force_ok']
    early = common & inputs['early_emg_ok']
    imp = np.isfinite(targets['signed_impulse_ns'])
    evt = np.isfinite(targets['event_new_load'])
    return {'impulse': common & imp, 'event': common & evt, 'impulse_early': early & imp, 'event_early': early & evt}


def input_valid(inputs):
    """Rows that receive a forecast: all six EMG channels and the target plate valid in all ten bins."""
    return inputs['emg_ok'] & inputs['past_force_ok']


def save_npz(path, arrays, fields):
    for k, (dtype, shape) in fields.items():
        a = arrays[k]
        if a.dtype != np.dtype(dtype) or a.shape[1:] != shape:
            raise ValueError(f'field {k} has dtype {a.dtype} shape {a.shape}')
    with open(path, 'xb') as stream:
        np.savez(stream, **{k: arrays[k] for k in fields})


def load_npz(path, fields):
    with np.load(path, allow_pickle=False) as z:
        if set(z.files) != set(fields):
            raise ValueError(f'unexpected members in {path}')
        return {k: z[k] for k in fields}
