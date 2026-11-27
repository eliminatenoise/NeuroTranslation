"""Independent replay for stage S-c: every primary aggregate and sample rows from each plate.

Written separately from score.py: person weights and per-person errors are recomputed with plain
loops, and the targets of sampled rows are recomputed from the decoded evaluation walk files by
summing the plate samples directly. Runtime B.

  replay.py --config CFG [--rows-per-plate 20]
"""
import argparse
import json
import zlib
from collections import defaultdict
from pathlib import Path

from common import load_config, need, private_folder, publish_dir, read_json, sha_file, single_thread_env, write_json


def loop_person_errors(code, member, tick, mask, error):
    """people -> walks -> ticks -> plates equal weights, then within-person weighted mean (plain loops)."""
    rows = [i for i in range(len(code)) if mask[i]]
    by_person = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for i in rows:
        by_person[code[i]][int(member[i])][int(tick[i])].append(i)
    out = {}
    for person, walks in by_person.items():
        total, mass = 0.0, 0.0
        for ticks in walks.values():
            for plates in ticks.values():
                w = 1.0 / (len(walks) * len(ticks) * len(plates))
                for i in plates:
                    total += w * float(error[i])
                    mass += w
        out[person] = total / mass
    return out


def run(cfg, rows_per_plate):
    single_thread_env()
    import numpy as np
    import c3dread
    import extract
    results = read_json(Path(cfg['out_dir']) / 'RESULTS.json')
    seal = read_json(publish_dir(cfg) / 'FORECASTS-SEAL.json')
    folder = Path(cfg['private_dir'])
    arrays, eval_walks = private_folder(cfg, 'evaluation', 'arrays'), private_folder(cfg, 'evaluation', 'walks')
    meta = read_json(arrays / 'EVAL-WALKS.json')
    inputs = extract.load_npz(arrays / 'EVAL-INPUTS.npz', extract.INPUT_FIELDS)
    targets = extract.load_npz(arrays / 'EVAL-TARGETS.npz', extract.TARGET_FIELDS)
    com = {w['member_index']: w['subject'] for w in meta['walks']}
    files = {}
    for name, entry in seal['files'].items():
        need(sha_file(folder / 'forecasts' / name) == entry['sha256'], f'{name} changed')
        files[name] = np.load(folder / 'forecasts' / name)
    rows = next(iter(files.values()))['rows']
    code = [com[int(m)] for m in inputs['member_index'][rows]]
    member, tick = inputs['member_index'][rows], inputs['issue_tick'][rows]
    valid = inputs['emg_ok'][rows] & inputs['past_force_ok'][rows]
    imp = targets['signed_impulse_ns'][rows]
    mask = valid & np.isfinite(imp)
    worst = 0.0
    checked = 0
    for fam, by_n in results['curves']['impulse'].items():
        for n, entry in by_n.items():
            # replay one replicate per rung exactly, and the rung mean from all replicates
            per_rep = []
            prefix = f'{fam}_N{int(n):03d}_'
            for z in files.values():
                for k in z.files:
                    if k.startswith(prefix) and k.endswith('::i'):
                        err = np.where(mask, np.abs(z[k] - np.nan_to_num(imp)), 0.0)
                        per_rep.append(loop_person_errors(code, member, tick, mask, err))
            need(len(per_rep) == entry['fits_used'], f'replicate count differs for {fam} N={n}')
            for person, value in entry['per_person'].items():
                mine = sum(r[person] for r in per_rep) / len(per_rep)
                worst = max(worst, abs(mine - value))
                checked += 1
    # sample rows of each plate: recompute the impulse target from the decoded walk
    rng = np.random.default_rng(20261127)
    by_member = {w['member_index']: w for w in meta['walks']}
    row_checks = []
    for plate in (1, 2):
        candidates = np.flatnonzero(mask & (inputs['plate'][rows] == plate))
        for r in rng.choice(candidates, size=min(rows_per_plate, len(candidates)), replace=False):
            m, t = int(member[r]), int(tick[r])
            w = by_member[m]
            data = (eval_walks / f'{w["subject"]}-{w["trial"]}.c3d').read_bytes()
            need(f'{zlib.crc32(data):08x}' == w.get('crc32', f'{zlib.crc32(data):08x}'), 'walk file changed')
            parsed = c3dread.parse(data[:262144])
            _v, _r, lay, _d = c3dread.layout(parsed, len(data))
            col = lay['force_z_columns'][plate - 1]
            force = c3dread.read_columns(memoryview(data), lay, [col])[:, 0] * c3dread.plate_normal_z(lay)[plate - 1]
            direct = float(sum(float(v) for v in force[t + 1:t + 101]) / 1000.0)
            row_checks.append(abs(direct - float(imp[r])))
    body = {'aggregates_checked': checked, 'aggregate_max_abs_difference': worst,
            'rows_checked': len(row_checks), 'row_target_max_abs_difference': max(row_checks) if row_checks else None,
            'passed': worst <= 1e-9 and (not row_checks or max(row_checks) <= 1e-9)}
    write_json(Path(cfg['out_dir']) / 'REPLAY.json', body)
    return body


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--config', required=True)
    ap.add_argument('--rows-per-plate', type=int, default=20)
    args = ap.parse_args()
    print(json.dumps(run(load_config(args.config), args.rows_per_plate)))


if __name__ == '__main__':
    main()
