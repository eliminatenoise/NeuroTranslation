"""Load the named frozen population-motion packets in their original reader's process."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(root, files):
    expected = json.loads((HERE / 'source-hashes.json').read_text())
    for name in files:
        if digest(root / name) != expected[name]:
            raise ValueError(f'Source identity mismatch: {name}')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('split', choices=('train', 'test'))
    args = cli.parse_args()
    root = args.source.resolve()
    rats = json.loads((HERE / 'protocol.json').read_text())[args.split]
    files = ['study.py', 'predict.py', 'protocol.json']
    for rat in rats:
        files.extend([f'packets/{rat}.npz', f'source/selection-{rat}.json', f'source/ranges-{rat}.json'])
    checked(root, files)
    sys.path.insert(0, str(root))
    from study import read_rat
    rows = [r for rat in rats for r in read_rat(rat)[0]]
    if len(rows) != {'train': 824, 'test': 549}[args.split]:
        raise ValueError('Eligible window count changed')
    print(json.dumps(rows, allow_nan=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
