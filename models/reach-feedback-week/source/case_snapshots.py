"""Save just the eight preselected September 14 windows, with the recording-local column guide."""
import argparse
import json
from pathlib import Path

import numpy as np

KEY = ("block","workspace","original","ordinal","k")


def snapshot(arrays, selection, destination):
    destination.mkdir(parents=True, exist_ok=True)
    choices = json.loads(selection.read_text())["cases"]
    for block in (1, 2):
        with np.load(arrays/f"block{block}.npz", allow_pickle=False) as d, np.load(
            arrays/f"block{block}-lengths.npz", allow_pickle=False
        ) as lengths:
            keys = list(zip(*(d[k] for k in KEY), strict=True))
            for number, choice in enumerate(choices, 1):
                if choice["block"] != block:
                    continue
                key = tuple(choice[k] for k in KEY)
                row = keys.index(key)
                observed = {name: d[name][row] for name in ("pose","cue","cue_at_k","movement",
                            "all_history","all_concurrent","all_delayed","history_rows","movement_rows","delayed_rows")}
                with (destination/f"case-{number}.npz").open("xb") as target:
                    np.savez_compressed(target, key=np.asarray(key), all_guide=d["all_guide"],
                                        **observed, path_labels=lengths["names"], source_model_delta_m=lengths["delta_m"][row],
                                        source_model_anchor_m=lengths["anchor_m"][row])


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("arrays", type=Path)
    cli.add_argument("selection", type=Path)
    cli.add_argument("destination", type=Path)
    args = cli.parse_args()
    snapshot(args.arrays, args.selection, args.destination)
