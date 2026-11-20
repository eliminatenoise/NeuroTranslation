"""Participant-weighted ridge comparisons for wrist and sacrum forecasts."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

MOTION_HASH='6249dbf2b09197e63c84a93a47bd81a2149765d2a788367db9bfc57aa519a532'
SCALP_HASH='d37e05283468b7f761e0026c9d67435c68524324bcef39dbe46685aaa55f84e6'
FIELDS=('domain','person','session','event','direction','cutoff','age_s','patch_xyz_mm','patch_rms',
        'past_rms','future_rms','future_path_mm','muscle_mask')
MEASURES=('muscle_mae','path_mean_distance_mm','endpoint_distance_mm')

def check_arrays(archive, fields, expected):
    """Verify exact names, shapes, types and numeric payloads independently of ZIP metadata."""
    fingerprint=hashlib.sha256()
    for name in sorted(fields):
        array=np.ascontiguousarray(archive[name])
        fingerprint.update(f'{name}/{array.dtype.str}/{array.shape}\n'.encode('ascii'))
        fingerprint.update(array.view(np.uint8))
    if fingerprint.hexdigest()!=expected:raise ValueError('Unexpected arrays in input or donor assignment')

def weights(data,ids):
    w=np.zeros(len(ids))
    people=data['person'][ids];sessions=data['session'][ids];directions=data['direction'][ids]
    for person in np.unique(people):
        own=people==person
        for session in np.unique(sessions[own]):
            subset=own&(sessions==session)
            for direction in np.unique(directions[subset]):
                group=subset&(directions==direction)
                w[group]=1/(len(np.unique(sessions[own]))*len(np.unique(directions[subset]))*group.sum())
    return w/w.sum()

def features(d,z):
    n=len(d['domain'])
    def pool(x):
        return x.astype(float).reshape(n,5,4,-1).mean(2).reshape(n,-1)
    dt=1/32+d['age_s'][:,-2]-d['age_s'][:,-1]
    velocity=(d['patch_xyz_mm'][:,-1]-d['patch_xyz_mm'][:,-2])/dt[:,None]
    center=np.zeros((n,20,3,2)); good=np.zeros((n,3),dtype=bool)
    for prefix,names in [('balance',('D19','A1','B22')),('way',('C3','Cz','C4'))]:
        ids=z[prefix+'_rows']
        col=[z[prefix+'_names'].tolist().index(name) for name in names]
        good[ids]=z[prefix+'_good'][:,col]
        for j,k in enumerate(('mean','rms')):
            center[ids,:,:,j]=z[prefix+'_'+k][:,:,col]
    body=np.column_stack([pool(d['patch_xyz_mm']),pool(d['patch_rms']),d['past_rms'],
                          d['muscle_mask'],good,velocity,np.where(d['domain']==0,d['session'],0),d['direction']])
    head=pool(center);mask=np.broadcast_to(good[:,None,:,None],(n,5,3,2)).reshape(n,-1)
    base=np.concatenate([d['past_rms'],(velocity[:,None,:]*np.arange(1,33)[None,:,None]/256).reshape(n,96)],axis=1)
    return body,head,mask,base

def standardize_fit(x,mask,ids,w):
    x=x[ids];w=w[:,None]*mask[ids];total=w.sum(0)
    avg=(w*x).sum(0)/np.maximum(total,1e-15)
    sd=np.sqrt((w*(x-avg)**2).sum(0)/np.maximum(total,1e-15))
    return avg,np.where(sd>1e-10,sd,1.0)

def ridge(x,y,w):
    avg=w@x;offset=w@y
    x=x-avg
    co=np.linalg.solve(x.T@(w[:,None]*x)+.05*np.eye(x.shape[1]),x.T@(w[:,None]*(y-offset)))
    return np.vstack([co,offset-avg@co])

def losses(d,ids,pred):
    available=d['muscle_mask'][ids]
    muscle=(abs(pred[ids,:13]-d['future_rms'][ids])*available).sum(1)/available.sum(1)
    dist=np.linalg.norm(pred[ids,13:].reshape(-1,32,3)-d['future_path_mm'][ids],axis=2)
    return np.column_stack([muscle,dist.mean(1),dist[:,-1]])

def report(d,dom,predictions,other):
    common=(d['domain']==dom)&np.isfinite(predictions['central']).all(1)&np.isfinite(predictions[other]).all(1)
    rows=np.flatnonzero(common)
    people=np.unique(d['person'][rows])
    scores={key:[] for key in ('central',other)}
    for who in people:
        ids=rows[d['person'][rows]==who]
        for key in scores:scores[key].append(weights(d,ids)@losses(d,ids,predictions[key]))
    center,comparison=(np.array(scores[k]) for k in ('central',other))
    delta=center-comparison
    rng=np.random.default_rng(1641)
    boot=delta[rng.integers(len(people),size=(5000,len(people)))].mean(1)
    bounds=np.percentile(boot,[2.5,97.5,98.75],axis=0)
    return {'events':len(rows),'people':len(people),'metrics':{name:{'central':center[:,i].mean(),'comparison':comparison[:,i].mean(),
            'central_minus_comparison':delta[:,i].mean(),'people_lower':int((delta[:,i]<0).sum()),'ci95':bounds[:2,i].tolist(),
            'upper98_75':bounds[2,i]} for i,name in enumerate(MEASURES)}}

def fit(motion,scalp,support,out):
    with np.load(motion,allow_pickle=False) as f:
        check_arrays(f,FIELDS,MOTION_HASH)
        d={k:f[k] for k in FIELDS}
    with np.load(scalp,allow_pickle=False) as f:
        check_arrays(f,['person', 'domain', 'event', 'session', 'direction', 'cutoff', 'way_rows', 'way_names', 'way_good', 'way_mean', 'way_rms', 'balance_rows', 'balance_names', 'balance_good', 'balance_mean', 'balance_rms'],SCALP_HASH)
        for k in ('person','domain','session','direction','event','cutoff'):
            np.testing.assert_array_equal(d[k],f[k])
        body,head,mask,base=features(d,f)
    with np.load(support,allow_pickle=False) as f:
        check_arrays(f,('donor','row','central_mask'),'40b3731df54dae6ae9d0d9315209d6d4d33275982f217b3c6dd869b0f3efb456')
        donor=f['donor']; np.testing.assert_array_equal(f['row'],np.arange(len(donor)))
        np.testing.assert_array_equal(mask[:,:6:2],f['central_mask'])
    valid=donor>=0
    for k in ('person','session','direction','domain'):
        np.testing.assert_array_equal(d[k][valid],d[k][donor[valid]])
    np.testing.assert_array_equal(mask[valid],mask[donor[valid]])
    target=np.column_stack([d['future_rms'],d['future_path_mm'].reshape(-1,96)])-base
    results={k:np.full(base.shape,np.nan) for k in ('central','reference','wrong_trial')}
    fold=np.full(len(donor),-1);saved={}
    for dom in (0,1):
        select=d['domain']==dom
        for i,who in enumerate(np.unique(d['person'][select])):fold[select&(d['person']==who)]=i%3
        for f in range(3):
            train=np.flatnonzero(select&(fold!=f));test=np.flatnonzero(select&(fold==f))
            assert not set(d['person'][train])&set(d['person'][test])
            w=weights(d,train)
            bm,bs=standardize_fit(body,np.ones_like(body,dtype=bool),train,w)
            hm,hs=standardize_fit(head,mask,train,w)
            body_z=(body-bm)/bs; head_z=np.where(mask,(head-hm)/hs,0)
            prefix=f'd{dom}_f{f}_'
            for name,a in [('body_mean',bm),('body_sd',bs),('scalp_mean',hm),('scalp_sd',hs)]:saved[prefix+name]=a
            groups=[(np.arange(13,109),train)]+[(np.array([j]),train[d['muscle_mask'][train,j]]) for j in range(13)]
            for mode in ('reference','central'):
                x=np.column_stack([body_z, head_z if mode=='central' else np.zeros_like(head_z)])
                matrix=np.zeros((x.shape[1]+1,109))
                for columns,ids in groups:
                    if ids.size:
                        matrix[:,columns]=ridge(x[ids],target[np.ix_(ids,columns)],weights(d,ids))
                saved[prefix+mode]=matrix
                def predict(rows,brain):
                    design=np.column_stack([body_z[rows],brain,np.ones(len(rows))])
                    values=base[rows]+design@matrix
                    values[:,:13]=np.maximum(values[:,:13],0)*d['muscle_mask'][rows]
                    return values
                results[mode][test]=predict(test,x[test,body.shape[1]:])
                if mode=='central':
                    rows=test[valid[test]]
                    results['wrong_trial'][rows]=predict(rows,head_z[donor[rows]])
    out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'coefficients.npz',**saved)
    np.savez_compressed(out/'private.npz',fold=fold,donor=donor,**results)
    output={name:{k:report(d,i,results,k) for k in ('reference','wrong_trial')} for i,name in enumerate(('balance','way'))}
    output['all_four_reference_upper_negative']=all(output[dom]['reference']['metrics'][m]['upper98_75']<0 for dom in ('balance','way') for m in MEASURES[:2])
    (out/'results.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('motion','scalp','support','out'):p.add_argument('--'+name,type=Path,required=True)
    fit(**vars(p.parse_args()))
