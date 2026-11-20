"""Read the two assessment people, including the authors' saved 1 kHz copies where verified."""
import argparse
import io
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat, whosmat
from extract import (ALTERNATIVES, PAPER, PROCEDURE, TOL_S, digest, extract_record,
                     fetch_original, require, vector, write_atomic)

CHANNELS = {'time_s': ('time', 'time_new'), 'emg': ('emg_1', 'emg_1_new'),
            'load': ('loadcell_right', 'loadcell_right_new')}


def stored_rows(record, base):
    original = base.with_suffix('.mat')
    base.parent.mkdir(parents=True, exist_ok=True)
    fetch_original(record, original)
    inventory = {n: {'shape': list(s), 'class': kind} for n, s, kind in whosmat(original)}
    selected = {n for pair in CHANNELS.values() for n in pair}
    optional = (set(ALTERNATIVES.values()) | {'trig'}) & inventory.keys()
    data = loadmat(original, variable_names=sorted(selected | optional))
    require(selected <= data.keys(), 'Missing an original channel or its author-provided copy')
    raw = {key: vector(data, pair[0]) for key, pair in CHANNELS.items()}
    saved = {key: vector(data, pair[1]) for key, pair in CHANNELS.items()}
    raw_n, n = len(raw['time_s']), len(saved['time_s'])
    require(raw_n == 10 * (n - 1) + 1 and n > 1, 'Original and saved endpoint counts differ')
    for key in CHANNELS:
        require(len(raw[key]) == raw_n and len(saved[key]) == n, f'Unequal source grid for {key}')
        require(raw[key][::10].dtype == saved[key].dtype and
                raw[key][::10].tobytes() == saved[key].tobytes(),
                f'{key} saved samples differ from the original values at every tenth row')
    raw_step = np.diff(raw['time_s'])
    step = np.diff(saved['time_s'])
    require(np.all(np.abs(raw_step - .0001) <= TOL_S), 'Non-regular original 10 kHz grid')
    require(np.all(np.abs(step - .001) <= TOL_S), 'Non-regular saved 1 kHz grid')
    arrays = {k: digest(np.asarray(v, dtype='<f8').tobytes()) for k, v in saved.items()}
    if 'array_f64le_sha256' in record:
        require(arrays == record['array_f64le_sha256'], 'Saved-grid fingerprint differs')
    if 'rows' in record:
        require(record['rows'] == n, 'Saved-grid length differs')
    trigger = None
    if 'trig' in optional:
        trig = vector(data, 'trig')
        ix = np.flatnonzero((trig[1:] > 0) & (trig[:-1] <= 0)) + 1
        trigger = dict(rows=len(trig), rising_edges=len(ix),
                       first_rising_row_zero_based=int(ix[0]) if len(ix) else None,
                       spacing_in_rows=np.unique(np.diff(ix)).tolist())
    alternatives = {}
    for raw_name, other in ALTERNATIVES.items():
        if other in optional:
            x, y = vector(data, raw_name), vector(data, other)
            alternatives[other] = dict(rows=len(y), distinct_from=raw_name,
                                       equal_to_selected=bool(np.array_equal(x,y)))
    source = {k: record[k] for k in ('person','condition','trial','filename_category','member',
                                      'url','bytes','etag','sha256')}
    clock = {'source_field':'time_new','time_origin':'stored_regular_vector',
             'start_s':float(saved['time_s'][0]),'end_s':float(saved['time_s'][-1]),
             'nominal_rate_hz':1000,'observed_step_min_s':float(step.min()),'observed_step_max_s':float(step.max()),
             'non_nominal_stored_intervals':0,'interval_tolerance_s':TOL_S,
             'independent_hardware_timestamps':False,'hardware_dropped_samples_known':False}
    detail = {**source, 'representation':'author_stored_1khz_exact_every_tenth_raw_row',
              'rows':n,'samples':n,'time_origin':'stored_regular_vector','clock':clock,
              'array_f64le_sha256':arrays, 'source_fields':{k:v[1] for k,v in CHANNELS.items()},
              'raw_source_fields':{k:v[0] for k,v in CHANNELS.items()},
              'raw_clock':{'source_field':'time','rows':raw_n,'nominal_rate_hz':10000,
                           'start_s':float(raw['time_s'][0]),'end_s':float(raw['time_s'][-1]),
                           'observed_step_min_s':float(raw_step.min()),'observed_step_max_s':float(raw_step.max()),
                           'non_nominal_stored_intervals':0,'interval_tolerance_s':TOL_S},
              'copies_equal_to_every_tenth_raw_row':{k:True for k in saved},'first_source_row_zero_based':0,
              'finite_support':{k:int(np.isfinite(v).sum()) for k,v in saved.items()},
              'raw_finite_support':{k:int(np.isfinite(v).sum()) for k,v in raw.items()},
              'trigger_on_raw_grid':trigger,'alternative_channels_on_raw_grid':alternatives,
              'source_inventory':inventory,'procedure_url':PROCEDURE,'methods':PAPER,
              'unit':'native acquisition units for the conditioned EMG and right load-cell signals'}
    buf = io.BytesIO()
    np.savez(buf, **saved)
    write_atomic(base.with_suffix('.npz'),buf.getvalue())
    write_atomic(base.with_suffix('.source.json'),(json.dumps(detail,indent=2,allow_nan=False)+'\n').encode())
    return detail


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,required=True)
    args = p.parse_args()
    m = json.loads(Path(__file__).with_name('assessment-manifest.json').read_text())
    for group, fn in [('records', extract_record), ('author_grid_records', stored_rows)]:
        for rec in m[group]:
            stem = args.cache/rec['person']/f"{rec['condition']}-trial-{rec['trial']}"
            result = fn(rec,stem)
            print(stem, result['rows'], result.get('representation', result['time_origin']))
    for rec in m['unsupported_records']:
        stem = args.cache/rec['person']/f"{rec['condition']}-trial-{rec['trial']}"
        stem.parent.mkdir(parents=True, exist_ok=True)
        fetch_original(rec,stem.with_suffix('.mat'))
        require(not stem.with_suffix('.npz').exists(), f'Stale unsupported output in cache: {stem}.npz')
        write_atomic(stem.with_suffix('.source.json'),(json.dumps(rec,indent=2,allow_nan=False)+'\n').encode())
        print(stem, 'Original verified. No paired analysis arrays.', rec['reason'])

if __name__ == '__main__':
    main()
