"""Forecast a stored neck-electrode reading from past voltage bins, in microvolts."""
from pathlib import Path
import json
import numpy as np

CHANNELS = ("Biceps", "SC6", "Thumb", "CP4", "ECG")
INPUTS = {
    "event_median": (), "persistence": ("SC6",), "median_innovation": ("SC6",),
    "neck": ("SC6",), "other_sites": ("SC6", "Thumb", "CP4", "ECG"), "with_axilla": CHANNELS,
}
FITTED = ("neck", "other_sites", "with_axilla")


def center(bins):
    return bins - bins[:, :5].mean(axis=1, keepdims=True)


def as_features(mode, bins):
    indices = [CHANNELS.index(ch) for ch in INPUTS[mode]]
    return bins[:, :, indices].reshape(len(bins), -1)


def regression(fit, features):
    z = np.clip((features - fit["center"]) / fit["scale"], -8, 8)
    return fit["target_center"] + fit["target_scale"] * (fit["bias"] + z @ fit["coef"])


def with_anchor(mode, model, centered, anchor):
    if mode == "event_median":
        return np.full(len(anchor), model["event_median"])
    if mode == "persistence":
        return anchor
    if mode == "median_innovation":
        return anchor + model["median_innovation"]
    return anchor + regression(model["fits"][mode], as_features(mode, centered))


def read_model(path):
    model = json.loads(Path(path).read_bytes())
    if model["format"] != 1 or tuple(model["channels"]) != CHANNELS:
        raise ValueError("Incompatible cervical voltage model.")
    return model


def predict(record, model):
    mode = record.get("mode")
    if not isinstance(mode, str) or mode not in INPUTS:
        raise ValueError("Choose a supported cervical forecast method.")
    if set(record) != {"domain", "mode", "readings_uV"} or record["domain"] != "cervical_voltage":
        raise ValueError("Supply the cervical_voltage domain, a mode and its required readings_uV.")
    measurements = record["readings_uV"]
    if not isinstance(measurements, dict) or set(measurements) != set(INPUTS[mode]):
        raise ValueError("Required electrode names for this method: " + ", ".join(INPUTS[mode]))
    bins = np.zeros((1, 8, len(CHANNELS)))
    for name, column in measurements.items():
        if (not isinstance(column, list) or len(column) != 8
            or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in column)):
            raise ValueError("Each electrode needs eight numbers: five before the event and three after it.")
        try:
            a = np.asarray(column, dtype=np.float64)
        except OverflowError as e:
            raise ValueError("Voltage exceeds the numerical range.") from e
        if not np.isfinite(a).all():
            raise ValueError("Each electrode needs eight finite readings in microvolts.")
        bins[0, :, CHANNELS.index(name)] = a
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        z = center(bins)
        if not np.isfinite(z).all():
            raise ValueError("Centered voltage exceeds the numerical range.")
        value = float(with_anchor(mode, model, z, z[:, -1, 1])[0])
    if not np.isfinite(value):
        raise ValueError("Forecast exceeds the numerical range.")
    return {"domain": "cervical_voltage", "mode": mode, "electrode": "SC6",
            "reference": "TH6", "window_ms": [12, 14], "baseline_ms": [-15, -10],
            "mean_change_uV": value}
