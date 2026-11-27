"""Issue stage: forecasts of every sealed fit, frozen checkpoint and control on the evaluation inputs.

  issue.py run  --config CFG --runtime torch|sk   (runtime A for M1-type fits and F1; runtime B for the rest)
  issue.py seal --config CFG                      -> FORECASTS-SEAL.json (C4)

Custody (protocol section 14): this process opens only EVAL-INPUTS.npz (keys, histories, input masks);
it never opens the targets. Forecasts are issued for every input-valid row (all six EMG channels and
the target plate valid in all ten bins), in one fixed order and fixed batches, into three private files
per runtime:
  FORECASTS-PRIMARY-BELOW-NMAX-*  M1, M2, M3 at the rungs below N_max (the only file stage S-b reads)
  FORECASTS-NMAX-*                every fit at N_max, including the G8 sets
  FORECASTS-OTHER-*               secondary arms below N_max, frozen checkpoints and controls
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from common import HERE, load_config, need, publish_dir, read_json, sha_file, single_thread_env, write_json

GROUPS = ('PRIMARY-BELOW-NMAX', 'NMAX', 'OTHER')


def group_of(job):
    if job['kind'] in ('max', 'g8'):
        return 'NMAX'
    if job['arm'] in ('M1', 'M2', 'M3'):
        return 'PRIMARY-BELOW-NMAX'
    return 'OTHER'


def key(name):
    return name.replace('|', '_')


def forecast_dir(cfg):
    return Path(cfg['private_dir']) / 'forecasts'


def load_eval_inputs(cfg):
    import extract
    folder = Path(cfg['private_dir']) / 'arrays'
    meta = read_json(folder / 'EVAL-WALKS.json')
    need(sha_file(folder / 'EVAL-INPUTS.npz') == meta['inputs_sha256'], 'evaluation inputs changed')
    return extract.load_npz(folder / 'EVAL-INPUTS.npz', extract.INPUT_FIELDS), meta


def run(cfg_path, allocation_path, fit_complete_path, runtime):
    single_thread_env()
    import numpy as np
    import extract
    import fit
    import frozen
    import plan
    cfg = load_config(cfg_path)
    allocation = read_json(allocation_path)
    sealed = read_json(fit_complete_path)
    need(sealed['allocation_sha256'] == sha_file(allocation_path), 'FIT-COMPLETE.json was made for another allocation')
    by_id = {c['id']: c for c in sealed['checkpoints']}
    inputs, meta = load_eval_inputs(cfg)
    rows = np.flatnonzero(extract.input_valid(inputs))
    if runtime == 'torch':
        import threepass
        threepass.setup_runtime()
    out = {g: {} for g in GROUPS}
    skipped = []
    for job in plan.jobs(allocation):
        if job['runtime'] != runtime:
            continue
        entry = by_id[job['id']]
        if entry['status'] != 'done':
            skipped.append(job['id'])
            continue
        ck, side = fit.job_paths(cfg, job)
        need(sha_file(ck) == entry['file_sha256'], f'checkpoint differs from FIT-COMPLETE.json: {job["id"]}')
        prob, imp = fit._issue_one(job, ck, read_json(side), inputs, rows)
        out[group_of(job)][key(job['id'])] = (prob, imp)
    repo = cfg['repo_root']
    frozen.pinned(repo)
    if runtime == 'torch':
        out['OTHER']['F1'] = frozen.issue_f1(repo, inputs, rows)
    else:
        out['OTHER']['C1'] = frozen.control_c1(inputs, rows)
        out['OTHER']['C2'] = frozen.control_c2(rows, sealed_median(sealed, cfg))
        out['OTHER']['C3'] = frozen.control_c3(inputs, rows)
        out['OTHER']['F2'] = frozen.issue_f2(repo, inputs, rows)
        out['OTHER'].update(frozen.issue_f3(frozen.f3_models(repo), inputs, rows))
        _mod, grid = frozen.f4_grid(repo)
        out['OTHER'].update(frozen.issue_f4(grid, sealed['F4_penalties'], inputs, rows))
    folder = forecast_dir(cfg)
    folder.mkdir(parents=True, exist_ok=True)
    written = {}
    for group, items in out.items():
        path = folder / f'FORECASTS-{group}-{runtime}.npz'
        need(not path.exists(), f'{path.name} exists: forecasts are issued once')
        arrays = {'rows': rows, **{k: inputs[k][rows] for k in extract.KEYS}}
        for name, (p, i) in items.items():
            arrays[f'{name}::p'] = np.asarray(p, dtype=np.float64)
            arrays[f'{name}::i'] = np.asarray(i, dtype=np.float64)
        with open(path, 'xb') as stream:
            np.savez_compressed(stream, **arrays)
        written[path.name] = {'sha256': sha_file(path), 'methods': len(items)}
    write_json(folder / f'ISSUED-{runtime}.json', {'runtime': runtime, 'rows': int(len(rows)), 'files': written,
                                                   'not_issued_failed_fits': skipped,
                                                   'eval_inputs_sha256': meta['inputs_sha256'],
                                                   'fit_complete_sha256': sha_file(fit_complete_path),
                                                   'utc': datetime.now(timezone.utc).isoformat()})
    return written


def sealed_median(sealed, cfg):
    """C2 uses the person-weighted median impulse of the 12 earlier fit people (published fallback)."""
    pre = json.loads((Path(cfg['repo_root']) / 'benchmarks/walking-neural-scaling/checkpoints/preprocessing.json').read_text())
    return pre['missing_force_fallback_ns']


def seal(cfg_path, fit_complete_path):
    cfg = load_config(cfg_path)
    folder = forecast_dir(cfg)
    issued = {r: read_json(folder / f'ISSUED-{r}.json') for r in ('torch', 'sk')}
    files = {}
    for r, info in issued.items():
        for name, entry in info['files'].items():
            need(sha_file(folder / name) == entry['sha256'], f'{name} changed after issue')
            files[name] = entry
    body = {'schema': 'walking-force-scale-forecasts-seal-v1', 'protocol_sha256': sha_file(HERE / 'PROTOCOL.json'),
            'fit_complete_sha256': sha_file(fit_complete_path), 'eval_inputs_sha256': issued['sk']['eval_inputs_sha256'],
            'rows': issued['sk']['rows'], 'files': files,
            'not_issued_failed_fits': issued['torch']['not_issued_failed_fits'] + issued['sk']['not_issued_failed_fits'],
            'custody': 'The issuing processes read evaluation inputs only; targets were never opened before this seal.',
            'utc': datetime.now(timezone.utc).isoformat()}
    digest = write_json(publish_dir(cfg) / 'FORECASTS-SEAL.json', body)
    return body, digest


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('step', choices=('run', 'seal'))
    ap.add_argument('--config', required=True)
    ap.add_argument('--allocation', default=str(HERE / 'ALLOCATION.json'))
    ap.add_argument('--fit-complete', default=str(HERE / 'FIT-COMPLETE.json'))
    ap.add_argument('--runtime', choices=('torch', 'sk'))
    args = ap.parse_args()
    if args.step == 'run':
        print(json.dumps(run(args.config, args.allocation, args.fit_complete, args.runtime)))
    else:
        body, digest = seal(args.config, args.fit_complete)
        print(json.dumps({'files': len(body['files']), 'sha256': digest}))


if __name__ == '__main__':
    main()
