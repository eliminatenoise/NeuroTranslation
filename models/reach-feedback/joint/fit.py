"""Fit a matched parallel or recurrent path/count decoder from recorded histories."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from portable import features,standard,predict,MODES,SEEDS

class JointFit(nn.Module):
    def __init__(self,mode,rate):
        super().__init__();self.mode=mode
        self.embed=nn.Linear(42,16);self.past_pos=nn.Parameter(torch.zeros(20,16))
        self.future_pos=nn.Parameter(torch.empty(10,16));nn.init.normal_(self.future_pos,std=.05)
        self.qkv=nn.Linear(16,48);self.project=nn.Linear(16,16);self.attn_norm=nn.LayerNorm(16)
        self.expand=nn.Linear(16,32);self.reduce=nn.Linear(32,16);self.ff_norm=nn.LayerNorm(16)
        self.decode=nn.GRUCell(24,16);self.motion=nn.Linear(16,8);self.counts=nn.Linear(16,23)
        with torch.no_grad():self.counts.bias.copy_(torch.from_numpy(np.log(np.expm1(np.maximum(rate,.0001)))).float())
    def forward(self,x):
        h=self.embed(x)+self.past_pos
        q,k,v=[a.reshape(-1,20,2,8).transpose(1,2) for a in self.qkv(h).chunk(3,dim=-1)]
        weights=torch.softmax((q@k.transpose(-2,-1))/(8**.5),dim=-1)
        h=self.attn_norm(h+self.project((weights@v).transpose(1,2).reshape(-1,20,16)))
        ctx=self.ff_norm(h+self.reduce(torch.relu(self.expand(h))))[:,-1]
        zero=ctx.new_zeros(len(x),8)
        if self.mode.startswith('parallel'):
            feed=torch.cat([ctx[:,None,:]+self.future_pos,zero[:,None].expand(-1,10,-1)],dim=-1)
            state=self.decode(feed.reshape(-1,24),ctx[:,None,:].expand(-1,10,-1).reshape(-1,16)).reshape(-1,10,16)
            return self.motion(state),F.softplus(self.counts(state))+1e-6
        state=ctx;previous=zero;trajectory=[];rates=[]
        for j in range(10):
            feedback=previous if self.mode=='rollout' else zero
            state=self.decode(torch.cat([ctx+self.future_pos[j],feedback],dim=-1),state)
            previous=self.motion(state);trajectory.append(previous)
            rates.append(F.softplus(self.counts(state))+1e-6)
        return torch.stack(trajectory,dim=1),torch.stack(rates,dim=1)

def write(p,value):
    p.write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def group_weights(ids):
    groups,idx,n=np.unique(ids,return_inverse=True,return_counts=True)
    return 1/(len(groups)*n[idx])

def fit(cli):
    torch.set_num_threads(cli.threads);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);torch.set_float32_matmul_precision('highest')
    with np.load(cli.source,allow_pickle=False) as d:
        if np.any(d['workspace']!=1) or np.any(d['fold']<0):raise ValueError('Requires workspace 1 training originals')
        keep=d['fold']>0;guide=d['unit_guide'].tolist()
        raw=features(d['pose'][keep],d['spikes'][keep],d['cue'][keep]);ym=d['movement'][keep].astype(float);yc=d['delayed'][keep].astype(float)
        w=group_weights(d['original'][keep])
    n=len(raw);avg=w@raw.mean(1);sd=np.sqrt(w@((raw-avg)**2).mean(1))
    ms=np.maximum(np.sqrt(w@(ym**2).mean(1)),1e-6);initial=w@yc.mean(1)
    common=dict(format='reach-rollout-v1',unit_guide=guide,x_mean=avg.tolist(),x_scale=np.where(sd>1e-8,sd,1).tolist(),motion_scale=ms.tolist())
    tensor=lambda a:torch.as_tensor(a,dtype=torch.float32,device=cli.device)
    x=tensor(standard(raw,common));y=tensor(ym/ms);z=tensor(yc);weights=tensor(n*w)
    out=cli.out;out.mkdir(exist_ok=True,parents=True)
    if not cli.bench and (out/'lock.json').is_file():raise ValueError('Destination already fitted')
    hashes={};results={}
    for mode in (['rollout'] if cli.bench else MODES):
        for seed in ([17] if cli.bench else SEEDS):
            torch.manual_seed(seed);rng=np.random.default_rng(seed);net=JointFit(mode,initial).to(cli.device)
            opt=torch.optim.AdamW(net.parameters(),lr=.0015,weight_decay=.001,foreach=False,fused=False)
            then=time.perf_counter();count=0
            for _ in range(32):
                arr=rng.permutation(n)
                for start in range(0,n,64):
                    idx=arr[start:start+64];opt.zero_grad()
                    path,rate=net(x[idx])
                    motion=(path-y[idx]).square().mean((1,2));neural=(rate-z[idx]*torch.log(rate)).mean((1,2))
                    value=neural if mode=='parallel_count' else (motion if mode=='parallel_motor' else motion+neural)
                    (value*weights[idx]).sum().div(64).backward()
                    torch.nn.utils.clip_grad_norm_(net.parameters(),1);opt.step();count+=1
                    if cli.bench and count>=20:break
                if cli.bench and count>=20:break
            net.eval()
            with torch.no_grad():path,rate=net(x)
            native_m=path.cpu().numpy()*ms;native_n=rate.cpu().numpy()
            model={**common,'mode':mode,'seed':seed,'parameters':{k:v.detach().cpu().tolist() for k,v in net.state_dict().items()}}
            a,b=predict(raw,model);dm=float(np.max(abs(a-native_m)));dn=float(np.max(abs(b-native_n)))
            if max(dm,dn)>2e-5:raise ValueError((mode,dm,dn))
            if cli.bench:
                np.savez(out/'probe.npz',motion=native_m[:64],counts=native_n[:64]);return
            p=out/f'{mode}-{seed}.json';write(p,model);hashes[p.name]=sha(p)
            results[p.name]={'updates':count,'parameters':sum(v.numel() for v in net.parameters()),'seconds':time.perf_counter()-then,'max_motion_port_difference':dm,'max_count_port_difference':dn}
    write(out/'lock.json',{'models':hashes,'fit_input_sha256':sha(cli.source),'methods':{n:sha(Path(__file__).with_name(n)) for n in ('PROTOCOL.md','portable.py','fit.py')},'rows':n,'device':cli.device,'threads':cli.threads,'fits':results})
if __name__=='__main__':
    cmd=argparse.ArgumentParser(description=__doc__);cmd.add_argument('source',type=Path);cmd.add_argument('out',type=Path);cmd.add_argument('--device',default='cpu');cmd.add_argument('--threads',type=int,default=1);cmd.add_argument('--bench',action='store_true');fit(cmd.parse_args())
