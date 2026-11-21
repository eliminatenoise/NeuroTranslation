"""Attach a frozen specialist's forecast to the exact historical cases; original adapter code CC0."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from pack import checked, digest


def human_forecast(a, w, arm):
    n = len(a["event"])
    x = []
    for name in ("scalp", "leg", "position", "physics"):
        arr = (a[name] - w[name + "_mean"]) / w[name + "_scale"]
        if name == "scalp":
            arr = np.where(a["present"][:, None, :, None], arr, 0).reshape(n, -1)
            arr = np.column_stack([arr, a["present"]])
        x.append(arr.reshape(n, -1))

    def layer(x, which):
        prefix = f"{arm}_431/{which}."
        return x @ w[prefix + "weight"].T + w[prefix + "bias"]

    z = np.stack(
        [np.tanh(layer(item, f"projections.{j}")) for j, item in enumerate(x)], axis=1
    )
    if arm == "early":
        mixing = (
            np.array([[1, 1, 1, 1], [1, -1, 1, -1], [1, 1, -1, -1], [1, -1, -1, 1]])
            * 0.5
        )
        z = np.einsum("ij,bjk->bik", mixing, z)
    states = []
    for branch, (i, j) in enumerate(((0, 1), (2, 3))):
        states.append(
            np.tanh(
                layer(
                    np.column_stack((z[:, i], z[:, j], z[:, i] * z[:, j])),
                    f"branches.{branch}",
                )
            )
        )
    joined = np.column_stack(
        [*states, states[0] * states[1], a["posture"], a["direction"]]
    )
    y = (
        layer(np.tanh(layer(joined, "join")), "head") * w["target_scale"]
        + w["target_mean"]
    )
    return np.maximum(0, np.expm1(y[:, :8])) if arm == "early" else y[:, 8:]


def add(out, task, split, pred, description, align):
    index = out / "manifest.json"
    manifest = json.loads(index.read_text())
    entry = manifest["tasks"][task]
    path = out / entry["splits"][split]
    with np.load(path, allow_pickle=False) as f:
        data = {k: f[k] for k in f.files}
    order = align(data)
    reference = pred[order].astype("<f4")
    assert reference.shape == data["y"].shape
    data["strong_reference"] = reference
    with path.with_suffix(".tmp").open("wb") as f:
        np.savez_compressed(f, **data)
    path.with_suffix(".tmp").replace(path)
    entry["support"][split].update(
        sha256=digest(path), strong_reference_description=description
    )
    index.with_suffix(".tmp").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    )
    index.with_suffix(".tmp").replace(index)


def with_human(inputs, model, out):
    from paired import HUMAN

    checked(inputs / "assessment.npz", HUMAN["test"][1])
    checked(model, "055f5263b2ad5b6b5fd3e9d9eb57764a91638ac6972f4e120f2841472aa9505f")
    with np.load(inputs / "assessment.npz", allow_pickle=False) as f:
        a = {k: f[k] for k in f.files}
    with np.load(model, allow_pickle=False) as f:
        weights = {k: f[k] for k in f.files}
    ix = {
        k: i
        for i, k in enumerate(zip(a["person"], a["posture"], a["event"], a["cutoff"]))
    }

    def align(d):
        return [ix[k] for k in zip(d["group"], d["posture"], d["event"], d["issue"])]

    for arm, task in [("early", "human_leg_emg"), ("paired", "human_sacrum_path")]:
        desc = f"Earlier balance study, frozen {arm} neural/muscle fusion, seed 431 (first of three published seeds). Same six historical people and original target. Prior study summarized errors over seeds."
        add(out, task, "test", human_forecast(a, weights, arm), desc, align)


def with_macaque(inputs, model, out):
    from paired import MACAQUE

    sys.path.insert(0, str(model))
    spec = importlib.util.spec_from_file_location("motor_replay", model / "replay.py")
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    reference = json.loads(Path(__file__).with_name("reference-files.json").read_text())
    for name, sha in reference.items():
        checked(model / name, sha)
    for part in ("test_block1", "test_block2"):
        name, sha = MACAQUE[part]
        checked(inputs / name, sha)
        with np.load(inputs / name, allow_pickle=False) as a:
            history = replay.pooled_history(a["all_history"], a["all_guide"])
            pred = replay.predict(
                a["pose"],
                a["cue"],
                history,
                arm="full",
                family="mlp",
                weights_dir=model / "weights",
            )
            pred = pred[:, -1] * np.array([1000.0] * 6 + [10.0] * 2)
            lookup = {
                k: i
                for i, k in enumerate(
                    zip(a["block"], a["original"], a["ordinal"], a["k"])
                )
            }

        def align(d, lookup=lookup):
            return [
                lookup[k]
                for k in zip(d["block"], d["original"], d["ordinal"], d["issue"])
            ]

        desc = "Earlier reach-feedback-week full movement residual MLP + frozen pose/cue Transformer, ensemble of its three published seeds 17,41,73. Same 100 ms displacement endpoint. This prior specialist additionally observes cue timing."
        add(out, "macaque_cortex_to_motion", part, pred, desc, align)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("assay", choices=("human", "macaque"))
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    {"human": with_human, "macaque": with_macaque}[args.assay](
        args.inputs, args.model, args.out
    )
