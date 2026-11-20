"""Build the offline predictor, its ZIP, and the rat replay from the frozen public models."""
import argparse
import base64
import hashlib
from html import escape
import json
import importlib.util
from pathlib import Path
import zipfile
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / 'src'
STATIC = ('CC0-1.0.txt', 'CDLA-Permissive-2.0.txt', 'DATA-CREDITS.md', 'NOTICE.md', 'README.md',
          'SPATIAL-API.md', 'early-example.json', 'early-scores.json', 'arm-example.json', 'group-arm-example.json', 'group-arm-scores.json', 'point-example.json', 'right-plate-example.json', 'knee-moment-example.json', 'knee-example.json', 'angular-example.json', 'examples.json', 'forearm-example.json', 'predict.mjs', 'predictor.mjs')
PLATE_LICENCE = 'RIGHT-PLATE-DATA-LICENCE.txt'
ARTIFACTS = (*STATIC, PLATE_LICENCE, 'model.json', 'population-example.json', 'shared-motion.js')


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


def export_knee(model, checkpoint):
    manifest = read(SRC/'inputs.json')
    calc = (SRC/'runtime/knee.js').read_bytes()
    if sha(calc) != manifest['kneeCalculationSha256']:
        raise ValueError('Knee calculation differs from the verified source.')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'knee.json'
        subprocess.run([sys.executable, '-B', str(model/'knee/export_browser.py'),
                        str(checkpoint), str(path)], check=True)
        if sha(path.read_bytes()) != manifest['kneeExportSha256']:
            raise ValueError('Knee export differs from the verified checkpoint conversion.')
        return read(path), calc.decode()


def moment_parameters(checkpoint, saved, manifest, groups, descriptions):
    converter = SRC/'moment_export.py'
    calculation = (SRC/'runtime/knee-moment.js').read_bytes()
    if sha(converter.read_bytes()) != manifest['momentConversionSha256'] or sha(calculation) != manifest['momentCalculationSha256']:
        raise ValueError('The knee moment calculation or weight conversion differs from the checked reader.')
    spec = importlib.util.spec_from_file_location('moment_export', converter)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    weights = module.export(checkpoint)
    encoded = json.dumps(weights, separators=(',', ':'), allow_nan=False).encode() + b'\n'
    if sha(encoded) != manifest['momentExportSha256']:
        raise ValueError('The five knee moment methods differ from the checked weight export.')

    for name, flat in weights['shared'].items():
        if not np.array_equal(saved[name].ravel(), flat):
            raise ValueError('The shared knee moment encoder differs from the spatial encoder.')
    used = set()
    for kind, prefix in [('stats', 'load.'), ('trained', 'load.trained.'), ('scrambled', '')]:
        tensors = {}
        for name, flat in weights[kind].items():
            template = saved[prefix + name]
            vector = np.asarray(flat, dtype=template.dtype)
            if not np.array_equal(vector, flat):
                raise ValueError('Loss of precision in knee moment weights.')
            tensors[name] = vector.reshape(template.shape)
            if kind != 'scrambled':
                used.add(prefix + name)
        group = 'moment.' + kind
        groups[group], descriptions[group] = pack(tensors, tensors)
    if used != {name for name in saved.files if name.startswith('load.')} or len(used) != 35:
        raise ValueError('Incomplete set of knee moment parameters.')
    return calculation.decode().removesuffix("if (typeof module === 'object' && module.exports) module.exports = kneeMoment;\n")


