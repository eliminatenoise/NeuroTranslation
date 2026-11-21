"""Fit one shared inertial model per condition and seed, and weighted ridge comparisons."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from portable import inputs,make_tokens,predict,MODES,SEEDS

class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed=nn.Linear(33,16);self.position=nn.Parameter(torch.zeros(5,16))
        self.qkv=nn.Linear(16,48);self.project=nn.Linear(16,16);self.attention_norm=nn.LayerNorm(16)
        self.expand=nn.Linear(16,32);self.reduce=nn.Linear(32,16);self.final_norm=nn.LayerNorm(16);self.out=nn.Linear(16,6)
    def forward(self,x):
        x=self.embed(x)+self.position
        q,k,v=[z.reshape(-1,5,2,8).transpose(1,2) for z in self.qkv(x).chunk(3,dim=-1)]
        a=torch.softmax(q@k.transpose(-2,-1)/(8**.5),dim=-1)
        x=self.attention_norm(x+self.project((a@v).transpose(1,2).reshape(-1,5,16)))
        return self.out(self.final_norm(x+self.reduce(torch.relu(self.expand(x))))[:,-1])

def balanced(person,hand,trial):
    lookup={};counts={}
    for key in zip(person,hand,trial):lookup[key]=lookup.get(key,0)+1
    for p,_,_ in lookup:counts[p]=counts.get(p,0)+1
    return np.array([1/(len(counts)*counts[p]*lookup[p,h,t]) for p,h,t in zip(person,hand,trial)])
def write(p,obj):p.write_text(json.dumps(obj,separators=(',',':'),allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):
    torch.set_num_threads(args.threads);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);torch.set_float32_matmul_precision('highest')
    with np.load(args.data,allow_pickle=False) as d:
        person=d['participant'];hand=d['hand'];trial=d['trial']
        if not np.isin(d['repetition'],[2,3,4,5]).all():raise ValueError('Only the earlier fit repetitions may enter training')
        raw=make_tokens(d['gyro'],d['accel'],d['time'],hand,d['target'])
        y=np.concatenate([d['y_gyro'],d['y_accel']],axis=1)
    if not np.isfinite(y).all():raise ValueError('Nonfinite outcome')
    n=len(y);w=balanced(person,hand,trial)
    xm=np.zeros(33);xs=np.ones(33)
    xm[:13]=w@raw[:,:,:13].mean(1)
    sd=np.sqrt(w@((raw[:,:,:13]-xm[:13])**2).mean(1));xs[:13]=np.where(sd>1e-6,sd,1)
    ym=w@y;v=w@((y-ym)**2)
    ys=np.repeat(np.maximum(np.sqrt(v.reshape(2,3).mean(-1)),.0001),3);yn=(y-ym)/ys
    out=args.out;out.mkdir(exist_ok=True,parents=True)
    if not args.bench and (out/'weights-lock.json').exists():raise ValueError('Already fitted')
    wt=torch.tensor(w*n,dtype=torch.float32,device=args.device);yt=torch.tensor(yn,dtype=torch.float32,device=args.device)
    files={};fits={}
    for mode in (['full'] if args.bench else MODES):
        info=dict(format='ruhr-inertial-v1',mode=mode,x_mean=xm.tolist(),x_scale=xs.tolist(),y_mean=ym.tolist(),y_scale=ys.tolist())
        x=inputs(raw,info);flat=x.reshape(n,-1)
        if mode!='gyro_loss' and not args.bench:
            mx=w@flat;my=w@yn;xc=flat-mx
            coef=np.linalg.solve((xc.T*w)@xc+.01*np.eye(xc.shape[1]),(xc.T*w)@(yn-my))
            model={**info,'family':'ridge','parameters':{'coefficient':coef.tolist(),'bias':(my-mx@coef).tolist()}}
            dest=out/(mode+'-ridge.json');write(dest,model);files[dest.name]=sha(dest)
        xx=torch.tensor(x,dtype=torch.float32,device=args.device)
        for seed in ([17] if args.bench else SEEDS):
            tick=time.perf_counter();torch.manual_seed(seed);rng=np.random.default_rng(seed)
            net=Encoder().to(args.device)
            opt=torch.optim.AdamW(net.parameters(),lr=.0015,weight_decay=.001,foreach=False,fused=False)
            limit=3 if mode=='gyro_loss' else 6
            updates=0
            for epoch in range(20):
                order=rng.permutation(n)
                for j in range(0,n,256):
                    ix=order[j:j+256];opt.zero_grad()
                    err=(net(xx[ix])[:,:limit]-yt[ix,:limit]).square().mean(-1)
                    loss=(err*wt[ix]).sum()/256;loss.backward()
                    torch.nn.utils.clip_grad_norm_(net.parameters(),1);opt.step()
                    updates+=1
                    if args.bench and updates>=32:break
                if args.bench and updates>=32:break
            net.eval()
            with torch.no_grad():native=net(xx).cpu().numpy()*ys+ym
            m={**info,'family':'transformer','seed':seed,'parameters':{k:v.detach().cpu().tolist() for k,v in net.state_dict().items()}}
            comparisons=[]
            for j in range(0,n,512):comparisons.append(predict(raw[j:j+512],m))
            diff=np.max(abs(np.concatenate(comparisons)-native),axis=0)
            assert np.max(diff)<.0005,diff
            if args.bench:np.save(out/'probe.npy',native[:64]);return
            f=out/f'{mode}-{seed}.json';write(f,m);files[f.name]=sha(f)
            fits[f.name]={'steps':updates,'seconds':time.perf_counter()-tick,'native_numpy_max_abs':diff.tolist()}
    write(out/'weights-lock.json',{'source_arrays_sha256':sha(args.data),'parameters_sha256':files,'fits':fits,'source_sha256':sha(Path(__file__)),'kernel_sha256':sha(Path(__file__).with_name('portable.py')),'n_windows':n,'n_people':len(np.unique(person)),'n_originals':len(set(zip(person,hand,trial))),'device':args.device,'threads':args.threads})
if __name__=='__main__':
    c=argparse.ArgumentParser(description=__doc__);c.add_argument('data',type=Path);c.add_argument('out',type=Path);c.add_argument('--threads',type=int,default=1);c.add_argument('--device',default='cpu');c.add_argument('--bench',action='store_true');run(c.parse_args())
