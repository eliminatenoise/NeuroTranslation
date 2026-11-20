"""Rebuild the standalone offline reader from the trained model and aggregate results."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
def read(name):
    return json.loads((HERE / name).read_bytes())

if __name__ == "__main__":
    data = {k:read(n) for k,n in (("model","model.json"), ("dev","results.json"), ("held","assessment-summary.json"), ("example","example.json"))}
    data["labels"] = {"event_median":"Typical response at the event time", "persistence":"Latest neck reading",
        "median_innovation":"Latest neck reading + typical change","neck":"Neck history","other_sites":"Neck, thumb, scalp and heart",
        "with_axilla":"Same four sites + axilla", "wrong_event":"Axilla from a different event"}
    met = data["held"]["criterion_met"]
    data["finding"] = ("The axillary recording met" if met else "The axillary recording fell short of") + " the preset test. It required at least 5% less error than both the four-site model and the wrong-event comparison, with improvement for all six people."
    payload=json.dumps(data,separators=(",",":"),allow_nan=False).replace("<","\\u003c")
    template=(HERE/"reader.html.in").read_text()
    assert template.count("@@DATA@@")==1
    (HERE/"index.html").write_text(template.replace("@@DATA@@",payload),encoding="utf-8")
