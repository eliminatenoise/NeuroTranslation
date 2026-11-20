"""Angle-only input encoding and portable knee turning-moment forecasts."""
import numpy as np

MODES=('mean','ridge','shared','scrambled','trained')
CHANNELS=('right_knee','left_knee','right_hip','left_hip','right_ankle','left_ankle')
LAGS=range(75,301)
SNAPSHOTS=np.arange(359,400,5)


def valid_history(frames,angles):
    from knee.adapter import contains_boolean
    if contains_boolean(frames) or contains_boolean(angles):
        raise ValueError('Supply numbers for frame indices and angles.')
    f=np.asarray(frames); a=np.asarray(angles)
    if f.ndim==1 and a.ndim==2:
        f=f[None];a=a[None]
    if (a.ndim!=3 or a.shape[1:]!=(400,6) or not len(a) or f.shape!=a.shape[:2]
            or f.dtype.kind not in 'iu' or a.dtype.kind not in 'fiu'):
        raise ValueError('Expected 400 consecutive integer frames with six angles in degrees at every frame.')
    if (f<0).any() or (f>=2**53).any() or (np.diff(f.astype(np.int64),axis=1)!=1).any():
        raise ValueError('Frame numbers must be nonnegative, consecutive and below 2^53.')
    if not np.isfinite(a).all() or np.any(a==0):
        raise ValueError('A zero or nonfinite angle is ineligible under this source protocol.')
    return a.astype(np.float64,copy=False)


def periods(history):
    knees=history[:,:,:2]
    with np.errstate(over='ignore',invalid='ignore'):
        costs=np.column_stack([np.square(knees[:,-100:]-knees[:,-100-p:-p]).sum(axis=(1,2)) for p in LAGS])
    if not np.isfinite(costs).all():
        raise ValueError('The angles exceed the numeric range of the stride comparison.')
    return np.argmin(costs,axis=1)+LAGS.start


def features(history,p):
    i=np.arange(len(p))
    bins=history[:,-100:].reshape(-1,4,25,6).mean(axis=2)
    snap=history[:,SNAPSHOTS].reshape(-1,54)
    raw=np.column_stack((snap,history[i,399+25-p],history[i,399+20-p],
                         history[:,-1]-history[i,399-p],p,bins.reshape(-1,24)))
    if not np.isfinite(raw).all() or not np.isfinite(bins).all():
        raise ValueError('The angle history exceeds the numeric range of the motion features.')
    return raw,bins


def encoder_weights(w,mode):
    select=sorted(n for n in w if n=='position' or n.startswith(('project.','blocks.','last_norm.')))
    if mode=='scrambled':
        rng=np.random.default_rng(4281)
        return {n:rng.permutation(w[n].ravel()).reshape(w[n].shape) for n in select}
    if mode=='trained':
        return {n:w['load.trained.'+n] for n in select}
    return w


def states(config,w,z,linear,encode):
    return encode(config,w,linear(w,'project',z),all_tokens=True)


def readout(w,mode,x):
    key='load.'+mode+'.'
    return (x-w[key+'mean'])/w[key+'sd']@w[key+'coef']+w[key+'bias']


def from_features(mode,raw,bins,config,w,linear,encode,encoder=None):
    if mode not in MODES:raise ValueError('Unknown knee-moment mode')
    if mode=='mean':return np.broadcast_to(w['load.target_mean'],(len(raw),2)).copy()
    if mode=='ridge':return readout(w,mode,raw)
    z=(bins-w['load.bin_mean'])/w['load.bin_sd']
    hidden=states(config,encoder if encoder is not None else encoder_weights(w,mode),z,linear,encode)
    if mode=='trained':
        return readout(w,'ridge',raw)+linear(w,'load.trained.readout',hidden[:,-1])*w['load.target_sd']
    return readout(w,mode,np.column_stack((raw,hidden.reshape(len(raw),-1))))


def forecast(frames,angles,mode,config,w,linear,encode):
    if mode not in MODES or config.get('knee_moment',{}).get('format')!=1:
        raise ValueError('Expected a supported knee-moment mode and fitted checkpoint.')
    histories=valid_history(frames,angles);values=[];period_list=[]
    encoder=encoder_weights(w,mode) if mode in ('shared','scrambled','trained') else None
    for i in range(0,len(histories),64):
        x=histories[i:i+64]; period=periods(x);raw,bins=features(x,period)
        y=from_features(mode,raw,bins,config,w,linear,encode,encoder)
        if not np.isfinite(y).all(): raise ValueError('Knee-moment forecast exceeded the numeric range.')
        values.append(y);period_list.append(period)
    return np.concatenate(values),np.concatenate(period_list)
