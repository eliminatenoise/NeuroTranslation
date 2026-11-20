"""A small projection introduces recorded voltage summaries into each temporal token."""
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from interface import MUSCLES, fixture
from network import INPUT_KEYS, WIDTH, SharedNet, check_event, tensors
from scalp_inputs import normalize_values

KINDS = ('central', 'reference', 'frontal', 'eye', 'neck')
SITE_NAMES = {
    'central': {'0': ['D19', 'A1', 'B22'], '1': ['C3', 'Cz', 'C4']},
    'frontal': {'0': ['C29', 'C16', None], '1': ['Fp1', 'Fp2', None]},
    'eye': {'0': ['R_horizontal_eog', 'L_horizontal_eog', 'L_vertical_eog'], '1': [None]*3},
    'neck': {'0': ['L_neck_emg', 'R_neck_emg', None], '1': [None]*3},
}


class FusionNet(SharedNet):
    def __init__(self):
        super().__init__()
        self.scalp_patch = nn.Linear(9, WIDTH, bias=False)
        nn.init.zeros_(self.scalp_patch.weight)

    def forward(self, batch, electrical):
        return super().forward(batch, self.scalp_patch(electrical))


def create(seed):
    torch.manual_seed(seed)
    return FusionNet()


def export(model, kind, scales, scalp_scales):
    return dict(format='scalp-muscle-motion-v1', kind=kind, muscles=MUSCLES,
                scales=scales, scalp_scales=scalp_scales, site_names=SITE_NAMES,
                state={k:v.detach().cpu().tolist() for k,v in model.state_dict().items()})


@torch.no_grad()
def predict_batch(model, data, scales, electrical, step=256):
    """Inverse-scale forecast arrays for already constructed input histories."""
    device = next(model.parameters()).device
    rms, path = [], []
    for start in range(0, len(electrical), step):
        rows = slice(start, start+step)
        inputs = {k: data[k][rows] for k in INPUT_KEYS}
        batch = tensors(inputs, scales, device, labels=False)
        extension = torch.as_tensor(electrical[rows], dtype=torch.float32, device=device)
        r, p = model(batch, extension)
        domain = inputs['domain']
        rms.append(r.cpu().numpy()*np.asarray(scales['amp'])[domain])
        path.append(p.cpu().numpy()*np.asarray(scales['xyz'])[domain,None,None])
    return np.concatenate(rms), np.concatenate(path)


def predict_event(weights, event):
    if isinstance(weights, (str, Path)):
        weights = json.loads(Path(weights).read_text())
    kind = weights['kind']
    if (weights['format'] != 'scalp-muscle-motion-v1' or weights['muscles'] != MUSCLES
            or kind not in KINDS or weights['site_names'] != SITE_NAMES):
        raise ValueError('Incompatible checkpoint format, branch or anatomy')
    check_event(event)
    native = np.asarray(event['scalp_values'], dtype=np.float64)
    mask = np.asarray(event['scalp_mask'])
    domain = str(event['domain'])
    branch = 'central' if kind == 'reference' else kind
    slots = np.array([slot is not None for slot in SITE_NAMES[branch][domain]])
    if (native.shape != (20,3,2) or not np.isfinite(native).all() or mask.shape != (3,)
            or mask.dtype != np.bool_ or not mask.any() or (mask & ~slots).any()):
        raise ValueError('Invalid electrical histories or site availability in this study')
    m, r = native[:,:,0], native[:,:,1]
    if (r < 0).any() or (np.abs(m)>r+1e-5*np.maximum(1,r)).any() or np.any(native[:,~mask]):
        raise ValueError('Invalid signed mean, RMS or missing-site placeholder')
    values = normalize_values(native[None], mask[None], np.array([int(domain)]), weights['scalp_scales'], branch)
    if kind == 'reference':
        values.reshape(1,20,3,3)[:,:,:,:2] = 0
    model = FusionNet()
    model.load_state_dict({k:torch.tensor(v, dtype=torch.float32) for k,v in weights['state'].items()})
    data = {k:np.asarray([event[k]]) for k in INPUT_KEYS}
    rms, path = predict_batch(model.eval(), data, weights['scales'], values)
    return dict(rms=[float(x) if valid else None for x,valid in zip(rms[0],event['muscle_mask'])],
                path_mm=path[0].tolist())


def synthetic_event(domain, branch='central'):
    event = fixture(domain)
    names = SITE_NAMES[branch][str(domain)]
    mask = [name is not None and (domain == 1 or index != 1) for index,name in enumerate(names)]
    if not any(mask):
        raise ValueError('This electrical recording is absent in the selected study')
    # Illustrative mathematical summaries, independent of the participant recordings.
    t = np.arange(20)[:,None]
    j = np.arange(3)[None,:]
    amplitude = (1.5 if domain == 0 else 35.) * np.cos(0.38*t+0.7*j)
    values = np.stack([amplitude, np.hypot(amplitude, 1.4*(j+1))], axis=-1)
    values[:,~np.array(mask)] = 0
    return dict(**event, scalp_values=values.tolist(), scalp_mask=mask)
