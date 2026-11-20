"""Prepare only the six source archives identified by study.json. No downloading."""
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np

from common import PEOPLE, RESULT, ROWS, SOURCE, digest, read_npz, seal
import decode_source as src
from features import OFFSETS, collect_rows


def table_digest(digest_state, table):
    for key in sorted(table):
        value = np.ascontiguousarray(table[key].astype(table[key].dtype.newbyteorder("<"), copy=False))
        header = json.dumps([key, value.dtype.str, value.shape], separators=(",", ":")).encode()
        digest_state.update(len(header).to_bytes(4, "little"))
        digest_state.update(header)
        digest_state.update(value.tobytes())


def decode_one(path, record, person):
    pid = PEOPLE[person]
    if path.name != record["file"] or path.stat().st_size != record["bytes"] or digest(path) != record["sha256"]:
        raise ValueError("Source archive differs from the specified public release")
    pieces = []
    with zipfile.ZipFile(path) as archive:
        stem = f"{pid}_task-WristPointingTask"
        channels = src.read_dictionary(archive, f"{pid}/eeg/{stem}_channels.tsv")
        if [(r["name"], r["type"], r["units"]) for r in channels] != [
            *((k, "EEG", "microV") for k in src.EEG), *((k, "EMG", "microV") for k in src.EMG)]:
            raise ValueError("Electrode identity or units differ")
        motion = src.read_dictionary(archive, f"{pid}/motion/{stem}_tracksys-BiomechWrist_channels.tsv")
        if [(r["name"], r["tracked_point"], r["units"]) for r in motion] != [
            ("X", "RightWrist", "rad"), ("Y", "RightWrist", "rad")]:
            raise ValueError("Wrist encoder metadata differs")
        available = src.archive_run_ids(archive, pid)
        expected = set(src.TASK_RUN_IDS)
        if pid == "sub-17":
            expected.remove("03")
        if available - {"01","11"} != expected:
            raise ValueError("Expected task run missing or unexpected run present")
        for block, run in enumerate(src.TASK_RUN_IDS, 1):
            if run not in expected:
                continue
            signal, _ = src.decode_edf(archive.read(f"{pid}/eeg/{stem}_run-{run}_eeg.edf"))
            _, cues, returns = src.trial_ticks(signal)
            motion_name = f"{pid}/motion/{stem}_tracksys-BiomechWrist_run-{run}_motion.tsv"
            _, angle, valid = src.coordinate_data(archive.read(motion_name), signal)
            r, _ = collect_rows(signal[:, :8], signal[:, 8:16], angle, valid, cues, returns, person, block)
            ids = cues[r.trial] + OFFSETS[r.slot]
            if not (np.array_equal(r.target, angle[ids]) and np.array_equal(r.anchor, angle[ids-128])):
                raise ValueError("Source encoder lookup failed")
            d = {k: getattr(r, k) for k in ("person","block","trial","slot","anchor","past","target")}
            d.update(cue=cues[r.trial], target_tick=ids, bins=r.bins[:, :, :6],
                     parent=np.full(len(ids), f"{pid}/run-{run}", dtype="U32"))
            pieces.append(d)
    return {k: np.concatenate([d[k] for d in pieces]) for k in pieces[0]}


def prepare(archives):
    source = json.loads(SOURCE.read_text())
    hashes = {}
    merged = hashlib.sha256()
    totals = 0
    for i, rec in enumerate(source["archives"]):
        d = decode_one(Path(archives) / rec["file"], rec, i)
        table_digest(merged, d)
        totals += len(d["slot"])
        target = ROWS / (PEOPLE[i] + ".npz")
        if target.exists():
            old = read_npz(target)
            if set(old) != set(d) or any(not np.array_equal(v, old[k]) for k,v in d.items()):
                raise ValueError("Existing prepared data differs")
        else:
            seal(target, d, archive=True)
        hashes[target.name] = digest(target)
    if totals != 11274 or merged.hexdigest() != source["combined_training_table_sha256"]:
        raise ValueError("Reconstructed training table differs from the original")
    receipt = {"freeze_sha256": digest(SOURCE), "outputs": hashes, "rows": totals,
               "table_sha256": merged.hexdigest()}
    out = RESULT / "extraction.json"
    if out.exists():
        if json.loads(out.read_text()) != receipt:
            raise ValueError("Existing extraction receipt differs")
    else:
        seal(out, receipt)
    print(f"Matched all {totals:,} recorded target windows.")
