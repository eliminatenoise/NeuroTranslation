"""Check or run the six-channel Research Edition preview on an invented history."""

from argparse import ArgumentParser, ArgumentTypeError
from collections import Counter
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from math import prod
import os
from pathlib import Path
import platform
import sys
from unittest.mock import patch

from synthetic_fixture import admitted, check, make, mutate_hidden


PACKAGE = Path(__file__).resolve().parent
CHECKPOINT_SHA = '41e75166a36e858818b1e2502eb0ed8ae7093b71183a74361af744efa7fb5b3d'
SHARD = 'model-00001-of-00001.safetensors'
IO = 'weights/SENSOR-LOOP-JOINT.safetensors'
DELTA = 'weights/NATIVE-JOINT-DELTA.safetensors'
CHANNELS = ('LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'RERS')
DEPENDENCIES = {'torch': '2.14.1+cpu', 'transformers': '5.24.0', 'safetensors': '0.8.0', 'numpy': '2.5.3'}
BATCH_LAYOUT = 'two-invented-rows'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def hash_file(path):
    digest = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def check_file(path, identity):
    need(path.is_file() and path.stat().st_size == identity['bytes'],
         f'Missing or incomplete file {path.name}. See README.md for the expected file.')
    need(hash_file(path) == identity['sha256'], f'Checksum differs for {path.name}. Use the exact pinned file.')


def asset_manifest():
    raw = (PACKAGE / 'checkpoint.json').read_bytes()
    need(sha256(raw).hexdigest() == CHECKPOINT_SHA, 'checkpoint.json checksum differs from this package.')
    data = json.loads(raw)
    need(data['schema_version'] == 1 and tuple(data['channels']) == CHANNELS
         and data['targets']['window_ms'] == 100 and set(data['weights']) == {IO, DELTA}, 'Unexpected package contract.')
    return data


def weights_header(path, identity):
    """Check the exact small Safetensors file schema with Python alone."""
    with path.open('rb') as stream:
        size = int.from_bytes(stream.read(8), 'little')
        need(0 < size <= 65536, f'Unexpected tensor header in {path.name}.')
        tensors = json.loads(stream.read(size))
    metadata = tensors.pop('__metadata__', {})
    need(metadata == identity['public_safe_embedded_metadata']
         and {key: entry['shape'] for key, entry in tensors.items()} == identity['tensor_shapes'],
         f'Unexpected tensor names, shapes or provenance in {path.name}.')
    offset, word_bytes = 0, {'F32': 4, 'F64': 8}[identity['dtype']]
    for entry in sorted(tensors.values(), key=lambda entry: entry['data_offsets'][0]):
        first, last = entry['data_offsets']
        need(entry['dtype'] == identity['dtype'] and first == offset and last - first == prod(entry['shape']) * word_bytes,
             f'Unexpected tensor dtype or storage in {path.name}.')
        offset = last
    need(size + 8 + offset == identity['bytes'], f'Tensor archive extent differs in {path.name}.')


def self_test():
    data = asset_manifest()
    for name, identity in data['local_assets'].items():
        path = PACKAGE / name
        need(not path.is_symlink(), f'Packaged asset {name} must be a regular local file.')
        check_file(path, identity)
    for name, identity in data['weights'].items():
        weights_header(PACKAGE / name, identity)
    fixture = json.loads((PACKAGE / 'example.json').read_bytes())
    need(fixture == make(), 'The invented fixture does not match its package-local generator.')
    masked = mutate_hidden(fixture)
    need(all(admitted(fixture, key) == admitted(masked, key) for key in ('emg', 'force')),
         'The invented fixture did not exercise withheld values correctly.')
    return data, {'package_assets_sha256_verified': len(data['local_assets']),
                  'joint_checkpoint_tensor_counts': {Path(name).name: len(record['tensor_shapes'])
                                                     for name, record in data['weights'].items()},
                  'sample': check(), 'base_weights_loaded': False}


def base_directory(option):
    if option is not None:
        return option.expanduser().resolve()
    environment = os.environ.get('NEUROTRANSLATE_RESEARCH_BASE_DIR')
    if environment:
        return Path(environment).expanduser().resolve()
    conventional = PACKAGE / 'research-edition-base'
    need(conventional.is_dir(),
         'Choose the Research Edition folder with --base-dir PATH or NEUROTRANSLATE_RESEARCH_BASE_DIR. See README.md.')
    return conventional


def check_base(path, manifest):
    need(path.is_dir(), f'Base folder {path.name or path} is missing. See README.md for the exact download.')
    names = manifest['base']['files']
    # Inspect all four extents before reading the large shard.
    for name, identity in names.items():
        file = path / name
        need(file.is_file() and file.stat().st_size == identity['bytes'], f'Missing or incomplete base file {name}.')
    for name, identity in names.items():
        check_file(path / name, identity)
    index = json.loads((path / 'model.safetensors.index.json').read_bytes())
    need(set(index['weight_map'].values()) == {SHARD}, 'This index refers to an unexpected weight shard.')


def dependency_checks():
    for name, expected in DEPENDENCIES.items():
        try:
            found = version(name)
        except PackageNotFoundError:
            raise ValueError(f'Install {name} {expected} using README.md.') from None
        need(found == expected, f'Found {name} {found}. Use {expected} for this preview.')


def available_memory_kib():
    with Path('/proc/meminfo').open() as stream:
        def host_available(line):
            fields = line.split()
            return int(fields[1]) if fields and fields[0] == 'MemAvailable:' else None

        free = next(amount for line in stream if (amount := host_available(line)) is not None)
    limits = Path('/sys/fs/cgroup/memory.max')
    used = Path('/sys/fs/cgroup/memory.current')
    if limits.is_file() and used.is_file():
        ceiling = limits.read_text().strip()
        if ceiling != 'max':
            free = min(free, (int(ceiling) - int(used.read_text())) // 1024)
    return free


def restore(torch, decoder, forecast, manifest, load_file):
    """Restore original I/O tensors plus the two exact additive native updates."""
    expected = manifest['weights']
    local = load_file(PACKAGE / IO, device='cpu')
    additive = load_file(PACKAGE / DELTA, device='cpu')
    small = {name: tensor for name, tensor in (*forecast.named_parameters(), *forecast.named_buffers())
             if not name.startswith('backbone.') or name.startswith('backbone.sensor_messages.')}
    need(set(small) == set(local) == set(expected[IO]['tensor_shapes'])
         and set(additive) == set(expected[DELTA]['tensor_shapes']),
         'The release tensors do not match the reconstructed Research Edition.')
    native = {name: decoder.get_parameter(name) for name in additive}
    prepared = {}
    for name, values in local.items():
        need(values.dtype == torch.float32 and values.shape == small[name].shape
             and torch.isfinite(values).all().item() and (not name.endswith('.scale') or (values > 0).all().item()),
             f'Invalid learned projection or scale {name}.')
    for name, values in additive.items():
        target = native[name]
        need(values.dtype == torch.float64 and target.dtype == torch.float32 and values.shape == target.shape
             and torch.isfinite(values).all().item() and torch.count_nonzero(values).item() > 0,
             f'Invalid native update {name}.')
        prepared[name] = (target.detach().double() + values).float()
        need(torch.isfinite(prepared[name]).all().item(), f'Native update overflowed for {name}.')
    with torch.no_grad():
        for name, value in local.items():
            small[name].copy_(value)
        for name, value in prepared.items():
            native[name].copy_(value)
    need(all(torch.equal(small[name], values) for name, values in local.items())
         and all(torch.equal(native[name], values) for name, values in prepared.items()),
         'The model did not restore both learned tensor groups exactly.')


def load_preview(folder, manifest, threads):
    need(platform.system() == 'Linux' and platform.machine() == 'x86_64' and sys.version_info[:2] == (3, 13),
         'The available full-loader route is Linux x86-64 on Python 3.13. The offline self-test can run separately.')
    dependency_checks()
    need(available_memory_kib() >= 64 * 1024**2,
         'This CPU loader needs 64 GiB of available RAM. Run --self-test or --check-only without loading the model.')
    check_base(folder, manifest)
    os.environ.update({
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_DEACTIVATE_ASYNC_LOAD': '1',
        'HF_HUB_DISABLE_PROGRESS_BARS': '1', 'CUDA_VISIBLE_DEVICES': '', 'ROCR_VISIBLE_DEVICES': '',
        'TOKENIZERS_PARALLELISM': 'false',
    })
    import torch
    import transformers
    from safetensors import safe_open
    from safetensors.torch import load_file
    from transformers import AutoConfig, AutoModelForImageTextToText, modeling_utils
    from forecast import SensorLoopForecast
    from model import StreamSpec, TargetSpec

    root = Path(transformers.__file__).resolve().parent
    for name, digest in manifest['tested_prior_runtime']['transformers_code_sha256'].items():
        need(hash_file(root / name) == digest, f'The Transformers file {name} differs from the verified wheel.')
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    config = AutoConfig.from_pretrained(folder, local_files_only=True, trust_remote_code=False)
    opened = []

    def verified_shard(path, *args, **kwargs):
        need(Path(path).resolve() == (folder / SHARD).resolve() and kwargs.get('framework') == 'pt'
             and kwargs.get('device') == 'cpu' and kwargs.get('backend') == 'mmap',
             'Unexpected source shard or reader route.')
        opened.append(Path(path).name)
        return safe_open(path, *args, **{**kwargs, 'backend': 'pread'})

    with patch.object(modeling_utils, 'safe_open', verified_shard):
        full, report = AutoModelForImageTextToText.from_pretrained(
            folder, config=config, dtype=torch.bfloat16, local_files_only=True, trust_remote_code=False,
            attn_implementation='eager', experts_implementation='eager', use_kernels=False, output_loading_info=True,
        )
    need(opened == [SHARD] and type(full).__name__ == 'Inkling2LoopForConditionalGeneration'
         and not any(report.get(k) for k in ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs')),
         'The original Research Edition checkpoint did not load cleanly.')
    full.eval().requires_grad_(False)
    native = full.model.language_model
    form = native.config
    need((len(native.layers), form.hidden_size, form.loop_layer_index_start,
          form.loop_layer_index_end, form.loop_num_passes) == (24, 2304, 6, 18, 3)
         and native.embed_tokens.weight.dtype == torch.bfloat16, 'Unexpected released decoder architecture.')
    view = SensorLoopForecast(native, (StreamSpec('emg', 6), StreamSpec('force', 1)),
                              (TargetSpec('new_load', 1, 'event'), TargetSpec('impulse', 1, 'movement')),
                              message_rank=4).eval().requires_grad_(False)
    restore(torch, native, view, manifest, load_file)
    return view


def as_history(torch, fixture):
    from model import History

    end = torch.tensor(fixture['bin_end_tick'], dtype=torch.float64).expand(len(fixture['rows']), -1) / 1000
    issue = torch.tensor([row['issue_tick'] for row in fixture['rows']], dtype=torch.float64) / 1000
    streams = {}
    for name, row in fixture['streams'].items():
        streams[name] = History(
            torch.tensor(row['values'], dtype=torch.float32), torch.tensor(row['observed'], dtype=torch.bool),
            torch.tensor(row['acquired_tick'], dtype=torch.float64) / 1000,
            torch.tensor(row['available_tick'], dtype=torch.float64) / 1000,
        )
    return streams, end, issue


def forecast(folder, manifest, passes, threads, check_mask):
    model = load_preview(folder, manifest, threads)
    import torch

    fixture = json.loads((PACKAGE / 'example.json').read_bytes())
    visits = Counter()

    def mark(index):
        def hook(*_):
            visits[index] += 1
        return hook

    native = model.backbone.native
    handles = [layer.register_forward_hook(mark(i)) for i, layer in enumerate(native.layers)]
    handles.append(native.message_input.register_forward_hook(mark('native_messages')))
    try:
        with torch.inference_mode():
            raw = model(*as_history(torch, fixture), passes=passes)
    finally:
        for handle in handles:
            handle.remove()
    need([visits[i] for i in range(24)] == [1] * 6 + [passes] * 12 + [1] * 6
         and visits['native_messages'] == 12 * (passes - 1)
         and all(value.shape == (2, 1) for value in raw.values()), 'The executed pass or fixed example shape differs.')
    result = {
        'scope': 'invented two-row preview, separate from the 48-row fit replay',
        'passes': passes, 'issue_plate_rows': 2, 'next_window_ms': 100,
        'decoder_layer_visits': sum(visits[i] for i in range(24)),
        'native_cross_pass_messages': visits['native_messages'],
        'new_load_logit': raw['new_load'].reshape(-1).tolist(),
        'new_load_probability_uncalibrated': raw['new_load'].sigmoid().reshape(-1).tolist(),
        'signed_vertical_force_impulse_N_s': raw['impulse'].reshape(-1).tolist(),
    }
    if check_mask:
        with torch.inference_mode():
            repeated = model(*as_history(torch, fixture), passes=passes)
            altered = model(*as_history(torch, mutate_hidden(fixture)), passes=passes)
        need(all(torch.equal(raw[key], repeated[key]) and torch.equal(raw[key], altered[key]) for key in raw),
             'Repeated input or hidden sample mutation changed an output.')
        result['repeat_and_hidden_mutation_match_bit_for_bit'] = True
    return result


def positive(value):
    try:
        integer = int(value)
    except ValueError as error:
        raise ArgumentTypeError('Use a positive whole number.') from error
    if integer < 1:
        raise ArgumentTypeError('Use a positive whole number.')
    return integer


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--self-test', action='store_true', help='Check the packaged files and invented input with Python alone. This is the default.')
    actions.add_argument('--check-only', action='store_true', help='Check the packaged files and the four separately fetched base files without loading them.')
    actions.add_argument('--forecast', action='store_true', help='Request the full local experimental CPU forecast.')
    parser.add_argument('--base-dir', type=Path, help='Folder containing the exact Research Edition base files.')
    parser.add_argument('--batch-layout', choices=(BATCH_LAYOUT,), help='Explicitly choose the separate two-row invented case for --forecast.')
    parser.add_argument('--passes', type=positive, default=3, help='Number of times to run the 12 shared layers. Default 3.')
    parser.add_argument('--threads', type=positive, default=4, help='CPU threads for --forecast. Default 4.')
    parser.add_argument('--check-mask', action='store_true', help='Check exact repeat and withheld-value invariance when forecasting.')
    args = parser.parse_args(argv)
    if not args.forecast and (args.batch_layout is not None or args.check_mask):
        parser.error('--batch-layout and --check-mask apply to --forecast.')
    if args.forecast and args.batch_layout != BATCH_LAYOUT:
        parser.error('--forecast requires --batch-layout two-invented-rows. Read the batch comparison in README.md.')
    try:
        manifest, result = self_test()
        if args.check_only:
            check_base(base_directory(args.base_dir), manifest)
            result['base_files_sha256_verified'] = len(manifest['base']['files'])
        elif args.forecast:
            result = forecast(base_directory(args.base_dir), manifest, args.passes, args.threads, args.check_mask)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
