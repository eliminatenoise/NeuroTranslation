"""Use past observations to forecast hand, elbow and handle displacement."""
import argparse
import json
from pathlib import Path
import numpy as np

ARMS = ("full", "pose_cue", "spike_cue", "spikes_only", "cue_only")
SEEDS = (17, 41, 73)
GROUPS = {"pose": slice(0, 16), "spike": slice(16, 39), "cue": slice(39, 42)}
MODALITIES = {
    "full": ("pose", "spike", "cue"),
    "pose_cue": ("pose", "cue"),
    "spike_cue": ("spike", "cue"),
    "spikes_only": ("spike",),
    "cue_only": ("cue",),
}


def history_tokens(pose, spikes, cue):
    """Batch of complete measurements in native units, oldest first."""
    pose, spikes, cue = (np.asarray(x, dtype=np.float64) for x in (pose, spikes, cue))
    n = len(pose)
    if [x.shape for x in (pose, spikes, cue)] != [(n, 20, 8), (n, 20, 23), (n, 20, 3)]:
        raise ValueError("Expected 20 known bins of 8 positions, 23 sorted counts and 3 elapsed-cue fields")
    if not all(np.isfinite(x).all() for x in (pose, spikes, cue)):
        raise ValueError("A complete finite history is required")
    if np.any(spikes < 0) or not np.array_equal(spikes, np.rint(spikes)):
        raise ValueError("Expected nonnegative integer spike counts")
    increments = np.diff(pose, axis=1, prepend=pose[:, :1])
    return np.concatenate((pose, increments, np.sqrt(spikes), cue), axis=2)


def load_model(path):
    with np.load(path, allow_pickle=False) as f:
        model = dict(f)
    if str(model["schema"]) != "chowdhury-motor-v1":
        raise ValueError("Unrecognized motor weight format")
    return model


def standardized(raw, model):
    scaled = (raw - model["x_mean"]) / model["x_scale"]
    keep = MODALITIES[str(model["arm"])]
    for name, columns in GROUPS.items():
        if name not in keep:
            scaled[:, :, columns] = 0
    return scaled


def forward_standardized(x, p):
    if str(p["family"]) == "ridge":
        return x.reshape(len(x), 840) @ p["coef"] + p["bias"]

    def dense(a, key):
        return a @ p[key + ".weight"].T + p[key + ".bias"]

    def norm(a, key):
        centered = a - a.mean(-1, keepdims=True)
        return (centered / np.sqrt(np.mean(centered**2, axis=-1, keepdims=True) + 1e-5)
                * p[key + ".weight"] + p[key + ".bias"])

    x = dense(x, "embed") + p["position"]
    q, k, v = [t.reshape(-1, 20, 3, 8).transpose(0, 2, 1, 3)
               for t in np.split(dense(x, "qkv"), 3, axis=-1)]
    logits = (q @ k.swapaxes(-1, -2)) / np.sqrt(8)
    attention = np.exp(logits - logits.max(-1, keepdims=True))
    attention /= attention.sum(-1, keepdims=True)
    attended = (attention @ v).transpose(0, 2, 1, 3).reshape(-1, 20, 24)
    x = norm(x + dense(attended, "project"), "attention_norm")
    x = norm(x + dense(np.maximum(dense(x, "expand"), 0), "reduce"), "final_norm")
    return dense(x[:, -1], "out")


def predict(raw, model, unit_guide):
    if not np.array_equal(unit_guide, model["unit_guide"]):
        raise ValueError("Channel / sort identities differ from the fitted recording")
    pieces = []
    for start in range(0, len(raw), 96):
        normalized = forward_standardized(standardized(raw[start:start + 96], model), model)
        pieces.append(normalized.reshape(-1, 10, 8) * model["y_scale"] + model["y_mean"])
    return np.concatenate(pieces) if pieces else np.empty((0, 10, 8))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    cli.add_argument("record", type=Path, nargs="?", default=here / "recorded-example.json")
    cli.add_argument("--weights", type=Path, default=here / "weights" / "full-17.npz")
    args = cli.parse_args()
    record = json.loads(args.record.read_text())
    tokens = history_tokens(*[[record[key]] for key in ("pose", "spikes", "cue")])
    pred = predict(tokens, load_model(args.weights), record["unit_guide"])
    print(json.dumps({"displacement_hand_xyz_m_elbow_xyz_m_handle_xy_cm": pred[0].tolist()}))
