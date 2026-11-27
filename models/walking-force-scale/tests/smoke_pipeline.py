"""End-to-end smoke run of every stage on the 12 consumed fit people only, with reduced seed counts.

Base rung: 4 fit people; "training pool": 5 fit people; "evaluation": 3 fit people; plus synthetic
QP and X people made by patching copies of fit walks. All bytes come from the earlier fit cache,
served by a local emulator; nothing leaves the machine and no evaluation, reserved, physics or
supplement byte of the real pool is involved. Stages: D1 probe -> allocation -> D2 -> extraction ->
fits (both runtimes, lanes with CPU slots) -> F4 choice -> P1 -> FIT-COMPLETE -> D3 -> issue (both
runtimes) -> FORECASTS-SEAL -> S-b and P2 -> commit of P2 in a scratch repository -> S-c -> replay.
Custody checks: D3 refuses before the fit seal; the evaluation walks, receipts and EVAL-* arrays land
only in eval-walks/ and eval-arrays/, never in the walks/ and arrays/ folders physics-source may read;
S-b opens only the below-N_max file; S-c refuses an uncommitted P2.

  python -B tests/smoke_pipeline.py --config CFG --python-a PY_A --python-b PY_B     (run with runtime B)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402
import allocate  # noqa: E402
import fetch  # noqa: E402
import fit  # noqa: E402
import issue  # noqa: E402
import prepare  # noqa: E402
import replay  # noqa: E402
import score  # noqa: E402
from common import (HERE, PHYSICS_SOURCE_READABLE, hash_text, load_config, private_folder, read_json,  # noqa: E402
                    write_json)

BASE = ['SUBJ024', 'SUBJ038', 'SUBJ039', 'SUBJ040']
OTHERS = ['SUBJ043', 'SUBJ044', 'SUBJ061', 'SUBJ062', 'SUBJ082', 'SUBJ096', 'SUBJ110', 'SUBJ112']
TAG = 'smoke|walking-scale|synthetic'


def expect_refusal(fn):
    try:
        fn()
        return False
    except SystemExit:
        return True


def build_allocation(qual, pool, members_by_path):
    q6 = sorted((s for s, p in qual['people'].items() if p['class'] == 'Q6'), key=lambda s: hash_text(f'{TAG}|{s}'))
    qp = sorted(s for s, p in qual['people'].items() if p['class'] == 'QP')
    xs = sorted(s for s, p in qual['people'].items() if p['class'] == 'X')
    cand = {c['subject']: c for c in pool['candidates']}

    def walks(s):
        by_trial = {m['trial']: m for m in cand[s]['probe_first'] + cand[s]['probe_if_needed']}
        return [by_trial[t] for t in qual['people'][s]['trials']]

    e_group, t_group = q6[:3], q6[3:]
    draws = {a: [sorted(sorted(t_group, key=lambda s: hash_text(f'{TAG}|rung-draw-{d}|{s}'))[:a]) for d in range(2)] for a in (1, 3)}
    rungs = [{'added': a, 'N': 4 + a, 'draws': [{'draw': d, 'added_people': x, 'inner_folds': allocate.folds(TAG, BASE + x)}
                                                for d, x in enumerate(draws[a])]} for a in (1, 3)]
    rungs.append({'added': len(t_group), 'N': 4 + len(t_group),
                  'draws': [{'draw': 0, 'added_people': sorted(t_group), 'inner_folds': allocate.folds(TAG, BASE + t_group)}]})
    tails = {str(d): sorted(sorted(t_group, key=lambda s: hash_text(f'{TAG}|rung-draw-{d}|{s}'))[3:]) for d in range(2)}
    first = sorted(t_group, key=lambda s: hash_text(f'{TAG}|rung-draw-0|{s}'))
    variety = {'one_walk_each': {s: walks(s)[int(hash_text(f'{TAG}|variety-walk|{s}'), 16) % 3]['trial'] for s in sorted(t_group)},
               'three_walks_each': sorted(first[:len(t_group) // 3])}
    listing = lambda group: [{'subject': s, 'walks': walks(s)} for s in sorted(group)]  # noqa: E731
    return {'schema': 'walking-force-scale-allocation-v1', 'step': 'assign', 'smoke': {'seeds': 2},
            'sizes': {'Q': len(q6), 'E': 3, 'P': 0, 'T': len(t_group), 'ladder': 'run', 'added': [1, 3, len(t_group)],
                      'N': [4, 5, 7, 4 + len(t_group)]},
            'groups': {'evaluation': listing(e_group), 'physics_source': [], 'training_pool': listing(t_group),
                       'physics_supplement': listing(qp), 'unusable': [{'subject': s, 'reason': qual['people'][s]['reason']} for s in xs],
                       'unallocated_unopened': [], 'excluded_boundary_never_opened': []},
            'twelve_person_rung': sorted(BASE), 'rung_zero_inner_folds': allocate.folds(TAG, BASE), 'rungs': rungs,
            'pool_tail_for_prediction_P1': tails, 'variety_control': variety}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--python-a', required=True)
    ap.add_argument('--python-b', required=True)
    ap.add_argument('--keep', action='store_true')
    args = ap.parse_args()
    base_cfg = read_json(args.config)
    root = Path(base_cfg['scratch_dir']) / 'smoke'
    shutil.rmtree(root, ignore_errors=True)
    repo = root / 'repo'
    publish = repo / 'models' / 'walking-force-scale'
    publish.mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    cfg_path = root / 'smoke-config.json'
    write_json(cfg_path, {**base_cfg, 'private_dir': str(root / 'private'), 'out_dir': str(root / 'out'),
                          'publish_dir': str(publish), 'publish_repo': str(repo)})
    cfg = load_config(cfg_path)
    env = {**os.environ, 'NS_CPU_SLOTS': os.environ.get('NS_CPU_SLOTS', '')}
    report = {}

    def cli(python, script, *extra):
        cmd = [python, '-B', str(HERE / script), *extra, '--config', str(cfg_path)]
        done = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if done.returncode != 0:
            raise RuntimeError(f'{script} {extra} failed:\n{done.stdout[-2000:]}\n{done.stderr[-4000:]}')
        return done.stdout

    walks = synthetic.fit_walk_bytes(cfg)
    entries, pool = [], {'candidates': []}
    for s in OTHERS:
        entries += [(walks[(s, t)][0], walks[(s, t)][1]) for (p, t) in sorted(walks) if p == s]
    qp_walks = [synthetic.relabel(walks[('SUBJ024', t)][1], 'Voltage.LBF', 'Voltage.12') for t in (1, 2, 3)]
    x_walks = [synthetic.plate_type(walks[('SUBJ038', t)][1], 3) for t in (1, 2, 3)]
    entries += [(f'synthetic/SUBJ901/SUBJ901 ({k + 1}).c3d', d) for k, d in enumerate(qp_walks)]
    entries += [(f'synthetic/SUBJ902/SUBJ902 ({k + 1}).c3d', d) for k, d in enumerate(x_walks)]
    blob, members = synthetic.build_archive(entries)
    for s in OTHERS:
        trials = sorted(t for (p, t) in walks if p == s)
        pool['candidates'].append({'subject': s, 'probe_first': [{**members[walks[(s, t)][0]], 'trial': t} for t in trials], 'probe_if_needed': []})
    for s in ('SUBJ901', 'SUBJ902'):
        pool['candidates'].append({'subject': s, 'probe_first': [{**members[f'synthetic/{s}/{s} ({t}).c3d'], 'trial': t} for t in (1, 2, 3)],
                                   'probe_if_needed': []})
    pool_path = root / 'POOL-smoke.json'
    write_json(pool_path, pool)
    emu = synthetic.Emulator(blob)
    try:
        client = fetch.Client(emu.identity, root / 'private' / 'receipts' / 'requests.jsonl', min_interval=0.02,
                              retry_wait=0.1, allow_plain_http=True)
        qual, _ = fetch.run_probe(cfg, pool_path, HERE / 'PROTOCOL.json', 'smoke test (no lease needed: local emulator)', client=client)
        report['D1_counts'] = qual['counts']
        allocation = build_allocation(qual, pool, members)
        alloc_path = publish / 'ALLOCATION.json'
        write_json(alloc_path, allocation)
        report['D3_refused_before_fit_seal'] = expect_refusal(
            lambda: fetch.run_download(cfg, alloc_path, 'evaluation', 'smoke', client=client, fit_complete=None))
        report['physics_download_refused'] = expect_refusal(lambda: fetch.run_download(cfg, alloc_path, 'physics_supplement', 'smoke', client=client))
        fetch.run_download(cfg, alloc_path, 'training_pool', 'smoke', client=client)
        meta = prepare.run(cfg, alloc_path, 'training')
        report['training_arrays'] = {k: meta[k] for k in ('people', 'rows', 'walks_without_supported_rows')}
        for runtime, python in (('torch', args.python_a), ('sk', args.python_b)):
            out = cli(python, 'fit.py', 'run', '--allocation', str(alloc_path), '--runtime', runtime, '--lanes', '3')
            report[f'fit_{runtime}'] = json.loads(out.strip().splitlines()[-1])
            cli(python, 'fit.py', 'p1', '--allocation', str(alloc_path), '--runtime', runtime)
        fit.run_f4(cfg_path, alloc_path)
        body, _digest = fit.seal(cfg_path, alloc_path)
        report['fit_complete'] = {'fits': body['fits'], 'failed': body['failed_fits'], 'readback': body['readback_all_equal'],
                                  'P1_present': body['P1_pool_tail_prediction'] is not None}
        fetch.run_download(cfg, alloc_path, 'evaluation', 'smoke', client=client, fit_complete=publish / 'FIT-COMPLETE.json')
        prepare.run(cfg, alloc_path, 'evaluation')
    finally:
        emu.close()
    eval_people = {p['subject'] for p in allocation['groups']['evaluation']}
    shared = [root / 'private' / f for f in PHYSICS_SOURCE_READABLE]
    in_shared = sorted(str(f.relative_to(root)) for d in shared for f in d.rglob('*')
                       if f.name.startswith('EVAL-') or f.name.split('-')[0] in eval_people)
    report['custody_eval_files_outside_shared_folders'] = {
        'eval_files_in_physics_readable_folders': in_shared,
        'eval_walks': len(list(private_folder(cfg, 'evaluation', 'walks').glob('*.c3d'))),
        'eval_arrays': sorted(f.name for f in private_folder(cfg, 'evaluation', 'arrays').glob('EVAL-*')),
        'passed': not in_shared and len(list(private_folder(cfg, 'evaluation', 'walks').glob('*.c3d'))) == 3 * len(eval_people)}
    fitc = publish / 'FIT-COMPLETE.json'
    for runtime, python in (('torch', args.python_a), ('sk', args.python_b)):
        cli(python, 'issue.py', 'run', '--allocation', str(alloc_path), '--fit-complete', str(fitc), '--runtime', runtime)
    seal_body, _ = issue.seal(cfg_path, fitc)
    seal_path = publish / 'FORECASTS-SEAL.json'
    report['forecast_files'] = sorted(seal_body['files'])
    sb = score.Scorer(cfg, alloc_path, fitc, seal_path, allowed_groups=('PRIMARY-BELOW-NMAX',))
    report['S_b_reads_only_below_nmax'] = all('BELOW-NMAX' in n for n in sb.forecasts) and len(sb.forecasts) == 2
    p2, p2_sha = score.stage_below(cfg, alloc_path, fitc, seal_path)
    report['P2'] = {'trend_test': p2['trend_test'], 'rungs_below': p2['rungs_below_n_max'],
                    'bootstrap_lengths': sorted({len(v) for f in p2['families'].values() for v in f.get('bootstrap_predictions', {}).values()})}
    try:
        score.stage_final(cfg, alloc_path, fitc, seal_path, p2_sha)
        report['S_c_refuses_uncommitted_P2'] = False
    except (SystemExit, subprocess.CalledProcessError):
        report['S_c_refuses_uncommitted_P2'] = True
    git = ['git', '-C', str(repo), '-c', 'user.name=smoke', '-c', 'user.email=smoke@invalid']
    subprocess.run(git + ['add', 'models/walking-force-scale/P2-TREND-PREDICTION.json'], check=True)
    subprocess.run(git + ['commit', '-q', '-m', 'smoke P2'], check=True)
    results, _ = score.stage_final(cfg, alloc_path, fitc, seal_path, p2_sha)
    report['S_c'] = {'labels': {f: results['primary_impulse'][f]['label'] for f in ('M1', 'M2', 'M3')},
                     'trend_test_families': sorted(results['trend_test']) if isinstance(results['trend_test'], dict) else results['trend_test'],
                     'F3_first_test': {k: v.get('reading') for k, v in results['F3_past_load_gate_first_test'].items()},
                     'counts': results['counts'], 'secondary_arms': sorted(results['secondary_arms'])}
    report['replay'] = replay.run(cfg, 6)
    report['passed'] = (report['D1_counts'] == {'Q6': 8, 'QP': 1, 'X': 1} and report['D3_refused_before_fit_seal']
                        and report['physics_download_refused'] and not report['fit_complete']['failed']
                        and report['fit_complete']['readback'] and report['fit_complete']['P1_present']
                        and report['S_b_reads_only_below_nmax'] and report['S_c_refuses_uncommitted_P2']
                        and report['P2']['trend_test'] and report['P2']['bootstrap_lengths'] == [10000]
                        and report['replay']['passed'] and report['custody_eval_files_outside_shared_folders']['passed'])
    write_json(Path(base_cfg['out_dir']) / 'tests' / 'smoke_pipeline.json', report)
    print(json.dumps(report, indent=1))
    if not args.keep:
        shutil.rmtree(root, ignore_errors=True)
    sys.exit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
