"""Replay the registered development-only path-decoder experiment. See REPLAY.md."""
import argparse
import hashlib
import json
import os
import platform
import resource
import time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from decoder_model import create, export
from network import INPUT_KEYS, fit_scales, predict_arrays, tensors
from training import optimizer, weights

DATA_HASH = 'a11706a31bb049fcd84c81264cfbdc5497205602ceb67c0f7a69fbbf906f7590'
SEEDS = (1641, 2718, 3917)
DOMAINS = ('lower', 'upper')
JOINT = ('separate', 'matched', 'original')
METHODS = (*JOINT, 'specialist_exposure', 'specialist_steps')


def file_hash(path):
    with open(path, 'rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def array_hash(array):
    return hashlib.sha256(np.ascontiguousarray(array, dtype='<i8').tobytes()).hexdigest()


def state_hash(net):
    digest = hashlib.sha256()
    for key, value in sorted(net.state_dict().items()):
        digest.update(key.encode() + b'\0')
        digest.update(value.detach().cpu().contiguous().numpy().astype('<f4', copy=False).tobytes())
    return digest.hexdigest()


def write_json(path, obj):
    tmp = path.with_suffix('.pending')
    with open(tmp, 'w') as handle:
        json.dump(obj, handle, sort_keys=True, separators=(',', ':'), allow_nan=False)
        handle.write('\n')
    tmp.replace(path)


def write_arrays(path, arrays):
    tmp = path.with_suffix('.pending')
    with open(tmp, 'wb') as handle:
        np.savez_compressed(handle, **arrays)
    tmp.replace(path)


def inputs_only(data, rows):
    return {k: data[k][rows] for k in INPUT_KEYS}


def folds_of(data):
    result = np.full(len(data['domain']), -1, dtype=np.int64)
    for d in (0, 1):
        for rank, person in enumerate(np.unique(data['person'][data['domain'] == d])):
            result[(data['person'] == person) & (data['domain'] == d)] = rank % 3
    assert np.all(result >= 0)
    return result


def make_draws(data, train, seed):
    orders = []
    for d in (0, 1):
        subset = train[data['domain'][train] == d]
        rng = np.random.Generator(np.random.PCG64(seed + d))
        orders.append(rng.choice(subset, size=(384, 48), replace=True, p=weights(data, subset)))
    return orders


def prepare(data, folds, out):
    arrays = dict(row=np.arange(len(folds)), fold=folds)
    plan = dict(seeds=list(SEEDS), people={}, folds={}, draws={}, init={})
    for d, name in enumerate(DOMAINS):
        plan['people'][name] = {p: int(folds[(data['domain'] == d) & (data['person'] == p)][0])
                                for p in np.unique(data['person'][data['domain'] == d])}
    for fold in range(3):
        train, held = np.flatnonzero(folds != fold), np.flatnonzero(folds == fold)
        assert not set(data['person'][train]) & set(data['person'][held])
        scales = fit_scales(data, train)
        plan['folds'][str(fold)] = dict(train_rows=array_hash(train), held_rows=array_hash(held), scales=scales,
                                        held_count=len(held), train_count=len(train))
        for seed in SEEDS:
            for d, draws in enumerate(make_draws(data, train, seed)):
                key = f's{seed}-f{fold}-{DOMAINS[d]}'
                arrays[key] = draws
                plan['draws'][key] = array_hash(draws)
    for seed in SEEDS:
        plan['init'][str(seed)] = {kind: state_hash(create(kind, seed)) for kind in JOINT}
    write_arrays(out / 'splits-and-orders.npz', arrays)
    plan['split_archive_sha256'] = file_hash(out / 'splits-and-orders.npz')
    write_json(out / 'design.json', plan)


def load_fold(data, folds, output, seed, fold, device):
    plan = json.loads((output / 'design.json').read_text())
    archive = output / 'splits-and-orders.npz'
    assert file_hash(archive) == plan['split_archive_sha256']
    train, held = np.flatnonzero(folds != fold), np.flatnonzero(folds == fold)
    metadata = plan['folds'][str(fold)]
    assert array_hash(train) == metadata['train_rows'] and array_hash(held) == metadata['held_rows']
    assert fit_scales(data, train) == metadata['scales']
    with np.load(archive, allow_pickle=False) as store:
        assert np.array_equal(folds, store['fold'])
        draws = [store[f's{seed}-f{fold}-{name}'] for name in DOMAINS]
    orders = [np.searchsorted(train, draw) for draw in draws]
    for d, (raw, loc) in enumerate(zip(draws, orders)):
        assert np.array_equal(train[loc], raw) and np.all(data['domain'][raw] == d)
        assert array_hash(raw) == plan['draws'][f's{seed}-f{fold}-{DOMAINS[d]}']
    train_only = {key: data[key][train] for key in (*INPUT_KEYS, 'future_rms', 'future_path_mm')}
    batch = tensors(train_only, metadata['scales'], device)
    return train, held, metadata['scales'], batch, orders, plan['init'][str(seed)]


def sync(device):
    if device == 'cuda':
        torch.cuda.synchronize()


def fit_steps(model, batch, indices, opt, device, track, train_rows):
    model.train()
    ids = torch.as_tensor(indices, device=device)
    params = dict(model.named_parameters())
    seen = {k: torch.zeros_like(v, dtype=torch.bool) for k, v in params.items()} if track else {}
    losses = []
    norms = []
    sync(device)
    start = time.perf_counter()
    for rows in ids:
        pred_rms, pred_path = model([x[rows] for x in batch[:8]])
        mask = batch[1][rows]
        amplitudes = (F.smooth_l1_loss(pred_rms, batch[-2][rows], reduction='none') * mask).sum(1) / mask.sum(1)
        paths = F.smooth_l1_loss(pred_path, batch[-1][rows], reduction='none').mean((1, 2))
        loss = .5 * (amplitudes + paths).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if track:
            for name, param in params.items():
                seen[name] |= param.grad.detach() != 0
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        losses.append(loss.detach())
        norms.append(norm.detach())
        opt.step()
    sync(device)
    elapsed = time.perf_counter() - start
    loss_trace = torch.stack(losses).cpu().numpy()
    norm_trace = torch.stack(norms).cpu().numpy()
    assert np.isfinite(loss_trace).all() and np.isfinite(norm_trace).all()
    raw = train_rows[indices]
    counts = torch.bincount(batch[0][ids.flatten()].cpu(), minlength=2).tolist()
    return dict(updates=len(indices), examples=int(indices.size), examples_by_domain=counts,
                unique_events=int(len(np.unique(raw))), ordered_global_rows_sha256=array_hash(raw),
                fit_seconds=elapsed, loss_trace=loss_trace.tolist(), max_preclip_norm=float(norm_trace.max())), seen


def paired(orders):
    half = [arr[:192].reshape(384, 24) for arr in orders]
    return np.concatenate(half, axis=1)


@torch.no_grad()
def check_initial(model, batch, ids, expected):
    actual = model([x[ids] for x in batch[:8]])
    assert all(torch.equal(x, y) for x, y in zip(actual, expected))


def system_info(device):
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None
    return dict(torch=str(torch.__version__), numpy=np.__version__, python=platform.python_version(),
                hip=torch.version.hip, device=device, gpu=torch.cuda.get_device_name() if device == 'cuda' else None,
                threads=torch.get_num_threads(), interop=torch.get_num_interop_threads(), affinity=affinity,
                env={k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                gpu_peak_bytes=torch.cuda.max_memory_allocated() if device == 'cuda' else None)


def state_path(output, seed, fold, name):
    return output / 'fits' / f's{seed}-f{fold}-{name}.npz'


def save_run(model, seen, logs, output, seed, fold, name, initial, scales):
    filename = state_path(output, seed, fold, name)
    params = {k: t.detach().cpu().numpy() for k, t in model.named_parameters()}
    write_arrays(filename, params)
    counts = {k: int(v.size) for k, v in params.items()}
    active = {k: int(v.sum().item()) for k, v in seen.items()}
    if name in ('separate', 'matched') and seed == 1641:
        write_json(filename.with_suffix('.json'), export(model, scales))
    return dict(initial_sha256=initial, final_sha256=state_hash(model), file_sha256=file_hash(filename),
                parameters=sum(counts.values()), per_tensor_parameters=counts, active_loss_gradients=sum(active.values()),
                per_tensor_active_loss_gradients=active, updates=sum(s['updates'] for s in logs),
                examples=sum(s['examples'] for s in logs), examples_by_domain=np.sum([s['examples_by_domain'] for s in logs], axis=0).tolist(),
                fit_seconds=sum(s['fit_seconds'] for s in logs), segments=logs)


def fit_fold(data, folds, args, seed, fold):
    receipt = args.output / 'fits' / f'seed-{seed}-fold-{fold}.json'
    if receipt.exists():
        prior = json.loads(receipt.read_text())
        for name, record in prior['runs'].items():
            assert file_hash(state_path(args.output, seed, fold, name)) == record['file_sha256']
        return
    start = time.perf_counter()
    train, held, scales, batch, orders, initial = load_fold(data, folds, args.output, seed, fold, args.device)
    joint_ids = paired(orders)
    probe = torch.as_tensor(joint_ids[0], device=args.device)
    with torch.no_grad():
        original = create('original', seed).to(args.device)
        expected = original([x[probe] for x in batch[:8]])
    runs = {}
    for kind in JOINT:
        model = create(kind, seed).to(args.device)
        assert state_hash(model) == initial[kind]
        check_initial(model, batch, probe, expected)
        result, seen = fit_steps(model, batch, joint_ids, optimizer(model), args.device, True, train)
        runs[kind] = save_run(model, seen, [result], args.output, seed, fold, kind, initial[kind], scales)
        assert runs[kind]['parameters'] == (3924 if kind == 'original' else 3975)
    for d, domain in enumerate(DOMAINS):
        model = create('original', seed).to(args.device)
        assert state_hash(model) == initial['original']
        opt = optimizer(model)
        prefix, seen = fit_steps(model, batch, orders[d][:192], opt, args.device, True, train)
        name = domain + '-exposure'
        runs[name] = save_run(model, seen, [prefix], args.output, seed, fold, name, initial['original'], scales)
        extra, seen_new = fit_steps(model, batch, orders[d][192:], opt, args.device, True, train)
        name = domain + '-steps'
        runs[name] = save_run(model, {k: seen[k] | seen_new[k] for k in seen}, [prefix, extra],
                              args.output, seed, fold, name, initial['original'], scales)
    write_json(receipt, dict(seed=seed, fold=fold, train_rows_sha256=array_hash(train), held_rows_sha256=array_hash(held),
                             exact_initial_outputs_on_balanced_train_probe=True, scales=scales, runs=runs,
                             process=system_info(args.device), elapsed_seconds=time.perf_counter()-start))
    print(f'Completed seed {seed}, fold {fold}', flush=True)


def load_saved(output, seed, fold, name, record):
    filename = state_path(output, seed, fold, name)
    assert file_hash(filename) == record['file_sha256']
    model = create(name if name in JOINT else 'original', seed)
    with np.load(filename, allow_pickle=False) as source:
        model.load_state_dict({k: torch.from_numpy(source[k]) for k in source.files})
    assert state_hash(model) == record['final_sha256']
    return model.eval()


def predict_seed(data, folds, args, seed):
    out = args.output / f'oof-seed-{seed}.npz'
    meta = out.with_suffix('.json')
    if meta.exists():
        assert file_hash(out) == json.loads(meta.read_text())['sha256']
        return
    rows = np.arange(len(folds))
    results = dict(row=rows, fold=folds)
    timings = {}
    for kind in METHODS:
        results[kind+'_rms'] = np.full((len(rows), 13), np.nan)
        results[kind+'_path'] = np.full((len(rows), 32, 3), np.nan)
    for fold in range(3):
        receipt = json.loads((args.output / 'fits' / f'seed-{seed}-fold-{fold}.json').read_text())
        held = np.flatnonzero(folds == fold)
        assert array_hash(held) == receipt['held_rows_sha256']
        for name, record in receipt['runs'].items():
            model = load_saved(args.output, seed, fold, name, record)
            if name in JOINT:
                valid, kind = held, name
            else:
                domain, budget = name.split('-')
                valid = held[data['domain'][held] == DOMAINS.index(domain)]
                kind = 'specialist_' + budget
            start = time.perf_counter()
            rms, path = predict_arrays(model, inputs_only(data, valid), receipt['scales'])
            timings[f'f{fold}-{name}'] = dict(events=len(valid), seconds=time.perf_counter()-start)
            assert np.all(rms[~data['muscle_mask'][valid]] == 0) and np.all(rms >= 0)
            assert np.isnan(results[kind+'_rms'][valid]).all()
            results[kind+'_rms'][valid], results[kind+'_path'][valid] = rms, path
    assert all(np.isfinite(value).all() for value in results.values())
    write_arrays(out, results)
    write_json(meta, dict(seed=seed, rows=len(rows), sha256=file_hash(out), shapes={k:list(v.shape) for k,v in results.items()},
                          inference_by_fold_and_model=timings, process=system_info('cpu')))


def bench(data, folds, args):
    seed, fold = SEEDS[0], 0
    train, _, scales, batch, orders, initial = load_fold(data, folds, args.output, seed, fold, args.device)
    seq = paired(orders)[:16]
    records = {}
    for kind in ('separate', 'matched'):
        model = create(kind, seed).to(args.device)
        assert state_hash(model) == initial[kind]
        record, _ = fit_steps(model, batch, seq, optimizer(model), args.device, True, train)
        rms, path = predict_arrays(model.eval(), inputs_only(data, train[seq[0]]), scales)
        records[kind] = dict(seconds=record['fit_seconds'], loss=record['loss_trace'], rms=rms.tolist(), path=path.tolist())
    write_json(args.output / f'bench-{args.device}{args.threads}.json', dict(records=records, process=system_info(args.device)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'bench', 'fit', 'predict'])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--threads', type=int, choices=(1, 3), default=3)
    parser.add_argument('--seed', type=int, choices=SEEDS)
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    assert file_hash(args.data) == DATA_HASH
    if args.stage != 'bench':
        assert (args.device, args.threads) == ('cpu', 3)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'fits').mkdir(exist_ok=True)
    with np.load(args.data, allow_pickle=False) as data_file:
        keys = (*INPUT_KEYS, 'person') if args.stage in ('prepare', 'predict') else (*INPUT_KEYS, 'person', 'future_rms', 'future_path_mm')
        data = {k:data_file[k] for k in keys}
    folds = folds_of(data)
    assert np.bincount(data['domain']).tolist() == [5179, 1764]
    if args.stage == 'prepare':
        prepare(data, folds, args.output)
    elif args.stage == 'bench':
        bench(data, folds, args)
    else:
        for seed in (SEEDS if args.seed is None else [args.seed]):
            if args.stage == 'fit':
                for fold in range(3):
                    fit_fold(data, folds, args, seed, fold)
            else:
                predict_seed(data, folds, args, seed)


if __name__ == '__main__':
    main()
