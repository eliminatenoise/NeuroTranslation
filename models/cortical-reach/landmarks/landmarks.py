"""Regularized 100-ms handle forecasts with paired handle, arm landmarks and cortical inputs."""
import argparse, json
from pathlib import Path
import numpy as np

PATTERNS = {'body_control':('movement','cue'), 'body_markers':('movement','cue','marker'),
            'body_neural':('movement','cue','neural'), 'full':('movement','cue','marker','neural'),
            'markers':('marker',), 'neural':('neural',)}
EPOCHS={0:'perturbation',1:'reach'}
FEATURES=('movement','cue','marker','neural')

def load(path):
    fields=(*FEATURES,'marker_valid','original_trial','trial','epoch','offset','k','donor','y','cv')
    with np.load(path,allow_pickle=False) as source:data={k:source[k] for k in fields}
    n=len(data['trial'])
    for k,width in [('movement',4),('cue',7),('marker',12),('neural',30)]:
        if data[k].shape!=(n,5,width):raise ValueError('Invalid '+k+' shape')
    if data['y'].shape!=(n,2) or data['cv'].shape!=(n,3,2):raise ValueError('Invalid outcome/control')
    return data

def support(data):
    ok=data['marker_valid'].reshape(len(data['trial']),-1).all(1)
    for name in ('movement','neural','cue','marker','y','cv'):
        ok=ok&np.isfinite(data[name].reshape(len(ok),-1)).all(1)
    return ok

def weights(data,ids):
    trials,epochs=data['trial'][ids],data['epoch'][ids]
    result=np.zeros(len(ids))
    for t in np.unique(trials):
        own=trials==t
        modes=np.unique(epochs[own])
        for e in modes:
            pick=own&(epochs==e)
            result[pick]=1/(len(modes)*pick.sum())
    return result/result.sum()

def flat(a,ids):
    return a[ids].astype(np.float64).reshape(len(ids),-1)

def standardized(data,ids,fields,state,donations=None):
    cols=[]
    for key in fields:
        source=(donations or {}).get(key,ids)
        center,scale=(np.array(a) for a in state['scales'][key])
        cols.append((flat(data[key],source)-center)/scale)
    return np.column_stack(cols)

def train(data):
    ids=np.flatnonzero(support(data));w=weights(data,ids)
    state={'format':'cortical-reach-landmarks-1','scales':{},'coef':{},'n_train':len(ids)}
    for name in FEATURES:
        x=flat(data[name],ids);mean=w@x
        sd=np.sqrt(w@(x-mean)**2)
        state['scales'][name]=[mean.tolist(),np.where(sd>1e-12,sd,1.).tolist()]
    for name,fields in PATTERNS.items():
        x=standardized(data,ids,fields,state);target=data['y'][ids].copy()
        if 'movement' in fields:target-=data['cv'][ids,0,:]
        mean=w@x; center=w@target; z=x-mean
        coef=np.linalg.solve(z.T@(w[:,None]*z)+.1*np.eye(z.shape[1]),z.T@(w[:,None]*(target-center)))
        state['coef'][name]=np.vstack([coef,center-mean@coef]).tolist()
    return state

def forecast(data,ids,name,state,donations=None):
    fields=PATTERNS[name];x=standardized(data,ids,fields,state,donations)
    coef=np.array(state['coef'][name]);y=x@coef[:-1]+coef[-1]
    return y+data['cv'][ids,0,:] if 'movement' in fields else y

