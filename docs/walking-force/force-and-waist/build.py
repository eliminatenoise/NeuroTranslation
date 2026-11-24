"""Render a standalone browser page from the verified public checkpoint."""

from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'src'
BENCH = HERE.parents[2] / 'benchmarks' / 'native-force-waist'
CHECKPOINT = 'd285453548c7e7254116bec4f9b39bf35865d98e2e8123beac2e47f66eaacc86'


def build_payload():
    model = BENCH / 'model.npz'
    assert sha256(model.read_bytes()).hexdigest() == CHECKPOINT
    summary = json.loads((BENCH / 'results.json').read_text())
    assert summary['model_sha256'] == CHECKPOINT
    with np.load(model, allow_pickle=False) as arrays:
        arch = json.loads(str(arrays['architecture']))
        assert arch == {'width': 32, 'heads': 4, 'depth': 1, 'ff_width': 64}
        schemas = json.loads(str(arrays['schemas']))
        assert {name: len(schema['channels']) for name, schema in schemas.items()} == {'force': 1, 'waist': 6}
        tensors = {}
        for key in sorted(set(arrays.files) - {'version', 'architecture', 'schemas'}):
            value = arrays[key]
            assert value.dtype.name in ('float32', 'float64') and np.isfinite(value).all()
            encoded = value.astype(value.dtype.newbyteorder('<'), copy=False).tobytes(order='C')
            tensors[key] = {'shape': value.shape, 'dtype': value.dtype.name, 'data': b64encode(encoded).decode()}
    sys.path.insert(0, str(BENCH))
    from run_forecast import examples

    generated = {name: np.round(np.asarray(history), 14).tolist() for name, history in examples()}
    return {'checkpoint': CHECKPOINT, 'schemas': schemas, 'tensors': tensors, 'benchmark': summary['results'],
            'examples': generated}


def render(payload):
    page = (SOURCE / 'page.html').read_text()
    scripts = '\n'.join((SOURCE / name).read_text() for name in ('model.js', 'history-chart.js', 'view.js'))
    values = {'CSS': (SOURCE / 'style.css').read_text(), 'JS': scripts,
              'PAYLOAD': json.dumps(payload, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')}
    for name, value in values.items():
        token = '%%' + name + '%%'
        assert page.count(token) == 1
        page = page.replace(token, value)
    return page


if __name__ == '__main__':
    page = render(build_payload())
    if sys.argv[1:] == ['--check']:
        if (HERE / 'index.html').read_text() != page:
            raise SystemExit('The standalone page differs from its source.')
    elif not sys.argv[1:]:
        (HERE / 'index.html').write_text(page)
    else:
        raise SystemExit('usage: build.py [--check]')
