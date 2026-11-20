"""Frozen bounded training, balanced target draws, shared-trunk transfer and benchmarks."""
import argparse
import copy
import hashlib
import json
import resource
import time
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F
from interface import fixture
from network import SharedNet, INPUT_KEYS, fit_scales, tensors, export, predict_arrays, save_json, fingerprint
from donors import match

SEED=1641
STEPS=192
BATCH=48


def weights(data,ids):
    people=data['person'][ids]
    session=data['session'][ids]
    cue=data['direction'][ids]
    out=np.zeros(len(ids))
    for p in np.unique(people):
        who=people==p
        sessions=np.unique(session[who])
        for s in sessions:
            ss=who&(session==s)
            dirs=np.unique(cue[ss])
            for direction in dirs:
                g=ss&(cue==direction)
                out[g]=1/(len(sessions)*len(dirs)*int(g.sum()))
    return out/out.sum()


def draws(data,ids,d,n=STEPS*2):
    selected=ids[data['domain'][ids]==d]
    prob=weights(data,selected)
    return np.random.default_rng(SEED+d).choice(selected,size=(n,BATCH),replace=True,p=prob)


def fresh(device):
    torch.manual_seed(SEED)
    return SharedNet().to(device)


def optimizer(model):
    return torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.0001)


def run(model,t,indices,opt,target_map=None):
    device=next(model.parameters()).device
    all_indices=torch.as_tensor(indices,device=device)
    labels=all_indices if target_map is None else torch.as_tensor(target_map[indices],device=device)
    if device.type=='cuda': torch.cuda.synchronize()
    start=time.perf_counter()
    first=None
    for k,(ii,jj) in enumerate(zip(all_indices,labels)):
        pred=model([v[ii] for v in t[:8]])
        mask=t[1][ii]
        muscle=(F.smooth_l1_loss(pred[0],t[-2][jj],reduction='none')*mask).sum(1)/mask.sum(1)
        path=F.smooth_l1_loss(pred[1],t[-1][jj],reduction='none').mean((1,2))
        loss=.5*(muscle+path).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if k==0:
            first=(loss.detach().cpu().item(),float(model.qkv.weight.grad.norm().detach().cpu()))
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        opt.step()
    last=float(loss.detach().cpu())
    return dict(updates=len(indices),examples=indices.size,seconds=time.perf_counter()-start,
                unique_rows=int(len(np.unique(indices))),indices_sha256=hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest(),
                targets_sha256=hashlib.sha256((indices if target_map is None else target_map[indices]).astype('<i8').tobytes()).hexdigest(),
                first_loss=first[0],first_qkv_grad_norm=first[1],last_loss=last)


def synthetic():
    rows=[fixture(d) for d in (0,1) for _ in range(128)]
    data={k:np.asarray([row[k] for row in rows]) for k in INPUT_KEYS}
    rng=np.random.default_rng(SEED)
    data['patch_rms']*=rng.uniform(.5,1.5,(256,20,1))
    data['past_rms']=np.sqrt(np.mean(data['patch_rms'][:,-4:]**2,axis=1))
    data.update(future_rms=data['past_rms']*rng.uniform(.8,1.2,(256,1)),
                future_path_mm=rng.normal(0,.4,(256,32,3)),person=np.tile(np.arange(8),32))
    return data


def read_data(paths):
    parts=[]
    for path in paths:
        with np.load(path,allow_pickle=False) as z: parts.append({k:z[k] for k in z.files})
    keys=set.intersection(*(set(part) for part in parts))
    return {k:np.concatenate([part[k] for part in parts]) for k in keys}


