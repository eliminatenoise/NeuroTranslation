# SPDX-License-Identifier: CC0-1.0
"""Reproduce held-person folds and the distinct deployment fits."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys

import numpy as np
import torch

from model import fit, predict, training_data
from movement import Ineligible, METHOD_HASH, PEOPLE, prepare
from score import score_person, summary

HERE = Path(__file__).resolve().parent


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False,
                               default=lambda value: value.tolist()) + '\n')


def open_reader(source_dir):
    spec = importlib.util.spec_from_file_location('fingerflex_source', source_dir / 'fingerflex_source.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def readouts(training, output, held=None):
    x, y, importance, table = training_data(training)
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output/'cue_table.npz', table=table)
    predictions = {}
    if held is not None:
        current = held.x[held.recipients]
        n = len(current)
        wrong = current.copy()
        wrong[..., 60:] = held.x[held.donors, ..., 60:]
        wrong = wrong.reshape(-1, 4, 85)
        current = current.reshape(-1, 4, 85)
        predictions['cue_table'] = table[held.cues[held.recipients]-1]
    for family in ('ridge', 'transformer'):
        for mode in ('cue', 'cortex', 'aligned'):
            key = family + '_' + mode
            weights = fit(x, y, importance, family, mode)
            np.savez_compressed(output/(key+'.npz'), **weights)
            if held is not None:
                predictions[key] = predict(current, family, mode, weights).reshape(n, 68, 5)
                if mode == 'aligned':
                    predictions[family+'_earlier'] = predict(wrong, family, mode, weights).reshape(n, 68, 5)
    if held is not None:
        np.savez_compressed(output/'predictions.npz', **predictions)
        return score_person(held, predictions)


def run(source_dir, cache, out, threads):
    if hashlib.sha256((HERE/'METHOD.md').read_bytes()).hexdigest() != METHOD_HASH:
        raise ValueError('Frozen study design changed')
    if out.exists():
        raise FileExistsError('Choose a fresh private output directory')
    reader = open_reader(source_dir)
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    out.mkdir(parents=True, mode=0o700)
    people, exclusions = {}, {}
    for name in PEOPLE:
        source = reader.load_development(name, cache)
        try:
            people[name] = prepare(name, source)
        except Ineligible as exc:
            exclusions[name] = str(exc)
        del source
    save_json(out/'admission.json', {'eligible': list(people), 'excluded': exclusions,
                                     'support': {k: v.support for k, v in people.items()}})
    if len(people) < 3:
        raise ValueError('Fewer than three eligible people; study cannot be fitted')
    scores = {}
    for name, held in people.items():
        train = [p for k, p in people.items() if k != name]
        scores[name] = readouts(train, out/'folds'/name, held)
        print('Completed held-person fold', name, flush=True)
    result = summary(scores)
    result.update({'method_sha256': METHOD_HASH, 'exclusions': exclusions,
                   'software': {'python': platform.python_version(), 'numpy': np.__version__,
                                'torch': str(torch.__version__), 'device': 'cpu',
                                'torch_threads': threads, 'torch_interop_threads': 1}})
    save_json(out/'results.json', result)
    readouts(list(people.values()), out/'deployment')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=HERE/'source')
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private directory')
    parser.add_argument('--threads', default=2, type=int, choices=(1,2))
    opt = parser.parse_args()
    run(opt.source_dir, opt.cache, opt.output, opt.threads)
