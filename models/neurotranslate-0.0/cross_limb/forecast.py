"""Frame-equivariant, unit-respecting temporal baselines for two movement studies."""
import numpy as np

LEG=tuple(side+" "+m for side in ("left","right") for m in
          ("tibialis anterior","soleus","medial gastrocnemius","peroneus longus"))
ARM=tuple("right "+m for m in ("anterior deltoid","brachioradialis","flexor digitorum",
                                "common extensor digitorum","first dorsal interosseous"))
CHANNELS=LEG+ARM
FITS=("pooled","leg","arm","leg_limited","arm_limited","arm_to_leg","leg_to_arm")
BASELINES=("hold_still","hold_repeat","hold_velocity","context_mean")


def prepared(d):
    m=d["muscle_mask"].astype(bool)
    a=np.where(m[:,None,:],d["patch_rms"],0.)
    scales=np.sqrt(np.mean(a*a,axis=1))
    active=m&(scales>0)
    ratios=np.divide(a,scales[:,None,:],out=np.zeros_like(a),where=active[:,None,:])
    across=(ratios*m[:,None,:]).sum(axis=2)/m.sum(axis=1)[:,None]
    h=d["patch_xyz_mm"]
    step=np.diff(h,axis=1)
    scale=4*np.sqrt(np.mean(np.sum(step**2,axis=2),axis=1))
    moving=scale>=1e-8
    vectors=h[:,-1,None,:]-h[:,[-2,-3,-5,-9,-17],:]
    basis=np.divide(vectors,scale[:,None,None],out=np.zeros_like(vectors),where=moving[:,None,None])
    descriptors=np.linalg.norm(basis,axis=2)
    count=len(h)
    common=np.column_stack((np.ones(count),across,descriptors))
    xm=np.concatenate((ratios.transpose(0,2,1),np.broadcast_to(common[:,None,:],(count,len(CHANNELS),common.shape[1]))),axis=2)
    def aggregate(q):
        return (np.sqrt(np.mean(q*q,axis=1))*m).sum(axis=1)/m.sum(axis=1)
    mult=np.column_stack((np.ones(count),aggregate(ratios[:,-4:]),aggregate(ratios[:,-8:-4])))
    xp=(basis[:,:,:,None]*mult[:,None,None,:]).transpose(0,2,1,3).reshape(count,3,15)
    return {"muscle_x":xm,"path_x":xp,"scale":scales,"moving":moving,"active":active,
            "path_scale":scale,"hold":np.sqrt(np.mean(a[:,-4:]*a[:,-4:],axis=1))}


def context_key(domain,session,direction):
    return f"balance/{int(session)}/{int(direction)}" if domain==0 else "grasp_lift"


def estimate(mode,d,v,state,hold_override=None):
    count=len(d["domain"]);clip=np.zeros(count,int)
    if mode=="context_mean":
        vals=[state["means"][context_key(dom,pose,cue)] for dom,pose,cue in zip(d["domain"],d["session"],d["direction"])]
        rms=np.asarray([t["rms"] for t in vals]);path=np.asarray([t["path"] for t in vals])
    elif mode in BASELINES:
        rms=v["hold"].copy();prev=d["repeat_path_mm"]
        if mode=="hold_still":path=np.zeros_like(prev)
        elif mode=="hold_velocity":path=prev[:,-1:,:]*np.arange(1,33)[None,:,None]/32
        else:path=prev.copy()
    else:
        fit=state["fits"][mode];base=v["hold"] if hold_override is None else hold_override
        rms=base+(v["muscle_x"]@fit["muscle_coef"])*v["scale"]
        clip=((rms<0)&d["muscle_mask"]).sum(axis=1)
        rms=np.maximum(rms,0)
        path=d["repeat_path_mm"]+(v["path_x"]@fit["path_coef"]).transpose(0,2,1)*v["path_scale"][:,None,None]
    return np.where(d["muscle_mask"],rms,0.),path,clip


def finite(value,shape,name):
    a=np.asarray(value)
    if a.shape!=shape or a.dtype.kind not in "iuf" or not np.isfinite(a).all():
        raise ValueError(f"{name} needs finite numerical values with shape {shape}.")
    return a.astype(float)


def forecast(record,state):
    keys={"domain","study","mode","context","channel_names","patch_rms","patch_xyz_mm","repeat_path_mm","age_s"}
    if set(record)!=keys:raise ValueError("Expected "+", ".join(sorted(keys))+".")
    study=record["study"];mode=record["mode"]
    if study not in ("balance","grasp_lift") or mode not in (*FITS,*BASELINES):raise ValueError("Choose a supported study and method.")
    upper=study=="grasp_lift";allowed=ARM if upper else LEG
    names=record["channel_names"]
    if not isinstance(names,list) or not all(isinstance(n,str) and n in allowed for n in names):
        raise ValueError("Supply source-qualified muscle names for this study.")
    if len(set(names))!=len(names) or len(names)<(3 if upper else 8):raise ValueError("Duplicate or insufficient named muscle channels.")
    ctx=record["context"]
    if upper and ctx!="led_grasp_lift":raise ValueError("The grasp-and-lift context is led_grasp_lift.")
    if not upper and ctx not in ("standing_cw","standing_ccw","walking_cw","walking_ccw"):
        raise ValueError("Select the standing or walking visual rotation.")
    a=finite(record["patch_rms"],(20,len(names)),"patch_rms")
    if (a<0).any():raise ValueError("RMS amplitudes must be nonnegative.")
    age=finite(record["age_s"],(20,),"age_s")
    if (age < -1e-9).any() or (age >= 1/(500 if upper else 256)+1e-9).any():raise ValueError("A position is too old or comes from the future.")
    q=finite(record["patch_xyz_mm"],(20,3),"patch_xyz_mm")
    if not np.allclose(q[-1],0.,rtol=0,atol=1e-6):raise ValueError("Positions must be relative to the final observed marker.")
    path=finite(record["repeat_path_mm"],(32,3),"repeat_path_mm")
    idx=[CHANNELS.index(n) for n in names];a_full=np.zeros((20,13));a_full[:,idx]=a;m=np.zeros((1,13),bool);m[0,idx]=True
    d={"patch_rms":a_full[None],"muscle_mask":m,"patch_xyz_mm":q[None],"repeat_path_mm":path[None],
       "domain":np.array([int(upper)]),"session":np.array([1 if not upper and ctx.startswith("walking") else 0]),
       "direction":np.array([0 if upper else (-1 if ctx.endswith("ccw") else 1)])}
    with np.errstate(all="ignore"):amplitudes,positions,clip=estimate(mode,d,prepared(d),state)
    if not np.isfinite(amplitudes).all() or not np.isfinite(positions).all():raise ValueError("Input exceeds the supported numerical range.")
    return {"mode":mode,"study":study,"muscle_names":names,"rms_unit":"WAY native amplitude" if upper else "µV",
            "future_rms":amplitudes[0,idx].tolist(),"marker":"right wrist" if upper else "sacrum",
            "axes":["Polhemus X","Polhemus Y","Polhemus Z"] if upper else ["mediolateral","superiorinferior","anteriorposterior"],
            "future_path_mm":positions[0].tolist(),"stored_horizon_ms":125,"clipped_amplitudes":int(clip[0])}
