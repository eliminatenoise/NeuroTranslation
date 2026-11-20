"""Source-bound examples, participant-balanced summaries and frozen decisions."""
from dataclasses import dataclass
from hashlib import sha256
import json
from math import comb
from pathlib import Path
import numpy as np

from portable import METHODS, predict_all

DEV = ('A01', 'A02', 'A03', 'A04')
HELD = ('A05', 'A06', 'A07', 'A08')
PROTOCOL = 'f7ee4e500e860dff3ef8bdd04932b8dbd5019cf73020ef3386d634023980dfe4'
HERE = Path(__file__).resolve().parent


def digest(path):
    h = sha256()
    with path.open('rb') as src:
        for block in iter(lambda: src.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.writing')
    tmp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
    tmp.replace(path)


@dataclass
class Trial:
    length: np.ndarray
    angle: np.ndarray
    target: np.ndarray
    cutoff_row: np.ndarray
    candidate_count: int
    source: dict


def windows(row, label, segment, length, angle):
    row, label, segment, length, angle = map(np.asarray, (row, label, segment, length, angle))
    if row.ndim != 1 or any(a.shape != row.shape for a in (label, segment, length, angle)):
        raise ValueError('Mismatched native knot arrays')
    if not np.issubdtype(row.dtype, np.integer) or not np.issubdtype(segment.dtype, np.integer):
        raise ValueError('Expected integral source rows and segment IDs')
    if not len(row) or np.any(row < 1) or np.any(np.diff(row) <= 0):
        raise ValueError('Original source rows must increase')
    # Enumerate by native row ordinal even if an unqualified row was omitted.
    cutrows = np.arange(21, int(row[-1]) - 9, 10)
    loc = np.searchsorted(row, cutrows)
    loc = loc[(row[loc] == cutrows) & (loc >= 20) & (loc + 10 < len(row))]
    ix = loc[:, None] + np.arange(-20, 11)
    valid = np.all(np.diff(row[ix], axis=1) == 1, axis=1)
    valid &= (segment[loc] >= 0) & np.all(segment[ix] == segment[loc, None], axis=1)
    valid &= np.all(np.isfinite(label[ix]), axis=1) & np.all(np.diff(label[ix], axis=1) > 0, axis=1)
    valid &= np.all(np.isfinite(length[ix]) & np.isfinite(angle[ix]), axis=1)
    ix = ix[valid]
    if not len(ix):
        raise ValueError('Trial has no contiguous supported windows')
    return Trial(length[ix[:, :21]], angle[ix[:, :20]], length[ix[:, -1]] - length[ix[:, 20]],
                 row[ix[:, 20]], len(cutrows), {})


def donor_ranks(n, m):
    if min(n, m) < 1:
        raise ValueError('Both recordings must have eligible cutoffs')
    if n == 1:
        return np.zeros(1, dtype=int)
    j = np.arange(n, dtype=np.int64)
    return (2*j*(m-1) + n-1) // (2*(n-1))


def score_person(model, trials):
    if len(trials) != 2:
        raise ValueError('Two distinct qualified trials required')
    diagnostics = []
    for t, donor in (trials, trials[::-1]):
        ix = donor_ranks(len(t.target), len(donor.target))
        forecasts = predict_all(model, t.length, t.angle, donor.angle[ix])
        errors, counts = {}, {}
        for name, pred in forecasts.items():
            usable = np.isfinite(pred)
            if name != 'projection' and not np.all(usable):
                raise ValueError('Nonfinite primary forecast')
            errors[name] = float(np.mean(np.abs(pred[usable] - t.target[usable]))) if np.any(usable) else None
            counts[name] = int(np.sum(usable))
        diagnostics.append({'mae_mm': errors, 'score_counts': counts, 'candidates': t.candidate_count,
                            'eligible': len(t.target), 'source': t.source})
    means = {m: float(np.mean([r['mae_mm'][m] for r in diagnostics])) if all(r['mae_mm'][m] is not None for r in diagnostics)
             else None for m in METHODS}
    return {'mae_mm': means, 'trials': diagnostics}


def summarize(people):
    if len(people) != 4:
        raise ValueError('Study decisions require four complete people')
    rows = list(people.values())
    scores = {m: float(np.mean([r['mae_mm'][m] for r in rows])) if all(r['mae_mm'][m] is not None for r in rows)
              else None for m in METHODS}
    pairs = {}
    for method, alternatives in (('length', ('zero', 'recent', 'typical', 'ridge')),
                                 ('full', ('zero', 'recent', 'typical', 'ridge', 'length', 'wrong'))):
        for base in alternatives:
            gain = np.array([r['mae_mm'][base] - r['mae_mm'][method] for r in rows])
            wins, losses = int(sum(gain > 0)), int(sum(gain < 0))
            n = wins + losses
            p = min(1., 2 * sum(comb(n, k) for k in range(min(wins, losses)+1)) / 2**n) if n else 1.
            pairs[method + '_vs_' + base] = {'mean_gain_mm': float(gain.mean()), 'gain_range_mm': [float(gain.min()), float(gain.max())],
                'people_improved': wins, 'people_tied': 4 - n, 'two_sided_exact_sign_p': p,
                'passes': bool(gain.mean() > 0 and wins >= 3)}
    return {'people': 4, 'trials': 8, 'eligible_windows': sum(t['eligible'] for r in rows for t in r['trials']),
            'candidate_windows': sum(t['candidates'] for r in rows for t in r['trials']),
            'projection_windows': sum(t['score_counts']['projection'] for r in rows for t in r['trials']),
            'mae_mm': scores, 'comparisons': pairs, 'length_beats_zero_and_recent': all(pairs['length_vs_'+b]['passes'] for b in ('zero','recent')),
            'length_beats_typical_and_ridge': all(pairs['length_vs_'+b]['passes'] for b in ('typical','ridge')),
            'pennation_increment_supported': all(v['passes'] for k,v in pairs.items() if k.startswith('full_vs_'))}


def load_person(cache, person):
    if person not in DEV + HELD:
        raise ValueError('Person is outside the authorized split')
    trials = []
    for trial in (1, 2):
        prefix = cache / person / ('trial-' + str(trial))
        receipt_path = prefix.with_suffix('.source.json')
        r = json.loads(receipt_path.read_text())
        expected_member = f'Task 3/Sub_{person}/{person}_echo_emg_angle_PA_FL_trial{trial}.mat'
        if (r.get('qualified') is not True or r.get('person') != person or r.get('trial') != trial or
                r.get('dataset') != '10.6019/S-BIAD1482' or r.get('member') != expected_member):
            raise ValueError(f'Unqualified or misidentified source {person}, trial {trial}')
        file = prefix.with_suffix('.knots.npz')
        if digest(file) != r['npz_sha256'] or digest(prefix.with_suffix('.mat')) != r['sha256']:
            raise ValueError('Source member or exported knots changed')
        keys = ['tracking_row', 'tracker_time', 'segment_id', 'length_mm', 'angle_deg']
        with np.load(file, allow_pickle=False) as pack:
            if set(pack.files) != set(keys):
                raise ValueError('Unexpected export keys')
            data = [pack[k] for k in keys]
        if any(sha256(a.tobytes()).hexdigest() != r['array_sha256'][k] for k, a in zip(keys, data)):
            raise ValueError('Array digest mismatch')
        t = windows(*data)
        t.source = {'member': expected_member, 'mat_sha256': r['sha256'], 'npz_sha256': r['npz_sha256'],
                    'receipt_sha256': digest(receipt_path), 'rows': len(data[0])}
        trials.append(t)
    if trials[0].source['mat_sha256'] == trials[1].source['mat_sha256']:
        raise ValueError('Donor trial is the same recording')
    return trials
