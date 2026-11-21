"""Dependency-light inertial forecasting. All angles here are rates, expressed in rad/s."""
import json
from pathlib import Path
import numpy as np

MODES=('full','gyro_task','accel_task','sensors','task','gyro_loss')
SEEDS=(17,41,73)
def make_tokens(gyro,accel,times,hands,targets):
    g=np.asarray(gyro,float);a=np.asarray(accel,float);ts=np.asarray(times,float)
    hands=np.asarray(hands).astype(str);targets=np.asarray(targets,int)
    n=len(g)
    if g.shape!=(n,20,3) or a.shape!=g.shape or ts.shape!=(n,20):raise ValueError('Expected twenty consecutive three-axis samples')
    if not all(np.isfinite(v).all() for v in (g,a,ts)) or not (np.diff(ts,axis=1)>0).all():raise ValueError('Invalid history')
    if not np.isin(hands,['left','right']).all() or not np.isin(targets,np.arange(1,10)).all():raise ValueError('Unknown hand or target')
    side=(hands=='right').astype(int)
    cues=np.concatenate([np.eye(2)[side],np.eye(18)[side*9+targets-1]],axis=1)
    parts=[]
    for samples in (g,a):
        token=samples.reshape(n,5,4,3)
        parts.extend([token[:,:,-1],token.mean(2)])
    return np.concatenate([*parts,(ts[:,3::4]+.01)[:,:,None],np.repeat(cues[:,None,:],5,axis=1)],axis=2)
def inputs(raw,model):
    x=np.clip((raw-np.asarray(model['x_mean']))/np.asarray(model['x_scale']),-10,10)
    mode=model['mode']
    if mode in ('accel_task','task'):x[:,:,:6]=0
    if mode in ('gyro_task','task'):x[:,:,6:12]=0
    if mode=='sensors':x[:,:,15:]=0
    return x
def predict(raw,model):
    x=inputs(raw,model);p={k:np.asarray(v) for k,v in model['parameters'].items()}
    if model['family']=='ridge':
        output=x.reshape(len(x),-1)@p['coefficient']+p['bias']
    else:
        def dense(a,k):return a@p[k+'.weight'].T+p[k+'.bias']
        def norm(a,k):return (a-a.mean(-1,keepdims=True))/np.sqrt(a.var(-1,keepdims=True)+1e-5)*p[k+'.weight']+p[k+'.bias']
        x=dense(x,'embed')+p['position']
        q,k,v=[t.reshape(-1,5,2,8).transpose(0,2,1,3) for t in np.split(dense(x,'qkv'),3,axis=-1)]
        logits=(q@k.swapaxes(-1,-2))/(8**.5)
        prob=np.exp(logits-logits.max(-1,keepdims=True));prob/=prob.sum(-1,keepdims=True)
        x=norm(x+dense((prob@v).transpose(0,2,1,3).reshape(-1,5,16),'project'),'attention_norm')
        x=norm(x+dense(np.maximum(dense(x,'expand'),0),'reduce'),'final_norm')
        output=dense(x[:,-1],'out')
    return output*np.asarray(model['y_scale'])+np.asarray(model['y_mean'])
if __name__=='__main__':
    import argparse
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('weights',type=Path);cli.add_argument('history',type=Path);args=cli.parse_args()
    h=json.loads(args.history.read_bytes());w=json.loads(args.weights.read_bytes())
    x=make_tokens([h['gyro']],[h['accel']],[h['time']],[h['hand']],[h['target']])
    y=predict(x,w)[0]
    out={'mean_gyro_rad_s':y[:3].tolist()}
    if w['mode']!='gyro_loss':out['mean_acceleration_m_s2_including_gravity']=y[3:].tolist()
    print(json.dumps(out))
