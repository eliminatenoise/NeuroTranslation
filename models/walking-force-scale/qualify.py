"""Header probe and qualification (protocol section 4). Standard library only.

probe_walk() reads one archive member through a byte-range reader (HTTP in fetch.py, a local file in
tests), checks the local header against the central directory, inflates the raw deflate stream with
a hard output limit that stops at the end of the C3D parameter section, and returns a verdict. No
sample byte is ever produced and no header byte is written anywhere: the buffers are discarded.
"""
import hashlib
import struct
import zlib

import c3dread
from common import need

FIRST_READ = 8704
STEP = 8192
LIMIT = 65536
LOCAL = struct.Struct('<4s5H3I2H')
SCHEMA = 'walking-force-scale-qualification-v1'


class BoundedInflater:
    """Raw-deflate inflation that never produces more output than the target asked for."""

    def __init__(self):
        self.d = zlib.decompressobj(-15)
        self.out = bytearray()
        self.tail = b''
        self.pending = b''
        self.most_requested = 0

    def feed(self, data):
        self.pending += bytes(data)

    def fill(self, target):
        self.most_requested = max(self.most_requested, target)
        while len(self.out) < target:
            data = self.tail + self.pending
            self.pending = b''
            if not data or self.d.eof:
                return False
            got = self.d.decompress(data, target - len(self.out))
            self.out += got
            self.tail = self.d.unconsumed_tail
            if not got and not self.tail:
                continue
        return True


def check_local_header(blob, member):
    if len(blob) < LOCAL.size:
        return 'local-header-short', None
    magic, _ver, flags, method, _t, _d, crc, csize, usize, nlen, xlen = LOCAL.unpack_from(blob, 0)
    name = bytes(blob[LOCAL.size:LOCAL.size + nlen])
    ok = (magic == b'PK\x03\x04' and flags == 0 and method == 8 and f'{crc:08x}' == member['crc32']
          and csize == member['compressed_bytes'] and usize == member['expanded_bytes']
          and name == member['path'].encode())
    return (None if ok else 'local-header-mismatch'), LOCAL.size + nlen + xlen


def probe_walk(member, read_range):
    """read_range(start, stop) -> bytes of archive range [start, stop). Returns the per-walk record."""
    o, end = member['local_header_offset'], member['next_header_offset']
    ranges, digest = [], hashlib.sha256()

    def take(start, stop):
        stop = min(stop, end)
        data = read_range(start, stop)
        need(len(data) == stop - start, f'short range read for {member["path"]}')
        ranges.append([start, stop])
        digest.update(data)
        return data

    record = {'path': member['path'], 'trial': member['trial']}
    blob = take(o, o + FIRST_READ)
    problem, data_at = check_local_header(blob, member)
    inflater = BoundedInflater()
    verdict, reasons, description, produced = 'X', [], None, 0
    if problem:
        reasons = [problem]
    else:
        inflater.feed(blob[data_at:])
        received = len(blob)
        stage, h_end = 0, None
        while True:
            try:
                if stage == 0 and inflater.fill(512):
                    stage = 1
                if stage == 1 and inflater.fill((c3dread.needed_bytes(inflater.out)[0] - 1) * 512 + 4):
                    h_end = c3dread.parameter_end(inflater.out)
                    _, data_start = c3dread.needed_bytes(inflater.out)
                    if h_end > (data_start - 1) * 512:
                        reasons = ['parameters-overlap-data']
                        break
                    stage = 2
                if stage == 2 and inflater.fill(h_end):
                    stage = 3
                    break
            except c3dread.ReadError as error:
                reasons = [str(error)]
                break
            if received >= LIMIT or o + received >= end:
                reasons = ['header-not-reached']
                break
            more = take(o + received, o + received + STEP)
            inflater.feed(more)
            received += len(more)
        if stage == 3:
            try:
                parsed = c3dread.parse(bytes(inflater.out[:h_end]))
                verdict, reasons, _lay, description = c3dread.layout(parsed, member['expanded_bytes'])
            except c3dread.ReadError as error:
                verdict, reasons = 'X', [str(error)]
        produced = len(inflater.out)
    record.update({'ranges': ranges, 'compressed_bytes_received': sum(b - a for a, b in ranges),
                   'compressed_sha256': digest.hexdigest(), 'verdict': verdict, 'reasons': reasons,
                   'inflated_bytes': produced, 'inflation_limit': inflater.most_requested})
    if description:
        record.update(description)
    del inflater, blob
    return record


