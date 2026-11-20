"""Fit or assess the shared movement adapter on the fixed walking/standing study."""
import argparse,hashlib,json,math
from pathlib import Path
import sys
import numpy as np
from features import CODES,read_trial
from forecast import METHOD,MODES,batch,design
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from predict import read_checkpoint,linear,encode

PARENT_SHA="6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864"
FIT=(1,2,3,5)
TEST=(10,12,13,14)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def stack(parts):
    return tuple(np.concatenate(x) for x in zip(*parts))


def load(cache,people):
    trials=[];quality=[];hashes={}
    for person in people:
        for trial in (2,3):
            p=cache/f"S{person:02d}"/f"trial-{trial:02d}.mat"
            metadata=json.loads(p.with_suffix('.source.json').read_bytes())
            sha=digest(p)
            if (metadata["member_sha256"]!=sha or metadata["member_bytes"]!=p.stat().st_size
                or metadata["member"]!=f"S{person:02d}_{metadata['archive']['name'].removesuffix('.zip').split('_')[-1]}_trial_{trial:02d}.mat"
                or not metadata["archive"]["name"].startswith(f"Experiment2_S{person:02d}_")):
                raise ValueError(f"Unexpected original acquisition identity: {p.name}")
            inputs,coverage=read_trial(p,person,trial)
            trials.append(inputs);quality.append(coverage);hashes[str(p.relative_to(cache))]=sha
    return stack(trials),quality,hashes


def weights(g):
    people=np.unique(g[:,0])
    wt=np.zeros(len(g))
    for p in people:
        for task in CODES:
            for trial in (2,3):
                idx=(g[:,0]==p)&(g[:,2]==task)&(g[:,1]==trial)
                if not idx.any():raise ValueError("Missing participant/task/trial stratum")
                wt[idx]=1/(len(people)*4*idx.sum())
    return wt


def scale(a,wt):
    mid=np.average(a,axis=0,weights=wt)
    sd=np.sqrt(np.average((a-mid)**2,axis=0,weights=wt))
    return mid,np.where(sd<1e-8,1.,sd)


def weighted_median(y,w):
    order=np.argsort(y,kind="stable"); ix=np.searchsorted(np.cumsum(w[order]),w.sum()/2)
    return float(y[order[ix]])


