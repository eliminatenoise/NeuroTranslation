"""Replay ten motion forecasts from the preceding twenty 10-ms recording bins."""
from pathlib import Path
import numpy as np
from frozen_forecast import forward_standardized, load_model

SEEDS = (17, 41, 73)
CONTACTS = np.array([2,4,6,10,12,13,15,16,18,19,20,21,23,28,33,35,36,37,39,44,
                     46,47,49,53,55,56,58,59,64,72,74,84,87,88,89,94,95])
WEIGHTS = Path(__file__).resolve().parent / "weights"


def pooled_history(all_history, all_guide):
    """Sum local exports once, regardless of their local positive sort numbers."""
    counts = np.asarray(all_history, dtype=np.float64)
    guide = np.asarray(all_guide)
    if (counts.ndim != 3 or counts.shape[1] != 20 or guide.shape != (counts.shape[2], 2)
        or len(np.unique(guide, axis=0)) != len(guide) or np.any(guide[:, 1] < 0)):
        raise ValueError("Invalid recording-local guide or history shape")
    bins = []
    for channel in CONTACTS:
        entries = guide[:,0] == channel
        if not np.any(guide[entries,1] == 0):
            raise ValueError(f"Missing common sort-0 contact {channel}")
        values = counts[:,:,entries]
        valid = np.isfinite(values) & (values >= 0) & (values == np.floor(values))
        pooled = np.where(valid, values, np.nan).sum(axis=2)
        bins.append(pooled.reshape(-1,4,5).sum(axis=2))
    return np.stack(bins, axis=2)


def body_tokens(pose, cue, model):
    if str(model["arm"]) != "pose_cue" or str(model["family"]) != "transformer":
        raise ValueError("The body-only path requires frozen pose/cue Transformer weights")
    pose, cue = np.asarray(pose), np.asarray(cue)
    if pose.shape[1:] != (20,8) or cue.shape != (len(pose),20,3):
        raise ValueError("Expected 20 past pose and cue bins")
    raw_body = np.concatenate((pose, np.diff(pose, axis=1, prepend=pose[:,:1])), axis=2)
    x = np.zeros((len(pose),20,42), dtype=np.float64)
    x[:,:,:16] = (raw_body - model["x_mean"][:16]) / model["x_scale"][:16]
    x[:,:,39:] = (cue - model["x_mean"][39:]) / model["x_scale"][39:]
    return x


def body_forecast(pose, cue, base):
    x = body_tokens(pose, cue, base)
    out = np.full((len(x),10,8), np.nan)
    ids = np.flatnonzero(np.isfinite(x).all(axis=(1,2)))
    for start in range(0, len(ids), 64):
        ix = ids[start:start+64]
        out[ix] = forward_standardized(x[ix],base).reshape(-1,10,8)*base["y_scale"]+base["y_mean"]
    return out


def body_features(pose, cue):
    return np.column_stack((pose[:,-1], np.diff(pose,axis=1).reshape(len(pose),-1),
                            cue[:,4::5].reshape(len(cue),-1)))


def design(pose, cue, pooled, cfg, arm):
    a = ((body_features(pose,cue)-cfg["body_mean"])/cfg["body_scale"]) @ cfg["body_projection"]
    if arm == "full":
        c = np.log1p(pooled.reshape(len(pose),148))
        a += ((c-cfg["count_mean"])/cfg["count_scale"]) @ cfg["count_projection"]
    elif arm != "pose":
        raise ValueError("Expected full or pose adapter")
    return a


def residual(x, weights, family):
    if family == "ridge":
        return x @ weights["ridge_weight"] + weights["ridge_bias"]
    if family != "mlp":
        raise ValueError("Unknown residual family")
    hidden = np.tanh(x @ weights["in_weight"].T + weights["in_bias"])
    return hidden @ weights["out_weight"].T + weights["out_bias"]


def predict_seed(pose, cue, pooled, base, cfg, weights, arm, family="mlp"):
    """Inputs never include the forecast target, workspace, future cues or trial IDs."""
    x = design(pose, cue, pooled, cfg, arm)
    return body_forecast(pose,cue,base) + residual(x,weights,family).reshape(-1,10,8)*base["y_scale"]


def load_arrays(path):
    with np.load(path,allow_pickle=False) as f:
        return dict(f)


def predict(pose, cue, pooled, arm="full", family="mlp", weights_dir=WEIGHTS):
    cfg = load_arrays(weights_dir/"features.npz")
    if not np.array_equal(cfg["contacts"],CONTACTS):
        raise ValueError("Contact order does not match the registered model")
    forecasts = []
    for seed in SEEDS:
        base = load_model(weights_dir/f"pose_cue-{seed}.npz")
        adapter = load_arrays(weights_dir/f"adapter-{arm}-{seed}.npz")
        forecasts.append(predict_seed(pose,cue,pooled,base,cfg,adapter,arm,family))
    return np.mean(forecasts,axis=0)
