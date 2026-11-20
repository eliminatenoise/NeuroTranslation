"""Build, read, fit or assess the compact, source-derived right-hand feature edition."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from fit import POLICY, code_identity, fitted, write_gallery
from hand_data import read_role, Segment
from kit_components import digest, dump
from rank import Scorer
from score import assess

FROZEN_EDITION = '44c9c00221241ecf3b1a896fa93af102dbb4ea13ea6c730db2c98b4cc3fe30b5'


def role_files(role):
    return role + '.json', role + '.npz'


def payload(c):
    return dict(key=c.key, recording=c.recording, group=c.group, captions=c.captions,
                duration=c.duration, context=c.context, cue=list(c.cue), start=c.start, end=c.end)


def read_segments(pack, role):
    if role not in ('train','review'):
        raise ValueError('Unknown feature role')
    contract=json.loads((pack/'manifest.json').read_text())
    for name in role_files(role):
        if digest(pack/name)!=contract['files'][name]:
            raise ValueError('Feature file checksum mismatch: ' + name)
    meta=json.loads((pack/(role+'.json')).read_text())
    with np.load(pack/(role+'.npz'),allow_pickle=False) as z:
        x=z['sequence']
    if x.shape!=(len(meta),24,16) or x.dtype!=np.float32:
        raise ValueError('Unexpected geometry shape or type')
    rows=[Segment(**dict(m,cue=tuple(m['cue']),sequence=v)) for m,v in zip(meta,x,strict=True)]
    if len({s.key for s in rows})!=len(rows):
        raise ValueError('Repeated segment identifier')
    return rows


def create(source, split, experiment, pack):
    pack.mkdir(parents=True,exist_ok=False)
    files={}
    for role in ('train','review'):
        rows,ledger=read_role(source,split,role)
        sealed=experiment/('training.json' if role=='train' else 'assessment/sources.json')
        if ledger!=json.loads(sealed.read_text()):
            raise ValueError('Source files or eligibility differ from original evaluation')
        names=role_files(role)
        dump([payload(c) for c in rows],pack/names[0])
        np.savez_compressed(pack/names[1],sequence=np.stack([c.sequence for c in rows]))
        files.update({n:digest(pack/n) for n in names})
    dump({'features':'24 phase bins by 16 distances in metres, missing=NaN',
          'reader_code':code_identity(),'split':digest(split),'files':files,
          'source_train_ledger':digest(experiment/'training.json'),
          'source_assessment_ledger':digest(experiment/'assessment/sources.json'),
          'rights':'CDLA-Permissive-2.0'},pack/'manifest.json')
    for role in ('train','review'):
        recovered=read_segments(pack,role)
        original,_=read_role(source,split,role)
        for a,b in zip(recovered,original,strict=True):
            if payload(a)!=payload(b) or not np.array_equal(a.sequence,b.sequence,equal_nan=True):
                raise ValueError('Feature round-trip mismatch')


def train_pack(pack,out):
    rows=read_segments(pack,'train')
    out.mkdir(parents=True,exist_ok=False)
    fitted(rows,out/'fit',POLICY)
    write_gallery(rows,out)
    fit=out/'fit'
    dump({'feature_manifest':digest(pack/'manifest.json'),'code':code_identity(),
          'weights':{p.name:digest(p) for p in sorted(fit.iterdir())},
          'gallery':{n:digest(out/n) for n in ('gallery.json','gallery.npz')},
          'training_segments':len(rows),'source':'compact feature edition'},
         fit/'seal.json')


def assess_pack(pack,out):
    scorer=Scorer(out/'fit')
    if scorer.seal.get('feature_manifest')!=digest(pack/'manifest.json'):
        raise ValueError('This fit and feature edition differ')
    train=read_segments(pack,'train')
    test=read_segments(pack,'review')
    if {s.group for s in train}&{s.group for s in test}:
        raise ValueError('Recording groups cross feature roles')
    assess(train,test,scorer,out/'assessment')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sp=p.add_subparsers(dest='action',required=True)
    build=sp.add_parser('pack')
    build.add_argument('--data',type=Path,required=True)
    build.add_argument('--split',type=Path,required=True)
    build.add_argument('--experiment',type=Path,required=True)
    for action in ('fit','assess'):
        sub=sp.add_parser(action)
        sub.add_argument('--pack',type=Path,default=Path(__file__).resolve().parent/'features')
        sub.add_argument('--output',type=Path,required=True)
        sub.add_argument('--allow-custom-features',action='store_true',
                         help='Use an explicitly different, locally prepared edition')
    build.add_argument('--pack',type=Path,required=True)
    a=p.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if a.action!='pack' and not a.allow_custom_features and digest(a.pack/'manifest.json')!=FROZEN_EDITION:
        raise ValueError('Feature edition differs from the published study. For a separate local experiment, explicitly select --allow-custom-features.')
    if a.action=='pack':
        create(a.data,a.split,a.experiment,a.pack)
    elif a.action=='fit':
        train_pack(a.pack,a.output)
    else:
        assess_pack(a.pack,a.output)


if __name__=='__main__':
    main()
