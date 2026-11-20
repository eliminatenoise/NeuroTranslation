"""Verify both study partitions and score the distributed weights on the historical assessment."""
import argparse
from pathlib import Path
from train import load_rows, predictions, read, record, sha, torch

HERE = Path(__file__).resolve().parent
DEVELOPMENT_SHA = "30e584890531eb9576c10581839e48244961d0bf98ad767470cff67755f1e735"
HISTORICAL_SHA = "c8acd32db57449fbc8fb0c354d4950d836f44313ba28b39e49deed8901008b64"
WEIGHTS_SHA = "bb6b1847e6ac0ba273dc9e4c79ba8d509da30e0df094aecf0f06d6b317da16e2"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared", type=Path, help="Directory holding development.npz and historical.npz")
    parser.add_argument("output", type=Path, help="New directory for aggregate results and private local receipts")
    args = parser.parse_args()
    dev, held = [args.prepared / name for name in ("development.npz", "historical.npz")]
    weights = HERE / "weights.json"
    if [sha(p) for p in (dev, held, weights)] != [DEVELOPMENT_SHA, HISTORICAL_SHA, WEIGHTS_SHA]:
        raise ValueError("Source split or weights differ from the published experiment")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    fitted_people = set(load_rows(dev)["person"])
    historical = load_rows(held)
    if fitted_people & set(historical["person"]):
        raise ValueError("Person overlap between study partitions")
    prediction = predictions(read(weights), historical)
    args.output.mkdir(parents=True, exist_ok=False)
    record(args.output, "assessment", historical, prediction, "Historical participants, after fit and scorer seal")
    print(args.output / "assessment-summary.json")


if __name__ == "__main__":
    main()
