"""Fit stage: every fit of plan.jobs() in single-thread lanes, the F4 penalty choice, P1, and the seal.

  fit.py run  --config CFG --allocation A --runtime torch|sk [--lanes 12]   (runtime A for torch, B for sk)
  fit.py f4   --config CFG --allocation A                                  (runtime B)
  fit.py p1   --config CFG --allocation A --runtime torch|sk               (only when T >= 32)
  fit.py seal --config CFG --allocation A                                  (runtime B) -> FIT-COMPLETE.json

Lanes hold CPU slots (lanes.py, CPUs 20-31, at most 12) so that every track together stays within 16
threads on CPUs 16-31. Record chain per runtime: LOCK (job list, code, inputs), ATTEMPT, per-fit
checkpoint plus sidecar with reload equality, RESULT, and at the seal a READBACK of every file.
A failed fit keeps its failed sidecar and is never replaced; a rerun resumes only missing fits.
Checkpoints are written only under the private folder of the configuration.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from common import (HERE, base_people, canonical, code_hashes, hash_text, load_config, n_max, need, protocol_tag,
                    publish_dir, read_json, sha_bytes, sha_file, single_thread_env, write_json)

_W = {}


def fits_dir(cfg):
    return Path(cfg['private_dir']) / 'fits'


def job_paths(cfg, job):
    safe = job['id'].replace('|', '_')
    folder = fits_dir(cfg) / job['arm']
    ext = 'safetensors' if job['runtime'] == 'torch' else 'joblib'
    return folder / f'{safe}.{ext}', folder / f'{safe}.json'


def load_training(cfg):
    import extract
    folder = Path(cfg['private_dir']) / 'arrays'
    meta = read_json(folder / 'TRAIN-WALKS.json')
    need(sha_file(folder / 'TRAIN-INPUTS.npz') == meta['inputs_sha256'] and
         sha_file(folder / 'TRAIN-TARGETS.npz') == meta['targets_sha256'], 'training arrays changed')
    inputs = extract.load_npz(folder / 'TRAIN-INPUTS.npz', extract.INPUT_FIELDS)
    targets = extract.load_npz(folder / 'TRAIN-TARGETS.npz', extract.TARGET_FIELDS)
    return inputs, targets, meta


def members_of(meta, job):
    """Member indices of a job's training walks."""
    by_person = {}
    for w in meta['walks']:
        by_person.setdefault(w['subject'], []).append(w)
    out = []
    for person, trials in job['walks'].items():
        rows = by_person[person]
        out += [w['member_index'] for w in rows if trials is None or w['trial'] in trials]
    return sorted(out)


def budget_subsample(table, code_of_member, trial_of_member, job, tag, keep):
    """S4: rows ranked by sha256(TAG|example-budget|N|d|subject|walk|tick|plate); the lowest `keep` stay."""
    import numpy as np
    keys = [hash_text(f'{tag}|example-budget|{job["N"]}|{job["rung_draw_for_hash"]}|{code_of_member[int(m)]}|'
                      f'{trial_of_member[int(m)]}|{int(t)}|{int(p)}')
            for m, t, p in zip(table['member_index'], table['issue_tick'], table['plate'])]
    chosen = np.sort(np.argsort(np.asarray(keys), kind='stable')[:keep])
    return chosen


def _init(cfg_path, allocation_path, runtime, use_slots):
    single_thread_env()
    if use_slots:
        import lanes
        lanes.worker_init()
    import numpy as np
    import compact
    cfg = load_config(cfg_path)
    inputs, targets, meta = load_training(cfg)
    pom = {w['member_index']: w['participant_index'] for w in meta['walks']}
    com = {w['member_index']: w['subject'] for w in meta['walks']}
    tom = {w['member_index']: w['trial'] for w in meta['walks']}
    tables = {}
    for mode in ('current', 'none', 'earlier'):
        t = compact.training_table(inputs, targets, pom, emg_mode=mode)
        t['code'] = np.asarray([com[int(m)] for m in t['member_index']])
        tables[('c', mode)] = t
    if runtime == 'torch':
        import threepass
        threepass.setup_runtime()
    else:
        import trees
        for emg in (True, False):
            t = trees.tree_table(inputs, targets, pom, emg=emg)
            t['code'] = np.asarray([com[int(m)] for m in t['member']])
            tables[('t', emg)] = t
    base = tables[('c', 'current')]
    twelve = np.isin(base['code'], base_people(read_json(allocation_path)))
    _W.update(cfg=cfg, meta=meta, tables=tables, com=com, tom=tom, tag=protocol_tag(HERE / 'PROTOCOL.json')[1],
              rows12=int(base['impulse_supported'][twelve].sum()), union12=int(twelve.sum()))


