"""Reproduce the person partitions, fits and native held forecasts for the scalp study."""
import hashlib
import json
import os
import platform
try:
    import resource
except ImportError:  # Windows
    resource = None
import time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from fusion_model import KINDS, create, export, predict_batch
from network import INPUT_KEYS, SharedNet, fit_scales, predict_arrays, tensors
from scalp_inputs import fit_normalizers, load_inputs, tokens

SEEDS = (1641, 2718, 3917)
LABELS = ('future_rms', 'future_path_mm')
DOMAINS = ('lower', 'upper')
REUSED = ('original', 'specialist_exposure', 'specialist_steps')


def digest(path):
    with open(path, 'rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def row_hash(rows):
    return hashlib.sha256(np.ascontiguousarray(rows, dtype='<i8').tobytes()).hexdigest()


def state_hash(net):
    h = hashlib.sha256()
    for key, value in sorted(net.state_dict().items()):
        h.update(key.encode() + b'\0')
        h.update(value.detach().cpu().contiguous().numpy().astype('<f4', copy=False).tobytes())
    return h.hexdigest()


def write(path, data):
    temp = path.with_suffix('.pending')
    if path.suffix == '.npz':
        with temp.open('wb') as handle:
            np.savez_compressed(handle, **data)
    else:
        temp.write_text(json.dumps(data, indent=1, allow_nan=False)+'\n')
    temp.replace(path)


def load(path):
    return json.loads(path.read_text())


def select(data, rows, labels=False):
    keys = (*INPUT_KEYS, *LABELS) if labels else INPUT_KEYS
    return {k:data[k][rows] for k in keys}


def study_draws(data, train, seed, domain):
    pool = train[data['domain'][train] == domain]
    people, sessions, direction = (data[k][pool] for k in ('person','session','direction'))
    weight = np.zeros(len(pool))
    for who in np.unique(people):
        person = people == who
        conditions = np.unique(sessions[person])
        for condition in conditions:
            series = person & (sessions == condition)
            cues = np.unique(direction[series])
            for cue in cues:
                group = series & (direction == cue)
                weight[group] = 1/(len(conditions)*len(cues)*int(group.sum()))
    return np.random.Generator(np.random.PCG64(seed+domain)).choice(
        pool, size=(384,48), replace=True, p=weight/weight.sum())


def design(data, inputs, folds, args, prior):
    arrays = dict(fold=folds, row=np.arange(len(folds)), donor=inputs.donor)
    plans = {}
    with np.load(args.prior/'splits-and-orders.npz', allow_pickle=False) as old_rows:
        assert np.array_equal(old_rows['fold'], folds)
        for f in range(3):
            train, held = np.flatnonzero(folds!=f), np.flatnonzero(folds==f)
            sc = fit_scales(data, train)
            old = prior['folds'][str(f)]
            assert sc == old['scales'] and row_hash(train)==old['train_rows'] and row_hash(held)==old['held_rows']
            plans[str(f)] = dict(scales=sc, scalp_scales=fit_normalizers(inputs,train),
                                 train_sha256=row_hash(train), held_sha256=row_hash(held))
            for seed in SEEDS:
                half = []
                for d,name in enumerate(DOMAINS):
                    key = f's{seed}-f{f}-{name}'
                    draws = study_draws(data,train,seed,d)
                    assert np.array_equal(draws,old_rows[key]) and row_hash(draws)==prior['draws'][key]
                    half.append(draws[:192].reshape(384,24))
                arrays[f's{seed}-f{f}'] = np.concatenate(half,axis=1)
    write(args.out/'splits.npz',arrays)
    init = {}
    for seed in SEEDS:
        net = create(seed)
        assert sum(t.numel() for t in net.parameters())==4068
        torch.manual_seed(seed)
        base = SharedNet()
        assert state_hash(base)==prior['init'][str(seed)]['original']
        assert all(torch.equal(v,net.state_dict()[k]) for k,v in base.state_dict().items())
        init[str(seed)] = state_hash(net)
    write(args.out/'design.json', dict(folds=plans, initial=init, splits_sha256=digest(args.out/'splits.npz')))


def settings(device):
    return dict(torch=str(torch.__version__), numpy=np.__version__, python=platform.python_version(),
                device=device, hip=torch.version.hip, gpu=torch.cuda.get_device_name() if device=='cuda' else None,
                intraop=torch.get_num_threads(), interop=torch.get_num_interop_threads(),
                affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
                pools={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS')},
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource is not None else None,
                peak_gpu_bytes=torch.cuda.max_memory_allocated() if device=='cuda' else None)


def parts(kind):
    return ('central','reference') if kind=='reference' else (kind,'real')


def sync(device):
    if device=='cuda':
        torch.cuda.synchronize()


def train_branch(model, batch, electrical, draws, device):
    ids = torch.as_tensor(draws,device=device)
    params = dict(model.named_parameters())
    active = {k:torch.zeros_like(p,dtype=torch.bool) for k,p in params.items()}
    opt = torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.0001)
    losses, norms = [], []
    sync(device)
    start = time.perf_counter()
    for rows in ids:
        rms,path = model([v[rows] for v in batch[:8]],electrical[rows])
        muscle = (F.smooth_l1_loss(rms,batch[-2][rows],reduction='none')*batch[1][rows]).sum(1)/batch[1][rows].sum(1)
        marker = F.smooth_l1_loss(path,batch[-1][rows],reduction='none').mean((1,2))
        loss = .5*(muscle+marker).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        for k,p in params.items():
            active[k] |= p.grad.detach() != 0
        norms.append(torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True).detach())
        losses.append(loss.detach())
        opt.step()
    sync(device)
    elapsed = time.perf_counter()-start
    loss = torch.stack(losses).cpu().numpy()
    assert np.isfinite(loss).all()
    return dict(seconds=elapsed, losses=loss.tolist(), max_preclip_norm=float(torch.stack(norms).max().cpu()),
                nonzero_gradient_counts={k:int(a.sum().item()) for k,a in active.items()})


