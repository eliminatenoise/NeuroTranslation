"""Predict stored upward load on the source-assigned right foot plate from four 60 ms bins."""
import numpy as np

OFFSETS=(14,24,34,44)
MODES=('phase','marker_ridge','combined_ridge','marker_shared','combined_shared','scrambled_combined')
COMBINED={'combined_ridge','combined_shared','scrambled_combined'}


def unpack(record):
    from knee.adapter import contains_boolean
    mode=record.get('mode')
    if mode not in MODES:
        raise ValueError('Choose a supported anatomical right-plate model.')
    required={'domain','mode','offset_frames','markers_m'} | ({'emg_uV','emg_valid'} if mode in COMBINED else set())
    if set(record)!=required or record['domain']!='right_plate_force':
        raise ValueError('The input fields must match this right-plate model.')
    off=record['offset_frames']
    if isinstance(off,(bool,np.bool_)) or not isinstance(off,(int,np.integer)) or off not in OFFSETS:
        raise ValueError('Choose an offset of 14, 24, 34 or 44 frames after the annotated right strike.')
    def measurements(name,shape):
        values=record[name];a=np.asarray(values)
        if contains_boolean(values) or a.shape!=shape or a.dtype.kind not in 'fiu' or not np.isfinite(a).all():
            raise ValueError(f'Expected {shape} finite numbers in {name}.')
        return a.astype(np.float64)
    m=measurements('markers_m',(4,6));emg=valid=None
    if mode in COMBINED:
        emg=measurements('emg_uV',(4,8));valid=np.asarray(record['emg_valid'])
        if valid.shape!=(4,8) or valid.dtype.kind not in 'ibu' or not np.isin(valid,[0,1]).all():
            raise ValueError('Each EMG measurement needs one Boolean or 0/1 integer availability flag.')
        if (emg<0).any() or (emg[valid==0]!=0).any():raise ValueError('EMG RMS must be nonnegative and zero wherever unavailable.')
        emg=emg[None];valid=valid[None].astype(float)
    return mode,np.array([OFFSETS.index(int(off))]),m[None],emg,valid


def encoder(w,mode):
    if mode!='scrambled_combined':return w
    keys=sorted(k for k in w if k=='position' or k.startswith(('blocks.','project.','last_norm.')))
    rng=np.random.default_rng(71863)
    return {k:rng.permutation(w[k].ravel()).reshape(w[k].shape) for k in keys}


def design(w,mode,offset,markers,emg,valid,config,linear,encode):
    cols=[markers.reshape(-1,24),np.eye(4)[offset]]
    if mode in COMBINED:cols.extend([np.log1p(emg).reshape(-1,32),valid.reshape(-1,32)])
    if mode in ('marker_shared','combined_shared','scrambled_combined'):
        e=encoder(w,mode)
        z=(markers-w['right_plate.marker_mean'])/w['right_plate.marker_sd']
        cols.append(encode(config,e,linear(e,'project',z)))
    x=np.column_stack(cols)
    if not np.isfinite(x).all():raise ValueError('Input exceeds numerical range for the right-plate readout.')
    return x


def batch(w,mode,offset,markers,emg,valid,config,linear,encode):
    if config.get('right_plate_force',{}).get('format')!=1:raise ValueError('The checkpoint lacks the right-plate readout.')
    if mode=='phase':return w['right_plate.phase'][offset]
    x=design(w,mode,offset,markers,emg,valid,config,linear,encode)
    key='right_plate.'+mode+'.'
    values=(x-w[key+'mean'])/w[key+'sd']@w[key+'coef']+w[key+'bias']
    if not np.isfinite(values).all():raise ValueError('Input exceeds numerical range for the right-plate forecast.')
    return values


def forecast(record,config,weights,linear,encode):
    mode,off,m,e,v=unpack(record);output=batch(weights,mode,off,m,e,v,config,linear,encode)
    return {'right_vertical_plate_force_N':float(output[0]),'mode':mode,'offset_frames':int(record['offset_frames']),
            'stored_hz':100,'lead_frames':10}
