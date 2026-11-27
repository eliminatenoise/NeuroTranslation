"""Downloader for stages D1 (header probe), D2 (training pool) and D3 (evaluation group). Standard library.

Protocol section 15. Every request starts at the stable file address, takes a fresh redirect (the
signed storage address lives about 10 s) and then makes one ranged read. ETag and storage version
must equal the pins; whole members are checked for size and CRC-32 against the central directory
and their sha256 is recorded. At most one request per second (monotonic pacing inside the client, 1.1 s
between request starts so that network jitter cannot bring two requests closer than 1 s at the server);
on a 429 or 5xx reply, one retry after 60 s, then halt. Receipts drop the signed query parameters.

Usage (each stage needs its lease and the preceding commit; see README-CODE.md):
  fetch.py probe    --config CFG --lease-note TEXT                     -> private probe log, QUALIFICATION.json
  fetch.py download --config CFG --group training_pool --lease-note TEXT
  fetch.py download --config CFG --group evaluation --fit-complete FIT-COMPLETE.json --lease-note TEXT
"""
import argparse
import http.client
import json
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import allocate
import qualify
from common import HERE, load_config, need, publish_dir, read_json, sha_bytes, sha_file, write_json

SOURCE = read_json(HERE / 'PROTOCOL.json')['data_sources']['van_criekinge_healthy']
IDENTITY = {'stable_url': SOURCE['archive']['stable_url'], 'size': SOURCE['archive']['bytes'],
            'etag': SOURCE['archive_object']['etag'], 'version': SOURCE['archive_object']['s3_version_id']}
NEVER = set(allocate.code(c) for role in ('validation', 'test') for c in allocate.EARLIER_ROSTER[role]) | {
    allocate.code(c) for c in allocate.BOUNDARY}


class Halt(Exception):
    pass


class Client:
    def __init__(self, identity, receipts, *, min_interval=1.1, retry_wait=60.0, allow_plain_http=False, timeout=30.0):
        self.identity = identity
        self.receipts = Path(receipts)
        self.min_interval, self.retry_wait, self.timeout = min_interval, retry_wait, timeout
        self.allow_plain_http = allow_plain_http
        self.last = None
        self.requests = 0
        self.bytes = 0

    def _pace(self):
        if self.last is not None:
            wait = self.last + self.min_interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
        self.last = time.monotonic()

    def _once(self, method, url, headers):
        parts = urlsplit(url)
        if parts.scheme == 'https':
            conn = http.client.HTTPSConnection(parts.hostname, parts.port or 443, timeout=self.timeout)
        else:
            need(self.allow_plain_http and parts.scheme == 'http', 'only https is allowed')
            conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=self.timeout)
        target = parts.path + (f'?{parts.query}' if parts.query else '')
        self._pace()
        self.requests += 1
        try:
            conn.request(method, target, headers={'User-Agent': 'walking-force-scale/1', **headers})
            resp = conn.getresponse()
            body = resp.read() if method == 'GET' else b''
            return resp.status, {k.lower(): v for k, v in resp.getheaders()}, body
        except (OSError, http.client.HTTPException) as error:
            raise Halt(f'{method} failed ({type(error).__name__}); no retry') from None
        finally:
            conn.close()

    def _request(self, method, url, headers):
        status, head, body = self._once(method, url, headers)
        if status == 429 or 500 <= status <= 599:
            time.sleep(self.retry_wait)
            status, head, body = self._once(method, url, headers)
            if status == 429 or 500 <= status <= 599:
                raise Halt(f'{method} answered {status} twice; halting')
        return status, head, body

    def _log(self, row):
        self.receipts.parent.mkdir(parents=True, exist_ok=True)
        with open(self.receipts, 'a') as stream:
            stream.write(json.dumps(row, sort_keys=True) + '\n')

    def signed(self):
        status, head, _ = self._request('HEAD', self.identity['stable_url'], {})
        location = head.get('location', '')
        parts = urlsplit(location)
        if status != 302 or not parts.hostname or (parts.scheme != 'https' and not self.allow_plain_http):
            raise Halt(f'unexpected redirect answer {status}')
        return location, {'storage_host': parts.hostname, 'storage_path': parts.path}

    def read(self, start, stop, purpose):
        """Bytes [start, stop) of the archive through a fresh redirect and one ranged GET."""
        need(0 <= start < stop <= self.identity['size'], 'range outside the archive')
        url, where = self.signed()
        status, head, body = self._request('GET', url, {'Range': f'bytes={start}-{stop - 1}', 'Accept-Encoding': 'identity'})
        row = {'utc': datetime.now(timezone.utc).isoformat(), 'purpose': purpose, 'stable_url': self.identity['stable_url'],
               **where, 'version': head.get('x-amz-version-id'), 'etag': head.get('etag'), 'status': status,
               'range_half_open': [start, stop], 'bytes': len(body), 'sha256': sha_bytes(body)}
        self._log(row)
        ok = (status == 206 and head.get('etag') == self.identity['etag'] and head.get('x-amz-version-id') == self.identity['version']
              and head.get('content-range') == f'bytes {start}-{stop - 1}/{self.identity["size"]}' and len(body) == stop - start
              and head.get('content-encoding', 'identity') == 'identity')
        if not ok:
            raise Halt(f'range check failed for {purpose}: status {status}')
        self.bytes += len(body)
        return body


