"""Check serialization, shapes, eligibility and the shared path on fictional examples."""
import argparse
import json
from pathlib import Path

import numpy as np
from inference import JointModel

HERE = Path(__file__).resolve().parent


def rejects(action):
    try:
        action()
    except ValueError:
        return True
    raise AssertionError('Expected an explicit input rejection')


def check(checkpoint, examples):
    model = JointModel.load(checkpoint)
    samples = json.loads(examples.read_text())['examples']
    assert set(samples)==set(model.tasks)
    # Perturb only a shared parameter in memory. Every fitted adapter stays identical.
    changed = JointModel(dict(model.arrays))
    changed.arrays['trunk.v.weight'] = np.zeros_like(model.arrays['trunk.v.weight'])
    report = {}
    for t,r in samples.items():
        x = np.asarray(r['X'],dtype='f')
        output = model.predict(t,x)
        assert np.isfinite(output).all()
        effect = float(np.abs(changed.predict(t,x)-output).max())
        if effect <= 1e-8:
            raise ValueError('No detectable shared-weight influence on '+t)
        rank = model.tasks[t]['kind']=='categorical'
        assert output.shape==(len(x),x.shape[1] if rank else len(model.tasks[t]['outputs']))
        if rank:
            assert np.allclose(output.sum(axis=-1),1.)
            perm = np.arange(x.shape[1])[::-1]
            assert np.allclose(model.predict(t,x[:,perm]),output[:,perm],atol=2e-6)
            padded = np.concatenate((x,np.full_like(x[:,:1],np.nan)),axis=1)
            valid = np.ones(padded.shape[:2],dtype=bool)
            valid[:,-1] = False
            padding_out = model.predict(t,padded,valid)
            assert np.allclose(padding_out[:,:-1],output,atol=2e-6)
            assert (padding_out[:,-1]==0).all()
            rejects(lambda:model.predict(t,padded))
            silent = x.copy()
            silent[:,0] = 0.
            assert (model.predict(t,silent)[:,0]>0).all()
        else:
            rejects(lambda:model.predict(t,np.full_like(x,np.nan)))
            missing = x.copy()
            missing[:,0,0] = np.nan
            assert np.isfinite(model.predict(t,missing)).all()
        rejects(lambda:model.predict(t,np.full_like(x,np.inf)))
        report[t] = {'output_shape':list(output.shape),'shared_weight_perturbation_max_abs_in_output_units':effect}
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,default=HERE/'neurotranslate.npz')
    p.add_argument('--examples',type=Path,default=HERE/'example.json')
    a=p.parse_args()
    print(json.dumps(check(a.checkpoint,a.examples),indent=2))
