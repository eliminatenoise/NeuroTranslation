"""Checked allocation on synthetic verdicts for the real pool (no recording byte is involved).

Scenarios: all 80 candidates Q6; a mixed set with QP, X and 4th/5th-walk substitutions; a low set
(ladder of two rungs); a cancelled ladder (T < 6). Tampered receipts must be refused: wrong pool
sha256, wrong protocol sha256, listed walks not the lowest-numbered qualified ones, extra walks probed
although the first three were Q6.

  python -B tests/test_assign.py --config CFG     (any runtime; standard library only)
"""
import argparse
import copy
import json
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import allocate  # noqa: E402
import assign  # noqa: E402
import qualify  # noqa: E402
from common import HERE, load_config, read_json, sha_file, write_json  # noqa: E402


def synthetic_people(pool, rng, p_x_walk=0.0, p_qp_person=0.0, p_x_person=0.0):
    people = {}
    for c in pool['candidates']:
        kind = rng.random()
        walks = []
        for m in c['probe_first']:
            v = 'Q6'
            if kind < p_qp_person:
                v = 'QP'
            elif kind < p_qp_person + p_x_person:
                v = 'X'
            elif rng.random() < p_x_walk:
                v = 'X'
            walks.append({'trial': m['trial'], 'path': m['path'], 'verdict': v, 'reasons': [] if v == 'Q6' else ['synthetic']})
        if any(w['verdict'] != 'Q6' for w in walks):
            for m in c['probe_if_needed']:
                walks.append({'trial': m['trial'], 'path': m['path'], 'verdict': 'Q6' if kind >= p_qp_person else 'QP', 'reasons': []})
        cls, trials, reason = qualify.person_class(walks)
        people[c['subject']] = {'class': cls, 'trials': trials, 'reason': reason, 'walks': walks}
    return people


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    cfg = load_config(ap.parse_args().config)
    scratch = Path(cfg['scratch_dir']) / 'test-assign'
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    protocol, pool_path = HERE / 'PROTOCOL.json', HERE / 'POOL.json'
    pool = read_json(pool_path)
    psha, poolsha = sha_file(protocol), sha_file(pool_path)
    rng = random.Random(20261127)
    report = {}
    scenarios = {'all_q6': synthetic_people(pool, rng), 'mixed': synthetic_people(pool, rng, 0.08, 0.06, 0.04),
                 'low': synthetic_people(pool, rng, 0.0, 0.40, 0.25), 'cancelled': synthetic_people(pool, rng, 0.0, 0.55, 0.20)}
    for name, people in scenarios.items():
        rec = qualify.receipt(psha, poolsha, people)
        path = scratch / f'Q-{name}.json'
        write_json(path, rec)
        result = assign.checked_allocation(path, protocol, pool_path, cfg['central_directory_file'])
        sizes = result['sizes']
        q = rec['counts']['Q6']
        report[name] = {'Q6': q, 'QP': rec['counts']['QP'], 'X': rec['counts']['X'], 'sizes': sizes,
                        'size_rule': sizes == allocate.sizes(q),
                        'substitutions': sum(1 for p in people.values() if p['class'] == 'Q6' and p['trials'] != [1, 2, 3])}
    # tampered receipts
    base = qualify.receipt(psha, poolsha, scenarios['mixed'])
    sub = next(s for s, p in base['people'].items() if p['class'] == 'Q6' and p['trials'] != [1, 2, 3])
    clean = next(s for s, p in base['people'].items() if p['class'] == 'Q6' and len(p['walks']) == 3)
    extra_walk = next(m for c in pool['candidates'] if c['subject'] == clean for m in c['probe_if_needed']) \
        if any(c['subject'] == clean and c['probe_if_needed'] for c in pool['candidates']) else None
    tamper = {
        'pool_sha256': lambda r: r.__setitem__('pool_sha256', '0' * 64),
        'protocol_sha256': lambda r: r.__setitem__('protocol_sha256', '0' * 64),
        'not_lowest_walks': lambda r: r['people'][sub].__setitem__('trials', sorted(r['people'][sub]['trials'])[::-1]),
    }
    if extra_walk is None:
        clean = next(c['subject'] for c in pool['candidates'] if c['probe_if_needed'] and base['people'][c['subject']]['class'] == 'Q6'
                     and len(base['people'][c['subject']]['walks']) == 3)
        extra_walk = next(c for c in pool['candidates'] if c['subject'] == clean)['probe_if_needed'][0]
    tamper['extra_walk_probed'] = lambda r: r['people'][clean]['walks'].append(
        {'trial': extra_walk['trial'], 'path': extra_walk['path'], 'verdict': 'Q6', 'reasons': []})
    refused = {}
    for name, change in tamper.items():
        r = copy.deepcopy(base)
        change(r)
        path = scratch / f'T-{name}.json'
        write_json(path, r)
        try:
            assign.checked_allocation(path, protocol, pool_path)
            refused[name] = False
        except SystemExit:
            refused[name] = True
    report['tampered_receipts_refused'] = refused
    report['allocate_py_unchanged'] = sha_file(HERE / 'allocate.py') == assign.ALLOCATE_SHA256
    report['passed'] = (all(v['size_rule'] for k, v in report.items() if isinstance(v, dict) and 'size_rule' in v)
                        and all(refused.values()) and report['allocate_py_unchanged']
                        and report['cancelled']['sizes']['ladder'] == 'cancelled' and report['all_q6']['sizes']['T'] == 44)
    shutil.rmtree(scratch, ignore_errors=True)
    write_json(Path(cfg['out_dir']) / 'tests' / 'test_assign.json', report)
    print(json.dumps(report, indent=1))
    sys.exit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
