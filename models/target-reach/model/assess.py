"""Score registered object-transport forecasts on whole participants."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from kernel import MODES,SEEDS,HORIZONS,predict,tokens

def load(path):
    with np.load(path,allow_pickle=False) as a:
        return {k:a[k] for k in a.files}

def error(p,y):
    return np.linalg.norm(p-y,axis=-1)

def summarize(losses,ids,mask,group):
    subjects=np.unique(ids[group])
    # Each array is seed x row x horizon, with fixed models represented by one fit.
    res={}
    for method,loss in losses.items():
        a=loss.mean(0)[:,mask][group]
        person=np.array([v.mean() if len(v:=a[(ids[group]==s)&np.isfinite(a)]) else np.nan for s in subjects])
        good=np.isfinite(person);per=person[good]
        if len(per):
            draws=np.random.default_rng(20261122).integers(0,len(per),(10000,len(per)))
            ci=np.quantile(per[draws].mean(1),[.025,.975])
            res[method]={'mean_m':float(per.mean()),'ci':ci.tolist(),'by_participant':dict(zip(map(str,subjects[good]),per.tolist())),'by_fit_m':[float(np.mean([np.nanmean(e[(ids==s)&group,mask]) for s in subjects[good]])) for e in loss]}
    return res

def compare(scores,a,b):
    aa=scores[a]['by_participant'];bb=scores[b]['by_participant']
    assert set(aa)==set(bb)
    z=np.array([v-bb[s] for s,v in aa.items()])
    draws=np.random.default_rng(20261122).integers(0,len(z),(10000,len(z)))
    return {'mean_m':float(z.mean()),'ci':np.quantile(z[draws].mean(1),[.025,.975]).tolist(),'by_participant':dict(zip(aa,z.tolist()))}

def run(data,weights,train,out):
    src=load(data);dev=load(train);out.mkdir(exist_ok=True,parents=True)
    ids,side,target=src['participant'],src['hand'].astype(str),src['target'].astype(int)
    raw=tokens(src['xyz'],src['time'],side,target)
    wrong=[tokens(src['xyz'],src['time'],side,(target-1+n)%9+1) for n in range(1,9)]
    y=np.asarray(src['y'],float).copy();valid=src['valid'].astype(bool);y[~valid]=np.nan
    v=(src['xyz'][:,-1]-src['xyz'][:,-2])/(src['time'][:,-1]-src['time'][:,-2])[:,None]
    elapsed=np.asarray(HORIZONS)[None,:]-src['time'][:,-1,None]
    predicted={'stationary':np.zeros_like(y)[None], 'velocity':(v[:,None,:]*elapsed[:,:,None])[None]}
    mu=np.full_like(y,np.nan);means={}
    for hand,goal in sorted(set(zip(side,target))):
        sub=(dev['hand'].astype(str)==hand)&(dev['target']==goal)
        for h in range(3):
            eligible=sub&dev['valid'][:,h].astype(bool)
            people=np.unique(dev['participant'][eligible])
            if len(people):
                avg=np.mean([dev['y'][eligible&(dev['participant']==s),h].mean(0) for s in people],0)
                mu[(side==hand)&(target==goal),h]=avg
                means[f'{hand}/{goal}/{h}']=avg.tolist()
    predicted['goal_hand_mean']=mu[None]
    loss={}
    for family,seeds in [('transformer',SEEDS),('ridge',('ridge',))]:
        for mode in MODES:
            models=[json.loads((weights/f'{mode}-{s}.json').read_bytes()) for s in seeds]
            p=np.array([predict(raw,w) for w in models])
            predicted[family+'_'+mode]=p
            if mode=='full':
                loss[family+'_wrong_target']=np.array([np.mean([error(predict(alt,w),y) for alt in wrong],axis=0) for w in models])
    for name,p in predicted.items():loss[name]=error(p,y)
    support={};groups={}
    for h,hz in enumerate(HORIZONS):
        key=str(int(hz*1000));support[key]={}
        for label,sel in [('both',np.ones(len(ids),bool)),('left',side=='left'),('right',side=='right')]:
            group=sel&valid[:,h]
            support[key][label]={'n':int(group.sum()),'people':len(np.unique(ids[group]))}
            if not group.any():continue
            table=summarize(loss,ids,h,group)
            comparisons={c:compare(table,'transformer_full',c) for c in ('transformer_pose_only','transformer_goal_only','transformer_wrong_target','goal_hand_mean','ridge_full')}
            groups[key+'/'+label]={'scores':table,'comparisons':comparisons,'true_amplitude_m':float(np.mean([np.mean(np.linalg.norm(y[(ids==s)&group,h],axis=1)) for s in np.unique(ids[group])]))}
    primary=groups.get('600/both',{}).get('comparisons',{})
    gate=None if not primary else all(primary[m]['ci'][1]<0 for m in ('transformer_pose_only','transformer_wrong_target'))
    out_file=out/'summary.json'
    out_file.write_text(json.dumps({'units':'metres, mean 3D Euclidean error per participant','rows':len(ids),'people':len(np.unique(ids)),'horizons_s':HORIZONS,'eligible':support,'groups':groups,'incremental_gate':gate,'training_only_goal_hand_mean':means,'model_lock':hashlib.sha256((weights/'weights-lock.json').read_bytes()).hexdigest()},indent=2,allow_nan=False)+'\n')
    np.savez_compressed(out/'forecasts.npz',**predicted,**{k:src[k] for k in ('participant','hand','target','repetition','valid')})
if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for key in ('data','weights','train','out'):cli.add_argument(key,type=Path)
    args=cli.parse_args();run(args.data,args.weights,args.train,args.out)
