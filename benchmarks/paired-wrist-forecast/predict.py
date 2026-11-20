"""Forecast both right-wrist angles from earlier measurements on the pointing-task grid."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

import study_model as m
from broader_learner import ModalityBatch, ObservationBatch, QueryBatch, configure_cpu_runtime


HERE = Path(__file__).resolve().parent


def values(payload,name,shape):
    array = np.asarray(payload[name])
    if array.dtype.kind not in "iuf" or array.shape!=shape or not np.isfinite(array).all():
        raise ValueError(f"{name} must contain finite numbers of shape {shape}")
    return array.astype(np.float64)


def substreams(payload,mode):
    anchor = values(payload,"anchor_deg",(2,))
    mean = values(payload,"mean_angles_deg",(16,2))
    groups = {m.MOTION:mean-anchor}
    if m.EMG in m.MODES[mode]:
        groups[m.EMG] = values(payload,"emg_rms_uv",(16,4))
        if (groups[m.EMG]<0).any():
            raise ValueError("EMG RMS amplitude must be nonnegative")
    if m.EEG in m.MODES[mode]:
        groups[m.EEG] = values(payload,"eeg_mean_uv",(16,8))
    return anchor,groups


@torch.inference_mode()
def predict(payload,mode):
    anchor,groups = substreams(payload,mode)
    offset = payload["target_offset_after_cue_ticks"]
    if type(offset) is not int or offset not in m.OFFSETS:
        raise ValueError("The target must be one of the six studied cue offsets")
    norm_path = HERE/"normalizers.json"
    weights = HERE/"weights"/(mode+".npz")
    pins = json.loads((HERE/"model-sources.json").read_text())
    if hashlib.sha256(norm_path.read_bytes()).hexdigest()!=pins["normalizers_sha256"]:
        raise ValueError("The stored training scales differ from the published study")
    norm = {k:np.asarray(v,dtype=np.float64) for k,v in json.loads(norm_path.read_text()).items()}
    if hashlib.sha256(weights.read_bytes()).hexdigest()!=pins["trained_weights_sha256"][mode]:
        raise ValueError("The fitted parameter file differs from the published study")
    model = m.make_model(norm,{"six-participant-training-cohort"})
    with np.load(weights,allow_pickle=False) as source:
        model.load_state_dict({k:torch.from_numpy(source[k]) for k in source.files},strict=True)
    model.eval()
    slot = int(np.flatnonzero(m.OFFSETS == offset)[0])
    grid = torch.from_numpy(((offset-m.LEAD+np.arange(-240,1,16))/512)[None,:])
    cutoff = grid[:,-1]
    ids,parents = ("supplied-window",),("supplied-trial",)
    records = {}
    for k,g in groups.items():
        x = torch.from_numpy(g.astype(np.float32))[None]
        available = cutoff[:,None].expand_as(grid) if k==m.MOTION else grid
        records[k] = ModalityBatch(m.IDS[k],ids,parents,m.PAIR,x,torch.ones_like(x,dtype=torch.bool),
                                   available[:,:,None].expand_as(x))
    context = np.concatenate(((anchor-norm["anchor_center"])/norm["anchor_scale"], np.eye(6)[slot]))
    context = torch.from_numpy(context.astype(np.float32))[None]
    obs = ObservationBatch(ids,parents,"DEV",m.TASK,m.CLOCK,m.ALIGN,m.PAIR,grid,torch.ones_like(grid,dtype=torch.bool),
                           context,cutoff[:,None].expand_as(context),records)
    requested = torch.tensor([[offset/512]],dtype=torch.float64)
    query = QueryBatch(requested,torch.ones_like(requested,dtype=torch.bool))
    dist = model.predict(obs,query,m.direction(mode))[m.MOTION]
    stored = model.to_stored_units(m.MOTION,dist)
    return {"angle_deg":(anchor+stored.mean[0,0].numpy().astype(np.float64)).tolist(),
            "variance_deg2":stored.variance[0,0].numpy().astype(np.float64).tolist()}


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=HERE/"example.json")
    parser.add_argument("--mode",choices=("all",*m.MODES),default="all")
    args = parser.parse_args()
    configure_cpu_runtime(1,1,True)
    data = json.loads(args.input.read_text())
    modes = list(m.MODES) if args.mode=="all" else [args.mode]
    print(json.dumps({"axes":["extension","radial_deviation"],"horizon_stored_s":.25,
                      "predictions":{mode:predict(data,mode) for mode in modes}},indent=2,allow_nan=False))
