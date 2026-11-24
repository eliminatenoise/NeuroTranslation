"""Run the released NeuroTranslate 0.1 adapter on an invented history."""

from argparse import ArgumentParser
from collections import Counter
from dataclasses import replace
from hashlib import file_digest
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import os
import sys


PACKAGE = Path(__file__).resolve().parent
SHARD = 'model-00001-of-00001.safetensors'
VERSIONS = {'torch': '2.14.1+cpu', 'transformers': '5.24.0', 'safetensors': '0.8.0'}


def check_file(path, identity):
    if not path.is_file() or path.stat().st_size != identity['bytes']:
        raise ValueError(f'Missing or incomplete file: {path.name}')
    with path.open('rb') as stream:
        checksum = file_digest(stream, 'sha256').hexdigest()
    if checksum != identity['sha256']:
        raise ValueError(f'Checksum differs for {path.name}. Use the pinned release in checkpoint.json.')


def preflight(base_dir):
    """Check the local adapter and every pinned base file by size and SHA-256."""
    manifest = json.loads((PACKAGE / 'checkpoint.json').read_bytes())
    small = manifest['adapter']
    check_file(PACKAGE / small['file'], small)
    for name, identity in manifest['base']['files'].items():
        check_file(base_dir / name, identity)
    return manifest


