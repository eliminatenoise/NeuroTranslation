"""Run the joint movement and delayed-count forecast with NumPy only."""
from pathlib import Path
import argparse,json
import numpy as np
MODES=('parallel','recurrent','rollout','parallel_motor','parallel_count')
SEEDS=(17,41,73)
def features(pose,spikes,cue):
    pose=np.asarray(pose,dtype=float);spikes=np.asarray(spikes,dtype=float);cue=np.asarray(cue,dtype=float)
    n=len(pose)
    if pose.shape!=(n,20,8) or spikes.shape!=(n,20,23) or cue.shape!=(n,20,3): raise ValueError('Expected twenty native rows, eight position, 23 count and three cue columns')
    if not all(np.isfinite(v).all() for v in (pose,spikes,cue)) or (spikes<0).any() or (spikes!=np.floor(spikes)).any():raise ValueError('Invalid history')
    return np.concatenate([pose,np.diff(pose,axis=1,prepend=pose[:,:1]),np.log1p(spikes),cue],axis=2)
def standard(raw,m):return np.clip((raw-np.asarray(m['x_mean']))/m['x_scale'],-8,8)
def predict(raw,m):
    if m['format']!='reach-rollout-v1' or m['mode'] not in MODES:raise ValueError('Unknown fit')
    p={k:np.asarray(v) for k,v in m['parameters'].items()}
    def dense(x,n):return x@p[n+'.weight'].T+p[n+'.bias']
    def norm(x,n):return (x-x.mean(-1,keepdims=True))/np.sqrt(x.var(-1,keepdims=True)+1e-5)*p[n+'.weight']+p[n+'.bias']
    x=dense(standard(raw,m),'embed')+p['past_pos']
    q,k,v=[u.reshape(-1,20,2,8).transpose(0,2,1,3) for u in np.split(dense(x,'qkv'),3,axis=-1)]
    z=(q@k.swapaxes(-1,-2))/np.sqrt(8);a=np.exp(z-z.max(-1,keepdims=True));a/=a.sum(-1,keepdims=True)
    x=norm(x+dense((a@v).transpose(0,2,1,3).reshape(-1,20,16),'project'),'attn_norm')
    context=norm(x+dense(np.maximum(dense(x,'expand'),0),'reduce'),'ff_norm')[:,-1]
    hidden=context;pos=np.zeros((len(context),8));mout=[];cout=[]
    sigmoid=lambda t: 1/(1+np.exp(-np.clip(t,-50,50)))
    for j in range(10):
        state=hidden if m['mode'] in ('rollout','recurrent') else context
        previous=pos if m['mode']=='rollout' else np.zeros_like(pos)
        feed=np.concatenate([context+p['future_pos'][j],previous],axis=1)
        ir,iz,inn=np.split(feed@p['decode.weight_ih'].T+p['decode.bias_ih'],3,axis=-1)
        hr,hz,hn=np.split(state@p['decode.weight_hh'].T+p['decode.bias_hh'],3,axis=-1)
        reset=sigmoid(ir+hr);update=sigmoid(iz+hz);new=np.tanh(inn+reset*hn)
        hidden=(1-update)*new+update*state
        pos=dense(hidden,'motion');mout.append(pos*m['motion_scale'])
        cout.append(np.logaddexp(0,dense(hidden,'counts'))+1e-6)
    return np.stack(mout,axis=1),np.stack(cout,axis=1)
if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('weights',type=Path);cli.add_argument('history',type=Path);args=cli.parse_args()
    h=json.loads(args.history.read_bytes());m=json.loads(args.weights.read_bytes())
    if h['unit_guide']!=m['unit_guide']:raise ValueError('Use declared channel and sort order')
    motor,count=predict(features([h['pose']],[h['spikes']],[h['cue']]),m);result={}
    if m['mode']!='parallel_count':result['movement_next_ten_rows_native']=motor[0].tolist()
    if m['mode']!='parallel_motor':result['expected_counts_following_ten_bins']=count[0].tolist()
    print(json.dumps(result))
