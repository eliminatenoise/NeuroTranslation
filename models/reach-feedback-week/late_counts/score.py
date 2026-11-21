"""Evaluate the frozen positive-sort motion update on a keyed, previously reconstructed recording."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np


FIT_HASH = "3cc1921584bb309249c2eec47c5aa14b3e9f349c2f3dac98036437bf4a2ad2ca"
TRAIN_HASH = "40bb17cd64e61bfb4ef52b5ee943d27d50e1c82bbf487d58c623c4ed2d6666ab"
METADATA = {
    "held-roster.json":"2e7578114bda89b18f5e2e0bbf6079dd52e4fb477c63405461b2cdf1ff2dccc6",
    "held-windows.json":"308cfb92f66c627cda88babe818c5b4431c8dcfda9629d58f0123693b95e4f6b",
    "held-schema.json":"0050b332d90a3d42f4fa00c7a83d296e8b60b54e861b1dce07760a0ab8e6a8ba",
}
MEMBER = "4456c7bf8cda177f31c849e3fe794100269ca951c741c1718dd5c750d5432a76"
KEY = ("block", "workspace", "original", "ordinal", "k")
ARMS = ("measured_update", "stale_position", "earlier", "movement_only")
METHODS = ARMS + ("wrong_donor", "zero_displacement", "previous_100ms", "pre_k_100ms", "train_mean")
CONTROL_ARMS = ("stale_position", "wrong_donor", "zero_displacement")
CONTRASTS = ("measured_minus_stale", "measured_minus_donor", "measured_minus_zero_displacement")
MOTION_LABELS = tuple(f"{p}_{a}" for p in ("Marker_1", "Pronation_Pt1") for a in "xyz") + ("handle_x", "handle_y")


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sealed_json(path, expected):
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, f"Unexpected contents: {path}")
    return json.loads(raw)


def concept_rows(guide):
    require(guide.ndim == 2 and guide.shape[1] == 2 and guide.dtype.kind in "iu", "Invalid guide")
    require(np.all(guide[:, 0] > 0) and np.all(guide[:, 1] > 0), "Positive-sort columns required")
    require(len(np.unique(guide, axis=0)) == len(guide), "Duplicate native guide entry")
    return {int(c): np.flatnonzero(guide[:, 0] == c) for c in np.unique(guide[:, 0])}


def field_validity(a, counts=False):
    valid = np.isfinite(a)
    if counts:
        valid &= (a >= 0) & (np.floor(a) == a)
    return valid.all(axis=tuple(range(1, a.ndim)))


def time_and_shapes(pack):
    n, u = len(pack["k"]), len(pack["unit_guide"])
    for key in KEY:
        v = pack[key]
        require(v.shape == (n,) and v.dtype.kind in "iu", f"Invalid integer {key}")
    for key, shape in {"pose":(20, 8), "movement":(10, 8), "cue":(20, 3),
                       "spikes":(20, u), "concurrent":(10, u), "delayed":(10, u)}.items():
        a = pack[key]
        require(a.dtype.kind in "iuf" and a.shape == (n, *shape), f"Invalid numeric {key}")
    for key, offsets in (("history_rows", range(-20, 0)), ("movement_rows", range(10)),
                         ("delayed_rows", range(10, 20))):
        v = pack[key]
        require(v.dtype.kind in "iu" and np.array_equal(v, pack["k"][:, None] + offsets), f"Invalid {key}")
    return concept_rows(pack["unit_guide"])


def keyed_rows(pack):
    return list(zip(*(map(int, pack[n]) for n in KEY), strict=True))


def native_cue(rows, events):
    count = np.searchsorted(events, rows, side="left")
    elapsed = np.zeros(len(rows))
    has = count > 0
    elapsed[has] = .01 * (rows[has] - np.array(events)[count[has] - 1])
    return np.column_stack((count, elapsed, has))


def validate_held_pack(pack, schema, windows, roster):
    """Check every candidate, native clock/labels and strictly causal task covariates."""
    time_and_shapes(pack)
    require(pack["source_member_sha256"].shape == () and pack["source_member_sha256"].item() == MEMBER,
            "Wrong source member identity")
    require(tuple(pack["pose_labels"].tolist()) == MOTION_LABELS, "Wrong motion axes/order")
    native = np.asarray(schema["guide"])
    columns = np.flatnonzero(native[:, 1] > 0)
    require(pack["sorted_columns"].dtype.kind in "iu" and np.array_equal(pack["sorted_columns"], columns+1)
            and np.array_equal(pack["unit_guide"], native[columns]), "Guide or source columns changed")
    block = schema["block"]
    expected = [tuple(w[n] for n in KEY) for w in windows if w["block"] == block]
    require(keyed_rows(pack) == expected, "Expect one row per frozen candidate, in native order")
    originals = {r["original"]:r for r in roster if r["block"] == block}
    for i, (_, _, oid, _, _) in enumerate(expected):
        c = native_cue(pack["history_rows"][i], originals[oid]["go"])
        require(np.allclose(c, pack["cue"][i], rtol=0., atol=1e-12), "Causal go features differ from metadata")


def previous_donors(rows, roster, eligible):
    """Return last numerically eligible earlier original within physical block, workspace and ordinal."""
    ordered = {(r["block"], r["original"]):r for r in roster}
    require(len(ordered) == len(roster), "Duplicate physical block/original key")
    result = np.full(len(rows), -1, dtype=int)
    last = {}
    windows_seen = set()
    prior_k = {}
    for i, (block, ws, oid, ordinal, k) in enumerate(rows):
        r = ordered[block, oid]
        require((block, oid, ordinal) not in windows_seen, "Repeated ordinal in physical original")
        windows_seen.add((block, oid, ordinal))
        require(r["workspace"] == ws and r["start"] <= k-20 and k+20 <= r["end"], "Invalid original/time key")
        require(k > prior_k.get(block, -1), "Windows must follow native row chronology")
        prior_k[block] = k
        key = (block, ws, ordinal)
        if key in last:
            j = last[key]
            donor_original = ordered[block, rows[j][2]]
            require(donor_original["original"] != oid and donor_original["end"] < r["start"],
                    "Donor must be a distinct strictly earlier original")
            result[i] = j
        if eligible[i]:
            last[key] = i
    return result


def draws(blocks, moving, repetitions=5000, seed=20261125):
    """Return positions in the full workspace roster, stratified by acquisition block."""
    blocks = np.asarray(blocks)
    if not len(blocks):
        return None
    rng = np.random.default_rng(seed)
    samples = []
    for b in dict.fromkeys(blocks):
        pos = np.flatnonzero(blocks == b)
        size = len(pos)
        if moving:
            if size < 8:
                return None
            starts = rng.integers(size-7, size=(repetitions, (size+7)//8))
            picked = (starts[...,None] + np.arange(8)).reshape(repetitions, -1)[:, :size]
        else:
            picked = rng.integers(size, size=(repetitions, size))
        samples.append(pos[picked])
    return np.concatenate(samples, axis=1)


def per_original(values, positions, length):
    sums = np.zeros((length, values.shape[1]))
    np.add.at(sums, positions, values)
    counts = np.bincount(positions, minlength=length)[:,None]
    return np.divide(sums, counts, where=counts > 0, out=np.full_like(sums, np.nan))


def summarize(values, positions, roster_length, weights):
    table = per_original(values, positions, roster_length)
    ok = np.isfinite(table).all(1)
    shape = table.shape[1]
    out = {"originals":int(ok.sum()), "windows":len(values),
           "mean":table[ok].mean(0).tolist() if ok.any() else [None]*shape}
    for method, w in weights.items():
        entry = {"interval":None}
        if w is None:
            entry["reason"] = "no assigned roster or fewer than eight assigned originals in a physical block"
        elif not ok.any():
            entry.update(reason="no supported original", empty_draws=len(w))
        else:
            denom = w @ ok.astype(float)
            empty = int(np.count_nonzero(denom == 0))
            entry["empty_draws"] = empty
            if empty or ok.sum() < 2:
                entry["reason"] = "empty bootstrap draw or fewer than two supported originals"
            else:
                samples = (w @ np.nan_to_num(table)) / denom[:,None]
                entry["interval"] = np.quantile(samples, [.025, .975], axis=0).T.tolist()
        out[method] = entry
    return out


def resample_weights(blocks):
    out = {}
    for label, moving in (("moving8", True), ("original_bootstrap", False)):
        d = draws(blocks, moving)
        if d is None:
            out[label] = None
        else:
            size = d.shape[1]
            shifted = d + np.arange(len(d))[:,None]*size
            out[label] = np.bincount(shifted.ravel(), minlength=d.size).reshape(d.shape).astype(float)
    return out


def design(pose, cue, history, recent, move, arm):
    parts = [pose[:,19], pose[:,19]-pose[:,9], cue[:,19]]
    if arm != "movement_only":
        parts.append(np.log1p(history.reshape(len(pose), 4, 5).sum(2)))
        if arm != "earlier":
            parts.append(np.log1p(recent.reshape(len(pose), 2, 5).sum(2)))
    if arm in ("movement_only", "measured_update"):
        parts.extend([move[:,4], move[:,9]])
    return np.column_stack(parts)


def rate(model, x):
    z = (x - np.array(model["mean"])) / np.array(model["scale"])
    beta = np.array(model["coefficients"])
    pred = np.exp(beta[0] + np.clip(z, -8., 8.) @ beta[1:])
    require(np.isfinite(pred).all() and np.all(pred > 0), "Invalid frozen head prediction")
    return pred


def deviance(y, mu):
    mu = np.maximum(mu, 1e-6)
    value = mu-y
    nz = y > 0
    value[nz] += y[nz] * np.log(y[nz]/mu[nz])
    return 2*value


def score_contacts(arrays, fit, channels, obs, donors, paired):
    """Use the same recipient windows and equal weights across every contact and arm."""
    used = np.flatnonzero(paired)
    scores = np.empty((len(used), len(channels), len(METHODS)))
    if not len(used) or not channels:
        return np.empty((0, len(METHODS))), None
    pose, cue, move = (arrays[k][used] for k in ("pose","cue","movement"))
    wrong = arrays["movement"][donors[used]]
    for j,c in enumerate(channels):
        history, recent, response = (obs[c][f][used] for f in ("spikes","concurrent","delayed"))
        y = response.sum(1)
        weights = {arm:fit["arms"][arm][str(c)] for arm in ARMS}
        mus = [rate(weights[a], design(pose, cue, history, recent, move, a)) for a in ARMS]
        for substitute in (wrong, np.zeros_like(move)):
            mus.append(rate(weights["measured_update"], design(pose, cue, history, recent, substitute, "measured_update")))
        mus.extend((recent.sum(1), history[:,-10:].sum(1), np.full(len(y), weights["measured_update"]["mean_count"])))
        for m,mu in enumerate(mus):
            scores[:,j,m] = deviance(y,mu)
    return scores.mean(1), scores


def memberships(rows, mask):
    selected = [r for i,r in enumerate(rows) if mask[i]]
    return {"windows":len(selected), "originals":len({(r[0], r[2]) for r in selected}),
            "by_ordinal":dict(sorted(Counter(r[3] for r in selected).items()))}


def count_reasons(select, masks):
    return {k:int(np.count_nonzero(select & ~m)) for k,m in masks.items()}


def evaluate(packs, roster, fit):
    """All contacts, allocations and QC masks are decided before calculation of count loss."""
    for block in {r["block"] for r in roster}:
        chronology = [r for r in roster if r["block"] == block]
        require(all(a["end"] < b["start"] for a,b in zip(chronology,chronology[1:])),
                "Native roster contains overlapping or unordered originals")
    guides = [time_and_shapes(p) for p in packs]
    trained = {int(c):m["positive_sort_count"] for c,m in fit["arms"]["measured_update"].items()}
    common = sorted(set(trained).intersection(*guides))
    multiplicity = {c:[len(g[c]) for g in guides] for c in common}
    groups = {"common":common, "equal":[c for c in common if all(n == trained[c] for n in multiplicity[c])],
              "growing":[c for c in common if all(n > trained[c] for n in multiplicity[c])],
              "shrinking":[c for c in common if all(n < trained[c] for n in multiplicity[c])]}
    rows = [r for p in packs for r in keyed_rows(p)]
    arrays = {k:np.concatenate([p[k] for p in packs]) for k in ("pose","cue","movement")}
    base_masks = {k:field_validity(a) for k,a in arrays.items()}
    contact_masks, obs = {}, {}
    for c in common:
        contact_masks[c], obs[c] = {}, {}
        for k in ("spikes","concurrent","delayed"):
            raw = [p[k][:,:,g[c]] for p,g in zip(packs,guides)]
            contact_masks[c][k] = np.concatenate([field_validity(a, counts=True) for a in raw])
            obs[c][k] = np.concatenate([np.sum(a, axis=2, dtype=float) for a in raw])

    out = {"method_order":list(METHODS), "contrast_order":list(CONTRASTS),
           "total_roster":len(roster), "unassigned_originals":sum(r["workspace"] not in (1,2) for r in roster),
           "candidate_windows":len(rows), "contacts":groups, "training_multiplicities":trained,
           "positive_guide_multiplicities_by_input_block":[{c:len(ix) for c,ix in g.items()} for g in guides],
           "train_missing_in_one_or_more_held_blocks":sorted(set(trained)-set(common)),
           "positive_held_only":sorted(set.union(*(set(g) for g in guides))-set(trained)), "workspaces":{}}
    for ws in (1,2):
        assigned = [r for r in roster if r["workspace"] == ws]
        pos = {(r["block"],r["original"]):i for i,r in enumerate(assigned)}
        in_ws = np.array([r[1] == ws for r in rows], dtype=bool)
        w = resample_weights([r["block"] for r in assigned])
        stages = {}
        for name, channels in groups.items():
            masks = {**base_masks, **{f"{c}/{k}":v for c in channels for k,v in contact_masks[c].items()}}
            observable = np.logical_and.reduce(list(masks.values())) & bool(channels)
            donors = previous_donors(rows, roster, observable)
            paired = in_ws & observable & (donors >= 0)
            losses, each_contact = score_contacts(arrays, fit, channels, obs, donors, paired)
            ix = np.flatnonzero(paired)
            positions = np.array([pos[rows[i][0], rows[i][2]] for i in ix], dtype=int)
            contrast = losses[:,[0]] - losses[:,[METHODS.index(m) for m in CONTROL_ARMS]]
            estimates = summarize(np.column_stack((losses,contrast)), positions, len(assigned), w)
            strata = {}
            for b in sorted({r["block"] for r in roster}):
                mask = in_ws & np.array([r[0] == b for r in rows], dtype=bool)
                stratum = [r for r in assigned if r["block"] == b]
                strata[b] = {"assigned_originals":len(stratum),"rewarded_originals":sum(r["result"] == "R" for r in stratum),
                             "metadata":memberships(rows,mask),"observable":memberships(rows,mask & observable),
                             "matched":memberships(rows,mask & paired),
                             "observable_without_donor":memberships(rows,mask & observable & (donors < 0)),
                             "qc_failures_may_overlap":count_reasons(mask,masks)}
            stages[name] = {"by_physical_block":strata, "observable":memberships(rows,in_ws & observable),
                            "observable_without_donor":memberships(rows,in_ws & observable & (donors < 0)),
                            "matched":estimates,
                            "mean_deviance_by_contact_on_matched_rows":{},
                            "window_audit":[{"recipient":rows[i],"qc_failed":[k for k,m in masks.items() if not m[i]],
                                             "has_contact_set":bool(channels), "observable":bool(observable[i]),
                                             "donor":rows[donors[i]] if observable[i] and donors[i]>=0 else None}
                                            for i in np.flatnonzero(in_ws)]}
            if each_contact is not None:
                for j,c in enumerate(channels):
                    per = per_original(each_contact[:,j], positions, len(assigned))
                    supported = np.isfinite(per).all(1)
                    stages[name]["mean_deviance_by_contact_on_matched_rows"][c] = per[supported].mean(0).tolist()
        out["workspaces"][ws] = {"assigned_originals":len(assigned), "rewarded_originals":sum(r["result"]=="R" for r in assigned),
                                 "metadata":memberships(rows,in_ws), "populations":stages}
    upper = []
    for ws in (1,2):
        interval = out["workspaces"][ws]["populations"]["common"]["matched"]["moving8"]["interval"]
        if interval is not None:
            upper.extend(x[1] for x in interval[len(METHODS):len(METHODS)+2])
    out["consistent_improvement_both_workspaces"] = (all(x<0 for x in upper) if len(upper)==4 else None)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fits", type=Path, required=True)
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--blocks", type=Path, nargs=2, required=True, metavar=("BLOCK1_NPZ", "BLOCK2_NPZ"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    require(not args.output.exists(), "Output already exists")
    fit = sealed_json(args.fits, FIT_HASH)
    roster, windows, schemas = [sealed_json(args.metadata/n, h) for n,h in METADATA.items()]
    packs, hashes = [], []
    fields = (*KEY, "unit_guide", "source_member_sha256", "pose_labels", "sorted_columns", "history_rows",
              "movement_rows", "delayed_rows", "pose", "movement", "cue", "spikes", "concurrent", "delayed")
    for path, schema in zip(args.blocks, schemas, strict=True):
        hashes.append(digest(path))
        with np.load(path, allow_pickle=False) as data:
            pack = {k:data[k] for k in fields}
        validate_held_pack(pack, schema, windows, roster)
        packs.append(pack)
    result = evaluate(packs, roster, fit)
    result["roster_with_metadata_exclusions"] = [
        {k:r[k] for k in ("block","original","workspace","result","start","end","reasons","candidates")}
        for r in roster
    ]
    result["inputs"] = {"day":"2017-09-14","fits_sha256":FIT_HASH,"metadata_sha256":METADATA,
                        "npz_sha256_in_block_order":hashes,"source_member_sha256":MEMBER}
    payload = json.dumps(result, allow_nan=False, separators=(",",":"))+"\n"
    with args.output.open("x", encoding="utf8") as stream:
        stream.write(payload)


if __name__ == "__main__":
    main()
