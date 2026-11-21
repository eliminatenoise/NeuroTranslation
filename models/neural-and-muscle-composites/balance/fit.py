"""Fit from a development file only. Stores numerical weights as portable arrays."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from model import BASES, PROTOCOL, draws, fit_model, fit_tensors, load, scales


def synchronize(device):
    if device == "cuda":
        torch.cuda.synchronize()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("development",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--benchmark",action="store_true")
    p.add_argument("--threads",type=int,default=1)
    p.add_argument("--device",choices=("cpu","cuda"),default="cpu")
    args=p.parse_args()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    a = load(args.development)
    if len(np.unique(a["person"])) != 18:
        raise ValueError("fit requires development cohort only")
    s = scales(a)
    xs, y = fit_tensors(a, s, args.device)
    models = ["paired"] if args.benchmark else list(BASES)
    seeds = PROTOCOL["fit"]["seeds"][:1] if args.benchmark else PROTOCOL["fit"]["seeds"]
    updates = 32 if args.benchmark else PROTOCOL["fit"]["steps"]
    states = {k:v for k,v in s.items()}
    durations = {}
    for seed in seeds:
        indices = torch.as_tensor(draws(a,seed,updates), device=args.device)
        for name in models:
            synchronize(args.device)
            start = perf_counter()
            net = fit_model(name,seed,xs,y,indices,args.device)
            synchronize(args.device)
            durations[f"{name}_{seed}"] = perf_counter()-start
            if args.benchmark:
                with torch.inference_mode():
                    states = {"benchmark_prediction":net([x[:128] for x in xs]).cpu().numpy()}
            else:
                states.update({f"{name}_{seed}/{k}":v.detach().cpu().numpy() for k,v in net.state_dict().items()})
    np.savez_compressed(args.output, **states)
    print(json.dumps({"torch":torch.__version__,"numpy":np.__version__,"device":args.device,
                      "threads":torch.get_num_threads(),"interop":torch.get_num_interop_threads(),
                      "updates_each":updates,"parameters_each":sum(p.numel() for p in net.parameters()),
                      "train_seconds":durations,"models":len(models),"seeds":seeds,
                      "examples_each":updates*128},indent=2))


if __name__ == "__main__":
    main()
