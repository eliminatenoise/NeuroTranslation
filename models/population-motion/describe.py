"""Report timing and a secondary equal-window summary alongside the registered score."""
import json
import numpy as np
from study import ROOT, read_rat, write


def main():
    proto = json.loads((ROOT/"protocol.json").read_text())
    pred = np.genfromtxt(ROOT/"predictions.csv", delimiter=",", names=True, dtype=None, encoding="utf-8")
    out = {}
    for rat in proto["test"]:
        rows, _ = read_rat(rat)
        times = np.array([(r["target_time_s"]-r["cutoff_s"],r["cutoff_s"]-r["prior_time_s"][-1],
                           r["target_time_s"]-r["prior_time_s"][-1]) for r in rows]) * 1000
        out[rat] = {name:dict(min=float(t.min()),median=float(np.median(t)),max=float(t.max()))
                    for name,t in zip(("future_ms_from_cutoff","age_at_cutoff_ms","measured_span_ms"),times.T,strict=True)}
    pooled = {name:float(np.mean(np.abs(pred[name]-pred["target_cm"])))
              for name in ("constant_speed","motion","combined","earlier_trip")}
    write("timing-and-pooled.json",dict(timing_ms=out,pooled_MAE_cm=pooled))


if __name__ == "__main__":
    main()
