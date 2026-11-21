"""Original-balanced metrics for the subsequent-go movement and delayed-count study."""
import numpy as np

SEEDS = (17, 41, 73)
N_BOOT = 5000
BOOT_SEED = 20261125
BLOCK_LENGTH = 8
RATE_FLOOR = 1e-6
PARTS = {"hand": (slice(0, 3), 1000.0), "elbow": (slice(3, 6), 1000.0), "handle": (slice(6, 8), 1.0)}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def identities(data):
    return list(zip(data["block"].tolist(), data["original"].tolist()))


def positions(data, roster):
    index = {pair: i for i, pair in enumerate(roster)}
    need(len(index) == len(roster), "duplicate original on roster")
    return np.array([index[pair] for pair in identities(data)], dtype=np.int64)


def means_in_originals(x, pos, n_original):
    """Window axis first. Empty roster entries survive as NaN."""
    x = np.asarray(x, dtype=np.float64)
    need(x.shape[0] == len(pos) and np.isfinite(x).all(), "invalid metric or roster position")
    result = np.zeros((n_original, *x.shape[1:]), dtype=np.float64)
    np.add.at(result, pos, x)
    n = np.bincount(pos, minlength=n_original).reshape((n_original,) + (1,) * (x.ndim - 1))
    return np.divide(result, n, where=n > 0, out=np.full_like(result, np.nan))


def balanced(x, pos):
    """Each observed original has weight one, including when subsampling ordinals."""
    if not len(pos):
        return None
    unique, index = np.unique(pos, return_inverse=True)
    return means_in_originals(x, index, len(unique)).mean(axis=0)


def ordinal_controls(train_values, train_pos, train_ord, eval_ord):
    overall = balanced(train_values, train_pos)
    need(overall is not None, "no training observations for baseline")
    lookup = {}
    for ordinal in np.unique(train_ord):
        select = train_ord == ordinal
        lookup[int(ordinal)] = balanced(train_values[select], train_pos[select])
    pred = np.broadcast_to(overall, (len(eval_ord), *overall.shape)).copy()
    for ordinal, value in lookup.items():
        pred[eval_ord == ordinal] = value
    return np.broadcast_to(overall, pred.shape), pred


def donors(blocks, pos, ordinals):
    """Find latest different supported original, strictly earlier in the native block."""
    result = np.full(len(pos), -1, dtype=np.int64)
    recent = {}
    for i, (block, sequence, ordinal) in enumerate(zip(blocks, pos, ordinals)):
        key = (int(block), int(ordinal))
        previous = recent.get(key)
        if previous is not None:
            j, earlier = previous
            need(earlier < sequence, "unordered or duplicated go ordinal in original")
            result[i] = j
        recent[key] = (i, sequence)
    return result


def motion_errors(actual, pred):
    need(pred.shape == actual.shape and np.isfinite(pred).all(), "incomplete motion forecast")
    out = {}
    for part, (cols, factor) in PARTS.items():
        residual = (pred[..., cols] - actual[..., cols]) * factor
        dist = np.linalg.norm(residual, axis=-1)
        out[part] = {"endpoint": dist[:, -1], "trajectory": dist.mean(axis=1),
                     "distance_by_horizon": dist, "absolute_error_by_axis": np.abs(residual).mean(axis=1),
                     "per_window_rmse_by_axis": np.sqrt(np.square(residual).mean(axis=1)), "signed_endpoint_xyz" if part != "handle" else "signed_endpoint_xy": residual[:, -1]}
    return out


def deviance(actual, pred):
    mu = np.maximum(pred, RATE_FLOOR)
    # The analytic y log(y/mu) limit at y=0 is zero.
    term = np.zeros_like(mu, dtype=np.float64)
    nz = actual > 0
    term[nz] = actual[nz] * np.log(actual[nz] / mu[nz])
    return 2 * (term - actual + mu)


