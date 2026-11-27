"""Physics-source allocations that can be computed from metadata alone.

Writes ALLOCATION.json next to this file (or to the path given as the first argument).
It needs only the Python standard library (3.10 or later) and reads no data file.

It computes three things:
1. Inner person folds for the 18 consumed Van Criekinge people that every arm trains on.
2. The hashed person subsets for the data-efficiency curve.
3. The table of simulated bodies: a scrambled Sobol sequence (seed 20261127) over ten body and
   condition factors, mapped to physical values.

The reserved test group is NOT allocated here. It is the physics-source group of the walking-scale
track's single allocation and is copied into BINDING.json once that protocol is committed.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

VERSION = 'physics-source-allocation-v1'
SEED = 20261127
DOI = '10.6084/m9.figshare.24192480.v1'

# The 12 people of the earlier fit role and the 6 of the earlier validation role. Both groups were
# consumed by earlier fits; here they are training people only and are never called new.
EARLIER_FIT = ['SUBJ112', 'SUBJ110', 'SUBJ096', 'SUBJ024', 'SUBJ082', 'SUBJ062',
               'SUBJ061', 'SUBJ040', 'SUBJ044', 'SUBJ043', 'SUBJ039', 'SUBJ038']
EARLIER_VALIDATION = ['SUBJ047', 'SUBJ011', 'SUBJ115', 'SUBJ075', 'SUBJ066', 'SUBJ116']
TRAINING_KNOWN = EARLIER_FIT + EARLIER_VALIDATION

N_FOLDS = 4
SUBSET_SIZES = (3, 6, 12)
N_SUBSETS = 5
N_BODIES = 1024          # Sobol points written; generators use prefixes of this list
H_NOMINAL_M = 1.70       # stature of the generic model the MyoLeg legs derive from (Rajagopal et al. 2016)


def h(text):
    return hashlib.sha256(text.encode('ascii')).hexdigest()


def inner_folds(people):
    """Rank people by sha256('physics-source-inner-v1|' + code); fold = rank mod 4."""
    order = sorted(people, key=lambda c: h(f'physics-source-inner-v1|{c}'))
    return {c: i % N_FOLDS for i, c in enumerate(order)}, order


def subsets(people):
    """For subset s, rank people by sha256('physics-source-subset-v1|s|' + code) and take the first n."""
    out = {}
    for n in SUBSET_SIZES:
        out[str(n)] = []
        for s in range(N_SUBSETS):
            order = sorted(people, key=lambda c: h(f'physics-source-subset-v1|{s}|{c}'))
            out[str(n)].append(sorted(order[:n]))
    out[str(len(people))] = [sorted(people)]
    return out


# Sobol direction numbers (Joe and Kuo, new-joe-kuo-6.21201), dimensions 2-10: (s, a, m_1..m_s).
JOE_KUO = [(1, 0, [1]), (2, 1, [1, 3]), (3, 1, [1, 3, 1]), (3, 2, [1, 1, 1]), (4, 1, [1, 1, 3, 3]),
           (4, 4, [1, 3, 5, 13]), (5, 2, [1, 1, 5, 5, 17]), (5, 4, [1, 1, 5, 5, 5]), (5, 7, [1, 1, 7, 11, 19])]
BITS = 32


def direction_numbers(dim):
    if dim == 0:
        return [1 << (BITS - k) for k in range(1, BITS + 1)]
    s, a, m = JOE_KUO[dim - 1]
    v = [0] * (BITS + 1)
    for k in range(1, s + 1):
        v[k] = m[k - 1] << (BITS - k)
    for k in range(s + 1, BITS + 1):
        x = v[k - s] ^ (v[k - s] >> s)
        for l in range(1, s):
            if (a >> (s - 1 - l)) & 1:
                x ^= v[k - l]
        v[k] = x
    return v[1:]


def sobol_int(index, v):
    """Unscrambled Sobol point in natural (binary) index order, as a 32-bit integer."""
    x, k = 0, 0
    while index:
        if index & 1:
            x ^= v[k]
        index >>= 1
        k += 1
    return x


def bitstream(label, n):
    bits, block = [], 0
    while len(bits) < n:
        digest = hashlib.sha256(f'{label}|block{block}'.encode('ascii')).digest()
        for byte in digest:
            bits.extend((byte >> (7 - i)) & 1 for i in range(8))
        block += 1
    return bits[:n]


def scrambler(dim):
    """Linear matrix scramble plus digital shift, all bits from sha256 of the seed label.

    Row p (p = 0 is the most significant bit) of the lower-triangular matrix has a 1 on the diagonal and
    hash bits below it. Output bit p is the parity of (row p AND input).
    """
    label = f'{VERSION}|sobol-scramble|seed{SEED}|dim{dim}'
    bits = bitstream(label, BITS * (BITS - 1) // 2 + BITS)
    rows, pos = [], 0
    for p in range(BITS):
        mask = 1 << (BITS - 1 - p)
        for q in range(p):
            if bits[pos]:
                mask |= 1 << (BITS - 1 - q)
            pos += 1
        rows.append(mask)
    shift = 0
    for p in range(BITS):
        shift = (shift << 1) | bits[pos + p]

    def apply(x):
        y = 0
        for p, mask in enumerate(rows):
            if bin(mask & x).count('1') & 1:
                y |= 1 << (BITS - 1 - p)
        return y ^ shift
    return apply


FACTORS = ['stature', 'bmi', 'thigh_shank_ratio', 'foot_length', 'pelvis_width', 'strength_base',
           'vmax', 'contact_time_constant', 'friction', 'speed_factor']


def body_table():
    dims = len(FACTORS)
    vs = [direction_numbers(d) for d in range(dims)]
    scr = [scrambler(d) for d in range(dims)]
    rows = []
    for i in range(N_BODIES):
        u = [(scr[d](sobol_int(i, vs[d])) + 0.5) / 2 ** BITS for d in range(dims)]
        stature = 1.50 + 0.45 * u[0]
        bmi = 18.0 + 16.0 * u[1]
        mass_raw = bmi * stature ** 2
        mass = min(115.0, max(45.0, mass_raw))
        strength_base = 0.6 + 0.7 * u[5]
        speed_factor = 0.8 + 0.45 * u[9]
        rows.append({
            'body_id': f'B{i:04d}',
            'sobol_index': i,
            'u': [round(x, 9) for x in u],
            'stature_m': round(stature, 4),
            'segment_scale': round(stature / H_NOMINAL_M, 5),
            'bmi_drawn': round(bmi, 3),
            'mass_kg': round(mass, 3),
            'mass_clipped': mass != mass_raw,
            'thigh_shank_ratio_factor': round(1 + 0.12 * (u[2] - 0.5), 5),
            'foot_length_factor': round(1 + 0.16 * (u[3] - 0.5), 5),
            'pelvis_width_factor': round(1 + 0.16 * (u[4] - 0.5), 5),
            'strength_base': round(strength_base, 5),
            'strength_factor': round(strength_base * (mass / 75.0) ** (2 / 3), 5),
            'vmax_l0_per_s': round(8.0 + 4.0 * u[6], 4),
            'contact_time_constant_s': round(0.02 + 0.02 * u[7], 5),
            'friction': round(0.6 + 0.6 * u[8], 4),
            'speed_factor': round(speed_factor, 5),
            'g1_target_speeds_m_s': [round(min(1.70, max(0.95, speed_factor * f * 1.25 * math.sqrt(stature / H_NOMINAL_M))), 4)
                                     for f in (0.9, 1.0, 1.1)],
        })
    return rows


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('ALLOCATION.json')
    folds, fold_order = inner_folds(TRAINING_KNOWN)
    bodies = body_table()
    result = {
        'version': VERSION,
        'source_doi': DOI,
        'reads_data': False,
        'training_people_known': {'earlier_fit_role': EARLIER_FIT, 'earlier_validation_role': EARLIER_VALIDATION},
        'inner_folds': {
            'rule': "Rank training people by ascending sha256('physics-source-inner-v1|' + subject code); fold = rank mod 4. "
                    'People added at binding (walking-scale training rungs) are ranked together with these 18 by the same rule, '
                    'unless the coverage test in PROTOCOL.md section 4 selects the walking-scale folds.',
            'rank_order_18': fold_order,
            'fold_of_18': folds,
        },
        'data_efficiency_subsets': {
            'rule': "For n in (3, 6, 12) and subset s in 0..4, rank the 18 people by ascending "
                    "sha256('physics-source-subset-v1|' + s + '|' + subject code) and take the first n. n = 18 is the single "
                    'set of all 18. The full pool (18 plus walking-scale training rungs) is the last point of the curve.',
            'subsets': subsets(TRAINING_KNOWN),
        },
        'bodies': {
            'rule': 'Scrambled Sobol sequence in natural index order, 10 dimensions, Joe-Kuo direction numbers, linear matrix scramble '
                    "plus digital shift with bits from sha256('physics-source-allocation-v1|sobol-scramble|seed20261127|dim' + d + "
                    "'|block' + b). u = (integer + 0.5) / 2^32. Generators use prefixes: G1 B0000-B0127, G4 B0000-B0599, "
                    'G3c B0000-B0031, G3f B0000-B0015; diversity series 1, 8, 32 and 128 bodies.',
            'factors': FACTORS,
            'mapping': {
                'stature_m': '1.50 + 0.45 u0; segment_scale = stature / 1.70',
                'mass_kg': 'BMI = 18 + 16 u1; mass = BMI * stature^2, clipped to 45..115 kg (mass_clipped records it)',
                'thigh_shank_ratio_factor': '1 + 0.12 (u2 - 0.5): thigh length times sqrt(f), shank length divided by sqrt(f)',
                'foot_length_factor': '1 + 0.16 (u3 - 0.5)',
                'pelvis_width_factor': '1 + 0.16 (u4 - 0.5)',
                'strength_factor': '(0.6 + 0.7 u5) * (mass / 75 kg)^(2/3), multiplies every muscle peak isometric force',
                'vmax_l0_per_s': '8 + 4 u6, muscle maximum shortening velocity in optimal fibre lengths per second',
                'contact_time_constant_s': '0.02 + 0.02 u7, MuJoCo solref time constant of foot-floor contacts',
                'friction': '0.6 + 0.6 u8, sliding friction of foot-floor contacts',
                'speed_factor': '0.8 + 0.45 u9; G1 target speeds = speed_factor * (0.9, 1.0, 1.1) * 1.25 m/s * sqrt(stature / 1.70), '
                                'clipped to 0.95..1.70 m/s; G4 target speed = speed_factor * reference speed * sqrt(stature / reference stature), '
                                'clipped to 0.95..1.70 m/s',
            },
            'count': len(bodies),
            'table': bodies,
        },
    }
    # One compact line per body keeps the file small and easy to compare line by line.
    table = result['bodies'].pop('table')
    text = json.dumps(result, indent=1, ensure_ascii=True)
    rows = ',\n'.join('   ' + json.dumps(r, separators=(',', ':')) for r in table)
    marker = '"count": %d' % len(table)
    text = text.replace(marker, marker + ',\n  "table": [\n' + rows + '\n  ]', 1) + '\n'
    assert json.loads(text)['bodies']['table'] == table
    out_path.write_text(text)
    print(out_path.name, hashlib.sha256(text.encode('utf-8')).hexdigest())


if __name__ == '__main__':
    main()
