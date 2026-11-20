"""Portable inference on five consecutive completed bins. Requires only NumPy."""
import json
from pathlib import Path
import numpy as np

SESSION = 'C_20170912_COactpas'
FORMAT = 'area2-handle-transformer-v1'
SEEDS = (17, 41, 73)
UNITS = ['ch12:sort1','ch13:sort1','ch16:sort1','ch17:sort1','ch18:sort1','ch24:sort1',
         'ch25:sort1','ch27:sort1','ch27:sort2','ch29:sort1','ch35:sort1','ch35:sort2',
         'ch37:sort1','ch39:sort1','ch49:sort1','ch52:sort1','ch52:sort2','ch53:sort1',
         'ch55:sort1','ch56:sort1','ch58:sort1','ch61:sort1','ch62:sort1','ch65:sort1',
         'ch67:sort1','ch70:sort1','ch72:sort1','ch73:sort1','ch90:sort1','ch92:sort1']
BLOCKS = {'movement': slice(0,4), 'neural':slice(4,34), 'cue':slice(34,41)}
MODES = {'all': tuple(BLOCKS), 'movement_cue':('movement','cue'), 'neural_cue':('neural','cue'),
         'cue_only':('cue',), 'movement_only':('movement',), 'neural_only':('neural',)}
SHAPES = {'position':(5,16)}
for name, widths in {'embed':(16,41),'qkv':(48,16),'project':(16,16),'expand':(32,16),
                     'reduce':(16,32),'readout':(2,16)}.items():
    SHAPES[name+'.weight'] = widths
    SHAPES[name+'.bias'] = (widths[0],)
for name in ('attn_norm','ff_norm','final_norm'):
    for suffix in ('.weight','.bias'):
        SHAPES[name+suffix]=(16,)

def array(value, shape, label):
    # Check raw scalar types before NumPy silently promotes mixed booleans to numbers.
    if isinstance(value, (list,tuple)) and np.asarray(value,dtype=object).size:
        if any(type(v) not in (int,float) for v in np.asarray(value,dtype=object).flat):
            raise ValueError(f'{label}: numeric array required')
    a=np.asarray(value)
    if a.dtype.kind not in 'ifu' or a.shape!=shape or not np.isfinite(a).all():
        raise ValueError(f'{label}: expected finite real array of shape {shape}')
    return a.astype(np.float64,copy=False)

def validate_cues(cue):
    for col in (0,3,6):
        flag=cue[...,col]
        if not np.isin(flag,[0,1]).all() or (flag[...,1:]<flag[...,:-1]).any():
            raise ValueError('cue availability must be binary and nondecreasing')
        if col==6:
            continue
        xy=cue[...,col+1:col+3]
        if (xy[flag==0]!=0).any() or (np.abs(np.linalg.norm(xy[flag==1],axis=-1)-1)>1e-5).any():
            raise ValueError('unknown directions must be zero; known ones must be unit vectors')
        if (np.abs(np.diff(xy,axis=-2))[flag[...,:-1]==1]>1e-5).any():
            raise ValueError('known direction changed within the five tokens')

def validate_block(name, a):
    if name=='cue':
        validate_cues(a)
    if name=='neural' and ((a<0).any() or np.any(a!=np.floor(a)) or (a>2**53-1).any()):
        raise ValueError('neural entries must be nonnegative safe integers')

def decode_weights(w):
    if (w.get('format')!=FORMAT or w.get('session')!=SESSION or w.get('mode') not in MODES or
            w.get('seed') not in SEEDS or w.get('unit_ids')!=UNITS):
        raise ValueError('unknown weights format, mode, seed, session or unit order')
    if set(w['parameters'])!=set(SHAPES):
        raise ValueError('unexpected parameter keys')
    p={name:array(w['parameters'][name],shape,name) for name,shape in SHAPES.items()}
    for name, shape in [('x_mean',(41,)),('x_scale',(41,)),('y_mean',(2,)),('y_scale',())]:
        p[name]=array(w[name],shape,name)
    if np.any(p['x_scale']<=0) or p['y_scale']<=0:
        raise ValueError('scale must be positive')
    return p

def history_array(history, mode):
    if history.get('session')!=SESSION:
        raise ValueError('session mismatch')
    x=np.zeros((5,41))
    for name,index in BLOCKS.items():
        if name not in history:
            if name in MODES[mode]:
                raise ValueError(f'missing required history: {name}')
            continue
        if name=='neural' and history.get('unit_ids')!=UNITS:
            raise ValueError('recording or unit order differs')
        a=array(history[name],(5,index.stop-index.start),name)
        validate_block(name,a)
        x[:,index]=a
    return x

def mask(mode):
    keep=np.zeros(41,dtype=bool)
    for name in MODES[mode]:
        keep[BLOCKS[name]]=True
    return keep

def forward(raw, p, mode):
    """Batched internal kernel. Call predict for checked public input."""
    x=np.clip((raw-p['x_mean'])/p['x_scale'],-8.,8.) * mask(mode)
    def linear(h,name):
        return h @ p[name+'.weight'].T+p[name+'.bias']
    def norm(h,name):
        centered=h-h.mean(axis=-1,keepdims=True)
        return centered/np.sqrt((centered**2).mean(axis=-1,keepdims=True)+1e-5)*p[name+'.weight']+p[name+'.bias']
    h=linear(x,'embed')+p['position']
    q,k,v=linear(norm(h,'attn_norm'),'qkv').reshape(-1,5,3,2,8).transpose(2,0,3,1,4)
    a=(q @ k.swapaxes(-1,-2)) / np.sqrt(8.)
    a=np.exp(a-a.max(axis=-1,keepdims=True))
    attended=((a/a.sum(axis=-1,keepdims=True)) @ v).transpose(0,2,1,3).reshape(-1,5,16)
    h=h+linear(attended,'project')
    h=h+linear(np.maximum(linear(norm(h,'ff_norm'),'expand'),0),'reduce')
    result=linear(norm(h[:,-1],'final_norm'),'readout')*p['y_scale']+p['y_mean']
    if not np.isfinite(result).all():
        raise ValueError('nonfinite forecast')
    return result

def predict(weights, history):
    """Return the next 100-ms [dx,dy] in native handle centimetres."""
    p=decode_weights(weights)
    return forward(history_array(history,weights['mode'])[None],p,weights['mode'])[0].tolist()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('weights',type=Path)
    parser.add_argument('history',type=Path)
    args=parser.parse_args()
    print(json.dumps(predict(json.loads(args.weights.read_text()),json.loads(args.history.read_text()))))
