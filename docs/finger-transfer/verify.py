# SPDX-License-Identifier: CC0-1.0
"""Check the built page's tokens and seven readouts against the released Python model."""
import argparse
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
MODES = ('aligned', 'cue', 'cortex')
REGIONS = (1, 2, 3, 4, 6, 7, 8, 9)
TS = (-120, -80, -40, 0)
JS = """
const fs = require('node:fs'), vm = require('node:vm');
const job = JSON.parse(fs.readFileSync(0, 'utf8'));
const doc = {getElementById: id => ({textContent:job.study})};
const ctx = vm.createContext({atob, document:doc, cases:job.cases});
const query = `cases.map(s => ({
  tokens: tokensFor(s).map(t => Array.from(t)),
  predictions: Object.fromEntries(["aligned","cue","cortex"].map(m=>[m,predictStudy(s,m)]))
}))`;
process.stdout.write(JSON.stringify(vm.runInContext(job.script + "\\n" + query,ctx)));
"""


def scenarios():
    for i, (digit, phase, tick) in enumerate(itertools.product(range(1, 6), range(2), range(9, 43))):
        mask = [bool((i*59) % 256 & (1 << j)) for j in range(8)]
        yield dict(digit=digit, phase=phase, tick=tick, region=REGIONS[i % 8],
                   low=(i % 17 - 8)/4, high=((i*7) % 17 - 8)/4,
                   mask=mask, unknown=(i % 2 == 0))


def native_tokens(s, movement):
    # Make one invented contact per available region. Unknown contacts, if any, carry code 0.
    codes = [code for code, present in zip(REGIONS, s['mask']) if present]
    if s['unknown']:
        codes.append(0)
    bands = np.full((4, 2, len(codes)), 3., dtype=np.float64)
    for i, code in enumerate(codes):
        if code == s['region']:
            bands[:, :, i] += np.arange(1, 5)[:, None] * [s['low']/4, s['high']/4]
    cal = dict(mean=np.full((2, len(codes)), 3.), sd=np.ones((2, len(codes))))
    regional = movement.pool(bands, np.array(codes, dtype=int), cal)
    times = (s['tick']*40 + np.array(TS)) / 1000
    cue = movement.cue_features(s['digit'], s['phase'], times)
    return np.concatenate([cue, regional], axis=1).astype(np.float32)


def check(model):
    sys.path.insert(0, str(model.resolve()))
    import model as fitted
    import movement
    import build

    page = (HERE/'index.html').read_text()
    if build.build(model) != page:
        raise ValueError('HTML differs from its frozen model and source rebuild')
    script = (HERE/'src/network.js').read_text()
    if script not in page:
        raise ValueError('Numerical source missing from the built page')
    study = page.split('<script type="application/json" id="study">', 1)[1].split('</script>', 1)[0]
    cases = list(scenarios())
    run = subprocess.run(['node', '-e', JS], text=True, capture_output=True, check=True,
                         input=json.dumps(dict(script=script, study=study, cases=cases)))
    js = json.loads(run.stdout)
    x = np.array([native_tokens(s, movement) for s in cases])
    np.testing.assert_array_equal(x, [row['tokens'] for row in js])
    maximum = dict(transformer=0., ridge=0., table=0.)
    for mode in MODES:
        for family in ('transformer', 'ridge'):
            weights = fitted.load_weights(model/'weights' / f'{family}_{mode}.npz')
            expected = fitted.predict(x, family, mode, weights)
            actual = np.array([entry['predictions'][mode][family] for entry in js])
            error = float(np.abs(expected-actual).max())
            maximum[family] = max(maximum[family], error)
            np.testing.assert_allclose(actual, expected, atol=1e-5 if family == 'transformer' else 1e-11, rtol=0)
        table = fitted.load_weights(model/'weights/cue_table.npz')['table']
        expected = [table[s['digit']-1, s['phase']*34+s['tick']-9] for s in cases]
        np.testing.assert_array_equal(expected, [row['predictions'][mode]['table'] for row in js])
    return dict(packets=len(cases), exact_token_values=int(x.size),
                checked_model_values=len(cases)*5*7, max_absolute_error=maximum,
                python=sys.version.split()[0], torch=torch.__version__, numpy=np.__version__,
                node=subprocess.check_output(['node','--version'], text=True).strip(),
                torch_threads=torch.get_num_threads(), torch_interop=torch.get_num_interop_threads())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', type=Path, default=HERE.parent.parent/'models/finger-transfer')
    args = ap.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    print(json.dumps(check(args.model), indent=2))
