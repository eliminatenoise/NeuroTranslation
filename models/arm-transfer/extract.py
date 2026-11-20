"""Extract the original mechanical windows. The separate source reader checks the file identity."""

from collections import Counter
from pathlib import Path

import numpy as np

SENSORS = (93, 94, 68)


def rows(cache, people):
    from ofner_transfer import Run, digests, filename

    x, y, groups, audit = [], [], [], []
    people = list(people)
    if (
        not people
        or len(set(people)) != len(people)
        or not (
            all(type(p) is int and 1 <= p <= 7 for p in people)
            or all(type(p) is int and 8 <= p <= 12 for p in people)
        )
    ):
        raise ValueError("Select a unique list from one allowed cohort.")
    for person in people:
        for number in (1, 2, 3):
            reasons = Counter()
            first_row = len(x)
            try:
                recording = Run(cache, person, number)
            except ValueError as error:
                # A wrong or incomplete local copy must be replaced before any experimental scoring.
                if str(error).startswith("Wrong size or MD5"):
                    raise
                with (Path(cache) / filename(person, number)).open("rb") as stream:
                    _, _, source_sha = digests(stream)
                audit.append(
                    {
                        "person": person,
                        "run": number,
                        "source_sha256": source_sha,
                        "eligible": 0,
                        "cue_events": None,
                        "excluded": {"unsupported_run_layout": 1},
                        "run_error": str(error),
                        "flat_target_coordinates": None,
                        "input_level_min": None,
                        "input_level_max": None,
                    }
                )
                continue
            with recording as run:
                cues = [(t, code) for t, code in run.events if 0x600 <= code <= 0x606]
                for j, (t, code) in enumerate(cues):
                    limit = cues[j + 1][0] if j + 1 < len(cues) else run.records * 512
                    ends = [
                        q
                        for q, c in run.events
                        if c == code + 0x8000 and t < q <= limit
                    ]
                    if len(ends) != 1 or ends[0] < t + 896:
                        reasons["missing_or_short_end"] += 1
                        continue
                    cutoff = t + 128
                    last = cutoff // 8
                    if last < 31 or (cutoff + 768) // 8 >= run.records * 64:
                        reasons["incomplete_window"] += 1
                        continue
                    bins = np.column_stack(
                        [run.window(c, last - 31, last + 1) for c in SENSORS]
                    ).reshape(4, 8, 3)
                    future = []
                    for horizon in (256, 512, 768):
                        e = (cutoff + horizon) // 8
                        future.append(
                            np.column_stack(
                                [run.window(c, e - 7, e + 1) for c in SENSORS]
                            )
                        )
                    if not np.isfinite(bins).all() or not np.isfinite(future).all():
                        reasons["nonfinite_window"] += 1
                        continue
                    levels = np.median(bins, axis=1)
                    drift = np.median(bins[:, 4:], axis=1) - np.median(
                        bins[:, :4], axis=1
                    )
                    x.append(np.column_stack([levels, drift]))
                    y.append(np.median(future, axis=1) - levels[-1])
                    groups.append((person, number, code - 0x600))
                dx, dy = np.array(x[first_row:]), np.array(y[first_row:])
                audit.append(
                    {
                        "person": person,
                        "run": number,
                        "source_sha256": run.sha256,
                        "cue_events": len(cues),
                        "eligible": len(dx),
                        "excluded": dict(reasons),
                        "flat_target_coordinates": (np.ptp(dy, axis=0) < 1e-8).tolist()
                        if len(dy)
                        else None,
                        "input_level_min": dx[:, :, :3].min(axis=(0, 1)).tolist()
                        if len(dx)
                        else None,
                        "input_level_max": dx[:, :, :3].max(axis=(0, 1)).tolist()
                        if len(dx)
                        else None,
                    }
                )
    if not x:
        raise ValueError("No eligible trials.")
    return np.stack(x), np.stack(y), np.asarray(groups, dtype=int), audit
