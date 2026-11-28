"""Time the released walking checkpoint on its invented two-plate example."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median
import sys
from time import perf_counter_ns


HERE = Path(__file__).resolve().parent
RELEASE = {
    "checkpoint.json": "43c91015e7fb6552766844c92c2b1bf7a007855ad7e8b065492b7c70a1221b97",
    "demo.py": "f999b768e7e84b5ecf02da4032841f5fc6f57887b76121fb479ecb9506cd6f2e",
    "example.json": "dfea4d6a2b194014212ab4e7753a8fea0f0d890a24bdb3de7015bcb23a3b5b71",
}
FIELDS = ("new_load_logit", "new_load_probability_uncalibrated", "signed_vertical_force_impulse_N_s")
DEPTHS = {"one": 1, "three": 3, "five": 5, "three_package_example": 3}
THREADS = [4, 8, 12, 16]


def require(ok, explanation):
    if not ok:
        raise ValueError(explanation)


def encode(output, *, sorted_keys=False):
    return json.dumps(output, sort_keys=sorted_keys, separators=(",", ":"), allow_nan=False).encode()


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def checked_directory(path):
    folder = path.expanduser().resolve()
    for name, expected in RELEASE.items():
        require(fingerprint((folder / name).read_bytes()) == expected, f"Unexpected release file: {name}")
    return folder


def numeric(output):
    return {name: output[name] for name in FIELDS}


def request(torch, demo, model, history, passes):
    with torch.inference_mode():
        raw = model(*demo.as_history(torch, history), passes=passes)
        scores = raw["new_load"].reshape(-1)
        return dict(zip(FIELDS, (scores.tolist(), scores.sigmoid().tolist(), raw["impulse"].reshape(-1).tolist())))


def summary(rows):
    ns = sorted(row["elapsed_ns"] for row in rows)
    return {
        "n": len(ns), "p50_ms": median(ns) / 1e6,
        "p95_ms": ns[math.ceil(0.95 * len(ns)) - 1] / 1e6,
        "min_ms": ns[0] / 1e6, "max_ms": ns[-1] / 1e6,
        "within_100_ms": sum(x <= 100_000_000 for x in ns),
        "exact_reference_matches": sum(row["exact_reference"] for row in rows),
    }


def grouped(rows):
    keys = dict.fromkeys(row["case"] for row in rows)
    return {key: summary([row for row in rows if row["case"] == key]) for key in keys}


def cases_in_block(cases, block, reverse_groups=False):
    i = block % len(cases)
    order = cases[i:] + cases[:i]
    if reverse_groups and block // len(cases) % 2:
        order.reverse()
    return order


def depth_trial(torch, demo, model, history):
    def packaged(passes):
        result = demo.forecast_example(model, passes, False)
        require(result["issue_plate_rows"] == 2 and result["decoder_layer_visits"] == 12 + 12 * passes
                and result["native_cross_pass_messages"] == 12 * (passes - 1), "Unexpected package visit count.")
        return encode(numeric(result))

    references = {p: packaged(p) for p in (1, 3, 5)}
    for passes, ref in references.items():
        require(encode(request(torch, demo, model, history, passes)) == ref, "Warm-up differs from package output.")
    cases = list(DEPTHS)
    rows = []
    for block in range(20):
        for case in cases_in_block(cases, block, reverse_groups=True):
            passes = DEPTHS[case]
            start = perf_counter_ns()
            if case == "three_package_example":
                produced = packaged(passes)
            else:
                produced = encode(request(torch, demo, model, history, passes))
            elapsed = perf_counter_ns() - start
            require(produced == references[passes], f"Timed output differs in {case}.")
            rows.append({"block": block, "case": case, "elapsed_ns": elapsed, "exact_reference": True,
                         "forecast_sha256": fingerprint(produced)})
    return {"reference_outputs": {str(p): json.loads(ref) for p, ref in references.items()}, "rows": rows}


def invented_histories(original):
    import numpy as np

    examples = []
    for factor in (1.0, 0.75, 1.15):
        history = deepcopy(original)
        for stream in history["streams"].values():
            values = np.asarray(stream["values"], dtype=np.float64)
            values[np.asarray(stream["observed"], dtype=bool)] *= factor
            stream["values"] = values.tolist()
        examples.append(history)
    return examples


def thread_trial(torch, demo, model, fixture):
    examples = invented_histories(fixture)
    references = [request(torch, demo, model, history, 3) for history in examples]
    released = json.loads((HERE / "results.json").read_bytes())["four_cpu_depths"]["reference_outputs"]["3"]
    require(encode(references[0]) == encode(numeric(released)), "Four-thread control differs from the published example.")
    rows = []
    for block in range(4):
        for threads in cases_in_block(THREADS, block):
            torch.set_num_threads(threads)
            require(torch.get_num_threads() == threads and torch.get_num_interop_threads() == 1, "Unexpected thread setup.")
            request(torch, demo, model, examples[0], 3)
            for index in range(6):
                example = (index + block) % 3
                start = perf_counter_ns()
                out = request(torch, demo, model, examples[example], 3)
                produced = encode(out, sorted_keys=True)
                elapsed = perf_counter_ns() - start
                ref = references[example]
                delta = {name: max(abs(x - y) for x, y in zip(out[name], ref[name], strict=True)) for name in FIELDS}
                rows.append({"block": block, "case": str(threads), "example": example, "elapsed_ns": elapsed,
                             "exact_reference": produced == encode(ref, sorted_keys=True), "max_abs_delta": delta})
    return {"reference_outputs": references, "rows": rows}


def validate_recorded():
    results = json.loads((HERE / "results.json").read_bytes())
    a, b = results["four_cpu_depths"], results["wider_affinity_threads"]
    for record in (a, b):
        require(grouped(record["rows"]) == record["summary"], "Recorded timing summaries differ from samples.")
    require(len(a["rows"]) == 80 and len(b["rows"]) == 96, "Unexpected recorded sample count.")
    expected_depths = [(i, case) for i in range(20) for case in cases_in_block(list(DEPTHS), i, True)]
    expected_widths = [(i, str(n), (k + i) % 3) for i in range(4) for n in cases_in_block(THREADS, i) for k in range(6)]
    require([(r["block"], r["case"]) for r in a["rows"]] == expected_depths, "Unexpected sequence of pass counts.")
    require([(r["block"], r["case"], r["example"]) for r in b["rows"]] == expected_widths, "Unexpected thread/input order.")
    for row in a["rows"]:
        ref = numeric(a["reference_outputs"][str(DEPTHS[row["case"]])])
        require(row["exact_reference"] and fingerprint(encode(ref)) == row["forecast_sha256"], "Recorded depth output differs.")
    require(numeric(a["reference_outputs"]["3"]) == numeric(b["reference_outputs"][0]), "Different four-thread controls.")
    for width in THREADS:
        rows = [r for r in b["rows"] if r["case"] == str(width)]
        require(Counter(r["example"] for r in rows) == {0: 8, 1: 8, 2: 8}, "Unbalanced thread trial.")
        require(all(r["exact_reference"] == all(d == 0 for d in r["max_abs_delta"].values()) for r in rows),
                "Numeric differences disagree with exact-match counts.")
        maxima = {c: max(r["max_abs_delta"][c] for r in rows) for c in FIELDS}
        require(maxima == b["largest_absolute_differences"][str(width)], "Recorded maximum differences disagree.")
    return {"four_cpu_depths": a["summary"], "wider_affinity_threads": b["summary"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify-results", "check-package", "depths", "threads"])
    parser.add_argument("--package", type=Path, help="Directory of the extracted 547-update Research Edition package.")
    parser.add_argument("--base-dir", type=Path, help="Directory containing the separate released base files.")
    args = parser.parse_args()
    if args.action == "verify-results":
        return validate_recorded()
    if not args.package:
        parser.error("--package is required for this action.")
    if args.action != "check-package" and not args.base_dir:
        parser.error("--base-dir is required for a timed model run.")
    folder = checked_directory(args.package)
    if args.action != "check-package":
        os.environ.update(OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", OPENBLAS_NUM_THREADS="1",
                          HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DEACTIVATE_ASYNC_LOAD="1",
                          CUDA_VISIBLE_DEVICES="", ROCR_VISIBLE_DEVICES="", TOKENIZERS_PARALLELISM="false")
    start = perf_counter_ns()
    sys.path.insert(0, str(folder))
    import demo

    manifest, checks = demo.self_test()
    if args.action == "check-package":
        return checks
    model = demo.load_preview(args.base_dir.expanduser().resolve(), manifest, 4)
    load_ns = perf_counter_ns() - start
    import torch

    require(not model.training and torch.get_num_threads() == 4 and torch.get_num_interop_threads() == 1,
            "Expected four CPU compute threads, one inter-op thread and evaluation mode.")
    fixture = json.loads((demo.PACKAGE / "example.json").read_bytes())
    fn = depth_trial if args.action == "depths" else thread_trial
    results = fn(torch, demo, model, fixture)
    return {"torch_version": str(torch.__version__), "logical_cpu_affinity": sorted(os.sched_getaffinity(0)),
            "verified_load_ms": load_ns / 1e6, "summary": grouped(results["rows"]), **results}


if __name__ == "__main__":
    try:
        print(json.dumps(main(), indent=2, allow_nan=False))
    except (OSError, ValueError, ImportError, RuntimeError) as error:
        sys.exit(str(error))
