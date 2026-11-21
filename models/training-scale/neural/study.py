"""Fit/scoring entry point for source replacement by nested unique origin counts."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize

from prepare import HERE, RETINA, ref

PROTOCOL = json.loads((HERE/'protocol.json').read_text())
SEEDS = PROTOCOL['training']['sample_seeds']
SIZES = PROTOCOL['training']['sizes']
HELD = ('ER1','turtle','turtle_declared')
FEATURE_NAMES = ['log_count','trace_10ms','trace_100ms','trace_1000ms','last_bin_fired']
KNOTS = [(1.0,3.0),(.25,.8),(.5,1.5),(.8,2.)]


def design(x, nonlinear):
    if not nonlinear:
        return x
    out = np.empty((*x.shape[:-1],13),dtype=np.float64)
    out[:,:,:5] = x
    for i, pair in enumerate(KNOTS):
        for j, knot in enumerate(pair):
            np.maximum(0,x[:,:,i]-knot,out=out[:,:,5+2*i+j])
    return out


def membership(rows, seed, n, arm):
    groups = [['JS14']] if arm=='rat' else [['JS14'], RETINA]
    selection = {}
    for stream, families in enumerate(groups):
        pool = [r for r in rows if r['family'] in families]
        lengths = np.array([r['qc']['resolved_targets'] for r in pool], dtype=np.int64)
        take = n if arm=='rat' else n//2
        rng = np.random.default_rng(np.random.SeedSequence([seed,stream]))
        if take > lengths.sum():
            raise ValueError('Insufficient distinct training origins')
        idx = np.sort(rng.permutation(lengths.sum())[:take])
        edges = np.r_[0,np.cumsum(lengths)]
        for row,a,b in zip(pool,edges[:-1],edges[1:],strict=True):
            selection[row['key']] = idx[np.searchsorted(idx,a):np.searchsorted(idx,b)]-a
    return selection


def matrices(cache, rows, selected, nonlinear):
    sources = defaultdict(list)
    membership_hashes = {}
    for r in rows:
        local = selected.get(r['key'])
        if local is None or not len(local):
            continue
        key = r['key']
        if r['family'] not in ('JS14',*RETINA):
            raise ValueError('Held sample admitted to fitting')
        x = np.load(cache/f'{key}-x.npy',mmap_mode='r')[local]
        y = np.load(cache/f'{key}-y.npy',mmap_mode='r')[local]
        o = np.load(cache/f'{key}-o.npy',mmap_mode='r')[local]
        membership_hashes[key] = dict(origins=len(o),sha256=hashlib.sha256(o.astype('<i8').tobytes()).hexdigest())
        sources[r['family']].append((x,y))
    packs = []
    for items in sources.values():
        x = design(np.concatenate([v[0] for v in items]),nonlinear)
        y = np.concatenate([v[1] for v in items]); rows = np.arange(len(y))
        target = x[rows,y,:].sum(axis=0)
        packs.append((x.reshape(-1,x.shape[-1]), y, x.shape[1], target))
        items.clear()
    return packs, membership_hashes


def fit(cache, inventory, n, arm, seed, kind):
    start = time.perf_counter()
    selected = membership(inventory,seed,n,arm)
    packs, groups = matrices(cache,inventory,selected,kind=='hinge13')
    dim = packs[0][0].shape[-1]
    if sum(len(y) for _,y,_,_ in packs) != n:
        raise ValueError('Training size mismatch')
    def objective(w):
        loss = 0.
        grad = np.zeros_like(w)
        for x,y,k,observed in packs:
            logits = (x@w).reshape(-1,k)
            logp = ref.logprobs(logits)
            loss -= logp[np.arange(len(y)),y].sum()
            grad += np.exp(logp).ravel() @ x - observed
        return loss/n + 0.00005 * (w@w), grad/n + 0.0001*w
    if n==54578 and arm=='rat' and kind=='linear5':
        original = json.loads((HERE/'reference-weights.json').read_text())
        w = np.array(original['weights'])
        loss,grad = objective(w)
        if abs(loss-original['training_objective'])>1e-10 or np.max(np.abs(grad))>1e-5:
            raise ValueError('Legacy full rat reference differs from rebuilt objective')
        nit = original['iterations']; status = 'original verified against reconstructed loss and gradient'
    else:
        opt = minimize(objective,np.zeros(dim),method='L-BFGS-B',jac=True,
                       options=dict(maxiter=250,ftol=1e-10,gtol=1e-7))
        if not opt.success:
            raise RuntimeError(f'Fit failed: {n} {arm} {seed} {kind}: {opt.message}')
        w,loss,grad,nit,status = opt.x,opt.fun,opt.jac,int(opt.nit),str(opt.message)
    return dict(n=n,arm=arm,seed=seed,kind=kind,weights=w.tolist(),train_objective=float(loss),
                max_abs_gradient=float(np.max(np.abs(grad))),iterations=nit,optimizer_status=status,
                groups=groups,fit_seconds=time.perf_counter()-start)


def metric_arrays(values,y):
    average = values.mean(axis=0)
    counts = np.bincount(y)
    units = np.flatnonzero(counts)
    unit = np.column_stack([np.bincount(y,weights=col,minlength=len(counts))[units]/counts[units]
                            for col in values.T])
    return dict(log_loss=float(average[0]),top1=float(average[1]),mean_rank=float(average[2]),
                unit_balanced_log_loss=float(unit[:,0].mean()),unit_balanced_top1=float(unit[:,1].mean()))


def assess(cache, inventory, models):
    outputs = {}
    for family in HELD:
        held = [r for r in inventory if r['family']==family]
        per_case = defaultdict(list); labels = []; ordinals = []
        for r in held:
            key = r['key']; x=np.load(cache/f'{key}-x.npy',mmap_mode='r'); y=np.load(cache/f'{key}-y.npy')
            o = np.load(cache/f'{key}-o.npy'); labels.append(y); ordinals.append(o)
            expanded=design(x,True)
            for name,m in models.items():
                if name=='uniform':
                    logits=np.zeros(x.shape[:2])
                elif name=='rate':
                    logits=x[:,:,0]
                elif name=='recency':
                    logits=x[:,:,0]+x[:,:,2]
                else:
                    matrix=expanded if m['kind']=='hinge13' else x
                    logits=(matrix.reshape(-1,matrix.shape[-1])@np.asarray(m['weights'])).reshape(x.shape[:2])
                per_case[name].append(ref.row_scores(logits,y))
        all_y=np.concatenate(labels); order=np.concatenate(ordinals); result={}
        for name,vals in per_case.items():
            v=np.concatenate(vals)
            trial_metrics=[dict(trial=r['trial'],rows=len(y),**metric_arrays(a,y)) for r,a,y in zip(held,vals,labels,strict=True) if len(y)]
            trial_average={k:float(np.mean([t[k] for t in trial_metrics])) for k in metric_arrays(v,all_y)}
            bands={b:metric_arrays(v[mask],all_y[mask]) for b,mask in [('1-10',order<=10),('11-100',(order>10)&(order<=100)),('101+',order>100)] if mask.any()}
            result[name]=dict(equal_trial=trial_average,pooled=metric_arrays(v,all_y),by_trial=trial_metrics,by_ordinal=bands)
        outputs[family]=result
    return outputs


def model_key(n,arm,seed,kind):
    return f'{n}-{arm}-{seed}-{kind}'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('fit','score')); p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); p.add_argument('--n',type=int,choices=SIZES,required=True)
    p.add_argument('--arm',choices=('rat','mixed')); p.add_argument('--seed',type=int,choices=SEEDS)
    args=p.parse_args(); inv=json.loads((args.cache/'groups.json').read_bytes())['rows']
    args.out.mkdir(parents=True,exist_ok=True)
    if args.n==SIZES[-1]:
        sealed = args.out/'prediction-seal.json'
        if not sealed.exists() or json.loads(sealed.read_text())['prediction_sha256']!=ref.digest(args.out/'prediction.json'):
            raise ValueError('Missing or mismatched small-run prediction seal')
    if args.stage=='fit':
        if args.arm is None or args.seed is None:
            p.error('fit needs arm and seed')
        for kind in ('linear5','hinge13'):
            key=model_key(args.n,args.arm,args.seed,kind); dest=args.out/f'fit-{key}.json'
            if args.n==SIZES[-1] and args.arm=='rat' and args.seed!=SEEDS[0]:
                raise ValueError('Full rat fit identical across seeds; reuse seed 11')
            print(key,flush=True); ref.dump(dest,fit(args.cache,inv,args.n,args.arm,args.seed,kind))
    else:
        models={'uniform':{},'rate':{},'recency':{}}
        for arm in ('rat','mixed'):
            for seed in SEEDS:
                for kind in ('linear5','hinge13'):
                    key=model_key(args.n,arm,seed,kind)
                    src=model_key(args.n,arm,SEEDS[0] if args.n==SIZES[-1] and arm=='rat' else seed,kind)
                    models[key]=json.loads((args.out/f'fit-{src}.json').read_bytes())
        ref.dump(args.out/f'scores-{args.n}.json',assess(args.cache,inv,models))


if __name__=='__main__':
    main()
