"""Independently compare all exported positions to the original C3D bytes.

The reader below supports only the three pinned, analogue-free files in this
release. It reads the parameter directory for identities and uses the original
one-based header and on-disk point words. It does not use the exporter's library.
"""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import struct


def original_labels(data):
    # Byte 1 of the file chooses a 512-byte parameter block.
    start = (data[0] - 1) * 512
    processor = data[start + 3]
    if processor not in (84, 85):
        raise ValueError('Unsupported C3D processor')
    groups, tables = {}, {}
    pos = start + 4
    while pos < len(data):
        n, group = struct.unpack_from('bb', data, pos)
        if not n or not group:
            break
        n = abs(n)
        name = data[pos + 2:pos + 2 + n].decode('ascii').upper()
        next_field = pos + 2 + n
        step, = struct.unpack_from('<H', data, next_field)
        if group < 0:
            groups[-group] = name
        elif name == 'LABELS' or (name.startswith('LABELS') and name[6:].isdigit()):
            parameter = next_field + 2
            kind, dims = struct.unpack_from('bB', data, parameter)
            if kind == -1 and dims == 2:
                width, count = data[parameter + 2:parameter + 4]
                first = parameter + 4
                tables[group, name] = [data[i:i+width].decode('ascii').strip().split(':')[-1]
                                       for i in range(first, first + count * width, width)]
        if step == 0:
            break
        pos = next_field + step
    point_group = next(k for k, v in groups.items() if v == 'POINT')
    labels = []
    for n in range(1, 10):
        key = (point_group, 'LABELS' if n == 1 else 'LABELS'+str(n))
        if key not in tables:
            break
        labels.extend(tables[key])
    return processor, labels


def f32(data, index, processor):
    if processor == 84:
        return struct.unpack_from('<f', data, index)[0]
    # In the normal finite VAX F-floating values in this header, reorder the
    # two little-endian 16-bit words, then correct for the exponent bias.
    a,b,c,d = data[index:index+4]
    return struct.unpack('>f', bytes((b,a,d,c)))[0] / 4


def verify(original, packet, expected):
    raw = original.read_bytes()
    assert sha256(raw).hexdigest() == packet['source']['sha256'] == expected
    processor, labels = original_labels(raw)
    count, analog, first, last = struct.unpack_from('<4H', raw, 2)
    block, = struct.unpack_from('<H', raw, 16)
    assert len(labels) == count and analog == 0
    assert f32(raw, 20, processor) == packet['sourceRateHz'] == 120
    assert first == packet['firstFrame'] and last == packet['source']['sourceLastFrame']
    assert packet['units'] == 'mm' and packet['frameStride'] == 4 and packet['rateHz'] == 30
    assert len(packet['frames']) == 1 + (last - first) // 4
    names = set('C7 T10 STRN CLAV RBAC LFHD RFHD'.split())
    names.update(('NOSE','ANT') if packet['id']=='132_23' else ('LBHD','RBHD'))
    for side in 'LR':
        for site in 'SHO UPA ELB FRM WRA WRB FIN FWT BWT THI KNE SHN ANK HEE TOE MT5'.split():
            names.add(side+site)
    assert set(packet['markers']) == names and len(packet['markers']) == 41
    ordered = [labels.index(name) for name in packet['markers']]
    assert all(labels.count(name)==1 for name in packet['markers'])
    scale = f32(raw, 12, processor)
    sample = struct.Struct('<4f' if scale < 0 else '<4h')
    assert (processor,scale < 0) in ((84, True), (85, False))
    xyz_scale = 1.0 if scale < 0 else scale
    missing = zero_word = positions = 0
    maximum = 0.0
    for frame, points in enumerate(packet['frames']):
        assert len(points)==len(ordered)
        for point, idx in zip(points, ordered):
            offset = (block-1)*512 + (4*frame*count + idx)*sample.size
            x, y, z, flag = sample.unpack_from(raw, offset)
            valid = flag >= 0 and all(math.isfinite(v) for v in (x,y,z))
            assert valid == (point is not None)
            if not valid:
                missing += 1
                continue
            positions += 1
            zero_word += flag == 0
            error = max(abs(a-b*xyz_scale) for a,b in zip(point,(x,y,z)))
            maximum = max(maximum,error)
            assert len(point)==3 and error <= 0.050001, (frame,idx,error)
    assert missing == packet['missingMarkerSamples']
    return {'id':packet['id'],'nativeFrames':[first,last],'displayedFrames':len(packet['frames']),
            'coordinatesChecked':3*positions,'unavailablePoints':missing,'zeroQualityWords':zero_word,
            'maxExportDifferenceMm':maximum,'reader':'C3D header, parameter directory and point words'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('source'))
    p.add_argument('--packets',type=Path,default=Path('public'))
    opt=p.parse_args()
    pins={'02_06':'d99fa814308bfb0c2939fbda2bc214fc098961b48f7fb368d0574cb3d8c75356',
          '13_11':'b6939749aa733169f010a94588419cfbcf13067c01586dab0bedddd306518288',
          '132_23':'589afa2fd3d78fe08c839f84a148727ad6a97580a6947314aa87d9e5f5082d53'}
    manifest = json.loads((opt.packets/'manifest.json').read_bytes())
    assert {c['id'] for c in manifest['clips']} == set(pins)
    rows=[]
    for c in manifest['clips']:
        blob = (opt.packets/c['file']).read_bytes()
        assert sha256(blob).hexdigest()==c['sha256']
        rows.append(verify(opt.source/(c['id']+'.c3d'),json.loads(blob),pins[c['id']]))
    print(json.dumps(rows,indent=2))


if __name__=='__main__':
    main()
