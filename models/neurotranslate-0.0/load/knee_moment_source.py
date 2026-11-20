"""Read the continuous Reznick walking segment and select an offline knee moment target."""

from dataclasses import dataclass
from hashlib import file_digest
import json
from pathlib import Path

import h5py
import numpy as np


SCHEMA = json.loads(Path(__file__).with_name("knee_moment_schema.json").read_text())
TARGET_LEAD = 25


def verify_archive(path):
    """Verify the full archive before using it, once per run."""
    path = Path(path)
    expected = SCHEMA["archive"]
    if path.stat().st_size != expected["bytes"]:
        raise ValueError("Unexpected archive size")
    with path.open("rb") as source:
        actual = file_digest(source, "sha256").hexdigest()
    if actual != expected["sha256"]:
        raise ValueError("Unexpected archive digest")
    return actual


@dataclass(frozen=True)
class Trial:
    person: str
    first_source_frame: int
    angles: np.ndarray
    moments: np.ndarray | None


def load_trial(archive: h5py.File, person: str, *, include_moments=False) -> Trial:
    """Return time × channels. Moments are opt-in for training or frozen evaluation."""
    row = SCHEMA["participants"][person]
    start, stop = row["zero_based_half_open"]
    trial = archive[SCHEMA["trial"].format(person=person)]
    events = trial["events"]
    labels = [
        "".join(map(chr, archive[r][...].ravel())) for r in events["tasks"][...].ravel()
    ]
    wanted = SCHEMA["task_label"]
    if labels.count(wanted) != 1:
        raise ValueError(f"{person}: expected one {wanted} interval")
    bounds = events["cutPoints"][:, labels.index(wanted)]
    if not np.array_equal(bounds, row["native_event_bounds"]):
        raise ValueError(f"{person}: task bounds do not match the selected release")
    if [start, stop] != [bounds[0] + 1, bounds[1] - 1]:
        raise ValueError(f"{person}: inconsistent stored selection")
    expected_shape = (3, row["full_trial_samples"])

    def channels(group):
        selected = []
        for name in SCHEMA[group]["fields"]:
            field = trial[name]
            if field.shape != expected_shape:
                raise ValueError(f"{person}: unexpected shape for {name}")
            selected.append(field[SCHEMA[group]["h5py_component"], start:stop])
        return np.column_stack(selected)

    return Trial(person, start, channels("angles"),
                 channels("moments") if include_moments else None)


def future_moment(trial: Trial, cutoff: int):
    """Return a two-value vector at k+25, or None if outside the interval or invalid."""
    if trial.moments is None:
        raise ValueError("Moment channels were not requested")
    if not isinstance(cutoff, (int, np.integer)):
        raise TypeError("cutoff must be an integer index")
    target = int(cutoff) + TARGET_LEAD
    if cutoff < 0 or target >= len(trial.moments):
        return None
    moment = trial.moments[target]
    return moment.copy() if np.isfinite(moment).all() and (moment != 0).all() else None


def valid_history(angles):
    """Check only the chosen angle values up to and including the prediction cutoff."""
    angles = np.asarray(angles)
    return bool(angles.size and np.isfinite(angles).all() and (angles != 0).all())
