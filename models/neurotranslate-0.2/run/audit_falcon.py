"""P2 role audit of the conditional member FALCON M1-A (DANDI 000941, version 0.241029.1405).

  python audit_falcon.py --paths PATHS.json

PROTOCOL.json admits only 'held-in-calib' days that no earlier NeuroTranslation or project evaluation used, and
Q2 keeps out every unit of a line that is in flight or on hold. This script lists the version's assets (one
metadata request), then records the evidence for each held-in-calib day:
  - 20120928: acquired and scored by earlier project work (the earlier muscle decoder and the first-fit study,
    whose chronological test trials 350-411 were exposed) -> consumed;
  - 20120924, 20120926, 20120927: the primary candidate pool of the author-frozen FALCON M1-A cross-session
    contract (awaiting independent review; its owning line is on hold), which reserves previously unused days
    for future external-session tests -> a held line's units.
No FALCON recording file is downloaded or opened. The result is written as manifest-parts/falcon_m1.json and
audits/falcon_m1-AUDIT.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import licences  # noqa: E402

ASSETS = "https://api.dandiarchive.org/api/dandisets/000941/versions/0.241029.1405/assets/?page_size=100"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    head = common.protocol_head(paths)
    pacer = common.Pacer(1.05)
    r = common.http_get(ASSETS, pacer, headers={"Accept": "application/json"})
    common.log_download(paths, {"dataset": "falcon_m1", "url": ASSETS, "final_url": r["final_url"], "hosts": r["hosts"],
                                "range": None, "status": r["status"], "bytes": r["bytes"], "sha256": r["sha256"],
                                "purpose": "asset listing of the pinned version (metadata; no recording bytes)"})
    listing = json.loads(r["body"])
    held_in = sorted({re.search(r"ses-(\d{8})", x["path"]).group(1) for x in listing["results"]
                      if x["path"].startswith("sub-MonkeyL-held-in-calib/")})
    ev = {k: Path(v) for k, v in paths["falcon_evidence"].items()}
    digests = {k: common.sha256_file(p) for k, p in ev.items()}
    summary = ev["cross_session_contract_summary"].read_text()
    contract = json.loads(ev["cross_session_contract"].read_text())
    in_pool = "held-in days 20120924/26/27 (primary pool" in summary
    frozen = "AUTHOR-FROZEN" in contract.get("status", "")
    fitmap = json.loads(ev["earlier_fit_map"].read_text())
    scored_0928 = fitmap.get("completed_split", {}).get("test_trials_inclusive") == [350, 411]
    emg = json.loads(ev["earlier_emg_metrics"].read_text())
    emg_session = json.dumps(emg).count('"session": "20120928"') > 0
    days = []
    for d in held_in:
        if d == "20120928":
            reason = ("consumed: acquired and scored by earlier project work (earlier muscle decoder, session 20120928; "
                      "first-fit study test trials 350-411 exposed)")
            ok = False
        elif d in ("20120924", "20120926", "20120927") and in_pool and frozen:
            reason = ("held line: primary candidate pool of an author-frozen FALCON M1-A cross-session contract that "
                      "awaits independent review and reserves previously unused days for future external-session tests; "
                      "its owning line is on hold")
            ok = False
        else:
            reason = "no earlier use found"
            ok = True
        days.append({"unit": "held-in-calib ses-" + d, "eligible": ok, "reason": reason})
    passed = [x for x in days if x["eligible"]]
    audit = {"dataset": "falcon_m1", "protocol_head": head, "rule": "only held-in-calib days that no earlier evaluation used; "
             "no unit of a line in flight or on hold (Q2)", "held_in_calib_days_listed": held_in, "days": days,
             "evidence": {k: {"file": str(Path(v).name), "sha256": digests[k]} for k, v in ev.items()},
             "checks": {"0928_scored_by_earlier_study": scored_0928, "0928_earlier_emg_decoder_session": emg_session,
                        "0924_0926_0927_in_contract_primary_pool": in_pool, "contract_author_frozen": frozen},
             "all_units_pass": False, "admitted_days": [x["unit"] for x in passed],
             "files_downloaded_or_opened": 0}
    common.atomic_write_json(Path(paths["audits"]) / "falcon_m1-AUDIT.json", audit)
    lic = json.loads((Path(paths["licences"]) / "falcon_m1.json").read_text())
    not_assessed = {"pass": False, "how": "not assessed: the role audit admitted no day, so no file was downloaded or opened"}
    part = {
        "dataset": "falcon_m1", "part": "neural", "wave": "1 (conditional; not admitted by the P2 role audit)",
        "name": "FALCON Benchmark M1-A", "doi": "10.48324/dandi.000941/0.241029.1405", "licence": lic.get("spdx") or lic["declared_licence"],
        "licence_as_declared": lic["declared_licence"], "species": "macaque", "sites": 1, "protocol_head": head, "built_at": common.now_iso(), "qualified": False,
        "not_qualified_because": "Q2 role: no held-in-calib day is free. 20120928 was scored by earlier project work; "
                                 "20120924, 20120926 and 20120927 are the primary candidate pool of an author-frozen "
                                 "cross-session contract of a line on hold.",
        "counts": {"individuals": 0, "individuals_in_roster": 0, "animals": 0, "people": 0, "sites": 1, "sessions": 0,
                   "recordings": 0, "tasks": {}, "conditions": {}, "unique_steps_20ms": 0, "steps_with_any_channel": 0,
                   "windows_1200ms": 0, "windows_1200ms_every_step_with_data": 0, "windows_inner_training": 0,
                   "windows_inner_validation": 0, "channel_seconds": {}, "spikes": 0,
                   "events": {"count": 0, "definition": "none (not admitted)"}, "sources_read_without_a_full_step": 0},
        "qualification": {
            "Q1_licence": licences.q1_gate(lic),
            "Q2_role": {"pass": False, "days": days, "evidence_sha256": digests},
            "Q3_access": not_assessed, "Q4_clock": not_assessed, "Q5_labels": not_assessed, "Q6_causality": not_assessed},
        "role_audit": {"pass": False, "units": len(days), "admitted": [], "excluded": [x["unit"] for x in days]},
        "tokens": {"shards": 0, "bytes": 0},
        "notes": ["Held-in-minival files are subsets of held-in-calib files; held-out-calib days are not held-in-calib and are "
                  "also in the contract's candidate pool. None is used."],
    }
    common.atomic_write_json(Path(paths["manifest_parts"]) / "falcon_m1.json", part)
    print(json.dumps({"held_in_calib_days": held_in, "admitted": audit["admitted_days"], "checks": audit["checks"]}))


if __name__ == "__main__":
    main()
