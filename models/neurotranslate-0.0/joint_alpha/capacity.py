"""Build and evaluate an inner fold using only the original train split."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from evaluate import metrics,group_means,decoded_batches
from inference import JointModel
from train import Cases, split_path


def build(src,out):
    out.mkdir(parents=True,exist_ok=True)
    tasks=json.loads(src.read_text())['tasks']
    details={}
    for t,s in tasks.items():
        with np.load(split_path(src.parent,s['splits']['train']),allow_pickle=False) as z:
            X,y,g=z['X'],z['y'],z['group']
            groups=np.unique(g)
            if t.startswith('macaque_'):
                held=z['development_fold']>=3
            elif t.startswith('human_'):
                held=np.isin(g,groups[3::5])
            elif t=='rat_next_unit':
                held=g>=74
            elif t=='optical_fluorescence':
                held=np.isin(g,[k for k in groups if not str(k).startswith('Fish')][-2:])
                for flag in (0,1):
                    use=X[:,0,2]==flag
                    train_only=X[use&~held,:,0].astype('d')
                    m,sd=train_only.mean(),train_only.std()
                    X[use,:,0]=(X[use,:,0]-m)/sd
                    y[use]=(y[use]-m)/sd
            elif t=='landmark_motion':
                held=g=='mice_of'
            else:
                raise ValueError('No prespecified fold for '+t)
            if np.intersect1d(g[held],g[~held]).size or not (held.any() and (~held).any()):
                raise ValueError('Groups must be disjoint and both folds nonempty')
            split={}
            for name,mask in [('train',~held),('validation',held)]:
                rows=np.flatnonzero(mask)
                if name=='validation':
                    rng=np.random.default_rng(441)
                    parts=[]
                    for group in np.unique(g[rows]):
                        matched=rows[g[rows]==group]
                        parts.append(np.sort(rng.choice(matched,min(len(matched),256),replace=False)))
                    rows=np.concatenate(parts)
                filename=t+'-'+name+'.npz'
                # Uncompressed temporary arrays avoid needless CPU time in repeated fitting.
                np.savez(out/filename,X=X[rows],y=y[rows],group=g[rows])
                split[name]=filename
                details.setdefault(t,{})[name]={'groups':len(np.unique(g[rows])),'rows':len(rows),'row_index_sha256':hashlib.sha256(rows.tobytes()).hexdigest()}
        s['splits']=split
        s.pop('support',None)
    (out/'manifest.json').write_text(json.dumps({'tasks':tasks},indent=2)+'\n')
    (out/'fold-counts.json').write_text(json.dumps(details,indent=2)+'\n')


def score(src,checkpoint,out):
    tasks=json.loads(src.read_text())['tasks']
    model=JointModel.load(checkpoint)
    detail={}
    latencies=[]
    for t,s in model.tasks.items():
        data=Cases(src.parent,tasks[t],'validation')
        pred=decoded_batches(model,t,data)
        if data.kind=='categorical':
            valid=np.isfinite(data.x).any(axis=(-1,-2))
            prior=valid/valid.sum(axis=1,keepdims=True)
        else:
            prior=np.broadcast_to(model.arrays[t+'.ymean'],data.y.shape)
        actual=metrics(t,data.kind,data.y,pred)
        primary=next(iter(actual))
        m=float(group_means(actual[primary],data.buckets).mean())
        ref=float(group_means(metrics(t,data.kind,data.y,prior)[primary],data.buckets).mean())
        domain=('macaque' if t.startswith('macaque_') else 'human' if t.startswith('human_') else t)
        detail[t]=dict(primary=primary,score=m,prior=ref,ratio=m/ref,domain=domain)
        for _ in range(5):
            start=time.monotonic()
            model.predict(t,data.x[:1])
            latencies.append(time.monotonic()-start)
    domains={k:float(np.mean([v['ratio'] for v in detail.values() if v['domain']==k])) for k in sorted(set(v['domain'] for v in detail.values()))}
    result=dict(architecture=model.architecture,task_scores=detail,domain_scores=domains,aggregate=float(np.mean(list(domains.values()))),median_latency_seconds=float(np.median(latencies)))
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'architecture':model.architecture,'validation_aggregate':result['aggregate']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='cmd',required=True)
    b=sub.add_parser('build')
    b.add_argument('src',type=Path);b.add_argument('out',type=Path)
    s=sub.add_parser('score')
    s.add_argument('src',type=Path);s.add_argument('checkpoint',type=Path);s.add_argument('out',type=Path)
    a=p.parse_args()
    if a.cmd=='build':
        build(a.src,a.out)
    else:
        score(a.src,a.checkpoint,a.out)
