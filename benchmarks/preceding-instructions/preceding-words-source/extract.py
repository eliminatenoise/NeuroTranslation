"""Project exact public annotation byte ranges into fixed-vocabulary presence features.

No unredacted transcription is logged, saved, hashed individually or returned.
The public source already has exact whole-record SHA-256 digests.
"""
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import requests


HERE = Path(__file__).resolve().parent
COHORT_SHA = "873e7081ff0ff309cd5b8ffc8f7d6bc900fa56c090f3e2ee90aa57a142493b6d"
RESOURCE = "https://hl2data.z5.web.core.windows.net/holoassist-data-release/data-annotation-trainval-v1_1.json"
TOTAL = 117011015
ETAG = '"0x8DC8C9D769BBF54"'
PURPOSE = {
    "instructor start conversation describing high level instruction",
    "instructor start conversation follow up instruction",
    "instructor reply to task performer follow up instruction",
}
GRADE = {"none": "unrated", "high confidence": "explicit-high", "high confidence transcription": "explicit-high"}
INCOMPLETE = re.compile(
    r"[\[\]<>*{}]|\b(?:unintelligible|indistinct|inaudible|incomprehensible|unclear|redacted|crosstalk|untranscribed|unheard|unrecognized|incoherent|unidentified)\b",
    re.IGNORECASE,
)
EMPTY = {"none", "null", "n a", "na", "unknown", "no speech", "no transcription", "silence", "blank", "inaudible", "unintelligible"}


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower())) if text is not None else ""


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def contiguous_record(session, meta):
    assert meta["source"] == RESOURCE and meta["etag"] == ETAG
    first, count = meta["start"], meta["length"]
    last = first + count - 1
    with session.get(RESOURCE, headers={"Accept-Encoding": "identity", "If-Match": ETAG,
                                        "Range": f"bytes={first}-{last}"}, timeout=(10, 40), stream=True) as response:
        actual = (response.status_code, response.headers["Content-Range"], response.headers["ETag"])
        if actual != (206, f"bytes {first}-{last}/{TOTAL}", ETAG):
            raise ValueError(("Range identity mismatch", meta["recording"], actual))
        raw = response.raw.read(count + 1)
    if len(raw) != count or sha(raw) != meta["sha256"]:
        raise ValueError(("Record checksum mismatch", meta["recording"]))
    return json.loads(raw)


def duration(value):
    hours, minutes, seconds = value.split(":")
    return 3600 * int(hours) + 60 * int(minutes) + float(seconds)


def valid_time(value):
    return type(value) in (float, int) and math.isfinite(value)


def classify(attr):
    purpose = attr.get("Conversation Purpose")
    if normalize(purpose) not in PURPOSE:
        return "other-purpose"
    grade = normalize(attr.get("Transcription Confidence"))
    if grade not in GRADE:
        return "excluded-confidence"
    words = attr.get("Transcription")
    if not isinstance(words, str) or not re.search(r"[a-z]", words, flags=re.I):
        return "blank-or-nontext"
    if normalize(words) in EMPTY or INCOMPLETE.search(words):
        return "uncertain-or-placeholder"
    return "admitted"


def lexical_projection(words, allow):
    # Boundaries keep digit-adjacent strings or local parts from becoming model terms.
    words = re.sub(r"\S+(?:@|://)\S+", " ", words)
    literal = re.findall(r"(?<![\w])[a-z]+(?![\w])", words.lower())
    return sorted(allow.intersection(literal))


