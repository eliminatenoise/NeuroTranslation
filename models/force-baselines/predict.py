"""Run the Van Criekinge fit-only force forecast candidates with NumPy."""

from argparse import ArgumentParser
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import numpy as np


PENALTIES = (0.001, 0.01, 0.1, 1.0)
ENDPOINTS = ('event', 'impulse')
ARMS = {
    'main': ('emg', 'force', 'force_emg'),
    'early': ('force_emg', 'force_earlier_emg'),
}
CHANNELS = {
    'common-six': ('LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'RERS'),
    'strict-fourteen': (
        'LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'LTA', 'LVL',
        'RBF', 'RERS', 'RGAS', 'RRF', 'RST', 'RTA', 'RVL',
    ),
}
DIGESTS = {
    'common-six': 'aa499793a7d84488befd94bc2a628df490896700291af58d2befa0bd1d6bb3bf',
    'strict-fourteen': '2b90dd0b5ddc337ba58c96d5cc387ffe375ad7170cea6cdf3191d3a700553bdd',
}


def prefix(endpoint, group):
    return endpoint + ('_early' if group == 'early' else '') + '_matched'


@dataclass(frozen=True)
class CandidateGrid:
    channels: tuple
    coefficients: dict

    def predict(self, *, endpoint, group, arm, penalty, emg_rms_v=None, past_force_n=None, earlier_emg_rms_v=None):
        """Predict one outcome for one plate from complete histories in physical units."""
        if endpoint not in ENDPOINTS or group not in ARMS or arm not in ARMS[group] or penalty not in PENALTIES:
            raise ValueError('Choose an available endpoint, comparison group, sensor arm and penalty.')
        name = prefix(endpoint, group)
        center = self.coefficients[name + '_center']
        scale = self.coefficients[name + '_scale']
        split = 10 * len(self.channels)
        design = np.zeros(len(center) + 1, dtype=np.float64)
        design[0] = 1.0
        if arm != 'force':
            emg = earlier_emg_rms_v if arm == 'force_earlier_emg' else emg_rms_v
            emg = np.asarray(emg, dtype=np.float64)
            if emg.shape != (10, len(self.channels)) or not np.isfinite(emg).all() or (emg < 0).any():
                raise ValueError('Pass ten complete, nonnegative RMS voltage bins for the ordered EMG channels.')
            design[1:split + 1] = (emg.reshape(-1) - center[:split]) / scale[:split]
        if arm != 'emg':
            force = np.asarray(past_force_n, dtype=np.float64)
            if force.shape != (10,) or not np.isfinite(force).all():
                raise ValueError('Pass ten complete signed vertical-force means in newtons for one plate.')
            design[split + 1:] = (force - center[split:]) / scale[split:]
        beta = self.coefficients[f'{name}_{arm}_beta'][PENALTIES.index(penalty)]
        value = float(design @ beta)
        if not np.isfinite(value):
            raise ValueError('Prediction overflowed. Check the input units and ranges.')
        if endpoint == 'event':
            small = float(np.exp(-abs(value)))
            return 1.0 / (1.0 + small) if value >= 0.0 else small / (1.0 + small)
        return value


def load(mode):
    """Authenticate the bundled learned candidate archive and load numeric arrays."""
    if mode not in CHANNELS:
        raise ValueError(f'Choose one of {", ".join(CHANNELS)}.')
    channels = CHANNELS[mode]
    width = 10 * (len(channels) + 1)
    shapes = {}
    for endpoint in ENDPOINTS:
        for group, arms in ARMS.items():
            name = prefix(endpoint, group)
            shapes.update({name + '_center': (width,), name + '_scale': (width,)})
            shapes.update({name + '_' + arm + '_beta': (len(PENALTIES), width + 1) for arm in arms})
    raw = Path(__file__).resolve().with_name(mode + '.npz').read_bytes()
    if sha256(raw).hexdigest() != DIGESTS[mode]:
        raise ValueError(f'The {mode} coefficient archive does not match its SHA-256.')
    with np.load(BytesIO(raw), allow_pickle=False) as archive:
        if len(archive.files) != len(shapes) or set(archive.files) != set(shapes):
            raise ValueError('Unexpected coefficient archive fields.')
        arrays = {}
        for name, shape in shapes.items():
            value = archive[name]
            if (value.shape != shape or value.dtype != np.float64 or not np.isfinite(value).all()
                    or (name.endswith('_scale') and (value <= 0).any())):
                raise ValueError(f'Invalid coefficient array {name}.')
            value.setflags(write=False)
            arrays[name] = value
    return CandidateGrid(channels, arrays)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=CHANNELS)
    parser.add_argument('--group', choices=ARMS, default='main')
    parser.add_argument('--arm', choices=sorted(set().union(*ARMS.values())), default='force_emg')
    args = parser.parse_args()
    if args.arm not in ARMS[args.group]:
        parser.error('That sensor arm is unavailable in this comparison group.')
    grid = load(args.mode)
    emg = np.linspace(0.00002, 0.00004, 10)[:, None] * np.linspace(0.8, 1.2, len(grid.channels))
    force = np.linspace(-0.5, 1.0, 10)
    print('Invented histories. Fit-only candidates.')
    print(f'{args.mode} / {args.group} / {args.arm}')
    print('Penalty      New-load probability      Signed impulse (N s)')
    for penalty in PENALTIES:
        prediction = {
            endpoint: grid.predict(endpoint=endpoint, group=args.group, arm=args.arm, penalty=penalty,
                                   emg_rms_v=emg, earlier_emg_rms_v=0.75 * emg, past_force_n=force)
            for endpoint in ENDPOINTS
        }
        print(f'{penalty:<12g} {prediction["event"]:<25.7f} {prediction["impulse"]:.7f}')


if __name__ == '__main__':
    main()
