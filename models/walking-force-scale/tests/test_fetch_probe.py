"""Downloader, header probe and qualification on a synthetic local archive (consumed fit walks only).

Checks: fresh redirect per request; pacing; one retry after a 429 and a halt after two 5xx; ETag,
version, range and size checks; signed query parameters never written to receipts; local-header and
CRC-32 checks; bounded inflation that stops at the parameter end; Q6 / QP / X verdicts; the person
rule (extra walks only when one of the first three is not Q6; three lowest-numbered qualified walks);
the receipt checker catching tampered receipts; whole-member download equal to the source bytes.

  python -B tests/test_fetch_probe.py --config CFG     (runtime B)
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synthetic  # noqa: E402  (puts the code folder on sys.path)
import c3dread  # noqa: E402
import fetch  # noqa: E402
import qualify  # noqa: E402
from common import load_config, write_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    cfg = load_config(ap.parse_args().config)
    scratch = Path(cfg['scratch_dir']) / 'test-fetch-probe'
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    walks = synthetic.fit_walk_bytes(cfg)
    entries, candidates = [], []
    # Q6 people: four fit people unchanged
    for s in ('SUBJ043', 'SUBJ044', 'SUBJ061', 'SUBJ062'):
        trials = sorted(t for (p, t) in walks if p == s)
        entries += [(f'synthetic/{s}/{s} ({t}).c3d', walks[(s, t)][1]) for t in trials]
        candidates.append((s, trials, []))
    base = walks[('SUBJ024', 1)][1], walks[('SUBJ024', 2)][1], walks[('SUBJ024', 3)][1], walks[('SUBJ038', 1)][1]
    qp = synthetic.relabel(base[0], 'Voltage.LBF', 'Voltage.12')
    qp2 = synthetic.relabel(base[1], 'Voltage.LRF', 'Voltage.13')
    xx = synthetic.plate_type(base[0], 3)
    # SUBJ901: walks 1-2 QP, 3 Q6, extra 4 Q6 -> QP person, trials [1, 2, 3]
    # SUBJ902: walks 1-2 X, 3 Q6, no extra -> X person
    # SUBJ903: walk 1 X, 2-3 Q6, extra 4 Q6 -> Q6 person with trials [2, 3, 4] (substitution rule)
    # SUBJ904: three Q6 walks and an extra walk that must never be probed
    plan = {'SUBJ901': [qp, qp2, base[2], base[3]], 'SUBJ902': [xx, synthetic.plate_type(base[1], 3), base[2]],
            'SUBJ903': [xx, base[1], base[2], base[3]], 'SUBJ904': [base[0], base[1], base[2], qp]}
    for s, datas in plan.items():
        entries += [(f'synthetic/{s}/{s} ({k + 1}).c3d', d) for k, d in enumerate(datas)]
        candidates.append((s, [1, 2, 3], list(range(4, len(datas) + 1))))
    blob, members = synthetic.build_archive(entries)
    pool = {'candidates': []}
    for s, first, extra in candidates:
        rec = lambda t: {**members[f'synthetic/{s}/{s} ({t}).c3d'], 'trial': t}  # noqa: E731
        pool['candidates'].append({'subject': s, 'probe_first': [rec(t) for t in first], 'probe_if_needed': [rec(t) for t in extra]})
    emu = synthetic.Emulator(blob)
    report = {}
    try:
        client = fetch.Client(emu.identity, scratch / 'requests.jsonl', min_interval=0.05, retry_wait=0.2, allow_plain_http=True)
        people = {}
        t0 = time.monotonic()
        for c in pool['candidates']:
            people[c['subject']] = qualify.probe_person(c, lambda a, b: client.read(a, b, 'test probe'))
        report['probe_seconds'] = time.monotonic() - t0
        got = {s: (p['class'], p['trials'], [w['trial'] for w in p['walks']]) for s, p in people.items()}
        expect = {'SUBJ043': ('Q6', [1, 2, 3], [1, 2, 3]), 'SUBJ901': ('QP', [1, 2, 3], [1, 2, 3, 4]),
                  'SUBJ902': ('X', [], [1, 2, 3]), 'SUBJ903': ('Q6', [2, 3, 4], [1, 2, 3, 4]),
                  'SUBJ904': ('Q6', [1, 2, 3], [1, 2, 3])}
        report['person_rule'] = {s: got[s] == expect[s] for s in expect}
        walks_flat = [w for p in people.values() for w in p['walks']]
        report['inflation_stops_at_parameter_end'] = all(w['inflated_bytes'] <= w['inflation_limit'] for w in walks_flat)
        report['first_read_bytes'] = sorted({w['ranges'][0][1] - w['ranges'][0][0] for w in walks_flat})
        report['reasons_seen'] = sorted({r for w in walks_flat for r in w['reasons']})
        # receipts never hold the signed query
        text = (scratch / 'requests.jsonl').read_text()
        report['no_signed_query_in_receipts'] = 'secret' not in text and 'X-Amz' not in text
        # pacing: every request at least min_interval apart
        heads = [e for e in emu.log]
        report['requests'] = client.requests
        gaps = [b[3] - a[3] for a, b in zip(heads, heads[1:])]
        report['min_gap_seconds'] = min(gaps)
        report['paced_at_min_interval'] = min(gaps) >= 0.045
        report['every_read_took_fresh_redirect'] = sum(1 for e in heads if e[0] == 'HEAD') == sum(1 for e in heads if e[0] == 'GET')
        # receipt and checker
        rec = qualify.receipt('p' * 64, 'q' * 64, people)
        report['receipt_checks_clean'] = qualify.check_receipt(rec, pool, 'p' * 64, 'q' * 64) == []
        bad = json.loads(json.dumps(rec))
        bad['people']['SUBJ903']['trials'] = [1, 2, 3]
        bad['pool_sha256'] = 'r' * 64
        bad['people']['SUBJ904']['walks'].append({'trial': 4, 'path': members['synthetic/SUBJ904/SUBJ904 (4).c3d']['path'], 'verdict': 'QP', 'reasons': []})
        problems = qualify.check_receipt(bad, pool, 'p' * 64, 'q' * 64)
        report['receipt_checker_catches'] = {'pool_sha256': 'pool_sha256' in problems,
                                            'wrong_trials': 'SUBJ903:class-or-trials' in problems,
                                            'extra_walk_probed': 'SUBJ904:probe-order' in problems}
        # 429 then success: one retry
        emu.faults = [429]
        before = client.requests
        data = client.read(0, 100, 'retry test')
        report['retry_after_429'] = len(data) == 100 and client.requests - before == 3
        # two 5xx: halt
        emu.faults = [503, 503]
        try:
            client.read(0, 100, 'halt test')
            report['halt_after_two_5xx'] = False
        except fetch.Halt:
            report['halt_after_two_5xx'] = True
        # wrong ETag halts
        ident = dict(emu.identity, etag='"other"')
        strict = fetch.Client(ident, scratch / 'r2.jsonl', min_interval=0.05, retry_wait=0.2, allow_plain_http=True)
        try:
            strict.read(0, 100, 'etag test')
            report['etag_mismatch_halts'] = False
        except fetch.Halt:
            report['etag_mismatch_halts'] = True
        # whole member equals the source bytes; a wrong CRC halts
        m = members['synthetic/SUBJ043/SUBJ043 (1).c3d']
        data, info = fetch.whole_member(client, m, 'download test')
        report['whole_member_equal'] = data == walks[('SUBJ043', 1)][1] and info['crc32'] == m['crc32']
        try:
            fetch.whole_member(client, dict(m, crc32='00000000'), 'crc test')
            report['crc_mismatch_halts'] = False
        except fetch.Halt:
            report['crc_mismatch_halts'] = True
        # https is required outside tests
        try:
            fetch.Client(emu.identity, scratch / 'r3.jsonl').read(0, 10, 'http test')
            report['plain_http_refused'] = False
        except SystemExit:
            report['plain_http_refused'] = True
        # header probe would fail cleanly when the parameter section overlaps the data
        report['parameter_overlap_gate'] = c3dread.parameter_end(walks[('SUBJ043', 1)][1]) <= (c3dread.needed_bytes(walks[('SUBJ043', 1)][1])[1] - 1) * 512
    finally:
        emu.close()
        shutil.rmtree(scratch, ignore_errors=True)
    flat = [v for k, v in report.items() if isinstance(v, bool)] + list(report['person_rule'].values()) + list(report['receipt_checker_catches'].values())
    report['passed'] = all(flat) and report['reasons_seen'] == ['plate-type-calibration-axis', 'six-names']
    out = Path(cfg['out_dir']) / 'tests' / 'test_fetch_probe.json'
    write_json(out, report)
    print(json.dumps(report, indent=1))
    sys.exit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
