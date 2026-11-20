"""Score a separate, authorized 80-event recording with the sealed bundle."""
import argparse
import json
from pathlib import Path
import numpy as np
from evaluation import N, errors, load_npz, sealed_predictions

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("recording", type=Path, help="One authorized, source-contract-compatible NPZ.")
    parser.add_argument("receipt", type=Path, help="Matching acquisition receipt with units, timing and SHA256.")
    parser.add_argument("--export", type=Path, default=Path(__file__).parent / "export")
    args = parser.parse_args()
    x, baseline, target = load_npz(args.recording, args.receipt)
    weights = json.loads((args.export / "weights.json").read_text())
    controls = json.loads((args.export / "controls.json").read_text())
    predictions = sealed_predictions(x, baseline, np.arange(N), np.zeros(N), weights, controls)
    print(json.dumps(errors(target, predictions), indent=2, allow_nan=False))
