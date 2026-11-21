"""NumPy inference for NeuroTranslate 0.0. One checkpoint serves every task."""
import argparse
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent


def standardize(x, mean, scale):
    observed = np.isfinite(x)
    z = np.where(observed, (x - mean) / scale, 0.).astype('f')
    return np.concatenate((z, observed.astype('f')), axis=-1)


def softmax(x, axis):
    exp = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return exp / exp.sum(axis=axis, keepdims=True)


class JointModel:
    def __init__(self, arrays):
        self.arrays = arrays
        self.tasks = json.loads(str(arrays['schemas']))
        self.version = str(arrays['version'])
        self.architecture = json.loads(str(arrays['architecture'])) if 'architecture' in arrays else dict(width=32,heads=4,depth=1,ff_width=64)

    @classmethod
    def load(cls, path=HERE / 'neurotranslate.npz'):
        with np.load(path, allow_pickle=False) as archive:
            return cls({name: archive[name] for name in archive.files})

    def _linear(self, x, name):
        return x @ self.arrays[name + '.weight'].T + self.arrays[name + '.bias']

    def _layer_norm(self, x, name):
        centered = x - x.mean(axis=-1, keepdims=True)
        norm = centered / np.sqrt((centered * centered).mean(axis=-1, keepdims=True) + 1e-5)
        return norm * self.arrays[name + '.weight'] + self.arrays[name + '.bias']

    def predict(self, task, X, valid=None):
        if task not in self.tasks:
            raise ValueError('Unsupported task ' + str(task))
        schema = self.tasks[task]
        x = np.asarray(X, dtype='f')
        rank = schema['kind'] == 'categorical'
        expected = (schema['history_steps'], len(schema['channels']))
        if x.ndim != (4 if rank else 3) or x.shape[-2:] != expected or x.shape[0] < 1:
            raise ValueError(f'Expected a batch with trailing history and channel shape {expected}')
        if np.any(np.isinf(x)):
            raise ValueError('Use null or NaN to mark missing observations')
        shape = x.shape
        if rank:
            if shape[1] < 1:
                raise ValueError('At least one candidate is required')
            observed_candidate = np.isfinite(x).any(axis=(-1,-2))
            if valid is None:
                valid = np.ones(shape[:2],dtype=bool)
            valid = np.asarray(valid)
            if valid.dtype != np.dtype(bool) or valid.shape != shape[:2] or not valid.any(axis=1).all():
                raise ValueError('Each case needs a boolean mask and at least one eligible candidate')
            if np.any(valid & ~observed_candidate):
                raise ValueError('An eligible candidate lacks all observed history; provide its observations or abstain')
        elif not np.isfinite(x).any(axis=(-1,-2)).all():
            raise ValueError('A forecast needs at least one observed history value in every case')
        elif valid is not None:
            raise ValueError('Candidate masks apply only to ranking tasks')
        x = x.reshape(-1, *expected)
        a = self.arrays
        x = standardize(x, a[task+'.xmean'], a[task+'.xscale'])
        x = self._linear(x, 'adapters.'+task)
        n, t, d = x.shape
        h = self.architecture['heads']
        omega = np.exp(np.arange(0, d, 2, dtype='f') * (-np.log(10000.) / d)).astype('f')
        phase = np.arange(1-t, 1, dtype='f')[:, None] * omega
        x = x + np.stack((np.sin(phase), np.cos(phase)), axis=-1).reshape(t,d)
        z = x[:,-1]
        for i in range(self.architecture['depth']):
            prefix = 'trunk.' if i==0 else f'trunk.extra.{i-1}.'
            memory = np.concatenate((np.broadcast_to(a[prefix+'null'], (n,1,d)), x), axis=1)
            q = self._linear(z, prefix+'q').reshape(n,h,d//h)
            k = self._linear(memory, prefix+'k').reshape(n,t+1,h,d//h)
            v = self._linear(memory, prefix+'v').reshape(n,t+1,h,d//h)
            attn = softmax((q[:,None]*k).sum(axis=-1) / np.float32(np.sqrt(d//h)), axis=1)
            pooled = (attn[...,None]*v).sum(axis=1).reshape(n,d)
            z = self._layer_norm(z+self._linear(pooled,prefix+'proj'),prefix+'ln1')
            z = self._layer_norm(z+self._linear(np.maximum(self._linear(z,prefix+'ff1'),0),prefix+'ff2'),prefix+'ln2')
        out = self._linear(z, 'outputs.'+task)
        if rank:
            prediction = softmax(np.where(valid,out.reshape(shape[:2]),-np.inf),axis=1)
        elif schema['kind']=='count':
            prediction = a[task+'.ymean']*np.exp(np.clip(out,-10.,10.))
        else:
            prediction = out*a[task+'.yscale']+a[task+'.ymean']
            if schema.get('output_bound')=='nonnegative':
                prediction = np.maximum(prediction,0.)
        if not np.isfinite(prediction).all():
            raise ValueError('Input magnitude exceeds the model numerical range')
        return prediction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, default=HERE/'neurotranslate.npz')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--list', action='store_true')
    actions.add_argument('--example', action='store_true')
    actions.add_argument('--input', type=Path, help='JSON object with task, X and optional valid')
    args = parser.parse_args()
    model = JointModel.load(args.checkpoint)
    if args.list:
        print(json.dumps(model.tasks, indent=2))
        return
    if args.input:
        rows = [json.loads(args.input.read_text())]
    else:
        rows = list(json.loads((HERE/'example.json').read_text())['examples'].values())
    result = [{ 'task': r['task'], 'prediction': model.predict(**r).tolist()} for r in rows]
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
