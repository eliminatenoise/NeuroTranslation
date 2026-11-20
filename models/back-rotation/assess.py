"""Independent evaluator for the four designated assessment participants after release of all seals."""
import argparse
import hashlib
import json
from pathlib import Path

from extract import read_trial
from score import person_scores, predictions, summarize

HERE = Path(__file__).resolve().parent


def verify(directory):
    manifest = json.loads((directory / 'seal.json').read_text())
    required = {'model.json', 'protocol.json', 'extract.py', 'portable.py', 'score.py', 'assess.py', 'fit.py', 'development.json'}
    if not required.issubset(manifest['sha256']):
        raise ValueError('Incomplete frozen specialist seal')
    for name, expected in manifest['sha256'].items():
        if Path(name).name != name or hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen specialist file failed verification: {name}')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cache', type=Path)
    ap.add_argument('--output', required=True, type=Path, help='New path for aggregate scores')
    ap.add_argument('--private-person-output', type=Path, help='Optional new private path for paired person scores')
    args = ap.parse_args()
    if args.private_person_output and args.private_person_output.resolve() == args.output.resolve():
        raise ValueError('Aggregate and person-level scores require distinct files')
    if args.output.exists() or (args.private_person_output and args.private_person_output.exists()):
        raise FileExistsError('Choose a new output path to preserve completed results')
    seal = verify(HERE)
    model = json.loads((HERE / 'model.json').read_text())
    spec = json.loads((HERE / 'protocol.json').read_text())
    people = {}
    for person in spec['split']['assessment_after_seal']:
        trials = [read_trial(args.cache / person / f'trial-{n:02}.mat') for n in spec['split']['trials']]
        people[person] = person_scores(trials, [predictions(model, t) for t in trials])
    report = {'stage': 'Untouched four-person assessment', 'model_sha256': seal['sha256']['model.json'], **summarize(people)}
    with args.output.open('x') as stream:
        json.dump(report, stream, allow_nan=False, indent=2)
        stream.write('\n')
    if args.private_person_output:
        with args.private_person_output.open('x') as stream:
            json.dump(people, stream, allow_nan=False, indent=2)
            stream.write('\n')

if __name__ == '__main__':
    main()
