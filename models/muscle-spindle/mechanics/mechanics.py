"""Predict next-bin native force and apparatus-position changes on unseen filename groups."""
import argparse
import json
from pathlib import Path
import numpy as np

GROUPS=(0,1,4)
TARGETS=('force','position')
MODES=('zero','velocity','repeat','spikes','mechanics','combined','wrong_spikes')

def weights(data,ids):
    """Each prefix, afferent within a prefix, and trial of an afferent count equally."""
    result=np.zeros(len(ids))
    prefix,member,trial=(data[k][ids] for k in ('prefix','afferent','trial'))
    for group in np.unique(prefix):
        group_rows=prefix==group
        members=np.unique(member[group_rows])
        for name in members:
            own=group_rows&(member==name);trials=np.unique(trial[own])
            for t in trials:
                sel=own&(trial==t)
                result[sel]=1/(len(members)*len(trials)*sel.sum())
    return result/result.sum()

def earlier(data):
    keys=list(zip(data['afferent'].tolist(),data['trial'].tolist(),data['bin_index'].tolist()))
    lookup={key:i for i,key in enumerate(keys)}
    if len(lookup)!=len(keys):raise ValueError('Duplicate trial windows')
    ix=np.array([lookup.get((a,t,b-10),-1) for a,t,b in keys],dtype=np.int64)
    ok=ix>=0
    np.testing.assert_allclose(data['cutoff_s'][ok]-data['cutoff_s'][ix[ok]],.2,atol=1e-8,rtol=0)
    return ix

def design(x,mode,center,scale):
    z=(x-center)/scale
    if mode=='mechanics':z[:,:,4]=0
    if mode=='spikes':z[:,:,:4]=0
    return np.column_stack([z.reshape(len(x),-1),np.ones(len(x))])

def fit_one(x,y,w):
    mean=np.einsum('n,ntc->tc',w,x)
    sd=np.sqrt(np.einsum('n,ntc->tc',w,(x-mean)**2))
    sd=np.where(sd>1e-12,sd,1.)
    state={'mean':mean.tolist(),'scale':sd.tolist(),'coefficients':{}}
    for mode in ('spikes','mechanics','combined'):
        xx=design(x,mode,mean,sd)
        target=y if mode=='spikes' else y-x[:,-1,2:4]*.020
        penalty=np.eye(xx.shape[1])*.05;penalty[-1,-1]=0.
        coef=np.linalg.solve(xx.T@(w[:,None]*xx)+penalty, xx.T@(w[:,None]*target))
        state['coefficients'][mode]=coef.tolist()
    return state

def predict(x,state,mode):
    x=np.asarray(x,dtype=float)
    if x.ndim!=3 or x.shape[1:]!=(5,5) or not np.isfinite(x).all():raise ValueError('Five finite bins with five inputs each are required')
    counts=x[:,:,4]
    if not ((counts>=0)&(counts==np.floor(counts))).all():raise ValueError('Spike counts must be nonnegative integers')
    if mode=='zero':return np.zeros((len(x),2))
    if mode=='velocity':return x[:,-1,2:4]*.020
    if mode=='repeat':return x[:,-1,:2]-x[:,-2,:2]
    beta=np.asarray(state['coefficients'][mode])
    out=design(x,mode,np.asarray(state['mean']),np.asarray(state['scale']))@beta
    return out if mode=='spikes' else out+x[:,-1,2:4]*.020

def summarize(data,ids,preds,group_key,groups,*,keep_members=False):
    def scope(rows):
        weights_here=weights(data,rows)
        report={}
        for mode,pred in preds.items():
            err=pred[rows]-data['y_delta'][rows]
            report[mode]={'mae':(weights_here@abs(err)).tolist(),'rmse':np.sqrt(weights_here@err**2).tolist(),'bias':(weights_here@err).tolist()}
        return {'windows':len(rows),'afferents':len(np.unique(data['afferent'][rows])),
                'trials':len(set(zip(data['afferent'][rows],data['trial'][rows]))),'methods':report}
    if keep_members:
        return {str(a):scope(ids[data['afferent'][ids]==a]) for a in np.unique(data['afferent'][ids])}
    by_group={str(g):scope(ids[data[group_key][ids]==g]) for g in groups}
    full=scope(ids)
    # Fold-specific tests are important because pooled averages can hide reversals.
    def gate(a,b):
        return {t:all(v['methods'][a]['mae'][j]<v['methods'][b]['mae'][j] for v in [full,*by_group.values()]) for j,t in enumerate(TARGETS)}
    return {'overall':full,'by_held_group':by_group,'combined_beats_mechanics_everywhere':gate('combined','mechanics'),
            'combined_beats_wrong_everywhere':gate('combined','wrong_spikes') if 'wrong_spikes' in preds else None}

def fit(path,out,validation):
    keys=('X','y_delta','prefix','afferent','trial','bin_index','cutoff_s')
    with np.load(path,allow_pickle=False) as z:d={k:z[k] for k in keys}
    if validation=='strict-afferent':
        group_key='afferent';groups=('aff004','aff015','aff017')
        assert set(d['prefix'])=={0} and set(np.unique(d[group_key]))==set(groups)
    else:
        group_key='prefix';groups=GROUPS
        assert set(np.unique(d[group_key]))==set(groups)
    x=d['X'].astype(float);y=d['y_delta'].astype(float)
    assert x.shape==(len(y),5,5) and y.shape==(len(x),2)
    good=np.all(np.isfinite(x),axis=(1,2))&np.all(np.isfinite(y),axis=1)
    donor=earlier(d);matches=(donor>=0)&good&good[np.maximum(donor,0)]
    pred={mode:np.full(y.shape,np.nan) for mode in MODES}
    checkpoints={}
    for fold in groups:
        train=np.flatnonzero(good&(d[group_key]!=fold))
        held=np.flatnonzero(good&(d[group_key]==fold))
        assert not set(d['afferent'][train])&set(d['afferent'][held])
        fitted=fit_one(x[train],y[train],weights(d,train))
        checkpoints[str(fold)]=fitted
        for mode in MODES[:-1]:pred[mode][held]=predict(x[held],fitted,mode)
        aligned=held[matches[held]]
        shifted=x[aligned].copy()
        shifted[:,:,4]=x[donor[aligned],:,4]
        pred['wrong_spikes'][aligned]=predict(shifted,fitted,'combined')
    result={'validation':validation,'group_key':group_key,'targets':list(TARGETS),'excluded_for_secondary':int((~good).sum()),
            'primary':summarize(d,np.flatnonzero(good),{k:pred[k] for k in MODES[:-1]},group_key,groups),
            'timing':summarize(d,np.flatnonzero(matches),pred,group_key,groups)}
    out.mkdir(parents=True,exist_ok=True)
    per_afferent={'primary':summarize(d,np.flatnonzero(good),{k:pred[k] for k in MODES[:-1]},group_key,groups,keep_members=True),
                  'timing':summarize(d,np.flatnonzero(matches),pred,group_key,groups,keep_members=True)}
    (out/'private-by-afferent.json').write_text(json.dumps(per_afferent,indent=2,allow_nan=False)+'\n')
    (out/'checkpoints.json').write_text(json.dumps(checkpoints,separators=(',',':'),allow_nan=False)+'\n')
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    np.savez_compressed(out/'private.npz',donor=donor,valid=good,**pred)

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('windows',type=Path);cli.add_argument('output',type=Path)
    cli.add_argument('--validation',choices=('strict-afferent','three-prefix'),required=True)
    args=cli.parse_args();fit(args.windows,args.output,args.validation)