def routine(data,args):
    idx=np.arange(len(data['domain']))
    if args.bench:
        model=fresh(args.device)
        sc=fit_scales(data,idx)
        ds=[draws(data,idx,d,8) for d in (0,1)]
        seq=np.stack(ds,axis=1).reshape(16,BATCH)
        log=run(model,tensors(data,sc,args.device),seq,optimizer(model))
        sub={k:v[seq.ravel()[:96:2]] for k,v in data.items()}
        # Use examples drawn from both domains, including a separate upper half.
        ids=np.r_[ds[0][0],ds[1][0]]
        sub={k:v[ids] for k,v in data.items()}
        rm,pa=predict_arrays(model,sub,sc)
        np.savez(args.out/'native.npz',rms=rm,path_mm=pa)
        save_json(args.out/'model.json',export(model,sc))
        save_json(args.out/'benchmark.json',dict(log=log,torch=torch.__version__,numpy=np.__version__,
                  threads=torch.get_num_threads(),interop=torch.get_num_interop_threads(),device=args.device,
                  gpu_name=torch.cuda.get_device_name() if args.device=='cuda' else None,
                  maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  gpu_peak_bytes=torch.cuda.max_memory_allocated() if args.device=='cuda' else None))
        return

    from scoring import aggregate, event_errors, compare
    fold_ids=np.full(len(idx),-1)
    for d in (0,1):
        persons=sorted(set(data['person'][data['domain']==d].tolist()))
        for rank,p in enumerate(persons): fold_ids[(data['domain']==d)&(data['person']==p)]=rank%3
    summary={}
    oof={}
    for fold in (0,1,2,'all'):
        train=idx if fold=='all' else idx[fold_ids!=fold]
        held=idx[:0] if fold=='all' else idx[fold_ids==fold]
        sc=fit_scales(data,train)
        batch=tensors(data,sc,args.device)
        ds=[draws(data,train,d) for d in (0,1)]
        logs={}
        def capture(name,model,domains):
            if fold=='all':
                save_json(args.out/f'model-{name}.json',export(model,sc))
            else:
                valid=held[np.isin(data['domain'][held],domains)]
                inp={k:v[valid] for k,v in data.items()}
                r,p=predict_arrays(model,inp,sc)
                if name not in oof:
                    oof[name]=(np.full((len(idx),13),np.nan),np.full((len(idx),32,3),np.nan))
                oof[name][0][valid]=r
                oof[name][1][valid]=p
        joint=fresh(args.device)
        seq=np.stack([x[:STEPS] for x in ds],axis=1).reshape(STEPS*2,BATCH)
        logs['joint']=run(joint,batch,seq,optimizer(joint))
        capture('joint',joint,[0,1])
        pre={}
        for d,label in enumerate(('lower','upper')):
            net=fresh(args.device)
            opt=optimizer(net)
            logs[label]=run(net,batch,ds[d][:STEPS],opt)
            pre[d]=copy.deepcopy(net)
            capture(label,net,[d,1-d])
            logs[label+'-extra']=run(net,batch,ds[d][STEPS:],opt)
            capture(label+'-total',net,[d])
        for target,label in enumerate(('lower','upper')):
            source=1-target
            net=copy.deepcopy(pre[source])
            logs['adapt-'+label]=run(net,batch,ds[target][:STEPS],optimizer(net))
            capture('adapt-'+label,net,[target])
            pool=train[data['domain'][train]==source]
            good,foreign=match(data,pool,identical_mask=True)
            if not len(good): raise ValueError('No disjoint shuffled source controls')
            mapping=np.arange(len(idx))
            mapping[good]=foreign
            source_seq=draws(data,np.sort(good),source,STEPS)
            for name,shuffle in [('shuffled',True),('paired-source',False)]:
                net=fresh(args.device)
                logs[f'{name}-{label}-pre']=dict(**run(net,batch,source_seq,optimizer(net),mapping if shuffle else None),
                    eligible_source_rows=len(good),original_source_rows=len(pool))
                logs[f'{name}-{label}-adapt']=run(net,batch,ds[target][:STEPS],optimizer(net))
                capture(f'{name}-{label}',net,[target])
        summary[str(fold)]=logs
        save_json(args.out/'fit-log.json',summary)
        print('Completed fold',fold,flush=True)
    from evaluation import summarize_predictions
    summary_data,private=summarize_predictions(data,oof,idx,include_donors=False)
    save_json(args.out/'development.json',summary_data)
    np.savez_compressed(args.private/'out-of-fold.npz',fold=fold_ids,**{name+'_'+k:arr for name,values in oof.items() for k,arr in zip(('rms','path'),values)})
    save_json(args.out/'training.json',dict(seed=SEED,updates_per_domain=STEPS,batch=BATCH,
              parameters=sum(p.numel() for p in fresh('cpu').parameters()),inputs_sha256=[fingerprint(p) for p in args.data],
              rows=len(idx),people=[len(np.unique(data['person'][data['domain']==d])) for d in (0,1)],
              threads=torch.get_num_threads(),device=args.device,torch=torch.__version__,numpy=np.__version__,
              total_executed_updates=sum(x['updates'] for f in summary.values() for x in f.values())))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,nargs='+',help='development NPZ file(s)')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--private',type=Path)
    parser.add_argument('--threads',type=int,default=3)
    parser.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    parser.add_argument('--bench',action='store_true')
    args=parser.parse_args()
    if not args.data and not args.bench: parser.error('Real training requires development data')
    if not args.bench and not args.private: parser.error('Supply --private for out-of-fold predictions')
    args.out.mkdir(parents=True,exist_ok=True)
    if args.private: args.private.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    routine(read_data(args.data) if args.data else synthetic(),args)
