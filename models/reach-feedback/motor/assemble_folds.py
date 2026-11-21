"""Assemble early-piece forecasts and seal the all-original model without a held read."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "source/train.npz"
KEYS = ("original", "block", "ordinal", "k", "fold")
SEEDS = [17, 41, 73]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def store(path, data):
    tmp = path.with_suffix(".tmp")
    with tmp.open("xb") as f:
        np.savez_compressed(f, **data)
    if path.exists():
        raise FileExistsError(path)
    tmp.rename(path)


def write(path, obj):
    with path.open("x") as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")


def assemble_oof():
    with np.load(SOURCE, allow_pickle=False) as f:
        out = {k: f[k] for k in KEYS}
    n = len(out["k"])
    out.update(seeds=np.array(SEEDS), full=np.full((3, n, 10, 8), np.nan),
               ridge_full=np.full((n, 10, 8), np.nan), supported=out["fold"] > 0)
    folds = []
    for target in range(1, 5):
        folder = HERE / "folds" / f"fold-{target}"
        fit = json.loads((folder / "fit.json").read_text())
        train = out["fold"] < target
        ids = out["fold"] == target
        pairs = np.column_stack([out["block"], out["original"]])
        if fit["train_originals"] != np.unique(pairs[train], axis=0).tolist() or fit["prediction_originals"] != np.unique(pairs[ids], axis=0).tolist():
            raise ValueError("Fold original identity mismatch")
        if set(map(tuple, pairs[train])) & set(map(tuple, pairs[ids])):
            raise ValueError("Training and receiving fold overlap")
        with np.load(folder / "predictions.npz", allow_pickle=False) as z:
            if not all(np.array_equal(out[k][ids], z[k]) for k in KEYS) or z["seeds"].tolist() != SEEDS:
                raise ValueError("Fold forecast identity mismatch")
            out["full"][:, ids] = z["full"]
            out["ridge_full"][ids] = z["ridge_full"]
        folds.append(dict(target=target, train_originals=len(fit["train_originals"]),
                          prediction_originals=len(fit["prediction_originals"]),
                          train_rows=fit["train_rows"], prediction_rows=fit["predict_rows"],
                          fit_sha256=digest(folder / "fit.json"), prediction_sha256=digest(folder / "predictions.npz")))
    good = out["supported"]
    if (not np.isfinite(out["full"][:, good]).all() or not np.isfinite(out["ridge_full"][good]).all()
            or not np.isnan(out["full"][:, ~good]).all() or not np.isnan(out["ridge_full"][~good]).all()):
        raise ValueError("Invalid OOF supported rows")
    path = HERE / "oof.npz"
    store(path, out)
    write(HERE / "folds/oof.json", dict(sha256=digest(path), source_sha256=digest(SOURCE),
                                          rows=n, supported=int(good.sum()), folds=folds))


def assemble_refit():
    folder = HERE / "folds/fold-5"
    product = HERE / "product"
    weights = product / "weights"
    weights.mkdir(exist_ok=True)
    fit = json.loads((folder / "fit.json").read_text())
    if len(fit["fits"]) != 20 or len(fit["train_originals"]) != 198:
        raise ValueError("Incomplete all-original refits")
    for name, derivation in fit["fits"].items():
        source = folder / name
        if digest(source) != derivation["sha256"]:
            raise ValueError("Weight hash mismatch")
        shutil.copyfile(source, weights / name)
    shutil.copyfile(folder / "predictions.npz", HERE / "train-predictions.npz")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("oof", "refit"))
    stage = parser.parse_args().stage
    (assemble_oof if stage == "oof" else assemble_refit)()
