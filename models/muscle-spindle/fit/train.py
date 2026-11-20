"""Train or reproduce the predeclared prefix-held spindle count models. See PROTOCOL.json."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

SEEDS = (1641, 2718, 3917)
FOLDS = (0, 1, 4)
CHANNELS = ("force_mean","position_mean","force_backward_rate","position_backward_rate","spike_count")
MODES = {"history":(4,), "mechanics":(0,1,2,3), "all":(0,1,2,3,4), "force":(0,2), "position":(1,3)}
BATCH = 80
STEPS = 240
WIDTH = 16
HEADS = 2

def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1<<20), b""):
            digest.update(block)
    return digest.hexdigest()

class CountTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Linear(5, WIDTH)
        self.position = nn.Parameter(torch.empty(5, WIDTH))
        nn.init.normal_(self.position, std=.025)
        self.attn_norm = nn.LayerNorm(WIDTH)
        self.qkv = nn.Linear(WIDTH, WIDTH*3)
        self.proj = nn.Linear(WIDTH, WIDTH)
        self.ff_norm = nn.LayerNorm(WIDTH)
        self.expand = nn.Linear(WIDTH, WIDTH*2)
        self.reduce = nn.Linear(WIDTH*2, WIDTH)
        self.final_norm = nn.LayerNorm(WIDTH)
        self.readout = nn.Linear(WIDTH, 1)
    def forward(self, x):
        h = self.embed(x) + self.position
        batch, length, width = h.shape
        qkv = self.qkv(self.attn_norm(h)).reshape(batch,length,3,HEADS,width//HEADS)
        q, k, v = qkv.permute(2,0,3,1,4).unbind(0)
        a = torch.softmax((q @ k.transpose(-2,-1)) / (width//HEADS)**.5, dim=-1)
        h = h + self.proj((a @ v).transpose(1,2).reshape(batch,length,width))
        h = h + self.reduce(F.relu(self.expand(self.ff_norm(h))))
        return F.softplus(self.readout(self.final_norm(h[:, -1])).squeeze(-1)) + 1e-6

def load_data(path):
    with np.load(path, allow_pickle=False) as data:
        x = data["X"].astype("float64",copy=True)
        x[:,:,:2] = data["mech_mean"]
        info = {k: data[k] for k in ("y_count","afferent","prefix","trial","bin_index")}
    n = len(x)
    assert x.shape == (n,5,5) and np.isfinite(x).all()
    assert np.all(x[:,:,4] >= 0) and np.all(x[:,:,4] == np.floor(x[:,:,4]))
    y = info["y_count"]
    assert y.shape == (n,) and np.all(y>=0) and np.issubdtype(y.dtype,np.integer)
    assert set(np.unique(info["prefix"]).tolist()) == set(FOLDS)
    assert all(a.shape==(n,) for a in info.values())
    return x, info

def training_groups(info, held):
    ids = np.flatnonzero(info["prefix"] != held)
    groups = []
    for afferent in np.unique(info["afferent"][ids]):
        af = ids[info["afferent"][ids] == afferent]
        assert len(np.unique(info["prefix"][af])) == 1
        groups.append([af[info["trial"][af] == t] for t in np.unique(info["trial"][af])])
    return groups

def normalizer(x, groups):
    # Two passes avoid catastrophic cancellation of a large native-scale offset.
    def aggregate(center):
        def moment(rows):
            a = x[rows]
            return (a if center is None else np.square(a-center)).mean(axis=(0,1))
        return np.mean([np.mean([moment(rows) for rows in trials], axis=0) for trials in groups], axis=0)
    mean = aggregate(None)
    sd = np.maximum(aggregate(mean)**.5, 1e-6)
    assert np.isfinite(mean).all() and np.isfinite(sd).all()
    return mean, sd

def draw_plan(groups, seed, fold):
    rng = np.random.default_rng(seed + 10000*fold)
    members = rng.integers(len(groups), size=BATCH*STEPS)
    result = np.empty(len(members),dtype=np.int64)
    for member, trials in enumerate(groups):
        i = np.flatnonzero(members == member)
        chosen_trials = rng.integers(len(trials),size=len(i))
        for t, rows in enumerate(trials):
            j = i[chosen_trials == t]
            result[j] = rows[rng.integers(len(rows),size=len(j))]
    return result.reshape(STEPS,BATCH)

def earlier_rows(info):
    table = {}
    pairs = zip(info["afferent"].tolist(),info["trial"].tolist(),info["bin_index"].tolist())
    for i, key in enumerate(pairs):
        if key in table:
            raise ValueError("duplicate window identity")
        table[key] = i
    return np.asarray([table.get((a,t,b-5), -1) for a,t,b in table],dtype=np.int64)

def fit_one(inputs, y, plan, seed, mode, steps, device):
    torch.manual_seed(seed)
    model = CountTransformer().to(device)
    mask = torch.tensor([i in MODES[mode] for i in range(5)],dtype=torch.float32,device=device)
    opt = torch.optim.AdamW(model.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=.001,foreach=False,fused=False)
    for ids in plan[:steps]:
        rate = model(inputs[ids] * mask)
        loss = (rate - y[ids]*rate.log()).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        opt.step()
    if device == "cuda":
        torch.cuda.synchronize()
    return model.eval(), mask

@torch.no_grad()
def predict(model, inputs, ids, mask, shifted=None):
    rates = []
    for start in range(0,len(ids),512):
        chunk = ids[start:start+512]
        observed = inputs[chunk]
        if shifted is not None:
            observed = observed.clone()
            observed[:,:,:4] = inputs[shifted[chunk],:,:4]
        rates.append(model(observed*mask).cpu().numpy())
    rate = np.concatenate(rates) if len(rates) else np.empty(0,np.float32)
    assert np.all(np.isfinite(rate)) and np.all(rate > 0)
    return rate

def export(model, scale, fold, seed, mode):
    return {
        "format":"spindle-count-transformer-1", "channels":CHANNELS, "mode":mode,
        "active":MODES[mode], "held_prefix":fold, "seed":seed, "bin_seconds":.020,
        "width":WIDTH, "heads":HEADS, "normalizer":{"mean":scale[0].tolist(),"sd":scale[1].tolist(),"clip":10},
        "weights":{k:v.detach().cpu().tolist() for k,v in model.state_dict().items()}
    }

def run(args):
    start = time.monotonic()
    out = args.out
    out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Requested GPU is unavailable")
    x, info = load_data(args.data)
    earlier = earlier_rows(info)
    modes = list(MODES)
    is_full = args.task == "fit"
    folds = FOLDS if is_full else (0,)
    seeds = SEEDS if is_full else (1641,)
    branches = modes if is_full else ("all",)
    steps = 24 if args.task == "bench" else STEPS
    y = torch.as_tensor(info["y_count"],dtype=torch.float32,device=args.device)
    if is_full:
        rates = np.full((len(x),len(modes),len(SEEDS)),np.nan,np.float32)
        wrong = np.full((len(x),len(SEEDS)),np.nan,np.float32)
    details = []
    plans = {}
    for fold in folds:
        groups = training_groups(info,fold)
        held = np.flatnonzero(info["prefix"]==fold)
        shifted_ids = held[earlier[held]>=0]
        mean, sd = scale = normalizer(x,groups)
        inputs = torch.as_tensor(np.clip((x-mean)/sd,-10,10),dtype=torch.float32,device=args.device)
        for seed in seeds:
            plan = draw_plan(groups,seed,fold)
            plans[f"prefix{fold}-seed{seed}"] = plan
            assert np.all(info["prefix"][plan]!=fold)
            batches = torch.as_tensor(plan,device=args.device)
            for mode in branches:
                before = time.monotonic()
                model, mask = fit_one(inputs,y,batches,seed,mode,steps,args.device)
                elapsed = time.monotonic()-before
                details.append({"held_prefix":fold,"seed":seed,"mode":mode,"seconds":elapsed})
                if args.task == "bench":
                    probe = np.unique(plan[:4].ravel())
                    save_json(out/f"bench-{args.device}-{args.threads}.json",{
                      "seconds_fit":elapsed,"seconds_total":time.monotonic()-start,
                      "threads":torch.get_num_threads(),"interop":torch.get_num_interop_threads(),"device":args.device,
                      "backend": torch.cuda.get_device_name(0) if args.device=="cuda" else "cpu",
                      "torch":torch.__version__,"hip":torch.version.hip,"numpy":np.__version__,
                      "probe":predict(model,inputs,probe,mask).tolist()})
                    return
                checkpoint = export(model,scale,fold,seed,mode)
                name = f"prefix{fold}-seed{seed}-{mode}.json"
                if args.task == "refit":
                    save_json(out / name, checkpoint)
                    np.save(out/"refit.npy",predict(model,inputs,held,mask))
                    return
                checkpoints = out/"checkpoints"
                checkpoints.mkdir(exist_ok=True)
                save_json(checkpoints/name,checkpoint)
                si = SEEDS.index(seed)
                rates[held,modes.index(mode),si] = predict(model,inputs,held,mask)
                if mode == "all":
                    wrong[shifted_ids,si] = predict(model,inputs,shifted_ids,mask,earlier)
    assert np.all(np.isfinite(rates)) and np.array_equal(np.isfinite(wrong).all(axis=1),earlier>=0)
    np.savez_compressed(out/"oof.npz",**info, modes=np.array(modes), seeds=SEEDS, rate=rates,
                        wrong_mechanics=wrong, earlier_row=earlier, available_wrong=earlier>=0)
    np.savez_compressed(out/"train-row-samples.npz",**plans)
    save_json(out/"fit-run.json",{"seconds":time.monotonic()-start,"fits":details,"data_sha256":sha256(args.data),
                                  "params_per_fit":sum(p.numel() for p in model.parameters()),
                                  "device":args.device,"threads":args.threads,"interop":torch.get_num_interop_threads(),
                                  "torch":torch.__version__,"numpy":np.__version__})

if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("task",choices=("bench","fit","refit"))
    p.add_argument("--data",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--device",choices=("cpu","cuda"),default="cpu")
    p.add_argument("--threads",type=int,default=1)
    run(p.parse_args())
