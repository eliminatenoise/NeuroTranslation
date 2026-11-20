"""Native-unit event losses and participant-balanced paired resampling."""
import numpy as np

MUSCLES = ["left_tibialis_anterior","left_soleus","left_medial_gastrocnemius","left_peroneus_longus",
           "right_tibialis_anterior","right_soleus","right_medial_gastrocnemius","right_peroneus_longus"]
FIELDS = ["muscle_mae_uv","path_mean_distance_mm","endpoint_distance_mm"] + [
    f"{k}_mae_uv" for k in MUSCLES] + [f"{k}_bias_uv" for k in MUSCLES] + [
    f"{axis}_path_bias_mm" for axis in ("ML","SI","AP")]


def extract_errors(data, ids, yr, yp):
    muscle = yr.astype("float64") - data["future_rms_uv"][ids].astype("float64")
    path = yp.astype("float64") - data["future_path_mm"][ids].astype("float64")
    distance = np.linalg.norm(path, axis=2)
    return np.column_stack([np.abs(muscle).mean(1), distance.mean(1), distance[:, -1],
                            np.abs(muscle), muscle, path.mean(1)])


def participant_means(data, ids, errors, postures, directions):
    people = data["person"][ids]
    pose, cue = data["posture"][ids], data["direction"][ids]
    balanced, codes, count = [], [], 0
    for p in np.unique(people):
        cells = [(people == p) & (pose == s) & (cue == d) for s in postures for d in directions]
        if all(mask.any() for mask in cells):
            balanced.append(np.mean([errors[mask].mean(0) for mask in cells], axis=0))
            codes.append(p)
            count += sum(int(mask.sum()) for mask in cells)
    return np.array(codes),np.array(balanced).reshape(-1,len(FIELDS)),count


def grouped(data, ids, errors, postures, directions=(-1,1)):
    people, means, n = participant_means(data, ids, errors, postures, directions)
    if not len(people):
        return {"people":0,"events":0,"scores":None}, (people,means)
    return dict(people=len(people),events=n,scores=dict(zip(FIELDS,means.mean(0).tolist()))),(people,means)


def summarize(data, ids, errors):
    overall, rows = grouped(data,ids,errors,(0,1))
    overall["by_posture"] = {n:grouped(data,ids,errors,(s,))[0] for s,n in ((0,"stand"),(1,"walk"))}
    overall["by_direction"] = {str(d):grouped(data,ids,errors,(0,1),(d,))[0] for d in (-1,1)}
    return overall, rows


def paired(first, second):
    people, x = first
    other, y = second
    if not np.array_equal(people,other):
        raise ValueError("A paired comparison requires identical participants and cells")
    if not len(people):
        return {"people":0,"differences":None}
    delta = x[:,:3]-y[:,:3]
    draw = np.random.default_rng(1419).integers(len(x), size=(5000,len(x)))
    estimates = delta[draw].mean(1)
    lo,hi = np.percentile(estimates,[2.5,97.5],axis=0)
    return dict(people=len(x),differences={
        name:dict(mean=float(delta[:,j].mean()),ci95=[float(lo[j]),float(hi[j])],
                  upper_97_5_one_sided=float(hi[j]),people_lower=int((delta[:,j]<0).sum()))
        for j,name in enumerate(FIELDS[:3])})


def donors(data, ids):
    strata = {}
    for i in ids:
        key = tuple(data[k][i] for k in ("person","posture","direction","block"))
        strata.setdefault(key, []).append(i)
    targets, sources = [], []
    for group in strata.values():
        ordered = sorted(group,key=lambda i:int(data["cutoff"][i]))
        for t,s in zip(ordered,ordered[1:]+ordered[:1]):
            if abs(int(data["cutoff"][t])-int(data["cutoff"][s])) > 207:
                targets.append(t)
                sources.append(s)
    return np.array(targets,dtype=int),np.array(sources,dtype=int)
