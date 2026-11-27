"""Whitelist C3D reader and walk qualification gates (protocol sections 4.2 and 4.3).

The same reader serves the bounded header probe and the full walk reader. It decodes:
- file header words 1-12 only (the event table, words 150-234, is never decoded);
- group names, to map group numbers;
- parameter names only inside ANALOG, FORCE_PLATFORM, POINT and TRIAL (elsewhere the name bytes
  are stepped over by their length field);
- parameter values only for the whitelist below.
EVENT, EVENT_CONTEXT, ANALYSIS, SUBJECTS, MANUFACTURER, PROCESSING and every other group are never
decoded. Every decode is written to an audit log so tests can prove it.

Standard library only for parsing; NumPy is needed only by read_columns().
"""
import math
import struct

INTEL = 84
NAME_GROUPS = ('ANALOG', 'FORCE_PLATFORM', 'POINT', 'TRIAL')
VALUE_WHITELIST = {
    'ANALOG': frozenset({'USED', 'LABELS', 'UNITS', 'SCALE', 'OFFSET', 'GEN_SCALE', 'RATE'}),
    'FORCE_PLATFORM': None,  # every parameter
    'POINT': frozenset({'RATE', 'DATA_START', 'UNITS', 'FRAMES', 'USED', 'SCALE'}),
    'TRIAL': frozenset({'Z_DIRECTION'}),
}
NEVER_DECODED = ('EVENT', 'EVENT_CONTEXT', 'ANALYSIS', 'SUBJECTS', 'MANUFACTURER', 'PROCESSING')
ANALOG_ALLOWED = frozenset({'USED', 'LABELS', 'DESCRIPTIONS', 'GEN_SCALE', 'SCALE', 'OFFSET', 'UNITS', 'RATE', 'GAIN'})
SIX = ('LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'RERS')
FOURTEEN = ('LBF', 'LERS', 'LGAS', 'LRF', 'LST', 'LTA', 'LVL', 'RBF', 'RERS', 'RGAS', 'RRF', 'RST', 'RTA', 'RVL')
FORCE_ROWS = ('Force.Fx', 'Force.Fy', 'Force.Fz', 'Moment.Mx', 'Moment.My', 'Moment.Mz')
PLATES_USED = (1, 2)


class ReadError(Exception):
    pass


def needed_bytes(prefix):
    """Bounded-inflation targets from the first bytes: (parameter block p, DATA_START word 9)."""
    if len(prefix) < 512:
        raise ReadError('header-short')
    p = prefix[0]
    data_start = struct.unpack_from('<H', prefix, 16)[0]
    if p < 2 or prefix[1] != 0x50:
        raise ReadError('header-magic')
    return p, data_start


def parameter_end(prefix):
    """H = (p - 1 + c) * 512 once (p - 1) * 512 + 4 bytes are available."""
    p, _ = needed_bytes(prefix)
    at = (p - 1) * 512
    if len(prefix) < at + 4:
        raise ReadError('parameter-start-short')
    return (p - 1 + prefix[at + 2]) * 512


def _value(raw, esize, dims):
    n = 1
    for d in dims:
        n *= d
    if esize == -1:
        if len(dims) <= 1:
            return raw.decode('latin1').strip()
        width = dims[0]
        return [raw[i * width:(i + 1) * width].decode('latin1').strip() for i in range(n // width)]
    code = {1: 'b', 2: 'h', 4: 'f'}.get(esize)
    if code is None:
        raise ReadError('parameter-type')
    return list(struct.unpack(f'<{n}{code}', raw))


def parse(buf, audit=None):
    """Parse words 1-12 and the whitelisted parameters from at least H bytes of a C3D file."""
    p, data_start = needed_bytes(buf)
    h_end = parameter_end(buf)
    if len(buf) < h_end:
        raise ReadError('parameter-section-short')
    log = audit if audit is not None else []
    words = struct.unpack_from('<6H', buf, 0)
    header = {
        'parameter_block': buf[0], 'magic': buf[1], 'point_count': words[1], 'analog_words': words[2],
        'first_frame': words[3], 'last_frame': words[4], 'scale': struct.unpack_from('<f', buf, 12)[0],
        'data_start': data_start, 'analog_per_frame': struct.unpack_from('<H', buf, 18)[0],
        'frame_rate': struct.unpack_from('<f', buf, 20)[0],
    }
    start = (p - 1) * 512
    blocks, processor = buf[start + 2], buf[start + 3]
    if processor != INTEL:
        raise ReadError('not-intel')
    end = start + blocks * 512
    records = []
    groups = {}
    q = start + 4
    while q + 2 <= end:  # pass 1: group names; parameter names stepped over by length only
        nlen, gid = struct.unpack_from('<bb', buf, q)
        if nlen == 0:
            break
        size = abs(nlen)
        r = q + 2 + size
        if r + 2 > end:
            raise ReadError('parameter-record-overrun')
        offset = struct.unpack_from('<h', buf, r)[0]
        nxt = r + offset if offset else end
        if gid < 0:
            name = buf[q + 2:q + 2 + size].decode('latin1').upper()
            groups[-gid] = name
            log.append(('group-name', name, None))
        else:
            records.append((gid, q, size, r, nxt))
        if offset and nxt <= q:
            raise ReadError('parameter-record-loop')
        q = nxt
    params = {g: {} for g in NAME_GROUPS}
    names = {g: [] for g in NAME_GROUPS}
    for gid, q, size, r, nxt in records:  # pass 2: whitelisted groups only
        group = groups.get(gid)
        if group not in NAME_GROUPS:
            continue
        name = buf[q + 2:q + 2 + size].decode('latin1').upper()
        names[group].append(name)
        log.append(('parameter-name', group, name))
        allowed = VALUE_WHITELIST[group]
        if allowed is not None and name not in allowed:
            continue
        esize = struct.unpack_from('<b', buf, r + 2)[0]
        nd = buf[r + 3]
        dims = list(buf[r + 4:r + 4 + nd])
        count = 1
        for d in dims:
            count *= d
        at = r + 4 + nd
        raw = buf[at:at + abs(esize) * count]
        if len(raw) != abs(esize) * count or at + len(raw) > end:
            raise ReadError('parameter-value-overrun')
        params[group][name] = {'dims': dims, 'value': _value(raw, esize, dims), 'type': esize}
        log.append(('parameter-value', group, name))
    return {'header': header, 'params': params, 'names': names, 'groups': sorted(set(groups.values())),
            'parameter_end': h_end, 'processor': processor}


def _get(params, group, name):
    item = params[group].get(name)
    return None if item is None else item['value']


def _scalar(v):
    if isinstance(v, list):
        return v[0] if len(v) == 1 else None
    return v


def layout(parsed, expanded_bytes=None):
    """Apply the walk gates. Returns (verdict, reasons, layout dict, description dict)."""
    reasons = []
    h, prm = parsed['header'], parsed['params']

    def gate(ok, code):
        if not ok:
            reasons.append(code)
        return ok

    point_rate = _scalar(_get(prm, 'POINT', 'RATE'))
    analog_rate = _scalar(_get(prm, 'ANALOG', 'RATE'))
    point_scale = _scalar(_get(prm, 'POINT', 'SCALE'))
    gate(point_rate == 100.0 and h['frame_rate'] == 100.0, 'clock-point')
    gate(analog_rate == 1000.0 and h['analog_per_frame'] == 10, 'clock-analog')
    gate(h['scale'] < 0 and point_scale is not None and point_scale == h['scale'], 'storage-not-float')
    gate(parsed['processor'] == INTEL, 'not-intel')
    used = _scalar(_get(prm, 'ANALOG', 'USED'))
    points = _scalar(_get(prm, 'POINT', 'USED'))
    p_start = _scalar(_get(prm, 'POINT', 'DATA_START'))
    p_frames = _scalar(_get(prm, 'POINT', 'FRAMES'))
    first, last = h['first_frame'], h['last_frame']
    frames = last - first + 1
    agree = (used is not None and points is not None and p_start is not None and p_frames is not None
             and points == h['point_count'] and (p_start & 0xFFFF) == h['data_start'] and 1 <= first <= last
             and h['analog_words'] == used * h['analog_per_frame']
             and (p_frames & 0xFFFF) in (frames, last))
    gate(agree, 'header-parameter-disagree')
    frame_bytes = (h['point_count'] * 16 + (used or 0) * 10 * 4) if agree else 0
    data_offset = (h['data_start'] - 1) * 512
    extent_end = data_offset + frames * frame_bytes
    if expanded_bytes is not None:
        gate(agree and 0 <= expanded_bytes - extent_end < 512, 'extent')
    gate(parsed['parameter_end'] <= data_offset, 'parameters-overlap-data')
    labels = _get(prm, 'ANALOG', 'LABELS') or []
    units = _get(prm, 'ANALOG', 'UNITS') or []
    labels = [labels] if isinstance(labels, str) else labels
    units = [units] if isinstance(units, str) else units
    gate(len(labels) == len(units) == (used or -1) and len(set(labels)) == len(labels), 'analog-labels')
    gate(not (set(parsed['names']['ANALOG']) - ANALOG_ALLOWED), 'analog-unknown-field')
    volt = [i for i, (lab, unit) in enumerate(zip(labels, units)) if lab.startswith('Voltage.') and unit == 'V']
    six_ok = all(labels.count(f'Voltage.{m}') == 1 for m in SIX)
    emg = [labels.index(f'Voltage.{m}') for m in SIX] if six_ok else []
    six_ok = six_ok and all(units[c] == 'V' for c in emg)
    fp = prm['FORCE_PLATFORM']
    gate(_scalar(_get(prm, 'FORCE_PLATFORM', 'USED')) == 4 and _get(prm, 'FORCE_PLATFORM', 'TYPE') == [2, 2, 2, 2]
         and _get(prm, 'FORCE_PLATFORM', 'ZERO') == [1, 0] and 'CAL_MATRIX' not in fp
         and _scalar(_get(prm, 'TRIAL', 'Z_DIRECTION')) == 5 and _get(prm, 'POINT', 'UNITS') == 'mm',
         'plate-type-calibration-axis')
    channel = _get(prm, 'FORCE_PLATFORM', 'CHANNEL')
    channel_ok = (isinstance(channel, list) and len(channel) == 24 and fp['CHANNEL']['dims'] == [6, 4]
                  and all(1 <= c <= len(labels) for c in channel) and len(set(channel)) == 24)
    board = [channel[i * 6:(i + 1) * 6] for i in range(4)] if channel_ok else []
    if channel_ok:
        for plate, cols in enumerate(board, 1):
            channel_ok &= [labels[c - 1] for c in cols] == [f'{row}{plate}' for row in FORCE_ROWS]
            channel_ok &= [units[c - 1] for c in cols] == ['N'] * 3 + ['Nmm'] * 3
        clash = set(emg) if six_ok else set(volt)
        channel_ok &= not ({c - 1 for c in channel} & clash)
    gate(channel_ok, 'plate-channels')
    corners, origin = _get(prm, 'FORCE_PLATFORM', 'CORNERS'), _get(prm, 'FORCE_PLATFORM', 'ORIGIN')
    geometry_ok = (isinstance(corners, list) and len(corners) == 48 and isinstance(origin, list) and len(origin) == 12
                   and all(math.isfinite(v) for v in corners + origin))
    normal_z = []
    if geometry_ok:
        c = [[corners[(pl * 4 + k) * 3:(pl * 4 + k) * 3 + 3] for k in range(4)] for pl in range(4)]
        geometry_ok &= all(abs(c[pl][k][2]) <= 1e-9 for pl in range(4) for k in range(4))
        geometry_ok &= all(origin[pl * 3 + 2] > 0 for pl in range(4))
        for pl in range(4):
            a = [c[pl][0][j] - c[pl][1][j] for j in range(3)]
            b = [c[pl][0][j] - c[pl][3][j] for j in range(3)]
            n = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
            norm = math.sqrt(sum(x * x for x in n))
            geometry_ok &= norm > 0 and abs(n[2] / norm + 1.0) <= 1e-12
            normal_z.append(n[2] / norm if norm > 0 else float('nan'))
    gate(geometry_ok, 'plate-geometry')
    scale = _get(prm, 'ANALOG', 'SCALE') or []
    offset = _get(prm, 'ANALOG', 'OFFSET') or []
    gen = _scalar(_get(prm, 'ANALOG', 'GEN_SCALE'))
    gate(len(scale) == len(labels) == len(offset) and all(math.isfinite(s) and s != 0 for s in scale)
         and gen is not None and math.isfinite(gen) and gen != 0, 'analog-calibration')
    other = list(reasons)
    if not six_ok:
        reasons.append('six-names')
    if not reasons:
        verdict = 'Q6'
    elif not other and len(volt) >= 4:
        verdict = 'QP'
    else:
        verdict = 'X'
    names = {lab[len('Voltage.'):] for lab, unit in zip(labels, units) if lab.startswith('Voltage.') and unit == 'V'}
    description = {'analog_channels': len(labels), 'voltage_channels_in_V': len(volt),
                   'muscle_names_present': {m: m in names for m in FOURTEEN}}
    lay = None
    if verdict in ('Q6', 'QP') and agree:
        lay = {'first_frame': first, 'last_frame': last, 'frames': frames, 'data_offset': data_offset,
               'point_bytes': h['point_count'] * 16, 'analog_count': used, 'frame_bytes': frame_bytes,
               'emg_columns': emg, 'force_z_columns': [board[p - 1][2] - 1 for p in PLATES_USED] if board else [],
               'scale': scale, 'gen_scale': gen, 'offset': offset, 'corners': corners, 'labels': labels}
    return verdict, reasons, lay, description


def read_columns(buffer, lay, columns):
    """Calibrated samples (raw - OFFSET) * (SCALE * GEN_SCALE) of the selected analog columns, float64."""
    import numpy as np
    end = lay['data_offset'] + lay['frame_bytes'] * lay['frames']
    if not 0 <= len(buffer) - end < 512:
        raise ReadError('extent')
    if len(set(columns)) != len(columns) or not all(0 <= c < lay['analog_count'] for c in columns):
        raise ReadError('columns')
    scale = np.asarray(lay['scale'], dtype=np.float64) * float(lay['gen_scale'])
    offset = np.asarray(lay['offset'], dtype=np.float64)
    first = lay['data_offset'] + lay['point_bytes']
    stride = lay['analog_count'] * 4
    out = np.empty((lay['frames'] * 10, len(columns)), dtype=np.float64)
    for k, c in enumerate(columns):
        view = np.ndarray((lay['frames'], 10), dtype='<f4', buffer=buffer, offset=first + c * 4,
                          strides=(lay['frame_bytes'], stride))
        out[:, k] = (view.astype(np.float64).reshape(-1) - offset[c]) * scale[c]
    return out


def plate_normal_z(lay):
    """Upward-sign factor of plates 1 and 2, computed as in the earlier selected-column reader."""
    import numpy as np
    corners = np.asarray(lay['corners'], dtype=np.float64).reshape(4, 4, 3)
    normal = np.cross(corners[:, 0] - corners[:, 1], corners[:, 0] - corners[:, 3])
    return (normal[:, 2] / np.linalg.norm(normal, axis=1))[:2]
