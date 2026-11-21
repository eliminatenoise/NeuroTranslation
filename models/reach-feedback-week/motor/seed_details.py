"""Display the already registered individual-seed range for the paired contrasts."""
import argparse
import json
import numpy as np
from pathlib import Path
from scoring import REGIONS,errors,per_original,resamples,summary

cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument("--input",type=Path, required=True)
cli.add_argument("--output",type=Path, required=True)
args=cli.parse_args()
with np.load(args.input,allow_pickle=False) as archive:
    a={k:archive[k] for k in ("seeds_full","seeds_pose","seeds_wrong","seeds","movement","workspace","block","original")}
roster=json.loads(Path(__file__).with_name("held-population.json").read_text())["roster"]
results={}
row_keys=list(zip(a["block"],a["original"]))
for workspace in (1,2):
    section={}
    group=[(r["block"],r["original"]) for r in sorted(roster,key=lambda r:(r["block"],r["start"])) if r["workspace"]==workspace]
    draws=resamples(group)
    for region in REGIONS:
        detail={}
        for si,seed in enumerate(a["seeds"]):
            e={k:errors(a["seeds_"+k][si],a["movement"],region) for k in ("full","pose","wrong")}
            mask=(a["workspace"]==workspace) & np.logical_and.reduce([np.isfinite(v).all(1) for v in e.values()])
            detail[str(seed)]={}
            for ctl in ("pose","wrong"):
                delta=per_original(e["full"]-e[ctl],row_keys,group,mask)
                first_two=summary(delta[:,:2],draws)
                detail[str(seed)][ctl]={"mean_all_horizons":summary(delta)["mean"],"trajectory_and_endpoint_intervals":first_two}
        for ctl in ("pose","wrong"):
            values=[detail[str(s)][ctl]["mean_all_horizons"] for s in a["seeds"]]
            detail[ctl+"_seed_mean_range"]=np.stack((np.min(values,axis=0),np.max(values,axis=0)),axis=1).tolist()
        section[region]=detail
    results[str(workspace)]=section
args.output.write_text(json.dumps(results,indent=2,allow_nan=False) + "\n")
