"""Download fixed public source windows or reproduce the voltage arrays offline."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import csv
from decimal import Decimal
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
from eeglab_header import selected_header

HERE = Path(__file__).resolve().parent
SOURCE_SHA = "e127fff2b81c919ec1a0fdb428659c3c1047e2e75c984200752fd755891c1c53"
CHANNELS = ["Biceps", "SC6", "Thumb", "CP4", "ECG"]
WINDOWS = {"baseline": (-150, -100), "early": (50, 80), "late": (120, 140)}
N = 80
RATE = 10000


def verify(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def immutable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        verify(
            path.read_bytes() == data,
            f"Existing content differs at {path}. Choose a new output directory.",
        )
        return
    with tempfile.NamedTemporaryFile(
        prefix=".acquire-", dir=path.parent, delete=False
    ) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            file.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, value):
    immutable(
        path,
        (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(),
    )


@contextmanager
def exclusive_output(path):
    # OS-level advisory locks are automatically released when the process closes.
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            if path.stat().st_size == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def read_url(url, limit, headers=None, expected_range=None):
    for attempt in range(3):
        try:
            request = Request(
                url, headers={"Accept-Encoding": "identity", **(headers or {})}
            )
            with urlopen(request, timeout=30) as response:
                if expected_range is None:
                    verify(response.status == 200, "Metadata retrieval failed")
                else:
                    verify(
                        response.status == 206
                        and all(
                            response.headers.get(k) == v
                            for k, v in expected_range.items()
                        ),
                        "Version, ETag, range, or length mismatch",
                    )
                data = response.read(limit + 1)
                verify(len(data) <= limit, "Exceeded bounded response length")
                return data
        except (
            TimeoutError,
            ConnectionError,
            http.client.IncompleteRead,
            URLError,
        ) as exc:
            # HTTP status and identity errors are definitive. Only transient I/O may retry.
            if getattr(exc, "code", None) is not None or attempt == 2:
                raise
            time.sleep(2**attempt)


def meta_file(out, record, name, offline):
    item = record["sidecars_and_pointers"][name]
    path = out / "metadata" / record["subject"] / name
    if path.exists():
        body = path.read_bytes()
    else:
        verify(not offline, "Offline metadata missing: " + name)
        body = read_url(item["url"], item["bytes"])
        verify(sha(body) == item["sha256"], "Publisher metadata hash mismatch: " + name)
        immutable(path, body)
    verify(
        len(body) == item["bytes"] and sha(body) == item["sha256"],
        "Metadata mismatch: " + name,
    )
    git_hash = hashlib.sha1(
        b"blob " + str(len(body)).encode() + b"\0" + body
    ).hexdigest()
    verify(git_hash == item["git_blob"], "Snapshot blob differs: " + name)
    return body


def verify_remote_version(out, record, ext, obj, offline):
    path = (
        out
        / "metadata"
        / record["subject"]
        / (Path(record["stem"]).name + "eeg." + ext + ".log.rmet")
    )
    if path.exists():
        body = path.read_bytes()
    else:
        verify(not offline, "Offline version binding missing: " + path.name)
        body = read_url(obj["rmet_url"], 16384)
        verify(sha(body) == obj["rmet_sha256"], "Published version binding changed")
        immutable(path, body)
    expected = "+" + obj["version"] + "#ds004388/" + record["stem"] + "eeg." + ext
    verify(
        sha(body) == obj["rmet_sha256"] and expected in body.decode("ascii").split(),
        "Stored object version differs from the public annex key binding",
    )


def read_range(obj, start, stop, directory, offline):
    count = stop - start + 1
    verify(0 <= start <= stop < obj["bytes"], "Out-of-bounds range")
    key = directory / f"{start}-{stop}"
    raw = key.with_suffix(".bin")
    sidecar = key.with_suffix(".json")
    base = {
        "start_byte": start,
        "end_byte_inclusive": stop,
        "bytes": count,
        "version": obj["version"],
        "etag": obj["etag"],
        "url": obj["url"],
        "object_bytes": obj["bytes"],
        "publisher_whole_sha256": obj["publisher_whole_file_sha256"],
    }
    if sidecar.exists():
        data = raw.read_bytes()
        receipt = json.loads(sidecar.read_bytes())
        verify(
            receipt == dict(base, sha256=sha(data)) and len(data) == count,
            "Cached slice or identity mismatch",
        )
        return data, receipt
    verify(not offline, "Offline range missing: " + str(key))
    headers = {"Range": f"bytes={start}-{stop}", "If-Match": obj["etag"]}
    checks = {
        "Content-Range": f"bytes {start}-{stop}/{obj['bytes']}",
        "Content-Length": str(count),
        "ETag": obj["etag"],
        "x-amz-version-id": obj["version"],
    }
    data = read_url(obj["url"], count, headers, checks)
    verify(len(data) == count, "Truncated range")
    receipt = dict(base, sha256=sha(data))
    immutable(raw, data)
    write_json(sidecar, receipt)
    return data, receipt


def parse(body):
    return list(csv.DictReader(body.decode("utf-8").splitlines(), delimiter="\t"))


def extract(record, out, offline, workers, snapshot):
    sid = record["subject"]
    stem = Path(record["stem"]).name
    objects = record["objects"]
    folder = out / "ranges" / sid
    files = {
        name: meta_file(out, record, name, offline)
        for name in record["sidecars_and_pointers"]
    }
    rows = parse(files[stem + "events.tsv"])
    channels = parse(files[stem + "channels.tsv"])
    run = json.loads(files[stem + "eeg.json"])
    labels = [r["name"] for r in channels]
    indices = [labels.index(name) for name in CHANNELS]
    for ext, obj in objects.items():
        verify_remote_version(out, record, ext, obj, offline)
        pointer = files[stem + "eeg." + ext].decode("ascii").strip().split("/")[-1]
        verify(
            pointer
            == obj["annex_key"]
            == f"SHA256E-s{obj['bytes']}--{obj['publisher_whole_file_sha256']}.{ext}",
            "Incorrect annex identity",
        )
    header_receipts = []

    def fetch_header(start, stop):
        verify(
            sum(r["bytes"] for r in header_receipts) + stop - start + 1 <= 1_000_000,
            "Excessive header request",
        )
        data, receipt = read_range(objects["set"], start, stop, folder / "set", offline)
        header_receipts.append(receipt)
        return data

    header = selected_header(fetch_header, objects["set"]["bytes"], len(rows) + 1)
    native = header.pop("first_events")
    verify(
        header["channel_order"] == labels
        and header["nbchan"] == len(labels) == len(set(labels)),
        "Native channel order differs",
    )
    verify(
        all(channels[i]["units"] == "microV" for i in indices)
        and record["expected_columns"] == CHANNELS,
        "Calibrated channel order mismatch",
    )
    verify(
        header["external_data_file"] == stem + "eeg.fdt"
        and header["trials"] == 1
        and header["xmin"] == 0
        and header["srate"] == run["SamplingFrequency"] == RATE,
        "Continuous frame clock/origin mismatch",
    )
    verify(
        run["TaskName"] == "median"
        and run["RecordingType"] == "continuous"
        and Decimal(str(run["RecordingDuration"])) * RATE == header["pnts"],
        "Run or duration mismatch",
    )
    frame = len(labels) * 4
    verify(
        frame * header["pnts"] == objects["fdt"]["bytes"], "Unexpected float32 layout"
    )
    verify(len(rows) == len(native), "Incomplete native event list")
    previous = -1
    samples = []
    selected_rows = []
    for index, (row, event) in enumerate(zip(rows, native)):
        s = Decimal(row["sample"])
        verify(
            s == int(s) == Decimal(row["onset"]) * RATE == event["latency"] - 1
            and event["type"] == row["value"]
            and previous < s < header["pnts"],
            "Native/BIDS event mismatch",
        )
        previous = int(s)
        if (
            row["trial_type"] == "stimulus"
            and row["value"] == "Median - Stimulation"
            and len(samples) < N
        ):
            samples.append(int(s))
            selected_rows.append(index)
    verify(len(samples) == N, "Insufficient eligible events")
    plan = [
        (i, w, (s + lo) * frame, (s + hi) * frame - 1, hi - lo)
        for i, s in enumerate(samples)
        for w, (lo, hi) in WINDOWS.items()
    ]
    verify(
        sum(b - a + 1 for _, _, a, b, _ in plan) == N * 100 * frame
        and all(a[3] < b[2] for a, b in zip(plan, plan[1:])),
        "Overlapping or excessive requests",
    )
    arrays = {
        w: np.empty((N, b - a, len(indices)), dtype="<f4")
        for w, (a, b) in WINDOWS.items()
    }
    receipts = []

    def fetch(plan_row):
        i, w, a, b, steps = plan_row
        data, rec = read_range(objects["fdt"], a, b, folder / "fdt", offline)
        values = np.frombuffer(data, dtype="<f4").reshape(steps, len(labels))[
            :, indices
        ]
        verify(np.isfinite(values).all(), "Nonfinite measurement")
        return i, w, values, dict(rec, event_index=i, event_sample=samples[i], window=w)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for begin in range(0, len(plan), workers * 2):
            for i, w, values, receipt in pool.map(
                fetch, plan[begin : begin + workers * 2]
            ):
                arrays[w][i] = values
                receipts.append(receipt)
    arrays["event_samples"] = np.asarray(samples, dtype="<i8")
    buffer = io.BytesIO()
    np.savez(buffer, **arrays)
    package = buffer.getvalue()
    verify(
        sha(package) == record["npz_sha256"],
        "Output bytes differ from the frozen reference",
    )
    name = record["group"] + "-" + sid + ".npz"
    immutable(out / name, package)
    result = {
        "subject": sid,
        "snapshot": snapshot,
        "selected_rows_zero_based": selected_rows,
        "stem": record["stem"],
        "source_identity_sha256": SOURCE_SHA,
        "channel_names": CHANNELS,
        "channels": [dict(channels[i], index_zero_based=i) for i in indices],
        "event_samples": samples,
        "native_bids_event_rows_verified": len(rows),
        "header": header,
        "acquisition_reference": run["EEGReference"],
        "intervals_samples_half_open": WINDOWS,
        "output": name,
        "output_sha256": sha(package),
        "header_ranges": header_receipts,
        "signal_ranges": receipts,
        "whole_binary_hash_verified_locally": False,
    }
    write_json(out / (sid + "-receipt.json"), result)
    return name, sha(package)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True, choices=("development", "assessment"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--participant", help="One donor code from the selected group")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=6)
    args = parser.parse_args()
    manifest = (HERE / "sources.json").read_bytes()
    verify(sha(manifest) == SOURCE_SHA, "Manifest hash differs")
    identity = json.loads(manifest)
    records = [
        r
        for r in identity["records"]
        if r["group"] == args.group and args.participant in (None, r["subject"])
    ]
    verify(records, "No matching participant in this group")
    args.output.mkdir(parents=True, exist_ok=True)
    with exclusive_output(args.output / ".acquisition.lock"):
        for record in records:
            print(
                *extract(
                    record,
                    args.output,
                    args.offline,
                    args.workers,
                    identity["snapshot"],
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
