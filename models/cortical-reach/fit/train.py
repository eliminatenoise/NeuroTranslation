"""Reproduce the frozen five-token Transformer and the forward-only block forecasts."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from predict import (BLOCKS, FORMAT, MODES, SEEDS, SESSION, UNITS, decode_weights,
                     forward, mask, validate_block)

BATCH=128
EPOCHS=24
ID_KEYS=('trial','epoch','offset','k','donor')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,value):
    path.write_text(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n')

class Transformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed=nn.Linear(41,16)
        self.position=nn.Parameter(torch.empty(5,16))
        nn.init.normal_(self.position,std=.025)
        self.attn_norm=nn.LayerNorm(16)
        self.qkv=nn.Linear(16,48)
        self.project=nn.Linear(16,16)
        self.ff_norm=nn.LayerNorm(16)
        self.expand=nn.Linear(16,32)
        self.reduce=nn.Linear(32,16)
        self.final_norm=nn.LayerNorm(16)
        self.readout=nn.Linear(16,2)

    def forward(self,x):
        h=self.embed(x)+self.position
        q,k,v=self.qkv(self.attn_norm(h)).reshape(-1,5,3,2,8).permute(2,0,3,1,4).unbind(0)
        attention=torch.softmax((q @ k.transpose(-1,-2)) / (8**.5),dim=-1)
        h=h+self.project((attention @ v).transpose(1,2).reshape(-1,5,16))
        h=h+self.reduce(torch.relu(self.expand(self.ff_norm(h))))
        return self.readout(self.final_norm(h[:,-1]))

def load(path,stage,with_targets):
    if path.name!=stage+'.npz':
        raise ValueError('source block name must match requested stage')
    with np.load(path,allow_pickle=False) as source:
        ids={name:source[name] for name in ID_KEYS}
        n=len(ids['trial'])
        if not n or any(a.shape!=(n,) or a.dtype.kind not in 'iu' for a in ids.values()):
            raise ValueError('invalid row identities')
        original=source['original_trial']
        if len(original)!={'train':324,'validation':108,'test':108}[stage] or not np.isin(ids['trial'],original).all():
            raise ValueError('unexpected split size or row group')
        if len(set(zip(ids['trial'],ids['epoch'],ids['offset'])))!=n:
            raise ValueError('duplicate forecast identity')
        if not np.isin(ids['epoch'],[0,1]).all() or not np.isin(ids['offset'],[0,5,10,15]).all():
            raise ValueError('unknown epoch/offset')
        guide=source['unit_guide']
        if (guide.shape!=(30,2) or guide.dtype.kind not in 'ui' or
                [f'ch{ch}:sort{unit}' for ch,unit in guide]!=UNITS):
            raise ValueError('source unit identities/order differ')
        raw=np.empty((n,5,41),dtype=np.float64)
        for key,index in BLOCKS.items():
            a=source[key]
            if a.dtype.kind not in 'fiu' or a.shape!=(n,5,index.stop-index.start) or not np.isfinite(a).all():
                raise ValueError(f'invalid source {key}')
            validate_block(key,a)
            raw[:,:,index]=a
        y=source['y'].astype(np.float64) if with_targets else None
        if with_targets and (y.shape!=(n,2) or not np.isfinite(y).all()):
            raise ValueError('invalid target')
    donor=ids['donor']
    if np.any((donor < -1) | (donor>=n)):
        raise ValueError('invalid donor row')
    ok=donor>=0
    d=donor[ok]
    if (np.any(ids['trial'][d]==ids['trial'][ok]) or np.any(ids['k'][d]>=ids['k'][ok]) or
            np.any(ids['epoch'][d]!=ids['epoch'][ok]) or np.any(ids['offset'][d]!=ids['offset'][ok])):
        raise ValueError('wrong-trial donor identity or clock differs')
    if not np.array_equal(raw[d,-1,BLOCKS['cue']],raw[ok,-1,BLOCKS['cue']]):
        raise ValueError('donor cues differ at cutoff')
    return raw,y,ids

def row_weights(ids):
    weights=np.zeros(len(ids['trial']))
    trials=np.unique(ids['trial'])
    for trial in trials:
        rows=np.flatnonzero(ids['trial']==trial)
        epochs=np.unique(ids['epoch'][rows])
        for epoch in epochs:
            chosen=rows[ids['epoch'][rows]==epoch]
            weights[chosen]=1./(len(trials)*len(epochs)*len(chosen))
    assert np.isclose(weights.sum(),1)
    return weights

def scaler(raw,y,w):
    mean=np.einsum('i,ijk->k',w,raw)/5
    sd=np.sqrt(np.einsum('i,ijk->k',w,(raw-mean)**2)/5)
    ymean=w @ y
    yscale=max(float(np.sqrt(w @ ((y-ymean)**2).mean(axis=1))),1e-6)
    return dict(x_mean=mean.tolist(),x_scale=np.where(sd<1e-6,1.,sd).tolist(),y_mean=ymean.tolist(),y_scale=yscale)

def tensors(raw,y,w,s,device):
    def fp32(a):
        return torch.as_tensor(a,dtype=torch.float32,device=device)
    return (fp32(np.clip((raw-s['x_mean'])/s['x_scale'],-8.,8.)),fp32((y-s['y_mean'])/s['y_scale']),
            fp32(w*len(w)))

def train_one(tensors,plan,seed,mode,device,steps=None):
    x,y,w=tensors
    torch.manual_seed(seed)
    model=Transformer().to(device)
    keep=torch.as_tensor(mask(mode),device=device)
    x=x*keep
    opt=torch.optim.AdamW(model.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=.001,
                          foreach=False,fused=False)
    counter=0
    for epoch in plan:
        for rows in epoch.split(BATCH):
            prediction=model(x[rows])
            loss=(((prediction-y[rows])**2).mean(dim=1)*w[rows]).sum()/BATCH
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
            opt.step()
            counter+=1
            if counter==steps:
                return model
    return model

def weight_path(out,mode,seed):
    return out/f'weights-{mode}-{seed}.json'

def export(model,scales,seed,mode):
    return dict(format=FORMAT,session=SESSION,mode=mode,seed=seed,unit_ids=UNITS,**scales,
                parameters={k:v.detach().cpu().tolist() for k,v in model.state_dict().items()})

def native(model,tensor,mode,s):
    with torch.no_grad():
        values=model(tensor*torch.as_tensor(mask(mode),device=tensor.device)).cpu().numpy()
    return values*np.asarray(s['y_scale'])+s['y_mean']

def fit(args):
    start=time.monotonic()
    raw,y,ids=load(args.data,'train',True)
    w=row_weights(ids)
    s=scaler(raw,y,w)
    t=tensors(raw,y,w,s,args.device)
    benchmark=args.task=='bench'
    seeds=SEEDS[:1] if benchmark else SEEDS
    modes=('all',) if benchmark else MODES
    checks={}
    prediction={mode:np.empty((len(seeds),len(y),2)) for mode in modes} if not benchmark else {}
    for si,seed in enumerate(seeds):
        rng=np.random.default_rng(seed)
        order=np.stack([rng.permutation(len(w)) for _ in range(EPOCHS)])
        if not benchmark:
            np.save(args.out/f'train-permutations-{seed}.npy',order.astype(np.int32))
        plan=torch.as_tensor(order,device=args.device)
        for mode in modes:
            tick=time.monotonic()
            model=train_one(t,plan,seed,mode,args.device,24 if benchmark else None)
            row_count=min(len(y),32) if benchmark else len(y)
            result=native(model,t[0][:row_count],mode,s)
            weights=export(model,s,seed,mode)
            py=forward(raw[:row_count],decode_weights(weights),mode)
            diff=float(np.max(np.abs(result-py)))
            if diff>=1e-4:
                raise ValueError(f'native/portable parity failed: {diff}')
            checks[f'{mode}-{seed}']={'seconds':time.monotonic()-tick,'max_portable_error_cm':diff}
            if benchmark:
                save(args.out/f'bench-{args.device}-{args.threads}.json',
                     {'prediction':result.tolist(),'seconds_since_load':time.monotonic()-start,
                      'torch':torch.__version__,'hip':torch.version.hip,'threads':torch.get_num_threads(),
                      'interop':torch.get_num_interop_threads(),'device':args.device,'fit':checks})
            else:
                save(weight_path(args.out,mode,seed),weights)
                prediction[mode][si]=result
    if benchmark:
        return
    np.savez_compressed(args.out/'train-insample-predictions.npz',seeds=SEEDS,**ids,**prediction,
                        source_sha256=sha(args.data))
    save(args.out/'normalizer.json',s)
    np.save(args.out/'train-row-weights.npy',w)
    entries=[*args.out.glob('weights-*.json'),*args.out.glob('train-permutations-*.npy'),
             args.out/'normalizer.json',args.out/'train-insample-predictions.npz',args.out/'train-row-weights.npy']
    if len(entries)!=24:
        raise ValueError('unanticipated number of frozen outputs')
    save(args.out/'weights-lock.json',{'files':{p.name:sha(p) for p in sorted(entries)},
         'train_source_sha256':sha(args.data),'train_ids':np.unique(ids['trial']).tolist(),
         'epochs':EPOCHS,'batch_size':BATCH,'updates_per_fit':EPOCHS*((len(y)+BATCH-1)//BATCH),
         'rows':len(y),'device':args.device,'intraop':torch.get_num_threads(),'interop':torch.get_num_interop_threads(),
         'torch':torch.__version__,'numpy':np.__version__,'fits':checks,'seconds':time.monotonic()-start})

def evaluate(args):
    # Only frozen weights and already-released inputs are loaded. This stage never opens y.
    lock=json.loads((args.out/'weights-lock.json').read_text())
    for name,digest in lock['files'].items():
        if sha(args.out/name)!=digest:
            raise ValueError('frozen artifact differs: '+name)
    raw,_,ids=load(args.data,args.task,False)
    if set(lock['train_ids']) & set(ids['trial'].tolist()):
        raise ValueError('evaluation overlaps the fitting trials')
    if args.task=='test':
        with np.load(args.out/'validation-predictions.npz',allow_pickle=False) as val:
            if set(val['trial']) & set(ids['trial']):
                raise ValueError('test overlaps validation')
    ok=ids['donor']>=0
    wrong=raw[ok].copy()
    wrong[:,:,BLOCKS['neural']]=raw[ids['donor'][ok],:,BLOCKS['neural']]
    prediction={mode:np.empty((len(SEEDS),len(raw),2)) for mode in MODES}
    prediction['wrong_neural']=np.full((len(SEEDS),len(raw),2),np.nan)
    max_native_error=0.
    for mode in MODES:
        for si,seed in enumerate(SEEDS):
            weights=json.loads(weight_path(args.out,mode,seed).read_text())
            p=decode_weights(weights)
            model=Transformer()
            model.load_state_dict({name:torch.tensor(v) for name,v in weights['parameters'].items()})
            def compare(x):
                nonlocal max_native_error
                portable=forward(x,p,mode)
                xt=torch.as_tensor(np.clip((x-p['x_mean'])/p['x_scale'],-8,8),dtype=torch.float32)
                official=native(model,xt,mode,p)
                max_native_error=max(max_native_error,float(np.max(np.abs(official-portable))))
                return official
            prediction[mode][si]=compare(raw)
            if mode=='all' and np.any(ok):
                prediction['wrong_neural'][si,ok]=compare(wrong)
    if max_native_error>=1e-4:
        raise ValueError('portable and native outputs differ')
    np.savez_compressed(args.out/(args.task+'-predictions.npz'),seeds=SEEDS,**ids,**prediction,
                        source_sha256=sha(args.data),weights_sha256=sha(args.out/'weights-lock.json'),
                        native_portable_max_error=max_native_error)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task',choices=['bench','fit','validation','test'])
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--threads',type=int,default=1)
    parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision('highest')
    if args.device=='cuda' and (not torch.cuda.is_available() or not torch.version.hip):
        raise RuntimeError('ROCm unavailable')
    if args.task=='fit' and (args.out/'weights-lock.json').exists():
        raise FileExistsError('weights already frozen; use a fresh output directory to reproduce')
    if args.task in ('validation','test') and (args.out/(args.task+'-predictions.npz')).exists():
        raise FileExistsError('predictions already sealed for this stage')
    if args.task in ('bench','fit'):
        fit(args)
    else:
        evaluate(args)
