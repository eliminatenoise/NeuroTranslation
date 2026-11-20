"""Summarize watched trials, exclusions, source coverage and output identities."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from fetch import ROOT
from excluded_metadata import diagnose
from prepare import TRACE, write_json


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def unique(records, field):
    return sorted({row[field] for row in records if field in row})


def hist(values):
    return dict(sorted(Counter(values).items()))


def data_summary(trials):
    good = [t for t in trials if t["eligible"]]
    total = lambda key: sum(t.get(key, 0) for t in trials)
    return {"stored_trials": len(trials), "eligible_trials": len(good),
            "excluded_trials": len(trials)-len(good),
            "exclusions": hist(t["reason"] for t in trials if not t["eligible"]),
            "trial_labels": hist(t.get("trial_type", "(not assigned because source identity or label count failed)") for t in trials),
            "sparse_trials_lt_50_archived_events": sum(t.get("event_count", 50) < 50 for t in trials),
            "zero_event_trials": sum(t.get("event_count") == 0 for t in trials),
            "native_mechanics_hz": unique([t["time"] for t in trials if "time" in t], "hz"),
            "native_electrical_hz": unique([t["time_PotMem"] for t in trials if "time_PotMem" in t], "hz"),
            "event_coordinates": hist(t["event_coordinates"] for t in trials if "event_coordinates" in t),
            "exclusions_missing_explicit_electrical_clock": sum(t.get("excluded_source_diagnostics",{}).get("time_PotMem",{}).get("available") is False for t in trials),
            "failed_clock_lattice_trials": sum("irregular or incompatible" in t.get("reason","") for t in trials),
            "nominal_mechanical_rate_disagreements": sum(t.get("mechanics_matches_readme") is False for t in trials),
            "trials_checked_for_interval_consistency_before_source_gate": sum("ISI" in t for t in trials),
            "tail_after_last_complete_bin_s_total_on_admitted_trials": sum(t.get("trailing_native_intervals",0)/t["time"]["hz"] for t in good),
            "supplied_ISI_disagreements": sum(not t["ISI"]["ok"] for t in trials if "ISI" in t),
            "supplied_interval_rate_disagreements": sum(not t["firing_rate"]["ok"] for t in trials if "firing_rate" in t),
            "signal_ranges_native_units": {
                n: [min(v[0] for v in vals),max(v[1] for v in vals)] if vals else None
                for n in ("Force","Length","PotMem") for vals in [
                    [t["signals"][n]["range"] for t in trials if t.get("signals", {}).get(n,{}).get("range") is not None]]},
            "flat_trials_by_signal": {n: sum(t.get("signals",{}).get(n,{}).get("flat") is True for t in trials)
                                      for n in ("Force","Length","PotMem")},
            "complete_mechanics_bins": total("complete_mechanics_bins"),"joint_valid_bins": total("valid_bins"),
            "bins_missing_electrical_coverage": total("bins_missing_electrical_coverage"),
            "bins_nonfinite_potential": total("bins_nonfinite_potential"), "bins_nonfinite_mechanics": total("bins_nonfinite_mechanics"),
            "candidate_windows_from_structurally_valid_trials": total("candidate_windows"),
            "eligible_windows": total("rows"), "events_in_trials_with_event_inventory": total("event_count"),
            "events_in_eligible_windows": total("target_spikes")}


def metadata(groups, directory):
    records = {}
    for g in groups:
        info = loadmat(directory/g["member"], variable_names=["info"], squeeze_me=True,
                       struct_as_record=False)["info"]
        labels = np.atleast_1d(info.trial_type).ravel(order="F").tolist()
        records[g["afferent"]] = {"archive_member":g["member"],"internal_affname":str(info.affname),
            "archive_date":str(info.date),"actual_trials":g["stored_trials"],"type_labels":len(labels),
            "internal_name_agrees":str(info.affname)==g["afferent"], "label_count_agrees":len(labels)==g["stored_trials"],
            "original_type_labels_in_deposit_order":labels}
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory",type=Path,default=ROOT/"private"/"members")
    parser.add_argument("--output",type=Path,default=ROOT/"private")
    args = parser.parse_args()
    local = args.output
    groups = json.loads((local / "trial-qc.json").read_text())
    originals = metadata(groups,args.directory)
    write_json(local/"member-metadata.json",originals)
    extra = diagnose(groups,args.directory)
    write_json(local/"quarantined-measurements.json",extra)
    clipped = []
    for g in groups:
        for t in g["trials"]:
            if "lattice" not in t.get("reason",""):
                continue
            d = t["excluded_source_diagnostics"]["time_PotMem"]
            ideal = t["time_PotMem"]["hz"]
            span = d["last_s"]-d["first_s"]
            clipped.append(dict(afferent=g["afferent"],trial=t["trial"],measured_hz=1/d["median_step_s"],
                                measured_span_s=span, signed_last_time_error_vs_required_grid_s=span-(d["samples"]-1)/ideal,
                                electrical_step_range_s=d["step_range_s"],measured_mechanical_and_electrical_last_time_difference_s=
                                d["last_s"]-t["excluded_source_diagnostics"]["time"]["last_s"]))
    trials = [trial for g in groups for trial in g["trials"]]
    with np.load(local/"windows.npz", allow_pickle=False) as rows:
        assert len(rows["X"]) == sum(t["rows"] for t in trials)
        assert np.array_equal(rows["current_mech"], rows["X"][:, -1, :2])
        assert all(np.isfinite(rows[k]).all() for k in ("X","mech_mean","y_count","y_delta","cutoff_s"))
        assert set(rows["prefix"].tolist()).issubset({0,1,4})
        assert np.all(rows["y_count"] >= 0)
        assert len(set(zip(rows["afferent"].tolist(), rows["trial"].tolist(), rows["bin_index"].tolist()))) == len(rows["y_count"])
        schema = {k: {"dtype": str(rows[k].dtype), "shape": list(rows[k].shape)} for k in rows.files}
    receipts = json.loads((local/"fetch-receipts.json").read_text())
    assert set(receipts) == {g["member"] for g in groups}
    for g in groups:
        assert all(g["integrity"][k] == receipts[g["member"]][k] for k in ("size", "crc32", "sha256"))
    manifest = {g["member"]: g["integrity"] for g in groups}
    write_json(ROOT/"member-manifest.json", manifest)
    summary = {
        "source":"Blum et al. 2020, original observed healthy rat muscle-spindle recordings.",
        "source_doi":"https://doi.org/10.5061/dryad.vdncjsxsw", "paper":"https://doi.org/10.7554/eLife.55177",
        "data_licence":"Creative Commons CC0 1.0", "data_grain":"one sensory afferent, one archived stretch trial, one nonoverlapping target bin of 20 ms; consecutive 100 ms histories overlap",
        "excluded_near_uniform_electrical_lattices":clipped,
        "quarantined_member_diagnostics":{n:{"excluded_trials":len(v["trials"]),"eligible_rows":0,
             "native_mechanics_hz":unique([t["time"] for t in v["trials"] if "time" in t],"hz"),
             "native_electrical_hz":unique([t["time_PotMem"] for t in v["trials"] if "time_PotMem" in t],"hz"),
             "trials_with_verified_event_coordinates": sum("event_coordinates" in t for t in v["trials"]),
             "diagnostic_failures":hist(t["diagnostic_failure"] for t in v["trials"] if "diagnostic_failure" in t)}
             for n,v in extra.items()},
        "metadata_checks":{k:{f:x for f,x in v.items() if f!="original_type_labels_in_deposit_order"} for k,v in originals.items()},
        "overall":data_summary(trials),
        "prefixes":{str(pr): data_summary([t for t in trials if t["prefix"] == pr]) for pr in (0,1,4)},
        "members":{g["afferent"]: data_summary(g["trials"]) for g in groups},
        "excluded_trials":[{"afferent":t["afferent"],"trial":t["trial"],"reason":t["reason"]} for t in trials if not t["eligible"]],
        "on_disk":schema,
        "output_sha256":{n:sha(local/n) for n in ["windows.npz","bin-mask.npz","trial-qc.json","member-metadata.json","quarantined-measurements.json",TRACE]},
        "source_freeze":sha(ROOT/"SOURCE-FREEZE.json"),
        "units":"Force, servo position and potential retain their signed archive scales. No documented individual gain/offset or absolute anatomical or electrical reference; no signal polarity inversion. Time is in seconds and rates of change use archived amplitude units per second.",
        "limits":"Archive included selected analyzable stretches and previously discriminated events. A held prefix is a filename group. Animal-wise independence, out-of-species or voluntary control, intrafusal force, causal feedback and prospective or closed-loop performance are unverified. aff015 trial 1 appeared in a prior engineering pilot; later model training and scaling exclude prefix 0 for its held replay.",
        "rights":"https://creativecommons.org/publicdomain/zero/1.0/","reserve_access":"Zero prefix-5, disease, stimulation or numerical simulation member payloads requested.",
        "source_integrity":"ZIP central directory from prior source verification; exact allowlisted local headers and compressed bytes from Zenodo (except source-verified retained pilot). Archive SHA-256 published by Dryad; individual approved MAT size, CRC32 and SHA-256 reproduced locally."}
    write_json(ROOT/"QC-SUMMARY.json", summary)
    print(json.dumps(summary["overall"], indent=2))


if __name__ == "__main__":
    main()
