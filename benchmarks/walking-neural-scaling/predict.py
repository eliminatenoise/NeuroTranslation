"""Run a 100 ms forecast from a 200 ms window of recorded muscle and floor force."""

import argparse
import json
from pathlib import Path

import numpy as np


CHECKPOINTS = Path(__file__).resolve().parent / 'checkpoints'


def read_json(path):
    return json.loads(path.read_text())


def model_session(filename):
    import onnxruntime as ort

    config = ort.SessionOptions()
    config.intra_op_num_threads = 1
    config.inter_op_num_threads = 1
    return ort.InferenceSession(str(CHECKPOINTS / filename), sess_options=config, providers=['CPUExecutionProvider'])


def tree_features(history, available, settings):
    center, scale = np.asarray(settings['center']), np.asarray(settings['scale'])
    scaled = np.where(available, (history - center) / scale, 0.)
    encoded = np.concatenate((scaled, available), axis=-1)
    baseline = np.where(available[:, -1, 6], history[:, -1, 6] * .1, settings['missing_force_fallback_ns'])
    values = np.column_stack((encoded.reshape(len(history), -1), scaled[:, -1], scaled.mean(axis=1),
                              scaled[:, -1] - scaled[:, 0], baseline))
    return values.astype(np.float32), baseline


def recurrent_features(emg, force):
    known, force_known = np.isfinite(emg), np.isfinite(force)
    strength = np.where(known, np.square(emg), 0.)
    sum_strength = np.cumsum(strength, axis=1)[:, 2:-1]
    count = np.cumsum(known, axis=1)[:, 2:-1]
    baseline = np.sqrt(sum_strength / np.maximum(count, 1))
    usable = (count >= 3) & (baseline > 1e-12) & known[:, 3:]
    change = np.log1p(np.divide(emg[:, 3:], baseline, out=np.zeros_like(baseline), where=usable))
    summaries = np.zeros((len(force), 10, 2))
    present = np.zeros_like(force_known)
    for row, tick in np.ndindex(usable.shape[:2]):
        values = change[row, tick, usable[row, tick]]
        if values.size:
            summaries[row, tick + 3] = np.quantile(values, [.5, .8])
            present[row, tick + 3] = True
    return np.concatenate((np.where(force_known, force / 800., 0.)[..., None], summaries,
                           force_known[..., None], present[..., None]), axis=-1).astype(np.float32)


def recurrent_model():
    import torch
    from safetensors.torch import load_file
    from torch import nn
    from torch.nn import functional as F

    class ThreePass(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = nn.Conv1d(5, 24, 3)
            self.recurrent = nn.GRU(24, 24, batch_first=True)
            self.shared_step = nn.GRUCell(24, 24)
            self.out = nn.Linear(24, 2)

        def forward(self, inputs):
            encoded = F.silu(self.conv(F.pad(inputs.transpose(1, 2), (2, 0)))).transpose(1, 2)
            outputs, _ = self.recurrent(encoded)
            summary = outputs[:, -1]
            state = summary
            for _ in range(3):
                state = self.shared_step(summary, state)
            return self.out(state)

    model = ThreePass().eval()
    model.load_state_dict(load_file(CHECKPOINTS / 'three-pass.safetensors', device='cpu'), strict=True)
    return model


def run_recurrent(model, values, baseline, prior):
    import torch

    with torch.inference_mode():
        corrections = model(torch.from_numpy(values)).numpy()
    log_odds = np.log(prior / (1 - prior)) + corrections[:, 0].astype(np.float64)
    probability = 1 / (1 + np.exp(-log_odds))
    return probability, baseline + corrections[:, 1]


def run_trees(load_model, impulse_model, values, baseline):
    probability = load_model.run(None, {'histories': values})[1][:, 1]
    impulse = impulse_model.run(None, {'histories': values})[0].reshape(-1) + baseline
    return probability, impulse


def history(example, model):
    emg = np.asarray(example['emg_rms_volts'], dtype=np.float64)
    own = np.asarray(example['measured_plate_force_n'], dtype=np.float64)
    channels = {6} if model == 'trees' else {4, 6}
    if (emg.ndim != 2 or emg.shape[0] != 10 or emg.shape[1] not in channels or
            own.shape != (10,) or not np.isfinite(own).all() or np.any(np.isinf(emg) | (emg < 0))):
        raise ValueError('Supply ten force bins and ten rows of nonnegative muscle RMS voltage. Use null for an absent muscle reading.')
    return emg[None], own[None]


def forecast(example, model):
    emg, own = history(example, model)
    if model == 'trees':
        other = np.asarray(example['other_plate_force_n'], dtype=np.float64)
        if other.shape != (10,) or not np.isfinite(other).all():
            raise ValueError('The tree comparison uses the same ten force bins from a second plate.')
        input_history = np.concatenate((emg, own[..., None], other[None, :, None]), axis=-1)
        settings = read_json(CHECKPOINTS / 'preprocessing.json')
        values, baseline = tree_features(input_history, np.isfinite(input_history), settings)
        return run_trees(model_session('load.onnx'), model_session('impulse-residual.onnx'), values, baseline)
    settings = read_json(CHECKPOINTS / 'recurrent-preprocessing.json')
    return run_recurrent(recurrent_model(), recurrent_features(emg, own),
                         own[:, -1] * .1, settings['load_prior'])


def example_history():
    force = [1., 2., 6., 20., 120., 270., 420., 555., 630., 625.]
    muscle = [[.00004 + .000013 * tick * (channel + 1) for channel in range(6)] for tick in range(10)]
    return {'emg_rms_volts': muscle, 'measured_plate_force_n': force,
            'other_plate_force_n': [100., 70., 44., 27., 10., 5., 3., 2., 1., 1.]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=('three-pass', 'trees'), default='three-pass')
    parser.add_argument('--input', type=Path, help='JSON window of recorded inputs. Omitting it runs the generated example.')
    args = parser.parse_args()
    if args.model == 'three-pass':
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    example = read_json(args.input) if args.input else example_history()
    probability, impulse = forecast(example, args.model)
    print(json.dumps({'data': 'recorded input supplied by the caller' if args.input else 'generated example',
                      'model': args.model, 'forecast_ms': 100, 'new_load_probability': float(probability[0]),
                      'vertical_impulse_n_s': float(impulse[0])}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
