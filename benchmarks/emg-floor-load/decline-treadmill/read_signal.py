"""Read named voltage and calibrated force columns on the stored trial clock."""

from dataclasses import dataclass
from hashlib import file_digest
from pathlib import Path
import struct

import c3d
import numpy as np
from scipy.io import loadmat


POINT_HZ = 200
ANALOG_HZ = 2000
SUBFRAMES = ANALOG_HZ // POINT_HZ
EMG_SITES = ('LTA', 'RTA', 'LRF', 'RRF', 'LBF', 'RBF', 'LGMED', 'RGMED',
             'LMGAS', 'RMGAS', 'LVL', 'RVL', 'LGRAC', 'RGRAC', 'LGMAX', 'RGMAX')
BIN_MS = 50
LONG_HISTORY_MS = 1000
SHORT_HISTORY_MS = 200
PRE_ISSUE_GAP_MS = 10
HORIZON_MS = 100
ISSUE_STEP_MS = 100


def require(test, message):
    if not test:
        raise ValueError(message)


def hash_file(path):
    with Path(path).open('rb') as handle:
        return file_digest(handle, 'sha256').hexdigest()


@dataclass
class Trial:
    analog: np.ndarray
    names: np.ndarray
    units: np.ndarray
    force_axes: np.ndarray
    corners: np.ndarray
    frames: int
    data_offset: int

    @property
    def sample_count(self):
        return self.frames * SUBFRAMES

    def columns(self, indices, columns):
        rows = np.asarray(indices, dtype=np.int64)
        cols = np.asarray(columns, dtype=np.int64)
        require(rows.ndim == cols.ndim == 1 and len(rows) and len(cols)
                and rows.min() >= 0 and rows.max() < self.sample_count
                and cols.min() >= 0 and cols.max() < len(self.names), 'An analogue read is out of range.')
        # Select the columns in the first indexed read. Reshaping the record
        # to a flat analogue grid can copy all channels, including held force.
        selection = self.analog[(rows // SUBFRAMES)[:, None], (rows % SUBFRAMES)[:, None], cols[None, :]]
        return selection.astype(np.float64)


def open_trial(path):
    with path.open('rb') as stream:
        first_block = stream.read(512)
        param, tag, points, analog, start, stop, _, scale, data_block, subframes, rate = struct.unpack_from(
            '<BBHHHHHfHHf', first_block)
        stream.seek((param - 1) * 512 + 3)
        processor = stream.read(1)
        require((tag, start, subframes, rate, processor) == (80, 1, SUBFRAMES, POINT_HZ, b'T')
                and scale < 0 and analog % SUBFRAMES == 0, 'Unsupported native C3D clock or encoding.')
        stream.seek(0)
        metadata = c3d.Reader(stream)
        count = stop - start + 1
        channels = analog // SUBFRAMES
        require((metadata.first_frame, metadata.last_frame, metadata.point_used, metadata.analog_used)
                == (start, stop, points, channels) and metadata.analog_rate == ANALOG_HZ
                and metadata.point_rate == POINT_HZ and int(metadata.header.data_block) == data_block
                and metadata.get_float('ANALOG:GEN_SCALE') == 1, 'Header, acquisition clock or units disagree.')

        def analogue_parameter(name, attribute):
            pieces = [metadata.get('ANALOG:' + name + suffix) for suffix in ('', '2')]
            joined = np.concatenate([getattr(piece, attribute) for piece in pieces if piece is not None])
            require(joined.size == channels, f'Analogue metadata for {name} have the wrong size.')
            return joined

        names = np.char.strip(np.asarray(analogue_parameter('LABELS', 'string_array'), dtype=str))
        units = np.char.strip(np.asarray(analogue_parameter('UNITS', 'string_array'), dtype=str))
        require(np.all(analogue_parameter('SCALE', 'float_array') == 1)
                and np.all(analogue_parameter('OFFSET', 'int16_array') == 0), 'Unexpected analogue calibration scale.')
        force_axes = metadata.get('FORCE_PLATFORM:CHANNEL').int16_array.astype(np.int64) - 1
        corners = metadata.get('FORCE_PLATFORM:CORNERS').float_array.astype(np.float64)
        require(int(metadata.get('FORCE_PLATFORM:USED').uint16_value) == 2
                and np.array_equal(metadata.get('FORCE_PLATFORM:TYPE').int16_array, [2, 2])
                and force_axes.shape == (2, 6) and corners.shape == (2, 4, 3)
                and np.isfinite(corners).all() and len(set(force_axes.ravel())) == 12
                and force_axes.min() >= 0 and force_axes.max() < channels, 'Two independent Type-2 plates are required.')
        for number, row in enumerate(force_axes, 1):
            expected = [base + str(number) for base in (
                'Force.Fx', 'Force.Fy', 'Force.Fz', 'Moment.Mx', 'Moment.My', 'Moment.Mz')]
            require(list(names[row]) == expected and list(units[row]) == ['N'] * 3 + ['Nmm'] * 3,
                    'Physical plate names and units do not agree.')
        normals = np.cross(corners[:, 0] - corners[:, 1], corners[:, 0] - corners[:, 3])
        lengths = np.linalg.norm(normals, axis=1)
        require((lengths > 0).all() and (normals[:, 2] / lengths < -.98).all(),
                'Calibrated plate normals do not support positive-up force.')
    start_byte = (data_block - 1) * 512
    width = 4 * points + analog
    require(start_byte + count * width * 4 == path.stat().st_size, 'Native sample extent disagrees with file size.')
    frame_words = np.memmap(path, dtype='<f4', mode='r', offset=start_byte, shape=(count, width))
    analogue = frame_words[:, 4 * points:].reshape(count, SUBFRAMES, channels)
    require(np.shares_memory(frame_words, analogue), 'Analogue view unexpectedly copies signal data.')
    return Trial(analogue, names, units, force_axes, corners, count, start_byte)


def match_emg(trial, author_csv):
    with author_csv.open() as handle:
        names = handle.readline().strip().split(',')
    require(names[0] == 'time' and len(set(names)) == len(names) and all(site in names for site in EMG_SITES),
            'The named same-trial author EMG header is incomplete or ambiguous.')
    # Use only an early one-second identity check. Later voltages and every
    # force column stay out of the name and offset decision.
    first = ANALOG_HZ
    rows = np.arange(first, first + ANALOG_HZ, dtype=np.int64)
    stored = np.loadtxt(author_csv, skiprows=1 + first, max_rows=len(rows), delimiter=',',
                        usecols=[0, *(names.index(site) for site in EMG_SITES)])
    require(stored.shape == (len(rows), len(EMG_SITES) + 1)
            and np.max(np.abs(stored[:, 0] - rows / ANALOG_HZ)) < 1e-10,
            'Author EMG time does not match the native early sample indices.')
    available = np.flatnonzero(trial.units == 'V')
    values = trial.columns(rows, available)
    chosen = []
    checks = []
    for index, site in enumerate(EMG_SITES, 1):
        reference = stored[:, index]
        margin = np.max(np.abs(values - reference[:, None]), axis=0)
        exact = np.flatnonzero(np.isfinite(margin) & (margin < 1e-16))
        require(np.isfinite(reference).all() and reference.std() > 1e-8 and len(exact) == 1,
                f'No unique, nonflat exact voltage channel for {site}.')
        word = int(available[exact[0]])
        chosen.append(word)
        checks.append({'muscle': site, 'channel': word + 1, 'native_label': str(trial.names[word]),
                       'max_abs_error_volts': float(margin[exact[0]])})
    require(len(set(chosen)) == len(chosen), 'More than one muscle matches the same column.')
    return np.asarray(chosen), checks


def activity_bounds(down, up, flags, trial):
    def parse(path):
        result = {}
        data = loadmat(path, variable_names=('left', 'right'), verify_compressed_data_integrity=True)
        for side in ('left', 'right'):
            rows = data.get(side)
            require(rows is not None and rows.ndim == 2 and rows.shape[1] == 2 and np.isfinite(rows).all(),
                    f'Invalid author cycle timing for {side}.')
            if len(rows) == 0:
                result[side] = np.empty((0, 2), dtype=np.int64)
                continue
            samples = np.rint(rows * POINT_HZ).astype(np.int64)
            require(np.allclose(rows * POINT_HZ, samples, rtol=0, atol=1e-8)
                    and np.all(samples[:, 0] < samples[:, 1]) and samples.min() >= 0
                    and samples.max() < trial.frames and np.all(samples[:-1, 1] <= samples[1:, 0]),
                    'Author cycle timing is overlapping or off the original point grid.')
            result[side] = samples
        return result

    down_rows, up_rows = parse(down), parse(up)
    with flags.open() as handle:
        require(handle.readline().strip() == 'time,left,right', 'Unverified author activity flag format.')
    labels = np.loadtxt(flags, skiprows=1, delimiter=',')
    require(labels.shape == (trial.frames, 3)
            and np.max(np.abs(labels[:, 0] - np.arange(trial.frames) / POINT_HZ)) < 1e-8
            and np.isin(labels[:, 1:], [0, 1]).all(), 'Author flags do not match the stored point-frame clock.')
    down_used = [rows for rows in down_rows.values() if len(rows)]
    up_used = [rows for rows in up_rows.values() if len(rows)]
    require(down_used and up_used, 'The paired author sessions need observed activity bounds.')
    first = max(rows[0, 0] for rows in down_used)
    last = min(rows[-1, 1] for rows in down_used)
    earliest_up = min(rows[0, 0] for rows in up_used)
    latest_up = max(rows[-1, 1] for rows in up_used)
    require(first < last and (last < earliest_up or first > latest_up),
            'Incline and decline boundaries do not identify distinct intervals in the original file.')
    return (int(first), int(last)), {
        'decline_counts': {side: len(value) for side, value in down_rows.items()},
        'incline_counts': {side: len(value) for side, value in up_rows.items()},
        'decline_activity_flag_fraction': labels[first:last, 1:].mean(axis=0).tolist(),
        'decline_point_bounds': [int(first), int(last)], 'incline_point_extent': [int(earliest_up), int(latest_up)],
    }


def windows(trial, channel_indices, point_bounds):
    to_rows = lambda milliseconds: milliseconds * ANALOG_HZ // 1000
    left, right = (bound * SUBFRAMES for bound in point_bounds)
    history = to_rows(LONG_HISTORY_MS)
    gap = to_rows(PRE_ISSUE_GAP_MS)
    bin_rows = to_rows(BIN_MS)
    horizon = to_rows(HORIZON_MS)
    step = to_rows(ISSUE_STEP_MS)
    first = ((left + history + gap + step - 1) // step) * step
    issue = np.arange(first, right - horizon + 1, step, dtype=np.int64)
    require(len(issue) > 0, 'The admission interval does not contain a complete forecast window.')
    indices = issue[:, None] - gap - history + np.arange(history)
    volts = trial.columns(indices.ravel(), channel_indices).reshape(len(issue), -1, bin_rows, len(channel_indices))
    recorded = np.isfinite(volts).all(axis=(2, 3)).all(axis=1)
    rms = np.sqrt(np.mean(np.square(volts[recorded]), axis=2))
    require(np.isfinite(rms).all(), 'RMS overflowed or retained a missing value.')
    return issue, recorded, np.log10(np.maximum(rms, 1e-6)).astype(np.float32)


def force_impulses(trial, issue):
    samples = np.asarray(issue, dtype=np.int64)[:, None] + np.arange(HORIZON_MS * ANALOG_HZ // 1000)
    values = -trial.columns(samples.flat, trial.force_axes[:, 2]).reshape(*samples.shape, 2)
    return values.sum(axis=1) / ANALOG_HZ
