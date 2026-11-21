"""Fit frozen balance models on nested training subsets, then score sealed fits."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib
import json
import os
from pathlib import Path
from time import perf_counter
import sys

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

PLAN = json.loads(Path(__file__).with_name('protocol.json').read_text())
VARIANTS = [(name, width) for name in ('paired', 'early') for width in (8, 16, 32)]
VARIANTS += [(name, 16) for name in ('without_scalp', 'without_electrical', 'without_mechanics')]


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def verify(path, expected):
    if digest(path) != expected:
        raise ValueError(f'SHA-256 differs for {path.name}')


def sources(source):
    for filename, key in (('protocol.json','source_protocol_sha256'), ('model.py','source_model_sha256'),
                          ('evaluate.py','source_evaluation_sha256')):
        verify(source / filename, PLAN[key])
    sys.path.insert(0, str(source.resolve()))
    return importlib.import_module('model'), importlib.import_module('evaluate')


def hash_parts(*parts):
    return hashlib.sha256('|'.join(map(str, parts)).encode('ascii')).digest()


def subsets(a):
    people = np.unique(a['person'])
    if len(people) != 18 or len(a['event']) != 5179:
        raise ValueError('Unexpected development split')
    cells = {}
    for p in people:
        cells[p] = []
        for h in (0, 1):
            for d in (-1, 1):
                rows = np.flatnonzero((a['person'] == p) & (a['posture'] == h) & (a['direction'] == d))
                cells[p].append(sorted(rows, key=lambda i: hash_parts(PLAN['window_seed'], p, h, d, a['event'][i])))
    designs = {}
    for seed in PLAN['order_seeds']:
        order = sorted(people, key=lambda p: hash_parts(seed, p))
        for n in PLAN['donor_counts']:
            for limit in ([0, 432, 864, 1728, 3456] if n == 18 else [0, 432]):
                key = f"{'common' if n == 18 else seed}-{n}-{'all' if not limit else limit}"
                quota = limit // (n * 4) if limit else None
                selected = order[:n]
                idx = sorted(i for p in selected for cell in cells[p] for i in cell[:quota])
                if limit and (len(idx) != limit or any(len(cell) < quota for p in selected for cell in cells[p])):
                    raise ValueError('Insufficient unique windows in balanced design')
                if key in designs:
                    assert idx == designs[key]['indices']
                else:
                    designs[key] = dict(people=sorted(selected), indices=[int(i) for i in idx], n=n, limit=limit)
    return designs


def network(m, name, width):
    class SizedFusion(m.Fusion):
        def __init__(self):
            nn.Module.__init__(self)
            self.name = name
            self.projections = nn.ModuleList(nn.Linear(w, width) for w in m.WIDTHS)
            self.branches = nn.ModuleList(nn.Linear(3*width, width) for _ in range(2))
            self.join = nn.Linear(3*width+2, 2*width)
            self.head = nn.Linear(2*width, 20)
    return SizedFusion()


def fit_one(m, name, width, seed, xs, y, batches):
    torch.manual_seed(seed)
    net = network(m, name, width)
    optimizer = torch.optim.AdamW(net.parameters(), lr=.002, weight_decay=.01, foreach=False)
    for ix in batches:
        target = y[ix]
        output = net([x[ix] for x in xs])
        loss = (F.smooth_l1_loss(output[:, :8], target[:, :8]) + F.smooth_l1_loss(output[:, 8:], target[:, 8:])) * .5
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
    return net.eval()


def configure():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision('highest')


def fit_subset(task):
    source, development, previous, directory, key, design = task
    m, _ = sources(source)
    a = {k:v[design['indices']] for k,v in m.load(development).items()}
    s = m.scales(a)
    xs, y = m.fit_tensors(a, s, 'cpu')
    common = key == 'common-18-all'
    if common and previous:
        verify(previous, PLAN['source_weights_sha256'])
        inherited = m.load(previous)
        assert all(np.array_equal(value, inherited[field]) for field, value in s.items())
    rows = []
    for seed in PLAN['train_seeds']:
        states = s.copy()
        timings = {}
        batches = torch.as_tensor(m.draws(a, seed, 384))
        for name, width in VARIANTS:
            label = f'{name}_w{width}'
            start = perf_counter()
            if common and previous and width == 16:
                prefix = f'{name}_{seed}/'
                parameters = {k.removeprefix(prefix):v for k,v in inherited.items() if k.startswith(prefix)}
                net = network(m, name, width)
                net.load_state_dict({k:torch.from_numpy(v) for k,v in parameters.items()})
                reused = True
            else:
                net = fit_one(m, name, width, seed, xs, y, batches)
                parameters = {k:v.detach().numpy() for k,v in net.state_dict().items()}
                reused = False
            timings[label] = dict(seconds=perf_counter()-start, reused=reused,
                                  parameters=sum(p.numel() for p in net.parameters()))
            states.update({f'{label}/{k}':v for k,v in parameters.items()})
        file = directory / f'{key}-{seed}.npz'
        np.savez_compressed(file, **states)
        rows.append(dict(key=key, seed=seed, file=file.name, sha256=digest(file), timings=timings))
    return rows


def fit(args):
    start = perf_counter()
    verify(args.development, PLAN['development_sha256'])
    m, _ = sources(args.source)
    designs = subsets(m.load(args.development))
    directory = args.private / 'fits'
    directory.mkdir(parents=True, exist_ok=True)
    write_json(args.private/'subsets.json', designs)
    tasks = [(args.source, args.development, args.reuse, directory, k,v) for k,v in designs.items()]
    # Forkserver/spawn workers independently cap Torch and BLAS parallelism.
    with ProcessPoolExecutor(max_workers=args.workers, initializer=configure) as pool:
        fits = [row for group in pool.map(fit_subset, tasks) for row in group]
    write_json(args.private/'fit-seal.json', dict(fits=fits, subsets_sha256=digest(args.private/'subsets.json'),
               development_sha256=digest(args.development), protocol_sha256=digest(Path(__file__).with_name('protocol.json')),
               source_sha256=digest(Path(__file__)), parallel_processes=args.workers, wall_seconds=perf_counter()-start,
               numpy=np.__version__, torch=torch.__version__, python=sys.version, cpu_affinity=sorted(os.sched_getaffinity(0))))


def score(args):
    configure()
    m,e = sources(args.source)
    seal = json.loads((args.private/'fit-seal.json').read_text())
    verify(Path(__file__),seal['source_sha256'])
    verify(Path(__file__).with_name('protocol.json'),seal['protocol_sha256'])
    verify(args.private/'subsets.json',seal['subsets_sha256'])
    designs = json.loads((args.private/'subsets.json').read_text())
    for row in seal['fits']:
        verify(args.private/'fits'/row['file'],row['sha256'])
    verify(args.assessment, PLAN['assessment_sha256'])
    a = m.load(args.assessment)
    people = np.unique(a['person'])
    if len(people) != 6 or len(a['event']) != 1759 or set(people).intersection(designs['common-18-all']['people']):
        raise ValueError('Assessment cohort overlap or wrong denominator')
    mask = np.ones(len(a['event']), bool)
    def reduce_errors(emg, path):
        loss = e.errors(a, emg, path)
        return {part:e.people_means(a,loss,mask,h).tolist() for part,h in e.PARTS.items()}
    rows = {}
    for fit in seal['fits']:
        weights = m.load(args.private/'fits'/fit['file'])
        xs = m.mapped(a, weights, 'cpu')
        scores = {}
        for name, width in VARIANTS:
            label = f'{name}_w{width}'
            prefix = label+'/'
            net = network(m,name,width).eval()
            net.load_state_dict({k[len(prefix):]:torch.from_numpy(v) for k,v in weights.items() if k.startswith(prefix)})
            with torch.inference_mode():
                scores[label] = reduce_errors(*m.decode(net(xs).numpy(), weights))
        rows.setdefault(fit['key'],{})[str(fit['seed'])] = scores
    baselines = {k:reduce_errors(a['previous_rms'],path) for k,path in (
        ('stationary', np.zeros_like(a['y_path'])), ('velocity32',a['physics'][:,2:3]*np.arange(1,33)[None,:,None]/32))}
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output/'person-scores.json', dict(metrics=list(e.METRICS), people=['A','B','C','D','E','F'],
               axes='Every array is six assessment people in a common order by three errors. Equal weight to directions in posture.',
               assessment_events=dict(both=len(mask),standing=int((a['posture']==0).sum()),walking=int((a['posture']==1).sum())),
               training_sets={k:dict(people=v['n'], windows=len(v['indices']), limit=v['limit']) for k,v in designs.items()},
               variants={f'{n}_w{w}':sum(p.numel() for p in network(m,n,w).parameters()) for n,w in VARIANTS},
               fits=rows, baselines=baselines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='stage',required=True)
    f,s = subs.add_parser('fit'),subs.add_parser('score')
    for p in (f,s):
        p.add_argument('--source',type=Path,required=True,help='Pinned paired-study balance source directory')
        p.add_argument('--private',type=Path,required=True,help='Local private fitting directory')
    f.add_argument('--development',type=Path,required=True)
    f.add_argument('--reuse',type=Path,help='Exact original local states, optional. Absence refits the same models.')
    f.add_argument('--workers',type=int,choices=range(1,5),default=4)
    s.add_argument('--assessment',type=Path,required=True)
    s.add_argument('--output',type=Path,required=True,help='Directory for aggregate scores')
    args=parser.parse_args()
    if args.stage=='fit':
        fit(args)
    else:
        score(args)


if __name__ == '__main__':
    main()