def run_fit(data, inputs, folds, plan, splits, seed, fold, args, bench=False):
    train = np.flatnonzero(folds!=fold)
    raw = splits[f's{seed}-f{fold}']
    draws = np.searchsorted(train,raw)
    assert np.array_equal(train[draws],raw)
    assert np.all(data['domain'][raw[:,:24]]==0) and np.all(data['domain'][raw[:,24:]]==1)
    sc = plan['folds'][str(fold)]
    assert row_hash(train)==sc['train_sha256'] and fit_normalizers(inputs,train)==sc['scalp_scales']
    batch = tensors(select(data,train,True),sc['scales'],args.device)
    probe = torch.as_tensor(draws[0],device=args.device)
    torch.manual_seed(seed)
    base = SharedNet().to(args.device).eval()
    with torch.no_grad():
        probe_in = [a[probe] for a in batch[:8]]
        initial_out = base(probe_in)
    for kind in (('central',) if bench else KINDS):
        out = args.out/'checkpoints'/f's{seed}-f{fold}-{kind}.npz'
        if not bench and out.with_suffix('.json').is_file():
            assert digest(out)==load(out.with_suffix('.json'))['sha256']
            continue
        branch,mode = parts(kind)
        electric = tokens(inputs,sc['scalp_scales'],train,branch,mode=mode)
        x = torch.as_tensor(electric,device=args.device,dtype=torch.float32)
        net = create(seed).to(args.device)
        assert state_hash(net)==plan['initial'][str(seed)]
        with torch.no_grad():
            assert all(torch.equal(a,b) for a,b in zip(net(probe_in,x[probe]),initial_out))
        chosen = draws[:16] if bench else draws
        log = train_branch(net,batch,x,chosen,args.device)
        if bench:
            rr,pp=predict_batch(net.eval(),select(data,raw[0]),sc['scales'],electric[draws[0]])
            write(args.out/f'benchmark-{args.device}{args.threads}.json',
                  dict(log=log,rms=rr.tolist(),path=pp.tolist(),settings=settings(args.device)))
            return
        write(out,{k:v.detach().cpu().numpy() for k,v in net.state_dict().items()})
        write(out.with_suffix('.json'),dict(seed=seed,fold=fold,kind=kind,
              rows_sha256=row_hash(raw),init=plan['initial'][str(seed)],final=state_hash(net),
              sha256=digest(out),parameters=sum(p.numel() for p in net.parameters()),
              updates=len(chosen),examples_by_domain=[9216,9216],initial_outputs_exact=True,log=log))
        if seed==1641 and fold==0:
            write(args.out/f'model-{kind}.json',export(net,kind,sc['scales'],sc['scalp_scales']))
        print('Fit',seed,fold,kind,flush=True)