def _subset(table, members):
    import numpy as np
    key = 'member_index' if 'member_index' in table else 'member'
    keep = np.isin(table[key], members)
    return {k: (v[keep] if hasattr(v, '__len__') and not isinstance(v, str) and len(v) == len(keep) else v)
            for k, v in table.items()}


def _fit_job(job):
    import numpy as np
    cfg, meta, tables = _W['cfg'], _W['meta'], _W['tables']
    ck, side = job_paths(cfg, job)
    if side.exists():
        return read_json(side)
    ck.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    members = members_of(meta, job)
    record = {'id': job['id'], 'arm': job['arm'], 'N': job['N'], 'kind': job['kind'], 'draw': job['draw'],
              'replicate': job['replicate'], 'seed': job['seed'], 'people': len(job['people']), 'walks': len(members),
              'cpu': sorted(os.sched_getaffinity(0)), 'pid': os.getpid(), 'utc': datetime.now(timezone.utc).isoformat()}
    try:
        arm = job['arm']
        fam = arm.split('-')[-1] if '-' in arm else arm
        if job['runtime'] == 'torch':
            import threepass
            mode = 'none' if arm.startswith('S2') else ('earlier' if arm.startswith('S6') else 'current')
            table = _subset(tables[('c', mode)], members)
            if arm.startswith('S4'):
                table = threepass.take(table, budget_subsample(table, _W['com'], _W['tom'], job, _W['tag'], _W['union12']))
            batch = threepass.TrainingBatch(table)
            width = 96 if arm == 'S3' else 24
            updates = threepass.epoch_matched_updates(batch.impulse_rows, _W['rows12']) if arm in ('S1', 'S3') else 900
            model, loss, seconds = threepass.train(batch, job['seed'], width=width, updates=updates, readout_only=arm == 'C4')
            record.update(width=width, updates=updates, examples_drawn=updates * 128, emg_mode=mode, rows=batch.rows,
                          impulse_rows=batch.impulse_rows, event_only_rows=batch.event_only_rows, prior=batch.prior,
                          last_batch_loss=loss, train_seconds=seconds, readout_only=arm == 'C4')
            record['tensor_sha256'] = threepass.save(model, ck)
            reloaded = threepass.load(ck, width=width)
            x = table['x'][:2048]
            p0, i0 = threepass.forecast(model, x, table['persistence'][:2048], batch.prior)
            p1, i1 = threepass.forecast(reloaded, x, table['persistence'][:2048], batch.prior)
            record['reload_identical'] = bool(np.array_equal(p0, p1) and np.array_equal(i0, i1))
        else:
            import joblib
            import linear
            import trees
            mode = 'none' if arm.startswith('S2') else ('earlier' if arm.startswith('S6') else 'current')
            if fam == 'M3':
                table = _subset(tables[('t', not arm.startswith('S2'))], members)
            else:
                table = _subset(tables[('c', mode)], members)
            if arm.startswith('S4'):
                # The compact and tree tables hold the same rows in the same (member, tick, plate) order.
                ref = _subset(tables[('c', 'current')], members)
                need(len(ref['code']) == len(table['code']), 'compact and tree tables differ in rows')
                keep = budget_subsample(ref, _W['com'], _W['tom'], job, _W['tag'], _W['union12'])
                n = len(table['code'])
                table = {k: (v[keep] if hasattr(v, '__len__') and not isinstance(v, (str, dict)) and len(v) == n else v)
                         for k, v in table.items()}
            if arm == 'G9-M3':
                chosen, folds = trees.choose_leaves(table, job['folds'])
                fitted = trees.fit_m3(table, chosen)
                record.update(tuned=chosen, inner_fold_means=folds)
            elif arm == 'G9-M2':
                chosen, folds = linear.choose_penalty(table, job['folds'])
                fitted = linear.fit_m2(table, chosen)
                record.update(tuned=chosen, inner_fold_means=folds)
            elif fam == 'M3':
                fitted = trees.fit_m3(table, force_only=arm.startswith('S2'))
            elif arm == 'S5':
                fitted = trees.fit_s5(table)
            else:
                fitted = linear.fit_m2(table)
            record.update(rows=int(len(table['code'])), impulse_rows=int(table['impulse_supported'].sum()),
                          event_rows=int(table['event_supported'].sum()), emg_mode=mode)
            with open(ck, 'xb') as stream:
                joblib.dump(fitted, stream, compress=0)
            probe = _probe(fitted, table, fam, arm)
            again = _probe(joblib.load(ck), table, fam, arm)
            record['prediction_sha256'] = sha_bytes(probe[0].tobytes() + probe[1].tobytes())
            record['reload_identical'] = bool(np.array_equal(probe[0], again[0]) and np.array_equal(probe[1], again[1]))
        record['file_sha256'] = sha_file(ck)
        record['status'] = 'done' if record['reload_identical'] else 'failed-reload'
    except Exception as error:  # a failed fit stays visible and is never replaced
        record['status'] = 'failed'
        record['error'] = f'{type(error).__name__}: {error}'[:500]
    record['seconds'] = time.perf_counter() - started
    write_json(side, record, exclusive=True)
    return record


