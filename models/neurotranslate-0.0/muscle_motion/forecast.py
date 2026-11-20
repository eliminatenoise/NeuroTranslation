"""Time-history and cross-posture controls for forecasts on the stored 256 Hz clock."""
import numpy as np

BASELINES=("persistence","hold_position","velocity16","velocity32","envelope_trend","context_mean")
FITS=("pooled","pooled_no_posture","motion_signal","muscle_signal","walk_only","stand_only",
      "stand_limited","adapted_walk")
POSTURE_FITS=("pooled","motion_signal","muscle_signal")
MUSCLES=["left_tibialis_anterior","left_soleus","left_medial_gastrocnemius","left_peroneus_longus",
         "right_tibialis_anterior","right_soleus","right_medial_gastrocnemius","right_peroneus_longus"]


def amplitude(x):
    return np.sqrt(np.mean(np.square(x),axis=1))


def observations(d,donor=None):
    h=d["sacrum_mm"]-d["sacrum_mm"][:,-1:]
    leg=d["leg_uv"] if donor is None else d["leg_uv"][donor]
    n=len(leg)
    segments=h.reshape(n,8,20,3)
    volt=leg.reshape(n,8,20,8)
    prev=amplitude(leg[:,-64:-32])
    recent=amplitude(leg[:,-32:])
    path=h[:,-32:]-h[:,-33:-32]
    mf=[segments[:,:,-1].reshape(n,-1),(segments[:,:,-1]-segments[:,:,0]).reshape(n,-1)]
    mf.extend(h[:,-1]-h[:,-1-k] for k in (8,16,32,64))
    ef=[volt.mean(axis=2).reshape(n,-1),np.log1p(np.sqrt(np.mean(volt**2,axis=2))).reshape(n,-1),
        np.log1p(recent),np.log1p(prev)]
    return {"previous":prev,"rms":recent,"path":path,"motion":np.column_stack(mf),"emg":np.column_stack(ef),
            "recent":np.column_stack([recent,path.reshape(n,-1)])}


def design(mode,d,v):
    parts=[d["direction"][:,None]]
    if mode!="muscle_signal":parts.append(v["motion"])
    if mode!="motion_signal":parts.append(v["emg"])
    common=np.column_stack(parts)
    if mode in POSTURE_FITS:
        code=2*d["posture"][:,None].astype(float)-1
        return np.column_stack((common,code,common*code))
    return common


def predict(mode,d,v,state,*,keep_rms=None):
    if mode in FITS:
        f=state["fits"][mode]
        x=design(mode,d,v)
        out=v["recent"]+f["bias"]+((x-f["mean"])/f["sd"])@f["coef"]
        if keep_rms is not None:out[:,:8]+=keep_rms-v["rms"]
    else:
        out=v["recent"].copy()
        h=d["sacrum_mm"]
        if mode=="context_mean":
            out=np.stack([state["mean_target"][f"{int(p)}/{int(c)}"] for p,c in zip(d["posture"],d["direction"])])
        elif mode=="hold_position":out[:,8:]=0
        elif mode in ("velocity16","velocity32"):
            k=16 if mode=="velocity16" else 32
            speed=(h[:,-1]-h[:,-1-k])/k
            out[:,8:]=(np.arange(1,33)[None,:,None]*speed[:,None,:]).reshape(len(h),-1)
        elif mode=="envelope_trend":out[:,:8]=2*v["rms"]-v["previous"]
        elif mode!="persistence":raise ValueError("Unknown forecasting method.")
    negatives=(out[:,:8]<0).sum(axis=1)
    out[:,:8]=np.maximum(out[:,:8],0)
    return out,negatives


def numeric(value,shape,label):
    a=np.asarray(value)
    if a.shape!=shape or a.dtype.kind not in "iuf" or not np.isfinite(a).all():
        raise ValueError(f"{label} requires finite recorded numbers with shape {shape}.")
    return a.astype(float)[None]


def forecast(record,state):
    expected={"domain","mode","posture","direction","sacrum_mm","leg_uv"}
    if set(record)!=expected:raise ValueError("Expected domain, mode, posture, direction, sacrum_mm and leg_uv.")
    mode=record["mode"]
    if mode not in (*BASELINES,*FITS):raise ValueError("Choose a supported muscle and motion method.")
    postures={"standing":0,"walking":1};directions={"clockwise":1,"counterclockwise":-1}
    if record["posture"] not in postures or record["direction"] not in directions:
        raise ValueError("Supply the recorded posture and clockwise or counterclockwise visual rotation.")
    d={"posture":np.array([postures[record["posture"]]]),"direction":np.array([directions[record["direction"]]]),
       "sacrum_mm":numeric(record["sacrum_mm"],(160,3),"sacrum_mm"),
       "leg_uv":numeric(record["leg_uv"],(160,8),"leg_uv")}
    with np.errstate(all="ignore"):
        out,count=predict(mode,d,observations(d),state)
    if not np.isfinite(out).all():raise ValueError("Input exceeds the supported numerical range.")
    return {"mode":mode,"stored_horizon_ms":125,"muscle_order":MUSCLES,"future_rms_uv":out[0,:8].tolist(),
            "axes":["mediolateral","superiorinferior","anteriorposterior"],
            "future_path_mm":out[0,8:].reshape(32,3).tolist(),"rms_below_zero_before_bound":int(count[0])}
