"""Forecast the signed change of image-tracked fascicle length from 21 original tracking rows."""
import numpy as np

LEARNED=('linear_length','shared_length','linear_both','shared_both','random_both')
ANGLE_METHODS=('geometry','linear_both','shared_both','random_both')
MODES=('hold','recent','typical','geometry',*LEARNED)
N=21


def projection(length,angle):
    return length*np.cos(np.deg2rad(angle))


def geometry(length,angle):
    x=projection(length[:,[-11,-1]],angle[:,[-11,-1]])
    transverse=length[:,-1]*np.sin(np.deg2rad(angle[:,-1]))
    return np.hypot(2*x[:,1]-x[:,0],transverse)-length[:,-1]


def tokens(length,angle):
    index=np.arange(0,20,5)[:,None]+np.arange(6)
    l=length[:,index];a=angle[:,index]
    li,lf=l[:,:,0],l[:,:,-1];ai,af=a[:,:,0],a[:,:,-1]
    residual=l.mean(axis=2)-.5*(lf+li)
    return np.stack((lf,lf-li,residual,af,af-ai,projection(lf,af)-projection(li,ai)),axis=2)


def design(method,length,angle,fit,encoder,config,linear,encode):
    z=(tokens(length,angle)-fit['token_mean'])/fit['token_sd']
    if method.endswith('_length'):z[:,:,3:]=0
    features=[z.reshape(len(z),24),(length[:,-1]-length[:,-11])[:,None]]
    if not method.startswith('linear'):
        features.append(encode(config,encoder,linear(encoder,'project',z)))
    return np.column_stack(features)


def batch(method,length,angle,state,encoder,random,config,linear,encode):
    recent=length[:,-1]-length[:,-11]
    if method=='hold':return np.zeros(len(length))
    if method=='recent':return np.maximum(recent,-length[:,-1])
    if method=='typical':return np.maximum(np.full(len(length),state['typical']),-length[:,-1])
    if method=='geometry':return geometry(length,angle)
    fit=state['readouts'][method]; w=random if method=='random_both' else encoder
    mat=design(method,length,angle,fit,w,config,linear,encode)
    y=recent+fit['intercept']+((mat-fit['mean'])/fit['sd'])@fit['coef']
    return np.maximum(y,-length[:,-1])


def history(record,name):
    seq=record[name]
    if not isinstance(seq,list) or len(seq)!=N or any(isinstance(v,bool) or not isinstance(v,(float,int)) for v in seq):
        raise ValueError(f'Supply {N} consecutive numeric values for {name}.')
    try:a=np.asarray(seq,dtype=float)
    except OverflowError as exc:raise ValueError('Number outside supported range') from exc
    if not np.isfinite(a).all():raise ValueError('Use finite measurements.')
    if name=='length_mm' and np.any(a<=0):raise ValueError('Tracked lengths must be positive.')
    return a[None,:]


def forecast(record,state,encoder,random,config,linear,encode):
    m=record.get('mode')
    if not isinstance(m,str) or m not in MODES:raise ValueError('Choose a supported muscle tracking method.')
    required={'domain','mode','length_mm'}
    if m in ANGLE_METHODS:required.add('angle_deg')
    if set(record)!=required:raise ValueError('Supply only '+', '.join(sorted(required)))
    length=history(record,'length_mm')
    angle=history(record,'angle_deg') if m in ANGLE_METHODS else np.zeros_like(length)
    with np.errstate(over='ignore',invalid='ignore'):
        delta=float(batch(m,length,angle,state,encoder,random,config,linear,encode)[0])
        predicted=float(length[0,-1]+delta)
    if not np.isfinite([delta,predicted]).all():raise ValueError('Inputs exceed the numerical range.')
    return {'mode':m,'horizon_tracking_steps':10,'signed_length_change_mm':delta,'predicted_length_mm':predicted}
