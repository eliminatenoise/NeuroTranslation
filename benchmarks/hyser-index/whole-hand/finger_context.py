"""Forecast Hyser Random index-transducer voltage from released voltage histories."""

import numpy as np

EXPERIMENT = "hyser-random-finger-context-20261119-v1"
SCHEMA = "hyser-finger-context-weights-v1"
INPUT_ORDER = ("thumb", "index", "middle", "ring", "little")
FEATURE_ORDER = ("index", "thumb", "middle", "ring", "little")
FEATURE_COLUMNS = (1, 0, 2, 3, 4)
WIDTHS = {"index_only": 41, "aligned_five": 205, "aligned_summary": 49}
HORIZON = 12
LAGS = np.arange(-40, 1)
SLOPE_X = np.arange(-20.0, 21.0)
TICKS = np.arange(140, 2386, 5)
FEATURES = {
    "input_channel_order": list(INPUT_ORDER),
    "feature_channel_order": list(FEATURE_ORDER),
    "history_lags_ticks": LAGS.tolist(),
    "summary_per_nonindex_channel": ["latest_v", "ols_slope_v_per_tick"],
    "rate_hz": 100,
    "horizon_ticks": HORIZON,
    "input_unit": "V",
    "target_unit": "V",
    "target_channel": "index",
}
ATTRIBUTION = {
    "dataset": "Jiang, X., Dai, C., Liu, X., & Fan, J. (2023). Open Access Dataset and Toolbox of High-Density Surface Electromyogram Recordings (2.0.0). PhysioNet.",
    "dataset_doi": "10.13026/hxan-pe94",
    "dataset_url": "https://physionet.org/content/hd-semg/2.0.0/",
    "paper_doi": "10.1109/TNSRE.2021.3082551",
    "license": "Open Data Commons Attribution License 1.0",
    "license_url": "https://physionet.org/content/hd-semg/view-license/2.0.0/",
    "produced_work": "Contains pooled models and aggregate measures derived from the Hyser 2.0.0 Random dataset, made available by PhysioNet under ODC-By 1.0.",
}
ALPHAS = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0)


def histories(frames, ticks):
    """Gather oldest-first histories, with axes (cutoff, feature channel, lag)."""
    frames = np.asarray(frames, dtype=np.float64)
    ticks = np.asarray(ticks)
    if (frames.ndim != 2 or frames.shape[1] != 5 or ticks.ndim != 1 or not len(ticks)
            or ticks.dtype.kind not in "iu" or ticks.min() < 40 or ticks.max() >= len(frames)):
        raise ValueError("Supply a five-column voltage array and valid integer cutoffs with 41 available readings")
    positions = ticks.astype(np.intp, copy=False)[:, None] + LAGS
    return frames[positions][:, :, FEATURE_COLUMNS].transpose(0, 2, 1)


def arm_features(history, arm):
    if arm == "index_only":
        features = history[:, 0, :]
    elif arm == "aligned_five":
        features = history.reshape(len(history), WIDTHS[arm])
    elif arm == "aligned_summary":
        other = history[:, 1:, :]
        slope = (other @ SLOPE_X) / (SLOPE_X @ SLOPE_X)
        summary = np.stack((other[:, :, -1], slope), axis=-1).reshape(len(other), 8)
        features = np.column_stack((history[:, 0, :], summary))
    else:
        raise ValueError("Unknown predictive arm")
    if not np.isfinite(features).all():
        raise ValueError("Missing or nonfinite voltage in the prediction history")
    return features


def decode_model(record, width):
    if set(record) != {"alpha", "mean", "scale", "intercept", "coef"}:
        raise ValueError("Malformed model fields")
    mean, scale, coef = (np.asarray(record[key], dtype=np.float64) for key in ("mean", "scale", "coef"))
    if (any(values.shape != (width,) or not np.isfinite(values).all() for values in (mean, scale, coef))
            or np.any(scale <= 0) or not np.isfinite(record["intercept"]) or record["alpha"] not in ALPHAS):
        raise ValueError("Malformed predictor coefficients or standardization")
    return mean, scale, coef, float(record["intercept"])


def predict(frames, ticks, weights, arm="aligned_five"):
    """Use available voltages through each t to predict the released index voltage at t+12."""
    if (weights.get("schema") != SCHEMA or weights.get("experiment") != EXPERIMENT
            or weights.get("features") != FEATURES or set(weights["models"]) != set(WIDTHS)):
        raise ValueError("Weight payload and feature contract differ")
    width = WIDTHS.get(arm)
    if width is None:
        raise ValueError("Choose a deployable arm")
    mean, scale, coef, intercept = decode_model(weights["models"][arm], width)
    history = histories(frames, ticks)
    features = arm_features(history, arm)
    result = history[:, 0, -1] + intercept + ((features - mean) / scale) @ coef
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite predicted index voltage")
    return result
