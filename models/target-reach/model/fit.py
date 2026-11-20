"""Fit the preregistered three temporal and linear input comparisons using development people only."""
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from kernel import features,tokens,predict,MODES,SEEDS

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed=nn.Linear(27,16)
        self.pos=nn.Parameter(torch.zeros(5,16))
        self.qkv=nn.Linear(16,48);self.project=nn.Linear(16,16);self.ln1=nn.LayerNorm(16)
        self.expand=nn.Linear(16,32);self.reduce=nn.Linear(32,16);self.ln2=nn.LayerNorm(16)
        self.readout=nn.Linear(16,9)
    def forward(self,x):
        h=self.embed(x)+self.pos
        q,k,v=[t.reshape(-1,5,2,8).transpose(1,2) for t in self.qkv(h).chunk(3,dim=-1)]
        a=torch.softmax(q@k.transpose(-2,-1)/(8**.5),dim=-1)
        h=self.ln1(h+self.project((a@v).transpose(1,2).reshape(-1,5,16)))
        return self.readout(self.ln2(h+self.reduce(torch.relu(self.expand(h))))[:,-1]).reshape(-1,3,3)

def equal_people(person,valid):
    w=np.zeros((len(person),3))
    for h in range(3):
        available=np.unique(person[valid[:,h]])
        if not len(available):raise ValueError('An entire training horizon is unavailable')
        for subject in available:
            mask=(person==subject)&valid[:,h];w[mask,h]=1/(mask.sum()*len(available))
    return w

def write(p,obj):
    p.write_text(json.dumps(obj,separators=(',',':'),allow_nan=False)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):
    torch.set_num_threads(args.threads);torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True);torch.set_float32_matmul_precision('highest')
    with np.load(args.data,allow_pickle=False) as data:
        person=data['participant'];hand=data['hand'].astype(str);target=data['target'];y=np.asarray(data['y'],float);valid=np.asarray(data['valid'],bool)
        raw=tokens(data['xyz'],data['time'],hand,target)
        if not args.bench and (set(map(int,person)) & {4,8,12,16,20,24,28}):raise ValueError('Reserved person in fit')
    if not np.isfinite(y[valid]).all() or y.shape!=(len(person),3,3):raise ValueError('Invalid measured outcome')
    w=equal_people(person,valid);perperson=equal_people(person,np.ones_like(valid,bool))[:,0]
    mean=np.zeros(27);scale=np.ones(27)
    mean[:7]=np.sum(perperson[:,None]*raw[:,:,:7].mean(1),axis=0)
    sd=np.sqrt(np.sum(perperson[:,None]*((raw[:,:,:7]-mean[:7])**2).mean(1),axis=0))
    scale[:7]=np.where(sd>1e-8,sd,1)
    filled=np.where(valid[:,:,None],y,0.)
    span=max(float(np.sqrt(np.sum((filled**2).mean(-1)*w)/3)),1e-5)
    out=args.out;out.mkdir(exist_ok=True,parents=True)
    if not args.bench and (out/'weights-lock.json').exists():raise ValueError('Destination already fitted')
    torch_y=torch.tensor(filled/span,dtype=torch.float32,device=args.device)
    torch_w=torch.tensor(w*len(person),dtype=torch.float32,device=args.device)
    stats={};files={}
    for mode in (('full',) if args.bench else MODES):
        info={'format':'target-reach-v1','mode':mode,'mean':mean.tolist(),'scale':scale.tolist(),'target_scale':span}
        x=features(raw,info);flat=x.reshape(len(person),-1)
        if not args.bench:
            coef=[];bias=[]
            for h in range(3):
                weights=w[:,h];xm=weights@flat;ym=weights@filled[:,h]/span
                centered=flat-xm
                cov=(centered.T*weights)@centered+.01*np.eye(flat.shape[1])
                b=np.linalg.solve(cov,(centered.T*weights)@(filled[:,h]/span-ym))
                coef.append(b);bias.append(ym-xm@b)
            m={**info,'family':'ridge','parameters':{'coefficient':np.concatenate(coef,axis=1).tolist(),'bias':np.concatenate(bias).tolist()}}
            dest=out/(mode+'-ridge.json');write(dest,m);files[dest.name]=digest(dest)
        xx=torch.tensor(x,dtype=torch.float32,device=args.device)
        for seed in ((17,) if args.bench else SEEDS):
            torch.manual_seed(seed);net=Net().to(args.device);rng=np.random.default_rng(seed)
            opt=torch.optim.AdamW(net.parameters(),lr=.0015,weight_decay=.001,foreach=False,fused=False)
            nupdate=0;start=time.perf_counter()
            for epoch in range(40):
                order=rng.permutation(len(person))
                for begin in range(0,len(order),64):
                    ids=order[begin:begin+64]
                    opt.zero_grad();err=(net(xx[ids])-torch_y[ids]).square().mean(-1)
                    loss=(err*torch_w[ids]).sum()/(64*3)
                    loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),1.0);opt.step()
                    nupdate+=1
                    if args.bench and nupdate>=30:break
                if args.bench and nupdate>=30:break
            net.eval()
            with torch.no_grad():native=net(xx).cpu().numpy()*span
            m={**info,'family':'transformer','seed':seed,'parameters':{k:v.detach().cpu().tolist() for k,v in net.state_dict().items()}}
            portable=predict(raw,m);difference=float(np.max(abs(native-portable)))
            if difference>2e-5:raise ValueError(f'Native/portable difference {difference} m')
            if args.bench:
                np.save(out/'probes.npy',native[:32]);return
            dest=out/f'{mode}-{seed}.json';write(dest,m);files[dest.name]=digest(dest)
            stats[dest.name]={'updates':nupdate,'seconds':time.perf_counter()-start,'max_portable_difference_m':difference}
    write(out/'weights-lock.json',{'data':digest(args.data),'source':digest(Path(__file__)),'portable':digest(Path(__file__).with_name('kernel.py')),'parameters':files,'fits':stats,'rows':len(raw),'participants':len(np.unique(person)),'target_scale_m':span,'device':args.device,'threads':args.threads})
if __name__=='__main__':
    c=argparse.ArgumentParser(description=__doc__);c.add_argument('data',type=Path);c.add_argument('out',type=Path);c.add_argument('--device',default='cpu');c.add_argument('--threads',type=int,default=1);c.add_argument('--bench',action='store_true');run(c.parse_args())
