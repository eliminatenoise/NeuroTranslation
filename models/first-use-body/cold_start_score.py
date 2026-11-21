"""Score the first visible frame's last-position fallback at the prespecified horizon."""
import argparse
from pathlib import Path

import numpy as np

from first_use import predict
from forecaster import PROTOCOL, norms
from study import digest, load, records, save


def cold_start(manifest):
    result=[]
    for row in records(manifest,"test"):
        xy,t=load(row)
        visible=np.isfinite(xy).all(2).any(1)
        o=int(np.flatnonzero(visible)[0]) if visible.any() else None
        nominal=PROTOCOL["low_rate_horizon_s"] if np.median(np.diff(t))>.12 else PROTOCOL["horizon_s"]
        item={"group":row["group"],"track":row["id"],"nominal_s":nominal,"scored":0}
        if o is not None and o+1<len(t):
            e=o+1+int(np.argmin(np.abs(t[o+1:]-t[o]-nominal)))
            dt=t[e]-t[o]
            if abs(dt-nominal)<=PROTOCOL["horizon_tolerance_s"]+1e-10:
                predicted,_=predict(xy[o:o+1],t[o:o+1],dt,{})
                finite=np.isfinite(predicted).all(1)
                common=finite & np.isfinite(xy[e]).all(1)
                p=predicted[finite]
                radius=float(np.sqrt(np.mean(norms(p-p.mean(0))**2)))
                item.update(wait_s=float(t[o]-t[0]),actual_horizon_s=float(dt),visible=int(finite.sum()),
                            scored=int(common.sum()),radius=radius)
                if common.any():
                    error=float(norms(predicted[common]-xy[e,common]).mean())
                    item.update(mean_raw=error,mean_normalized=error/radius if radius>0 else None)
        result.append(item)
    return {"description":"First visible frame only; no learned weights. Last-position forecast scored against future optical track. Radius uses all visible points at that first observation.","manifest":digest(manifest),"track_results":result}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();save(a.out,cold_start(a.manifest))
