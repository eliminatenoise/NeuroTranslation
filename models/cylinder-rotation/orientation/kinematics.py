"""Project a native device-frame angular-rate forecast forward on the same instrument clock."""
import argparse,json
from pathlib import Path
import numpy as np

def product(a,b):
    """Hamilton product of scalar-first unit quaternions, broadcasting over row dimensions."""
    a,b=np.broadcast_arrays(a,b)
    s=a[...,:1]*b[...,:1]-np.sum(a[...,1:]*b[...,1:],axis=-1,keepdims=True)
    v=a[...,:1]*b[...,1:]+b[...,:1]*a[...,1:]+np.cross(a[...,1:],b[...,1:])
    return np.concatenate([s,v],axis=-1)

def increment(omega,dt):
    length=np.linalg.norm(omega,axis=-1,keepdims=True)
    # sinc(x) = sin(pi*x)/(pi*x), including the exact zero-rate limit.
    return np.concatenate([np.cos(.5*dt*length),(.5*dt)*np.sinc(.5*dt*length/np.pi)*omega],axis=-1)

def error_degrees(q,actual):
    q=q/np.linalg.norm(q,axis=-1,keepdims=True)
    actual=actual/np.linalg.norm(actual,axis=-1,keepdims=True)
    aligned=np.where((q*actual).sum(axis=-1,keepdims=True)<0,-actual,actual)
    return np.degrees(4*np.arctan2(np.linalg.norm(q-aligned,axis=-1),np.linalg.norm(q+aligned,axis=-1)))

def extract(source,raw,output):
    with np.load(source,allow_pickle=False) as d:
        participants,hand,trial=d['participant'],d['hand'],d['trial']
        original=np.array([f'{p}_{h[0].upper()}_X_rec{r}.csv' for p,h,r in zip(participants,hand,trial)])
        before=np.full((len(original),4),np.nan);after=before.copy();oracle=before.copy()
        for n in sorted(set(original)):
            x=np.loadtxt(raw/n,delimiter=';',skiprows=1,usecols=(0,7,8,9,13,14,15,16),ndmin=2)
            t=x[:,0]-x[0,0]
            for i in np.flatnonzero(original==n):
                dt=d['cutoff'][i]/1000
                near=np.flatnonzero(np.abs(t-dt)<1e-7)
                if len(near)!=1:raise ValueError(f'Cannot match eligible cutoff in {n}')
                k=int(near[0]);w=x[k:k+10,1:4];pair=x[[k-1,k+9],4:]
                np.testing.assert_allclose(w.mean(0),d['y_gyro'][i],atol=1e-10,rtol=1e-10)
                lengths=np.linalg.norm(pair,axis=1)
                if not np.isfinite(pair).all() or np.any(abs(lengths-1)>.01):continue
                before[i],after[i]=pair/lengths[:,None]
                q=before[i]
                for omega in w:q=product(q,increment(omega,.01))
                oracle[i]=q
        out={k:d[k] for k in ('participant','hand','trial','target','cutoff','donor','repetition')}
        np.savez_compressed(output,**out,q_before=before,q_after=after,future_rate_integration=oracle)

def per_person(values,d,mask):
    person=d['participant'][mask];hand=d['hand'][mask];trial=d['trial'][mask]
    keys=np.array([f'{p}/{h}/{t}' for p,h,t in zip(person,hand,trial)])
    unique,ix=np.unique(keys,return_inverse=True)
    sums=np.zeros((len(unique),values.shape[0]));np.add.at(sums,ix,values[:,mask].T)
    means=sums/np.bincount(ix)[:,None];ppl=np.array([int(k.split('/')[0]) for k in unique])
    return {int(p):float(means[ppl==p].mean()) for p in np.unique(ppl)}

def assess(source,forecasts):
    q0=source['q_before'];q1=source['q_after'];valid=np.isfinite(q0).all(1)&np.isfinite(q1).all(1)
    loss={'hold_orientation':error_degrees(q0,q1)[None],'future_gyro_integration_diagnostic':error_degrees(source['future_rate_integration'],q1)[None]}
    for method in ('transformer_full','transformer_gyro_task','transformer_wrong_accel','transformer_gyro_loss','ridge_full','persistence','linear_trend'):
        p=product(q0,increment(forecasts[method][:,:,:3],.10))
        loss[method]=error_degrees(p,q1)
    out={'units':'degrees, sensor orientation estimate','eligible_windows':len(q0),'invalid_endpoint_quaternion':int((~valid).sum()),'results':{}}
    for label,initial in [('eligible',valid),('matched',valid&(source['donor']>=0))]:
        strata={'overall':initial,**{'cutoff_'+str(t):initial&(source['cutoff']==t) for t in np.unique(source['cutoff'])},**{s:initial&(source['hand']==s) for s in ['left','right']}}
        for name,mask in strata.items():
            if not mask.any():continue
            group={}
            for method,err in loss.items():
                if not np.isfinite(err[:,mask]).all():continue
                means=per_person(err,source,mask);group[method]={'by_person':means,'mean_degrees':float(np.mean(list(means.values())))}
            baseline=group['transformer_full']['by_person'];subjects=sorted(baseline)
            b=np.random.default_rng(20261124).integers(0,len(subjects),size=(10000,len(subjects)))
            diffs={}
            for method,v in group.items():
                z=np.array([baseline[p]-v['by_person'][p] for p in subjects])
                diffs[method]={'mean_degrees':float(z.mean()),'interval':np.quantile(z[b].mean(1),[.025,.975]).tolist()}
            out['results'][label+'/'+name]={'rows':int(mask.sum()),'people':len(subjects),'methods':group,'full_minus':diffs}
    return out
if __name__=='__main__':
    c=argparse.ArgumentParser(description=__doc__);cmd=c.add_subparsers(dest='task',required=True)
    for kind,keys in [('extract',('source','raw','output')),('score',('source','forecasts','output'))]:
        parser=cmd.add_parser(kind)
        for key in keys:parser.add_argument(key,type=Path)
    a=c.parse_args()
    if a.task=='extract':extract(a.source,a.raw,a.output)
    else:
        with np.load(a.source,allow_pickle=False) as s,np.load(a.forecasts,allow_pickle=False) as f:
            for key in ('participant','trial','hand','cutoff','donor'):np.testing.assert_array_equal(s[key],f[key])
            a.output.write_text(json.dumps(assess(s,f),indent=2,allow_nan=False)+'\n')
