"""Audit sampling and events of identity/label-quarantined members without emitting rows."""
import numpy as np
from scipy.io import loadmat

from fetch import MEMBERS, check
from prepare import BIN, TrialError, clock, event_indices, vector


def diagnose(groups, directory):
    summary = {}
    for group in groups:
        if group["recorded_affname"] == group["afferent"] and group["stored_trials"] == group["label_count"]:
            continue
        path = directory / group["member"]
        if check(path, MEMBERS[path.name]) != group["integrity"]:
            raise ValueError("Unexpected quarantined member identity")
        trials = np.atleast_1d(loadmat(path,variable_names=["proc_data"],squeeze_me=True,
                                       struct_as_record=False)["proc_data"]).ravel(order="F")
        records = []
        for i, trial in enumerate(trials):
            meta = {"trial":i+1}
            try:
                tm, nm = clock(trial,"time",2,meta)
                tv, nv = clock(trial,"time_PotMem",1,meta)
                hz = nv/BIN
                offset = round((tm[0]-tv[0])*hz)
                meta["origin_grid_error_s"] = float(abs(tm[0]-(tv[0]+offset/hz)))
                meta["actual_last_neural_minus_last_mechanics_s"] = float(tv[-1]-tm[-1])
                meta["consistent_sample_lengths"] = (len(vector(trial,"PotMem"))==len(tv)
                   and len(vector(trial,"Force"))==len(tm) and len(vector(trial,"Length"))==len(tm))
                meta["raw_tail_s_after_last_complete_mechanics_bin"] = float(((len(tm)-1)%nm)/(nm/BIN))
                event_indices(trial,tv,hz,meta)
            except TrialError as exc:
                meta["diagnostic_failure"] = str(exc)
            records.append(meta)
        summary[group["afferent"]] = {"identity_or_label_quarantine":True,"admitted_rows":0,"trials":records}
    return summary
