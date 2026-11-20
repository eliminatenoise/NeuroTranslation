"""Participant-balanced native-unit outcomes with explicit channel denominators."""
import numpy as np
from interface import MUSCLES

PRIMARY=('muscle_mae','path_mean_distance_mm','endpoint_distance_mm')
FIELDS=PRIMARY+tuple('mae '+m for m in MUSCLES)+tuple('bias '+m for m in MUSCLES)+('axis0_bias_mm','axis1_bias_mm','axis2_bias_mm')


def event_errors(data,idx,r,p,mask=None):
    masks=data['muscle_mask'][idx] if mask is None else mask
    rm=np.where(masks,np.asarray(r)-data['future_rms'][idx],np.nan)
    pp=np.asarray(p)-data['future_path_mm'][idx]
    dist=np.linalg.norm(pp,axis=-1)
    return np.column_stack((np.nansum(np.abs(rm),axis=1)/masks.sum(1),dist.mean(1),dist[:,-1],np.abs(rm),rm,pp.mean(1)))


def finite_mean(a,axis=0):
    n=np.isfinite(a).sum(axis=axis)
    return np.divide(np.nansum(a,axis=axis),n,out=np.full(np.shape(n),np.nan),where=n>0)


def aggregate(data,idx,errors,domain,posture=None,session_detail=True):
    who=data['person'][idx]
    session=data['session'][idx]
    direction=data['direction'][idx]
    individuals=[]
    eligible=[]
    event_count=0
    denominators=np.zeros(len(FIELDS),dtype=int)
    for p in np.unique(who):
        owns=who==p
        if domain==0:
            sessions=(0,1) if posture is None else (posture,)
            cells=[owns&(session==s)&(direction==cue) for s in sessions for cue in (-1,1)]
        else:
            sessions=sorted(set(session[owns])) if posture is None else (posture,)
            cells=[owns&(session==s) for s in sessions]
        if not cells or not all(cell.any() for cell in cells): continue
        individuals.append(finite_mean(np.array([finite_mean(errors[cell]) for cell in cells])))
        eligible.append(p)
        accepted=np.any(cells,axis=0)
        event_count+=int(accepted.sum())
        denominators+=np.isfinite(errors[accepted]).sum(axis=0)
    rows=np.asarray(individuals).reshape(-1,len(FIELDS))
    means=finite_mean(rows) if len(rows) else np.full(len(FIELDS),np.nan)
    scores={key:float(val) for key,val in zip(FIELDS,means) if np.isfinite(val)}
    public=dict(people=len(rows),events=event_count,scores=scores,
                channel_counts={m:dict(events=int(denominators[3+j]),people=int(np.isfinite(rows[:,3+j]).sum()))
                                for j,m in enumerate(MUSCLES) if (j<8)==(domain==0)})
    if session_detail and posture is None:
        # For lower posture views retain the same paired people as the pooled result.
        keep=np.isin(who,eligible)
        public['by_session']={str(int(s)):aggregate(data,idx[keep],errors[keep],domain,int(s),False)[0]
                              for s in sorted(set(session[keep]))}
    return public,(np.array(eligible),rows)


def compare(pair_a,pair_b,seed=1641):
    ap,a=pair_a
    bp,b=pair_b
    if not np.array_equal(ap,bp): raise ValueError('Different participants in paired contrast')
    if not len(ap): return dict(people=0,differences={})
    delta=a[:,:3]-b[:,:3]
    rng=np.random.default_rng(seed)
    # Different domains use different group sizes; resampling never links people between studies.
    draw=rng.integers(len(ap),size=(5000,len(ap)))
    intervals=np.percentile(delta[draw].mean(1),[2.5,97.5,98.75],axis=0)
    return dict(people=len(ap),differences={key:dict(mean=float(delta[:,k].mean()),ci95=intervals[:2,k].tolist(),
           upper98_75=float(intervals[2,k]),people_lower=int((delta[:,k]<0).sum())) for k,key in enumerate(PRIMARY)})
