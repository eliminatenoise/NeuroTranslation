"""Build the offline predictor, its ZIP, and the rat replay from the frozen public models."""
import argparse
import base64
import hashlib
from html import escape
import json
from pathlib import Path
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / 'src'
STATIC = ('CC0-1.0.txt', 'CDLA-Permissive-2.0.txt', 'DATA-CREDITS.md', 'NOTICE.md', 'README.md',
          'SPATIAL-API.md', 'angular-example.json', 'examples.json', 'forearm-example.json', 'predict.mjs', 'predictor.mjs')
ARTIFACTS = (*STATIC, 'model.json', 'population-example.json', 'shared-motion.js')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def pack(archive, names):
    layout, tensors, payload = [], [], bytearray()
    for name in sorted(names):
        array = archive[name]
        if array.dtype.str not in ('<f4', '<f8') or not np.isfinite(array).all():
            raise ValueError(f'Unsupported tensor {name}')
        layout.append([name, array.size, array.itemsize])
        tensors.append(dict(name=name, shape=list(array.shape), dtype=array.dtype.str))
        payload.extend(array.tobytes(order='C'))
    info = dict(bytes=len(payload), sha256=sha(payload))
    return dict(**info, layout=layout, encoded=base64.b64encode(payload).decode('ascii')), dict(**info, tensors=tensors)


