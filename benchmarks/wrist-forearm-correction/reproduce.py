"""Recompute this study from six local source archives, or run an invented input."""
import argparse
import json
import os
from pathlib import Path


def example():
    import numpy as np
    import torch
    from forecast import TemporalNet
    torch.manual_seed(17)
    net = TemporalNet(2)
    with torch.no_grad():
        for param in net.parameters():
            param.zero_()
        net.predictor[-1].bias.copy_(torch.tensor([.25, -.50]))
        change = net(torch.zeros(1, 2, 16), torch.zeros(1, 8)).numpy()[0]
    anchor = np.array([2., -1.])
    print(json.dumps({"example":"Invented angles and illustrative weights",
                      "last_angle_deg":anchor.tolist(), "future_angle_deg":(anchor+change).tolist()}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="stage", required=True)
    subs.add_parser("example", help="Run an invented two-angle example with no real data")
    prepare = subs.add_parser("prepare", help="Verify and decode the six locally stored source ZIPs")
    prepare.add_argument("--archives", type=Path, required=True)
    for sub in (prepare, subs.add_parser("fit"), subs.add_parser("score")):
        sub.add_argument("--work", type=Path, required=True, help="A writable study output directory")
    a = p.parse_args()
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    if a.stage == "example":
        example()
        return
    a.work.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.environ["WRIST_STUDY_WORK"] = str(a.work.resolve())
    from common import RESULT
    lock = RESULT / "run.lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        if a.stage == "prepare":
            from read_archives import prepare as extract
            extract(a.archives)
        else:
            import torch
            torch.use_deterministic_algorithms(True)
            torch.set_num_interop_threads(1)
            torch.set_num_threads(2)
            if a.stage == "fit":
                from models import fit_all
                fit_all()
            else:
                from score import score_all
                score_all()
                scores = json.loads((RESULT / "scores.json").read_text())
                print(json.dumps({k:v["equal_person_rmse_deg"] for k,v in scores["scores"].items()}, indent=2))
    finally:
        lock.unlink()


if __name__ == "__main__":
    main()
