"""The recorded experiment's four-epoch fit on an already prepared and admitted TRAIN table.

This entry is importable for reproduction. Preparation must provide aligned source events as
described in REPRODUCE.md. It does not fetch recordings, assign participants or select a model.
"""
import numpy as np

from aligned_forecast import aligned_forecast_step
from study_model import BATCH, EPOCHS, MODES, SEED, make_model, pack, session


def fit_epochs(data, norm, training_runs, excluded_runs, mode, source_digest):
    if mode not in MODES or data.role != "train":
        raise ValueError("One registered input set and the TRAIN partition are required")
    if set(data.parent) != set(training_runs) or set(training_runs) & set(excluded_runs):
        raise ValueError("Observed parents must match the independent disjoint TRAIN roster")
    if len(training_runs) != 47 or len(data.parent) != 11274:
        raise ValueError("The original protocol requires 47 eligible runs and 11,274 forecast rows")
    if not np.array_equal(data.events.value, data.rows.target):
        raise ValueError("Independently retrieved encoder events differ from the target table")
    steps = EPOCHS * ((len(data.parent) + BATCH-1)//BATCH)
    model = make_model(norm, training_runs)
    managed = session(model, mode, training_runs, excluded_runs, steps, source_digest)
    schedule = np.random.default_rng(SEED)
    epoch_means = []
    for _ in range(EPOCHS):
        order = schedule.permutation(len(data.parent))
        losses, sizes = [], []
        for first in range(0,len(order),BATCH):
            idx = order[first:first+BATCH]
            observation, query, targets = pack(data,idx,mode,norm)
            losses.append(aligned_forecast_step(managed,observation,query,targets)["loss"])
            sizes.append(len(idx))
        epoch_means.append(float(np.average(losses,weights=sizes)))
    if managed.completed_steps!=steps or not np.isfinite(epoch_means).all():
        raise ValueError("Training left the fixed step count or numeric domain")
    return model,epoch_means
