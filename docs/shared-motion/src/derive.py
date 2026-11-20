"""Reconstruct the approved public inputs from the released study. Requires NumPy."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def read_json(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=REPO/"models/shared-motion")
    parser.add_argument("--rat", type=Path, default=REPO/"benchmarks/wtrack-neural-motion/recording/pairs/train/trial-055.npz")
    parser.add_argument("--out", type=Path, default=HERE/"inputs.json")
    parser.add_argument("--oracle", type=Path, help="Write exact reference outputs for the two public examples")
    args = parser.parse_args()
    model = args.study / "shared-motion-model"
    data = args.study / "shared-motion-data"
    sys.path[:0] = [str(data), str(model)]
    from prepare import future, history, load
    from features import history_tokens
    from methods import ridge_predictions
    from predict import forecast, physical_features

    seal = read_json(model/"fit-seal.json")
    scores = read_json(model/"summary.json")
    source = read_json(data/"demo-scope.json")
    assert digest(data/"contract.json") == source["data_contract_sha256"]
    permit = source["permitted_illustration"]
    record = next(r for r in read_json(data/"contract.json")["records"] if r["domain"]=="rat" and r["role"]=="train")
    assert record["recording"] == "trial-055" and permit["split"] == "train" and permit["trial"] == 55
    cutoff = permit["cutoff_trip_s"]
    assert cutoff == 2.0
    # The public repository retains the original, hash-checked trial at a new path.
    obs = load(dict(record, path=args.rat.name), args.rat.parent)
    past, reason = history(obs, cutoff)
    assert reason is None
    endpoint, reason = future(obs, past, cutoff)
    assert reason is None and cutoff + .30 <= obs.end - .25
    t = obs.native[past]
    rat = dict(intervals=history_tokens(obs.cm[past], t, cutoff).tolist(), cutoffS=cutoff,
               leadS=float(obs.native[endpoint] - t[-1]), measuredCm=float(np.linalg.norm(obs.cm[endpoint] - obs.cm[past[-1]])),
               lastObservationAgeS=float(cutoff - t[-1]))
    ref = read_json(model/"reference-examples.json")
    assert ref["domain"][0] == "wrist" and "invented" in ref["provenance"]
    wrist = dict(intervals=ref["x"][0], cutoffS=ref["cutoff_s"][0])
    examples = {"rat":rat, "wrist":wrist}

    weights = model/"shared-weights.npz"
    assert digest(weights) == scores["checkpoint_sha256"] == "9a3649cb8f2119984e7f9f0b96a07bdc95e1833c7068f0e9caef2680f22e3179"
    aggregate, ridge, oracle = {}, {}, {}
    methods = {"joint":"joint_27181", "recent":"recent", "still":"persistence", "ridge_log":"ridge_log",
               "ridge_cm":"ridge_cm", "solo32":"solo32_27181", "solo64":"solo64_27181"}
    for domain in ["wrist","rat"]:
        path = model/"fits"/f"ridge-{domain}.npz"
        assert digest(path) == seal["fits/"+path.name]
        with np.load(path,allow_pickle=False) as fit:
            ridge[domain] = dict(mu=fit["mu"].tolist(),sd=fit["sd"].tolist(),
                                 coef=fit["coef"][:,1].tolist(),intercept=float(fit["intercept"][1]))
            if args.oracle:
                raw = np.array([examples[domain]["intervals"]], dtype=np.float64)
                oracle[domain] = {"joint":float(forecast(raw,[domain],weights)[0]),
                                  "recent":float(physical_features(raw)[1][0]),
                                  "ridge":float(ridge_predictions(raw,fit)[1][0])}
        group = scores["domains"][domain]
        aggregate[domain] = {k:group["macro_mae_cm"][v] for k,v in methods.items()}
        paired = group["paired_joint_minus_comparator_cm"]
        aggregate[domain]["intervals"] = {k:paired[methods[k]]["percentile_95"] for k in ["solo32","solo64"]}
        aggregate[domain].update(groups=paired["recent"]["total_groups"], rows=group["rows"])
        assert group["transfer_gate"] is False
    assert scores["bidirectional_transfer_gate"] is False
    args.out.write_bytes((json.dumps(dict(examples=examples,aggregate=aggregate,ridge=ridge),
                                    indent=2,allow_nan=False)+"\n").encode())
    if args.oracle:
        assert abs(oracle["wrist"]["joint"]-ref["expected_cm"][0]) < 1e-12
        args.oracle.write_bytes((json.dumps(oracle,indent=2)+"\n").encode())
    print(args.out, digest(args.out))


if __name__ == "__main__":
    main()
