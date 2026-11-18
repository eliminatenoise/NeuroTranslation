"""A within-source surface EMG reference baseline for mechanical measurements."""

from dataclasses import asdict, dataclass
import math

import numpy as np


NANOSECONDS = 1_000_000_000


@dataclass(frozen=True)
class Trial:
    subject: str
    session: str
    trial: str
    source_trial: str
    channel_names: tuple[str, ...]
    emg_seconds: np.ndarray
    emg: np.ndarray
    target_seconds: np.ndarray
    target: np.ndarray
    target_start_row: int = 0
    emg_start_row: int = 0


@dataclass(frozen=True)
class Design:
    window_seconds: float
    lead_seconds: float
    maximum_gap_seconds: float
    minimum_emg_samples: int
    ridge_penalty: float

    def __post_init__(self):
        for value in (self.window_seconds, self.maximum_gap_seconds, self.ridge_penalty):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("window, gap and penalty must be finite and positive")
        if not math.isfinite(self.lead_seconds) or self.lead_seconds < 0:
            raise ValueError("lead must be finite and nonnegative")
        if type(self.minimum_emg_samples) is not int or self.minimum_emg_samples < 2:
            raise ValueError("at least two EMG samples are required")
        if self.maximum_gap_seconds >= self.window_seconds:
            raise ValueError("maximum gap must be shorter than the feature window")
        for seconds in (self.window_seconds, self.lead_seconds, self.maximum_gap_seconds):
            ticks = seconds * NANOSECONDS
            if abs(ticks) >= NANOSECONDS * 1e6 or abs(ticks - round(ticks)) > 1e-7:
                raise ValueError("timing design must use whole nanoseconds within a recording")


@dataclass(frozen=True)
class Windows:
    subject: str
    features: np.ndarray
    labels: np.ndarray
    target_rows: np.ndarray
    last_emg_rows: np.ndarray
    label_times: np.ndarray
    last_emg_times: np.ndarray
    total_label_rows: int
    missing_label_rows: int
    unavailable_history_rows: int


def _validate_times(times, name):
    times = np.asarray(times, dtype=np.float64)
    if times.ndim != 1 or not len(times) or not np.isfinite(times).all():
        raise ValueError(f"{name} must be a nonempty finite time vector")
    if not (np.diff(times) > 0).all():
        raise ValueError(f"{name} must be strictly increasing")
    if np.max(np.abs(times)) >= 1e6:
        raise ValueError(f"{name} must use relative seconds within a recording")
    ticks = np.rint(times * NANOSECONDS).astype(np.int64)
    if not (np.diff(ticks) > 0).all():
        raise ValueError(f"{name} contains samples that collide at nanosecond resolution")
    return ticks


def windows(trial: Trial, design: Design) -> Windows:
    """Build trailing EMG RMS windows from declared common-clock seconds."""
    times = _validate_times(trial.emg_seconds, "EMG clock")
    target_times = _validate_times(trial.target_seconds, "target clock")
    emg = np.asarray(trial.emg, dtype=np.float64)
    targets = np.asarray(trial.target, dtype=np.float64)
    if emg.shape != (len(times), len(trial.channel_names)) or not trial.channel_names:
        raise ValueError("EMG dimensions do not match its clock and channel order")
    if targets.shape != target_times.shape:
        raise ValueError("one scalar mechanical measurement per target timestamp is required")
    if not np.isfinite(emg).all() or np.isinf(targets).any():
        raise ValueError("EMG must be finite and target values must be finite or missing")

    end_times = target_times - round(design.lead_seconds * NANOSECONDS)
    start_times = end_times - round(design.window_seconds * NANOSECONDS)
    maximum_gap = round(design.maximum_gap_seconds * NANOSECONDS)
    begin = np.searchsorted(times, start_times, side="left")
    end = np.searchsorted(times, end_times, side="right")
    present = np.isfinite(targets)
    rows = np.flatnonzero(present & (end - begin >= design.minimum_emg_samples))
    first, after_last = begin[rows], end[rows]

    # Reject clock gaps inside a window and insufficient support at either edge.
    gap_prefix = np.r_[0, np.cumsum(np.diff(times) > maximum_gap)]
    support = (
        (gap_prefix[after_last - 1] == gap_prefix[first])
        & (times[first] - start_times[rows] <= maximum_gap)
        & (end_times[rows] - times[after_last - 1] <= maximum_gap)
    )
    rows = rows[support]
    first, after_last = first[support], after_last[support]

    with np.errstate(over="raise", invalid="raise"):
        squares = np.vstack((np.zeros((1, emg.shape[1])), (emg * emg).cumsum(axis=0)))
        energy = squares[after_last] - squares[first]
        features = np.sqrt(energy / (after_last - first)[:, None])

    return Windows(
        trial.subject, features, targets[rows], rows, after_last - 1,
        target_times[rows] / NANOSECONDS, times[after_last - 1] / NANOSECONDS, len(targets),
        len(targets) - int(present.sum()), int(present.sum()) - len(rows),
    )


