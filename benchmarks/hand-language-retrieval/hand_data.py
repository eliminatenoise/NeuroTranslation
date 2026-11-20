"""Turn one HoloAssist recording into a gallery of right-hand action intervals."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
import json
from pathlib import Path

import numpy as np

from kit_components import digest, words

STEPS = 24
PAIRS = list(combinations([1, 5, 10, 15, 20, 25], 2))
CHANNELS = len(PAIRS) + 1


@dataclass
class Segment:
    key: str
    recording: str
    group: str
    captions: list
    sequence: np.ndarray
    duration: float
    context: float
    cue: tuple
    start: float
    end: float


def geometry(t, xyz, ticks, start, end):
    inside = np.flatnonzero((t >= start) & (t < end))
    if inside.size < 2:
        return None, 0
    times = t[inside]
    grid = start + ((np.arange(STEPS) + 0.5) / STEPS) * (end - start)
    right = np.minimum(np.searchsorted(times, grid), len(times) - 1)
    left = np.maximum(right - 1, 0)
    j = np.where(abs(times[left] - grid) <= abs(times[right] - grid), left, right)
    selected = inside[j]
    loc = xyz[selected].copy()
    loc[abs(t[selected] - grid) > .10] = np.nan
    distances = [np.linalg.norm(loc[:, a] - loc[:, b], axis=-1) for a, b in PAIRS]
    wrist = loc[:, 1]
    valid_wrist = np.flatnonzero(np.isfinite(wrist).all(axis=1))
    drift = np.full(STEPS, np.nan) if not len(valid_wrist) else np.linalg.norm(wrist - wrist[valid_wrist[0]], axis=1)
    seq = np.stack(distances + [drift], axis=1).astype(np.float32)
    usable = np.isfinite(seq).sum(axis=1) >= 8
    repeated = usable.sum() - len(set(ticks[selected[usable]].tolist()))
    if usable.sum() < 12 or len(set(ticks[selected[usable]].tolist())) < 2:
        return None, int(repeated)
    return seq, int(repeated)


def recording(root, row):
    base = root / row['role'] / row['recording']
    npz, note = base.with_suffix('.npz'), base.with_suffix('.json')
    meta = json.loads(note.read_text())
    if any(meta[k] != row[k] for k in ('recording','role','group')):
        raise ValueError(f'Record identity differs from source split: {base}')
    with np.load(npz, allow_pickle=False) as z:
        t, xyz, ticks = z['t'], z['xyz'], z['ticks']
        joint_ok = z['valid'].astype(bool) & z['tracked'].astype(bool) & z['active'][:, None].astype(bool)
        if xyz.shape != (len(t),26,3) or joint_ok.shape != xyz.shape[:2] or ticks.shape != t.shape:
            raise ValueError(f'Unexpected sensor dimensions: {base}')
        xyz = np.where((joint_ok & np.isfinite(xyz).all(-1))[:, :, None], xyz, np.nan)
    if len(t) == 0 or not np.isfinite(t).all() or (np.diff(t) < 0).any():
        raise ValueError(f'Invalid sync time: {base}')
    first = np.r_[True, np.diff(t) != 0]
    t, xyz, ticks = t[first], xyz[first], ticks[first]
    duration = float(meta['duration_s'])
    if not np.isfinite(duration) or duration <= 0:
        raise ValueError('Recording duration must be positive and finite')
    grouped = defaultdict(list)
    count = Counter(events=len(meta['events']), repeated_sync_rows=int((~first).sum()))
    for ev in meta['events']:
        a,b,s=ev['start'],ev['end'],ev['text']
        if not isinstance(s,str) or not words(s) or not (0 <= a < b and np.isfinite(b)):
            count['unusable_event'] += 1
            continue
        grouped[(float(a),float(b))].append(ev)
    segments = []
    for (a,b), events in sorted(grouped.items()):
        cap, labels = {}, set()
        for ev in events:
            cap.setdefault(tuple(words(ev['text'])), ev['text'])
            labels.add(tuple(' '.join(words(str(ev.get(k) or ''))) for k in ['verb','noun']))
        count['collapsed_same_interval_events'] += len(events)-1
        x, repeats = geometry(t, xyz, ticks, a, b)
        count['reused_ticks_in_usable_bins_over_intervals'] += repeats
        if x is None:
            count['insufficient_measurement_intervals'] += 1
            continue
        if segments and a < segments[-1].end:
            count['overlapping_intervals'] += 1
            continue
        label = next(iter(labels)) if len(labels) == 1 else ('','')
        label = label if all(label) else ('','')
        segments.append(Segment(f"{row['recording']}:{events[0]['id']}", row['recording'], row['group'],
                                list(cap.values()), x, b-a, (a+b)/(2*duration),label,a,b))
    if len(segments) < 2:
        count['intervals_in_gallery_below_two'] = len(segments)
        segments = []
    count['retained_segments'] = len(segments)
    return segments, dict(count), {npz.name:digest(npz),note.name:digest(note)}


def read_role(root, split, role):
    if role not in {'train','review'}:
        raise ValueError('Only train and review roles have payloads')
    rows=json.loads(Path(split).read_text())['recordings']
    group_roles, seen = {}, set()
    for r in rows:
        if (r['recording'] in seen or '/' in r['recording'] or '..' in r['recording'] or
                r['role'] not in {'train','review','reserve'} or
                group_roles.setdefault(r['group'],r['role']) != r['role']):
            raise ValueError('Inconsistent or unsafe split')
        seen.add(r['recording'])
    segments, ledger = [], {}
    for row in sorted((r for r in rows if r['role']==role),key=lambda r:r['recording']):
        items,counts,seals=recording(Path(root),row)
        segments.extend(items)
        ledger[row['recording']]={'counts':counts,'files':seals,'group':row['group']}
    if len({s.key for s in segments}) != len(segments) or not segments:
        raise ValueError('Missing or repeated segment keys')
    return segments,ledger