def right_plate_parameters(saved, groups, descriptions):
    widths = {'marker_ridge':28, 'combined_ridge':92, 'marker_shared':52,
              'combined_shared':116, 'scrambled_combined':116}
    sizes = {'right_plate.phase':4, 'right_plate.marker_mean':6, 'right_plate.marker_sd':6}
    for mode, width in widths.items():
        for field in ('mean', 'sd', 'coef', 'bias'):
            sizes[f'right_plate.{mode}.{field}'] = 1 if field == 'bias' else width
    heads = {name:saved[name] for name in saved.files if name.startswith('right_plate.')}
    if set(heads) != set(sizes):
        raise ValueError('Incomplete or unexpected right-plate parameters.')
    for name, array in heads.items():
        if array.shape != (() if name.endswith('.bias') else (sizes[name],)) or (name.endswith('sd') and np.any(array <= 0)):
            raise ValueError('Invalid right-plate tensor: ' + name)
    groups['right_plate.readouts'], descriptions['right_plate.readouts'] = pack(heads, heads)
    names = sorted(n for n in saved.files if n == 'position' or n.startswith(('project.', 'blocks.', 'last_norm.')))
    rng = np.random.default_rng(71863)
    shuffled = {n:rng.permutation(saved[n].ravel()).reshape(saved[n].shape) for n in names}
    groups['right_plate.scrambled'], descriptions['right_plate.scrambled'] = pack(shuffled, shuffled)


