"""Export three hash-pinned Carnegie Mellon optical motion recordings for the game."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import ezc3d
import numpy as np

ORIGIN = 'http://mocap.cs.cmu.edu'
TRIALS = {
    '02_06': ('d99fa814308bfb0c2939fbda2bc214fc098961b48f7fb368d0574cb3d8c75356',
              'Bend, scoop and lift', 'bend over, scoop up, rise, lift arm'),
    '13_11': ('b6939749aa733169f010a94588419cfbcf13067c01586dab0bedddd306518288',
              'Jump forward', 'forward jump'),
    '132_23': ('589afa2fd3d78fe08c839f84a148727ad6a97580a6947314aa87d9e5f5082d53',
               'Hop on the left foot', 'Hop on left foot'),
}
# These are the named skin locations in the source marker set. Omit computed
# joint centres, coordinate system axes and unlabelled points in trial 13_11.
BODY = set('LFHD RFHD LBHD RBHD NOSE ANT C7 T10 CLAV STRN RBAC'.split())
for side in 'LR':
    BODY.update(side + part for part in 'SHO UPA ELB FRM WRA WRB FIN FWT BWT THI KNE SHN ANK HEE TOE MT5'.split())
STRIDE = 4


def write_json(path, value):
    path.write_text(json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_trial(key, source_dir, output_dir, download=False):
    digest, label, source_label = TRIALS[key]
    group = key.split('_')[0]
    url = f'{ORIGIN}/subjects/{group}/{key}.c3d'
    source = source_dir / (key + '.c3d')
    if download and not source.exists():
        with urlopen(url, timeout=45) as response:
            data = response.read(4 * 1024 * 1024 + 1)
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'Unexpected source bytes for {key}')
        source.write_bytes(data)
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError(f'Unexpected source bytes for {key}')
    capture = ezc3d.c3d(str(source))
    params = capture['parameters']['POINT']
    header = capture['header']['points']
    if params['UNITS']['value'] != ['mm'] or header['frame_rate'] != 120.0:
        raise ValueError('Unexpected source clock or units.')
    labels = []
    for number in range(1, 10):
        name = 'LABELS' if number == 1 else 'LABELS' + str(number)
        if name not in params:
            break
        labels.extend(item.strip().split(':')[-1] for item in params[name]['value'])
    if len(labels) != header['size']:
        raise ValueError('The label inventory does not cover the source point channels.')
    indices = [index for index, name in enumerate(labels) if name in BODY]
    names = [labels[i] for i in indices]
    if len(names) != 41 or len(set(names)) != len(names):
        raise ValueError('This source has a different body marker set.')
    raw = capture['data']['points'][:3, indices, ::STRIDE].transpose(2, 1, 0)
    residuals = capture['data']['meta_points']['residuals'][0, indices, ::STRIDE].T
    valid = np.isfinite(raw).all(axis=2) & np.isfinite(residuals) & (residuals >= 0)
    frames = np.round(raw, 1).tolist()
    for frame, where in enumerate(valid):
        for marker in np.flatnonzero(~where):
            frames[frame][marker] = None
    first = int(header['first_frame']) + 1  # ezc3d uses zero-based indices; the C3D header is one-based.
    last = int(header['last_frame']) + 1
    orientation = params.get('Y_SCREEN', {}).get('value')
    head_heights = raw[:, names.index('LFHD'), 2] - raw[:, names.index('LHEE'), 2]
    if (orientation and orientation != ['+Z']) or np.nanmedian(head_heights) < 800:
        raise ValueError('Expected a vertical Z axis for this preview.')
    provenance = {'database':'Carnegie Mellon Graphics Lab Motion Capture Database',
                  'trialId':key,'catalogueLabel':source_label,'catalogueUrl':f'{ORIGIN}/search.php?subjectnumber={group}',
                  'sourceUrl':url,'sha256':digest,'sourceFirstFrame':first,'sourceLastFrame':last,
                  'upAxisEvidence':'source Y_SCREEN = +Z and head–heel positions' if orientation else 'inferred from head and heel positions; screen axes absent',
                  'displayCoordinates':'Lab coordinates rounded to 0.1 mm. The displayed increment describes file precision.'}
    quality_note = ('All selected positions in the source have zero quality values. The recording supplies processed marker paths without per-sample measurement accuracy.'
                    if np.all(residuals == 0) else
                    'The archive includes processed positions. The recording does not establish a measurement error for each displayed point.')
    packet = {'schema':'brain2body-optical-markers-v1','id':key,'label':label,'source':provenance,
              'units':'mm','upAxis':'z','rateHz':30,'sourceRateHz':120,'frameStride':STRIDE,'firstFrame':first,
              'lastDisplayedSourceFrame':first+(len(raw)-1)*STRIDE,'sourceFrameCount':last-first+1,
              'markers':names,'missingMarkerSamples':int((~valid).sum()),'qualityNote':quality_note,'frames':frames}
    filename = key + '.json'
    file_hash = write_json(output_dir / filename, packet)
    return {'id':key,'label':label,'file':filename,'description':source_label,'sha256':file_hash,
            'rateHz':30,'frames':len(frames),'markers':len(names),'qualityNote':quality_note,
            'sourceUrl':url,'catalogueUrl':provenance['catalogueUrl']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('source'))
    parser.add_argument('--out', type=Path, default=Path('public'))
    parser.add_argument('--download', action='store_true', help='Retrieve missing public originals; verify before saving.')
    args = parser.parse_args()
    args.source.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    clips = [export_trial(key, args.source, args.out, args.download) for key in TRIALS]
    write_json(args.out / 'manifest.json', {'schema':'brain2body-optical-collection-v1','clips':clips,
               'attribution':{'text':'The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217.',
                              'url':ORIGIN+'/'},'termsUrl':ORIGIN+'/faqs.php'})


if __name__ == '__main__':
    main()