def from_state(model, file):
    with np.load(file,allow_pickle=False) as z:
        model.load_state_dict({k:torch.from_numpy(z[k]) for k in z.files})
    return model.eval()


def predict_seed(data, inputs, folds, plan, seed, args, prior_manifest):
    out = args.out/f'oof-seed-{seed}.npz'
    if out.with_suffix('.json').is_file():
        assert digest(out)==load(out.with_suffix('.json'))['sha256']
        return
    n=len(folds)
    results=dict(row=np.arange(n),fold=folds)
    for kind in (*KINDS,'wrong_trial',*REUSED):
        results[kind+'_support']=np.zeros(n,dtype=bool)
        results[kind+'_rms']=np.full((n,13),np.nan)
        results[kind+'_path']=np.full((n,32,3),np.nan)
    old=args.prior/f'oof-seed-{seed}.npz'
    assert digest(old)==prior_manifest[old.name]
    archive_errors={}
    with np.load(old,allow_pickle=False) as archive:
        assert np.array_equal(archive['fold'],folds) and np.array_equal(archive['row'],results['row'])
        for fold in range(3):
            held=np.flatnonzero(folds==fold)
            sc=plan['folds'][str(fold)]
            assert row_hash(held)==sc['held_sha256']
            for kind in (*KINDS,'wrong_trial'):
                branch,mode = ('central','wrong') if kind=='wrong_trial' else parts(kind)
                rows=held[inputs.mask[branch][held].any(axis=1)]
                if mode=='wrong':
                    rows=rows[inputs.donor[rows]>=0]
                    assert np.array_equal(inputs.mask[branch][rows],inputs.mask[branch][inputs.donor[rows]])
                file=args.out/'checkpoints'/f"s{seed}-f{fold}-{'central' if mode=='wrong' else kind}.npz"
                receipt=load(file.with_suffix('.json'))
                assert digest(file)==receipt['sha256']
                net=from_state(create(seed),file)
                assert state_hash(net)==receipt['final']
                electric=tokens(inputs,sc['scalp_scales'],rows,branch,mode=mode)
                r,p=predict_batch(net,select(data,rows),sc['scales'],electric)
                results[kind+'_rms'][rows],results[kind+'_path'][rows]=r,p
                results[kind+'_support'][rows]=True
            old_receipt_file=args.prior/'fits'/f'seed-{seed}-fold-{fold}.json'
            assert digest(old_receipt_file)==prior_manifest['fits/'+old_receipt_file.name]
            old_receipt=load(old_receipt_file)
            assert old_receipt['scales']==sc['scales']
            for kind in REUSED:
                for d in ((None,) if kind=='original' else (0,1)):
                    name=kind if d is None else DOMAINS[d]+'-'+kind.split('_')[1]
                    rows=held if d is None else held[data['domain'][held]==d]
                    file=args.prior/'fits'/f's{seed}-f{fold}-{name}.npz'
                    rr=old_receipt['runs'][name]
                    assert digest(file)==rr['file_sha256']==prior_manifest['fits/'+file.name]
                    net=from_state(SharedNet(),file)
                    assert state_hash(net)==rr['final_sha256']
                    r,p=predict_arrays(net,select(data,rows),sc['scales'])
                    errors=[]
                    for suffix,actual in (('rms',r),('path',p)):
                        recorded=archive[kind+'_'+suffix][rows]
                        errors.append(float(np.max(np.abs(actual-recorded))))
                        assert np.array_equal(actual,recorded)
                        results[kind+'_'+suffix][rows]=recorded
                    results[kind+'_support'][rows]=True
                    archive_errors[f'{fold}-{name}']=errors
    counts={}
    for kind in (*KINDS,'wrong_trial',*REUSED):
        support,r,p=(results[kind+'_'+x] for x in ('support','rms','path'))
        assert np.isfinite(r[support]).all() and np.isfinite(p[support]).all()
        assert np.isnan(r[~support]).all() and np.isnan(p[~support]).all()
        assert np.all(r[support]>=0) and np.all(r[support][~data['muscle_mask'][support]]==0)
        counts[kind]=[int(np.sum(support & (data['domain']==d))) for d in (0,1)]
    write(out,results)
    write(out.with_suffix('.json'),dict(seed=seed,rows=n,sha256=digest(out),
          supports_by_domain=counts,archived_native_max_abs=archive_errors,settings=settings('cpu')))
    print('Produced held forecasts',seed,flush=True)
