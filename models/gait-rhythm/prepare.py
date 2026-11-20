"""Fetch the listed muscle/angle trial files from the pinned PhysioNet release."""
import argparse
import hashlib
import json
import os
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

HERE=Path(__file__).resolve().parent
BASE='https://physionet.org/files/multimodal-gait-dataset/1.0.0/'

def check_file(path,expected):
    if not path.is_file():
        return False
    with path.open('rb') as src:
        return hashlib.file_digest(src,'sha256').hexdigest()==expected

def copy_stream(stream,destination,expected):
    destination.parent.mkdir(parents=True,exist_ok=True)
    path=None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent,delete=False) as out:
            path=Path(out.name);digest=hashlib.sha256()
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                digest.update(chunk);out.write(chunk)
        if digest.hexdigest()!=expected:raise ValueError('Original differs from release: '+destination.name)
        os.replace(path,destination)
    finally:
        if path and path.exists():path.unlink()

def download(url,dest,digest):
    if check_file(dest,digest):return
    with urlopen(url,timeout=120) as stream:copy_stream(stream,dest,digest)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--imu-archive',type=Path,help='Existing IMU.tar.gz from this release')
    parser.add_argument('--fetch-imu',action='store_true',help='Download the original multi-gigabyte IMU archive if missing')
    args=parser.parse_args()
    spec=json.loads((HERE/'sources.json').read_bytes())
    cache=args.cache;cache.mkdir(parents=True,exist_ok=True)
    download(BASE+'SHA256SUMS.txt',cache/'SHA256SUMS.txt',spec['release_index_sha256'])
    members={}
    for r in spec['members'].values():
        download(BASE+r['emg_path'],cache/r['emg_path'],r['emg_sha256'])
        for lname,sha in [('knee_member','knee_sha256'),('technical_member','technical_sha256')]:
            name=r[lname]
            if not check_file(cache/'imu-members'/name,r[sha]):members[name]=r[sha]
    if not members:return
    archive=args.imu_archive or (cache/'Dataset/IMU_Data/IMU.tar.gz')
    if not check_file(archive,spec['archive_sha256']):
        if not args.fetch_imu:raise SystemExit('Supply the versioned IMU archive with --imu-archive or request its download with --fetch-imu.')
        download(spec['archive_url'],archive,spec['archive_sha256'])
    with tarfile.open(archive,mode='r|gz') as tar:
        for entry in tar:
            name=entry.name.removeprefix('./')
            if name not in members:continue
            if not entry.isfile():raise ValueError('Invalid archive member type')
            with tar.extractfile(entry) as src:copy_stream(src,cache/'imu-members'/name,members.pop(name))
    if members:raise ValueError('Incomplete archive member set')
if __name__=='__main__':main()
