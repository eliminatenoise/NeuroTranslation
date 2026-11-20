"""Small causal temporal encoder using the project's shared forecast decoder, CPU only."""
import numpy as np
import torch
from torch import nn
from shared_decoder import ForecastDecoder
from wtrack import trial_weights

SEED = 27223
WIDTH = 16


def inputs(motion, clocks, spikes):
    return np.concatenate([motion,np.sqrt(spikes),
                           np.broadcast_to(clocks[:,None,:], (*motion.shape[:2],2))], axis=2)


def normalize_values(x, weight):
    center = np.average(x,axis=0,weights=weight)
    sd = np.sqrt(np.average((x-center)**2,axis=0,weights=weight))
    return center, np.where(sd < 1e-8, 1., sd)


class Temporal(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.embed = nn.Linear(channels, WIDTH)
        self.position = nn.Parameter(torch.randn(4,WIDTH)*.01)
        self.temporal = nn.TransformerEncoderLayer(WIDTH,2,32,0,activation="gelu",
                                                    batch_first=True,norm_first=True)
        self.decoder = ForecastDecoder(WIDTH,2,32,0,torch.float32)
        self.head = nn.Linear(WIDTH,2)
        self.register_buffer("causal", torch.triu(torch.ones(4,4,dtype=torch.bool),1))

    def forward(self, x):
        z = self.embed(x) + self.position
        memory = self.temporal(z,src_mask=self.causal)
        query = torch.full((len(x),1),.25,dtype=x.dtype)
        valid = torch.ones(x.shape[:2],dtype=torch.bool)
        return self.head(self.decoder(query,z[:,-1],memory,valid)[:,0])


def tensor(x):
    return torch.as_tensor(x, dtype=torch.float32)


def set_threads(n):
    torch.set_num_threads(n)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


def design(motion, clocks, spike, mode, norm):
    x = (inputs(motion,clocks,spike)-norm["center"])/norm["sd"]
    if mode == "motion":
        x[:,:,5:-2] = 0.
    return tensor(x)


def fit(data, mode, epochs=48):
    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)
    w = trial_weights(data.trial)
    x = inputs(data.motion,data.clocks,data.spike)
    if mode == "motion":
        x[:,:,5:-2] = 0.
    center, sd = normalize_values(x.reshape(-1,x.shape[2]),np.repeat(w/4,4))
    change = data.y-data.anchor
    ycenter, ysd = normalize_values(change,w)
    norm = dict(center=center,sd=sd,ycenter=ycenter,ysd=ysd)
    net = Temporal(x.shape[-1])
    xx = design(data.motion,data.clocks,data.spike,mode,norm)
    yy, ww = tensor((change-ycenter)/ysd), tensor(w*len(w))
    optim = torch.optim.AdamW(net.parameters(),lr=.003,weight_decay=.01)
    losses = []
    for _ in range(epochs):
        order = rng.permutation(len(yy))
        epoch = 0.
        for batch in range(0,len(yy),64):
            ix = order[batch:batch+64]
            optim.zero_grad()
            pred = net(xx[ix])
            loss = (ww[ix]*(pred-yy[ix]).square().mean(dim=1)).mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(),1.)
            optim.step()
            epoch += float(loss.detach())*len(ix)/len(yy)
        losses.append(epoch)
    state = {"state."+k:v.detach().numpy() for k,v in net.state_dict().items()}
    return dict(**norm,**state,mode=np.array(mode)),losses


@torch.inference_mode()
def predict(fit, motion, clocks, spike):
    mode = str(fit["mode"])
    xx = design(motion,clocks,spike,mode,fit)
    net = Temporal(xx.shape[-1])
    state = {k[6:]:torch.as_tensor(np.array(v,copy=True)) for k,v in fit.items() if k.startswith("state.")}
    net.load_state_dict(state)
    net.eval()
    chunks = [net(xx[i:i+64]).numpy() for i in range(0,len(xx),64)]
    return np.vstack(chunks)*fit["ysd"]+fit["ycenter"]+motion[:,-1,:2]
