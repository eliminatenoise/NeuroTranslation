"""Build a self-contained stride viewer from the pinned numerical study."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / 'src'


def bundle(arrays):
    layout, pieces = [], []
    for name, values in arrays.items():
        values = np.asarray(values)
        compact = values.astype('<f4')
        if not np.isfinite(compact).all() or not np.array_equal(values, compact):
            raise ValueError('Cannot reproduce original parameter: ' + name)
        layout.append([name, list(values.shape)])
        pieces.append(compact.tobytes())
    return {'layout': layout, 'precision': 32, 'base64': base64.b64encode(b''.join(pieces)).decode()}


def build(model, out):
    pins = json.loads((SRC / 'inputs.sha256.json').read_bytes())
    for name, expected in pins.items():
        if hashlib.sha256((model / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Changed model input: ' + name)

    def read(name):
        if name not in pins:
            raise ValueError('Unpinned study input: ' + name)
        return json.loads((model / name).read_bytes())

    models = {}
    for id_, name in [('conditional', 'conditional'), ('history', 'history-only')]:
        payload = read(name + '.json')
        if payload['format'] != 'stride-attention-1' or payload['mode'] != name:
            raise ValueError('Unexpected network format or mode')
        models[id_] = bundle(payload['weights'])
    if 'ridge.npz' not in pins:
        raise ValueError('Unpinned linear model')
    with np.load(model / 'ridge.npz', allow_pickle=False) as ridge:
        if ridge['coef'].shape != (627, 684) or ridge['bias'].shape != (684,):
            raise ValueError('Unexpected linear model dimensions')
        models['ridge'] = bundle({name: ridge[name] for name in ['coef', 'bias']})
    examples = {}
    for action in ['walk', 'run']:
        example = read('example-' + action + '.json')
        source = example['source']
        if example['action'] != action or source['role'] != 'recorded training example':
            raise ValueError('Unidentified recording')
        step = source['historyFrames'][1] - source['historyFrames'][0]
        description = (f"Source frames {source['historyFrames'][0]}–{source['historyFrames'][-1]} supply the history. "
                       f"Frames {source['outcomeFrames'][0]}–{source['outcomeFrames'][-1]} supply the later recording. "
                       f"Displayed samples are {step} source frames apart ({source['rateHz']} Hz capture).")
        examples[action] = {k: example[k] for k in ('action', 'history', 'observedFuture')}
        credit = {k:source[k] for k in ('database','role','id','sha256','url','terms','rateHz','historyFrames','clock')}
        credit['credit'] = 'The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217. Direct resale of the data, including conversions, is prohibited.'
        examples[action].update(id=source['id'], description=description, source=credit)
    study = json.loads((SRC / 'study.json').read_bytes())
    data = dict(schema=read('schema.json'), models=models, examples=examples, study=study)
    slots = {k: (SRC / name).read_text() for k, name in
             [('STYLE', 'style.css'), ('NETWORK', 'forecast.js'), ('SCENE', 'scene.js'), ('VIEW', 'view.js')]}
    slots['DATA'] = json.dumps(data, allow_nan=False, separators=(',', ':')).replace('<', r'\u003c')
    page = (SRC / 'page.html').read_text()
    for key, value in slots.items():
        marker = '/* ' + key + ' */'
        if page.count(marker) != 1 or '</script' in value.lower():
            raise ValueError('Unsafe template replacement: ' + key)
        page = page.replace(marker, value)
    out.write_text(page, encoding='utf-8')
    print(hashlib.sha256(page.encode()).hexdigest(), out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=HERE / 'index.html')
    args = parser.parse_args()
    build(args.model, args.out)
