"""Run a fitted model on one four-bin history. Prediction output is in centimeters."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from wtrack import HERE, PROTOCOL, UNITS, digest, predict_ridge


def predict_example(folder, name, ex):
    if (ex["subject"]!=PROTOCOL["source"]["rat"] or ex["session"]!="01" or ex["epoch_id"]!=5
            or not np.array_equal(ex["unit_ids"],UNITS)):
        raise ValueError("Wrong rat, recording, running epoch or unit order")
    cutoff = float(ex["cutoff_s"])
    times = np.asarray(ex["history_frame_s"],dtype=float)
    m = np.asarray(ex["motion"],dtype=float)
    c = np.asarray(ex["log_elapsed"],dtype=float)
    s = np.asarray(ex["spike_counts"],dtype=float)
    nominal = cutoff+np.arange(-4,1)/4
    if (times.shape!=(5,) or not np.isfinite(times).all() or not np.isfinite(cutoff)
        or np.any(np.diff(times)<=0) or np.any(times>nominal) or np.any(nominal-times>.075)
        or m.shape!=(4,5) or s.shape!=(4,len(UNITS)) or c.shape!=(2,)
        or not all(np.isfinite(v).all() for v in [m,c,s]) or not np.allclose(m[:,4],nominal[1:]-times[1:],atol=1e-8)
        or np.any(s<0) or np.any(s!=np.round(s))):
        raise ValueError("History timing, shape or count data outside contract")
    seal = json.loads((folder/"fit-seal.json").read_text())
    path = folder/(name+".npz")
    if digest(path)!=seal["weights"][name]:
        raise ValueError("Fitted weight hash does not match seal")
    with np.load(path,allow_pickle=False) as z:
        fit=dict(z)
    if name.startswith("ridge_"):
        fn=predict_ridge
    else:
        import attention
        attention.set_threads(1)
        fn=attention.predict
    xy=fn(fit,m[None],c[None],s[None])[0]
    return dict(model=name,subject=ex["subject"],epoch_id=5,trial_id=ex["trial_id"],cutoff_s=cutoff,
                requested_lead_s=.25,forecast_xy_cm=xy.tolist())


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fit",type=Path,default=HERE/"fitted")
    p.add_argument("--example",type=Path)
    p.add_argument("--model",default="ridge_combined",choices=["ridge_combined","ridge_motion","ridge_spikes",
                                                             "attention_combined","attention_motion"])
    a=p.parse_args()
    print(json.dumps(predict_example(a.fit,a.model,json.loads((a.example or a.fit/"example.json").read_text())),indent=2))
