"""Compare portable JS with independent NumPy inference on invented inputs."""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
MODES = ("markers","emg","combined")
METHODS = ("transformer","ridge")


def node(code, value=None):
    result = subprocess.run(["node","-e",code],cwd=ROOT,input=json.dumps(value),text=True,
                            capture_output=True,check=True)
    return json.loads(result.stdout)


def run(models):
    pins = json.loads((ROOT/"src/source-sha256.json").read_text())
    for source in ("predict.py","invented-example.json"):
        assert hashlib.sha256((models/source).read_bytes()).hexdigest() == pins[source]
    spec = importlib.util.spec_from_file_location("walking_numpy",models/"predict.py")
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    fixture = json.loads((models/"invented-example.json").read_text())
    inputs = node("""
        const e=require('./src/example.js');const out=[];
        for(const speed of [.4,.6,.8]) for(const gain of [0,1.6,3])
          for(const t of [0,240,720,1440]) out.push(e.history(t,{...e.defaults,speed,gain,shift:80}));
        console.log(JSON.stringify(out));
    """)
    rng = np.random.default_rng(301)
    # Stress missing flags, out-of-range values and clipping without using real data.
    for _ in range(48):
        x = rng.normal(0,1,(8,40))
        x[:,24:32] = abs(x[:,24:32])*120
        x[:,18:24] = rng.integers(0,2,(8,6))
        x[:,32:40] = rng.integers(0,2,(8,8))
        inputs.append(x.tolist())
    inputs.append(fixture["rows"])
    actual = node("""
        const fs=require('node:fs');const inputs=JSON.parse(fs.readFileSync(0,'utf8'));
        const m=require('./src/predict.js'),w=require('./src/bundle.json').weights,out={};
        for(const f of ['ridge','transformer'])for(const s of ['markers','emg','combined'])
          out[f+'-'+s]=inputs.map(x=>m.predict(x,w,f,s));
        console.log(JSON.stringify(out));
    """,inputs)
    errors = {}
    for f in METHODS:
        for m in MODES:
            key = f+"-"+m
            file = models/"weights"/(key+".npz")
            assert hashlib.sha256(file.read_bytes()).hexdigest()==pins[file.name]
            with np.load(file,allow_pickle=False) as w:
                expected = getattr(oracle,f)(inputs,w,m)
            difference = float(np.abs(expected-actual[key]).max())
            if not np.isfinite(difference) or difference >= 0.002:
                raise ValueError(f"{key} disagrees with Python by {difference} N")
            assert abs(actual[key][-1]-fixture["expected_N"][key]) < 0.002
            errors[key] = difference
    return {"invented_histories":len(inputs),"models":6,"predictions":6*len(inputs),"max_abs_difference_N":errors,
            "tolerance_N":0.002,"numpy":np.__version__,"node":subprocess.check_output(["node","-v"],text=True).strip(),
            "blas_threads":os.getenv("OPENBLAS_NUM_THREADS")}


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("models",type=Path)
    args=p.parse_args()
    print(json.dumps(run(args.models.resolve()),indent=2))
