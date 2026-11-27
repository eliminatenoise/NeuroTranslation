"""Extraction stage: checked walk files -> history-only inputs and, in a separate file, targets.

  prepare.py --config CFG --group training     (after D2: the 12 earlier fit people + the training pool)
  prepare.py --config CFG --group evaluation   (after D3)

Writes into <private>/arrays/: <GROUP>-INPUTS.npz, <GROUP>-TARGETS.npz and <GROUP>-WALKS.json. The
issuing process reads only the INPUTS file. Training walks with no supported rows stay in the table
(they add no rows) and are counted. Runtime B.
"""
import argparse
import json
from pathlib import Path

from common import load_config, need, read_json, sha_file, single_thread_env, write_json


def allocation_walks(allocation):
    """(subject, member) for the training pool and the evaluation group: the only walks this track reads."""
    return [(p['subject'], m) for g in ('training_pool', 'evaluation') for p in allocation['groups'][g] for m in p['walks']]


def build_table(allocation):
    import walks
    return walks.walk_table(allocation_walks(allocation))


def run(cfg, allocation_path, group):
    single_thread_env()
    import numpy as np
    import extract
    import walks

    allocation = read_json(allocation_path)
    table = build_table(allocation)
    private = Path(cfg['private_dir'])
    folder = private / 'arrays'
    folder.mkdir(parents=True, exist_ok=True)
    stage = 'D2' if group == 'training' else 'D3'
    receipt = read_json(private / 'receipts' / f'{stage}-RECEIPT.json')
    need(receipt['allocation_sha256'] == sha_file(allocation_path), 'download receipt made for another allocation')
    got = {(r['subject'], r['trial']): r for r in receipt['members']}
    people = {p['subject'] for p in allocation['groups']['training_pool' if group == 'training' else 'evaluation']}
    rows_i, rows_t, listing = [], [], []
    sources = []
    if group == 'training':
        base = set(allocation['twelve_person_rung'])
        fit = {(s, t): (m, data, digest) for s, t, m, data, digest in walks.load_fit12(cfg) if s in base}
        sources += [(r, *fit[(r['subject'], r['trial'])]) for r in table if (r['subject'], r['trial']) in fit]
    for r in table:
        if r['subject'] in people:
            rec = got[(r['subject'], r['trial'])]
            data, digest = walks.read_checked(private / 'walks' / rec['file'], r['member'], rec['decoded_sha256'])
            sources.append((r, r['member'], data, digest))
    for r, member, data, digest in sources:
        inp, tgt, n = extract.walk_arrays(data, r['member_index'], member['expanded_bytes'])
        sup = extract.supports(inp, tgt)
        rows_i.append(inp)
        rows_t.append(tgt)
        listing.append({'member_index': r['member_index'], 'participant_index': r['participant_index'],
                        'subject': r['subject'], 'trial': r['trial'], 'decoded_sha256': digest, 'samples': n,
                        'issue_rows': int(len(inp['plate'])), 'input_valid_rows': int(extract.input_valid(inp).sum()),
                        'impulse_rows': int(sup['impulse'].sum()), 'event_rows': int(sup['event'].sum())})
    inputs = extract.concat(rows_i, extract.INPUT_FIELDS)
    targets = extract.concat(rows_t, extract.TARGET_FIELDS)
    name = 'TRAIN' if group == 'training' else 'EVAL'
    extract.save_npz(folder / f'{name}-INPUTS.npz', inputs, extract.INPUT_FIELDS)
    extract.save_npz(folder / f'{name}-TARGETS.npz', targets, extract.TARGET_FIELDS)
    dropped = [w for w in listing if w['impulse_rows'] == 0 and w['event_rows'] == 0]
    meta = {'schema': 'walking-force-scale-walks-v1', 'group': group, 'allocation_sha256': sha_file(allocation_path),
            'walks': listing, 'walks_without_supported_rows': len(dropped),
            'inputs_sha256': sha_file(folder / f'{name}-INPUTS.npz'), 'targets_sha256': sha_file(folder / f'{name}-TARGETS.npz'),
            'people': len({w['subject'] for w in listing}), 'rows': int(len(inputs['plate']))}
    write_json(folder / f'{name}-WALKS.json', meta, exclusive=True)
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--config', required=True)
    ap.add_argument('--allocation', required=True)
    ap.add_argument('--group', choices=('training', 'evaluation'), required=True)
    args = ap.parse_args()
    meta = run(load_config(args.config), args.allocation, args.group)
    print(json.dumps({k: meta[k] for k in ('group', 'people', 'rows', 'walks_without_supported_rows')}))


if __name__ == '__main__':
    main()
