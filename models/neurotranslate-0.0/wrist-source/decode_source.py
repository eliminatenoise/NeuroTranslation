"""Read the publisher’s EDF channels, cue ticks and paired encoder words."""
import csv
import hashlib
import io
import re
import numpy as np

EEG = ("C3", "C1", "Cz", "C2", "C4", "CP3", "CPz", "CP4")
EMG = ("M1L", "M1R", "M2L", "M2R", "M3L", "M3R", "M4L", "M4R")
MARKERS = ("TrialInitStamp", "AllTargetShowSta", "TrialInitMovStam",
           "CurrentTarget", "TrialEndMovStamp", "XCoordinates", "YCoordinates")
EDF_LABELS = tuple(f"Ch{channel}" for channel in range(1, 17)) + MARKERS
SAMPLE_RATE = 512
FRAME_TICKS = 8
TRIALS_PER_BLOCK = 40
TASK_RUN_IDS = tuple(f"{run:02d}" for run in range(3, 11))


def sha256_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_dictionary(archive, path):
    raw = archive.read(path)
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter="\t"))


def archive_run_ids(archive, pid):
    eeg_pattern = re.compile(rf"{pid}/eeg/{pid}_task-WristPointingTask_run-(\d\d)_eeg\.edf")
    motion_pattern = re.compile(
        rf"{pid}/motion/{pid}_task-WristPointingTask_tracksys-BiomechWrist_run-(\d\d)_motion\.tsv"
    )
    members = archive.namelist()
    if len(members) != len(set(members)):
        raise ValueError(f"{pid}: duplicate archive member")
    eeg_runs = {match[1] for name in members if (match := eeg_pattern.fullmatch(name))}
    motion_runs = {match[1] for name in members if (match := motion_pattern.fullmatch(name))}
    published_layout = {"01", "11", *TASK_RUN_IDS}
    if eeg_runs != motion_runs or not {"01", "11"} <= eeg_runs or not eeg_runs <= published_layout:
        raise ValueError(f"{pid}: cannot identify task blocks flanked by rest: {eeg_runs=} {motion_runs=}")
    return eeg_runs


def decode_edf(raw):
    if raw[:8] != b"0       ":
        raise ValueError("Unexpected EEG recording file signature")
    header = int(raw[184:192])
    records = int(raw[236:244])
    seconds = float(raw[244:252])
    channel_count = int(raw[252:256])
    if (header, channel_count, seconds) != (6144, len(EDF_LABELS), FRAME_TICKS / SAMPLE_RATE):
        raise ValueError("EDF fixed metadata changed")
    if not 25_000 <= records <= 26_000:
        raise ValueError("EDF record count disagrees with the documented task duration")
    if len(raw) != header + records * channel_count * FRAME_TICKS * 2:
        raise ValueError("EDF payload bytes disagree with the independently checked frame size")
    sections = {}
    offset = 256
    for field, width in (
        ("label", 16), ("transducer", 80), ("unit", 8), ("physical_min", 8),
        ("physical_max", 8), ("digital_min", 8), ("digital_max", 8),
        ("prefilter", 80), ("record_samples", 8), ("reserved", 32),
    ):
        sections[field] = tuple(
            raw[start:start + width].strip() for start in range(offset, offset + width * channel_count, width)
        )
        offset += width * channel_count
    if tuple(label.decode("ascii") for label in sections["label"]) != EDF_LABELS:
        raise ValueError("EDF electrode/channel identity, marker identity or order changed")
    if sections["unit"][:16] != (b"uV",) * 16 or sections["unit"][16:] != (b"",) * 7:
        raise ValueError("EDF physical signal or state units changed")
    if any(sections[f"{domain}_{limit}"][:16] != (value,) * 16
           for domain in ("physical", "digital")
           for limit, value in (("min", b"-32768"), ("max", b"32767"))):
        raise ValueError("EDF bioelectric calibration changed")
    if sections["physical_min"][16:] != (b"0",) * 7 or sections["digital_min"][16:] != (b"0",) * 7:
        raise ValueError("EDF state lower ranges changed")
    if sections["physical_max"][16:] != (b"255",) * 5 + (b"32767",) * 2:
        raise ValueError("EDF state upper ranges changed")
    if sections["digital_max"][16:] != sections["physical_max"][16:]:
        raise ValueError("EDF state header physical/digital declarations disagree")
    if sections["prefilter"][:16] != (b"HP:0.1LP:200N:60",) * 16:
        raise ValueError("EDF hardware filter declarations changed")
    # The producer repeats the frame-count token within each fixed-width field.
    # Common frame size above is constrained by file length, run duration, channel
    # count, footer-free EDF layout, ordered marker roles and exact TSV parity.
    repeated_samples_field = sum(len(field.split()) > 1 for field in sections["record_samples"])
    if not repeated_samples_field and sections["record_samples"] != (b"8",) * channel_count:
        raise ValueError("Unknown EDF frame-count encoding")
    signals = np.frombuffer(raw, dtype="<i2", offset=header)
    return signals.reshape(records, channel_count, FRAME_TICKS).transpose(0, 2, 1).reshape(-1, channel_count), {
        "source_records": records, "frame_ticks": FRAME_TICKS,
        "header_bytes": header, "header_sha256": hashlib.sha256(raw[:header]).hexdigest(),
        "repeated_samples_header_fields": repeated_samples_field,
    }


def marker_ticks(pulses):
    if np.any((pulses != 0) & (pulses != 1)):
        raise ValueError("Unexpected non-binary state in source marker channel")
    return np.flatnonzero(pulses.astype(bool) & np.r_[True, pulses[:-1] == 0])


def trial_ticks(signal):
    starts = marker_ticks(signal[:, 16])
    all_targets = marker_ticks(signal[:, 17])
    cues = marker_ticks(signal[:, 18])
    returns = marker_ticks(signal[:, 20])
    if len(starts) not in (TRIALS_PER_BLOCK, TRIALS_PER_BLOCK + 1) or any(
        len(series) != TRIALS_PER_BLOCK for series in (all_targets, cues, returns)
    ):
        raise ValueError("Wrong count of stored source trial and movement markers")
    first = starts[:TRIALS_PER_BLOCK]
    stop = np.r_[starts[1:], len(signal)][:TRIALS_PER_BLOCK]
    if not np.all((first < all_targets) & (all_targets < cues) & (cues < returns) & (returns < stop)):
        raise ValueError("Stored source marker order is inconsistent")
    if not np.all(returns - cues > 1024):
        raise ValueError("Prespecified forecast support extends past the source movement interval")
    return first, cues, returns


def coordinate_data(motion, signal):
    raw_signed = np.loadtxt(io.BytesIO(motion), dtype=np.int32, delimiter="\t", ndmin=2)
    if raw_signed.shape != (len(signal), 2) or np.any(raw_signed < 0) or np.any(raw_signed > 65535):
        raise ValueError("Motion TSV shape or unsigned 16-bit word range disagrees with timed source")
    counts = raw_signed.astype("<u2")
    if not np.array_equal(counts, signal[:, 21:23].view("<u2")):
        raise ValueError("Motion TSV and EDF auxiliary states differ in the same stored row")
    angle_deg = (counts.astype(np.float64) * (25.0 / 65535.0) - 12.5) * (180.0 / np.pi)
    angle_deg[:, 1] *= -1.0
    # A raw zero is a missing sentinel, not a device-neutral reading. No
    # participant-specific normal range is applied to nonzero positions.
    valid = (counts != 0) & (np.abs(angle_deg) <= 180.0)
    angle_deg[~valid] = np.nan
    return counts, angle_deg, valid


