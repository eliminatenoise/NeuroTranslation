"""Download the CC0 salamander archive and verify both publisher identities."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen

DRYAD_DOI = '10.5061/dryad.1f1rc'
DRYAD_FILES = 'https://datadryad.org/api/v2/versions/1813/files'
ZENODO = 'https://zenodo.org/api/records/4976473'
FILENAME = 'error_robust_mode_data.zip'
FILE_SIZE = 87524253
ARCHIVE_SHA256 = 'f5ffc42ef4db643c83c70ac3a3b727e3192478c1401bd796184d8856de8a6039'
MD5 = 'f34c92b51f2abcc3ff965500176ff9fc'


def verify_archive(path):
    if path.stat().st_size != FILE_SIZE:
        raise ValueError('Archive length differs from the published version')
    with path.open('rb') as handle:
        if hashlib.file_digest(handle, 'md5').hexdigest() != MD5:
            raise ValueError('Archive differs from the published Dryad checksum')
    with path.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    if digest != ARCHIVE_SHA256:
        raise ValueError('Archive differs from the SHA-256 of the evaluated release')
    return digest


def acquire(directory):
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / FILENAME
    if dest.exists():
        return dest, verify_archive(dest)
    with urlopen(DRYAD_FILES, timeout=40) as response:
        files = json.load(response)['_embedded']['stash:files']
    with urlopen(ZENODO, timeout=40) as response:
        mirror = json.load(response)
    entries = [f for f in files if f['path'] == FILENAME]
    record = mirror['files'][0]
    if (len(entries) != 1 or entries[0]['size'] != FILE_SIZE
            or entries[0]['digestType'].lower() != 'md5' or entries[0]['digest'] != MD5
            or mirror['doi'] != DRYAD_DOI or mirror['metadata']['license']['id'] != 'cc-zero'
            or record['key'] != FILENAME or record['size'] != FILE_SIZE
            or record['checksum'] != 'md5:' + MD5):
        raise ValueError('Dryad and Zenodo version evidence differs')
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as out:
        tmp = Path(out.name)
    try:
        with urlopen(record['links']['self'], timeout=90) as src, tmp.open('wb') as out:
            while chunk := src.read(1024 * 1024):
                out.write(chunk)
        sha = verify_archive(tmp)
        tmp.replace(dest)
        return dest, sha
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    path, checksum = acquire(parser.parse_args().directory)
    print(f'{checksum}  {path}')
