"""Forecast a prepared held feature archive, then score its independently revealed labels."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from inference import JointModel
sys.path.insert(0, str(HERE/'controls'))
from predict import predict_all

TASK = 'human_touch_afferent'
KEYS = ('recording', 'trial', 'cutoff_ms')
METHODS = ('joint_true', 'joint_previous', 'touch_only_true', 'touch_only_previous',
           'training_rate', 'phase_and_spikes', 'with_true_force', 'with_previous_repeat_force')

def identity(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while chunk:=f.read(1024*1024):
            h.update(chunk)
    return h.hexdigest()

def predict(features, out):
    with np.load(features,allow_pickle=False) as data:
        if 'y' in data or 'observed' in data:
            raise ValueError('Use the test-features archive before revealing test labels.')
        x, prev = data['X'],data['previous_repeat_force']
        keys={k:data[k] for k in KEYS}
    joint=JointModel.load(HERE/'neurotranslate.npz')
    single=JointModel.load(HERE/'fit/touch-only.npz')
    controls=json.loads((HERE/'controls/pooled-weights.json').read_bytes())
    results=[]
    for i in range(0,len(x),256):
        a=x[i:i+256]
        earlier=prev[i:i+256]
        swapped=a.copy()
        swapped[:,:,:3]=earlier
        predictions=[m.predict(TASK,b).ravel() for m in (joint,single) for b in (a,swapped)]
        simple=predict_all(a,earlier,controls)
        results.append(np.column_stack(predictions+[simple[name].ravel() for name in METHODS[4:]]))
    values=np.concatenate(results)
    if not np.all(np.isfinite(values)&(values>=0)):
        raise ValueError('A predicted count is invalid.')
    with out.open('xb') as f:
        np.savez_compressed(f,**keys,predicted_rate=values,methods=np.array(METHODS))
    print('Prediction SHA-256',identity(out))

def score(predictions,labels):
    with np.load(labels,allow_pickle=False) as data,np.load(predictions,allow_pickle=False) as pred:
        if identity(predictions)!=str(data['prediction_sha256']) or list(pred['methods'])!=list(METHODS):
            raise ValueError('Predictions differ from the frozen label archive.')
        for name in KEYS:
            np.testing.assert_array_equal(pred[name],data[name])
        y=data['y'].reshape(-1)
        rates=pred['predicted_rate']
        roster=json.loads((HERE/'data/touch-roster.json').read_bytes())
        person_by_recording={Path(row['file']).stem:row['person'] for row in roster['recordings'] if row['split']=='test'}
        person=np.array([person_by_recording[stem] for stem in data['recording']])
    result={}
    for code in np.unique(person):
        take=(person==code)&np.isfinite(y)
        if not np.any(take):raise ValueError('One participant has no scored labels.')
        observed=y[take].astype(float)
        r=np.maximum(rates[take],1e-8).astype(float)
        logfact=np.array([math.lgamma(v+1) for v in observed])
        nll=(r-observed[:,None]*np.log(r)+logfact[:,None]).mean(axis=0)
        result[str(code)]=dict(zip(METHODS,nll.tolist()))
    print(json.dumps({'per_person_nll':result,'equal_person_nll':{m:np.mean([p[m] for p in result.values()]).item() for m in METHODS}},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='mode',required=True)
    for name,options in [('predict',('features','output')),('score',('predictions','labels'))]:
        parser=sub.add_parser(name)
        for opt in options:parser.add_argument(opt,type=Path)
    a=p.parse_args()
    if a.mode=='predict':predict(a.features,a.output)
    else:score(a.predictions,a.labels)