def whole_member(client, member, purpose):
    """One ranged read from the local header to the next local header; returns decoded bytes and receipt."""
    blob = client.read(member['local_header_offset'], member['next_header_offset'], purpose)
    problem, data_at = qualify.check_local_header(blob, member)
    if problem:
        raise Halt(f'{problem} for {member["path"]}')
    compressed = blob[data_at:data_at + member['compressed_bytes']]
    need(len(compressed) == member['compressed_bytes'], 'member shorter than its directory entry')
    d = zlib.decompressobj(-15)
    data = d.decompress(compressed, member['expanded_bytes'] + 1)
    crc = f'{zlib.crc32(data):08x}'
    if not d.eof or len(data) != member['expanded_bytes'] or crc != member['crc32']:
        raise Halt(f'size or CRC-32 check failed for {member["path"]}')
    return data, {'path': member['path'], 'range_half_open': [member['local_header_offset'], member['next_header_offset']],
                  'compressed_bytes': len(compressed), 'compressed_sha256': sha_bytes(compressed),
                  'crc32': crc, 'decoded_bytes': len(data), 'decoded_sha256': sha_bytes(data)}


def run_probe(cfg, pool_path, protocol_path, lease_note, client=None, out=None):
    pool_raw = Path(pool_path).read_bytes()
    pool = json.loads(pool_raw)
    private = Path(cfg['private_dir'])
    out = Path(out or publish_dir(cfg) / 'QUALIFICATION.json')
    need(not out.exists(), 'QUALIFICATION.json already exists; the probe runs once')
    client = client or Client(IDENTITY, private / 'receipts' / 'D1-requests.jsonl')
    log_path = private / 'receipts' / 'D1-walks.jsonl'
    candidates = sorted(pool['candidates'], key=lambda c: c['subject'])
    need(not ({c['subject'] for c in candidates} & NEVER), 'the pool contains a reserved or boundary person')

    def log(subject, walk):
        with open(log_path, 'a') as stream:
            stream.write(json.dumps({'subject': subject, **walk}, sort_keys=True) + '\n')

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'a') as stream:
        stream.write(json.dumps({'lease_note': lease_note, 'utc': datetime.now(timezone.utc).isoformat()}) + '\n')
    people = {}
    for c in candidates:
        people[c['subject']] = qualify.probe_person(
            c, lambda a, b, s=c['subject']: client.read(a, b, f'D1 header probe {s}'), log)
    receipt = qualify.receipt(sha_file(protocol_path), sha_bytes(pool_raw), people)
    receipt['requests'] = client.requests
    receipt['compressed_bytes_received'] = client.bytes
    digest = write_json(out, receipt, exclusive=True)
    return receipt, digest


def run_download(cfg, allocation_path, group, lease_note, client=None, fit_complete=None):
    need(group in ('training_pool', 'evaluation'), 'this track downloads only the training pool and the evaluation group')
    allocation = read_json(allocation_path)
    private = Path(cfg['private_dir'])
    if group == 'evaluation':
        need(fit_complete is not None and Path(fit_complete).is_file(), 'D3 needs the sealed FIT-COMPLETE.json (C3)')
        sealed = read_json(fit_complete)
        need(sealed.get('allocation_sha256') == sha_file(allocation_path), 'FIT-COMPLETE.json was made for another allocation')
    people = allocation['groups'][group]
    forbidden = {p['subject'] for g in ('physics_source', 'physics_supplement') for p in allocation['groups'][g]}
    need(not ({p['subject'] for p in people} & (forbidden | NEVER)), 'group overlaps a group this track never downloads')
    folder = private / 'walks'
    folder.mkdir(parents=True, exist_ok=True)
    client = client or Client(IDENTITY, private / 'receipts' / f'D-{group}-requests.jsonl')
    stage = 'D2' if group == 'training_pool' else 'D3'
    rows = []
    for person in sorted(people, key=lambda p: p['subject']):
        for member in person['walks']:
            target = folder / f'{person["subject"]}-{member["trial"]}.c3d'
            need(not target.exists(), f'{target.name} exists already')
            data, rec = whole_member(client, member, f'{stage} {person["subject"]} walk {member["trial"]}')
            with open(target, 'xb') as stream:
                stream.write(data)
            rows.append({'subject': person['subject'], 'trial': member['trial'], 'file': target.name, **rec})
    receipt = {'schema': 'walking-force-scale-download-v1', 'stage': stage, 'group': group, 'lease_note': lease_note,
               'allocation_sha256': sha_file(allocation_path), 'utc': datetime.now(timezone.utc).isoformat(),
               'requests': client.requests, 'bytes_received': client.bytes, 'members': rows}
    write_json(private / 'receipts' / f'{stage}-RECEIPT.json', receipt, exclusive=True)
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('step', choices=('probe', 'download'))
    ap.add_argument('--config', required=True)
    ap.add_argument('--lease-note', required=True, help='who gave the download lease, and when (recorded)')
    ap.add_argument('--pool', default=str(HERE / 'POOL.json'))
    ap.add_argument('--protocol', default=str(HERE / 'PROTOCOL.json'))
    ap.add_argument('--allocation', default=str(HERE / 'ALLOCATION.json'))
    ap.add_argument('--group')
    ap.add_argument('--fit-complete')
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.step == 'probe':
        receipt, digest = run_probe(cfg, args.pool, args.protocol, args.lease_note)
        print(json.dumps({'counts': receipt['counts'], 'requests': receipt['requests'], 'sha256': digest}))
    else:
        receipt = run_download(cfg, args.allocation, args.group, args.lease_note, fit_complete=args.fit_complete)
        print(json.dumps({k: receipt[k] for k in ('stage', 'requests', 'bytes_received')}))


if __name__ == '__main__':
    main()