def export_record(meta, full, allow):
    rec = meta["recording"]
    assert full["video_name"] == rec
    dur = duration(full["videoMetadata"]["duration"]["raw"])
    status_keys = [k for k in ("status", "state") if k in full]
    counts = collections.Counter()
    roles = collections.Counter()
    grades = collections.Counter()
    statuses = collections.Counter()
    kept = []
    turns = []
    keys = set()
    for event in full["events"]:
        if event["label"] != "Conversation":
            continue
        counts["conversation"] += 1
        attr = event["attributes"]
        role = normalize(attr.get("Conversation Purpose"))
        # Only pre-approved canonical role text is propagated; no unexpected string escapes.
        roles[role if role in PURPOSE else "other-or-missing"] += 1
        grade = normalize(attr.get("Transcription Confidence"))
        grade_label = grade if grade in (*GRADE, "low confidence", "low confidence transcription") else "other-or-missing"
        grades[grade_label] += 1
        if role in PURPOSE:
            counts["instructor-instruction-purpose"] += 1
            counts["instruction-confidence:" + grade_label] += 1
        status = [f"{layer}-{k}-present" for layer, obj in (("event", event), ("attribute", attr)) for k in ("state", "status") if k in obj]
        statuses["+".join(status) or "no-separate-event-or-attribute-status-field"] += 1
        a, b, idx = event.get("start"), event.get("end"), event.get("id")
        assert type(idx) is int and idx not in keys, ("invalid-or-duplicate-event-id", rec)
        keys.add(idx)
        clock_ok = event.get("type") == "range" and valid_time(a) and valid_time(b) and 0 <= a < b <= dur
        if clock_ok:
            turns.append(dict(recording=rec, id=idx, start=a, end=b))
        reason = classify(attr)
        if reason == "admitted" and not clock_ok:
            reason = "invalid-annotated-range"
        if reason == "admitted" and (status or status_keys):
            # No unknown or unqualified QA flags silently turn into source evidence.
            reason = "unqualified-status-field"
        counts[reason] += 1
        if reason != "admitted":
            continue
        safe = lexical_projection(attr["Transcription"], allow)
        if not safe:
            counts["admitted-without-allowlisted-word"] += 1
        st = GRADE[grade]
        counts["admitted-confidence:" + st] += 1
        kept.append(dict(recording=rec, group=meta["group"], task=meta["task"], id=idx,
                         start=a, end=b, duration_s=b-a, purpose=attr["Conversation Purpose"],
                         confidence=attr["Transcription Confidence"], confidence_status=st, tokens=safe))
    return sorted(kept, key=lambda r: (r["end"], r["start"], r["id"])), turns, {
        "duration_s": dur, "record_status_fields":status_keys, "event_status_presence_counts": dict(statuses),
        "counts": dict(counts), "conversation_confidences": dict(grades), "conversation_purposes":dict(roles),
    }


def encoded_lines(rows):
    return "".join(json.dumps(r, sort_keys=True, allow_nan=False) + "\n" for r in rows).encode()


def write_bound(name, raw):
    file = HERE / name
    if file.is_file():
        if file.read_bytes() != raw:
            raise ValueError(f"Frozen output mismatch: {name}")
        return
    with tempfile.NamedTemporaryFile(dir=HERE, delete=False) as temp:
        temp.write(raw)
    os.replace(temp.name, file)


def main():
    start = time.monotonic()
    raw = (HERE / "COHORT.json").read_bytes()
    assert sha(raw) == COHORT_SHA
    cohort = json.loads(raw)
    allowed = set(cohort["allowlist"])
    events, times, receipt = [], [], []
    with requests.Session() as session:
        for rec in cohort["recordings"]:
            row = rec["annotation"]
            full = contiguous_record(session, row)
            admitted, turns, summary = export_record(rec, full, allowed)
            events.extend(admitted)
            times.extend(turns)
            receipt.append(dict(recording=rec["recording"], source=row, verified_http_status=206,
                                verified_reply_etag=ETAG, verified_total_size=TOTAL, **summary))
    sums = collections.Counter()
    for row in receipt:
        sums.update(row["counts"])
    s = {
        "source_cohort_sha256": COHORT_SHA, "input_bytes":sum(r["annotation"]["length"] for r in cohort["recordings"]),
        "recordings":len(receipt), "groups":len({r["group"] for r in cohort["recordings"]}),
        "recordings_with_admissible_instruction":len({r["recording"] for r in events}),
        "groups_with_admissible_instruction":len({r["group"] for r in events}),
        "events": dict(sums), "unique_emitted_terms":len({w for r in events for w in r["tokens"]}),
    }
    write_bound("events.jsonl", encoded_lines(events))
    write_bound("conversation-times.jsonl", encoded_lines(times))
    write_bound("receipts.jsonl", encoded_lines(receipt))
    write_bound("COUNTS.json", (json.dumps(s, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps(dict(elapsed_s=time.monotonic()-start, **s), sort_keys=True))


if __name__ == "__main__":
    main()
