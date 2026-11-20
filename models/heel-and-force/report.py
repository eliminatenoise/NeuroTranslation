import numpy as np
from records import donors, subset, weights

DRAWS = 5000


def errors(d, pred):
    delta = pred - np.column_stack((d["heel_delta_mm"], d["force_n"]))
    return np.column_stack((np.linalg.norm(delta[:, :3], axis=1), np.abs(delta[:, 3]), delta))


def average(d, a):
    if not len(d["person"]):
        return None
    return float(weights(d) @ a)


def sufficient(d, e):
    trial, person = {}, {}
    for p in sorted(set(d["person"])):
        take = d["person"] == p
        trial[p] = {}
        for rep in sorted(set(d["repeat"][take])):
            mask = take & (d["repeat"] == rep)
            trial[p][str(rep)] = float(np.mean(e[mask]))
        person[p] = float(np.mean(list(trial[p].values())))
    return trial, person


def describe(d, e):
    keep = np.isfinite(e)
    if not keep.any():
        return None
    sub, val = subset(d, keep), e[keep]
    trial, person = sufficient(sub, val)
    vals = np.asarray(list(person.values()))
    rng = np.random.default_rng(7103)
    lo, hi = np.quantile(vals[rng.integers(0, len(vals), size=(DRAWS, len(vals)))].mean(axis=1), [.025,.975])
    desc = {"mean":float(vals.mean()), "participant_bootstrap_95":[float(lo),float(hi)],
            "people":len(vals), "repeats":sum(len(q) for q in trial.values()), "rows":len(val)}
    return desc

def summarize(d, predictions):
    es = {k: errors(d, val) for k, val in predictions.items()}
    labels = ("heel_mm", "force_N", "X_bias_mm", "Y_bias_mm", "Z_bias_mm", "force_bias_N")
    models = {k: {label: describe(d, e[:, i]) for i, label in enumerate(labels)} for k, e in es.items()}
    paired = {k: {label: describe(d, es["joint"][:, i] - e[:, i]) for i, label in enumerate(labels[:2])}
              for k, e in es.items() if k != "joint"}
    take, _ = donors(d)
    matched = subset(d, take)
    donor_metrics = {k: {label: describe(matched, es[k][take, i]) for i, label in enumerate(labels[:2])}
                     for k in ("joint", "marker", "wrong_emg")}
    def passed(metric):
        return metric is not None and metric["mean"] < 0 and metric["participant_bootstrap_95"][1] < 0
    primary = passed(paired["heel"]["heel_mm"]) and passed(paired["force"]["force_N"])
    emg = {k: passed(paired["marker"][k]) and passed(paired["wrong_emg"][k]) for k in labels[:2]}
    support = {"rows": len(take), "all_rows": len(d["person"]), "people": len(set(matched["person"])),
               "all_people": len(set(d["person"])), "repeats": len(set(zip(matched["person"], matched["repeat"]))),
               "all_repeats": len(set(zip(d["person"], d["repeat"])))}
    return {"models": models, "joint_minus": paired, "donor_metrics": donor_metrics,
            "joint_over_specialists": primary, "emg_increment": emg, "donor_support": support}