@dataclass(frozen=True)
class Ridge:
    mean: np.ndarray
    scale: np.ndarray
    weights: np.ndarray
    intercept: float

    def predict(self, features):
        return self.intercept + ((features - self.mean) / self.scale) @ self.weights


def fit(training_features, training_labels, penalty):
    """Fit only on training windows. The loss is mean square plus L2 penalty."""
    training_features = np.asarray(training_features, dtype=np.float64)
    training_labels = np.asarray(training_labels, dtype=np.float64)
    if training_features.ndim != 2 or len(training_features) < 2:
        raise ValueError("require at least two training feature rows")
    if training_labels.shape != (len(training_features),):
        raise ValueError("require one scalar label per training feature row")
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        mean = training_features.mean(axis=0)
        scale = training_features.std(axis=0)
        # A constant training channel contributes exactly zero to the fit.
        scale[scale == 0] = 1
        x = (training_features - mean) / scale
        center = float(training_labels.mean())
        y = training_labels - center
        n = len(y)
        gram = (x.T @ x) / n + penalty * np.eye(x.shape[1])
        weights = np.linalg.solve(gram, (x.T @ y) / n)
    if not (np.isfinite(weights).all() and math.isfinite(center)):
        raise ValueError("ridge returned nonfinite parameters")
    return Ridge(mean, scale, weights, center)


def _check_split(trials, train_subjects, test_subjects):
    train_subjects = tuple(train_subjects)
    test_subjects = tuple(test_subjects)
    train, test = set(train_subjects), set(test_subjects)
    if not train or not test or train & test:
        raise ValueError("training and test subjects must be nonempty and disjoint")
    if len(train) != len(train_subjects) or len(test) != len(test_subjects):
        raise ValueError("duplicate subject in the split")
    if {t.subject for t in trials} != train | test:
        raise ValueError("trial subject inventory must equal the declared split")
    entries = {(t.subject, t.session, t.trial) for t in trials}
    if len(entries) != len(trials) or len({t.source_trial for t in trials}) != len(trials):
        raise ValueError("duplicate trial or original source trial")
    if any(not all((t.subject, t.session, t.trial, t.source_trial)) for t in trials):
        raise ValueError("each trial requires source, subject, session and trial identities")
    channels = trials[0].channel_names
    if (
        not all(channels)
        or len(channels) != len(set(channels))
        or any(t.channel_names != channels for t in trials)
    ):
        raise ValueError("all trials must have the same uniquely named, ordered channels")
    return train


def _metrics(labels, predictions):
    def errors(estimate):
        with np.errstate(over="raise", invalid="raise"):
            residual = estimate - labels
            if not np.isfinite(residual).all():
                raise ValueError("nonfinite evaluation residual")
            return {
                "mae": float(np.mean(np.abs(residual))),
                "rmse": float(np.sqrt(np.mean(residual * residual))),
            }

    return {"rows": len(labels), **{name: errors(values) for name, values in predictions.items()}}