def load_model(base_dir, threads=4):
    """Restore the exact adapter and its frozen CPU backbone for local inference."""
    base_dir = Path(base_dir).resolve()
    for package, expected in VERSIONS.items():
        try:
            actual = version(package)
        except PackageNotFoundError:
            raise ValueError(f'Install {package} {expected} using the README.') from None
        if actual != expected:
            raise ValueError(f'Installed {package} {actual}. This checkpoint requires {expected}.')
    manifest = preflight(base_dir)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    os.environ['HF_DEACTIVATE_ASYNC_LOAD'] = '1'
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ['ROCR_VISIBLE_DEVICES'] = ''
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'

    import torch
    from safetensors import safe_open
    from safetensors.torch import load_file
    from transformers import AutoConfig, AutoModelForImageTextToText, modeling_utils
    from model import NeuroTranslate, StreamSpec, TargetSpec

    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    config = AutoConfig.from_pretrained(base_dir, local_files_only=True, trust_remote_code=False)
    opened = []

    def use_pread(path, *args, **kwargs):
        if Path(path).resolve() != (base_dir / SHARD).resolve() or kwargs.get('device') != 'cpu' or kwargs.get('backend') != 'mmap':
            raise ValueError('Unexpected shard or loader route.')
        opened.append(Path(path).name)
        return safe_open(path, *args, **{**kwargs, 'backend': 'pread'})

    # Select an official safetensors reader that reads tensor slices directly
    # instead of retaining the packed shard as a memory map while it expands.
    with patch.object(modeling_utils, 'safe_open', use_pread):
        backbone, checked = AutoModelForImageTextToText.from_pretrained(
            base_dir, config=config, dtype=torch.bfloat16, local_files_only=True, trust_remote_code=False,
            attn_implementation='eager', experts_implementation='eager', use_kernels=False, output_loading_info=True,
        )
    if opened != [SHARD] or any(checked.get(key) for key in ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs')):
        raise ValueError('The base checkpoint did not restore all expected weights.')
    backbone.eval().requires_grad_(False)
    decoder = backbone.model.language_model
    if (len(decoder.layers), decoder.config.loop_num_passes, decoder.config.total_num_hidden_layers) != (24, 3, 48):
        raise ValueError('The restored decoder does not match Inkling 2 Mini.')

    class SensorDecoder(torch.nn.Module):
        def __init__(self, source):
            super().__init__()
            self.source = source
            self.config = source.config

        def forward(self, *, inputs_embeds, **kwargs):
            states = self.source(inputs_embeds=inputs_embeds.to(torch.bfloat16), **kwargs)
            return SimpleNamespace(last_hidden_state=states.last_hidden_state.float())

    adapted = NeuroTranslate(SensorDecoder(decoder), decoder.config.hidden_size, (StreamSpec('emg', 14), StreamSpec('force', 1)),
                             (TargetSpec('new_load', 1, 'event'), TargetSpec('impulse', 1, 'movement')), freeze_backbone=True)
    adapter_file = manifest['adapter']['file']
    values = load_file(PACKAGE / adapter_file, device='cpu')
    tensors = {name: tensor for name, tensor in adapted.named_parameters() if not name.startswith('backbone.')}
    tensors.update({name: tensor for name, tensor in adapted.named_buffers() if name.startswith('adapters.')})
    if values.keys() != tensors.keys() or len(values) != manifest['adapter']['tensor_count']:
        raise ValueError('The adapter tensor names do not match this model.')
    with torch.no_grad():
        for name, target in tensors.items():
            value = values[name]
            if value.dtype != torch.float32 or value.shape != target.shape or not torch.isfinite(value).all():
                raise ValueError(f'Invalid adapter tensor: {name}')
            if name.endswith('.scale') and not (value > 0).all():
                raise ValueError(f'Invalid scale: {name}')
            target.copy_(value)
    if not all(torch.equal(tensors[name], value) for name, value in values.items()):
        raise ValueError('At least one adapter tensor changed during restore.')
    return adapted.eval().requires_grad_(False)


def invented_history():
    """Make a ten-bin example with muscle voltage and one plate's vertical force."""
    import torch
    from model import History

    # Bin 0 covers sample indices 0–19. Bin 9 ends at issue index 199.
    cutoffs = torch.arange(19, 200, 20, dtype=torch.float64)[None, :] / 1000
    rows = torch.arange(10, dtype=torch.float32).reshape(1, 10, 1)
    channels = torch.arange(1, 15, dtype=torch.float32).reshape(1, 1, 14)
    muscle = .0002 + .00003 * rows + .000015 * channels
    plate = torch.tensor([-0.5, 0.0, 0.2, -0.3, 0.2, 0.6, 1.0, 0.5, 2.0, 4.0]).reshape(1, 10, 1)
    streams = {}
    for name, values in (('emg', muscle), ('force', plate)):
        clock = cutoffs.unsqueeze(-1).expand_as(values)
        streams[name] = History(values, torch.ones_like(values, dtype=torch.bool), clock, clock)
    return streams, cutoffs, cutoffs[:, -1].clone()


def demo(base_dir, threads, check_mask):
    model = load_model(base_dir, threads)
    import torch

    given, cutoffs, issue = invented_history()
    visits = Counter()

    def mark(index):
        def tick(*_):
            visits[index] += 1
        return tick

    handles = [layer.register_forward_hook(mark(i)) for i, layer in enumerate(model.backbone.source.layers)]
    with torch.inference_mode():
        raw = model(given, cutoffs, issue)
        view = model.natural_outputs(raw)
    for handle in handles:
        handle.remove()
    if [visits[i] for i in range(24)] != [1] * 6 + [3] * 12 + [1] * 6:
        raise ValueError('The decoder did not execute its expected loop.')
    result = {'input': 'invented ten-bin muscle voltage and force history', 'next_window_ms': 100,
              'new_load_logit': float(raw['new_load'].item()), 'new_load_probability_uncalibrated': float(view['new_load'].item()),
              'signed_vertical_force_impulse_N_s': float(view['impulse'].item()), 'decoder_layer_visits': sum(visits.values()),
              'adapter_restored_all_tensors_exactly': True}
    if check_mask:
        emg, force = given['emg'], given['force']
        availability, present = emg.available_s.clone(), force.observed.clone()
        availability[0, -1, 0] = issue[0] + .001
        present[0, 0, 0] = False
        held = {'emg': replace(emg, available_s=availability), 'force': replace(force, observed=present)}
        noise_emg, noise_force = emg.values.clone(), force.values.clone()
        noise_emg[0, -1, 0] = noise_force[0, 0, 0] = float('nan')
        changed = {'emg': replace(held['emg'], values=noise_emg), 'force': replace(held['force'], values=noise_force)}
        with torch.inference_mode():
            repeat = model(given, cutoffs, issue)
            before, after = model(held, cutoffs, issue), model(changed, cutoffs, issue)
        if not all(torch.equal(raw[name], repeat[name]) and torch.equal(before[name], after[name]) for name in raw):
            raise ValueError('Repeat or missing-value check failed.')
        result['same_fixture_and_withheld_value_checks_match_bit_for_bit'] = True
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--base-dir', required=True, type=Path, help='Folder containing the pinned Inkling 2 Mini files.')
    parser.add_argument('--threads', type=int, default=4, help='CPU threads for the local model.')
    parser.add_argument('--check-only', action='store_true', help='Verify local file checksums without loading the model.')
    parser.add_argument('--check-mask', action='store_true', help='Also verify repeated inputs and missing or late samples.')
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('--threads must be a positive integer.')
    try:
        if args.check_only:
            manifest = preflight(args.base_dir)
            result = {'base_revision': manifest['base']['revision'], 'local_adapter_and_base_sha256_match': True}
        else:
            result = demo(args.base_dir, args.threads, args.check_mask)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
