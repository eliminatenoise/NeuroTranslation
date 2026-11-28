"""Apply the record corrections of protocol revision 3 to the private manifest parts (lead decisions B and E).

  python record_r3_corrections.py --paths PATHS.json

No shard, no TOKENS.json and no source file is changed, and no recording value is read: the script edits the
per-dataset manifest parts and the private record of protocol heads, from counts in each TOKENS.json and from
the two values the second data review counted in the shard masks (named below). It can be run again; a second
run changes nothing. build_manifest.py then carries the corrected parts into MIXTURE-MANIFEST.json.

  1. tokens.field_storage of every part that has one is the stored dtype name of the field group, as the
     neural reader writes it now (four parts held an older wording with a pointer in brackets).
  2. Gait120 Q4: the field that was named steps_inside_emg_span is filled from the frame-range check (each step
     segment's frames lie inside the frames of its trial). It is renamed segment_frames_inside_trial_frames.
  3. Gait120 Q4: the step-segment steps that hold no EMG token are recorded (count and recordings from the
     second data review; the step totals and the two recordings are checked here against TOKENS.json).
  4. Gait120 Q4: the consecutive step segments that share one boundary frame are counted from the TargetFrame
     ranges in TOKENS.json, with the number of those frames that both recordings hold.
  5. Gait120 counts: inner-training windows from step segments and from static trials, apart, with the signal
     kinds that the static trials hold.
  6. The private record of protocol heads gains the revision that governed each step.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

OLD_Q4_KEY = "steps_inside_emg_span"
NEW_Q4_KEY = "segment_frames_inside_trial_frames"

# Counted by the second data review in the Gait120 shard masks (checks g120_values_check and g120_emg_gap).
REVIEW_NO_EMG = {"steps_without_an_emg_token": 16,
                 "recordings": {"S063_StandToSit_T02_S01": {"steps": 90, "without_emg": 15, "where": "the last 15 steps"},
                                "S107_SlopeDescent_T04_S01": {"steps": 56, "without_emg": 1, "where": "the first step"}}}

REVISION_BY_STEP = {
    "note": "Which protocol revision governed which step. A commit is named as it is on the branch; the hash in "
            "brackets is the same commit before the protocol branch was rebased, as the download records hold it.",
    "steps": [
        {"steps": "P1: the Katmah force-plate download and the first Gait120 pass", "revision": 1,
         "commit": "c0e522fcb45183ed98cf54a86af6dc9e8b0fb9ac (17f956b17b23bcc27d30a16d417d2ade23310da0)"},
        {"steps": "the rest of P1 and all of P2", "revision": 2,
         "commit": "554c59c219e113e8d8746f7120b5a5699a98188e (7d09f33101f78e79bd42dbda84722a4203f7c1df); the later "
                   "branch head cc2cbda25ec4243b132cb8badffe4c7d081719fe holds the same PROTOCOL.json"},
        {"steps": "P3 onwards", "revision": 3,
         "commit": "the commit named in the protocol entry of MIXTURE-MANIFEST.json"}]}


def _rename_key(d, old, new):
    return {(new if k == old else k): v for k, v in d.items()}


def gait120(part, tokens, alloc):
    rows = tokens["recordings"]
    seg = [r for r in rows if r.get("task") != "Static"]
    sta = [r for r in rows if r.get("task") == "Static"]
    tr = set(alloc["inner_folds"]["gait120"]["inner_training"])
    q4 = part["qualification"]["Q4_clock"]
    if OLD_Q4_KEY in q4:
        q4 = _rename_key(q4, OLD_Q4_KEY, NEW_Q4_KEY)
    q4["segment_frames_inside_trial_frames_checks"] = (
        "the first and last frame of each step segment lie inside the frame range of its trial; it says nothing "
        "about EMG cover (the field was named steps_inside_emg_span before revision 3)")

    # steps without an EMG token: review values, checked against the counts in TOKENS.json
    n_emg = len(tokens["channels"]["emg"])
    short ={r["rec_id"]: r["steps"] for r in seg
             if round(r["channel_seconds"].get("emg:surface_emg", 0.0) / common.STEP_S, 6) < n_emg * r["steps"]}
    assert set(short) == set(REVIEW_NO_EMG["recordings"]), sorted(short)
    assert all(short[k] == v["steps"] for k, v in REVIEW_NO_EMG["recordings"].items())
    assert sum(v["without_emg"] for v in REVIEW_NO_EMG["recordings"].values()) == REVIEW_NO_EMG["steps_without_an_emg_token"]
    q4["emg_cover_of_step_segments"] = {
        "step_segment_steps": sum(r["steps"] for r in seg),
        "steps_without_an_emg_token": REVIEW_NO_EMG["steps_without_an_emg_token"],
        "recordings": {k: "%s of %d steps" % (v["where"], v["steps"]) for k, v in REVIEW_NO_EMG["recordings"].items()},
        "counted_by": "the second data review, in the shard masks; the step total and the two recordings agree with "
                      "the channel-seconds in TOKENS.json",
        "effect": "those steps are masked for EMG and carry markers; nothing is filled in"}

    # consecutive segments of one trial that share a boundary frame
    by = defaultdict(list)
    for r in seg:
        by[(r["unit"], r["task"], r["trial"])].append(r)
    pairs = both = 0
    for v in by.values():
        v.sort(key=lambda r: r["step"])
        for x, y in zip(v, v[1:]):
            if x["target_frames"][1] == y["target_frames"][0]:
                pairs += 1
                # N frames give floor(N / 2) steps: the last frame is inside a step only if N is even
                both += (x["target_frames"][1] - x["target_frames"][0] + 1) % 2 == 0
    assert both == q4["boundary_frames_in_two_recordings"], (both, q4["boundary_frames_in_two_recordings"])
    q4["consecutive_segments_sharing_one_boundary_frame"] = {
        "trials": len(by), "pairs": pairs, "boundary_frames_tokenised_in_both_recordings": both,
        "why_not_all": "N frames give floor(N / 2) steps, so the last frame of a segment with an odd number of "
                       "frames is in no step",
        "fold": "both recordings of a pair belong to the same person, so no shared frame crosses a fold"}
    part["qualification"]["Q4_clock"] = q4

    # where the inner-training windows come from
    w_seg = sum(r["windows"] for r in seg if r["unit"] in tr)
    w_sta = sum(r["windows"] for r in sta if r["unit"] in tr)
    assert w_seg + w_sta == part["counts"]["windows_inner_training"]
    kinds = sorted({k for r in sta for k, v in (r.get("channel_seconds") or {}).items() if v > 0})
    part["counts"]["windows_inner_training_by_recording_kind"] = {
        "step_segments": w_seg, "static_trials": w_sta,
        "static_trial_signal_kinds": kinds,
        "note": "the static-trial windows hold markers only (no EMG, no force)" if kinds == ["kin:marker"]
        else "see static_trial_signal_kinds"}
    return part


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths")
    ap.add_argument("--protocol-dir", default=str(Path(__file__).resolve().parent.parent))
    a = ap.parse_args()
    paths = common.load_paths(a.paths)
    alloc = json.loads((Path(a.protocol_dir) / "ALLOCATION.json").read_text())
    parts_dir, shards = Path(paths["manifest_parts"]), Path(paths["shards"])
    done = {"field_storage": {}, "gait120": False, "revision_by_step": False}
    for f in sorted(parts_dir.glob("*.json")):
        part = json.loads(f.read_text())
        before = json.dumps(part, sort_keys=True)
        name = part["dataset"]
        tf = shards / name / "TOKENS.json"
        tokens = json.loads(tf.read_text()) if tf.exists() else None
        if tokens and "field_storage" in (part.get("tokens") or {}):
            now = tokens["dtypes"]["field"]
            if part["tokens"]["field_storage"] != now:
                done["field_storage"][name] = {"was": part["tokens"]["field_storage"], "now": now}
                part["tokens"]["field_storage"] = now
        if name == "gait120" and tokens:
            part = gait120(part, tokens, alloc)
        if json.dumps(part, sort_keys=True) != before:
            part["records_corrected"] = {"by": "record_r3_corrections.py (protocol revision 3)", "at": common.now_iso()}
            common.atomic_write_json(f, part)
            done["gait120"] = done["gait120"] or name == "gait120"
    heads = Path(paths["private"]) / "P1-PROTOCOL-HEADS.json"
    if heads.exists():
        h = json.loads(heads.read_text())
        if h.get("revision_by_step") != REVISION_BY_STEP:
            h["revision_by_step"] = REVISION_BY_STEP
            common.atomic_write_json(heads, h)
            done["revision_by_step"] = True
    print(json.dumps(done))


if __name__ == "__main__":
    main()
