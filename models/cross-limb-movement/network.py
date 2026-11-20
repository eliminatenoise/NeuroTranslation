"""Trainable named-muscle set encoder and segment-conditioned temporal Transformer."""
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from interface import MUSCLES

WIDTH = 16
CHANNEL_WIDTH = 8
MATRIX_FIELDS = ('patch_rms','patch_xyz_mm','age_s','past_rms')
INPUT_KEYS = ('domain','session','direction','muscle_mask', *MATRIX_FIELDS)
INPUT_SHAPES = dict(muscle_mask=(13,), patch_rms=(20,13), patch_xyz_mm=(20,3), age_s=(20,), past_rms=(13,))


def check_event(event):
    d, s, cue = (event[key] for key in ('domain','session','direction'))
    if d not in (0,1) or type(d) is bool or not isinstance(s,(int,np.integer)) or type(s) is bool:
        raise ValueError('Invalid study or session')
    if (d==0 and (s not in (0,1) or cue not in (-1,1))) or (d==1 and (s<1 or cue!=0)):
        raise ValueError('Context does not belong to this study')
    mask = np.asarray(event['muscle_mask'])
    if mask.dtype != np.bool_ or mask.shape!=(13,) or (d==0 and (not mask[:8].all() or mask[8:].any())) or (d==1 and (mask[:8].any() or mask.sum()<3)):
        raise ValueError('Invalid named muscle availability')
    for key, shape in INPUT_SHAPES.items():
        if key=='muscle_mask': continue
        a = np.asarray(event[key],dtype=float)
        if a.shape!=shape or not np.isfinite(a).all():
            raise ValueError('Invalid dimensions or nonfinite value in '+key)
        if key in ('patch_rms','past_rms') and ((a<0).any() or (a[...,~mask]!=0).any()):
            raise ValueError('Nonnegative native RMS and zero masked placeholders required')
    age = np.asarray(event['age_s'])
    if (age < -1e-8).any() or (age > (1/500 if d else 1/256)+1e-8).any() or abs(age[-1])>1e-7:
        raise ValueError('Invalid sample age')
    if np.max(np.abs(event['patch_xyz_mm'][-1]))>1e-4:
        raise ValueError('Final marker knot must be relative to itself')


def fit_scales(data,ids):
    amp = np.ones((2,13))
    xyz = np.ones(2)
    for d in (0,1):
        subset = ids[data['domain'][ids]==d]
        if not len(subset): continue
        for j in range(13):
            good = subset[data['muscle_mask'][subset,j]]
            if len(good):
                amp[d,j] = max(1e-8,float(np.median(data['past_rms'][good,j])))
        xyz[d] = max(.1,float(np.median(np.linalg.norm(data['patch_xyz_mm'][subset],axis=-1).mean(1))))
    return dict(amp=amp.tolist(),xyz=xyz.tolist())


class SharedNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.names = nn.Embedding(13,CHANNEL_WIDTH)
        self.slope = nn.Parameter(torch.randn(CHANNEL_WIDTH)*.2)
        self.patch = nn.Linear(CHANNEL_WIDTH+7,WIDTH)
        self.time = nn.Embedding(20,WIDTH)
        self.segment = nn.Embedding(2,WIDTH)
        self.qkv = nn.Linear(WIDTH,WIDTH*3)
        self.attn_out = nn.Linear(WIDTH,WIDTH)
        self.norm1 = nn.LayerNorm(WIDTH)
        self.ff1 = nn.Linear(WIDTH,32)
        self.ff2 = nn.Linear(32,WIDTH)
        self.norm2 = nn.LayerNorm(WIDTH)
        self.rms_state = nn.Linear(WIDTH,CHANNEL_WIDTH)
        self.rms_out = nn.Linear(CHANNEL_WIDTH,1)
        self.path_state = nn.Linear(WIDTH,WIDTH)
        self.path_time = nn.Embedding(32,WIDTH)
        self.path_out = nn.Linear(WIDTH,3)
        for p in (self.time,self.segment,self.path_time,self.names):
            nn.init.normal_(p.weight,std=.14)
        for layer in (self.rms_out,self.path_out):
            nn.init.normal_(layer.weight,std=.015)
            nn.init.zeros_(layer.bias)

    def forward(self, batch):
        d, mask, r, pose, age, past, pose_context, direction = batch
        amplitude = torch.log1p(r).unsqueeze(-1)
        named = F.relu(self.names.weight + amplitude*self.slope)
        pooled = (named*mask[:,None,:,None]).sum(2)/mask.sum(1)[:,None,None]
        context = torch.stack((pose_context,direction,d.float()),dim=1)[:,None,:].expand(-1,20,-1)
        x = self.patch(torch.cat((pooled,pose,age.unsqueeze(-1)*500,context),dim=-1))
        x = x + self.time.weight + self.segment(d)[:,None,:]
        n = len(d)
        q,k,v = self.qkv(x).reshape(n,20,3,2,8).permute(2,0,3,1,4).unbind(0)
        score = torch.softmax(q@k.transpose(-2,-1)/8**.5,dim=-1)
        mixed = (score@v).transpose(1,2).reshape(n,20,WIDTH)
        x = self.norm1(x+self.attn_out(mixed))
        h = self.norm2(x+self.ff2(F.relu(self.ff1(x))))[:,-1]
        rmsh = F.relu(self.rms_state(h)[:,None,:] + self.names.weight)
        rms = (past+self.rms_out(rmsh).squeeze(-1)).clamp_min(0)*mask
        ph = F.relu(self.path_state(h)[:,None,:]+self.path_time.weight)
        u = torch.arange(1,33,device=d.device,dtype=pose.dtype)/32
        interval = 1/32 + age[:,-2]-age[:,-1]
        linear = (pose[:,-1]-pose[:,-2])*(.125/interval[:,None])
        path = u[None,:,None]*(linear[:,None,:]+self.path_out(ph))
        return rms,path


def tensors(data,scales,device='cpu',labels=True):
    d = np.asarray(data['domain'],dtype=np.int64)
    amp = np.array(scales['amp'],dtype=np.float32)[d]
    xyz = np.array(scales['xyz'],dtype=np.float32)[d]
    mask = np.asarray(data['muscle_mask'],dtype=bool)
    in_order = (d,mask, data['patch_rms']/amp[:,None,:],data['patch_xyz_mm']/xyz[:,None,None],
                data['age_s'], data['past_rms']/amp, np.where(d==0,data['session'],0),data['direction'])
    result = [torch.as_tensor(x,dtype=torch.long if j==0 else torch.float32,device=device)
              for j,x in enumerate(in_order)]
    if labels:
        result.extend((torch.as_tensor(data['future_rms']/amp,dtype=torch.float32,device=device),
                       torch.as_tensor(data['future_path_mm']/xyz[:,None,None],dtype=torch.float32,device=device)))
    return result


def export(model,scales):
    return dict(format='cross-limb-temporal-v1',muscles=MUSCLES,scales=scales,
                state={k:v.detach().cpu().tolist() for k,v in model.state_dict().items()})


def load_model(weights):
    if isinstance(weights,(str,Path)): weights=json.loads(Path(weights).read_text())
    if weights['format']!='cross-limb-temporal-v1' or weights['muscles']!=MUSCLES:
        raise ValueError('Unsupported model format or anatomy')
    model=SharedNet()
    model.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in weights['state'].items()})
    return model.eval(),weights['scales']


@torch.no_grad()
def predict_arrays(model,data,scales,step=256):
    device=next(model.parameters()).device
    r,p=[],[]
    for start in range(0,len(data['domain']),step):
        rows={k:v[start:start+step] for k,v in data.items() if k in INPUT_KEYS}
        batch=tensors(rows,scales,device,labels=False)
        rn,pn=model(batch)
        d=rows['domain']
        r.extend(rn.cpu().numpy()*np.asarray(scales['amp'])[d])
        p.extend(pn.cpu().numpy()*np.asarray(scales['xyz'])[d,None,None])
    return np.asarray(r),np.asarray(p)


def predict_event(weights,event):
    check_event(event)
    model,scales=load_model(weights)
    rows={k:np.asarray([event[k]]) for k in INPUT_KEYS}
    r,p=predict_arrays(model,rows,scales)
    return dict(rms=[float(x) if valid else None for x,valid in zip(r[0],event['muscle_mask'])],
                path_mm=p[0].tolist())


def save_json(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')


def fingerprint(path):
    digest=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''): digest.update(chunk)
    return digest.hexdigest()