def person_class(walks):
    """walks: records sorted by trial. Returns (class, trials, reason)."""
    q6 = [w['trial'] for w in walks if w['verdict'] == 'Q6']
    qp = [w['trial'] for w in walks if w['verdict'] in ('Q6', 'QP')]
    if len(q6) >= 3:
        return 'Q6', sorted(q6)[:3], ''
    if len(qp) >= 3:
        return 'QP', sorted(qp)[:3], ''
    bad = sorted({r for w in walks if w['verdict'] == 'X' for r in w['reasons']} |
                 {'six-names' for w in walks if w['verdict'] == 'QP'})
    return 'X', [], ';'.join(bad) or 'fewer-than-three-qualified-walks'


def probe_person(candidate, read_range, log=None):
    """First three walks; the 4th and 5th (lowest number first) only when one of the first three is not Q6."""
    walks = [probe_walk(m, read_range) for m in candidate['probe_first']]
    if log:
        for w in walks:
            log(candidate['subject'], w)
    if any(w['verdict'] != 'Q6' for w in walks):
        for m in sorted(candidate['probe_if_needed'], key=lambda m: m['trial']):
            w = probe_walk(m, read_range)
            walks.append(w)
            if log:
                log(candidate['subject'], w)
    walks.sort(key=lambda w: w['trial'])
    cls, trials, reason = person_class(walks)
    return {'class': cls, 'trials': trials, 'reason': reason, 'walks': walks}


def receipt(protocol_sha256, pool_sha256, people):
    keep = ('trial', 'path', 'ranges', 'compressed_bytes_received', 'compressed_sha256', 'verdict', 'reasons',
            'analog_channels', 'voltage_channels_in_V', 'muscle_names_present')
    out = {s: {'class': p['class'], 'trials': p['trials'], 'reason': p['reason'],
               'walks': [{k: w[k] for k in keep if k in w} for w in p['walks']]} for s, p in sorted(people.items())}
    counts = {c: sum(p['class'] == c for p in out.values()) for c in ('Q6', 'QP', 'X')}
    return {'schema': SCHEMA, 'protocol_sha256': protocol_sha256, 'pool_sha256': pool_sha256,
            'counts': counts, 'people': out}


def check_receipt(qualification, pool, protocol_sha256, pool_sha256):
    """The rules allocate.py assign does not check (admission review): pins, probe order, walk choice."""
    problems = []
    if qualification.get('schema') != SCHEMA:
        problems.append('schema')
    if qualification.get('protocol_sha256') != protocol_sha256:
        problems.append('protocol_sha256')
    if qualification.get('pool_sha256') != pool_sha256:
        problems.append('pool_sha256')
    people = qualification.get('people', {})
    candidates = {c['subject']: c for c in pool['candidates']}
    if set(people) != set(candidates):
        problems.append('people-set')
    for s, person in people.items():
        c = candidates.get(s)
        if c is None:
            continue
        first = [m['trial'] for m in c['probe_first']]
        extra = sorted(m['trial'] for m in c['probe_if_needed'])
        walks = sorted(person['walks'], key=lambda w: w['trial'])
        probed = [w['trial'] for w in walks]
        by_trial = {m['trial']: m for m in c['probe_first'] + c['probe_if_needed']}
        first_q6 = all(w['verdict'] == 'Q6' for w in walks if w['trial'] in first)
        expected = sorted(first) if first_q6 else sorted(first + extra)
        if probed != expected:
            problems.append(f'{s}:probe-order')
        for w in walks:
            m = by_trial.get(w['trial'])
            if m is None or w.get('path') != m['path']:
                problems.append(f'{s}:walk-path')
        cls, trials, _ = person_class(walks)
        if cls != person['class'] or trials != person['trials']:
            problems.append(f'{s}:class-or-trials')
    return problems
