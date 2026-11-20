"""Extract past-only four-bin features and a separately measured future orientation target."""
from pathlib import Path
import numpy as np
from scipy.io import loadmat

CODES = (611, 621)
REGIONS = ("brachial_matrix", "lumbar_matrix")


def degrees(a, b):
    """Inputs have unit norm along the final axis. q and −q give the same orientation."""
    dots = np.sum(a*b, axis=-1)
    return np.rad2deg(2*np.arccos(np.clip(np.abs(dots), 0, 1)))


def motion_bins(history):
    qbins = np.stack([history[:, start:start+51] for start in range(0,200,50)], axis=1)
    end_to_end = degrees(qbins[:, :, 0], qbins[:, :, -1])
    path = degrees(qbins[:, :, :-1], qbins[:, :, 1:]).sum(axis=-1)
    return np.stack([end_to_end, path], axis=-1)


def voltage_bins(raw, cutoffs):
    out = np.empty((len(cutoffs), 4, 2))
    for step in range(4):
        ix = cutoffs[:,None] - 200 + step*50 + np.arange(51)
        window = np.asarray(raw[:,ix],dtype=np.float64)
        valid = np.isfinite(window).all(axis=2)
        clean = np.where(valid[:,:,None],window,0.0)
        spread = np.std(clean,axis=2)
        change = np.sqrt(np.mean(np.square(np.diff(clean,axis=2)),axis=2))
        for j, feature in enumerate((spread,change)):
            # An unavailable channel affects only its own recipient bin.
            out[:,step,j] = np.ma.median(np.ma.array(feature,mask=~valid),axis=0).filled(np.nan)
        out[valid.sum(axis=0)<16,step,:] = np.nan
    return out


def read_trial(file, person, trial):
    doc=loadmat(Path(file),simplify_cells=True)["data_estructure"]
    labels=[str(x).strip() for x in doc["quaternions"]["labels"]]
    expected=[f"Quaternion ({i})[A.U]" for i in range(1,5)]
    if labels!=expected:
        raise ValueError(f"Cannot establish four orientation components in {Path(file).name}: {labels}")
    meta=doc["experiment_data"]
    q=np.asarray(doc["quaternions"]["data"],dtype=np.float64).T
    t=np.asarray(meta["time_vector"],dtype=np.float64)
    codes=np.asarray(meta["task_vector"])
    if (meta["sample_frequency"]!=2000 or q.shape!=(len(t),4) or codes.shape!=t.shape
            or not np.isfinite(t).all() or not np.allclose(np.diff(t),.0005,rtol=0,atol=1e-10)):
        raise ValueError(f"Unsupported source clock or quaternion layout: {file}")
    declared={(int(d["task_number"]),str(d["task_description"])) for d in meta["tasks_description"]}
    for k,part in ((611,"Static"),(621,"Motion")):
        if not any(code==k and part in label and "Basic task" in label for code,label in declared):
            raise ValueError("Original task label missing")
    bounds=np.r_[0,np.flatnonzero(codes[1:]!=codes[:-1])+1,len(codes)]
    cutoffs=np.concatenate([np.arange(a+200,b-200,200) for a,b in zip(bounds,bounds[1:]) if codes[a] in CODES])
    norm=np.linalg.norm(q,axis=1);valid=np.isfinite(q).all(axis=1)&(norm>0)
    q=np.divide(q,norm[:,None],out=np.full_like(q,np.nan),where=valid[:,None])
    history=q[cutoffs[:,None]+np.arange(-200,1)]
    bins=[motion_bins(history)]
    for region in REGIONS:
        raw=doc[region]["raw_data"]
        if raw.shape!=(32,len(t)):raise ValueError("Expected 32 raw channels with the shared sample clock")
        bins.append(voltage_bins(raw,cutoffs))
    x=np.concatenate(bins,axis=2)
    recent=degrees(history[:,0],history[:,-1])
    future=degrees(history[:,-1],q[cutoffs+200])
    past_ok=np.isfinite(x).all(axis=(1,2))&np.isfinite(recent)
    target_ok=np.isfinite(future)
    keep=past_ok&target_ok
    groups=np.column_stack([np.full(len(cutoffs),person),np.full(len(cutoffs),trial),codes[cutoffs],cutoffs]).astype(int)
    return (x[keep],recent[keep],future[keep],groups[keep]),dict(person=person,trial=trial,frames=len(t),
        candidates=len(keep),invalid_input=int((~past_ok).sum()),invalid_target=int((~target_ok).sum()),eligible=int(keep.sum()))
