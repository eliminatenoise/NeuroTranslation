"""Reconstruct one prespecified split from the original Chowdhury TRT session."""
import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from scipy.io import loadmat

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "selection.json").read_bytes())
SPLITS = {"train": "train", "validation": "validation",
          "within": "test_within_workspace", "transfer": "test_transfer_workspace"}
NATIVE_MARKERS = [f"{name}_{axis}" for name in ("Marker_1", "Pronation_Pt1") for axis in "xyz"]
COUNT_COLUMNS = [4, 10, 13, 14, 16, 18, 21, 29, 31, 33, 35, 37, 39, 42, 45, 47, 50, 53, 57, 59, 61, 68, 73]


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def key_hash(rows):
    return hashlib.sha256(json.dumps(rows, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def verify(condition, message):
    if not condition:
        raise ValueError(message)


def atomically(path, writer):
    with NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            writer(f)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        if path.exists():
            verify(digest(path) == digest(tmp), f"Existing {path.name} differs")
        else:
            os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def save_json(path, obj):
    atomically(path, lambda f: f.write((json.dumps(obj, indent=2, allow_nan=False) + "\n").encode()))


def admit(split, release_dir):
    seal = HERE / "source-seal.json"
    for name, expected in json.loads(seal.read_bytes())["files"].items():
        verify(digest(HERE / name) == expected, f"Source implementation changed: {name}")
    if split == "train":
        return None
    stage = "validation" if split == "validation" else "test"
    release = release_dir / f"{stage}-release.json"
    data = json.loads(release.read_bytes())
    verify(data.get("authorized") is True and data.get("stage") == stage
           and data.get("splits") == (["validation"] if stage == "validation" else ["within", "transfer"])
           and data.get("source_seal_sha256") == digest(seal), "Wrong numerical release")
    return digest(release)


def metadata(blocks):
    roster = []
    for b, td in enumerate(blocks, 1):
        verify((td.monkey, td.task, td.bin_size) == ("C", "TRT", 0.01), "Unexpected session or grid")
        go, target = td.idx_goCueTime, td.idx_targetStartTime
        rows = zip(td.trialID, td.idx_startTime, td.idx_endTime, td.spaceNum, td.result, strict=True)
        for oid, start, end, ws, result in rows:
            events = go[(go >= start) & (go <= end)].astype(int).tolist()
            onset = target[(target >= start) & (target <= end)].astype(int).tolist()
            region = int(ws) if float(ws).is_integer() else float(ws)
            roster.append(dict(block=b, original=int(oid), start=int(start), end=int(end),
                               workspace=region, result=str(result), go=events, target=onset, split="unused", fold=-1))
    train_region = [r for r in roster if r["workspace"] == 1 and r["result"] == "R"]
    a, v = len(train_region) * 7 // 10, len(train_region) * 15 // 100
    pieces = np.array_split(np.arange(a), 5)
    folds = [piece_no for piece_no, part in enumerate(pieces) for _ in part]
    for i, r in enumerate(train_region):
        r["split"] = "train" if i < a else ("validation" if i < a + v else "within")
        if i < a:
            r["fold"] = folds[i]
    for r in roster:
        if r["workspace"] == 2 and r["result"] == "R":
            r["split"] = "transfer"
    raw = [[r[k] for k in ("block", "original", "start", "end", "workspace", "result")]
           + [SPLITS.get(r["split"], "unused"), r["go"], r["target"]] for r in roster]
    verify(key_hash(raw) == CONFIG["original_roster_sha256"], "Original metadata or chronology changed")
    ids = [[[r["block"], r["original"]] for r in roster if r["fold"] == i] for i in range(5)]
    verify(key_hash(ids) == CONFIG["five_forward_pieces_sha256"], "Forward pieces changed")
    return roster


def anchors(roster):
    windows, summaries = [], []
    for r in roster:
        reasons = Counter()
        go = r["go"]
        if r["split"] == "unused":
            reasons["unassigned_workspace_or_unrewarded"] += 1
        elif not go or r["target"] != [go[0]]:
            reasons["no_matching_first_target_and_go"] += 1
        elif len(go) < 2:
            reasons["no_subsequent_go"] += 1
        else:
            for j, event in enumerate(go[1:], 2):
                k = event + 5
                failed = []
                if k - 20 < r["start"]:
                    failed.append("insufficient_history")
                if k + 20 > r["end"]:
                    failed.append("insufficient_future")
                if j < len(go) and go[j] <= k + 20:
                    failed.append("next_go_at_or_before_response_boundary")
                if failed:
                    reasons.update(failed)
                else:
                    windows.append((r, j, k))
        summaries.append(dict(block=r["block"], original=r["original"], split=r["split"],
                              result=r["result"], workspace=r["workspace"], start=r["start"], end=r["end"],
                              fold=r["fold"], go_events=len(go), excluded_reasons=dict(reasons)))
    keys = sorted((r["block"], r["original"], j, k - 5, k, SPLITS[r["split"]]) for r, j, k in windows)
    verify(key_hash(keys) == CONFIG["window_keys_sha256"], "Positive-lag anchor membership changed")
    return windows, summaries


def coordinates(td, selected, cols):
    return np.concatenate((td.markers[selected, cols], td.pos[selected, :2]), axis=1).astype(np.float64)


def has_bad_counts(x):
    return not np.all(np.isfinite(x) & (x >= 0) & (x == np.floor(x)))


def cue_features(rows, go):
    # An event logged in the same bin as a token is not known at its start.
    prior = np.searchsorted(go, rows, side="left")
    seconds = np.zeros(len(rows))
    available = prior > 0
    seconds[available] = (rows[available] - np.asarray(go)[prior[available] - 1]) * 0.01
    return np.column_stack((prior, seconds, available))


def extract(blocks, split, roster, windows, summaries):
    items = [(r, j, k) for r, j, k in windows if r["split"] == split]
    originals = [r for r in roster if r["split"] == split]
    ids = ["block", "original", "ordinal", "k", "workspace", "fold", "donor"]
    sample = defaultdict(list)
    seen = {}
    unit_guides = []
    marker_cols = []
    for td in blocks:
        guide = np.asarray(td.S1_unit_guide)
        cols = np.flatnonzero(guide[:, 1] > 0)
        verify((cols + 1).tolist() == COUNT_COLUMNS and td.S1_spikes.shape[1] == len(guide),
               "Native selected unit columns changed")
        unit_guides.append(guide[cols].astype(int))
        names = list(td.marker_names)
        marker_cols.append([names.index(n) for n in NATIVE_MARKERS])
    verify(all(np.array_equal(g, unit_guides[0]) for g in unit_guides), "Native unit identities differ")
    per_original = {s["original"]: dict(s, candidates=0, eligible=0) for s in summaries if s["split"] == split}
    required = CONFIG["example_block_original_ordinal_k"][split]
    verify([items[0][0]["block"], items[0][0]["original"], items[0][1], items[0][2]] == required,
           "Frozen metadata example changed")
    example = {"split": split, "block_original_ordinal_k": required, "eligible": False}
    qc = []
    for r, j, k in items:
        b, oid = r["block"], r["original"]
        td = blocks[b - 1]
        # k and all reported rows are one-based. Python slice.stop is exclusive.
        coords = coordinates(td, slice(k - 21, k + 9), marker_cols[b - 1])
        counts = td.S1_spikes[k - 21:k + 19, np.asarray(COUNT_COLUMNS) - 1]
        verify(coords.shape == (30, 8) and counts.shape == (40, 23), "Wrong native dimensions")
        reasons = []
        for name, x in (("history", coords[:20]), ("future", coords[20:])):
            for region, subset in (("hand", x[:, :3]), ("elbow", x[:, 3:6]), ("handle", x[:, 6:])):
                if not np.isfinite(subset).all():
                    reasons.append(f"{name}_{region}_nonfinite")
        for name, x in (("history", counts[:20]), ("concurrent", counts[20:30]), ("delayed", counts[30:])):
            if has_bad_counts(x):
                reasons.append(f"{name}_invalid_count")
        accepted = not reasons
        row_index = len(sample["k"]) if accepted else -1
        qc.append(dict(block=b, original=oid, ordinal=j, k=k, eligible=accepted,
                       array_index=row_index, reasons=reasons))
        per_original[oid]["candidates"] += 1
        per_original[oid]["eligible"] += int(accepted)
        if [b, oid, j, k] == required:
            example.update(eligible=accepted, array_index=row_index, reasons=reasons)
        if not accepted:
            continue
        donor = seen.get((b, j), -1)
        if donor >= 0:
            verify(sample["original"][donor] != oid and sample["k"][donor] < r["start"],
                   "Donor must precede the receiving original")
        seen[b, j] = row_index
        for name, value in zip(ids, (b, oid, j, k, r["workspace"], r["fold"], donor), strict=True):
            sample[name].append(value)
        sample["pose"].append(coords[:20])
        sample["movement"].append(coords[20:] - coords[19])
        sample["spikes"].append(counts[:20].astype(np.int64))
        sample["concurrent"].append(counts[20:30].astype(np.int64))
        sample["delayed"].append(counts[30:].astype(np.int64))
        sample["cue"].append(cue_features(np.arange(k - 20, k), r["go"]))
    arrays = {name: np.asarray(sample[name], dtype=np.int64) for name in ids}
    for name, length, fields in (("pose", 20, 8), ("movement", 10, 8), ("spikes", 20, 23),
                                 ("concurrent", 10, 23), ("delayed", 10, 23), ("cue", 20, 3)):
        dtype = np.int64 if name in ("spikes", "concurrent", "delayed") else np.float64
        arrays[name] = np.asarray(sample[name], dtype=dtype).reshape(-1, length, fields)
    arrays["unit_guide"] = unit_guides[0]
    arrays["sorted_columns"] = np.asarray(COUNT_COLUMNS, dtype=int)
    for name in ("original", "block", "start", "end", "fold"):
        arrays[f"roster_{name}"] = np.asarray([r[name] for r in originals], dtype=np.int64)
    for name, start, stop in (("history", -20, 0), ("movement", 0, 10), ("delayed", 10, 20)):
        arrays[f"{name}_rows"] = arrays["k"][:, None] + np.arange(start, stop)[None, :]
    if example["eligible"]:
        i = example["array_index"]
        example.update({name: arrays[name][i].tolist() for name in
                        ("pose", "cue", "spikes", "movement", "concurrent", "delayed")})
        example["unit_guide"] = arrays["unit_guide"].tolist()
    coverage = dict(split=split, roster=len(originals), metadata_eligible_originals=len({r["original"] for r, _, _ in items}),
                    numeric_eligible_originals=len(set(arrays["original"])), candidates=len(items),
                    eligible=len(arrays["k"]), matched_donor=int(np.sum(arrays["donor"] >= 0)),
                    ordinal_before_qc=dict(Counter(j for _, j, _ in items)),
                    ordinal_after_qc=dict(Counter(map(int, arrays["ordinal"]))),
                    qc_reasons_may_overlap=dict(Counter(reason for q in qc for reason in q["reasons"])),
                    member_sha256=CONFIG["member_sha256"], original_qc=list(per_original.values()), window_qc=qc)
    return arrays, coverage, example


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("split", choices=SPLITS)
    p.add_argument("--mat", required=True, type=Path)
    p.add_argument("--output", type=Path, default=HERE)
    p.add_argument("--releases", type=Path, default=HERE.parent / "core")
    args = p.parse_args()
    release = admit(args.split, args.releases)
    verify(args.mat.stat().st_size == CONFIG["member_bytes"] and digest(args.mat) == CONFIG["member_sha256"],
           "Source member checksum or length differs")
    blocks = np.atleast_1d(loadmat(args.mat, squeeze_me=True, struct_as_record=False,
                                   variable_names=["trial_data"])["trial_data"]).ravel()
    roster = metadata(blocks)
    windows, summaries = anchors(roster)
    arrays, coverage, example = extract(blocks, args.split, roster, windows, summaries)
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f"{args.split}.npz"
    atomically(archive, lambda f: np.savez_compressed(f, **arrays))
    coverage.update(npz_sha256=digest(archive), source_seal_sha256=digest(HERE / "source-seal.json"),
                    numerical_release_sha256=release)
    save_json(args.output / f"{args.split}-qc.json", coverage)
    save_json(args.output / f"{args.split}-example.json", example)
    save_json(args.output / "original-metadata.json", summaries)
    print(json.dumps({k: v for k, v in coverage.items() if k not in ("original_qc", "window_qc")}))


if __name__ == "__main__":
    main()