def build_runtime(model, out):
    original = read(SRC/'runtime/original-groups.json')
    checkpoint = model/'movement-weights.npz'
    groups, descriptions = {}, {}
    with np.load(checkpoint, allow_pickle=False) as saved:
        config = json.loads(str(saved['configuration']))
        policy = config['rat_population']
        assert policy['format'] == 1 and policy['region_order'] == ['CA1', 'PFC']
        assert policy['original_checkpoint_sha256'] == original['checkpoints']['movement']
        assert sha((model/'population/protocol.json').read_bytes()) == policy['protocol_sha256']
        for key, description in original['groups'].items():
            names = [t['name'] for t in description['tensors']]
            groups[key], descriptions[key] = pack(saved, names)
            assert descriptions[key] == description, key
        for mode, width in [('motion', 28), ('combined', 44)]:
            key = 'population.' + mode
            names = [key + '.' + field for field in ('mean', 'scale', 'coef', 'intercept')]
            assert [saved[n].shape for n in names] == [(width,), (width,), (width,), ()]
            assert np.all(saved[names[1]] > 0)
            groups[key], descriptions[key] = pack(saved, names)
        names = [name for group in groups.values() for name, *_ in group['layout']]
        assert len(names) == len(set(names)) == 51 and set(names) == set(saved.files) - {'configuration'}

    ids = dict(spatial=original['checkpoints']['spatial'], movement=sha(checkpoint.read_bytes()))
    template = (SRC/'runtime/runtime.js.in').read_text()
    script = template.replace('__CHECKPOINT__', json.dumps(ids)).replace('__GROUPS__', json.dumps(groups, separators=(',', ':')))
    out.mkdir(parents=True, exist_ok=True)
    for name in STATIC:
        (out/name).write_bytes((SRC/'runtime'/name).read_bytes())
    (out/'shared-motion.js').write_text(script)
    write_json(out/'model.json', dict(checkpoints=ids, config=config, groups=descriptions,
               pythonPredictorSha256=sha((model/'predict.py').read_bytes()),
               pythonCorrectionSha256=sha((model/'forearm/residual.py').read_bytes()),
               pythonPopulationSha256=sha((model/'population/adapter.py').read_bytes()), encoding=original['encoding']))
    example = read(model/'population/example.json')
    # Limit the worked record to the six measured inputs and the two API selectors.
    keys = {'domain':'domain', 'mode':'mode', 'cutoffS':'cutoff_s', 'priorTimeS':'prior_time_s',
            'priorXyCm':'prior_xy_cm', 'regionalCounts':'regional_counts', 'unitCounts':'unit_counts'}
    write_json(out/'population-example.json', {key: example[source] for key, source in keys.items()})
    (out/'SHA256SUMS').write_text(''.join(f'{sha((out/n).read_bytes())}  {n}\n' for n in sorted(ARTIFACTS)))
    expected = set(ARTIFACTS) | {'SHA256SUMS'}
    if {f.name for f in out.iterdir()} != expected:
        raise ValueError('Build into a clean runtime directory with only the listed products.')
    with zipfile.ZipFile(out.parent/'movement-browser.zip', 'w') as output:
        for name in sorted(expected):
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 20, 0, 0, 0))
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, (out/name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def viewer_data(direct, model):
    trace, weights, scores, protocol = (read(direct/name) for name in ('trace.json','weights.json','scores.json','protocol.json'))
    results = read(model/'population/results.json')
    frames = trace['camera_rows']
    assert len(frames) == len(set(frames))
    anchors = []
    for record in trace['forecast_anchors']:
        indexes = [frames.index(row) for row in record['prior_camera_rows']]
        target = frames.index(record['target_camera_row'])
        assert [trace['camera_time_s'][i] for i in indexes] == record['prior_time_s']
        assert [trace['camera_xy_cm'][i] for i in indexes] == record['prior_xy_cm']
        assert trace['camera_xy_cm'][target] == record['target_xy_cm']
        assert trace['camera_time_s'][target] == record['target_time_s']
        edge = trace['count_bin_edges_s'].index(record['cutoff_s'])
        counts = [list(pair) for pair in zip(*(series[edge-4:edge] for series in trace['spike_counts_by_region']), strict=True)]
        assert counts == record['regional_counts']
        anchors.append(dict(cutoff=record['cutoff_s'], history=indexes, target=target,
                            end_bin=edge, donor=record['donor_counts'],
                            donor_trip=record['donor_trip'], donor_cutoff=record['donor_cutoff_s']))
    assert len(anchors) == 12 and trace['region_order'] == ['CA1', 'PFC']
    assert protocol['test'] == [r['rat'] for r in scores['by_rat']] == [r['rat'] for r in results['by_rat']]
    assert sum(r['windows'] for r in results['by_rat']) == 549
    cols = ('shared_motion','shared_combined','shared_donor','scrambled_combined')
    return dict(times=trace['camera_time_s'], xy=trace['camera_xy_cm'], rows=frames,
                counts=trace['spike_counts_by_region'], start=trace['trip']['start_s'],
                stop=trace['trip']['stop_s'], units=trace['unit_counts'], anchors=anchors,
                weights=weights, scores=scores['by_rat'], mean=scores['equal_rat'],
                sharedScores=[{k:r[k] for k in ('rat','windows',*cols)} for r in results['by_rat']],
                sharedMean={k:results['equal_rat'][k] for k in cols})


def build_viewer(direct, model, runtime, out):
    src = SRC/'viewer'
    payload = json.dumps(viewer_data(direct, model), separators=(',', ':'), allow_nan=False).replace('<', r'\u003c')
    replacements = dict(STYLE=(src/'viewer.css').read_text(), DATA=payload, MODEL=(src/'model.js').read_text(),
                        RUNTIME=(runtime/'shared-motion.js').read_text(), VIEW=(src/'viewer.js').read_text(),
                        CDLA=escape((runtime/'CDLA-Permissive-2.0.txt').read_text()), CC0=escape((runtime/'CC0-1.0.txt').read_text()))
    page = (src/'index.html').read_text()
    for tag, replacement in replacements.items():
        token = '{{' + tag + '}}'
        assert page.count(token) == 1
        page = page.replace(token, replacement)
    out.mkdir(parents=True, exist_ok=True)
    (out/'index.html').write_text(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True, help='Public model directory containing movement-weights.npz and population/')
    parser.add_argument('--direct', type=Path, required=True, help='Direct population transfer directory containing trace.json and weights.json')
    parser.add_argument('--out', type=Path, default=HERE/'public')
    args = parser.parse_args()
    for key, root in [('model', args.model), ('direct', args.direct)]:
        for name, digest in read(SRC/'inputs.json')[key].items():
            if sha((root/name).read_bytes()) != digest:
                raise ValueError(f'Frozen {key} input differs: {name}')
    build_runtime(args.model, args.out/'runtime')
    build_viewer(args.direct, args.model, args.out/'runtime', args.out/'viewer')


if __name__ == '__main__':
    main()
