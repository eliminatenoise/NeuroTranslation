"""Download only the selected open session out of its public ZIP and check its SHA-256."""
import argparse
import hashlib
from pathlib import Path
import struct
from urllib.request import Request, urlopen
import zlib

URL='https://zenodo.org/records/5010943/files/s1-kinematics.zip'
ARCHIVE_BYTES=4016198198
MEMBER='reaching_experiments/C_20170912_COactpas_TD.mat'
MEMBER_SHA='a391516945a67aff89039f33c0829a1c5423d859ce79baaaca962985916996af'
SIZE=178807176
BASE=211140493

def read_range(start,end):
    with urlopen(Request(URL,headers={'Range':f'bytes={start}-{end}'}),timeout=75) as r:
        if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{ARCHIVE_BYTES}':raise ValueError('Expected the exact public member range')
        value=r.read(end-start+2)
    if len(value)!=end-start+1:raise EOFError('Incomplete byte range; rerun to resume')
    return value

def check(path):
    if not path.is_file() or path.stat().st_size!=SIZE:return False
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==MEMBER_SHA

def fetch(out):
    out.mkdir(parents=True,exist_ok=True);dest=out/Path(MEMBER).name
    if check(dest):return dest
    if dest.exists():raise ValueError('Existing destination is not the selected member')
    h=struct.unpack('<4s5H3I2H',read_range(BASE,BASE+29))
    if h[0]!=b'PK\x03\x04' or h[3]!=0 or read_range(BASE+30,BASE+29+h[9]).decode()!=MEMBER:raise ValueError('Wrong member or encoding')
    pos=BASE+30+h[9]+h[10];part=out/(dest.name+'.partial')
    offset=part.stat().st_size if part.exists() else 0
    if offset>SIZE:raise ValueError('Oversized partial file')
    with part.open('ab') as f:
        while offset<SIZE:
            end=min(SIZE,offset+4*1024*1024)
            payload=read_range(pos+offset,pos+end-1);f.write(payload);f.flush();offset=end
    if not check(part):raise ValueError('Member digest mismatch')
    part.replace(dest);return dest

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('directory',type=Path)
    print(fetch(cli.parse_args().directory))
