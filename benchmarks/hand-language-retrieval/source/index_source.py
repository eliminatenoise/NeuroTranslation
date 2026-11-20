"""Index only the deterministic TAR headers and permitted annotation records."""

import hashlib
import json
from pathlib import Path
import re
import tarfile
import time
import requests

HERE = Path(__file__).resolve().parent
BASE = "https://hl2data.z5.web.core.windows.net/holoassist-data-release/"
HANDS = BASE + "hands.tar"
LABELS = BASE + "data-annotation-trainval-v1_1.json"
OBJECTS = {
    HANDS: ('"0x8DC8C9DE150FE51"', 235404984320),
    LABELS: ('"0x8DC8C9D769BBF54"', 117011015),
}
SPLIT = json.loads((HERE / "SPLIT.json").read_text())
SELECTED = {
    r["recording"]: r for r in SPLIT["recordings"] if r["role"] in ("train", "review")
}
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def get(s, url, offset, length, stream=False):
    etag, total = OBJECTS[url]
    r = s.get(
        url,
        headers={
            "Accept-Encoding": "identity",
            "If-Match": etag,
            "Range": f"bytes={offset}-{offset + length - 1}",
        },
        timeout=(10, 60),
        stream=stream,
    )
    if (r.status_code, r.headers.get("Content-Range"), r.headers.get("ETag")) != (
        206,
        f"bytes {offset}-{offset + length - 1}/{total}",
        etag,
    ):
        raise ValueError(
            (r.status_code, r.headers.get("Content-Range"), r.headers.get("ETag"))
        )
    return r


def index_hands():
    seen = set()
    pos = 0
    start = time.monotonic()
    with (
        requests.Session() as session,
        (HERE / "tar-headers.jsonl").open("w", buffering=1) as out,
    ):
        while seen != set(SELECTED):
            # The first header at each bundle is a one-block PAX metadata record. Reading its 512-byte
            # header only first protects even unexpected layouts from accidental payload access.
            h = get(session, HANDS, pos, 512).content
            pax = tarfile.TarInfo.frombuf(h, "utf8", "strict")
            if pax.type != tarfile.XHDTYPE or pax.size > 512:
                raise ValueError(("unexpected layout", pos, pax.name, pax.size))
            off = pos + 1024
            h = get(session, HANDS, off, 512).content
            info = tarfile.TarInfo.frombuf(h, "utf8", "strict")
            rec = info.name.split("/")[0]
            if rec.startswith("R") and any(
                rec.startswith(r["group"] + "-")
                for r in SPLIT["recordings"]
                if r["role"] == "reserve"
            ):
                raise ValueError(
                    "Reached reserve metadata without finding development set"
                )
            if rec in SELECTED and info.name == rec + "/Export_py/Hands/Right_sync.txt":
                row = dict(
                    recording=rec,
                    name=info.name,
                    offset=off + 512,
                    length=info.size,
                    header_sha256=sha(h),
                    source=HANDS,
                    etag=OBJECTS[HANDS][0],
                )
                print(json.dumps(row), file=out)
                print(
                    "indexed",
                    len(seen) + 1,
                    rec,
                    info.size,
                    round(time.monotonic() - start, 1),
                    flush=True,
                )
                seen.add(rec)
            pos = off + 512 + (info.size + 511) // 512 * 512


def precise_duration(raw):
    hours, minutes, seconds = raw.split(":")
    return 3600 * int(hours) + 60 * int(minutes) + float(seconds)


def export_annotation(record, rec):
    events = []
    for event in record["events"]:
        if event["label"] == "Coarse grained action":
            attr = event["attributes"]
            events.append(
                {
                    "id": event["id"],
                    "start": event["start"],
                    "end": event["end"],
                    "text": attr["Action sentence"],
                    "verb": attr.get("Verb"),
                    "noun": attr.get("Noun"),
                }
            )
    dest = HERE / SELECTED[rec]["role"]
    dest.mkdir(exist_ok=True)
    duration = record["videoMetadata"]["duration"]
    result = dict(
        SELECTED[rec],
        task_type=record["taskType"],
        duration_s=precise_duration(duration["raw"]),
        source_duration_info=duration,
        events=events,
    )
    file = dest / (rec + ".json")
    encoded = json.dumps(result, indent=2) + "\n"
    if file.is_file() and file.read_text() == encoded:
        return
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", dir=dest, delete=False) as temp:
        temp.write(encoded)
    Path(temp.name).replace(file)


def rebuild_labels():
    with requests.Session() as session:
        rows = [
            json.loads(line)
            for line in (HERE / "annotation-ranges.jsonl").read_text().splitlines()
        ]
        if len(rows) != len(SELECTED) or {r["recording"] for r in rows} != set(
            SELECTED
        ):
            raise ValueError("Unexpected annotation index")
        for r in rows:
            raw = get(session, LABELS, r["start"], r["length"]).content
            if sha(raw) != r["sha256"]:
                raise ValueError("Source record changed")
            record = json.loads(raw)
            if record["video_name"] != r["recording"]:
                raise ValueError("Source recording differs")
            export_annotation(record, record["video_name"])


def labels():
    # Exact source layout: top-level objects indented four spaces. Video accession is the
    # last flat field in each record. Identify only names until a selected named slice is known.
    raw = b""
    offset = 0
    seen = set()
    header = re.compile(rb"(?m)^    \{\r?$")
    session = requests.Session()
    with (HERE / "annotation-ranges.jsonl").open("w") as out:
        while seen != set(SELECTED):
            block = 262144
            if offset + len(raw) > 20 * 1024**2:
                raise ValueError("Bounded prefix exhausted")
            raw += get(session, LABELS, offset + len(raw), block).content
            starts = list(header.finditer(raw))
            for a, b in zip(starts, starts[1:]):
                chunk = raw[a.start() : b.start()].rstrip().rstrip(b",").rstrip()
                match = re.search(rb'"video_name":\s*"([^"]+)"', chunk)
                if not match:
                    raise ValueError("Record accession missing")
                rec = match[1].decode()
                if rec not in SELECTED:
                    continue
                record = json.loads(chunk)
                assert record["video_name"] == rec
                export_annotation(record, rec)
                print(
                    json.dumps(
                        dict(
                            recording=rec,
                            start=offset + a.start(),
                            length=len(chunk),
                            sha256=sha(chunk),
                            source=LABELS,
                            etag=OBJECTS[LABELS][0],
                        )
                    ),
                    file=out,
                )
                seen.add(rec)
            if starts:
                offset += starts[-1].start()
                raw = raw[starts[-1].start() :]
    print("labels", len(seen), "bounded prefix", offset + len(raw), flush=True)


if __name__ == "__main__":
    import sys

    {"hands": index_hands, "index-labels": labels, "labels": rebuild_labels}[
        sys.argv[1]
    ]()
