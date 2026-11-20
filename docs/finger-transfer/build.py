# SPDX-License-Identifier: CC0-1.0
"""Build a local, single-file browser experiment from the seven published fits."""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / 'src'
FAMILIES = ('transformer', 'ridge')
MODES = ('aligned', 'cue', 'cortex')
AREAS = (1, 2, 3, 4, 6, 7, 8, 9)


def pack(a):
    if a.dtype.str not in ('<f4', '<f8') or not np.isfinite(a).all():
        raise ValueError('Expected finite little-endian floating parameters')
    return [a.dtype.itemsize, base64.b64encode(a.tobytes(order='C')).decode('ascii')]


def published_study(model):
    frozen = json.loads((SRC / 'inputs.sha256.json').read_text())
    for path, digest in frozen.items():
        if hashlib.sha256((model / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Review this changed study input before rebuilding: {path}')
    for license_name in ('CC0-1.0.txt', 'CC-BY-SA-4.0.txt'):
        if (model / 'licenses' / license_name).read_bytes() != (HERE / 'licenses' / license_name).read_bytes():
            raise ValueError(f'Changed license text: {license_name}')
    parameters = {}
    for key in [family + '_' + mode for family in FAMILIES for mode in MODES] + ['cue_table']:
        with np.load(model / 'weights' / (key + '.npz'), allow_pickle=False) as archive:
            parameters[key] = {k: pack(a) for k, a in archive.items()}
    results = json.loads((model / 'results.json').read_text())
    source = json.loads((model / 'source/source-manifest.json').read_text())
    ids = results['person_order']
    if ids != ['bp', 'cc', 'ht', 'jc', 'jp'] or results['exclusions']:
        raise ValueError('Revisit sample and fold descriptions')
    rows = []
    for person in ids:
        p = results['people'][person]
        member = source['members'][person]
        support = p['support']
        rows.append(dict(id=member['working_id'], code=person, trials=support['recipient_trials'],
                         repeats=sum(support['quartets_by_cue']), calibration=support['calibration_trials'],
                         coverage=[member['region_counts'].get(str(area), 0) for area in AREAS],
                         unknown=member['unknown_region_contacts'],
                         scores={k: v['scaled_mae'] for k, v in p['models'].items()}))
    contrasts = {key: {k: row[k] for k in ('mean', 'interval', 'person_means')}
                 for key, row in results['contrasts'].items()}
    study = dict(weights=parameters, people=rows, scores=results['cohort_mean_scaled_mae'],
                 contrasts=contrasts, gate=results['gate'])
    ethics = 'Ethics statement: ' + (model / 'METHOD.md').read_text().split('\nEthics statement: ', 1)[1].strip()
    if ethics not in (HERE / 'RIGHTS.md').read_text():
        raise ValueError('Methods require the original unmodified ethics paragraph')
    return study, ethics, source['catalog_privacy']


def build(model):
    study, ethics, privacy = published_study(model)
    scores = study['scores']
    if (min(scores, key=scores.get) != 'cue_table' or
            any(g['five_person_pass'] for g in study['gate'].values())):
        raise ValueError('Reconcile conclusions with the updated scientific results')
    assets = dict(STYLE=(SRC/'style.css').read_text(), SCRIPT='\n'.join(
        (SRC/name).read_text() for name in ('network.js','view.js')),
        DATA=json.dumps(study, separators=(',', ':'), allow_nan=False).replace('<', r'\u003c'),
        ETHICS=html.escape(ethics), PRIVACY=html.escape(privacy),
        LEGAL=html.escape('\n\n'.join((HERE/'licenses'/f).read_text()
                                     for f in ('CC-BY-SA-4.0.txt', 'CC0-1.0.txt'))))
    page = (SRC/'page.html').read_text()
    for key, value in assets.items():
        placeholder = '__' + key + '__'
        if page.count(placeholder) != 1:
            raise ValueError(f'Expected one {placeholder}')
        page = page.replace(placeholder, value)
    return page


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=HERE.parent.parent/'models/finger-transfer')
    parser.add_argument('--out', type=Path, default=HERE/'index.html')
    args = parser.parse_args()
    args.out.write_text(build(args.model), encoding='utf-8')
