"""Issue frozen forecasts on an extracted split and compare Torch and NumPy outputs."""
import argparse
import json
import os
import tempfile
import time
from pathlib import Path
import numpy as np
import torch
from predict import CONTACTS, MODES, SEEDS, forward, mask, read_weights, stack_inputs
from train import Transformer, configure, save, sha

ID_KEYS = ("trial","k","phase","offset","direction","donor")
HERE = Path(__file__).resolve().parent


def check_release(file):
    value = json.loads(file.read_text())
    workspace = file.resolve().parents[2]
    hashes = value["sha256"]
    required = {"contact-study/models/weights-lock.json","contact-study/models/PROTOCOL.md",
                "contact-study/models/infer.py","contact-study/core/DESIGN.md"}
    if not required.issubset(hashes) or not any("contact-study/source/" in k for k in hashes) or not any("contact-study/scoring/" in k for k in hashes):
        raise ValueError("release does not bind all required study components")
    for name,digest in hashes.items():
        p = (workspace/name).resolve()
        if not p.is_relative_to(workspace) or sha(p)!=digest:
            raise ValueError("release identity differs: "+name)


def native(raw,w):
    # Torch independently applies scaling, clipping and masking in the native path.
    x = torch.from_numpy(raw)
    z = ((x-torch.tensor(w["x_mean"]))/torch.tensor(w["x_scale"])).clamp(-8,8)
    z = z*torch.tensor(w["x_active"])*torch.tensor(mask(w["mode"]))
    with torch.inference_mode():
        if w["family"]=="poisson":
            return (z.reshape(-1,200) @ torch.from_numpy(w["parameters"]["coef"]) +
                    torch.from_numpy(w["parameters"]["intercept"])).exp().numpy()
        m = Transformer()
        m.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in w["parameters"].items()})
        m.eval()
        # Bound temporary activation memory across full-day predictions.
        return torch.cat([m(rows) for rows in z.float().split(256)]).numpy()


def check_ids(d,stage,raw):
    ids = {k:d[k] for k in ID_KEYS}
    n = len(raw)
    if any(v.shape!=(n,) or v.dtype.kind not in "iu" for v in ids.values()):
        raise ValueError("invalid row metadata")
    trial,k,phase,offset,direction,donor = (ids[name] for name in ID_KEYS)
    if not np.isin(phase,([0] if stage=="validation" else [0,1,2])).all() or len(set(zip(trial,phase,k)))!=n:
        raise ValueError("unexpected stage membership")
    if np.any((donor < -1)|(donor>=n)):
        raise ValueError("donor outside split")
    ok = donor>=0
    j = donor[ok]
    if (np.any(trial[j]>=trial[ok]) or np.any(k[j]>=k[ok]) or np.any(phase[j]!=phase[ok]) or
            np.any(offset[j]!=offset[ok]) or np.any(direction[j]!=direction[ok]) or
            not np.array_equal(raw[j,:,30:37],raw[ok,:,30:37])):
        raise ValueError("donor violates original, phase, direction, offset or visible cue constraints")
    return ids


def infer(stage,data,weights,out,release):
    configure(1)
    start = time.monotonic()
    if data.name!=stage+".npz":
        raise ValueError("input filename must match stage")
    if stage=="test" and HERE==weights.resolve() and out.resolve()==HERE:
        if release!=HERE.parent/"core/test-release.json":
            raise ValueError("the live study requires its specific release")
    if release:
        check_release(release)
    if data.resolve()==HERE.parent/"source/test.npz" and not release and weights.resolve()==HERE:
        raise ValueError("live test input requires release")
    if stage=="validation" and sha(data)!="0ed0cb0ea5b9ecddc96bb80c477c0d25fe6ab2153523115d574a6183acd5fc9c":
        raise ValueError("validation archive differs from the locked source")
    out.mkdir(exist_ok=True,parents=True)
    outputs = [out/f"{stage}-{fam}.npz" for fam in ("transformer","poisson")]
    receipt = out/f"{stage}-inference.json"
    if any(p.exists() for p in [*outputs,receipt]):
        raise FileExistsError("predictions or an inference receipt are already present")
    lock = json.loads((weights/"weights-lock.json").read_text())
    for k,h in lock["files"].items():
        if sha(weights/k)!=h:
            raise ValueError("model archive differs: "+k)
    for k,h in lock["methods"].items():
        if sha(HERE/k)!=h:
            raise ValueError("method differs: "+k)
    with np.load(data,allow_pickle=False) as d:
        raw = stack_inputs(d)
        ids = check_ids(d,stage,raw)
    ok = ids["donor"]>=0
    wrong = raw[ok].copy()
    wrong[:,:,:4] = raw[ids["donor"][ok],:,:4]
    metrics = {}
    with tempfile.TemporaryDirectory(dir=out) as folder:
        staging = Path(folder)
        for family,path in zip(("transformer","poisson"),outputs,strict=True):
            budget = SEEDS if family=="transformer" else (None,)
            arrays = {name:[] for name in (*MODES,"wrong_movement")}
            for seed in budget:
                for mode in MODES:
                    key = f"{mode}-{seed or 'poisson'}"
                    w = read_weights(weights/"weights"/(key+".json"))
                    if w["mode"]!=mode or w["seed"]!=seed or w["family"]!=family:
                        raise ValueError("model label or seed mismatch")
                    for condition,rows in ((mode,raw),("wrong_movement",wrong)) if mode=="all" else ((mode,raw),):
                        if len(rows):
                            p,ref = native(rows,w),forward(rows,w)
                            tol = (1e-4,0.) if seed else (1e-10,1e-10)
                            if not np.isfinite(p).all() or np.any(p<=0) or not np.allclose(p,ref,atol=tol[0],rtol=tol[1]):
                                raise ValueError("native/portable numerical parity failed: "+key+" "+condition)
                            metrics[key+"/"+condition] = float(np.max(np.abs(p-ref)))
                        else:
                            p = np.empty((0,26))
                        if condition=="wrong_movement":
                            full = np.full((len(raw),26),np.nan)
                            full[ok] = p
                            p = full
                        arrays[condition].append(p)
            values = {k:np.stack(v) if family=="transformer" else v[0] for k,v in arrays.items()}
            np.savez_compressed(staging/path.name,**values,**ids,seeds=np.asarray(SEEDS if family=="transformer" else [],np.int32))
        checks = dict(split=stage,input_sha256=sha(data),weights_sha256=sha(weights/"weights-lock.json"),
                      code_sha256=sha(HERE/"infer.py"),release_sha256=sha(release) if release else None,
                      rows=len(raw),matched_rows=int(ok.sum()),native_to_numpy_max_abs=metrics,
                      all_positive_and_allclose=True,seconds=time.monotonic()-start,
                      outputs={p.name:sha(staging/p.name) for p in outputs})
        save(staging/receipt.name,checks)
        for p in [*outputs,receipt]:
            os.replace(staging/p.name,p)
    print(f"Sealed {len(outputs)} {stage} archives; {len(raw)} rows, {ok.sum()} with donors.")


if __name__=="__main__":
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("stage",choices=("validation","test"))
    cmd.add_argument("--data",type=Path,required=True)
    cmd.add_argument("--weights",type=Path,default=HERE)
    cmd.add_argument("--out",type=Path,required=True)
    cmd.add_argument("--release",type=Path)
    args = cmd.parse_args()
    infer(args.stage,args.data,args.weights,args.out,args.release.resolve() if args.release else None)
