"""Frozen published checkpoints F1-F4 and controls C1-C3, issued through the published code.

Every published file is checked against the sha256 recorded in PROTOCOL.json (frozen_checkpoints,
repository commit 03e76d4) before it is used. F1 needs runtime A (torch); F2, F3, F4 and the controls
run in runtime B. F5 (Research Edition) is optional and is not issued by this code.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from common import FIT_PREVALENCE_12, HERE, need, read_json, sha_file

F3_EXTRA = {'models/neurotranslate-0.0/recorded-force/expanded/force_reference.py':
            '1c3ea2cf19d077f205f1fc42d9c7609aafbd55b1043a5538039c6c3d7813bae2'}
F3_TASK = 'recorded_plate_loading_common_six_100ms'
F3_MODELS = {'F3_gate_trainable': 'past-load-gate-trainable-core.npz', 'F3_gate_frozen': 'past-load-gate-frozen-core.npz',
             'F3_expanded_frozen': 'frozen-core.npz', 'F3_expanded_trainable': 'trainable-core.npz'}
NOT_SCORED = {
    'models/neurotranslate-0.1/IO-ADAPTER.safetensors': 'Needs all 14 muscle names; fitted on 2 people.',
    'models/force-baselines/strict-fourteen.npz': 'Needs all 14 muscle names; fitted on 2 people.',
    'models/neurotranslate-0.0/recorded-force/checkpoints/*.npz': 'Need all 14 names; fitted on 5 walks of 2 people.',
    'models/neurotranslate-0.1/paired-plates/*': (
        'Not scored and not refitted: the task names only the compact three-pass, the published trees, the 0.0 '
        'expanded preview, the force baselines and the optional Research Edition. Some paired-plates options were '
        'fitted on the same Belgian fit archive (admission review, minor 7); they are recorded here as not scored.'),
    'models/neurotranslate-0.1/research-edition (F5)': 'Optional; not issued in this stage (lead decision).',
}


def pinned(repo_root):
    """Map repository path -> expected sha256 for F1-F4 from the committed PROTOCOL.json."""
    proto = read_json(HERE / 'PROTOCOL.json')['frozen_checkpoints']
    pins = {}
    for key, entry in proto.items():
        if key.startswith('F') and key != 'F5_research_edition_optional':
            for path, info in entry['files'].items():
                pins[path] = info['sha256']
    pins.update(F3_EXTRA)
    root = Path(repo_root)
    bad = [p for p, h in pins.items() if sha_file(root / p) != h]
    need(not bad, f'published files differ from the protocol pins: {bad}')
    return pins


def _module(path, name, extra_path=None):
    if extra_path:
        sys.path.insert(0, str(extra_path))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        if extra_path:
            sys.path.remove(str(extra_path))
    return module


# --------------------------------------------------------------------------------------- controls
def control_c1(inputs, rows):
    force = inputs['past_force_n'][rows]
    return np.full(len(rows), FIT_PREVALENCE_12), force[:, -1] * .1


def control_c2(rows, median_12):
    return np.full(len(rows), FIT_PREVALENCE_12), np.full(len(rows), float(median_12))


def control_c3(inputs, rows):
    """OLS line through the last three bin means at t - 49.5, t - 29.5, t - 9.5; 0.1 s x (b0 + 50.5 b1)."""
    y = inputs['past_force_n'][rows][:, -3:]
    x = np.array([-49.5, -29.5, -9.5])
    xc = x - x.mean()
    slope = (y - y.mean(axis=1, keepdims=True)) @ xc / (xc @ xc)
    intercept = y.mean(axis=1) - slope * x.mean()
    return np.full(len(rows), FIT_PREVALENCE_12), 0.1 * (intercept + 50.5 * slope)


# ------------------------------------------------------------------------------------------ F1/F2
def wns_module(repo_root):
    return _module(Path(repo_root) / 'benchmarks/walking-neural-scaling/predict.py', 'wns_published_predict')


def issue_f1(repo_root, inputs, rows, chunk=4096):
    """Published three-pass checkpoint with its preprocessing (runtime A)."""
    import torch
    mod = wns_module(repo_root)
    settings = json.loads((Path(repo_root) / 'benchmarks/walking-neural-scaling/checkpoints/recurrent-preprocessing.json').read_text())
    model = mod.recurrent_model()
    emg, own = inputs['emg_rms_v'][rows], inputs['past_force_n'][rows]
    prob, imp = [], []
    with torch.inference_mode():
        for s in range(0, len(rows), chunk):
            values = mod.recurrent_features(emg[s:s + chunk], own[s:s + chunk])
            p, i = mod.run_recurrent(model, values, own[s:s + chunk, -1] * .1, settings['load_prior'])
            prob.append(p)
            imp.append(i)
    return np.concatenate(prob), np.concatenate(imp)


def issue_f2(repo_root, inputs, rows):
    """Published ONNX tree pair with its preprocessing (runtime B)."""
    from trees import tree_history
    mod = wns_module(repo_root)
    settings = json.loads((Path(repo_root) / 'benchmarks/walking-neural-scaling/checkpoints/preprocessing.json').read_text())
    history, available = tree_history(inputs, rows)
    values, baseline = mod.tree_features(history, available, settings)
    return mod.run_trees(mod.model_session('load.onnx'), mod.model_session('impulse-residual.onnx'), values, baseline)


# --------------------------------------------------------------------------------------------- F3
def f3_models(repo_root):
    folder = Path(repo_root) / 'models/neurotranslate-0.0/recorded-force/expanded'
    inference = _module(folder / 'inference.py', 'nt00_inference')
    _module(folder / 'force_reference.py', 'force_reference')
    gate = _module(folder / 'past_load_gate.py', 'nt00_past_load_gate', folder)
    out = {}
    for name, file in F3_MODELS.items():
        decoder = inference.JointModel.load(folder / 'models' / file)
        schema = decoder.tasks[F3_TASK]
        need(schema['history_steps'] == 10 and schema['horizon_ticks'] == 100, 'F3 schema changed')
        out[name] = (gate.GateModel(decoder) if name.startswith('F3_gate') else decoder)
    return out


def issue_f3(models, inputs, rows, chunk=4096):
    history = np.concatenate((inputs['emg_rms_v'][rows], inputs['past_force_n'][rows][..., None]), axis=-1)
    out = {}
    for name, model in models.items():
        prob, imp = [], []
        for s in range(0, len(rows), chunk):
            part = history[s:s + chunk]
            if name.startswith('F3_gate'):
                p, i = model.predict(part).T
            else:
                raw = model.predict(F3_TASK, part).astype(np.float64)
                small = np.exp(-np.abs(raw[:, 0]))
                p = np.where(raw[:, 0] >= 0, 1 / (1 + small), small / (1 + small))
                i = raw[:, 1]
            prob.append(p)
            imp.append(i)
        out[name] = (np.concatenate(prob), np.concatenate(imp))
    return out


# --------------------------------------------------------------------------------------------- F4
def f4_grid(repo_root):
    mod = _module(Path(repo_root) / 'models/force-baselines/predict.py', 'fb_published_predict')
    return mod, mod.load('common-six')


def issue_f4(grid, choice, inputs, rows):
    """choice: 'endpoint/group/arm' -> penalty (sealed in C3). Returns name -> (probability, impulse)."""
    from linear import F4_ARMS, f4_predict
    out = {}
    emg, force, earlier = inputs['emg_rms_v'][rows], inputs['past_force_n'][rows], inputs['early_emg_rms_v'][rows]
    for group, arms in F4_ARMS.items():
        for arm in arms:
            p = f4_predict(grid.coefficients, 'event', group, arm, choice[f'event/{group}/{arm}'], emg, force, earlier)
            i = f4_predict(grid.coefficients, 'impulse', group, arm, choice[f'impulse/{group}/{arm}'], emg, force, earlier)
            out[f'F4_{group}_{arm}'] = (p, i)
    return out
