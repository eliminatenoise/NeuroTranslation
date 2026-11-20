"""Recover the selected AnkleImage Task 1 recordings and their original signal rows."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
from scipy.io import loadmat, whosmat

ROOT_URL = 'https://ftp.ebi.ac.uk/biostudies/fire/S-BIAD/482/S-BIAD1482/Files/ScientificData/'
PAPER = 'https://doi.org/10.1038/s41597-024-04285-x'
PROCEDURE = ROOT_URL + 'Task%201/Manual%20labeling/mycom%20of%20PA%20and%20EMG.m'
RAW = ('emg_1', 'loadcell_right')
COPIES = {'time': 'time_new', 'emg_1': 'emg_1_new', 'loadcell_right': 'loadcell_right_new'}
ALTERNATIVES = {'emg_1': 'emg_2', 'loadcell_right': 'loadcell_left'}
STEP = .001
TOL_S = 1e-9


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_atomic(path, content):
    if path.is_file() and path.read_bytes() == content:
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        name = Path(handle.name)
        try:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            name.unlink(missing_ok=True)
            raise
    os.replace(name, path)


def fetch_original(record, target):
    if target.exists():
        content = target.read_bytes()
    else:
        url = ROOT_URL + quote(record['member'], safe='/')
        with urlopen(Request(url, method='HEAD', headers={'Accept-Encoding': 'identity'}), timeout=60) as response:
            require(response.status == 200 and response.url == url, 'Unexpected archive response')
            require(int(response.headers['Content-Length']) == record['bytes'], 'Source size changed')
            require(response.headers['ETag'] == record['etag'], 'Source ETag changed')
        headers = {'Accept-Encoding': 'identity', 'If-Match': record['etag']}
        with urlopen(Request(url, headers=headers), timeout=90) as response:
            require(response.status == 200 and response.url == url, 'Unexpected archive download')
            require(response.headers['ETag'] == record['etag'], 'Download ETag changed')
            content = response.read(record['bytes'] + 1)
    require(len(content) == record['bytes'] and digest(content) == record['sha256'],
            f"Source bytes differ from the fingerprint for {record['member']}")
    if not target.exists():
        write_atomic(target, content)


def vector(data, name):
    a = np.asarray(data[name])
    require(a.ndim == 2 and 1 in a.shape and a.size > 1 and a.dtype.kind in 'uif',
            f'{name} must be a real numeric MATLAB row or column vector')
    x = a.ravel(order='F')
    require(np.isfinite(x).all(), f'{name} contains missing or non-finite samples')
    return x


def extract_record(record, base):
    base.parent.mkdir(parents=True, exist_ok=True)
    original = base.with_suffix('.mat')
    fetch_original(record, original)
    inventory = {name: {'shape': list(shape), 'class': kind}
                 for name, shape, kind in whosmat(original)}
    names = set(RAW) | set(COPIES) | set(COPIES.values()) | set(ALTERNATIVES.values()) | {'trig'}
    chosen = sorted(names & inventory.keys())
    data = loadmat(original, variable_names=chosen)
    require(all(name in data for name in RAW), 'Original raw pair missing')
    values = {name: vector(data, name) for name in chosen}
    length = len(values['emg_1'])
    require(len(values['loadcell_right']) == length, 'Raw channel lengths differ')
    copies = {}
    for raw, copy in COPIES.items():
        if raw in values and copy in values:
            copies[copy] = bool(np.array_equal(values[raw], values[copy]))
    # Transforms always read the original fields when present, even if copies differ.
    clock_name = next((name for name in ('time', 'time_new') if name in values), None)
    if clock_name:
        t = values[clock_name]
        require(len(t) == length, 'Stored clock and raw pair lengths differ')
        dt = np.diff(t)
        require(np.all(dt > 0), 'Stored clock is not strictly increasing')
        bad = np.flatnonzero(np.abs(dt - STEP) > TOL_S)
        require(not len(bad), f'Irregular stored intervals after zero-based rows {bad[:10].tolist()}')
        clock = dict(time_origin='stored_regular_vector', source_field=clock_name,
                     observed_step_min_s=float(dt.min()), observed_step_max_s=float(dt.max()),
                     non_nominal_stored_intervals=int(len(bad)), interval_tolerance_s=TOL_S)
    else:
        t = np.arange(length, dtype=np.float64) / 1000
        clock = dict(time_origin='sample_index_at_published_1000_hz', source_field=None,
                     observed_step_min_s=None, observed_step_max_s=None,
                     non_nominal_stored_intervals=None, interval_tolerance_s=None)
    clock.update(start_s=float(t[0]), end_s=float(t[-1]), nominal_rate_hz=1000,
                 independent_hardware_timestamps=False, hardware_dropped_samples_known=False)
    alternatives = {}
    for raw, other in ALTERNATIVES.items():
        if other in values:
            alternatives[other] = dict(rows=len(values[other]), distinct_from=raw,
                                       equal_to_selected=bool(np.array_equal(values[raw], values[other])))
    trigger = None
    if 'trig' in values:
        v = values['trig']
        rises = np.flatnonzero((v[:-1] <= 0) & (v[1:] > 0)) + 1
        trigger = dict(rows=len(v), rising_edges=len(rises),
                       first_rising_row_zero_based=int(rises[0]) if len(rises) else None,
                       spacing_in_rows=np.unique(np.diff(rises)).tolist())
    output = dict(time_s=t, emg=values['emg_1'], load=values['loadcell_right'])
    dest = base.with_suffix('.npz')
    binary = io.BytesIO()
    np.savez(binary, **output)
    arrays = {key: digest(np.asarray(x, dtype='<f8').tobytes()) for key, x in output.items()}
    if 'array_f64le_sha256' in record:
        require(arrays == record['array_f64le_sha256'], 'Extracted array differs from release fingerprint')
    source = {key: record[key] for key in ('person', 'condition', 'trial', 'filename_category', 'member',
                                         'url', 'bytes', 'etag', 'sha256')}
    if 'rows' in record:
        require(record['rows'] == length and record['time_origin'] == clock['time_origin'],
                'Row count or timing provenance differs from the release')
    detail = {**source, 'rows': length, 'samples': length, 'time_origin': clock['time_origin'],
              'clock': clock, 'array_f64le_sha256': arrays, 'source_fields': {'emg': RAW[0], 'load': RAW[1], 'time_s': clock_name},
              'finite_support': {key: int(np.isfinite(x).sum()) for key, x in output.items()},
              'copies_equal': copies, 'alternative_channels': alternatives, 'trigger': trigger,
              'source_inventory': inventory, 'procedure_url': PROCEDURE, 'methods': PAPER,
              'unit': 'native acquisition units for the conditioned EMG and right load-cell signals'}
    write_atomic(dest, binary.getvalue())
    write_atomic(base.with_suffix('.source.json'), (json.dumps(detail, indent=2, allow_nan=False) + '\n').encode())
    return detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('split', choices=['development', 'assessment'])
    parser.add_argument('--cache', type=Path, required=True, help='directory for original and extracted files')
    args = parser.parse_args()
    manifest = Path(__file__).resolve().with_name(f'{args.split}-manifest.json')
    records = json.loads(manifest.read_text())['records']
    for rec in records:
        base = args.cache / rec['person'] / f"{rec['condition']}-trial-{rec['trial']}"
        result = extract_record(rec, base)
        print(f"{base}: {result['rows']} paired rows, {result['time_origin']}")


if __name__ == '__main__':
    main()
