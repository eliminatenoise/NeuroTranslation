"""Build the self-contained offline and GitHub Pages forecast page."""

from argparse import ArgumentParser
from base64 import b64encode
from hashlib import file_digest
import json
from pathlib import Path

import numpy as np


SITE = Path(__file__).resolve().parent
CHECKPOINT = 'd558811108aea23ef9e42cdce10478eeb1b23c82f7acad230e887bc33d55d497'
EXAMPLE = 'Example Muscles.csv'


def digest(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def embedded_weights(path):
    if digest(path) != CHECKPOINT:
        raise ValueError('Use the exact published transfer weights.')
    prefixes = ('compact.', 'linear.', 'research.muscle_only.relative_muscle.',
                'research.given_body_mass_and_slope.relative_muscle.')
    with np.load(path, allow_pickle=False) as pack:
        use = [name for name in pack.files if not name.endswith('.penalty') and
               (name.startswith(prefixes) or name.endswith('.blend_research_share'))]
        tensors = {}
        for name in use:
            value = pack[name]
            if value.dtype.kind != 'f' or value.dtype.itemsize not in (4, 8) or not np.isfinite(value).all():
                raise ValueError(f'Unexpected checkpoint type or value in {name}.')
            length = value.dtype.itemsize
            array = value.astype(f'<f{length}', copy=False)
            tensors[name] = {'shape': array.shape, 'dtype': f'f{8 * length}',
                             'data': b64encode(array.tobytes()).decode('ascii')}
    if len(tensors) != 479:
        raise ValueError('The embedded checkpoint is incomplete.')
    return {'checkpoint_sha256': CHECKPOINT, 'tensors': tensors}


def json_text(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).replace('<', '\\u003c')


def build(weights_path, example_path, output):
    template = (SITE / 'src/page.html').read_text(encoding='utf-8')
    manifest = embedded_weights(weights_path)
    markers = {
        '__STYLE__': (SITE / 'src/style.css').read_text(encoding='utf-8'),
        '__MODEL__': (SITE / 'src/model.js').read_text(encoding='utf-8'),
        '__CONTROLS__': (SITE / 'src/controls.js').read_text(encoding='utf-8'),
        '__PAYLOAD__': json_text(manifest),
        '__EXAMPLE__': json_text(example_path.read_text(encoding='utf-8')),
    }
    for marker, content in markers.items():
        if template.count(marker) != 1:
            raise ValueError(f'Expected one {marker} placeholder in the page.')
        template = template.replace(marker, content, 1)
    output.write_text(template, encoding='utf-8')


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    default = SITE.parents[2] / 'benchmarks/emg-floor-load/decline-treadmill'
    parser.add_argument('--weights', type=Path, default=default / 'TRANSFER-WEIGHTS.npz')
    parser.add_argument('--example', type=Path, default=default / EXAMPLE)
    parser.add_argument('--output', type=Path, default=SITE / 'index.html')
    args = parser.parse_args()
    build(args.weights, args.example, args.output)