def swapped(g):
    donor=np.full(len(g),-1,dtype=int)
    for p in np.unique(g[:,0]):
        for t in CODES:
            for trial in (2,3):
                idx=np.flatnonzero((g[:,0]==p)&(g[:,2]==t)&(g[:,1]==trial))
                other=np.flatnonzero((g[:,0]==p)&(g[:,2]==t)&(g[:,1]==5-trial))
                if not len(idx) or not len(other):raise ValueError("Wrong-pair trial unavailable")
                assert np.all(np.diff(g[idx,3])>0) and np.all(np.diff(g[other,3])>0)
                donor[idx]=other[np.arange(len(idx))*len(other)//len(idx)]
    if (donor<0).any() or not np.all(g[:,1]!=g[donor,1]) or not np.array_equal(g[:,[0,2]],g[donor][:,[0,2]]):
        raise ValueError("Incorrect pairing")
    return donor


def fit(data,config,w,random):
    x,a,y,g=data;wx=weights(g)
    center,sd=scale(np.log1p(x).reshape(-1,6),np.repeat(wx/4,4))
    model={'version':1,'parent_sha256':PARENT_SHA,'random_encoder':random,
           'task_medians':{str(c):weighted_median(y[g[:,2]==c],wx[g[:,2]==c]) for c in CODES},'fits':{}}
    residual=np.log1p(y)-np.log1p(a)
    intercept=float(np.average(residual,weights=wx))
    for mode in METHOD:
        f={'bin_mean':center.tolist(),'bin_sd':sd.tolist()}
        matrix=design(mode,x,a,g[:,2],f,model,config,w,linear,encode)
        mean,spread=scale(matrix,wx);z=(matrix-mean)/spread
        coef=np.linalg.solve(z.T@(wx[:,None]*z)+.05*np.eye(z.shape[1]),z.T@(wx*(residual-intercept)))
        f.update(mean=mean.tolist(),sd=spread.tolist(),coef=coef.tolist(),intercept=intercept)
        model['fits'][mode]=f
    return model


def predictions(data,model,config,w):
    x,anchor,y,g=data
    pred={mode:batch(mode,x,anchor,g[:,2],model,config,w,linear,encode) for mode in MODES}
    wrong=x.copy();wrong[:,:,2:]=x[swapped(g),:,2:]
    pred['wrong_full']=batch('shared_full',wrong,anchor,g[:,2],model,config,w,linear,encode)
    return pred


def person_scores(data,pred):
    _,_,y,g=data;rows=[]
    for p in np.unique(g[:,0]):
        who=g[:,0]==p
        row={'person':int(p),'windows':int(who.sum()),'tasks':{},'target':{}}
        for t,label in ((611,'standing'),(621,'walking')):
            include=who&(g[:,2]==t)
            wt=weights_for_task(g[include]);v=y[include]
            row['target'][label]={'windows':len(v),'median_deg':weighted_median(v,wt),'min_deg':float(v.min()),'max_deg':float(v.max())}
            row['tasks'][label]={}
            for m,forecast in pred.items():
                err=forecast[include]-v
                row['tasks'][label][m]={'mae_deg':float(wt@np.abs(err)),'rmse_deg':float(np.sqrt(wt@(err**2)))}
        row['balanced']={m:{k:float(np.mean([row['tasks'][task][m][k] for task in ('standing','walking')])) for k in ('mae_deg','rmse_deg')} for m in pred}
        rows.append(row)
    return rows


def weights_for_task(g):
    w=np.zeros(len(g))
    for trial in (2,3):
        match=g[:,1]==trial
        if not match.any():raise ValueError('A task is absent in one trial')
        w[match]=.5/match.sum()
    return w


def summary(rows):
    def mean_record(series):
        return {m:{k:float(np.mean([s[m][k] for s in series])) for k in ('mae_deg','rmse_deg')} for m in series[0]}
    macro=mean_record([r['balanced'] for r in rows])
    tasks={t:mean_record([r['tasks'][t] for r in rows]) for t in ('standing','walking')}
    contrasts={}
    for m in ('shared_motion','wrong_full','linear_full','random_full','recent'):
        gains=[r['balanced'][m]['mae_deg']-r['balanced']['shared_full']['mae_deg'] for r in rows]
        n=sum(g!=0 for g in gains);up=sum(g>0 for g in gains)
        p=min(1.,2*sum(math.comb(n,k) for k in range(min(up,n-up)+1))/2**n)
        contrasts[m]={'mean_gain_deg':float(np.mean(gains)),'paired_gains_deg':gains,'people_improved':up,'sign_p':p}
    both=sum(a>0 and b>0 for a,b in zip(contrasts['shared_motion']['paired_gains_deg'],contrasts['wrong_full']['paired_gains_deg']))
    ok=both>=3 and all(macro['shared_full']['mae_deg']<=.95*macro[m]['mae_deg'] for m in ('shared_motion','wrong_full')) and all(tasks[t]['shared_full']['mae_deg']<=tasks[t]['shared_motion']['mae_deg'] for t in tasks)
    return {'people':len(rows),'windows':sum(r['windows'] for r in rows),'balanced':macro,'tasks':tasks,'contrasts':contrasts,'better_on_both':both,'practical_criterion':bool(ok) if len(rows)==4 else None,
            'support':{t:sum(r['target'][t]['windows'] for r in rows) for t in tasks},
            'target_distribution_per_person':[r['target'] for r in rows]}


def select(data,mask):return tuple(v[mask] for v in data)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['fit','assess']);p.add_argument('data',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--weights',type=Path,default=HERE.parent/'movement-weights.npz')
    p.add_argument('--model',type=Path,default=HERE/'model.json')
    args=p.parse_args()
    if digest(args.weights)!=PARENT_SHA:raise ValueError('Original movement checkpoint checksum mismatch')
    cfg,w=read_checkpoint(args.weights)
    args.out.mkdir(exist_ok=True,parents=True)
    if args.phase=='fit':
        dev,quality,hashes=load(args.data,FIT);rows=[]
        random=json.loads((HERE/'random-encoder.json').read_bytes())
        for person in FIT:
            mask=dev[-1][:,0]==person; test=select(dev,mask)
            trained=fit(select(dev,~mask),cfg,w,random)
            rows+=person_scores(test,predictions(test,trained,cfg,w))
        trained=fit(dev,cfg,w,random)
        # The separate reproducible initializer file is shared by all methods.
        del trained['random_encoder']
        write(args.out/'model.json',trained)
    else:
        held,quality,hashes=load(args.data,TEST)
        trained=json.loads(args.model.read_bytes());trained['random_encoder']=json.loads((HERE/'random-encoder.json').read_bytes())
        rows=person_scores(held,predictions(held,trained,cfg,w))
    write(args.out/(args.phase+'-summary.json'),summary(rows))
    write(args.out/(args.phase+'-source.json'),{'quality':quality,'source_sha256':hashes})
    print(args.phase,summary(rows)['windows'],summary(rows)['balanced']['shared_full'],summary(rows)['practical_criterion'])
if __name__=='__main__':main()