def _probe(fitted, table, fam, arm):
    import trees
    import linear
    n = min(2048, len(table['code']))
    if fam == 'M3':
        return trees.predict_m3(fitted, table['history'][:n], table['available'][:n])
    if arm == 'S5':
        return trees.predict_compact(fitted, table['x'][:n], table['persistence'][:n])
    return linear.predict_m2(fitted, table['x'][:n], table['persistence'][:n])


def cost(job):
    weight = {'S3': 20, 'S1': 4, 'G9-M3': 30, 'G9-M2': 6, 'M3': 3, 'S2-M3': 3, 'S4-M3': 3}.get(job['arm'], 1)
    return weight * job['N']


def run(cfg_path, allocation_path, runtime, lanes_n, smoke=None, use_slots=True):
    import plan
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    cfg = load_config(cfg_path)
    allocation = read_json(allocation_path)
    job_list = [j for j in plan.jobs(allocation, smoke) if j['runtime'] == runtime]
    need(not allocation.get('smoke') or cfg.get('publish_dir'), 'a smoke allocation may only run in a synthetic test folder')
    need(1 <= lanes_n <= 12, 'between 1 and 12 lanes')
    folder = fits_dir(cfg)
    folder.mkdir(parents=True, exist_ok=True)
    meta = read_json(Path(cfg['private_dir']) / 'arrays' / 'TRAIN-WALKS.json')
    lock = {'stage': 'fit', 'runtime': runtime, 'protocol_sha256': sha_file(HERE / 'PROTOCOL.json'),
            'allocation_sha256': sha_file(allocation_path), 'jobs_sha256': sha_bytes(canonical(job_list)), 'jobs': len(job_list),
            'arms': plan.counts(job_list), 'training_inputs_sha256': meta['inputs_sha256'],
            'training_targets_sha256': meta['targets_sha256'], 'code_sha256': code_hashes(), 'smoke': smoke}
    lock_path = folder / f'LOCK-{runtime}.json'
    if lock_path.exists():
        need(read_json(lock_path) == json.loads(canonical(lock)), 'LOCK differs: inputs, code or job list changed since the first attempt')
    else:
        write_json(lock_path, lock, exclusive=True)
    attempt = folder / f'ATTEMPT-{runtime}.jsonl'
    with open(attempt, 'a') as stream:
        stream.write(json.dumps({'utc': datetime.now(timezone.utc).isoformat(), 'lanes': lanes_n, 'pid': os.getpid()}) + '\n')
    ordered = sorted(job_list, key=cost, reverse=True)
    results = []
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=lanes_n, mp_context=get_context('spawn'), initializer=_init,
                             initargs=(str(cfg_path), str(allocation_path), runtime, use_slots)) as pool:
        for rec in pool.map(_fit_job, ordered, chunksize=1):
            results.append({k: rec.get(k) for k in ('id', 'status', 'file_sha256', 'tensor_sha256', 'prediction_sha256', 'seconds')})
    summary = {'runtime': runtime, 'jobs': len(results), 'done': sum(r['status'] == 'done' for r in results),
               'failed': [r['id'] for r in results if r['status'] != 'done'], 'wall_seconds': time.perf_counter() - started,
               'lock_sha256': sha_file(lock_path), 'results': sorted(results, key=lambda r: r['id'])}
    write_json(folder / f'RESULT-{runtime}.json', summary)
    return summary


