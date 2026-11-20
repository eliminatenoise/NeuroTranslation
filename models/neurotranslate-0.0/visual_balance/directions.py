"""Direction-specific errors for correct scalp, no scalp and the same fitted model with a donor."""
import argparse
import json
from pathlib import Path
import numpy as np
from study import group_stats,put

def run(source, predfile, output):
    with np.load(source,allow_pickle=False) as f:d={k:f[k] for k in ("person","event","direction","block","cutoff","future_delta_mm")}
    with np.load(predfile,allow_pickle=False) as f:
        for k in ("person","event","direction","cutoff"):np.testing.assert_array_equal(d[k],f[k])
        p={k:f[k] for k in f.files if k.startswith(("shared_","linear_"))}
    bins={}
    for i, key in enumerate(zip(d["person"],d["direction"],d["block"])):
        bins.setdefault(key,[]).append(i)
    out={}
    for key,seed in (("cycle",None),("258",258),("1173",1173)):
        rng=np.random.default_rng(seed);narrow=0;eligible=np.zeros(len(d["event"]),bool)
        for _,indices in sorted(bins.items()):
            if len(indices)<2:continue
            idx=np.array(sorted(indices,key=lambda i:(d["cutoff"][i],d["event"][i])))
            if seed is not None:idx=rng.permutation(idx)
            dif=np.abs(d["cutoff"][idx]-d["cutoff"][np.roll(idx,-1)])
            narrow+=int(((dif>=200)&(dif<=207)).sum());eligible[idx]=dif>207
        np.testing.assert_array_equal(eligible,np.isfinite(p["shared_full_wrong_"+key][:,0,0]))
        both=[person for person in np.unique(d["person"][eligible]) if set(d["direction"][eligible & (d["person"]==person)])=={-1,1}]
        methods=("shared_full","shared_nuisance","shared_full_wrong_"+key,"shared_residual","shared_residual_wrong_"+key,"linear_full","linear_nuisance","linear_full_wrong_"+key)
        pair=eligible & np.isin(d["person"],both)
        out[key]={"pairs_excluded_at_200_through_207_samples":narrow,"both_directions_people":len(both),"eligible_pairs":int(pair.sum()),
            "by_direction":{str(direction):group_stats(d,p,pair & (d["direction"]==direction),methods)[0] for direction in (-1,1)}}
    put(output,out)
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ("source","predictions","output"):parser.add_argument(n,type=Path)
    a=parser.parse_args();run(a.source,a.predictions,a.output)
