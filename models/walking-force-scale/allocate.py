"""Single allocation of the never-assigned Van Criekinge healthy people for walking-force-scale.

Needs only the Python standard library (3.10 or later). Reads metadata only: the archive's
central directory (no recording bytes) and, for the last step, the qualification receipt.

Steps (each writes one JSON file; the default output is next to this script):

  pool    --directory CD.bin [--roster ROSTER.json]              -> POOL.json
          Lists the 138 healthy codes, why each is or is not a candidate, and the archive
          members (path, CRC-32, byte extent) of every candidate. CD.bin is the archive's central
          directory: 87,971 bytes, archive bytes 463,071,776 to 463,159,746 inclusive.
  order   --protocol PROTOCOL.json [--pool POOL.json]             -> ORDER.json
          Hash orders salted with the sha256 of the committed PROTOCOL.json.
  assign  --protocol PROTOCOL.json --qualification Q.json [--pool POOL.json] -> ALLOCATION.json
          Applies the header-probe verdicts to the order: evaluation group, physics-source group,
          training pool, rungs, nesting draws, inner folds, variety arms and download lists.
  sizes   Prints the group sizes and rungs for every possible number of qualified people.
  check   --directory CD.bin --protocol PROTOCOL.json
          Recomputes POOL.json and ORDER.json and compares them byte for byte with the files here.

Rules (also in PROTOCOL.json, section 'allocation'):
  TAG = DOI + '|walking-scale|' + sha256(PROTOCOL.json bytes)
  primary order: ascending sha256(TAG + '|SUBJnnn')
  nesting draw d (0-9): ascending sha256(TAG + '|rung-draw-' + d + '|SUBJnnn'), restricted to the training pool
  inner folds: rank by sha256(TAG + '|inner-fold|SUBJnnn') within a fit's training people; fold = rank mod 4
  variety walk: int(sha256(TAG + '|variety-walk|SUBJnnn'), 16) mod 3 picks one of a person's three walks
  Q = people with three walks passing the six-name gate (class Q6)
  E = clamp(floor((3 Q + 5) / 10), 12, 24); P = clamp(floor((3 Q + 10) / 20), 8, 12); T = Q - E - P
  (the same as floor(0.30 Q + 0.5) and floor(0.15 Q + 0.5), computed in integers)
  walking the primary order over class-Q6 people: first E -> evaluation, next P -> physics-source, rest -> training
  if T < 6 the ladder is cancelled: no evaluation group; P = min(clamp(...), Q) from the start of the order
  class QP (plates and clocks pass, 4+ voltage channels, six names incomplete) -> physics-supplement
  class X -> unusable
  added people per rung: a in (6, 12, 24) when a < T and (12 + T) / (12 + a) >= 1.25, plus a = T
"""
import argparse
import hashlib
import io
import json
import re
import struct
import sys
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
SCHEMA = 'walking-force-scale-allocation-v1'
DOI = '10.6084/m9.figshare.24192480.v1'
ARCHIVE = {
    'name': '138_HealthyPiG.zip', 'figshare_file_id': 42450060, 'bytes': 463159769,
    'md5': '85235c73455d4df8434810d61517efbb',
    'stable_url': 'https://ndownloader.figshare.com/files/42450060',
}
DIRECTORY = {
    'bytes': 87971, 'entries': 1016,
    'sha256': '96a6b5d97ab542eef90a773dfeabb1ad4ac025d768a559d1491deec0d99f4b2b',
    'archive_bytes_inclusive': [463071776, 463159746],
}
ROSTER_SHA256 = '34bf97f35e434357c5f9ff7fb945a0743dbbd0c5558fc99b64fe8248485b8f2c'
AUTHOR_NO_ANALOG = frozenset({23, 48, 54, 72, 85, *range(118, 139)})
ENGINEERING = frozenset({1})
# Earlier roster (metadata-only proposal, 22 Nov 2026). Never reallocated here. Only the 12 fit
# people's walks are reused, read-only, as the 12-person rung.
EARLIER_ROSTER = {
    'fit': (24, 38, 39, 40, 43, 44, 61, 62, 82, 96, 110, 112),
    'validation': (11, 47, 66, 75, 115, 116),
    'test': (8, 14, 16, 20, 53, 56, 57, 74, 77, 84, 89, 92),
}
# SUBJ099 lost its last walk to an entry-pairing step in the earlier selector; under the intended
# rule it would sit in the earlier test block. It is left out and never opened.
BOUNDARY = frozenset({99})
WALKS_PER_PERSON = 3
NEST_DRAWS = 10
RUNG_STEPS = (6, 12, 24)
FOLDS = 4

