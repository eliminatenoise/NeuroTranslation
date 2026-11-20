"""Check the public Node reader against the released Python adapter, without saving histories."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
FROZEN = "7a0c17c66049fba7812d0acf1392af21829c3c6528ace3667202c8091f97f8b4"
MODES = ("mean", "ridge", "shared", "scrambled", "trained")

def node(record):
    return subprocess.run(["node", HERE / "predict.cjs", "-"], input=json.dumps(record),
                          capture_output=True, text=True)

def held_examples(archive):
    import h5py
    from load import knee_moment_source as source

    source.verify_archive(archive)
    rows = []
    with h5py.File(archive) as f:
        for person in ("AB08", "AB09", "AB10"):
            trial = source.load_trial(f, person, include_moments=True)
            cuts = [k for k in range(399, len(trial.angles)-25, 5)
                    if source.valid_history(trial.angles[k-399:k+1]) and source.future_moment(trial, k) is not None]
            for k in (cuts[0], cuts[len(cuts)//2], cuts[-1]):
                last = trial.first_source_frame + k
                rows.append((list(range(last-399, last+1)), trial.angles[k-399:k+1].tolist()))
    return rows

def main(args):
    sys.path.insert(0, str(args.model.resolve()))
    from predict import predict_record

    if hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() != FROZEN:
        raise ValueError("Use the released knee moment checkpoint.")
    demo = json.loads(subprocess.check_output(["node", HERE / "predict.cjs", "--example-input"], text=True))
    rows = [(demo["frames"], demo["angles_deg"]),
            (list(range(400)), [[1, 1, 5, 5, -2, -2] for _ in range(400)])]
    if args.archive:
        rows.extend(held_examples(args.archive))
    largest = 0.
    for mode in MODES:
        batch = dict(domain="knee_moment", mode=mode, frames=[r[0] for r in rows], angles_deg=[r[1] for r in rows])
        native = predict_record(batch, args.checkpoint)
        response = node(batch)
        if response.returncode:
            raise RuntimeError(response.stderr)
        js = json.loads(response.stdout)
        key = "internal_knee_moment_Nm_per_kg"
        actual, expected = np.asarray(js.pop(key)), np.asarray(native.pop(key))
        assert np.max(np.abs(actual-expected)) < 1e-9
        assert js == native and js["period_frames"][1] == 75
        largest = max(largest, float(np.max(np.abs(actual-expected))))
        single = json.loads(node(demo | dict(mode=mode)).stdout)
        assert np.array_equal(single[key][0], actual[0]) and single["period_frames"] == js["period_frames"][:1]
    rejected = []
    for kind in ("gap", "fractional_frame", "zero_angle", "boolean_angle", "future_moment", "shape", "mode", "overflow"):
        record = copy.deepcopy(demo)
        if kind == "gap": record["frames"][99] += 1
        elif kind == "fractional_frame": record["frames"][0] += .5
        elif kind == "zero_angle": record["angles_deg"][0][0] = 0
        elif kind == "boolean_angle": record["angles_deg"][34][3] = True
        elif kind == "future_moment": record["future_moment"] = 3
        elif kind == "shape": record["angles_deg"][5].pop()
        elif kind == "mode": record["mode"] = "unknown"
        elif kind == "overflow": record["angles_deg"][-1][0] = 1e300
        try: predict_record(record, args.checkpoint)
        except (ValueError, TypeError, KeyError): pass
        else: raise AssertionError(f"Python accepted {kind}")
        assert node(record).returncode != 0, f"Node accepted {kind}"
        rejected.append(kind)
    print(json.dumps(dict(modes=len(MODES), invented_histories=2, held_histories=len(rows)-2,
                          maximum_absolute_difference=largest, rejected=rejected), indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--archive", type=Path)
    main(parser.parse_args())
