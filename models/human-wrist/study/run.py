"""Refit a fictional example or the two AJILE12 recording days, then export a local reader case."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
from tempfile import mkdtemp

# Set CPU pools before importing NumPy, SciPy or PyTorch.
for variable in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[variable] = "1"

import numpy as np

import bilateral
from case_format import pack_case, make_package
from estimators import fit, predict
import fictional
import scores

HERE = Path(__file__).resolve().parent
STAGES = ("fit", "predict", "score")
EXPECTED = json.loads((HERE / "expected.json").read_text())


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def dump(path, data):
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, allow_nan=False, separators=(",", ":"))
        f.write("\n")


def save(path, values):
    with path.open("xb") as f:
        np.savez_compressed(f, **values)


def load(path):
    with np.load(path, allow_pickle=False) as f:
        return dict(f)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def products(directory):
    return {
        p.name: sha(p)
        for p in sorted(directory.iterdir())
        if p.is_file() and p.name != "receipt.json"
    }


def software():
    return {
        p.name: sha(p)
        for p in sorted([*HERE.glob("*.py"), HERE / "assets.json", HERE / "expected.json"])
    }


@contextmanager
def stage_dir(work, stage, origin, bindings):
    """Commit complete stages atomically. Reuse only after checking their contents and upstream identities."""
    path = work / stage
    expected = {"source": origin, "software_sha256": software(), "upstream_sha256": bindings}
    if path.exists():
        receipt = read(path / "receipt.json")
        if receipt != {**expected, "outputs_sha256": products(path)}:
            raise ValueError(
                f"{stage} differs from its saved files or inputs. Use a new work directory."
            )
        yield None
        return
    scratch = Path(mkdtemp(prefix="." + stage + "-", dir=work))
    try:
        yield scratch
        dump(scratch / "receipt.json", {**expected, "outputs_sha256": products(scratch)})
        scratch.rename(path)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


def data_for(args, day, stage):
    if args.mode == "practice":
        return fictional.generate(day, stage), None
    from extract import materialize

    arrays, montage = materialize(
        day,
        stage,
        args.train_nwb if day == 3 else args.held_nwb,
        args.work,
        args.cap_mib,
        args.workers,
    )
    for name, digest in EXPECTED["source_arrays_sha256"][stage].items():
        array = np.ascontiguousarray(arrays[name])
        if hashlib.sha256(array.tobytes()).hexdigest() != digest:
            raise ValueError(f"Session {day}, {stage}, {name}: frozen source array differs")
    return arrays, montage


def stage_fit(args, dest):
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    data, montage = data_for(args, 3, "train")
    save(dest / "training.npz", data)
    weights, geo, older = fit(data)
    save(dest / "weights.npz", weights)
    dump(dest / "geometry.json", geo)
    save(dest / "legacy.npz", older)
    dump(dest / "montage.json", montage)


def stage_predict(args, dest):
    data, montage = data_for(args, 4, "inputs")
    fitted = args.work / "fit"
    if montage != read(fitted / "montage.json"):
        raise ValueError("Electrode coordinate or contact quality fields changed between days")
    save(dest / "inputs.npz", data)
    weights = load(fitted / "weights.npz")
    outputs, meta = predict(
        data, weights, read(fitted / "geometry.json"), load(fitted / "legacy.npz")
    )
    save(dest / "predictions.npz", outputs)
    save(dest / "row-checks.npz", meta)
    valid = meta["input_qc"].all(axis=1)
    if not valid.any():
        raise ValueError("No bilateral row passes input quality")
    i = int(np.flatnonzero(valid)[0])
    dump(
        dest / "case.json",
        make_package(weights, [pack_case(data["ecog_uv"][i], data["prior_pose_px"][i])]),
    )


def aggregate(outputs, checks, targets):
    for k in ("native_event_row", "onset_s", "source_block"):
        np.testing.assert_array_equal(checks[k], targets[k], err_msg="Held target alignment")
    n = len(checks["native_event_row"])
    outcome = targets["future_wrist_px"]
    if outcome.shape != (n, 2, 2, 2) or len(outputs) != 110:
        raise ValueError("Incomplete forecast or target suite")
    donor = checks["donor_index"]
    present = donor >= 0
    if np.any(donor[present] >= np.flatnonzero(present)) or np.any(
        checks["source_block"][donor[present]] >= checks["source_block"][present]
    ):
        raise ValueError("Donor must precede the recipient in another block")
    group = (checks["onset_s"] // 14400).astype(int)
    return dict(
        rows=n,
        stratum_window_counts=np.bincount(group, minlength=6).tolist(),
        right_left_input_qc=checks["input_qc"].sum(0).tolist(),
        target_valid_horizon_by_side=np.isfinite(outcome).all(3).sum(0).tolist(),
        eligible_prior_voltage_donor=int(present.sum()),
        seed_order=list(bilateral.SEEDS),
        **scores.report(outputs, outcome, group),
    )


def rounded_digest(obj):
    """Portable aggregate comparison, rounding floating-point output to five decimal places."""

    def rounded(v):
        if isinstance(v, dict):
            return {k: rounded(e) for k, e in v.items()}
        if isinstance(v, (tuple, list)):
            return [rounded(e) for e in v]
        if isinstance(v, float):
            return round(v, 5) or 0.0
        return v

    canonical = json.dumps(rounded(obj), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def stage_score(args, dest):
    targets, _ = data_for(args, 4, "targets")
    save(dest / "targets.npz", targets)
    directory = args.work / "predict"
    result = aggregate(
        load(directory / "predictions.npz"), load(directory / "row-checks.npz"), targets
    )
    dump(dest / "scores.json", result)
    digests = {k: rounded_digest(v) for k, v in result.items()}
    expected = EXPECTED.get("aggregate_sections_sha256", {})
    compare = {k: digests[k] == v for k, v in expected.items()} if args.mode == "clinical" else {}
    dump(
        dest / "comparison.json",
        dict(
            source=args.mode,
            methods=len(result["absolute"]),
            pairs=len(result["pairs"]),
            computed=digests,
            section_matches=compare,
        ),
    )


@contextmanager
def exclusive_run(work):
    """Hold one OS-managed writer lock while publishing a stage or charging a network range."""
    with (work / ".run.lock").open("a+b") as file:
        if os.name == "nt":
            import msvcrt

            if file.tell() == 0:
                file.write(b"0")
                file.flush()
            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield  # Closing the handle releases the lock, including after process exit.


def run(args):
    origin = (
        "fictional practice, generator version 1"
        if args.mode == "practice"
        else "AJILE12 DANDI:000055/0.220127.0436"
    )
    bindings = {}
    for stage, fn in zip(STAGES, (stage_fit, stage_predict, stage_score)):
        with stage_dir(args.work, stage, origin, bindings.copy()) as dest:
            if dest is not None:
                fn(args, dest)
        print(f"{stage}: {args.work / stage}", flush=True)
        bindings[stage] = sha(args.work / stage / "receipt.json")
        if stage == args.through:
            break
    if args.through == "score" and args.mode == "clinical":
        comparison = read(args.work / "score/comparison.json")["section_matches"]
        if not comparison or not all(comparison.values()):
            raise SystemExit(
                "Scores saved. Frozen aggregate differs in: "
                + ", ".join(k for k, v in comparison.items() if not v)
            )
        print("All frozen aggregate sections match at five decimal places.")


def export(args):
    work = args.work
    fit_status = read(work / "fit/receipt.json")
    pred_status = read(work / "predict/receipt.json")
    if (
        fit_status["outputs_sha256"] != products(work / "fit")
        or pred_status["outputs_sha256"] != products(work / "predict")
        or pred_status["upstream_sha256"]["fit"] != sha(work / "fit/receipt.json")
    ):
        raise ValueError("Fit and prediction files no longer match")
    data = load(work / "predict/inputs.npz")
    i = args.row
    if not 0 <= i < len(data["ecog_uv"]):
        raise ValueError("Held row outside the selected recording")
    future = None
    if args.with_reference:
        status = read(work / "score/receipt.json")
        if status["outputs_sha256"] != products(work / "score") or status["upstream_sha256"][
            "predict"
        ] != sha(work / "predict/receipt.json"):
            raise ValueError("Held score and forecast files no longer match")
        targets = load(work / "score/targets.npz")
        np.testing.assert_array_equal(targets["native_event_row"], data["native_event_row"])
        future = targets["future_wrist_px"][i]
    c = pack_case(data["ecog_uv"][i], data["prior_pose_px"][i], future)
    dump(args.output, make_package(load(work / "fit/weights.npz"), [c]))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("practice", "clinical"):
        p = commands.add_parser(mode)
        p.add_argument("--work", required=True, type=Path, help="Separate local output directory")
        p.add_argument("--through", choices=STAGES, default="score")
        if mode == "clinical":
            p.add_argument("--train-nwb", type=Path, help="Local official session 3 NWB file")
            p.add_argument("--held-nwb", type=Path, help="Local official session 4 NWB file")
            p.add_argument(
                "--download-ranges",
                action="store_true",
                help="Read pinned byte ranges from DANDI for any missing local NWB",
            )
            p.add_argument(
                "--cap-mib",
                type=int,
                default=384,
                choices=range(1, 385),
                metavar="1..384",
                help="Cumulative requested MiB per remote asset",
            )
            p.add_argument(
                "--workers",
                type=int,
                default=4,
                choices=range(1, 7),
                help="Concurrent independent chunk reads",
            )
    p = commands.add_parser("case")
    p.add_argument("--work", required=True, type=Path)
    p.add_argument("--row", required=True, type=int, help="Zero-based held row")
    p.add_argument("--output", required=True, type=Path, help="New private JSON")
    p.add_argument(
        "--with-reference",
        action="store_true",
        help="Include observed future wrist position after scoring",
    )
    args = parser.parse_args()
    if args.mode == "case":
        export(args)
    else:
        if args.mode == "clinical" and not args.download_ranges:
            if not args.train_nwb or (args.through != "fit" and not args.held_nwb):
                parser.error("Supply local NWB paths or explicitly enable --download-ranges")
        args.work.mkdir(mode=0o700, parents=True, exist_ok=True)
        with exclusive_run(args.work):
            run(args)


if __name__ == "__main__":
    main()
