"""Forecast a 100-sample change in the original pedal sensor output."""
import numpy as np

SETTINGS=('angle0','angle5')
READOUT=('relaxation_setting','relaxation_emg','linear_load','linear_both','shared_load_no_setting','shared_load','shared_both','random_both')
METHODS=('hold','recent','setting_median',*READOUT)
USES_EMG=('relaxation_emg','linear_both','shared_both','random_both')
FRACTION=float(-np.expm1(-100./150.))


def electrical(emg):
    """Six temporal summaries from a finite, retrospective 201-sample input history."""
    rect=np.abs(emg)
    envelopes=[]
    for tau in (25.,80.):
        alpha=-np.expm1(-1./tau)
        filt=np.empty_like(rect);filt[:,0]=rect[:,0]
        for i in range(1,rect.shape[1]):
            filt[:,i]=filt[:,i-1]+alpha*(rect[:,i]-filt[:,i-1])
        envelopes.append(filt)
    return rect,*envelopes


def summaries(load,emg):
    rect,fast,slow=electrical(emg)
    indices=50*np.arange(4)[:,None]+np.arange(51)
    raw=load[:,indices];end=raw[:,:,-1];start=raw[:,:,0]
    tokens=np.stack((end,end-start,raw.mean(axis=2)-(end+start)/2,
                     fast[:,indices[:,-1]],slow[:,indices[:,-1]],rect[:,indices].mean(axis=2)),axis=2)
    dynamics=np.column_stack((fast[:,-1],slow[:,-1],fast[:,-1]-fast[:,-101],slow[:,-1]-slow[:,-101]))
    return tokens,dynamics


def features(mode,tokens,dynamics,recent,setting,fit,encoder,config,linear,encode):
    if mode.startswith('relaxation'):
        return setting[:,None] if mode=='relaxation_setting' else np.column_stack((setting,dynamics))
    z=(tokens-fit['token_mean'])/fit['token_sd']
    if mode not in USES_EMG:z[:,:,3:]=0.
    condition=np.zeros_like(setting) if mode=='shared_load_no_setting' else setting
    parts=[z.reshape(len(z),24),recent[:,None],condition[:,None]]
    if not mode.startswith('linear'):parts.append(encode(config,encoder,linear(encoder,'project',z)))
    return np.column_stack(parts)


def batch(mode,load,setting,tokens,dynamics,state,encoder,random,cfg,linear,encode):
    recent=load[:,-1]-load[:,-101]
    if mode=='hold':return np.zeros(len(load))
    if mode=='recent':return recent
    if mode=='setting_median':return np.where(setting==1,state['medians']['angle5'],state['medians']['angle0'])
    fit=state['fits'][mode]
    matrix=features(mode,tokens,dynamics,recent,setting,fit,random if mode=='random_both' else encoder,cfg,linear,encode)
    adjusted=fit['intercept']+((matrix-fit['mean'])/fit['sd'])@fit['coef']
    if mode.startswith('relaxation'):return FRACTION*(adjusted-load[:,-1])
    return recent+adjusted


def signal(record,name):
    x=record[name]
    if not isinstance(x,list) or len(x)!=201 or any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in x):
        raise ValueError(f'{name} needs 201 chronological numbers.')
    try:a=np.asarray(x,dtype=float)
    except OverflowError as e:raise ValueError('Value exceeds the supported numerical range.') from e
    if not np.isfinite(a).all():raise ValueError('All inputs must be finite.')
    return a[None,:]


def forecast(record,state,encoder,random,cfg,linear,encode):
    mode=record.get('mode')
    if not isinstance(mode,str) or mode not in METHODS:raise ValueError('Choose a supported pedal-load method.')
    keys={'domain','mode','load'}
    if mode not in ('hold','recent','shared_load_no_setting'):keys.add('setting')
    if mode in USES_EMG:keys.add('emg')
    if set(record)!=keys:raise ValueError('Inputs required for this method: '+', '.join(sorted(keys)))
    name=record.get('setting','angle0')
    if name not in SETTINGS:raise ValueError('Choose angle0 or angle5.')
    load=signal(record,'load');emg=signal(record,'emg') if 'emg' in keys else np.zeros_like(load)
    with np.errstate(over='ignore',invalid='ignore'):
        tok,dyn=summaries(load,emg)
        delta=float(batch(mode,load,np.asarray([int(name=='angle5')]),tok,dyn,state,encoder,random,cfg,linear,encode)[0])
        later=float(load[0,-1]+delta)
    if not np.isfinite([delta,later]).all():raise ValueError('Numbers exceed forecast range.')
    return {'mode':mode,'horizon_sample_positions':100,'nominal_horizon_ms':100,
            'signed_load_change_native':delta,'later_load_native':later}