# ------------------------------------------------------------------------------------------ F4
def run_f4(cfg_path, allocation_path):
    single_thread_env()
    import numpy as np
    import extract
    import frozen
    import linear
    cfg = load_config(cfg_path)
    inputs, targets, meta = load_training(cfg)
    com = {w['member_index']: w['subject'] for w in meta['walks']}
    pool = set(p['subject'] for p in read_json(allocation_path)['groups']['training_pool'])
    in_pool = np.asarray([com[int(m)] in pool for m in inputs['member_index']])
    sup = extract.supports(inputs, targets)
    masks = {'event_main': sup['event'] & in_pool, 'impulse_main': sup['impulse'] & in_pool,
             'event_early': sup['event_early'] & in_pool, 'impulse_early': sup['impulse_early'] & in_pool}
    frozen.pinned(cfg['repo_root'])
    _mod, grid = frozen.f4_grid(cfg['repo_root'])
    choice, table = linear.f4_choose(grid.coefficients, inputs, targets, com, masks)
    body = {'schema': 'walking-force-scale-f4-choice-v1', 'rule': 'lowest person-equal error on the training-pool people '
            '(impulse MAE, new-load Brier); ties to the larger penalty', 'people': len(pool),
            'rows': {k: int(v.sum()) for k, v in masks.items()}, 'choice': choice, 'errors': table}
    write_json(fits_dir(cfg) / 'F4-CHOICE.json', body)
    return body


# ------------------------------------------------------------------------------------------ P1
def run_p1(cfg_path, allocation_path, runtime):
    single_thread_env()
    import numpy as np
    import compact
    import extract
    import plan
    cfg = load_config(cfg_path)
    allocation = read_json(allocation_path)
    tails = allocation['pool_tail_for_prediction_P1']
    need((allocation['sizes']['T'] >= 32 or allocation.get('smoke')) and tails, 'P1 runs only when T >= 32')
    inputs, targets, meta = load_training(cfg)
    com = {w['member_index']: w['subject'] for w in meta['walks']}
    code = np.asarray([com[int(m)] for m in inputs['member_index']])
    sup = extract.supports(inputs, targets)['impulse']
    fams = ('M1',) if runtime == 'torch' else ('M2', 'M3')
    out = {}
    for job in plan.jobs(allocation):
        if job['arm'] not in fams or job['kind'] not in ('12', 'mid'):
            continue
        ck, side = job_paths(cfg, job)
        rec = read_json(side)
        if rec.get('status') != 'done':
            continue
        need(sha_file(ck) == rec['file_sha256'], f'checkpoint changed: {job["id"]}')
        draws = [str(job['draw'])] if job['kind'] == 'mid' else sorted(tails)
        for d in draws:
            rows = np.flatnonzero(sup & np.isin(code, tails[d]))
            prob, imp = _issue_one(job, ck, rec, inputs, rows)
            err = np.zeros(len(code))
            err[rows] = np.abs(imp - targets['signed_impulse_ns'][rows])
            mask = np.zeros(len(code), bool)
            mask[rows] = True
            per = compact.person_errors(code, inputs['member_index'], inputs['issue_tick'], mask, err)
            out.setdefault(job['arm'], {}).setdefault(d, {}).setdefault(str(job['N']), {})[job['id']] = per
    write_json(fits_dir(cfg) / f'P1-{runtime}.json', out)
    return out


def _issue_one(job, ck, rec, inputs, rows):
    """Forecasts of one sealed fit on given input rows (shared by P1 and the issue stage)."""
    import compact
    fam = job['arm'].split('-')[-1] if '-' in job['arm'] else job['arm']
    mode = 'none' if job['arm'].startswith('S2') else ('earlier' if job['arm'].startswith('S6') else 'current')
    if job['runtime'] == 'torch':
        import threepass
        model = threepass.load(ck, width=rec['width'])
        x, pers = compact.compact_inputs(inputs, rows, emg_mode=mode)
        return threepass.forecast(model, x, pers, rec['prior'])
    import joblib
    import linear
    import trees
    fitted = joblib.load(ck)
    if fam == 'M3':
        h, av = trees.tree_history(inputs, rows, emg=not job['arm'].startswith('S2'))
        return trees.predict_m3(fitted, h, av)
    x, pers = compact.compact_inputs(inputs, rows, emg_mode=mode)
    if job['arm'] == 'S5':
        return trees.predict_compact(fitted, x, pers)
    return linear.predict_m2(fitted, x, pers)


# ----------------------------------------------------------------------------------------- seal
def training_counts(inputs, targets, meta, people):
    import numpy as np
    import extract
    com = {w['member_index']: w['subject'] for w in meta['walks']}
    code = np.asarray([com[int(m)] for m in inputs['member_index']])
    keep = np.isin(code, list(people))
    sup = extract.supports(inputs, targets)
    pos = keep & sup['event'] & (targets['event_new_load'] == 1)
    onsets = {(int(m), int(p), int(o)) for m, p, o in zip(inputs['member_index'][pos], inputs['plate'][pos], targets['onset_tick'][pos])}
    return {'people': len(set(code[keep])), 'walks': len(set(inputs['member_index'][keep].tolist())),
            'issue_rows': int(keep.sum()), 'impulse_rows': int((keep & sup['impulse']).sum()),
            'event_rows': int((keep & sup['event']).sum()), 'positive_rows': int(pos.sum()), 'distinct_onsets': len(onsets)}


