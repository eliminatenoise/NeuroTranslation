"""Four past seconds of bilateral knee angles, kept in right/left order."""
import numpy as np

MODES = ('stride', 'raw', 'shared', 'scrambled')
PERIODS = range(45, 181)


def validate_history(frames, knee_deg):
    frame = np.asarray(frames)
    knee = np.asarray(knee_deg)
    if knee.ndim == 2 and frame.ndim == 1:
        knee, frame = knee[None], frame[None]
    if (knee.ndim != 3 or knee.shape[1:] != (240, 2) or not len(knee)
            or frame.shape != knee.shape[:2] or frame.dtype.kind not in 'iu'
            or knee.dtype.kind not in 'fiu' or not np.isfinite(knee).all()):
        raise ValueError('Supply 240 integer frame numbers and 240 finite [right, left] degree pairs per walk.')
    # Cast first to avoid a wrapped unsigned decrement passing the consecutive-frame check.
    if (frame < 0).any() or (frame >= 2**53).any() or (np.diff(frame.astype(np.int64), axis=1) != 1).any():
        raise ValueError('Frame numbers must be nonnegative consecutive integers below 2^53.')
    return knee.astype(np.float64, copy=False)


def prefix_periods(knee):
    recent = knee[:, -60:]
    with np.errstate(over="ignore", invalid="ignore"):
        costs = np.column_stack([np.square(recent - knee[:, -60-p:-p]).sum(axis=(1, 2)) for p in PERIODS])
    if not np.isfinite(costs).all():
        raise ValueError("The angles exceed the numerical range of the stride comparison.")
    return np.argmin(costs, axis=1) + PERIODS.start


def features(knee, period):
    """Four time tokens, the replay estimate and the phase information shared by all readouts."""
    pieces = knee.reshape(-1, 4, 60, 2)
    token = np.concatenate((pieces.mean(axis=2), pieces[:, :, -1], pieces[:, :, -1] - pieces[:, :, -6]), axis=2)
    i = np.arange(len(knee))
    replay = knee[i, 239 + 15 - period]
    phase_error = knee[:, -1] - knee[i, 239 - period]
    extra = np.column_stack((replay, phase_error, period))
    return token, extra


def scramble(weights):
    """One prespecified permutation of each tensor used by the shared encoder."""
    rng = np.random.default_rng(1719)
    prefixes = ('project.', 'blocks.', 'last_norm.')
    return {name: rng.permutation(weights[name].ravel()).reshape(weights[name].shape)
            for name in sorted(weights) if name == 'position' or name.startswith(prefixes)}


def design(mode, token_z, extra, config, weights, linear, encode):
    raw = np.column_stack((token_z.reshape(len(extra), -1), extra))
    if mode == 'raw':
        return raw
    states = encode(config, weights, linear(weights, 'project', token_z), all_tokens=True)
    return np.column_stack((raw, states.reshape(len(extra), -1)))


def forecast(frames, knee_deg, mode, config, weights, linear, encode):
    if mode not in MODES or config.get('knee_angle', {}).get('format') != 1:
        raise ValueError('Choose a supported knee-angle checkpoint and mode: stride, raw, shared or scrambled.')
    histories = validate_history(frames, knee_deg)
    encoder = scramble(weights) if mode == 'scrambled' else weights
    outputs, periods = [], []
    for start in range(0, len(histories), 256):
        knees = histories[start:start+256]
        period = prefix_periods(knees)
        tokens, extra = features(knees, period)
        value = extra[:, :2].copy()
        if mode != 'stride':
            z = (tokens - weights['knee.token_center']) / weights['knee.token_scale']
            x = design(mode, z, extra, config, encoder, linear, encode)
            key = 'knee.' + mode + '.'
            value += ((x - weights[key+'center']) / weights[key+'scale']) @ weights[key+'coef'] + weights[key+'intercept']
        if not np.isfinite(value).all():
            raise ValueError('The input exceeds the numerical range of the knee forecast.')
        outputs.append(value)
        periods.append(period)
    return np.concatenate(outputs), np.concatenate(periods)
