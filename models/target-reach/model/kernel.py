"""Portable inference for goal-conditioned forecasts of a tracked transport object, in metres."""
import json
from pathlib import Path
import numpy as np

MODES=('full','pose_only','goal_only')
SEEDS=(17,41,73)
HORIZONS=(.4,.6,.8)

def tokens(xyz,time,hand,target):
    xyz=np.asarray(xyz,float);time=np.asarray(time,float);hand=np.asarray(hand).astype(str);target=np.asarray(target,int)
    n=len(xyz)
    if xyz.shape!=(n,5,3) or time.shape!=(n,5) or len(hand)!=n or len(target)!=n:raise ValueError('Expected five XYZ positions and sample times per trial')
    if not np.isfinite(xyz).all() or not np.isfinite(time).all() or not (np.diff(time,axis=1)>0).all():raise ValueError('Invalid motion history')
    if not np.isin(hand,['left','right']).all() or not np.isin(target,np.arange(1,10)).all():raise ValueError('Unknown hand or target')
    sides=(hand=='right').astype(int)
    delta=np.diff(xyz,axis=1,prepend=xyz[:,:1])
    common=np.eye(2)[sides]
    goal=np.eye(18)[sides*9+target-1]
    return np.concatenate([xyz-xyz[:,:1],delta,time[:,:,None],np.repeat(common[:,None],5,axis=1),np.repeat(goal[:,None],5,axis=1)],axis=-1)

def features(raw,model):
    x=(raw-np.asarray(model['mean']))/np.asarray(model['scale'])
    if model['mode']=='pose_only':x[:,:,9:]=0
    if model['mode']=='goal_only':x[:,:,:6]=0
    return x

def predict(raw,model):
    x=features(raw,model)
    p={k:np.asarray(v) for k,v in model['parameters'].items()}
    if model['family']=='ridge':
        return (x.reshape(len(x),-1)@p['coefficient']+p['bias']).reshape(-1,3,3)*model['target_scale']
    def dense(a,k):return a@p[k+'.weight'].T+p[k+'.bias']
    def norm(a,k):return (a-a.mean(-1,keepdims=True))/np.sqrt(a.var(-1,keepdims=True)+1e-5)*p[k+'.weight']+p[k+'.bias']
    x=dense(x,'embed')+p['pos']
    q,k,v=[t.reshape(-1,5,2,8).transpose(0,2,1,3) for t in np.split(dense(x,'qkv'),3,axis=-1)]
    logit=(q@k.swapaxes(-1,-2))/np.sqrt(8)
    a=np.exp(logit-logit.max(-1,keepdims=True));a/=a.sum(-1,keepdims=True)
    x=norm(x+dense((a@v).transpose(0,2,1,3).reshape(-1,5,16),'project'),'ln1')
    x=norm(x+dense(np.maximum(dense(x,'expand'),0),'reduce'),'ln2')
    return dense(x[:,-1],'readout').reshape(-1,3,3)*model['target_scale']

if __name__=='__main__':
    import argparse
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('weights',type=Path);cli.add_argument('example',type=Path);args=cli.parse_args()
    h=json.loads(args.example.read_bytes());m=json.loads(args.weights.read_bytes());x=tokens([h['xyz']],[h['time']],[h['hand']],[h['target']])
    print(json.dumps({'horizon_seconds_from_recording_start':HORIZONS,'displacements_m':predict(x,m)[0].tolist()}))
