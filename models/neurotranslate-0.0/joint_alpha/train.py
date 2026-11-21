"""Fit one common encoder on balanced task minibatches, then fit matched controls."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F
from inference import standardize
from network import Joint, DEFAULT

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE/'protocol.json').read_text())
SCHEMA_FIELDS = ('kind', 'channels', 'outputs', 'input_units', 'output_units', 'history_steps', 'description', 'horizon', 'clock', 'source', 'timing', 'target_definition', 'input_definition', 'history', 'target', 'limits', 'baseline_description', 'scales_training_history')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def weights_hash(items):
    digest = hashlib.sha256()
    for name, val in sorted(items):
        digest.update(name.encode())
        digest.update(val.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def moments(arr):
    # Streaming double-precision observed moments bound temporary allocation for candidate rosters.
    end = arr.shape[-1]
    total, squares, count = [np.zeros(end,dtype='d') for _ in range(3)]
    for i in range(0,len(arr),512):
        block = arr[i:i+512].reshape(-1,end).astype('d')
        finite = np.isfinite(block)
        block[~finite] = 0.
        total += block.sum(axis=0)
        squares += (block*block).sum(axis=0)
        count += finite.sum(axis=0)
    mean = total / np.maximum(count,1)
    std = np.sqrt(np.maximum(0.,squares/np.maximum(count,1)-mean*mean))
    return mean.astype('f'), np.where(std>1e-6, std, 1.).astype('f')


def split_path(root, entry):
    return root/(entry if isinstance(entry,str) else entry['path'])


class Cases:
    def __init__(self, root, schema, key):
        path = split_path(root,schema['splits'][key])
        with np.load(path,allow_pickle=False) as data:
            self.x = data['X']
            self.y = data['y']
            self.group = data['group']
            self.valid = data['valid'] if 'valid' in data else None
            self.baseline = data['baseline'] if 'baseline' in data else None
            self.strong_reference = data['strong_reference'] if 'strong_reference' in data else None
        self.groups, which = np.unique(self.group,return_inverse=True)
        self.buckets = [np.flatnonzero(which == group) for group in range(len(self.groups))]
        if self.x.shape[0] != self.y.shape[0] or self.x.shape[0] != len(self.group):
            raise ValueError('Input, target and group rows differ')
        self.kind = schema['kind']
        if self.kind=='categorical':
            if self.x.ndim != 4 or self.y.ndim != 1 or np.any((self.y<0)|(self.y>=self.x.shape[1])):
                raise ValueError('Invalid local candidate target')
            if self.valid is not None and not self.valid[np.arange(len(self.y)),self.y].all():
                raise ValueError('The observed next unit must belong to its eligible set')
        elif self.y.ndim!=2 or not np.isfinite(self.y).any(axis=1).all():
            raise ValueError('Each dense training case needs an observed target')
        if self.kind=='count' and np.any(np.isfinite(self.y)&((self.y<0)|(self.y!=np.floor(self.y)))):
            raise ValueError('Observed counts must be nonnegative integers')

    def stats(self):
        xm,xs = moments(self.x)
        if self.kind=='categorical':
            ym,ys = np.zeros(1,'f'),np.ones(1,'f')
        else:
            ym,ys = moments(self.y)
            if self.kind=='count':
                ym = np.maximum(ym,1e-4)
        return dict(xmean=xm,xscale=xs,ymean=ym,yscale=ys)

    def sample(self, rng, size):
        groups = rng.integers(len(self.buckets), size=size)
        return np.asarray([self.buckets[g][rng.integers(len(self.buckets[g]))] for g in groups])

    def tensors(self, ix, stats):
        x = self.x[ix]
        norm = torch.from_numpy(standardize(x,stats['xmean'],stats['xscale']))
        if self.kind=='categorical':
            valid = np.isfinite(x).any(axis=(-1,-2)) if self.valid is None else self.valid[ix]
            return norm, torch.from_numpy(self.y[ix].astype('int64')),torch.from_numpy(valid.astype(bool))
        return norm,torch.from_numpy(self.y[ix].astype('f')),None


def loss(model, task, batch, stats, kind):
    x,y,valid = batch
    device = next(model.parameters()).device
    if device.type != 'cpu':
        x,y = x.to(device),y.to(device)
        valid = None if valid is None else valid.to(device)
    raw = model(task,x,valid)
    if kind=='categorical':
        return F.cross_entropy(raw,y)
    observed = torch.isfinite(y)
    target = torch.where(observed,y,0.)
    mean = torch.as_tensor(stats['ymean'],device=device)
    if kind=='count':
        log_rate = torch.log(mean) + raw.clamp(-10.,10.)
        err = torch.exp(log_rate)-target*log_rate
    else:
        z = (target-mean)/torch.as_tensor(stats['yscale'],device=device)
        err = F.smooth_l1_loss(raw,z,reduction='none')
    return ((err*observed).sum(dim=-1)/observed.sum(dim=-1).clamp_min(1)).mean()


def train(model, tasks, cases, stats, steps, evidence, learning_rate=None, seed=None, schedule="constant"):
    started = time.monotonic()
    lr = learning_rate if learning_rate is not None else PLAN['learning_rate']
    seed = PLAN['seed'] if seed is None else seed
    opt = torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=PLAN['weight_decay'])
    rngs = {t:np.random.default_rng(seed+int(hashlib.sha256(t.encode()).hexdigest()[:8],16)) for t in tasks}
    grad = {}
    for step in range(steps):
        if schedule=='warmup_cosine':
            warm = max(1,round(.05*steps))
            if step<warm:
                mult = .1+.9*step/max(warm-1,1)
            else:
                phase = (step-warm)/max(steps-warm-1,1)
                mult = .1+.45*(1+math.cos(math.pi*phase))
            for group in opt.param_groups:
                group['lr']=lr*mult
        opt.zero_grad(set_to_none=True)
        losses = []
        for t in tasks:
            d = cases[t]
            ix = d.sample(rngs[t],PLAN['batch_per_task'])
            value = loss(model,t,d.tensors(ix,stats[t]),stats[t],d.kind)
            losses.append(value)
            if evidence and step in (0,steps-1):
                params = list(model.trunk.named_parameters())
                grads = torch.autograd.grad(value,[p for _,p in params],retain_graph=True)
                grad.setdefault(str(step+1),{})[t] = {name:float(g.norm()) for (name,_),g in zip(params,grads)}
        total = torch.stack(losses).mean()
        if not torch.isfinite(total):
            raise ValueError('Nonfinite training loss')
        total.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),PLAN['clip_gradient_norm'])
        opt.step()
    return {'seconds':time.monotonic()-started,'gradient_norms_of_each_task_on_the_shared_trunk':grad}


def save(model, schemas, stats, path):
    path.parent.mkdir(parents=True,exist_ok=True)
    payload = {k:v.detach().cpu().numpy() for k,v in model.state_dict().items()}
    for t,fields in stats.items():
        payload.update({t+'.'+name:value for name,value in fields.items()})
    payload['schemas'] = np.array(json.dumps(schemas,sort_keys=True))
    payload['version'] = np.array(PLAN['version'])
    payload['architecture'] = np.array(json.dumps(model.architecture,sort_keys=True))
    with path.with_suffix('.tmp').open('wb') as f:
        np.savez_compressed(f,**payload)
    path.with_suffix('.tmp').replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--tasks',nargs='+')
    parser.add_argument('--steps',type=int,default=PLAN['updates'])
    parser.add_argument('--threads',type=int,default=2)
    parser.add_argument('--seed',type=int,default=PLAN['seed'])
    parser.add_argument('--schedule',choices=['constant','warmup_cosine'],default='constant')
    parser.add_argument('--learning-rate',type=float,default=PLAN['learning_rate'])
    parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    parser.add_argument('--controls',action='store_true')
    for key, default in DEFAULT.items():
        parser.add_argument('--'+key.replace('_','-'), type=int, default=default)
    args = parser.parse_args()
    architecture = {key:getattr(args,key) for key in DEFAULT}
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True)
    data = json.loads(args.manifest.read_text())['tasks']
    tasks = sorted(args.tasks or data)
    schemas = {t:{k:data[t][k] for k in SCHEMA_FIELDS if k in data[t]} for t in tasks}
    if 'human_leg_emg' in schemas:
        schemas['human_leg_emg']['output_bound'] = 'nonnegative'
    cases = {t:Cases(args.manifest.parent,data[t],'train') for t in tasks}
    stats = {t:d.stats() for t,d in cases.items()}
    initial = Joint(schemas,architecture)
    model = copy.deepcopy(initial).to(args.device)
    args.evidence.mkdir(parents=True,exist_ok=True)
    report = dict(initial_shared_hash=weights_hash(initial.trunk.named_parameters()),steps=args.steps,
                  task_count=len(tasks),architecture=architecture,learning_rate=args.learning_rate,seed=args.seed,schedule=args.schedule,batch_per_task=PLAN['batch_per_task'],
                  training_split_sha256={t:file_hash(split_path(args.manifest.parent,data[t]['splits']['train'])) for t in tasks},
                  parameters_shared=sum(p.numel() for p in model.trunk.parameters()),
                  parameters_total=sum(p.numel() for p in model.parameters()),
                  training_rows={t:len(cases[t].x) for t in tasks},training_groups={t:len(cases[t].groups) for t in tasks})
    if args.device=='cuda':
        torch.cuda.reset_peak_memory_stats()
    report['joint'] = train(model,tasks,cases,stats,args.steps,True,args.learning_rate,args.seed,args.schedule)
    import resource
    report['rss_peak_through_fit_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report['training_device'] = args.device
    report['gpu_peak_allocated_bytes'] = torch.cuda.max_memory_allocated() if args.device=='cuda' else None
    report['gpu_peak_reserved_bytes'] = torch.cuda.max_memory_reserved() if args.device=='cuda' else None
    save(model,schemas,stats,args.out)
    report['final_shared_hash'] = weights_hash(model.trunk.named_parameters())
    report['checkpoint_sha256'] = file_hash(args.out)
    report['controls'] = {}
    log = args.evidence/'training.json'
    log.write_text(json.dumps(report,indent=2)+'\n')
    print('Joint checkpoint written',args.out,report['checkpoint_sha256'],flush=True)
    if args.controls:
        for t in tasks:
            single = copy.deepcopy(initial).to(args.device)
            item = train(single,[t],cases,stats,args.steps,False,args.learning_rate,args.seed,args.schedule)
            # Only this single task is used for control inference. Keep controls private.
            keep = Joint({t:schemas[t]},architecture)
            state = {name:v for name,v in single.state_dict().items() if name in keep.state_dict()}
            keep.load_state_dict(state)
            save(keep,{t:schemas[t]},{t:stats[t]},args.evidence/(t+'-control.npz'))
            report['controls'][t] = item['seconds']
        log.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
