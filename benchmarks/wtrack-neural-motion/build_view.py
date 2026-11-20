"""Build the offline explorer from the archived forecasts, camera endpoints and scores."""
import json
from pathlib import Path
import numpy as np
here=Path(__file__).resolve().parent
scores=json.loads((here/"fitted/scores.json").read_text())
labels={"ridge_motion":"Movement-only ridge","ridge_combined":"Movement + spikes, ridge",
        "velocity":"Constant velocity","persistence":"Last position","attention_motion":"Movement-only attention",
        "attention_combined":"Movement + spikes, attention","ridge_wrong":"Ridge, earlier-trip spikes",
        "ridge_order":"Ridge, reordered spike bins","attention_wrong":"Attention, earlier-trip spikes",
        "attention_order":"Attention, reordered spike bins","ridge_spikes":"Spikes only","train_centroid":"Training centroid"}
with np.load(here/"fitted/predictions.npz",allow_pickle=False) as z:
    trips={}
    for i in scores["paired_trials"]:
        sel=z["trial"]==i
        trips[str(i)]={"time":z["cutoff_s"][sel].tolist(),"truth":z["measured_xy_cm"][sel].tolist(),
                       "lead":(z["label_s"][sel]-z["cutoff_s"][sel]).tolist(),
                       "pred":{m:z["pred_"+m][sel].tolist() for m in labels}}
payload={"trips":trips,"labels":labels,"metrics":{m:scores["metrics"][m]["mean_trip_error_cm"] for m in labels}}
template=(here/"view-template.html").read_text()
(here/"results.html").write_text(template.replace("/* SEALED DATA */",json.dumps(payload,separators=(",",":"))))
