"""Test helpers: a synthetic archive built only from the 36 consumed fit walks (and patched copies),
served by a local emulator of the stable-address redirect and the ranged storage reads.

Nothing here touches the network or any evaluation, reserved, physics or supplement byte.
"""
import http.server
import io
import struct
import sys
import threading
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

ETAG = '"synthetic-etag"'
VERSION = 'synthetic-version'
STORAGE_PATH = '/figshare-com-storage/42450060/138_HealthyPiG.zip'


def find_parameter(buf, group, name):
    """(value offset, element size, dims) of one parameter, by walking the records."""
    p = buf[0]
    start = (p - 1) * 512
    end = start + buf[start + 2] * 512
    q, groups, recs = start + 4, {}, []
    while q < end:
        nlen, gid = struct.unpack_from('<bb', buf, q)
        if nlen == 0:
            break
        size = abs(nlen)
        nm = bytes(buf[q + 2:q + 2 + size]).decode('latin1')
        r = q + 2 + size
        off = struct.unpack_from('<h', buf, r)[0]
        if gid < 0:
            groups[-gid] = nm
        else:
            recs.append((gid, nm, r))
        q = r + off if off else end
    for gid, nm, r in recs:
        if groups.get(gid) == group and nm == name:
            esize = struct.unpack_from('<b', buf, r + 2)[0]
            nd = buf[r + 3]
            dims = list(buf[r + 4:r + 4 + nd])
            return r + 4 + nd, esize, dims
    raise KeyError((group, name))


def relabel(data, old, new):
    """Replace one ANALOG label (fixed-width field) to make a six-name failure (class QP)."""
    buf = bytearray(data)
    at, _esize, dims = find_parameter(buf, 'ANALOG', 'LABELS')
    width, count = dims
    for i in range(count):
        field = bytes(buf[at + i * width:at + (i + 1) * width]).decode('latin1').strip()
        if field == old:
            buf[at + i * width:at + (i + 1) * width] = new.ljust(width).encode('latin1')
            return bytes(buf)
    raise KeyError(old)


def plate_type(data, value):
    """Set FORCE_PLATFORM:TYPE of plate 1 (makes class X)."""
    buf = bytearray(data)
    at, esize, _dims = find_parameter(buf, 'FORCE_PLATFORM', 'TYPE')
    assert esize == 2
    struct.pack_into('<h', buf, at, value)
    return bytes(buf)


def build_archive(entries):
    """entries: [(archive path, bytes)] -> (archive bytes, member records keyed by path)."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path, data in entries:
            info = zipfile.ZipInfo(path, date_time=(2023, 10, 5, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data, compresslevel=6)
    blob = out.getvalue()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        infos = sorted(z.infolist(), key=lambda e: e.header_offset)
        cd_start = struct.unpack_from('<I', blob, blob.rfind(b'PK\x05\x06') + 16)[0]
    members = {}
    for k, e in enumerate(infos):
        assert e.flag_bits == 0 and e.compress_type == 8
        nxt = infos[k + 1].header_offset if k + 1 < len(infos) else cd_start
        members[e.filename] = {'path': e.filename, 'crc32': f'{e.CRC:08x}', 'local_header_offset': e.header_offset,
                               'next_header_offset': nxt, 'compressed_bytes': e.compress_size, 'expanded_bytes': e.file_size}
    return blob, members


class Emulator:
    """Local stand-in for the stable address (302 with a signed query) and the ranged storage reads."""

    def __init__(self, blob):
        self.blob = blob
        self.faults = []  # statuses to answer instead of the next requests (e.g. [429])
        self.log = []
        emulator = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _fault(self):
                if emulator.faults:
                    status = emulator.faults.pop(0)
                    self.send_response(status)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return True
                return False

            def do_HEAD(self):
                emulator.log.append(('HEAD', self.path, None, time.monotonic()))
                if self._fault():
                    return
                if self.path == '/files/42450060':
                    host, port = self.server.server_address
                    self.send_response(302)
                    self.send_header('Location', f'http://{host}:{port}{STORAGE_PATH}?X-Amz-Expires=10&X-Amz-Signature=secret')
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_GET(self):
                emulator.log.append(('GET', self.path, self.headers.get('Range'), time.monotonic()))
                if self._fault():
                    return
                if not self.path.startswith(STORAGE_PATH):
                    self.send_response(404)
                    self.end_headers()
                    return
                a, b = (int(x) for x in self.headers['Range'].split('=')[1].split('-'))
                body = emulator.blob[a:b + 1]
                self.send_response(206)
                self.send_header('ETag', ETAG)
                self.send_header('x-amz-version-id', VERSION)
                self.send_header('Content-Range', f'bytes {a}-{b}/{len(emulator.blob)}')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def identity(self):
        host, port = self.server.server_address
        return {'stable_url': f'http://{host}:{port}/files/42450060', 'size': len(self.blob), 'etag': ETAG, 'version': VERSION}

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def fit_walk_bytes(cfg):
    """{(subject, trial): (archive path, decoded bytes)} of the 36 consumed fit walks, read in place and checked."""
    import walks
    return {(s, t): (m['path'], data) for s, t, m, data, _d in walks.load_fit12(cfg)}
