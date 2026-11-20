# SPDX-License-Identifier: CC0-1.0
"""Calibration, anatomical pooling and trial construction on the nominal 1 kHz grid."""
from collections import Counter
from dataclasses import dataclass

import numpy as np

REGIONS = (1, 2, 3, 4, 6, 7, 8, 9)
FINGERS = ('thumb', 'index', 'middle', 'ring', 'little')
PEOPLE = ('bp', 'cc', 'ht', 'jc', 'jp')
LAGS = np.array([-120, -80, -40, 0])
TICKS = 68
METHOD_HASH = 'cd65faff30d4071070d01d22eef0e8c4467613cfab0cb6ce031c9f2f11e68f2c'


class Ineligible(ValueError):
    """A prospectively specified admission condition was not met."""


def spectral(counts):
    """Compute [token, band, contact] log powers from raw 160-row windows."""
    uv = np.asarray(counts, dtype=np.float64) * .0298
    if uv.ndim != 3 or uv.shape[1] != 160 or uv.shape[2] < 1 or not np.isfinite(uv).all():
        raise ValueError('Need finite [token,160,contact] windows of amplifier counts')
    uv -= uv.mean(axis=2, keepdims=True)
    uv -= uv.mean(axis=1, keepdims=True)
    taper = np.hanning(160)
    fft = np.fft.rfft(uv * taper[:, None], axis=1)
    power = np.abs(fft)**2 * (2 / (160 * (taper**2).sum()))
    hz = np.fft.rfftfreq(160, .001)
    bands = [(hz >= 12) & (hz <= 32),
             (hz >= 70) & (hz <= 150) & ((hz < 113.75) | (hz > 126.25))]
    return np.stack([np.log1p(power[:, band].sum(axis=1)) for band in bands], axis=1)