def comparisons(data,pred,ids,contrasts):
    groups=np.unique(data['trial'][ids]); index=data['trial'][ids]; phase=data['epoch'][ids]
    errors={k:p[ids]-data['y'][ids] for k,p in pred.items()}
    vals={k:np.column_stack([np.linalg.norm(v,axis=1), np.sum(v*v,axis=1),abs(v),v]) for k,v in errors.items()}
    per_epoch={}; per={}
    for name,value in vals.items():
        cube=np.full((len(groups),2,6),np.nan)
        for i,t in enumerate(groups):
            for e in (0,1):
                mask=(index==t)&(phase==e)
                if mask.any():cube[i,e]=value[mask].mean(0)
        present=np.isfinite(cube[:,:,0]).sum(1)
        per[name]=np.nansum(cube,axis=1)/present[:,None]
        per_epoch[name]=cube
    def metrics(mean):
        return dict(distance_cm=mean[0],endpoint_rmse_cm=np.sqrt(mean[1]),xy_mae_cm=mean[2:4].tolist(),xy_bias_cm=mean[4:6].tolist())
    stat={'total_rows':len(ids),'original_trials':len(groups),'by_epoch':{},'methods':{},'contrasts':{}}
    for m in per:stat['methods'][m]=metrics(per[m].mean(0))
    for e,label in EPOCHS.items():
        chosen=phase==e
        stat['by_epoch'][label]={'rows':int(chosen.sum()),'trials':len(np.unique(index[chosen])),
            'methods':{m:metrics(np.nanmean(x[:,e,:],axis=0)) for m,x in per_epoch.items()}}
    # Resample original trials in chronological blocks, keeping both epochs attached.
    # The full split, including a trial with no common donor rows, defines the clock.
    all_trials=data['original_trial'].reshape(-1)
    if len(set(all_trials.tolist()))!=len(all_trials):raise ValueError('Duplicate original trial')
    trial_order={int(t):i for i,t in enumerate(all_trials)}
    gpos=np.array([trial_order[int(t)] for t in groups])
    rng=np.random.default_rng(1641)
    starts=rng.integers(len(all_trials),size=(5000,(len(all_trials)+11)//12))
    draw=((starts[:,:,None]+np.arange(12))%len(all_trials)).reshape(5000,-1)[:,:len(all_trials)]
    for a,b in contrasts:
        effects=per[a][:,0]-per[b][:,0]; all_effect=np.full(len(all_trials),np.nan);all_effect[gpos]=effects
        sample=all_effect[draw]; n=np.isfinite(sample).sum(1); d=np.nansum(sample[n>0],axis=1)/n[n>0]
        ci=np.quantile(d,[.025,.975]);epoch_delta={label:np.nanmean(per_epoch[a][:,e,0]-per_epoch[b][:,e,0]) for e,label in EPOCHS.items()}
        stat['contrasts'][a+'_minus_'+b]={'mean':effects.mean(),'interval95':ci.tolist(),'upper97_5':ci[1],
            'trials_better':int((effects<0).sum()),'epoch_means':epoch_delta,'bootstrap_valid_draws':len(d),
            'gate':bool(effects.mean()<0 and ci[1]<0 and all(v<0 for v in epoch_delta.values()))}
    return stat

def score(data,state,out):
    good=support(data);ids=np.flatnonzero(good)
    n=len(good); preds={m:np.full((n,2),np.nan) for m in (*PATTERNS,'stationary','velocity40','velocity100','velocity200')}
    for m in PATTERNS:preds[m][ids]=forecast(data,ids,m,state)
    preds['stationary'][ids]=0
    for i,m in enumerate(['velocity40','velocity100','velocity200']):preds[m][ids]=data['cv'][ids,i]
    main=comparisons(data,preds,ids,[('body_markers','body_control'),('full','body_markers')])
    donor=data['donor'];paired=np.flatnonzero(good&(donor>=0)&good[np.maximum(donor,0)])
    for key in ('offset','epoch'):np.testing.assert_array_equal(data[key][paired],data[key][donor[paired]])
    assert (data['k'][donor[paired]]+10<data['k'][paired]-20).all()
    for key in ('neural','marker'):
        v=np.full((n,2),np.nan);v[paired]=forecast(data,paired,'full',state,{key:donor[paired]});preds['wrong_'+key]=v
    timing=comparisons(data,preds,paired,[('full','wrong_marker'),('full','wrong_neural')])
    out.mkdir(parents=True,exist_ok=True)
    cells={}
    for e,label in EPOCHS.items():
        cells[label]={}
        for k in (0,5,10,15):
            take=(data['epoch']==e)&(data['offset']==k); available=data['marker_valid'][take]
            mask_hand=available[:,:,[0,1,2,6,7,8]].all(axis=(1,2))
            mask_elbow=available[:,:,[3,4,5,9,10,11]].all(axis=(1,2))
            cells[label][str(k)]={'source_rows':int(take.sum()),'source_excluded':len(data['original_trial'])-int(take.sum()),
                                  'missing_hand':int((~mask_hand).sum()),'missing_ulna':int((~mask_elbow).sum()),
                                  'eligible':int((take&good).sum()),'matched_donor':int((take[paired]).sum())}
    (out/'results.json').write_text(json.dumps({'original_trials':len(data['original_trial']),'cells':cells,'eligible':len(ids),'excluded':int((~good).sum()),'primary':main,'timing':timing,
        'offset_support':{str(k):int(np.sum(good&(data['offset']==k))) for k in np.unique(data['offset'])}},indent=2,allow_nan=False)+'\n')
    np.savez_compressed(out/'private.npz',trial=data['trial'],k=data['k'],valid=good,donor=donor,**preds)

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('action',choices=('train','score'));cli.add_argument('data',type=Path)
    cli.add_argument('weights',type=Path);cli.add_argument('--output',type=Path)
    args=cli.parse_args();d=load(args.data)
    if args.action=='train':
        args.weights.write_text(json.dumps(train(d),separators=(',',':'),allow_nan=False)+'\n')
    else:
        if args.output is None:cli.error('Provide --output for scoring')
        score(d,json.loads(args.weights.read_text()),args.output)
