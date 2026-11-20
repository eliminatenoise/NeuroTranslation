"""Fit every frozen arm using training packets only; completed fits are never overwritten."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

import numpy as np
import torch
from torch.nn import functional as F

from methods import (ARMS, DOMAINS, SEEDS, SOURCE, STEPS, arm_indices, array_hash,
                     digest, fit_ridges, load_data, schedule)
from network import SharedMotion
from predict import physical_features

HERE = Path(__file__).resolve().parent


def setup(threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


def tensors(data):
    z, recent = physical_features(data['x'])
    domain = np.array([DOMAINS.index(s) for s in data['domain']])
    return tuple(torch.as_tensor(x, dtype=torch.float32) for x in
                 (z, np.log1p(recent), np.log1p(data['y']))) + (torch.as_tensor(domain),)


def state_digest(net):
    h = hashlib.sha256()
    for key, tensor in net.state_dict().items():
        h.update(key.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def fit_arm(data, seed, arm, batches, steps, capture_gradient):
    x, base, target, domains = data
    torch.manual_seed(seed)
    model = SharedMotion()
    initial_hash = state_digest(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001, foreach=False)
    grad, losses = {}, []
    t = time.perf_counter()
    for step, batch in enumerate(batches[:steps]):
        ix = torch.as_tensor(batch.copy())
        answer = model(x[ix], base[ix], domains[ix])
        each = F.smooth_l1_loss(answer, target[ix], beta=.2, reduction='none')
        if arm == 'joint':
            domain_losses = [each[domains[ix] == i].mean() * .5 for i in range(len(DOMAINS))]
            loss = sum(domain_losses)
            if capture_gradient and step == 1:
                for d, component in zip(DOMAINS, domain_losses):
                    qkv, readout = torch.autograd.grad(component, (model.blocks[0].qkv.weight,
                                                       model.readout.weight), retain_graph=True)
                    grad[d] = dict(step_index=step, after_updates=1, common_parameter='blocks.0.qkv.weight',
                                   common_l2=float(qkv.norm()), head_l2=readout.norm(dim=1).tolist())
        else:
            loss = each.mean() * .5
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    return model, dict(initial_state_sha256=initial_hash, final_state_sha256=state_digest(model),
                       train_seconds=time.perf_counter()-t, optimizer_updates=steps,
                       loss_trace_sha256=hashlib.sha256(np.array(losses,dtype='<f8').tobytes()).hexdigest(),
                       initial_loss=losses[0], last_loss=losses[-1], gradients=grad)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--train', type=Path, default=SOURCE/'train.npz')
    p.add_argument('--out', type=Path, default=HERE/'fits')
    p.add_argument('--threads', type=int, required=True)
    p.add_argument('--probe', action='store_true')
    args = p.parse_args()
    setup(args.threads)
    data = load_data(args.train, 'train')
    arr = tensors(data)
    if args.probe:
        plan = schedule(data, SEEDS[0])
        model, info = fit_arm(arr, SEEDS[0], 'joint', arm_indices(plan, 'joint'), 24, False)
        print(json.dumps(dict(threads=torch.get_num_threads(), interop=torch.get_num_interop_threads(),
                              torch=str(torch.__version__), cuda=torch.cuda.is_available(), hip=torch.version.hip,
                              omp=os.getenv('OMP_NUM_THREADS'), blas=os.getenv('OPENBLAS_NUM_THREADS'),
                              affinity=sorted(os.sched_getaffinity(0)), **info)))
        return
    args.out.mkdir(exist_ok=True, parents=True)
    provenance = {'train_sha256':digest(args.train), 'source':{p:digest(HERE/p) for p in
                  ('network.py','train.py','methods.py','predict.py','protocol.json','release-amendment.json')},
                  'threads':torch.get_num_threads(), 'interop':torch.get_num_interop_threads(),
                  'torch':str(torch.__version__), 'numpy':np.__version__}
    path = args.out/'provenance.json'
    if path.exists() and json.loads(path.read_text()) != provenance:
        raise ValueError('Existing fit provenance differs; use a new output directory')
    path.write_text(json.dumps(provenance, indent=2))
    for seed in SEEDS:
        plan = schedule(data, seed)
        for arm in ARMS:
            path = args.out/f'{seed}-{arm}.npz'
            receipt = path.with_suffix('.json')
            if path.exists() or receipt.exists():
                if not (path.exists() and receipt.exists() and digest(path)==json.loads(receipt.read_text())['checkpoint_sha256']):
                    raise ValueError('Incomplete/mismatched prior fit; inspect before resumption')
                continue
            indices = arm_indices(plan, arm)
            model, info = fit_arm(arr, seed, arm, indices, STEPS, arm=='joint')
            model.save(path)
            counts = {}
            for d in DOMAINS:
                seen = indices[data['domain'][indices]==d]
                counts[d] = dict(opportunities=int(seen.size), unique_rows=int(np.unique(seen).size),
                                 unique_groups=int(np.unique(data['group'][seen]).size),
                                 ordered_row_index_sha256=array_hash(seen))
            info.update(seed=seed, arm=arm,
                        fitted_parameter_slots=sum(p.numel() for p in model.parameters()),
                        exposures=counts, batch_indices_sha256=array_hash(indices),
                        checkpoint_sha256=digest(path))
            # Both readout rows are stored. A solo model receives loss through only one row.
            receipt.write_text(json.dumps(info, indent=2))
            print(f'Completed {seed} {arm}', flush=True)
    for d in DOMAINS:
        path = args.out/f'ridge-{d}.npz'
        if not path.exists():
            use = data['domain']==d
            np.savez_compressed(path, **fit_ridges(data['x'][use], data['y'][use], data['group'][use]))
    shutil.copyfile(args.out/f'{SEEDS[0]}-joint.npz',args.out/'shared-weights.npz')


if __name__ == '__main__':
    main()
