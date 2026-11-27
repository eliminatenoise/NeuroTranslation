"""Checked front end for `allocate.py assign` (admission review, minor 6). Standard library only.

allocate.py is pinned by sha256 in PROTOCOL.json, so it stays byte for byte as committed in C1. This
wrapper adds the checks it leaves to review, then calls its make_allocation() unchanged:
- allocate.py itself, POOL.json and ORDER.json equal their committed versions (allocate.py check);
- QUALIFICATION.json carries the protocol sha256 AND the pool sha256;
- each person's probed walks follow the rule (4th and 5th walks only when one of the first three is
  not Q6, lowest number first), the class follows from the walk verdicts, and the listed walks are the
  three lowest-numbered Q6 walks (Q6) or Q6-or-QP walks (QP);
- after assignment: groups are disjoint, cover the 80 candidates, follow the primary order, and the
  sizes equal allocate.sizes(Q).

  assign.py --qualification QUALIFICATION.json [--directory CD.bin] [--out ALLOCATION.json]
"""
import argparse
import json
from pathlib import Path

import allocate
import qualify
from common import HERE, hash_text, need, read_json, sha_bytes, sha_file, write_json

ALLOCATE_SHA256 = read_json(HERE / 'PROTOCOL.json')['companion_files']['allocate.py']['sha256']
POOL_SHA256 = read_json(HERE / 'PROTOCOL.json')['companion_files']['POOL.json']['sha256']


def checked_allocation(qualification_path, protocol_path, pool_path, directory=None):
    need(sha_file(HERE / 'allocate.py') == ALLOCATE_SHA256, 'allocate.py differs from its protocol pin')
    pool_raw = Path(pool_path).read_bytes()
    need(sha_bytes(pool_raw) == POOL_SHA256, 'POOL.json differs from its protocol pin')
    pool = json.loads(pool_raw)
    protocol_sha = sha_file(protocol_path)
    order = read_json(HERE / 'ORDER.json')
    need(order['protocol_sha256'] == protocol_sha and order['pool_sha256'] == POOL_SHA256, 'ORDER.json was made for another protocol or pool')
    if directory is not None:
        fresh = (json.dumps(allocate.make_order(protocol_path, pool, POOL_SHA256), indent=1, ensure_ascii=True) + '\n').encode('ascii')
        need(fresh == (HERE / 'ORDER.json').read_bytes(), 'ORDER.json does not recompute byte for byte')
        fresh_pool = (json.dumps(allocate.make_pool(directory), indent=1, ensure_ascii=True) + '\n').encode('ascii')
        need(fresh_pool == pool_raw, 'POOL.json does not recompute byte for byte')
    qual = allocate.load_json(qualification_path)
    problems = qualify.check_receipt(qual, pool, protocol_sha, POOL_SHA256)
    need(not problems, f'QUALIFICATION.json fails: {problems[:12]}')
    result = allocate.make_allocation(protocol_path, pool, qual)
    post_checks(result, pool, qual, protocol_sha)
    result['pool_sha256'] = POOL_SHA256
    result['checked_by'] = {'assign.py': sha_file(Path(__file__)), 'qualify.py': sha_file(HERE / 'qualify.py'),
                            'allocate.py': ALLOCATE_SHA256}
    return result


def post_checks(result, pool, qual, protocol_sha):
    tag = f'{allocate.DOI}|walking-scale|{protocol_sha}'
    groups = result['groups']
    named = {g: [p['subject'] for p in groups[g]] for g in ('evaluation', 'physics_source', 'training_pool', 'physics_supplement')}
    named['unusable'] = [p['subject'] for p in groups['unusable']]
    named['unallocated_unopened'] = list(groups['unallocated_unopened'])
    flat = [s for v in named.values() for s in v]
    candidates = {c['subject'] for c in pool['candidates']}
    need(len(flat) == len(set(flat)) and set(flat) == candidates, 'groups are not a partition of the candidates')
    q6 = [s for s in sorted(candidates, key=lambda s: hash_text(f'{tag}|{s}')) if qual['people'][s]['class'] == 'Q6']
    plan = allocate.sizes(len(q6))
    need(result['sizes'] == plan, 'sizes differ from the rule')
    need(sorted(named['evaluation']) == sorted(q6[:plan['E']]), 'evaluation group is not the first E qualified people')
    need(sorted(named['physics_source']) == sorted(q6[plan['E']:plan['E'] + plan['P']]), 'physics group is not the next P')
    for g in ('evaluation', 'physics_source', 'training_pool', 'physics_supplement'):
        for p in groups[g]:
            need([m['trial'] for m in p['walks']] == qual['people'][p['subject']]['trials'], f'{p["subject"]} walks differ from the receipt')
    for rung in result['rungs']:
        for d in rung['draws']:
            need(set(d['added_people']) <= set(named['training_pool']) and len(d['added_people']) == rung['added'], 'rung draw')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--qualification', required=True)
    ap.add_argument('--protocol', default=str(HERE / 'PROTOCOL.json'))
    ap.add_argument('--pool', default=str(HERE / 'POOL.json'))
    ap.add_argument('--directory', help='pinned central directory, to recompute POOL.json and ORDER.json')
    ap.add_argument('--out', default=str(HERE / 'ALLOCATION.json'))
    args = ap.parse_args()
    result = checked_allocation(args.qualification, args.protocol, args.pool, args.directory)
    need(not Path(args.out).exists() or args.out != str(HERE / 'ALLOCATION.json'), 'ALLOCATION.json already exists')
    digest = write_json(args.out, result)
    print(json.dumps({'sizes': result['sizes'], 'sha256': digest}))


if __name__ == '__main__':
    main()