def build_runtime(model, out):
    original = read(SRC/'runtime/original-groups.json')
    checkpoint = model/'movement-weights.npz'
    knee, calculation = export_knee(model, checkpoint)
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
        knee_names = {n for n in saved.files if n.startswith('knee.')}
        assert len(names) == len(set(names)) == 51
        moment_names = {n for n in saved.files if n.startswith('load.')}
        plate_names = {n for n in saved.files if n.startswith('right_plate.')}
        point_names = {n for n in saved.files if n.startswith('point_motion.')}
        expected_points = {'point_motion.token.mean', 'point_motion.token.scale'}
        expected_points.update('point_motion.' + m + '.' + field for m in ('shared', 'linear', 'shuffled')
                               for field in ('mean', 'scale', 'coef', 'bias'))
        if point_names != expected_points:
            raise ValueError('Expected only the fourteen deployable point tensors.')
        groups['point_motion.readouts'], descriptions['point_motion.readouts'] = pack(saved, point_names)
        point_core_names = sorted(n for n in saved.files if n == 'position' or n.startswith(('project.', 'blocks.', 'last_norm.')))
        rng = np.random.default_rng(3691)
        point_core = {n:rng.permutation(saved[n].ravel()).reshape(saved[n].shape) for n in point_core_names}
        groups['point_motion.scrambled'], descriptions['point_motion.scrambled'] = pack(point_core, point_core)
        arm_names = {n for n in saved.files if n.startswith('cued_arm.')}
        shapes = {'cued_arm.token.mean':(6,), 'cued_arm.token.sd':(6,)}
        for mode,width in [('cue',7),('motion',27),('cue_motion',34),('shared_motion',51),('shared_cue_motion',58),('shuffled_cue_motion',58)]:
            for key,shape in [('mean',(width,)),('sd',(width,)),('coef',(width,9)),('bias',(9,))]:
                shapes['cued_arm.'+mode+'.'+key] = shape
        if set(shapes) != arm_names or any(saved[n].shape != v for n,v in shapes.items()):
            raise ValueError('Incomplete arm cue model.')
        groups['cued_arm.readouts'],descriptions['cued_arm.readouts'] = pack(saved,arm_names)
        arm_rng = np.random.default_rng(20495)
        arm_core = {n:arm_rng.permutation(saved[n].ravel()).reshape(saved[n].shape) for n in point_core_names}
        groups['cued_arm.scrambled'],descriptions['cued_arm.scrambled'] = pack(arm_core,arm_core)
        group_shapes = {k.replace('cued_arm.','group_arm.'):v for k,v in shapes.items()}
        for key,source in [('offset_free_linear','cue_motion'),('offset_free_shared','shared_cue_motion')]:
            for field in ('mean','sd','coef','bias'):
                group_shapes['group_arm.'+key+'.'+field]=group_shapes['group_arm.'+source+'.'+field]
        group_shapes.update({'group_arm.cue_median':(7,3,3),'group_arm.target_sd':(3,3)})
        group_names={n for n in saved.files if n.startswith('group_arm.')}
        if group_names != set(group_shapes) or any(saved[k].shape!=s for k,s in group_shapes.items()):
            raise ValueError('Unexpected group arm model parameters.')
        group_values={n.replace('group_arm.','cued_arm.'):saved[n] for n in group_names if n not in ('group_arm.target_sd','group_arm.cue_median')}
        group_values['group_arm.cue_median']=saved['group_arm.cue_median']
        groups['group_arm.readouts'],descriptions['group_arm.readouts']=pack(group_values,group_values)
        residual_names={n for n in saved.files if n.startswith('scalp_residual.')}
        expected_residual={'scalp_residual.precue_sd99':(9,), 'scalp_residual.ocular.coef':(3,6)}
        for t,dim in [('eye',3),('scalp',6)]:
            for stat in ('mean','sd'): expected_residual['scalp_residual.ocular.'+t+'_'+stat]=(dim,)
        for method,width in [('mechanics',48),('scalp',72),('eye',60),('residual_scalp',72),('joint',84)]:
            for field,shape in [('mean',(width,)),('sd',(width,)),('coef',(width,9))]:
                expected_residual['scalp_residual.'+method+'.'+field]=shape
        if set(expected_residual)!=residual_names or any(saved[k].shape!=v for k,v in expected_residual.items()):
            raise ValueError('Unexpected scalp residual tensors.')
        sr={k:saved[k] for k in residual_names};sr['group_arm.target_sd']=saved['group_arm.target_sd']
        groups['scalp_residual.readouts'],descriptions['scalp_residual.readouts']=pack(sr,sr)
        assert len(knee_names) == 14 and set(saved.files) == {'configuration', *names, *knee_names, *moment_names, *plate_names, *point_names, *arm_names, *group_names, *residual_names}
        assert set(knee['readouts']) == {n.removeprefix('knee.') for n in knee_names}
        readouts = {n.removeprefix('knee.'):saved[n] for n in knee_names}
        groups['knee.readouts'], descriptions['knee.readouts'] = pack(readouts, readouts)
        shuffled = {}
        for name, flat in knee['scrambled_encoder'].items():
            array = saved[name]
            assert np.array_equal(array.ravel(), knee['encoder'][name])
            shuffled[name] = np.asarray(flat, dtype=array.dtype).reshape(array.shape)
        groups['knee.scramble'], descriptions['knee.scramble'] = pack(shuffled, shuffled)
        right_plate_parameters(saved, groups, descriptions)
        manifest = read(SRC/'inputs.json')
        moment_js = moment_parameters(checkpoint, saved, manifest, groups, descriptions)

    ids = dict(spatial=original['checkpoints']['spatial'], movement=sha(checkpoint.read_bytes()))
    template = (SRC/'runtime/runtime.js.in').read_text()
    template = template.replace('__GROUP_ARM_ID__', config['group_arm']['calibration_id'])
    script = template.replace('__KNEE_CALCULATION__', calculation).replace('__MOMENT_CALCULATION__', moment_js).replace('__CHECKPOINT__', json.dumps(ids)).replace('__GROUPS__', json.dumps(groups, separators=(',', ':')))
    out.mkdir(parents=True, exist_ok=True)
    for name in STATIC:
        (out/name).write_bytes((SRC/'runtime'/name).read_bytes())
    (out/PLATE_LICENCE).write_bytes((model/'right-plate/DATA-LICENCE.txt').read_bytes())
    (out/'shared-motion.js').write_text(script)
    write_json(out/'model.json', dict(checkpoints=ids, config=config, groups=descriptions,
               pythonPredictorSha256=sha((model/'predict.py').read_bytes()),
               pythonCorrectionSha256=sha((model/'forearm/residual.py').read_bytes()),
               pythonPopulationSha256=sha((model/'population/adapter.py').read_bytes()),
               kneeExportSha256=manifest['kneeExportSha256'], momentExportSha256=manifest['momentExportSha256'],
               pythonMomentSha256=manifest['model']['load/adapter.py'],
               pythonRightPlateSha256=manifest['model']['right_plate.py'], encoding=original['encoding']))
    example = read(model/'population/example.json')
    # Limit the worked record to the six measured inputs and the two API selectors.
    keys = {'domain':'domain', 'mode':'mode', 'cutoffS':'cutoff_s', 'priorTimeS':'prior_time_s',
            'priorXyCm':'prior_xy_cm', 'regionalCounts':'regional_counts', 'unitCounts':'unit_counts'}
    write_json(out/'population-example.json', {key: example[source] for key, source in keys.items()})
    (out/'SHA256SUMS').write_text(''.join(f'{sha((out/n).read_bytes())}  {n}\n' for n in sorted(ARTIFACTS)))
    expected = set(ARTIFACTS) | {'SHA256SUMS'}
    if {f.name for f in out.iterdir()} != expected:
        raise ValueError('Build into a clean runtime directory with only the listed products.')


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


