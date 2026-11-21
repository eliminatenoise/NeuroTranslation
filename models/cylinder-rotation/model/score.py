"""Run frozen single-clock models and compare errors in radians/second and metres/second² separately."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from portable import make_tokens,predict,MODES,SEEDS

def read(path):
    with np.load(path,allow_pickle=False) as n:return {k:n[k] for k in n.files}
def rows_to_people(values,ids,hands,trials):
    # values row x fit; every eligible recording has equal weight within a person.
    unique,order=np.unique(np.array([f'{p}/{h}/{t}' for p,h,t in zip(ids,hands,trials)]),return_inverse=True)
    sums=np.zeros((len(unique),values.shape[1]));np.add.at(sums,order,values)
    per_record=sums/np.bincount(order)[:,None]
    person=np.array([int(k.split('/',1)[0]) for k in unique]);people=np.unique(person)
    return people,np.stack([per_record[person==p].mean(0) for p in people])
def one_table(loss,src,mask,domain):
    if not mask.any():return {'windows':0,'recordings':0,'participants':0}
    ids=src['participant'][mask];hands=src['hand'][mask];trials=src['trial'][mask]
    stored={};aggregated={}
    for key,array in loss[domain].items():
        v=array[:,mask].T
        if not np.isfinite(v).all():continue
        people,full=rows_to_people(v,ids,hands,trials)
        means=full.mean(1);aggregated[key]=means
        stored[key]={'error':float(means.mean()),'by_fit':full.mean(0).tolist(),'by_person':dict(zip(map(str,people),means.tolist()))}
    index=np.random.default_rng(20261124).integers(0,len(people),(10000,len(people)))
    diffs={}
    for key in stored:
        if key=='transformer_full':continue
        a=aggregated['transformer_full']-aggregated[key]
        diffs[key]={'difference':float(a.mean()),'interval':np.quantile(a[index].mean(1),[.025,.975]).tolist(),'better_people':int((a<0).sum())}
    return {'windows':len(ids),'recordings':len(set(zip(ids,hands,trials))),'participants':len(people),'scores':stored,'full_minus':diffs}
def forecasts(x,weights):
    return np.concatenate([predict(x[i:i+512],weights) for i in range(0,len(x),512)])
def summarize(src,dev,weights,out):
    x=make_tokens(src['gyro'],src['accel'],src['time'],src['hand'],src['target'])
    ids=src['participant'];side=src['hand'];goal=src['target'];times=src['cutoff']
    matched=src['donor']>=0;donor=src['donor'].astype(int)
    if matched.any():
        for n in ('participant','hand','target','cutoff'):np.testing.assert_array_equal(src[n][matched],src[n][donor[matched]])
        assert (src['trial'][donor[matched]]<src['trial'][matched]).all()
    alt=x.copy();alt[matched,:,6:12]=x[donor[matched],:,6:12]
    observed=np.concatenate([src['y_gyro'],src['y_accel']],axis=1)
    recent=np.concatenate([src[k][:,-10:].mean(1) for k in ('gyro','accel')],1)
    earlier=np.concatenate([src[k][:,:10].mean(1) for k in ('gyro','accel')],1)
    forecast={'persistence':recent[None],'linear_trend':(2*recent-earlier)[None]}
    domain=np.concatenate([dev['y_gyro'],dev['y_accel']],axis=1)
    mean=np.full_like(observed,np.nan,dtype=float);means={}
    for hand,target,cutoff in sorted(set(zip(side,goal,times))):
        m=(dev['hand']==hand)&(dev['target']==target)&(dev['cutoff']==cutoff)
        if not m.any():continue
        _,mup=rows_to_people(domain[m],dev['participant'][m],dev['hand'][m],dev['trial'][m])
        mu=mup.mean(0);mean[(side==hand)&(goal==target)&(times==cutoff)]=mu
        means[f'{hand}/{target}/{cutoff}']=mu.tolist()
    forecast['hand_target_time_mean']=mean[None]
    for family,seeds in [('transformer',SEEDS),('ridge',('ridge',))]:
        for mode in MODES:
            if mode=='gyro_loss' and family=='ridge':continue
            bundle=[json.loads((weights/f'{mode}-{seed}.json').read_bytes()) for seed in seeds]
            forecast[family+'_'+mode]=np.array([forecasts(x,w) for w in bundle])
            if mode=='full':
                out_alt=np.full((len(seeds),len(x),6),np.nan)
                if matched.any():out_alt[:,matched]=np.array([forecasts(alt[matched],w) for w in bundle])
                forecast[family+'_wrong_accel']=out_alt
    losses={name:{} for name in ('gyro','accel')}
    for m,p in forecast.items():
        for name,sl in [('gyro',slice(0,3)),('accel',slice(3,6))]:
            if name=='accel' and m.endswith('gyro_loss'):continue
            losses[name][m]=np.linalg.norm(p[:,:,sl]-observed[:,sl],axis=2)
    summary={'units':{'gyro':'rad/s','accel':'m/s² inclusive of gravity'},'training_means':means,'groups':{}}
    conditional={'overall':np.ones(len(ids),bool),**{f'hand_{s}':side==s for s in ('right','left')},**{f'target_{g}':goal==g for g in range(1,10)},**{f'cutoff_{t}ms':times==t for t in np.arange(200,2601,400)}}
    for phase,mask in [('all',np.ones(len(ids),bool)),('matched',matched)]:
        for label,extra in conditional.items():
            for name in losses:summary['groups'][f'{phase}/{label}/{name}']=one_table(losses,src,mask&extra,name)
    core=summary['groups']['matched/overall/gyro'].get('full_minus',{})
    summary['primary_passed']=bool(core) and all(core[k]['interval'][1]<0 for k in ('transformer_gyro_task','transformer_wrong_accel'))
    summary['model_lock_sha256']=hashlib.sha256((weights/'weights-lock.json').read_bytes()).hexdigest()
    out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    # The acceleration head had no training objective in this particular fit.
    forecast['transformer_gyro_loss'][:,:,3:]=np.nan
    np.savez_compressed(out/'forecasts.npz',**forecast,**{k:src[k] for k in ('participant','hand','target','trial','repetition','cutoff','donor')},seeds=SEEDS)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','train','weights','out'):p.add_argument(k,type=Path)
    args=p.parse_args()
    summarize(read(args.source),read(args.train),args.weights,args.out)
