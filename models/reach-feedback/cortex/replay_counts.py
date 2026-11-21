"""Print a forecast and measured counts from one recorded training reach."""
import argparse
from pathlib import Path
import numpy as np
from count_model import predict

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["transformer","glm"], default="transformer")
    parser.add_argument("--seed", type=int, choices=[17,41,73], default=17)
    args = parser.parse_args()
    with np.load(HERE/"example.npz") as example:
        inputs = {k:example[k] for k in ("pose","spikes","cue")}
        if args.family == "transformer":
            seed_index = example["seeds"].tolist().index(args.seed)
            movement = example["forecast"][seed_index]
            suffix = f"-{args.seed}"
        else:
            movement = example["ridge_forecast"]
            suffix = ""
        output = {}
        for arm in ("direct","full"):
            path = HERE/"weights"/f"{args.family}-{arm}{suffix}.npz"
            with np.load(path) as weights:
                np.testing.assert_array_equal(weights["unit_guide"],example["unit_guide"])
                output[arm] = predict(weights, **inputs, movement=movement).sum(axis=1)[0]
        print(f"Training reach {example['original'].item()}, go {example['ordinal'].item()}, "
              f"first unseen 10 ms sample {example['k'].item()}")
        print("Expected and measured spikes per unit from 100 to 200 ms after cutoff")
        print("channel sort   history   history+forecast   measured")
        observed = example["delayed"].sum(axis=1)[0]
        for (channel, sort), direct, full, count in zip(example["unit_guide"],output["direct"],output["full"],observed):
            print(f"{int(channel):7d} {int(sort):4d} {direct:9.3f} {full:18.3f} {int(count):10d}")


if __name__ == "__main__":
    main()
