"""Export the fitted conditional model and two clearly identified training references."""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from acquire import HERE, digest, manifest
from generate import output_packet, predict


def save(path, value):
    path.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    d, out = args.local, args.out
    out.mkdir(parents=True, exist_ok=True)
    source = d / "fit" / "conditional.json"
    if (
        digest(source.read_bytes())
        != json.loads((source.parent / "lock.json").read_text())[source.name]
    ):
        raise ValueError("Conditional fit differs from lock")
    shutil.copyfile(source, out / "weights.json")
    w = json.loads(source.read_text())
    train = np.load(d / "train" / "targets.npz")
    rows = {r["id"]: r for r in manifest()["clips"] if r["split"] == "train"}
    meta = {r["id"]: r for r in json.loads((d / "train" / "geometry.json").read_text())}
    receipts = {
        r["id"]: r for r in json.loads((d / "train" / "acquisition.json").read_text())
    }
    for action in w["tokens"]:
        pred = predict(action, w)
        packet = output_packet(action, pred)
        packet.update({"kind": "generated", "modelSha256": digest(source.read_bytes())})
        save(out / (action + ".json"), packet)
        idx = next(
            i for i, uid in enumerate(train["ids"]) if rows[uid]["action"] == action
        )
        uid = str(train["ids"][idx])
        packet = output_packet(action, train["y"][idx])
        packet.update(
            {
                "kind": "measured-training-reference",
                "trialId": uid,
                "sourceLabel": rows[uid]["sourceLabel"],
                "sourceUrl": rows[uid]["url"],
                "catalogueUrl": rows[uid]["catalogueUrl"],
                "sourceSha256": receipts[uid]["sha256"],
                "sourceFrames": meta[uid]["sampledSourceFrames"],
                "sourceRateHz": 120,
                "sourceTerms": "CMU Graphics Lab; direct resale of data, including converted data, prohibited.",
                "sourceTermsUrl": "https://mocap.cs.cmu.edu/",
            }
        )
        save(out / ("reference-" + action + ".json"), packet)
    if (HERE / "schema.json").resolve() != (out / "schema.json").resolve():
        shutil.copyfile(HERE / "schema.json", out / "schema.json")


if __name__ == "__main__":
    main()
