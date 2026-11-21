"""NumPy inference for delayed cortical counts. Inputs retain native source units."""
import numpy as np

SEEDS = (17, 41, 73)
ARMS = {
    "direct": ("pose", "spikes", "cue"),
    "full": ("pose", "spikes", "cue", "movement"),
    "predicted_only": ("movement",),
    "spikes_only": ("spikes",),
    "cue_only": ("cue",),
    "pose_cue": ("pose", "cue"),
    "privileged": ("pose", "spikes", "cue", "movement"),
}
SHAPES = {"pose": (20, 8), "spikes": (20, 23), "cue": (20, 3), "movement": (10, 8)}


def original_weights(original):
    _, inverse, sizes = np.unique(original, return_inverse=True, return_counts=True)
    return 1.0 / sizes[inverse]


def samples(inputs, name):
    values = np.asarray(inputs[name], dtype=np.float64)
    if values.ndim != 3 or values.shape[1:] != SHAPES[name] or not np.isfinite(values).all():
        raise ValueError(f"Invalid {name} samples, expected [windows, {SHAPES[name]}]")
    if name == "spikes" and ((values < 0).any() or (values != np.floor(values)).any()):
        raise ValueError("Expected nonnegative observed spike counts")
    if name == "pose":
        return np.concatenate((values, values - values[:, -1:]), axis=-1)
    return values


def normalizers(arm, inputs, weight):
    result = {"arm": np.array(arm)}
    for key in ARMS[arm]:
        x = samples(inputs, key)
        mean = np.average(x.mean(axis=1), axis=0, weights=weight)
        var = np.average(((x - mean)**2).mean(axis=1), axis=0, weights=weight)
        scale = np.sqrt(var)
        result[key + "_mean"] = mean
        result[key + "_scale"] = np.where(scale > 1e-10, scale, 1.)
    return result


def patches(weights, inputs, dtype=np.float32):
    arm = str(weights["arm"])
    n = len(inputs[ARMS[arm][0]])
    arrays = []
    for group, shape in SHAPES.items():
        if group in ARMS[arm]:
            x = samples(inputs, group)
            if len(x) != n:
                raise ValueError("Input row counts differ")
            arrays.append(((x - weights[group + "_mean"]) / weights[group + "_scale"]).astype(dtype))
        else:
            width = 16 if group == "pose" else shape[1]
            arrays.append(np.zeros((n, shape[0], width), dtype=dtype))
    history = np.concatenate(arrays[:3], axis=2).reshape(n, 4, 5 * 42)
    future = arrays[3].reshape(n, 2, 5 * 8)
    return history, future


def glm_features(history, future):
    cols = []
    for x, width in ((history, 42), (future, 8)):
        x = x.reshape(len(x), -1, 5, width)
        cols.extend([x.mean(axis=2).reshape(len(x), -1),
                     np.einsum("btfc,f->btc", x, np.array([-.8, -.4, 0., .4, .8])).reshape(len(x), -1)])
    return np.column_stack(cols)


def linear(x, weights, key):
    return x @ weights[key + ".weight"].T + weights[key + ".bias"]


def layer_norm(x, weights, key):
    center = x - x.mean(axis=-1, keepdims=True)
    scaled = center / np.sqrt((center**2).mean(axis=-1, keepdims=True) + 1e-5)
    return scaled * weights[key + ".weight"] + weights[key + ".bias"]


def transformer(weights, history, future):
    n = len(history)
    p = weights["position"]
    x = np.concatenate((np.zeros((n, 1, 16), np.float32), linear(history, weights, "hist"),
                        linear(future, weights, "path")), axis=1) + p
    qkv = linear(layer_norm(x, weights, "norm1"), weights, "qkv")
    q, k, v = qkv.reshape(n, 7, 3, 2, 8).transpose(2, 0, 3, 1, 4)
    logits = (q @ k.swapaxes(-2, -1)) * (8 ** -.5)
    probs = np.exp(logits - logits.max(axis=-1, keepdims=True))
    probs /= probs.sum(axis=-1, keepdims=True)
    z = (probs @ v).transpose(0, 2, 1, 3).reshape(n, 7, 16)
    x = x + linear(z, weights, "project")
    z = np.maximum(linear(layer_norm(x, weights, "norm2"), weights, "ff1"), 0)
    x = x + linear(z, weights, "ff2")
    logits = linear(layer_norm(x[:, 0], weights, "read_norm"), weights, "read")
    return (np.logaddexp(logits, np.float32(0.)) + 1e-6).reshape(n, 10, 23)


def predict(weights, **inputs):
    """Pass an open np.load weight file and the inputs needed for its arm. For
    full/predicted_only supply its paired motor forecast as movement. Only
    privileged accepts subsequent *measured* displacement. One call = one seed.
    """
    if str(weights["family"]) == "transformer":
        return transformer(weights, *patches(weights, inputs))
    if str(weights["family"]) != "glm":
        raise ValueError("Unknown model family")
    x = glm_features(*patches(weights, inputs, np.float64))
    rate = np.exp(x @ weights["coefficient"] + weights["intercept"])
    return rate.reshape(len(x), 10, 23)


def simple_rates(weights, spikes, ordinal):
    ordinal = np.asarray(ordinal)
    n = len(ordinal)
    mean = np.broadcast_to(weights["train_mean"], (n, 10, 23)).copy()
    by_go = mean.copy()
    for i, go in enumerate(weights["ordinals"]):
        by_go[ordinal == go] = weights["ordinal_rates"][i]
    past = samples({"spikes": spikes}, "spikes")
    persistence = np.repeat(past[:, -10:].mean(axis=1, keepdims=True), 10, axis=1)
    return {"train_mean": mean, "ordinal_mean": by_go, "persistence": persistence}