def _score(parts, model, template_rows, template_angles):
    predictions = {method: [] for method in ("ridge", "training_mean", "onset_only")}
    for part in parts:
        predictions["ridge"].append(model.predict(part.features))
        predictions["training_mean"].append(np.full(len(part.labels), model.intercept))
        predictions["onset_only"].append(np.interp(part.target_rows, template_rows, template_angles))
    by_trial = [
        _metrics(part.labels, {name: values[index] for name, values in predictions.items()})
        for index, part in enumerate(parts)
    ]
    predictions = {name: np.concatenate(values) for name, values in predictions.items()}
    labels = np.concatenate([part.labels for part in parts])
    subjects = np.repeat([part.subject for part in parts], [len(part.labels) for part in parts])
    by_subject = {}
    for subject in sorted(set(subjects)):
        mask = subjects == subject
        by_subject[subject] = _metrics(
            labels[mask], {name: values[mask] for name, values in predictions.items()},
        )
    return {
        "pooled_errors": _metrics(labels, predictions),
        "errors_by_subject": by_subject,
        "errors_by_trial": by_trial,
        "subject_macro_errors": {
            method: {
                metric: float(np.mean([row[method][metric] for row in by_subject.values()]))
                for metric in ("mae", "rmse")
            }
            for method in predictions
        },
        "trial_macro_errors": {
            method: {
                metric: float(np.mean([row[method][metric] for row in by_trial]))
                for metric in ("mae", "rmse")
            }
            for method in predictions
        },
        "onset_template_clamped_rows": int(sum(
            np.count_nonzero((part.target_rows < template_rows[0]) | (part.target_rows > template_rows[-1]))
            for part in parts
        )),
    }


def evaluate(trials, train_subjects, test_subjects, design: Design, target_hz):
    """Evaluate on disjoint subjects using an onset-relative target grid."""
    if not math.isfinite(target_hz) or target_hz <= 0:
        raise ValueError("target sampling rate must be finite and positive")
    trials, train_subjects, test_subjects = tuple(trials), tuple(train_subjects), tuple(test_subjects)
    train = _check_split(trials, train_subjects, test_subjects)
    training, test, support = [], [], []
    for trial in trials:
        part = windows(trial, design)
        relative_times = trial.target_seconds - trial.target_seconds[0]
        expected_grid = np.arange(len(relative_times)) / target_hz
        if not np.allclose(relative_times, expected_grid, atol=1e-9, rtol=0):
            raise ValueError("onset-only template requires a common fixed-rate target grid")
        if not len(part.labels):
            raise ValueError(f"no valid paired windows in original trial {trial.source_trial}")
        is_train = trial.subject in train
        (training if is_train else test).append(part)
        leads = part.label_times - part.last_emg_times
        support.append({
            "subject": trial.subject,
            "session": trial.session,
            "trial": trial.trial,
            "source_trial": trial.source_trial,
            "partition": "train" if is_train else "test",
            "target_rows_total": part.total_label_rows,
            "scored_rows": len(part.labels),
            "excluded_rows": part.total_label_rows - len(part.labels),
            "missing_target_rows": part.missing_label_rows,
            "unavailable_emg_history_rows": part.unavailable_history_rows,
            "scored_original_target_row_range_zero_based": [
                int(part.target_rows[0]) + trial.target_start_row,
                int(part.target_rows[-1]) + trial.target_start_row,
            ],
            "feature_cutoff_original_emg_row_range_zero_based": [
                int(part.last_emg_rows[0]) + trial.emg_start_row,
                int(part.last_emg_rows[-1]) + trial.emg_start_row,
            ],
            "stored_lead_range_seconds": [float(leads.min()), float(leads.max())],
        })

    training_labels = np.concatenate([part.labels for part in training])
    training_rows = np.concatenate([part.target_rows for part in training])
    training_features = np.concatenate([part.features for part in training])
    model = fit(training_features, training_labels, design.ridge_penalty)
    frame_counts = np.bincount(training_rows)
    frame_sums = np.bincount(training_rows, weights=training_labels)
    template_rows = np.flatnonzero(frame_counts)
    template_angles = frame_sums[template_rows] / frame_counts[template_rows]
    reference = _score(training, model, template_rows, template_angles)
    development = _score(test, model, template_rows, template_angles)
    for partition, scores in (("train", reference), ("test", development)):
        trial_support = [row for row in support if row["partition"] == partition]
        for row, metrics in zip(trial_support, scores["errors_by_trial"], strict=True):
            metrics["source_trial"] = row["source_trial"]
    return {
        "design": asdict(design),
        "train_subjects": sorted(train_subjects),
        "test_subjects": sorted(test_subjects),
        "channel_names": list(trials[0].channel_names),
        "support": support,
        "training_rows": len(training_labels),
        "onset_template_frame_count": len(template_rows),
        "onset_template_frame_range": [int(template_rows[0]), int(template_rows[-1])],
        "reference_in_sample": reference,
        "development_held_out_subject": development,
    }
