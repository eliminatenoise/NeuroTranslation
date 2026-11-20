"""Report frozen forecasts beside an excluded original event, on separate denominators."""
import argparse,json
from pathlib import Path
import numpy as np
from study import put,group_stats

def run(qc_path,npz,rows_path,output):
    qc=json.loads(qc_path.read_bytes())
    with np.load(npz,allow_pickle=False) as f:
        data={k:f[k] for k in ("person","event","direction","cutoff","future_delta_mm")}
    with np.load(rows_path,allow_pickle=False) as f:
        pred={k:f[k] for k in ("shared_full","shared_nuisance","shared_residual","linear_nuisance","velocity","recent")}
        for k in ("person","event","direction","cutoff"):
            np.testing.assert_array_equal(data[k],f[k])
    flags={p:set(v["admitted_neighbors_of_excluded_ordinals"]) for p,v in qc["per_person"].items()}
    nearby=np.array([i in flags[p] for p,i in zip(data["person"],data["event"])])
    out={"definition":"Admitted event with an immediately adjacent excluded event in original log order. This is proximity in event order, not detection of a physical artefact.",
         "neighbor":group_stats(data,pred,nearby,pred.keys())[0],"others":group_stats(data,pred,~nearby,pred.keys())[0]}
    put(output,out)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("qc","npz","predictions","output"):p.add_argument(key,type=Path)
    a=p.parse_args();run(a.qc,a.npz,a.predictions,a.output)
