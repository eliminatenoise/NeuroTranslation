"""Verify the shipped example against the saved aggregate models."""
import argparse
import json
import math
from infer import HERE, predict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("python", "numpy"), default="python")
    args = parser.parse_args()
    load = lambda name: json.loads((HERE / name).read_text(encoding="utf-8"))
    models = load("model.json")["models"]
    sample, expected = load("example.json"), load("example-results.json")["estimates"]
    if set(models) != set(expected):
        raise ValueError("Unexpected method inventory")
    for name, model in models.items():
        result = predict(name, model, sample, args.backend)
        if not math.isclose(result, expected[name], abs_tol=1e-11, rel_tol=1e-10):
            raise ValueError(f"Example output differs for {name}")
    print(f"Matched all {len(models)} invented-input forecasts using {args.backend}.")


if __name__ == "__main__":
    main()
