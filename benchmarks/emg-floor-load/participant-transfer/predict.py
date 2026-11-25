"""Forecast two-plate impulse and load probability from past EMG history."""

from argparse import ArgumentParser
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn


CHANNELS = ('TibialisAnterior', 'GastrocnemiusMedialis', 'GastrocnemiusLateralis', 'VastusMedialis', 'VastusLateralis', 'RectusFemoris', 'Semitendinosus', 'BicepsFemoris')
METHODS = ('zero', 'ridge', 'direct_1', 'direct_3', 'conditional_linear', 'conditional_1', 'conditional_3')
SEEDS = (20261125, 20261126)
SETTINGS = {'threshold_ns': 1.0, 'quantiles': [0.025, 0.1, 0.25, 0.5, 0.75, 0.9]}


class Forecast(nn.Module):
    """The earlier compact attention block with a load-probability output."""

    def __init__(self, passes, outputs):
        super().__init__()
        self.passes = passes
        self.input = nn.Linear(16,32)
        self.positions = nn.Parameter(torch.zeros(10,32))
        self.block = nn.TransformerEncoderLayer(32,4,64,batch_first=True,
                                                activation='gelu',norm_first=True,dropout=0)
        self.output = nn.Sequential(nn.LayerNorm(32),nn.Linear(32,outputs))

    def forward(self, x):
        hidden = self.input(x) + self.positions
        for _ in range(self.passes):
            hidden = self.block(hidden)
        return self.output(hidden[:,-1])


def mixture_median(p, q, inactive_levels, inactive_quantiles):
    """Take the median of the fitted distribution on either side of the threshold."""
    result = np.empty(len(p),dtype=np.float64)
    active = p > .5
    result[~active] = np.interp(.5/(1-p[~active]),inactive_levels,inactive_quantiles)
    levels = SETTINGS['quantiles']
    threshold = SETTINGS['threshold_ns']
    for row in np.flatnonzero(active):
        result[row] = max(threshold,np.interp(1-.5/p[row],levels,np.sort(q[row])))
    return result


def predict(history, weights):
    """Use ten time bins and eight channels, with NaN marking unavailable bins."""
    history = np.asarray(history,dtype=np.float64)
    if history.ndim!=3 or history.shape[1:]!=(10,8) or len(history)==0:
        raise ValueError('Supply histories with shape (examples, 10, 8).')
    present = np.isfinite(history)
    if np.isinf(history).any() or present[:,:3].any() or not present.any(axis=(1,2)).all():
        raise ValueError('Use NaN for missing values. Leave the first three bins missing.')
    normalized = np.where(present,(history-weights['input_center'])/weights['input_scale'],0.)
    data = np.concatenate((normalized,present.astype(np.float64)),axis=2)
    tensor = torch.from_numpy(data.astype(np.float32))
    columns = np.column_stack((np.ones(len(data)),data.reshape(len(data),-1)))
    forecasts = {'zero':np.zeros(len(data)),'ridge':columns @ weights['ridge_weights']}
    probability = {name:np.full(len(data),float(weights['training_load_rate'])) for name in forecasts}
    target_scale=float(weights['target_scale'])
    with torch.inference_mode():
        for method in METHODS[2:]:
            impulse_members,load_members=[],[]
            conditional=method.startswith('conditional')
            size=1+len(SETTINGS['quantiles']) if conditional else 2
            for seed in SEEDS:
                model=nn.Sequential(nn.Flatten(),nn.Linear(160,size)) if method=='conditional_linear' \
                    else Forecast(int(method[-1]),size)
                prefix=f'{method}.{seed}.'
                model.load_state_dict({
                    name:torch.from_numpy(weights[prefix+name]) for name in model.state_dict()
                })
                model.eval()
                raw = torch.cat([model(part) for part in tensor.split(256)])
                p = raw[:,0].sigmoid().numpy().astype(np.float64)
                values = raw[:,1:].numpy().astype(np.float64)*target_scale
                median = mixture_median(p,values,weights['inactive_quantile_levels'],weights['inactive_quantiles_ns']) \
                    if conditional else values[:,0]
                impulse_members.append(median)
                load_members.append(p)
            forecasts[method]=np.mean(impulse_members,axis=0)
            probability[method]=np.mean(load_members,axis=0)
    return forecasts,probability


def main():
    cli=ArgumentParser(description=__doc__)
    cli.add_argument('input',nargs='?',type=Path,default=Path(__file__).with_name('EXAMPLE.npz'))
    cli.add_argument('--weights',type=Path,default=Path(__file__).with_name('PROSPECTIVE-WEIGHTS.npz'))
    cli.add_argument('--threads',type=int,default=1)
    args=cli.parse_args()
    if args.threads<1:
        cli.error('Choose one or more CPU threads.')
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision('highest')
    torch.use_deterministic_algorithms(True)
    with np.load(args.input,allow_pickle=False) as record:
        if tuple(record['channels'])!=CHANNELS:
            cli.error('The eight channel names and their order must match the guide.')
        history=record['history']
    with np.load(args.weights,allow_pickle=False) as stored:
        estimate,probability=predict(history,dict(stored))
    print(json.dumps({
        'force_quantity':'signed vertical impulse','unit':'N s','forecast_horizon_ms':100,
        'load_probability_threshold_ns':SETTINGS['threshold_ns'],
        'impulse':{name:values.tolist() for name,values in estimate.items()},
        'load_probability':{name:values.tolist() for name,values in probability.items()},
    },indent=2,allow_nan=False))


if __name__=='__main__':
    main()
