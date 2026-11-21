"""Measure fresh-process and cached batch-of-one inference on the installed CPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1] / "models" / "neurotranslate-0.0"


def worker():
    start = time.perf_counter()
    sys.path.insert(0, str(MODEL))
    from joint_alpha.product import Product, examples
    import numpy as np
    import resource

    model = Product()
    cases = examples()
    load = time.perf_counter() - start
    values = {}
    for name, row in cases.items():
        expected = model.predict(row)
        times = []
        for _ in range(50):
            then = time.perf_counter()
            actual = model.predict(row)
            times.append((time.perf_counter() - then) * 1e3)
            if actual != expected:
                raise ValueError("Output changed across repeated calls.")
        values[name] = {
            "median_ms": statistics.median(times), "p95_ms": sorted(times)[47],
            "output_sha256": hashlib.sha256(json.dumps(expected["prediction"]).encode()).hexdigest(),
        }
    return {"tasks": values, "checkpoint_sha256": model.digest, "load_ms": load * 1000,
            "process_peak_RSS_MiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss /
               (1024 ** 2 if platform.system() == "Darwin" else 1024), "numpy": np.__version__}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if args.worker:
        print(json.dumps(worker()))
        return
    if not args.out:
        p.error("Give an output filename with --out.")
    cpu = platform.processor() or platform.machine()
    if Path("/proc/cpuinfo").exists():
        cpu = next(x.split(":", 1)[1].strip() for x in Path("/proc/cpuinfo").read_text().splitlines() if x.startswith("model name"))
    result = {"cpu": cpu, "os": platform.system()+" "+platform.release(), "python": platform.python_version(),
              "allowed_logical_cpus": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count(),
              "method": "One CPU process. Fifty cached calls per invented case, batch size one. Four candidates in the rank example. RSS includes Python and NumPy. CLI wall time includes process and JSON I/O. Host background activity was not isolated. No GPU inference was used.", "threads": {}}
    for count in (1, 2):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS=str(count),
                   MKL_NUM_THREADS=str(count), OMP_NUM_THREADS=str(count), VECLIB_MAXIMUM_THREADS=str(count))
        row = json.loads(subprocess.check_output([sys.executable, "-B", __file__, "--worker"], env=env))
        times = []
        for _ in range(5):
            start = time.perf_counter()
            output = json.loads(subprocess.check_output([sys.executable, "-B", MODEL / "predict.py"], env=env))
            assert row["checkpoint_sha256"] == output["checkpoint_sha256"]
            times.append((time.perf_counter() - start) * 1000)
        row["fresh_cli_median_ms"] = statistics.median(times)
        result["threads"][str(count)] = row
    args.out.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
