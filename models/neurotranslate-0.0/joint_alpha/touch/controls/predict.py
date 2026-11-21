"""NumPy-only count forecasts. X contains 10 earlier 20 ms bins in chronological order."""
import numpy as np


MODELS = ("training_rate", "phase_and_spikes", "with_true_force", "with_previous_repeat_force")


def features(X, previous_repeat_force):
    """Design matrices for three independently fitted Poisson regressions."""
    x = np.asarray(X)
    donor = np.asarray(previous_repeat_force)
    if x.ndim != 3 or x.shape[1:] != (10, 5) or donor.shape != (*x.shape[:2], 3):
        raise ValueError("Expected X [N,10,5] and previous_repeat_force [N,10,3]")
    if not np.isfinite(x).all() or not np.isfinite(donor).all():
        raise ValueError("Nonfinite input outside registered common support")
    elapsed = x[:, -1, 4].astype(np.float64)
    centres = np.linspace(0, 6.9, 10)
    phase = np.exp(-0.5 * ((elapsed[:, None] - centres) / (centres[1] - centres[0])) ** 2)
    history = x[:, :, 3].astype(np.float64)
    common = np.column_stack((phase, history[:, -1], history[:, -3:].sum(1), history.sum(1)))
    designs = {MODELS[1]: common}
    for name, source in ((MODELS[2], x[:, :, :3]), (MODELS[3], donor)):
        recent = source[:, -1, :].astype(np.float64)
        change = recent - source[:, -2, :].astype(np.float64)
        designs[name] = np.column_stack((common, recent, change))
    return designs


def predict_all(X, previous_repeat_force, bundle):
    """Return expected spikes per future 20 ms per row, keyed by model name."""
    if bundle["format"] != 1 or set(bundle["models"]) != set(MODELS):
        raise ValueError("Unsupported predictor bundle")
    designs = features(X, previous_repeat_force)
    values = {MODELS[0]: np.full(len(X), bundle["models"][MODELS[0]]["mean_spikes_per_bin"], dtype=np.float64)}
    for name, design in designs.items():
        model = bundle["models"][name]
        standardized = (design - model["mean"]) / model["scale"]
        values[name] = np.exp(standardized @ np.asarray(model["slopes"]) + model["intercept"])
    if not all(np.isfinite(v).all() and (v > 0).all() for v in values.values()):
        raise ValueError("Nonpositive or nonfinite Poisson expectation")
    return values
