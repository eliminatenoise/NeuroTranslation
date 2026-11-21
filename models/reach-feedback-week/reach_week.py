"""Explore eight recorded reaches or rebuild the four September 7 to 14 comparisons."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
S = HERE / "source"
C = HERE / "counts"
M = HERE / "motor"
L = HERE / "late_counts"
G = HERE / "muscles"
DATA = json.loads((S / "selection.json").read_bytes())


def run(script, *args, python=sys.executable, threads=1):
    env = os.environ.copy()
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[variable] = str(threads)
    print(f"Running {script.relative_to(HERE)}", flush=True)
    subprocess.run([str(python), "-B", str(script), *map(str, args)], check=True, env=env)


def reproduce(args):
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Choose an empty output directory so previous fits and scores stay identifiable.")
    out.mkdir(parents=True, exist_ok=True)
    mat = {}
    for day, supplied in (("train", args.train_mat), ("held", args.held_mat)):
        mat[day] = supplied.resolve() if supplied else out / "raw" / Path(DATA[day]["member"]).name
    if not args.train_mat:
        run(S/"fetch.py", "train", out/"raw", *(["--archive", args.archive] if args.archive else []))
    arrays = out/"arrays"
    train, early = arrays/"train.npz", arrays/"train-positive.npz"
    run(S/"reconstruct.py", "train", "--mat", mat["train"], "--output", arrays)
    run(S/"positive_training.py", train, early)
    run(S/"coverage.py", "train", "--out", arrays)
    run(G/"read_lengths.py", "train", mat["train"], train, arrays/"train-lengths.npz")
    fits = out/"fits"
    fits.mkdir()
    run(C/"fit.py", train, fits/"counts.json", fits/"count-diagnostics.json")
    run(L/"fit.py", early, fits/"late.json")
    run(L/"training_check.py", early, fits/"late.json", fits/"late-forward.json")
    run(M/"refit_bases.py", early, fits/"bases", python=args.torch_python)
    run(M/"reproduce.py", "refit", train, fits/"motor", "--bases", fits/"bases", python=args.torch_python)
    run(G/"fit.py", train, arrays/"train-lengths.npz", fits/"weights.npz", threads=2)
    if not args.held_mat:
        run(S/"fetch.py", "held", out/"raw", *(["--archive", args.archive] if args.archive else []))
    run(S/"reconstruct.py", "held", "--mat", mat["held"], "--output", arrays)
    run(S/"coverage.py", "held", "--out", arrays)
    blocks = [arrays/f"block{i}.npz" for i in (1, 2)]
    lengths = [arrays/f"block{i}-lengths.npz" for i in (1, 2)]
    for block, length in zip(blocks, lengths, strict=True):
        run(G/"read_lengths.py", "held", mat["held"], block, length, "--labels", G/"names.json")
    scores = out/"scores"
    scores.mkdir()
    run(C/"score.py", "--fits", fits/"counts.json", "--metadata", C/"metadata", "--blocks", *blocks,
        "--result", scores/"counts.json", "--rows", scores/"counts.npz")
    run(L/"score.py", "--fits", fits/"late.json", "--metadata", C/"metadata", "--blocks", *blocks,
        "--output", scores/"late.json")
    run(M/"reproduce.py", "score", *blocks, scores/"motor", "--weights", fits/"motor", python=args.torch_python)
    run(M/"seed_details.py", "--input", scores/"motor/predictions.npz", "--output", scores/"motor/seed-contrasts.json")
    run(G/"score.py", "--weights", fits/"weights.npz", "--motor", scores/"motor/predictions.npz",
        "--roster", C/"metadata/held-roster.json", "--sources", *blocks, "--lengths", *lengths,
        "--out", scores/"muscles", threads=2)
    run(S/"case_snapshots.py", arrays, HERE/"cases/selection.json", out/"cases")
    run(HERE/"verify.py", out)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    operations = cli.add_subparsers(dest="command", required=True)
    operations.add_parser("list", help="List the eight recorded windows")
    case = operations.add_parser("case", help="Run the stored models on a recorded reach")
    case.add_argument("number", type=int, choices=range(1,9))
    case.add_argument("--json", type=Path, help="Save every forecast, reference and available control")
    rec = operations.add_parser("reproduce", help="Rebuild the inputs, refit, score, and compare with the release")
    rec.add_argument("output", type=Path)
    rec.add_argument("--train-mat", type=Path, help="Local original September 7 MATLAB member")
    rec.add_argument("--held-mat", type=Path, help="Local original September 14 MATLAB member")
    rec.add_argument("--archive", type=Path, help="Local original ZIP used for missing source members")
    rec.add_argument("--torch-python", default=sys.executable, help="Python executable with NumPy and PyTorch")
    args = cli.parse_args()
    if args.command == "reproduce":
        reproduce(args)
    else:
        from cases_api import case_list, forecast_case, describe
        if args.command == "list":
            for c in case_list():
                print(f"{c['case']}   block {c['block']}   workspace {c['workspace']}   reach {c['original']}   row {c['k']}   donor {c['donor_case']}")
        else:
            result = forecast_case(args.number)
            print(describe(result))
            if args.json:
                args.json.write_text(json.dumps(result, allow_nan=False, indent=2)+"\n", encoding="utf8")


if __name__ == "__main__":
    main()
