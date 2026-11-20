"""Fit the fixed 26-contact models on the hash-locked September 12 training rows."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from predict import CONTACTS, FIELDS, FORMAT, MODES, SEEDS, forward, mask, read_weights, stack_inputs

BATCH, EPOCHS = 128, 24
TRAIN_SHA = "3c5673f44c6f7ed164918d7f028e72c6acd3196a56137be45856d3f168b0d2e9"
HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,allow_nan=False,separators=(",",":"))+"\n")


def configure(threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")


class Transformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Linear(40,16)
        self.position = nn.Parameter(torch.empty(5,16))
        nn.init.normal_(self.position,std=.025)
        self.attn_norm = nn.LayerNorm(16)
        self.qkv = nn.Linear(16,48)
        self.project = nn.Linear(16,16)
        self.ff_norm = nn.LayerNorm(16)
        self.expand = nn.Linear(16,32)
        self.reduce = nn.Linear(32,16)
        self.final_norm = nn.LayerNorm(16)
        self.readout = nn.Linear(16,26)

    def forward(self,x):
        h = self.embed(x) + self.position
        q,k,v = self.qkv(self.attn_norm(h)).reshape(-1,5,3,2,8).permute(2,0,3,1,4).unbind(0)
        a = torch.softmax((q @ k.transpose(-1,-2))/(8**.5),dim=-1)
        h = h + self.project((a @ v).transpose(1,2).reshape(-1,5,16))
        h = h + self.reduce(torch.relu(self.expand(self.ff_norm(h))))
        return F.softplus(self.readout(self.final_norm(h[:,-1])))+1e-6


def load_train(path):
    if sha(path)!=TRAIN_SHA:
        raise ValueError("unrecognized training source")
    with np.load(path,allow_pickle=False) as d:
        raw = stack_inputs(d)
        y = d["target_count_100ms"].astype(np.float64)
        if not (y.shape==(1288,26) and np.all(y>=0) and np.all(y==np.floor(y))):
            raise ValueError("invalid count targets")
        trial = d["trial"]
        ids,inverse,counts = np.unique(trial,return_inverse=True,return_counts=True)
        w = 1.0/(len(ids)*counts[inverse])
        if len(ids)!=322 or not np.isclose(w.sum(),1):
            raise ValueError("training membership or sample weights differ")
        index = {k:d[k] for k in ("trial","k","offset","original_ids","contact_id")}
        example = {k:d[k][0].tolist() for k in FIELDS}
        example.update(contact_id=list(CONTACTS),trial=int(trial[0]),k=int(d["k"][0]),
                       offset=int(d["offset"][0]),measured_count_100ms=y[0].astype(int).tolist())
    xmean = np.einsum("i,ijk->k",w,raw)/5
    sd = np.sqrt(np.einsum("i,ijk->k",w,(raw-xmean)**2)/5)
    active = sd>=1e-6
    scale = np.where(active,sd,1.)
    x = np.clip((raw-xmean)/scale,-8,8)*active
    scaler = dict(x_mean=xmean.tolist(),x_scale=scale.tolist(),x_active=active.tolist())
    return raw,x,y,w,scaler,index,example


def train_transformer(x,y,w,order,seed,mode,ymean,device,limit=None):
    torch.manual_seed(seed)
    model = Transformer()
    with torch.no_grad():
        model.readout.bias.copy_(torch.tensor(np.log(np.expm1(np.maximum(ymean-1e-6,1e-6)))))
    initial = hashlib.sha256(b"".join(v.numpy().tobytes() for v in model.state_dict().values())).hexdigest()
    model.to(device)
    x = x*torch.as_tensor(mask(mode),device=device)
    opt = torch.optim.AdamW(model.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=.001,foreach=False,fused=False)
    initial_loss = None
    updates = 0
    for perm in order:
        for rows in perm.split(BATCH):
            mu = model(x[rows])
            loss = ((mu-y[rows]*mu.log()).mean(dim=1)*w[rows]).sum()/BATCH
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
            opt.step()
            if initial_loss is None:
                initial_loss = float(loss.detach().cpu())
            updates += 1
            if updates==limit:
                break
        if updates==limit:
            break
    model.eval()
    with torch.no_grad():
        pred = model(x if limit is None else x[:32]).cpu().numpy()
    return model, pred, dict(initial_state_sha256=initial,updates=updates,first_minibatch_nll=initial_loss,
                             parameter_count=sum(p.numel() for p in model.parameters()))


def fit_poisson(x,y,w,ymean,mode):
    x = torch.from_numpy((x*mask(mode)).reshape(-1,200))
    yt,wt = torch.from_numpy(y),torch.from_numpy(w)
    coef = nn.Parameter(torch.zeros((200,26),dtype=torch.float64))
    intercept = nn.Parameter(torch.tensor(np.log(np.maximum(ymean,1e-6))))
    opt = torch.optim.LBFGS((coef,intercept),lr=1,max_iter=300,max_eval=450,tolerance_grad=1e-8,
                           tolerance_change=1e-12,history_size=20,line_search_fn="strong_wolfe")
    def closure():
        opt.zero_grad()
        z = x @ coef + intercept
        loss = (wt[:,None]*(z.exp()-yt*z)).sum()+.015*coef.square().sum()
        loss.backward()
        return loss
    start_loss = float(opt.step(closure).detach())
    lbfgs_end = float(closure().detach())
    lbfgs_grad = max(float(v.grad.abs().max()) for v in (coef,intercept))
    # X' diag(w*mu) X plus the ridge curvature; the intercept is unpenalized.
    design = torch.column_stack((x,torch.ones(len(x),dtype=torch.float64)))
    penalty = torch.diag(torch.tensor([.03]*200+[0.],dtype=torch.float64))
    previous = lbfgs_end
    newton_trace = []
    for step in range(2):
        with torch.no_grad():
            mu = (x @ coef+intercept).exp()
            for j in range(26):
                h = design.T @ ((wt*mu[:,j])[:,None]*design)+penalty
                grad = torch.cat((coef.grad[:,j],intercept.grad[j:j+1]))
                delta = torch.linalg.solve(h,grad)
                coef[:,j].sub_(delta[:-1])
                intercept[j].sub_(delta[-1])
        final = float(closure().detach())
        grad = max(float(v.grad.abs().max()) for v in (coef,intercept))
        if not np.isfinite(final) or final>previous+1e-10:
            raise RuntimeError(f"Newton step {step} failed for {mode}: {previous} to {final}")
        newton_trace.append(dict(objective=final,max_abs_gradient=grad))
        previous = final
    if not np.isfinite(grad) or grad>1e-5:
        raise RuntimeError(f"regression fit failed for {mode}, gradient={grad}, objective={final}")
    with torch.no_grad():
        pred = (x @ coef+intercept).exp().numpy()
    info = dict(initial_penalized_nll_sum_contacts=start_loss,final_penalized_nll_sum_contacts=final,
                lbfgs_end=lbfgs_end,lbfgs_max_abs_gradient=lbfgs_grad,lbfgs_passed=lbfgs_grad<=1e-5,
                newton_trace=newton_trace,max_abs_gradient=grad,iterations=opt.state[coef]["n_iter"],
                closure_calls_in_solver=opt.state[coef]["func_evals"],parameter_count=coef.numel()+intercept.numel())
    return {"coef":coef.detach().tolist(),"intercept":intercept.detach().tolist()},pred,info


def run(args):
    configure(args.threads)
    if args.device=="cuda" and (not torch.cuda.is_available() or not torch.version.hip):
        raise RuntimeError("ROCm not available")
    if args.task=="fit" and (args.out/"weights-lock.json").exists():
        raise FileExistsError("frozen weights already present; reproduce in a fresh output folder")
    args.out.mkdir(exist_ok=True,parents=True)
    start = time.monotonic()
    raw,x,y,w,scaler,index,example = load_train(args.data)
    ym = w @ y
    xt,yt,wt = (torch.as_tensor(v,dtype=torch.float32,device=args.device) for v in (x,y,w*len(w)))
    bench = args.task=="bench"
    if args.retained:
        retained = {Path(line.split()[1]).stem:line.split()[0] for line in args.retained.read_text().splitlines()}
        if len(retained)!=18 or bench:
            raise ValueError("only a complete set of previously frozen Transformer weights can be reused")
    fixed = dict(format=FORMAT,contact_ids=list(CONTACTS),**scaler)
    checks,example_predictions = {},{}
    def record(key,mode,seed,params,p,info,elapsed):
        family = "transformer" if seed is not None else "poisson"
        path = args.out/"weights"/(key+".json")
        save(path,dict(**fixed,mode=mode,family=family,seed=seed,parameters=params))
        portable = forward(raw,read_weights(path))
        ok = np.allclose(p,portable,atol=(1e-4 if seed else 1e-10),rtol=(0 if seed else 1e-10))
        if not ok or not np.all(p>0):
            raise ValueError("portable/positive count check failed on training "+key)
        checks[key] = dict(**info,seconds=elapsed,train_nll=float(w @ (p-y*np.log(p)).mean(axis=1)),
                           max_native_numpy_error=float(np.max(np.abs(p-portable))))
        example_predictions[key] = p[0].tolist()
    if not bench:
        (args.out/"weights").mkdir(exist_ok=True)
        np.savez_compressed(args.out/"training-index.npz",**index,row_weights=w,training_mean_count=ym)
        save(args.out/"example.json",example)
    for seed in (SEEDS[:1] if bench else SEEDS):
        rng = np.random.default_rng(seed)
        perms = np.stack([rng.permutation(len(x)) for _ in range(EPOCHS)])
        if not bench:
            np.save(args.out/f"permutations-{seed}.npy",perms.astype(np.int32))
        order = torch.as_tensor(perms,device=args.device)
        for mode in (("all",) if bench else MODES):
            tick = time.monotonic()
            if args.retained:
                key = f"{mode}-{seed}"
                path = args.out/"weights"/(key+".json")
                if sha(path) != retained[key]:
                    raise ValueError("retained parameter file differs: "+key)
                portable_weights = read_weights(path)
                m = Transformer()
                m.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in portable_weights["parameters"].items()})
                with torch.no_grad():
                    p = m(xt.cpu()*torch.tensor(mask(mode))).numpy()
                py = forward(raw,portable_weights)
                if not np.allclose(p,py,atol=1e-4,rtol=0):
                    raise ValueError("retained model parity failed")
                torch.manual_seed(seed)
                initial = Transformer()
                with torch.no_grad():
                    initial.readout.bias.copy_(torch.tensor(np.log(np.expm1(np.maximum(ym-1e-6,1e-6)))))
                checks[key] = dict(retained=True,initial_state_sha256=hashlib.sha256(b"".join(
                    v.numpy().tobytes() for v in initial.state_dict().values())).hexdigest(),
                    parameter_count=sum(v.numel() for v in m.parameters()),updates=EPOCHS*((len(w)+BATCH-1)//BATCH),
                    train_nll=float(w @ (p-y*np.log(p)).mean(axis=1)),max_native_numpy_error=float(np.max(np.abs(p-py))))
                example_predictions[key] = p[0].tolist()
                continue
            m,p,info = train_transformer(xt,yt,wt,order,seed,mode,ym,args.device,24 if bench else None)
            if bench:
                save(args.out/f"bench-{args.device}-{args.threads}.json",dict(prediction=p.tolist(),
                     seconds=time.monotonic()-start,torch=torch.__version__,hip=torch.version.hip,threads=torch.get_num_threads(),
                     interop=torch.get_num_interop_threads(),device=(torch.cuda.get_device_name(0) if args.device=="cuda" else "cpu")))
                return
            params = {k:v.cpu().tolist() for k,v in m.state_dict().items()}
            record(f"{mode}-{seed}",mode,seed,params,p,info,time.monotonic()-tick)
    torch.set_num_threads(1)
    for mode in MODES:
        tick = time.monotonic()
        params,p,info = fit_poisson(x,y,w,ym,mode)
        record(mode+"-poisson",mode,None,params,p,info,time.monotonic()-tick)
    if len({checks[f"{mode}-{seed}"]["initial_state_sha256"] for mode in MODES for seed in SEEDS})!=3:
        raise ValueError("arms failed matched initialization")
    save(args.out/"example-predictions.json",example_predictions)
    files = [*sorted((args.out/"weights").glob("*.json")), *sorted(args.out.glob("permutations-*.npy")),
             *(args.out/n for n in ("training-index.npz","example.json","example-predictions.json"))]
    if len(files)!=30:
        raise ValueError("incomplete model file inventory")
    save(args.out/"weights-lock.json",dict(format=FORMAT,files={str(p.relative_to(args.out)):sha(p) for p in files},
         sha256_train=sha(args.data),methods={f:sha(HERE/f) for f in ("PROTOCOL.md","REGRESSION-NUMERICS.md","train.py","predict.py")},
         torch=torch.__version__,numpy=np.__version__,threads=args.threads,device=args.device,rows=len(y),originals=322,
         train_only=True,seeds=SEEDS,epochs=EPOCHS,batch_size=BATCH,seconds=time.monotonic()-start,fits=checks))
    print(f"Fit {len(checks)} models with full training-row parity.")


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task",choices=("bench","fit"))
    parser.add_argument("--data",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--threads",type=int,choices=[1,2],default=1)
    parser.add_argument("--device",choices=["cpu","cuda"],default="cpu")
    parser.add_argument("--retained",type=Path,help="SHA256 inventory of pre-existing Transformer fits")
    run(parser.parse_args())
