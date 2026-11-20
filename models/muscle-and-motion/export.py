"""Generate the distributable browser weights and wholly invented example."""
import argparse
import json
from pathlib import Path

from network import inputs, np, predictions, prepare, restore, write_json, configure


def export_files(folder):
    w=json.loads((folder/"weights.json").read_text())
    (folder/"weights.js").write_text("globalThis.MuscleMotionWeights="+json.dumps(w,separators=(",",":"))+";\n")
    t=np.arange(160)/256.
    leg=np.column_stack([(1+.18*j)*(7+2*np.cos(2*np.pi*(1+.1*j)*t))*np.sin(2*np.pi*(23+3*j)*t+.13*j)
                         for j in range(8)])
    xyz=np.column_stack([5*np.sin(2*np.pi*.8*t),3*np.cos(2*np.pi*1.4*t),95*t+2*np.sin(2*np.pi*1.5*t)])
    invented=dict(leg_uv=leg.round(6).tolist(),sacrum_mm=xyz.round(6).tolist(),posture=1,direction=-1)
    write_json(folder/"synthetic-event.json",invented)
    (folder/"example.js").write_text("globalThis.MuscleMotionExample="+json.dumps(invented,separators=(",",":"))+";\n")
    d={key:np.array([v]) for key,v in invented.items()}
    feats=prepare(inputs(d),w["scale"],"cpu")
    joint=predictions(restore(w["models"]["joint"],"joint"),feats,w["scale"])
    muscle=predictions(restore(w["models"]["muscle"],"muscle"),feats,w["scale"])
    path=predictions(restore(w["models"]["path"],"path"),feats,w["scale"])
    write_json(folder/"synthetic-reference.json",{name:dict(future_rms_uv=y[0].tolist(),future_path_mm=p[0].tolist())
                                 for name,(y,p) in {"joint":joint,"specialists":(muscle[0],path[1])}.items()})


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder",nargs="?",type=Path,default=Path(__file__).resolve().parent)
    configure(1)
    export_files(parser.parse_args().folder)