def bands_at(voltage, ticks):
    if ticks.min() < 159 or ticks.max() >= len(voltage):
        raise ValueError('Voltage support crosses the recording')
    return np.concatenate([spectral(voltage[b[:, None] + np.arange(-159, 1)])
                           for b in np.array_split(ticks, (len(ticks) + 63) // 64)])


def pool(bands, codes, cal):
    codes = np.asarray(codes)
    mu, sd = np.asarray(cal['mean']), np.asarray(cal['sd'])
    if (codes.ndim != 1 or mu.shape != (2, len(codes)) or sd.shape != mu.shape
            or bands.shape[-2:] != mu.shape or not np.isfinite(mu).all()
            or not np.isfinite(sd).all() or np.any(sd <= 0)):
        raise ValueError('Expected calibration mean and positive SD in band by original-contact order')
    z = (bands - mu) / sd
    values = np.zeros((*z.shape[:-2], 2, len(REGIONS)))
    masks = []
    for i, code in enumerate(REGIONS):
        take = codes == code
        masks.append(take.any())
        if take.any():
            values[..., i] = z[..., take].mean(axis=-1)
    masks.append((~np.isin(codes, REGIONS)).any())
    return np.concatenate([values.reshape(*z.shape[:-2], 16),
                           np.broadcast_to(masks, (*z.shape[:-2], 9))], axis=-1)


def cue_features(digit, phase, seconds):
    if digit not in range(1, 6) or phase not in (0, 1) or np.any(seconds < 0):
        raise ValueError('Expected named source finger and valid time in its display or blank phase')
    x = np.zeros((*seconds.shape, 60))
    k = 6 * (5 * phase + digit - 1)
    x[..., k:k+6] = np.stack([np.ones_like(seconds), seconds]
                              + [np.maximum(seconds - v, 0) for v in (.4, .8, 1.2, 1.6)], axis=-1)
    return x


def packet(raw_280, codes, calibration, digit, phase, elapsed_ms):
    """One calibrated 85-column packet. Only electrical observations and task context enter."""
    raw_280 = np.asarray(raw_280)
    if raw_280.shape != (280, len(codes)):
        raise ValueError('Need 280 consecutive amplifier rows, ending at cutoff')
    windows = np.stack([raw_280[offset:offset+160] for offset in (0, 40, 80, 120)])
    return np.concatenate([cue_features(digit, phase, (elapsed_ms + LAGS) / 1000),
                           pool(spectral(windows), codes, calibration)], axis=-1)


def trials(cue, bounds, grid_origin=0):
    """Yield complete cue + blank pairs and their cutoffs, in source order."""
    changes = np.r_[0, 1 + np.flatnonzero(cue[1:] != cue[:-1])]
    for i in range(1, len(changes)-2):
        start, blank, end = map(int, changes[i:i+3])
        digit = int(cue[start])
        if start < bounds[0] or end > bounds[1] or digit not in range(1, 6) or cue[blank] != 0:
            continue
        grids = []
        for a, b in [(start, blank), (blank, end)]:
            grid = grid_origin + ((a - grid_origin + 39) // 40 + np.arange(9, 43)) * 40
            if grid[0] - 279 < a or grid[-1] + 160 >= b:
                break
            grids.append(grid)
        if len(grids) == 2:
            yield digit, start, blank, end, np.concatenate(grids)


def movement(glove, cut, timestamps):
    """Glove is paired with an explicit nominal 25-Hz timestamp per row."""
    wanted = cut[:, None] + np.arange(40, 161, 40)
    idx = np.searchsorted(timestamps, wanted)
    if np.any(idx >= len(timestamps)) or not np.array_equal(timestamps[idx], wanted):
        raise ValueError('Missing required nominal glove sample')
    samples = glove[idx].astype(np.float64)
    if not np.isfinite(samples).all():
        raise ValueError('Non-finite glove calibration or scored observation')
    return np.abs(np.diff(samples, axis=1)).mean(axis=1)


def calibrate(voltage, glove, times, calibration_trials):
    """Fit the local input/output scales once, strictly on supplied calibration trials."""
    if len(calibration_trials) < 10:
        raise Ineligible('Fewer than ten complete calibration trials')
    cuts = np.concatenate([t[4] for t in calibration_trials])
    endpoints = np.unique(cuts[:, None] + LAGS)
    bands = bands_at(voltage, endpoints)
    sd = bands.std(axis=0)
    y = movement(glove, cuts, times)
    return {'mean': bands.mean(axis=0), 'sd': np.where(sd < 1e-8, 1., sd),
            'gain': np.maximum(1., np.sqrt((y*y).mean(axis=0)))}


@dataclass
class Person:
    x: np.ndarray           # trial, tick, token, feature; includes donor-only trials
    y: np.ndarray           # normalized trial, tick, digit
    cal: dict
    cues: np.ndarray        # original 1..5
    recipients: np.ndarray
    donors: np.ndarray      # matched previous trial for each recipient
    quartets: np.ndarray    # recipient-space indices for trials 2 and 4
    support: dict


def prepare(person, source):
    if person not in PEOPLE:
        raise ValueError('Unknown development participant')
    voltage = source['voltage']
    times = np.asarray(source['time_ms']).ravel()
    glove, cue = np.asarray(source['target']), np.asarray(source['cue']).ravel()
    codes = np.asarray(source['region']).ravel()
    limit = min(len(voltage), 236000) if person == 'bp' else len(voltage)
    voltage, cue = voltage[:limit], cue[:limit]
    if len(cue) != limit or voltage.ndim != 2 or len(codes) != voltage.shape[1]:
        raise Ineligible('Missing aligned voltage, cue or contact map')
    if times.size == 0 or not np.all(np.diff(times) == 40) or not (0 <= times[0] < 40):
        raise Ineligible('Unverified nominal 25 Hz grid')
    if glove.ndim != 2 or glove.shape[1] != 5:
        raise Ineligible('Five aligned glove columns unavailable')
    if len(glove) == len(source['voltage']):
        glove = glove[times[times < limit]]
    elif len(glove) == len(times):
        glove = glove[times < limit]
    else:
        raise Ineligible('Glove dimensions disagree with nominal timestamp vector')
    times = times[times < limit]
    calibration_trials = list(trials(cue, (0, 80000), times[0]))
    post = list(trials(cue, (88000, limit), times[0]))
    cues = np.array([t[0] for t in post])
    if set(cues) != set(range(1, 6)):
        raise Ineligible('Post-guard interval does not contain all five supported cues')
    recipient, donors, last = [], [], {}
    for i, digit in enumerate(cues):
        if digit in last:
            recipient.append(i)
            donors.append(last[digit])
        last[digit] = i
    recipient_index = {i: j for j, i in enumerate(recipient)}
    pairs = []
    for digit in range(1, 6):
        ix = np.flatnonzero(cues == digit)
        for start in range(0, len(ix)-3, 4):
            pairs.append([recipient_index[ix[start+1]], recipient_index[ix[start+3]]])
    if not pairs:
        raise Ineligible('No complete same-cue quartet')
    cal = calibrate(voltage, glove, times, calibration_trials)
    packets, targets = [], []
    for digit, start, blank, _, cut in post:
        ends = cut[:, None] + LAGS
        unique, inverse = np.unique(ends, return_inverse=True)
        cortex = pool(bands_at(voltage, unique), codes, cal)[inverse.reshape(ends.shape)]
        basis = np.concatenate([cue_features(digit, phase, (ticks-onset)/1000) for phase, (ticks, onset)
                                in enumerate(zip(np.split(ends, 2), [start, blank]))])
        packets.append(np.concatenate([basis, cortex], axis=-1))
        targets.append(movement(glove, cut, times) / cal['gain'])
    counts = np.array([Counter(cues)[digit] for digit in range(1, 6)], dtype=int)
    support = {'prefix_rows': limit, 'calibration_trials': len(calibration_trials),
               'eligible_later_trials_by_cue': counts.tolist(), 'recipient_trials': len(recipient),
               'quartets_by_cue': (counts//4).tolist(), 'unused_quartet_trials_by_cue': (counts%4).tolist()}
    return Person(np.array(packets, dtype=np.float32), np.array(targets), cal, cues,
                  np.array(recipient), np.array(donors), np.array(pairs), support)