def count_errors(actual, pred):
    need(pred.shape == actual.shape and np.isfinite(pred).all() and (pred >= 0).all(), "invalid count forecast")
    observed_sum, pred_sum = actual.sum(axis=1), pred.sum(axis=1)
    d_bins = deviance(actual, pred)
    d_sum = deviance(observed_sum, pred_sum)
    a_bins = np.abs(actual - pred)
    a_sum = np.abs(observed_sum - pred_sum)
    return {
        "total_deviance": d_sum.mean(axis=1), "total_mae": a_sum.mean(axis=1),
        "bin_deviance": d_bins.mean(axis=(1, 2)), "bin_mae": a_bins.mean(axis=(1, 2)),
        "total_deviance_by_unit": d_sum, "total_mae_by_unit": a_sum,
        "bin_deviance_by_unit": d_bins.mean(axis=1), "bin_mae_by_unit": a_bins.mean(axis=1),
        "deviance_by_bin": d_bins.mean(axis=2), "mae_by_bin": a_bins.mean(axis=2),
        "predicted_total_by_unit": pred_sum, "observed_total_by_unit": observed_sum,
    }


def bootstrap_draws(roster_blocks, moving, repetitions=N_BOOT, seed=BOOT_SEED):
    """Sample the full ordered roster; matrix counts include roster slots with no eligible pairs."""
    blocks = np.asarray(roster_blocks)
    size = len(blocks)
    if not size:
        return None
    rng = np.random.default_rng(seed)
    if moving:
        # Distinct recording blocks never form artificial contiguous stretches.
        groups = [np.flatnonzero(blocks == b) for b in dict.fromkeys(blocks)]
        if any(len(idx) < BLOCK_LENGTH for idx in groups):
            return None
        draws = []
        for idx in groups:
            n = len(idx)
            starts = rng.integers(n - BLOCK_LENGTH + 1, size=(repetitions, (n + BLOCK_LENGTH - 1) // BLOCK_LENGTH))
            samples = (starts[..., None] + np.arange(BLOCK_LENGTH)).reshape(repetitions, -1)[:, :n]
            draws.append(idx[samples])
        indices = np.concatenate(draws, axis=1)
    else:
        indices = rng.integers(size, size=(repetitions, size))
    flat = indices + np.arange(repetitions)[:, None] * size
    return np.bincount(flat.ravel(), minlength=repetitions * size).reshape(repetitions, size).astype(np.float64)


def difference(x, y, pos, roster_blocks, weights, seed_labels):
    """Paired seed-first, window-second loss arrays; bootstraps the mean of losses."""
    x, y = np.broadcast_arrays(x, y)
    need(x.ndim == 2 and x.shape[0] == len(seed_labels), "paired loss dimensions")
    arr = np.column_stack(((x - y).mean(axis=0), (x - y).T))
    matrix = means_in_originals(arr, pos, len(roster_blocks))
    finite = np.isfinite(matrix[:, 0])
    n = int(finite.sum())
    rows = {}
    for i, name in enumerate(["mean", *map(str, seed_labels)]):
        rows[name] = {"difference": float(matrix[finite, i].mean()) if n else None,
                      "moving_block_95": None, "iid_95": None}
    if n >= 2:
        for label, sample in weights.items():
            if sample is None:
                continue
            counts = sample @ finite.astype(float)
            valid = counts > 0
            draws = sample[valid] @ np.nan_to_num(matrix) / counts[valid, None]
            limits = np.quantile(draws, [0.025, 0.975], axis=0, method="linear")
            for i, row in enumerate(rows.values()):
                row[label] = limits[:, i].tolist()
                row[label + "_defined_draws"] = int(valid.sum())
    return {"windows": len(pos), "originals": n, "roster_originals": len(roster_blocks), **rows}


def map_tree(fn, value):
    if isinstance(value, dict):
        return {k: map_tree(fn, v) for k, v in value.items()}
    return fn(value)


def reduce_seeds(metrics, pos, mask, seed_labels):
    """Return original-balanced averages for each seed; inputs are per-window losses."""
    def reduce_leaf(value):
        avg = balanced(value[mask], pos[mask])
        return avg.tolist() if avg is not None else None
    def avg_trees(values):
        if isinstance(values[0], dict):
            return {k: avg_trees([v[k] for v in values]) for k in values[0]}
        return np.mean(values, axis=0).tolist() if values[0] is not None else None
    rows = [map_tree(reduce_leaf, val) for val in metrics]
    return {"windows": int(mask.sum()), "originals": len(np.unique(pos[mask])), "mean": avg_trees(rows),
            "by_seed": dict(zip(map(str, seed_labels), rows)) if len(rows) > 1 else {}}
