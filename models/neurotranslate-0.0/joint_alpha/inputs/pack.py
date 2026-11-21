"""Pack private, source-verified replay measurements for a shared offline predictor; original adapter code CC0."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked(path, expected):
    if digest(path) != expected:
        raise ValueError(f"Input checksum differs: {path.name}")


def schema(kind, channels, units, outputs, out_units, steps, **details):
    assert len(set(channels)) == len(channels) == len(units)
    assert len(set(outputs)) == len(outputs) == len(out_units)
    return dict(
        kind=kind,
        channels=channels,
        input_units=units,
        outputs=outputs,
        output_units=out_units,
        history_steps=steps,
        **details,
    )


def save(root, task, split, spec, *, X, y, group, baseline, **meta):
    root.mkdir(parents=True, exist_ok=True)
    store = root / "private" / split
    store.mkdir(parents=True, exist_ok=True)
    os.chmod(root / "private", 0o700)
    fname = store / (task + ".npz")
    X = np.asarray(X, dtype="<f4")
    rank = spec["kind"] == "categorical"
    y = np.asarray(y, dtype="<i4" if rank else "<f4")
    baseline = np.asarray(baseline, dtype="<f4")
    group = np.asarray(group)
    if not (
        X.ndim == (4 if rank else 3)
        and X.shape[-2:] == (spec["history_steps"], len(spec["channels"]))
        and len(X) == len(y) == len(baseline) == len(group)
        and len(X) > 0
    ):
        raise ValueError("Inconsistent record geometry")
    if rank:
        assert y.shape == (len(X),) and baseline.shape == X.shape[:2]
        assert np.logical_and(y >= 0, y < X.shape[1]).all()
    else:
        assert y.shape == baseline.shape == (len(X), len(spec["outputs"]))
    keep = np.isfinite(X).reshape(len(X), -1).any(1) & np.isfinite(y).reshape(
        len(y), -1
    ).any(1)
    arrays = dict(X=X, y=y, group=group, baseline=baseline, **meta)
    if any(len(v) != len(X) for v in arrays.values()):
        raise ValueError("Row metadata length")
    with fname.with_suffix(".tmp").open("wb") as f:
        np.savez_compressed(f, **{k: np.asarray(v)[keep] for k, v in arrays.items()})
    fname.with_suffix(".tmp").replace(fname)
    index = root / "manifest.json"
    record = (
        json.loads(index.read_text()) if index.exists() else {"format": 1, "tasks": {}}
    )
    entry = record["tasks"].setdefault(task, dict(spec, splits={}, support={}))
    if {k: v for k, v in entry.items() if k not in ("splits", "support")} != spec:
        raise ValueError("Task definitions must agree across splits")
    entry["splits"][split] = str(fname.relative_to(root))
    entry["support"][split] = {
        "rows": int(keep.sum()),
        "exclusions_all_missing": int((~keep).sum()),
        "groups": len(np.unique(group[keep])),
        "sha256": digest(fname),
    }
    index.with_suffix(".tmp").write_text(
        json.dumps(record, indent=2, allow_nan=False) + "\n"
    )
    index.with_suffix(".tmp").replace(index)
    print(
        f"{task} {split}: {keep.sum()} rows, {entry['support'][split]['groups']} groups",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", choices=["human", "macaque", "rat", "calcium", "landmark"]
    )
    parser.add_argument("stage", choices=["train", "held"])
    parser.add_argument(
        "--inputs",
        type=Path,
        required=True,
        help="Directory containing upstream files for the selected assay",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.source in ("human", "macaque"):
        from paired import human, macaque

        fn = {"human": human, "macaque": macaque}[args.source]
    else:
        from importlib import import_module

        module = {"rat": "rat", "calcium": "calcium", "landmark": "landmarks"}[
            args.source
        ]
        fn = getattr(import_module(module), args.source)
    fn(args.inputs, args.stage, args.out)


if __name__ == "__main__":
    main()
