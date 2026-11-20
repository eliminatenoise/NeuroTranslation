"""Score the frozen all-development fit against separated assessment recordings."""
import argparse
import json
from pathlib import Path
from study import HELD, HERE, PROTOCOL, digest, load_person, save, score_person, summarize


def assess(cache, bundle, seal_sha256, out):
    if (out/'assessment.json').exists() or (out/'private/assessment-person.json').exists():
        raise FileExistsError('Assessment outputs already exist. Preserve original results.')
    if digest(bundle / 'seal.json') != seal_sha256:
        raise ValueError('Independent seal hash mismatch')
    seal = json.loads((bundle / 'seal.json').read_text())
    if seal['protocol_sha256'] != PROTOCOL or digest(HERE/'PROTOCOL.md') != PROTOCOL:
        raise ValueError('Original protocol changed')
    for section, repo in [('code', HERE), ('files', bundle)]:
        for file, expected in seal[section].items():
            if digest(repo/file) != expected:
                raise ValueError(f'Sealed {file} changed')
    model = json.loads((bundle/'model.json').read_text())
    known = {s['mat_sha256'] for s in seal['development_sources']}
    people = {}
    for p in HELD:
        trials = load_person(cache, p)
        originals = {t.source['mat_sha256'] for t in trials}
        if known & originals:
            raise ValueError('Repeated development or assessment member')
        known |= originals
        people[p] = score_person(model, trials)
    public = summarize(people)
    public['frozen_model_sha256'] = seal['files']['model.json']
    public['development_seal_sha256'] = seal_sha256
    public['study'] = 'Four previously unseen people, two distinct recordings each. All weights fixed.'
    save(out / 'private/assessment-person.json', people)
    save(out / 'assessment.json', public)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assessment_cache', type=Path)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('seal_sha256')
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    assess(args.assessment_cache, args.bundle, args.seal_sha256, args.out)
