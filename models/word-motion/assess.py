"""Evaluate the locked models on the fixed, independent catalogue subject groups."""

import argparse
import json
from pathlib import Path

import numpy as np
from acquire import digest, manifest
from generate import predict

ACTIONS = ["walk", "run"]


def metrics(y, pred):
    difference = pred - y
    site_errors = np.linalg.norm(difference[:, :54].reshape(25, 18, 3), axis=2)
    actual_speed, predicted_speed = [
        np.linalg.norm(np.diff(a[:, :54].reshape(25, 18, 3), axis=0), axis=2).mean()
        * 40
        for a in (y, pred)
    ]
    return {
        "bodyMm": float(site_errors.mean()),
        "pelvisPathMm": float(np.linalg.norm(difference[:, -3:], axis=1).mean()),
        "signedForwardEndMm": float(difference[-1, -2]),
        "absForwardEndMm": float(abs(difference[-1, -2])),
        "absoluteMeanBodySpeedDifferenceMmS": float(
            abs(actual_speed - predicted_speed)
        ),
    }


def average(rows):
    return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}


def aggregate(records):
    subjects = sorted({r["subject"] for r in records})
    by_subject = {
        s: average([r["errors"] for r in records if r["subject"] == s])
        for s in subjects
    }
    return {"bySubject": by_subject, "equalSubject": average(list(by_subject.values()))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local", type=Path, required=True)
    args = p.parse_args()
    d = args.local
    fit = d / "fit"
    for name, sha in json.loads((fit / "lock.json").read_text()).items():
        if digest((fit / name).read_bytes()) != sha:
            raise ValueError("Fit artifact changed: " + name)
    rows = {r["id"]: r for r in manifest()["clips"] if r["split"] == "assessment"}
    ys = np.load(d / "assessment" / "targets.npz")
    ids = ys["ids"].tolist()
    models = {
        n: json.loads((fit / (n + ".json")).read_text())
        for n in ["conditional", "constant", "shuffled"]
    }
    means = np.load(fit / "means.npz")
    records = []
    for uid, y in zip(ids, ys["y"], strict=True):
        action = rows[uid]["action"]
        predictions = {
            n: predict("walk" if n == "constant" else action, m)
            for n, m in models.items()
        }
        predictions.update(
            {
                "classMean": means["byAction"][ACTIONS.index(action)],
                "globalMean": means["globalMean"],
            }
        )
        for name, pred in predictions.items():
            records.append(
                {
                    "id": uid,
                    "subject": rows[uid]["subject"],
                    "action": action,
                    "method": name,
                    "errors": metrics(y, pred),
                }
            )
    by_method = {}
    for method in sorted({r["method"] for r in records}):
        same = [r for r in records if r["method"] == method]
        by_method[method] = {
            **aggregate(same),
            "byActionEqualSubjects": {
                a: aggregate([r for r in same if r["action"] == a])["equalSubject"]
                for a in ACTIONS
                if any(r["action"] == a for r in same)
            },
        }
    primary = {n: r["equalSubject"]["bodyMm"] for n, r in by_method.items()}
    passed = all(
        primary["conditional"] < primary[n]
        for n in ["constant", "shuffled", "classMean"]
    )
    results = {
        "unitOfGrouping": "CMU catalogue subject ID",
        "primaryPass": passed,
        "dataCounts": {
            "trials": len(ids),
            "groups": len({rows[u]["subject"] for u in ids}),
        },
        "byMethod": by_method,
        "trials": records,
    }
    (d / "results.json").write_text(
        json.dumps(results, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps({"primaryEqualSubjectMm": primary, "primaryPass": passed}))


if __name__ == "__main__":
    main()
