"""Score the three qualified trial groups from the unchanged specialist weights."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from data import contiguous, windows
from portable import features, predict_tokens

HERE = Path(__file__).resolve().parent
GROUPS = {
    'complete': ('One participant, both settings, both repetitions',
                 [('A04', setting, trial) for setting in ('angle0', 'angle5') for trial in (1, 2)]),
    'other_angle5': ('Other participant, angle5, both repetitions',
                     [('A03', 'angle5', trial) for trial in (1, 2)]),
    'other_angle0': ('Other participant, angle0, second repetition only', [('A03', 'angle0', 2)]),
}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def load_source(cache, manifest):
    records = {}
    for group in ('records', 'author_grid_records'):
        for row in manifest[group]:
            person, setting, trial = (row[k] for k in ('person', 'condition', 'trial'))
            base = cache/person/f'{setting}-trial-{trial}'
            receipt = json.loads(base.with_suffix('.source.json').read_bytes())
            for key in ('person', 'condition', 'trial', 'member', 'sha256', 'rows', 'array_f64le_sha256'):
                if row[key] != receipt[key]:
                    raise ValueError(f'Source receipt differs for {key} in {base.name}')
            suffix = '_new' if group == 'author_grid_records' else ''
            if receipt['source_fields'] != {'time_s':'time'+suffix, 'emg':'emg_1'+suffix, 'load':'loadcell_right'+suffix}:
                raise ValueError('Unexpected source channel identity')
            with np.load(base.with_suffix('.npz'), allow_pickle=False) as source:
                arrays = {k:np.asarray(source[k],dtype=np.float64) for k in ('time_s','load','emg')}
            for name, values in arrays.items():
                if values.shape != (row['rows'],) or digest(np.ascontiguousarray(values,dtype='<f8').tobytes()) != row['array_f64le_sha256'][name]:
                    raise ValueError(f'Source array differs for {name} in {base.name}')
            records[person, setting, trial] = arrays
    if set(records) != {item for _, trials in GROUPS.values() for item in trials}:
        raise ValueError('Unexpected trial roster')
    return records


def unpaired_windows(record, setting):
    load, emg, clock = (record[k] for k in ('load','emg','time_s'))
    cutoffs = np.array([i for i in range(200,len(load)-100,100)
                        if contiguous(clock[i-200:i+101]) and np.isfinite(load[i+100])
                        and np.isfinite(load[i-200:i+1]).all() and np.isfinite(emg[i-200:i+1]).all()])
    if not len(cutoffs):
        raise ValueError('No qualified recipient-only windows')
    idx = cutoffs[:, None] + np.arange(-200, 1)
    tokens = np.stack([features(l,e,setting) for l,e in zip(load[idx],emg[idx])])
    return {'x':tokens, 'recent':load[cutoffs]-load[cutoffs-100], 'y':load[cutoffs+100]-load[cutoffs]}


def summarize_trial(model, record, donor, setting):
    block = unpaired_windows(record, setting) if donor is None else windows(record, donor, 5*setting)[0]
    predictions = predict_tokens(model, block['x'], block['recent'], block.get('wrong'))
    errors = {name:values-block['y'] for name,values in predictions.items()}
    return len(block['y']), {name:{'mae':float(np.mean(abs(err))), 'mse':float(np.mean(err**2)), 'bias':float(np.mean(err))}
                             for name,err in errors.items()}


def combine(scores):
    return {name:{'mae':float(np.mean([row[name]['mae'] for row in scores])),
                  'rmse':float(np.sqrt(np.mean([row[name]['mse'] for row in scores]))),
                  'bias':float(np.mean([row[name]['bias'] for row in scores]))}
            for name in scores[0]}


def run(cache):
    seal = json.loads((HERE/'PRETEST-SHA256.json').read_bytes())
    for name, checksum in seal['unchanged_specialist_files'].items():
        if digest((HERE/name).read_bytes()) != checksum:
            raise ValueError(f'Frozen file has changed: {name}')
    manifest_bytes = (HERE/'source/assessment-manifest.json').read_bytes()
    if digest(manifest_bytes) != seal['public_source_documents']['assessment-manifest.json']:
        raise ValueError('Source qualification manifest has changed')
    records = load_source(cache, json.loads(manifest_bytes))
    model = json.loads((HERE/'model.json').read_bytes())
    groups = {}
    for group, (label, keys) in GROUPS.items():
        rows = []
        counts = {}
        for person, setting, trial in keys:
            key = person, setting, trial
            partner = records.get((person,setting,3-trial))
            n, summary = summarize_trial(model,records[key],partner,int(setting=='angle5'))
            counts[setting] = counts.get(setting,0)+n
            rows.append((setting,summary))
        scores = {'balanced':combine([row for _,row in rows])}
        for setting in counts:
            scores[setting] = combine([row for category,row in rows if category==setting])
        groups[group] = {'description':label,'people':1,'trials':len(keys),'windows':sum(counts.values()),
                         'windows_by_setting':counts,'has_wrong_trial':group!='other_angle0','scores':scores}
    return {'assessment_status':'incomplete','original_planned_people':2,'full_roster_gates':None,
            'qualified_trials':len(records),'qualified_windows':sum(g['windows'] for g in groups.values()),
            'wrong_comparable_windows':sum(g['windows'] for g in groups.values() if g['has_wrong_trial']),
            'horizon':'100 source-grid sample positions; 1 kHz nominal','unit':'right load channel, native units','groups':groups}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('output', type=Path, help='A new JSON file for the three descriptive groups')
    args = parser.parse_args()
    report = run(args.cache)
    with args.output.open('x') as fp:
        json.dump(report, fp, indent=2, allow_nan=False)
        fp.write('\n')
