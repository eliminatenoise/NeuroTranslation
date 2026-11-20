"""Fit on seven walkers or evaluate the sealed checkpoint on the three held mechanics outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import h5py
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import predict
from load import adapter
from load.knee_moment_source import load_trial, verify_archive

TRAIN=tuple(f'AB{i:02}' for i in range(1,8))
TEST=('AB08','AB09','AB10')
PARENT_SHA='4541317c4e5d7f08f24d221278a0f3fec6f9f9acb9c7ea17669ef28511c187fe'
METHOD_SHA='c19fb4fe4c323c0bba559a8e03e92a7dc120704566a807b5dd3d2f351ce7c412'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def trial_features(source,person):
    trial=load_trial(source,person,include_moments=True)
    a,y=trial.angles,trial.moments
    cuts=np.arange(399,len(a)-25,5)
    bad=np.r_[0,(~(np.isfinite(a)&(a!=0)).all(axis=1)).cumsum()]
    good_past=(bad[cuts+1]==bad[cuts-399])
    future=y[cuts+25]
    good_target=np.isfinite(future).all(axis=1)&(future!=0).all(axis=1)
    support={'candidates':len(cuts),'bad_angle_history':int((~good_past).sum()),
             'bad_target':int((~good_target).sum()),'bad_target_after_angle_gate':int((good_past&~good_target).sum())}
    cuts=cuts[good_past&good_target]
    if not len(cuts):raise ValueError(f'No valid windows in {person}')
    windows=np.lib.stride_tricks.sliding_window_view(a,(400,6))[:,0]
    packed=[];bins=[];periods=[]
    for start in range(0,len(cuts),128):
        history=windows[cuts[start:start+128]-399]
        period=adapter.periods(history);x,b=adapter.features(history,period)
        packed.append(x);bins.append(b);periods.append(period)
    p=np.concatenate(periods)
    return dict(person=person,x=np.concatenate(packed),bins=np.concatenate(bins),y=y[cuts+25],
                current=y[cuts],replay=y[cuts+25-p],support=support)


def scale(x,weights):
    center=np.average(x,axis=0,weights=weights)
    sd=np.sqrt(np.average((x-center)**2,axis=0,weights=weights))
    return center,np.where(sd<1e-8,1.,sd)


def design(mode,raw,bins,config,w):
    if mode=='ridge':return raw
    encoder=adapter.encoder_weights(w,mode)
    z=(bins-w['load.bin_mean'])/w['load.bin_sd']
    h=np.concatenate([adapter.states(config,encoder,z[i:i+512],predict.linear,predict.encode) for i in range(0,len(z),512)])
    return np.column_stack((raw,h.reshape(len(raw),-1)))


def fit_network(parent,bins,raw,target,lengths,state):
    import torch
    from network import SharedMotion
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(4281)
    net=SharedMotion.load(parent)
    torch.nn.init.zeros_(net.readout.weight);torch.nn.init.zeros_(net.readout.bias)
    baseline=adapter.readout(state,'ridge',raw)
    z=torch.as_tensor((bins-state['load.bin_mean'])/state['load.bin_sd'],dtype=torch.float32)
    residual=torch.as_tensor((target-baseline)/state['load.target_sd'],dtype=torch.float32)
    opt=torch.optim.AdamW(net.parameters(),lr=.001,weight_decay=.001)
    rng=np.random.default_rng(4281);n=np.asarray(lengths);starts=np.r_[0,n.cumsum()[:-1]]
    for _ in range(400):
        p=rng.integers(len(n),size=96);idx=starts[p]+rng.integers(n[p])
        hidden=net.project(z[idx])+net.position
        for block in net.blocks:hidden=block(hidden)
        result=net.readout(net.last_norm(hidden[:,-1]))
        loss=(result-residual[idx]).square().mean()
        opt.zero_grad();loss.backward();opt.step()
    for k,v in net.state_dict().items():state['load.trained.'+k]=v.detach().cpu().numpy().copy()


def fit(archive,parent,out):
    if sha(parent)!=PARENT_SHA:raise ValueError('Original parent checkpoint required; see README.')
    with h5py.File(archive) as h:people=[trial_features(h,i) for i in TRAIN]
    sizes=[len(r['x']) for r in people];wgt=np.concatenate([np.full(n,1/(len(sizes)*n)) for n in sizes])
    raw,bins,y=[np.concatenate([r[k] for r in people]) for k in ('x','bins','y')]
    config,_=predict.read_checkpoint(parent)
    with np.load(parent,allow_pickle=False) as old:state={n:old[n] for n in old.files if n!='configuration'}
    state['load.bin_mean'],state['load.bin_sd']=scale(bins.reshape(-1,6),np.repeat(wgt/4,4))
    state['load.target_mean'],state['load.target_sd']=scale(y,wgt)
    for mode in ('ridge','shared','scrambled'):
        # The reference reader evaluates every encoder in float64.
        w={k:v.astype(np.float64,copy=False) for k,v in state.items()}
        x=design(mode,raw,bins,config,w)
        mean,sd=scale(x,wgt);z=(x-mean)/sd;zt=z.T*wgt
        coef=np.linalg.solve(zt@z+.03*np.eye(z.shape[1]),zt@(y-state['load.target_mean']))
        for k,v in [('mean',mean),('sd',sd),('coef',coef),('bias',state['load.target_mean'])]:
            state['load.'+mode+'.'+k]=v
    fit_network(parent,bins,raw,y,sizes,state)
    config['knee_moment']={'format':1,'sample_hz':100,'history_frames':400,'lead_frames':25,'input':adapter.CHANNELS,'units':'N m/kg'}
    state['configuration']=np.array(json.dumps(config))
    np.savez_compressed(out,**state)
    print(json.dumps({'fit':TRAIN,'windows':sizes,'total':sum(sizes),'sha256':sha(out),'method_sha256':METHOD_SHA}))


def nearest(raw,train,center,sd):
    x=(raw[:,:54]-center[:54])/sd[:54]; matched=[]
    for row in train:
        ref=(row['x'][:,:54]-center[:54])/sd[:54]
        distances=(x*x).sum(1)[:,None]+(ref*ref).sum(1)[None,:]-2*x@ref.T
        matched.append(row['y'][distances.argmin(axis=1)])
    return np.median(matched,axis=0)


def summary(pred,y,mask):
    if not np.any(mask):return None
    return {key:np.mean(np.abs(value[mask]-y[mask]),axis=0).tolist() for key,value in pred.items()}


def score(archive,checkpoint,out):
    config,w=predict.read_checkpoint(checkpoint)
    if config.get('knee_moment',{}).get('format')!=1:raise ValueError('Fitted mechanics checkpoint required')
    rows=[]
    with h5py.File(archive) as h:
        train=[trial_features(h,i) for i in TRAIN]
        for person in TEST:
            o=trial_features(h,person);pred={}
            for mode in adapter.MODES:
                pred[mode]=adapter.from_features(mode,o['x'],o['bins'],config,w,predict.linear,predict.encode)
            pred['train_walker_match']=nearest(o['x'],train,w['load.ridge.mean'],w['load.ridge.sd'])
            n=len(o['y']);whole=summary(pred,o['y'],np.ones(n,dtype=bool))
            subset=np.isfinite(o['current']).all(1)&np.isfinite(o['replay']).all(1)&(o['current']!=0).all(1)&(o['replay']!=0).all(1)
            subset_pred={**pred,'hold_past_moment':o['current'],'replay_past_moment':o['replay']}
            rows.append(dict(person=person,windows=n,eligibility=o['support'],right_left_mae=whole,
                             past_moment_windows=int(subset.sum()),right_left_mae_with_past_measurements=summary(subset_pred,o['y'],subset)))
    def aggregate(key):
        subset=[r[key] for r in rows if r[key] is not None]
        return {k:float(np.mean([person[k] for person in subset])) for k in subset[0]} if subset else {}
    avg=aggregate('right_left_mae')
    paired={}
    for mode,other in [('trained','ridge'),('trained','train_walker_match'),('shared','ridge'),('shared','scrambled')]:
        diffs=[float(np.mean(r['right_left_mae'][mode])-np.mean(r['right_left_mae'][other])) for r in rows]
        paired[mode+'_minus_'+other]={'per_walker':diffs,'mean':float(np.mean(diffs)),'wins':sum(d<0 for d in diffs)}
    counts=[len(v['x']) for v in train]
    result={'method_sha256':METHOD_SHA,'parent_sha256':PARENT_SHA,'checkpoint_sha256':sha(checkpoint),
            'training':{'people':list(TRAIN),'windows_by_person':counts,'windows':sum(counts)},
            'evaluation':{'scope':'Held mechanical outcomes of three people whose earlier optical angle outcomes were previously studied.',
                          'people':list(TEST),'windows':sum(r['windows'] for r in rows),'per_person':rows},
            'mean_person_mae_Nm_per_kg':avg,'mean_person_mae_past_moment_subset':aggregate('right_left_mae_with_past_measurements'),
            'paired_differences_Nm_per_kg':paired,
            'trained_advantage':all(paired['trained_minus_'+k]['wins']==3 for k in ('ridge','train_walker_match')),
            'shared_encoder_advantage':all(paired['shared_minus_'+k]['wins']==3 for k in ('ridge','scrambled'))}
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(avg))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=('fit','score'));ap.add_argument('archive',type=Path)
    ap.add_argument('checkpoint',type=Path);ap.add_argument('output',type=Path)
    a=ap.parse_args()
    if sha(HERE/'METHOD.md')!=METHOD_SHA or a.checkpoint.resolve()==a.output.resolve():ap.error('Use the frozen method and a distinct output path')
    verify_archive(a.archive)
    (fit if a.action=='fit' else score)(a.archive,a.checkpoint,a.output)
