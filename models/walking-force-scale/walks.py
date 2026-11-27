"""Walk table: archive members, member and participant indices, and checked reads of walk files.

Member indices: the 36 earlier fit walks keep 0-35 in the earlier cache order (common.FIT12_WALKS), so
the 12-person rung reproduces the sealed fits row for row; every other walk of the allocation follows
in ascending (subject, walk number) order. Participant indices: the 12 fit people in the earlier
salted order (common.fold_order), then the others in ascending code order. Both rules are fixed here,
before any new byte is read; indices only order rows and group weights.
Standard library only.
"""
import zlib
from pathlib import Path

import allocate
from common import FIT12, FIT12_WALKS, fold_order, need, read_json, sha_bytes, subject_code


def directory_members(directory_file):
    """code -> trial -> member record, from the pinned central directory (allocate.py's parser)."""
    rows, _extra = allocate.catalogue(allocate.read_directory(directory_file))
    return {allocate.code(c): t for c, t in rows.items()}


def fit12_members(directory_file):
    members = directory_members(directory_file)
    return [(s, members[s][t]) for s, trials in FIT12_WALKS for t in trials]


def cache_name(member):
    return Path(member['path']).name


def read_checked(path, member, expected_sha256=None):
    """Read a decoded walk; check size and CRC-32 against the directory and, if given, sha256."""
    data = Path(path).read_bytes()
    need(len(data) == member['expanded_bytes'], f'size differs for {member["path"]}')
    need(f'{zlib.crc32(data):08x}' == member['crc32'], f'CRC-32 differs for {member["path"]}')
    digest = sha_bytes(data)
    if expected_sha256 is not None:
        need(digest == expected_sha256, f'sha256 differs from the readback for {member["path"]}')
    return data, digest


def fit12_readback(readback_file):
    records = read_json(readback_file)['records']
    return {(subject_code(r['subject_code']), int(r['author_trial_index'])): r for r in records.values()}


def load_fit12(cfg):
    """The 36 earlier fit walks read in place: [(subject, trial, member, bytes, sha256)]."""
    readback = fit12_readback(cfg['fit_readback_file'])
    out = []
    for s, member in fit12_members(cfg['central_directory_file']):
        rb = readback[(s, member['trial'])]
        need(rb['archive_member'] == member['path'] and rb['member_crc32'] == member['crc32'], 'readback mismatch')
        data, digest = read_checked(Path(cfg['fit_cache_dir']) / cache_name(member), member, rb['decoded_sha256'])
        out.append((s, member['trial'], member, data, digest))
    return out


def walk_table(other_walks):
    """other_walks: iterable of (subject, member record). Returns rows with member and participant indices."""
    given = {(s, m['trial']): m for s, m in other_walks}
    table = [{'subject': s, 'trial': t, 'member': given.get((s, t), {'trial': t})} for s, trials in FIT12_WALKS for t in trials]
    extra = sorted((k, m) for k, m in given.items() if k[0] not in FIT12)
    table += [{'subject': s, 'trial': t, 'member': m} for (s, t), m in extra]
    people = fold_order(list(FIT12)) + sorted({r['subject'] for r in table} - set(FIT12))
    pindex = {p: i for i, p in enumerate(people)}
    for i, r in enumerate(table):
        r['member_index'] = i
        r['participant_index'] = pindex[r['subject']]
    return table


def person_maps(table):
    person_of_member = {r['member_index']: r['participant_index'] for r in table}
    code_of_member = {r['member_index']: r['subject'] for r in table}
    return person_of_member, code_of_member