def seal(cfg_path, allocation_path):
    single_thread_env()
    import plan
    import trend
    cfg = load_config(cfg_path)
    allocation = read_json(allocation_path)
    folder = fits_dir(cfg)
    inputs, targets, meta = load_training(cfg)
    job_list = plan.jobs(allocation)
    checkpoints, readback_ok = [], True
    for job in job_list:
        ck, side = job_paths(cfg, job)
        need(side.exists(), f'missing fit record {job["id"]}: run the fit stage first')
        rec = read_json(side)
        row = {'id': job['id'], 'status': rec['status'], 'file': f'{job["arm"]}/{ck.name}'}
        if rec['status'] == 'done':
            same = sha_file(ck) == rec['file_sha256']
            readback_ok &= same
            row.update(file_sha256=rec['file_sha256'], readback_equal=same)
            for k in ('tensor_sha256', 'prediction_sha256', 'updates', 'examples_drawn', 'rows', 'impulse_rows', 'tuned'):
                if k in rec:
                    row[k] = rec[k]
        else:
            row['error'] = rec.get('error', rec['status'])
        checkpoints.append(row)
    write_json(folder / 'READBACK.json', {'files': len(checkpoints), 'all_equal': bool(readback_ok)})
    sets = {}
    for tset in plan.training_sets(allocation):
        key = f'N{tset["N"]:03d}|d{"x" if tset["draw"] is None else tset["draw"]}'
        sets[key] = training_counts(inputs, targets, meta, tset['people'])
    f4 = read_json(folder / 'F4-CHOICE.json')
    p1 = None
    if (allocation['sizes']['T'] >= 32 or allocation.get('smoke')) and allocation['pool_tail_for_prediction_P1']:
        raw = {**read_json(folder / 'P1-torch.json'), **read_json(folder / 'P1-sk.json')}
        p1 = {}
        top = n_max(allocation)
        for fam in ('M1', 'M2', 'M3'):
            curves = {}
            for d, by_n in raw[fam].items():
                curves[d] = {}
                for n, fits in by_n.items():
                    people = sorted(set().union(*[set(v) for v in fits.values()]))
                    curves[d][int(n)] = float(sum(sum(f[p] for f in fits.values()) / len(fits) for p in people) / len(people))
            p1[fam] = trend.p1_curve(curves, top)
    body = {'schema': 'walking-force-scale-fit-complete-v1', 'protocol_sha256': sha_file(HERE / 'PROTOCOL.json'),
            'allocation_sha256': sha_file(allocation_path), 'training_inputs_sha256': meta['inputs_sha256'],
            'training_targets_sha256': meta['targets_sha256'], 'code_sha256': code_hashes(),
            'lock_sha256': {r: sha_file(folder / f'LOCK-{r}.json') for r in ('torch', 'sk')},
            'fits': len(checkpoints), 'failed_fits': [c['id'] for c in checkpoints if c['status'] != 'done'],
            'readback_all_equal': bool(readback_ok), 'training_sets': sets, 'F4_penalties': f4['choice'],
            'F4_training_pool_errors': f4['errors'], 'P1_pool_tail_prediction': p1, 'checkpoints': checkpoints,
            'utc': datetime.now(timezone.utc).isoformat()}
    digest = write_json(publish_dir(cfg) / 'FIT-COMPLETE.json', body)
    return body, digest


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('step', choices=('run', 'f4', 'p1', 'seal'))
    ap.add_argument('--config', required=True)
    ap.add_argument('--allocation', default=str(HERE / 'ALLOCATION.json'))
    ap.add_argument('--runtime', choices=('torch', 'sk'))
    ap.add_argument('--lanes', type=int, default=12)
    args = ap.parse_args()
    if args.step == 'run':
        single_thread_env()
        summary = run(args.config, args.allocation, args.runtime, args.lanes)
        print(json.dumps({k: summary[k] for k in ('runtime', 'jobs', 'done', 'failed', 'wall_seconds')}))
    elif args.step == 'f4':
        print(json.dumps(run_f4(args.config, args.allocation)['choice']))
    elif args.step == 'p1':
        run_p1(args.config, args.allocation, args.runtime)
    else:
        body, digest = seal(args.config, args.allocation)
        print(json.dumps({'fits': body['fits'], 'failed': len(body['failed_fits']), 'sha256': digest}))


if __name__ == '__main__':
    sys.exit(main())
