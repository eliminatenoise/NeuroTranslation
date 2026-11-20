"""Validate a prepared source split before retraining or evaluating the released model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("fit","score"))
    p.add_argument("prepared",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    stage="development" if args.action=="fit" else "assessment"
    env={**os.environ,"OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","OMP_NUM_THREADS":"3"}
    # Source verification needs NumPy only. It hashes the original inventory, QC and actual typed arrays.
    subprocess.run([sys.executable,"-B",str(HERE/"source/verify.py"),stage,str(args.prepared)],check=True,env=env)
    args.output.mkdir(parents=True,exist_ok=True)
    dataset=args.prepared/(stage+".npz")
    if args.action=="fit":
        subprocess.run([sys.executable,"-B",str(HERE/"fitting.py"),str(dataset),
                        str(args.output),"--device","cpu","--threads","3"],check=True,env=env)
        for file in ("weights.json","transfer-weights.json"):
            print(file,sha(args.output/file),"release match:",sha(args.output/file)==sha(HERE/file))
    else:
        report=args.output/"assessment-summary.json"
        subprocess.run([sys.executable,"-B",str(HERE/"assess.py"),str(dataset),str(HERE/"weights.json"),
                        str(HERE/"transfer-weights.json"),str(report)],check=True,env=env)
        print("Assessment aggregate matches:",json.loads(report.read_text())==json.loads((HERE/report.name).read_text()))


if __name__=="__main__":
    main()