GUI_SOURCES = ('build.py', 'README.md', 'Open on Linux.sh', 'Open on Windows.cmd', 'Open on macOS.command',
               'src/panel.html', 'src/panel.js', 'src/panel.css', 'src/inputs.json',
               'src/sources.json', 'src/derive.py', 'src/angular-scores.json')
GEN_SOURCES = ('build.py', 'README.md', 'src/inputs.json', 'src/moment_export.py',
               *('src/runtime/' + n for n in (*STATIC, 'original-groups.json', 'knee.js', 'knee-moment.js', 'runtime.js.in')),
               *('src/viewer/' + n for n in ('index.html', 'model.js', 'viewer.css', 'viewer.js')))


def package(model, gui, out):
    runtime = out/'runtime'
    gui_page = out/'index.html'
    subprocess.run([sys.executable, '-B', str(gui/'build.py'), '--runtime', str(runtime),
                    '--out', str(gui_page)], check=True)
    entries = {n:runtime/n for n in (*ARTIFACTS, 'SHA256SUMS')}
    entries['index.html'] = gui_page
    for n in ('Open on Linux.sh', 'Open on macOS.command', 'Open on Windows.cmd'):
        entries[n] = gui/n
    for n in GEN_SOURCES:
        entries['source/models/browser-source/'+n] = HERE/n
    for n in read(SRC/'inputs.json')['model']:
        entries['source/models/neurotranslate-0.0/'+n] = model/n
    for n in GUI_SOURCES:
        entries['source/docs/shared-motion/'+n] = gui/n
    checksums = out/'PACKAGE-SHA256SUMS'
    checksums.write_text(''.join(f'{sha(path.read_bytes())}  {name}\n' for name, path in sorted(entries.items())))
    entries[checksums.name] = checksums
    with zipfile.ZipFile(out/'movement-browser.zip', 'w') as output:
        for name, path in sorted(entries.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 20, 0, 0, 0))
            executable = name.endswith(('.sh', '.command'))
            entry.external_attr = (0o100755 if executable else 0o100644) << 16
            output.writestr(entry, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True, help='Public model directory containing movement-weights.npz and population/')
    parser.add_argument('--gui', type=Path, default=HERE.parents[1]/'docs/shared-motion')
    parser.add_argument('--direct', type=Path, help='Direct population transfer directory containing trace.json and weights.json')
    parser.add_argument('--out', type=Path, default=HERE/'public')
    args = parser.parse_args()
    for key, root in [('model', args.model), ('direct', args.direct)]:
        if root is None:
            continue
        for name, digest in read(SRC/'inputs.json')[key].items():
            if sha((root/name).read_bytes()) != digest:
                raise ValueError(f'Frozen {key} input differs: {name}')
    build_runtime(args.model, args.out/'runtime')
    package(args.model, args.gui, args.out)
    if args.direct:
        build_viewer(args.direct, args.model, args.out/'runtime', args.out/'viewer')


if __name__ == '__main__':
    main()
