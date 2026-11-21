"""Extract either original member from the official ZIP or verified HTTP ranges."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen
from zipfile import ZipFile
import zlib

PLAN=json.loads(Path(__file__).with_name('selection.json').read_bytes())
CHUNK=4*1024*1024


def verified_ranges(plan):
    start,end=plan['range_inclusive']
    for lo in range(start,end+1,CHUNK):
        hi=min(end,lo+CHUNK-1)
        req=Request(PLAN['archive_url'],headers={'Range':f'bytes={lo}-{hi}','Accept-Encoding':'identity'})
        with urlopen(req,timeout=60) as r:
            if r.status!=206 or r.headers['Content-Range']!=f"bytes {lo}-{hi}/{PLAN['archive_bytes']}":
                raise OSError('Server did not return the requested bytes. Use a downloaded official ZIP with --archive.')
            piece=r.read(hi-lo+2)
            if len(piece)!=hi-lo+1:
                raise EOFError('Truncated member range')
            yield piece


def from_archive(path,plan):
    with ZipFile(path) as archive:
        item=archive.getinfo(plan['member'])
        if (item.file_size, f'{item.CRC:08x}')!=(plan['bytes'],plan['crc32']):
            raise ValueError('ZIP directory mismatch')
        with archive.open(item) as stream:
            yield from iter(lambda:stream.read(CHUNK),b'')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('day',choices=('train','held'))
    p.add_argument('directory',type=Path)
    p.add_argument('--archive',type=Path)
    args=p.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    plan=PLAN[args.day]
    dest=args.directory/Path(plan['member']).name
    if dest.exists():
        with dest.open('rb') as stream:
            if dest.stat().st_size!=plan['bytes'] or hashlib.file_digest(stream,'sha256').hexdigest()!=plan['sha256']:
                raise ValueError('Existing destination differs')
        print(dest)
        return
    with NamedTemporaryFile(dir=dest.parent,delete=False) as stream:
        tmp=Path(stream.name)
        try:
            h=hashlib.sha256()
            crc=0
            for data in from_archive(args.archive,plan) if args.archive else verified_ranges(plan):
                stream.write(data)
                h.update(data)
                crc=zlib.crc32(data,crc)
            if (h.hexdigest(),stream.tell(),f'{crc:08x}')!=(plan['sha256'],plan['bytes'],plan['crc32']):
                raise ValueError('Downloaded length, checksum or CRC mismatch')
            stream.flush()
            os.link(tmp,dest)
        finally:
            tmp.unlink(missing_ok=True)
    print(dest)


if __name__=='__main__':
    main()