BASENAME = re.compile(r'SUBJ(\d+) \((\d+)\)\.c3d', re.IGNORECASE)
PARENT = re.compile(r'SUBJ(\d+)')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def h(text):
    return hashlib.sha256(text.encode('ascii')).hexdigest()


def code(n):
    return f'SUBJ{n:03d}'


def need(ok, message):
    if not ok:
        raise SystemExit(f'allocate.py: {message}')


def dump(obj, path):
    body = (json.dumps(obj, indent=1, ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
    Path(path).write_bytes(body)
    print(f'{Path(path).name} {len(body)} bytes sha256 {sha(body)}')
    return body


def read_directory(path):
    blob = Path(path).read_bytes()
    need(len(blob) == DIRECTORY['bytes'] and sha(blob) == DIRECTORY['sha256'],
         'the central directory differs from the pinned one')
    n = DIRECTORY['entries']
    eocd = struct.pack('<4s4H2IH', b'PK\x05\x06', 0, 0, n, n, len(blob), 0, 0)
    with zipfile.ZipFile(io.BytesIO(blob + eocd)) as z:
        entries = sorted(z.infolist(), key=lambda e: e.header_offset)
    need(len(entries) == n and len({e.header_offset for e in entries}) == n, 'entry identities do not close')
    return entries


def catalogue(entries):
    """Map code -> trial number -> member record. Trial 0 is the static trial."""
    ends = [e.header_offset for e in entries[1:]] + [DIRECTORY['archive_bytes_inclusive'][0]]
    rows, extra = {}, []
    for e, end in zip(entries, ends):
        p = PurePosixPath(e.filename)
        if '138_HealthyPiG_10.05' not in p.parts or not p.name.lower().endswith('.c3d'):
            continue
        m, parent = BASENAME.fullmatch(p.name), PARENT.fullmatch(p.parent.name)
        if not m:
            extra.append(e.filename)
            continue
        c, t = int(m.group(1)), int(m.group(2))
        need(parent is not None and int(parent.group(1)) == c and 1 <= c <= 138, f'odd member {e.filename}')
        need(e.flag_bits == 0 and e.compress_type == 8, f'unsupported member flags {e.filename}')
        need(end >= e.header_offset + 30 + len(e.filename.encode()) + e.compress_size, f'overlap {e.filename}')
        need(t not in rows.setdefault(c, {}), f'duplicate trial {e.filename}')
        rows[c][t] = {
            'trial': t, 'path': e.filename, 'crc32': f'{e.CRC:08x}',
            'local_header_offset': e.header_offset, 'next_header_offset': end,
            'compressed_bytes': e.compress_size, 'expanded_bytes': e.file_size,
        }
    need(set(rows) == set(range(1, 139)) and all(0 in r for r in rows.values()), 'codes or static trials missing')
    return rows, extra


def make_pool(directory, roster=None):
    entries = read_directory(directory)
    rows, extra = catalogue(entries)
    earlier = {c: role for role, codes in EARLIER_ROSTER.items() for c in codes}
    need(len(earlier) == 30, 'earlier roster must list 30 distinct people')
    if roster is not None:
        raw = Path(roster).read_bytes()
        need(sha(raw) == ROSTER_SHA256, 'the earlier roster file differs from the pinned one')
        listed = {int(p['subject_code'][4:]): role for role, people in json.loads(raw)['roles'].items() for p in people}
        need(listed == earlier, 'the earlier roster file disagrees with the roles written in this script')
    excluded, candidates = [], []
    for c in range(1, 139):
        if c in ENGINEERING:
            reason = 'engineering-person'
        elif c in AUTHOR_NO_ANALOG:
            reason = 'author-listed-without-analog-data'
        elif c in earlier:
            reason = f'earlier-roster-{earlier[c]}'
        elif c in BOUNDARY:
            reason = 'excluded-boundary-never-opened'
        else:
            reason = None
        if reason:
            excluded.append({'subject': code(c), 'reason': reason})
            continue
        dynamic = sorted(t for t in rows[c] if t > 0)
        need(len(dynamic) >= WALKS_PER_PERSON, f'{code(c)} has fewer than three walks')
        candidates.append({
            'subject': code(c),
            'probe_first': [rows[c][t] for t in dynamic[:WALKS_PER_PERSON]],
            'probe_if_needed': [rows[c][t] for t in dynamic[WALKS_PER_PERSON:]],
            'static_trial_not_used': {k: rows[c][0][k] for k in ('path', 'compressed_bytes')},
        })
    first = [m for p in candidates for m in p['probe_first']]
    later = [m for p in candidates for m in p['probe_if_needed']]
    sizes = sorted(m['compressed_bytes'] for m in first)
    return {
        'schema': SCHEMA, 'step': 'pool', 'source_doi': DOI, 'archive': ARCHIVE, 'central_directory': DIRECTORY,
        'earlier_roster_sha256': ROSTER_SHA256, 'earlier_roster_roles': {k: [code(c) for c in v] for k, v in EARLIER_ROSTER.items()},
        'counts': {
            'healthy_codes': 138, 'excluded': len(excluded), 'candidates': len(candidates),
            'excluded_by_reason': {r: sum(x['reason'] == r for x in excluded) for r in sorted({x['reason'] for x in excluded})},
            'walks_per_candidate': {str(k): sum(len(p['probe_first']) + len(p['probe_if_needed']) == k for p in candidates)
                                    for k in sorted({len(p['probe_first']) + len(p['probe_if_needed']) for p in candidates})},
            'first_three_walks': len(first), 'first_three_compressed_bytes': sum(sizes),
            'first_three_median_compressed_bytes': sizes[len(sizes) // 2], 'largest_walk_compressed_bytes': sizes[-1],
            'extra_walks_for_substitution': len(later),
        },
        'unnumbered_c3d_members_ignored': extra,
        'excluded': excluded,
        'candidates': candidates,
    }


def protocol_tag(protocol):
    digest = sha(Path(protocol).read_bytes())
    return digest, f'{DOI}|walking-scale|{digest}'


def make_order(protocol, pool, pool_sha256):
    digest, tag = protocol_tag(protocol)
    codes = [p['subject'] for p in pool['candidates']]
    fit12 = [code(c) for c in EARLIER_ROSTER['fit']]
    primary = sorted(codes, key=lambda s: h(f'{tag}|{s}'))
    draws = [sorted(codes, key=lambda s: h(f'{tag}|rung-draw-{d}|{s}')) for d in range(NEST_DRAWS)]
    return {
        'schema': SCHEMA, 'step': 'order', 'protocol_sha256': digest, 'tag': tag,
        'pool_sha256': pool_sha256,
        'primary_order': [{'rank': i, 'subject': s, 'sha256': h(f'{tag}|{s}')} for i, s in enumerate(primary)],
        'nesting_draw_orders': {str(d): o for d, o in enumerate(draws)},
        'inner_fold_key_order': sorted(codes + fit12, key=lambda s: h(f'{tag}|inner-fold|{s}')),
        'variety_walk_position': {s: int(h(f'{tag}|variety-walk|{s}'), 16) % WALKS_PER_PERSON for s in codes},
        'note': 'Qualification is unknown when this file is written; group membership follows in ALLOCATION.json.',
    }


def sizes(q):
    # Integer forms of floor(0.30 q + 0.5) and floor(0.15 q + 0.5), and of (12 + t) / (12 + a) >= 1.25.
    e = min(24, max(12, (3 * q + 5) // 10))
    p = min(12, max(8, (3 * q + 10) // 20))
    t = q - e - p
    if t < 6:
        return {'Q': q, 'E': 0, 'P': min(p, q), 'T': 0, 'ladder': 'cancelled', 'added': [], 'N': []}
    added = [a for a in RUNG_STEPS if a < t and 4 * (12 + t) >= 5 * (12 + a)] + [t]
    return {'Q': q, 'E': e, 'P': p, 'T': t, 'ladder': 'run', 'added': added, 'N': [12] + [12 + a for a in added]}


def folds(tag, people):
    ranked = sorted(people, key=lambda s: h(f'{tag}|inner-fold|{s}'))
    return [sorted(ranked[k::FOLDS]) for k in range(FOLDS)]


def members(pool_people, person, trials):
    p = pool_people[person]
    by_trial = {m['trial']: m for m in p['probe_first'] + p['probe_if_needed']}
    need(len(trials) == WALKS_PER_PERSON == len(set(trials)) and all(t in by_trial for t in trials),
         f'{person} must list three distinct walks of its own')
    return [by_trial[t] for t in sorted(trials)]


def make_allocation(protocol, pool, qualification):
    digest, tag = protocol_tag(protocol)
    need(qualification.get('protocol_sha256') == digest, 'qualification was made for another protocol')
    verdicts = qualification['people']
    pool_people = {p['subject']: p for p in pool['candidates']}
    need(set(verdicts) == set(pool_people), 'every candidate needs exactly one verdict')
    order = sorted(pool_people, key=lambda s: h(f'{tag}|{s}'))
    q6 = [s for s in order if verdicts[s]['class'] == 'Q6']
    qp = [s for s in order if verdicts[s]['class'] == 'QP']
    xs = [s for s in order if verdicts[s]['class'] == 'X']
    need(len(q6) + len(qp) + len(xs) == len(order), 'classes must be Q6, QP or X')
    plan = sizes(len(q6))
    e_group = q6[:plan['E']]
    p_group = q6[plan['E']:plan['E'] + plan['P']]
    t_group = q6[plan['E'] + plan['P']:] if plan['ladder'] == 'run' else []
    unallocated = q6[plan['E'] + plan['P']:] if plan['ladder'] == 'cancelled' else []
    fit12 = sorted(code(c) for c in EARLIER_ROSTER['fit'])
    walks = {s: members(pool_people, s, verdicts[s]['trials']) for s in q6 + qp}
    rungs = []
    for a in plan['added']:
        if a == plan['T']:
            sets = [sorted(t_group)]
        else:
            sets = [sorted(sorted(t_group, key=lambda s: h(f'{tag}|rung-draw-{d}|{s}'))[:a]) for d in range(NEST_DRAWS)]
        rungs.append({'added': a, 'N': 12 + a, 'draws': [{'draw': i, 'added_people': x, 'inner_folds': folds(tag, fit12 + x)}
                                                         for i, x in enumerate(sets)]})
    mid = [a for a in plan['added'] if a != plan['T']]
    tail = {}
    if plan['T'] >= 32 and mid:
        cut = max(mid)
        tail = {str(d): sorted(sorted(t_group, key=lambda s: h(f'{tag}|rung-draw-{d}|{s}'))[cut:]) for d in range(NEST_DRAWS)}
    variety = {}
    if plan['ladder'] == 'run':
        pos = {s: int(h(f'{tag}|variety-walk|{s}'), 16) % WALKS_PER_PERSON for s in t_group}
        first_draw = sorted(t_group, key=lambda s: h(f'{tag}|rung-draw-0|{s}'))
        variety = {
            'one_walk_each': {s: walks[s][pos[s]]['trial'] for s in sorted(t_group)},
            'three_walks_each': sorted(first_draw[:plan['T'] // 3]),
        }

    def listing(group):
        return [{'subject': s, 'walks': walks[s]} for s in group]

    def volume(group):
        ms = [m for s in group for m in walks[s]]
        return {'people': len(group), 'walks': len(ms), 'compressed_bytes': sum(m['compressed_bytes'] for m in ms)}

    return {
        'schema': SCHEMA, 'step': 'assign', 'protocol_sha256': digest, 'tag': tag,
        'qualification_sha256': qualification.get('_sha256'),
        'sizes': plan,
        'groups': {
            'evaluation': listing(sorted(e_group)),
            'physics_source': listing(sorted(p_group)),
            'training_pool': listing(sorted(t_group)),
            'physics_supplement': listing(sorted(qp)),
            'unusable': [{'subject': s, 'reason': verdicts[s].get('reason', '')} for s in sorted(xs)],
            'unallocated_unopened': sorted(unallocated),
            'excluded_boundary_never_opened': [code(c) for c in sorted(BOUNDARY)],
        },
        'twelve_person_rung': fit12,
        'rung_zero_inner_folds': folds(tag, fit12),
        'rungs': rungs,
        'pool_tail_for_prediction_P1': tail,
        'variety_control': variety,
        'downloads_by_this_track': {'D2_training_pool': volume(t_group), 'D3_evaluation': volume(e_group)},
        'never_downloaded_by_this_track': {'physics_source': volume(p_group), 'physics_supplement': volume(qp)},
    }


def load_json(path):
    raw = Path(path).read_bytes()
    obj = json.loads(raw)
    obj['_sha256'] = sha(raw)
    return obj


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('step', choices=('pool', 'order', 'assign', 'sizes', 'check'))
    ap.add_argument('--directory')
    ap.add_argument('--roster')
    ap.add_argument('--protocol', default=str(HERE / 'PROTOCOL.json'))
    ap.add_argument('--pool', default=str(HERE / 'POOL.json'))
    ap.add_argument('--qualification')
    ap.add_argument('--out')
    args = ap.parse_args(argv)
    if args.step == 'sizes':
        for q in range(0, 81):
            print(json.dumps(sizes(q)))
        return
    if args.step == 'pool':
        need(args.directory, '--directory is required')
        dump(make_pool(args.directory, args.roster), args.out or HERE / 'POOL.json')
        return
    pool_raw = Path(args.pool).read_bytes()
    pool = json.loads(pool_raw)
    if args.step == 'order':
        dump(make_order(args.protocol, pool, sha(pool_raw)), args.out or HERE / 'ORDER.json')
    elif args.step == 'assign':
        need(args.qualification, '--qualification is required')
        result = make_allocation(args.protocol, pool, load_json(args.qualification))
        dump(result, args.out or HERE / 'ALLOCATION.json')
    else:
        need(args.directory, '--directory is required')
        fresh_pool = (json.dumps(make_pool(args.directory), indent=1, ensure_ascii=True) + '\n').encode('ascii')
        fresh_order = (json.dumps(make_order(args.protocol, pool, sha(pool_raw)), indent=1, ensure_ascii=True) + '\n').encode('ascii')
        same_pool = fresh_pool == (HERE / 'POOL.json').read_bytes()
        same_order = fresh_order == (HERE / 'ORDER.json').read_bytes()
        print(json.dumps({'POOL.json': same_pool, 'ORDER.json': same_order}))
        sys.exit(0 if same_pool and same_order else 1)


if __name__ == '__main__':
    main()
