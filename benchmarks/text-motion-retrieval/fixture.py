"""Generate invented trajectories and descriptions solely to exercise the software."""
import argparse
from pathlib import Path
import numpy as np
from retrieval import dump


def fixture(out, frames=24):
    out.mkdir(parents=True,exist_ok=False)
    rows = []
    rng = np.random.default_rng(7085)
    for participant in range(12):
        part = "train" if participant < 7 else "assessment" if participant < 10 else "reserve"
        for j in range(12):
            key = f"P{participant}T{j}"
            cue = ["bend","reach","rotate"][j % 3]
            row = {"key":key,"recording":key,"group":f"p{participant}","performers":[f"p{participant}"],
                   "part":part,"action":cue,"families":[f"p{participant}f{j//3}"]}
            rows.append(row)
            if part != "reserve":
                u = np.linspace(0, 1, frames)
                signals = np.stack([np.sin((j%3+1)*np.pi*u + k/9) for k in range(12)],axis=1)
                seq = signals + rng.normal(0,.04, signals.shape)
                np.save(out/(key+".npy"),seq.astype(np.float32))
                dump([f"the toy actor will {cue}", f"{cue} the toy limb"],out/(key+".json"))
    dump({"status":"artificial software fixture","rows":rows},out/"manifest.json")


if __name__=="__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory",type=Path)
    fixture(p.parse_args().directory)
