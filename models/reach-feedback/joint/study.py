"""Use frozen joint models, compare native/portable outputs, and report grouped physical errors."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from portable import features,predict,MODES,SEEDS
def dev(y,mu):
    m=np.maximum(mu,1e-6)
    t=np.where(y>0,y*np.log(np.maximum(y,1e-300)/m),0)
    return 2*(t-y+m)
def per_original(values,ids,roster):
    rows=[]
    for orig in roster:
        z=values[ids==orig];rows.append(z.mean(0) if len(z) else np.full(values.shape[1:],np.nan))
    return np.array(rows)
def take_blocks(n):
    rng=np.random.default_rng(20261125);block=min(n,8)
    starts=rng.integers(n-block+1,size=(5000,(n+block-1)//block))
    return (starts[:,:,None]+np.arange(block)).reshape(5000,-1)[:,:n]
def stats(x,draw):
    sampled=x[draw]
    with np.errstate(invalid='ignore',divide='ignore'):
        values=np.nansum(sampled,axis=1)/np.isfinite(sampled).sum(1)
    kept=values[np.isfinite(values)]
    return {'mean':float(np.nanmean(x)),'interval':np.quantile(kept,[.025,.975]).tolist(),'valid_draws':len(kept)}
def losses(motion,rate,y,z):
    """Return window-wise errors; endpoint is 100 ms beyond the last known sampled position."""
    axes={'hand_mm':(0,3,1000.),'elbow_mm':(3,6,1000.),'handle_cm':(6,8,1.)}
    values={}
    for kind,(a,b,scale) in axes.items():
        e=np.linalg.norm(motion[:,:,a:b]-y[:,:,a:b],axis=-1)*scale
        values[kind+'_endpoint']=e[:,-1];values[kind+'_trajectory']=e.mean(1)
    v=z.sum(1);mu=rate.sum(1)
    values['count_deviance']=dev(v,mu).mean(1)
    values['count_mae']=np.abs(v-mu).mean(1)
    values['bin_deviance']=dev(z,rate).mean((1,2))
    return values
def native_predict(raw,m):
    import torch
    from fit import JointFit
    from portable import standard
    net=JointFit(m['mode'],np.ones(23))
    net.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in m['parameters'].items()})
    net.eval()
    with torch.no_grad():a,b=net(torch.tensor(standard(raw,m),dtype=torch.float32))
    return a.numpy()*m['motion_scale'],b.numpy()
def run(args):
    if args.with_native:
        import torch
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
    with np.load(args.source,allow_pickle=False) as d:
        original=d['original'];roster=d['roster_original'];raw=features(d['pose'],d['spikes'],d['cue'])
        y,z=d['movement'],d['delayed']
        ids={k:d[k] for k in ('original','block','ordinal','k','workspace','donor')}
    assert len(np.unique(roster))==len(roster) and set(original)<=set(roster)
    draw=take_blocks(len(roster));metrics={};outputs={};series={};parity={}
    for mode in MODES:
        native_delta=[];path_pool=[];rate_pool=[];seeds=[]
        for seed in SEEDS:
            m=json.loads((args.weights/f'{mode}-{seed}.json').read_bytes());path,rate=predict(raw,m)
            if args.with_native:
                a,b=native_predict(raw,m)
                dm=float(np.max(abs(a-path)));dc=float(np.max(abs(b-rate)));assert max(dm,dc)<2e-5,(dm,dc);native_delta.append([dm,dc])
            row=losses(path,rate,y,z)
            if mode=='parallel_count':
                row={k:v for k,v in row.items() if 'count_' in k or k=='bin_deviance'}
            else:path_pool.append(path)
            if mode=='parallel_motor':
                row={k:v for k,v in row.items() if not ('count_' in k or k=='bin_deviance')}
            else:rate_pool.append(rate)
            seeds.append({key:per_original(v,original,roster) for key,v in row.items()})
        if path_pool:outputs[mode+'_movement']=np.stack(path_pool)
        if rate_pool:outputs[mode+'_counts']=np.stack(rate_pool)
        series[mode]={key:np.stack([r[key] for r in seeds]) for key in seeds[0]}
        metrics[mode]={k:{**stats(v.mean(0),draw),'by_seed':[float(np.nanmean(x)) for x in v]} for k,v in series[mode].items()}
        parity[mode]=native_delta
    diffs={}
    for a,b in [('rollout','parallel'),('rollout','recurrent'),('parallel','parallel_count'),('parallel','parallel_motor')]:
        diffs[a+'_minus_'+b]={key:stats((series[a][key]-series[b][key]).mean(0),draw) for key in sorted(series[a].keys()&series[b].keys())}
    comp=diffs['rollout_minus_parallel']
    gate=all(comp[k]['interval'][1]<0 for k in ('hand_mm_endpoint','elbow_mm_endpoint','count_deviance'))
    args.out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.out/'predictions.npz',**outputs,**ids,seeds=np.array(SEEDS))
    report={'family':'secondary controlled closed rollout comparison','source':hashlib.sha256(args.source.read_bytes()).hexdigest(),'rows':len(y),'roster_originals':len(roster),'eligible_originals':len(np.unique(original)),'metrics':metrics,'paired':diffs,'all_three_rollout_better':gate,'parameters_lock_sha256':hashlib.sha256((args.weights/'lock.json').read_bytes()).hexdigest(),'native_numpy_max_by_seed':[dict(mode=k,difference=v) for k,v in parity.items()]}
    (args.out/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':
    c=argparse.ArgumentParser(description=__doc__)
    for k in ('source','weights','out'):c.add_argument(k,type=Path)
    c.add_argument('--with-native',action='store_true');run(c.parse_args())
