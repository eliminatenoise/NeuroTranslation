"""Score the two trained forecasts on two separately reconstructed blocks from September 14."""
import argparse
from pathlib import Path

import numpy as np

from forecast import (HERE, POPULATIONS, build_design, channels, contact_map, group_columns, predict, totals,
                      write_json)
from inputs import META_HASH, load, validate_test
from roster import (KEY, count_reasons, deviance, digest, keyed_rows, memberships, per_original, previous_donors,
                    require, resample_weights, sealed_json, summarize)

FIT_HASH = "b549ee0034445b91dc8dfb8d4777372ffc129a7470b9d61bb59f9be2b9ddaf74"
MAIN = ("update", "base", "wrong_motion")
REFERENCES = ("previous_late_100ms", "known_at_k_100ms", "train_mean")
CONTRASTS = ("update_minus_base", "update_minus_wrong_motion")


def assembled(packs, mapping, pop):
    output = {k:[] for k in ("base","residual","y","late","known","primary_history_ok","target_ok",
                             "late_ok","known_ok","pose_ok","cue_ok","movement_ok")}
    for p in packs:
        guide = p["all_guide"]
        common = group_columns(guide,channels(mapping,"primary"),"primary")
        endpoint = group_columns(guide,channels(mapping,pop),pop)
        history, history_ok = totals(p["all_history"], common)
        base, residual = build_design(p["pose"], p["cue_at_k"], history, p["movement"][:,-1])
        y, target_ok = totals(p["all_delayed"],endpoint)
        late, late_ok = totals(p["all_concurrent"],endpoint)
        known, known_ok = totals(p["all_history"][:,-10:],endpoint)
        for name,value in (("base",base),("residual",residual),("y",y),("late",late),("known",known),
                           ("primary_history_ok",history_ok),("target_ok",target_ok),("late_ok",late_ok),
                           ("known_ok",known_ok),("pose_ok",np.isfinite(p["pose"][:,[-5,-1]]).all((1,2))),
                           ("cue_ok",np.isfinite(p["cue_at_k"]).all(1)),
                           ("movement_ok",np.isfinite(p["movement"][:,-1]).all(1))):
            output[name].append(value)
    return {k:np.concatenate(v) for k,v in output.items()}


def original_summary(loss_cube, selected, positions, assigned, resamples, contacts, methods):
    """All named scores and paired deltas see identical rows on this support."""
    cube = loss_cube[selected]
    per_row = cube.mean(1)
    contrasts = per_row[:,[0]] - per_row[:,[1,2]]
    ids = positions[selected]
    summary = summarize(np.column_stack((per_row,contrasts)),ids,len(assigned),resamples)
    by_contact = {}
    for i,c in enumerate(contacts):
        table = per_original(cube[:,i,:],ids,len(assigned))
        supported = np.isfinite(table).all(1)
        by_contact[str(c)] = table[supported].mean(axis=0).tolist() if supported.any() else [None]*len(methods)
    return {"metric_order":list(methods) + list(CONTRASTS), "matched":summary,
            "per_contact_method_order":list(methods), "per_contact_deviance":by_contact}


def evaluate(packs, roster, fit, mapping):
    rows = [r for p in packs for r in keyed_rows(p)]
    require(len(rows) == len(set(rows)), "Duplicate candidate keys")
    for b in {r["block"] for r in roster}:
        order = [r for r in roster if r["block"] == b]
        require(all(a["end"] < c["start"] for a,c in zip(order,order[1:])), "Overlapping originals")
    report = {"contacts_by_population":{p:channels(mapping,p) for p in POPULATIONS},
              "roster":roster, "all_candidate_keys":rows, "workspaces":{}}
    per_row = {key:np.array([r[i] for r in rows]) for i,key in enumerate(KEY)}
    # Allocate bootstrap draws once per workspace from all assigned originals, even those with no windows.
    workspaces = {}
    for ws in (1,2):
        assigned = [r for r in roster if r["workspace"] == ws]
        position = {(r["block"],r["original"]):i for i,r in enumerate(assigned)}
        positions = np.array([position.get((b,oid),-1) if w == ws else -1 for b,w,oid,_,_ in rows],dtype=int)
        workspaces[ws] = assigned, positions, resample_weights([r["block"] for r in assigned])
        report["workspaces"][ws] = {"assigned_originals":len(assigned),"populations":{}}
    for pop in POPULATIONS:
        contacts = channels(mapping,pop)
        models = fit["populations"][pop]
        require(contacts == models["contacts"], "Unexpected endpoint channels")
        a = assembled(packs,mapping,pop)
        masks = {k:a[k] for k in ("pose_ok","cue_ok","movement_ok")}
        masks.update({f"primary_history_{c}":a["primary_history_ok"][:,i]
                      for i,c in enumerate(channels(mapping,"primary"))})
        masks.update({f"response_{c}":a["target_ok"][:,i] for i,c in enumerate(contacts)})
        observable = np.logical_and.reduce(list(masks.values()))
        donors = previous_donors(rows,roster,observable)
        matched = observable & (donors >= 0)
        all_methods = matched & a["known_ok"].all(1) & a["late_ok"].all(1)
        # Candidate donor eligibility depends on the original primary comparison, never on late spikes.
        means = np.full((len(rows),len(contacts),6),np.nan)
        means[observable,:,0] = predict(models["update"],np.column_stack((a["base"][observable],a["residual"][observable])))
        means[observable,:,1] = predict(models["base"],a["base"][observable])
        means[matched,:,2] = predict(models["update"],np.column_stack((a["base"][matched],a["residual"][donors[matched]])))
        means[:,:,3] = a["late"]
        means[:,:,4] = a["known"]
        means[:,:,5] = models["train_mean"]
        losses = np.stack([deviance(a["y"],means[:,:,j]) for j in range(means.shape[2])],axis=2)
        for k,v in (("observed",a["y"]),("expected",means),("observable",observable),("donor",donors),
                    ("matched",matched),("all_matched",all_methods)):
            per_row[f"{pop}_{k}"] = v
        ref_masks = {f"{name}_{c}":a[field][:,i] for name,field in (("late","late_ok"),("known","known_ok"))
                     for i,c in enumerate(contacts)}
        for ws,(assigned,positions,weights) in workspaces.items():
            in_ws = per_row["workspace"] == ws
            entry = {"prespecified":original_summary(losses[:,:,:3],in_ws & matched,positions,assigned,weights,contacts,MAIN),
                     "with_count_references":original_summary(losses,in_ws & all_methods,positions,assigned,weights,
                                                              contacts,MAIN+REFERENCES), "physical_blocks":{},
                     "candidate_audit":[]}
            for b in sorted({r["block"] for r in roster}):
                mask = in_ws & (per_row["block"] == b)
                group = [r for r in assigned if r["block"] == b]
                entry["physical_blocks"][b] = {
                    "assigned_originals":len(group), "rewarded_originals":sum(r["result"]=="R" for r in group),
                    "metadata":memberships(rows,mask), "observable":memberships(rows,mask & observable),
                    "matched":memberships(rows,mask & matched), "all_methods_matched":memberships(rows,mask & all_methods),
                    "observable_without_earlier_donor":memberships(rows,mask & observable & (donors<0)),
                    "qc_failure_counts_may_overlap":count_reasons(mask,{**masks,**ref_masks})}
            for i in np.flatnonzero(in_ws):
                entry["candidate_audit"].append({"key":rows[i], "failed_inputs_or_outputs":[k for k,v in masks.items() if not v[i]],
                    "failed_count_references":[k for k,v in ref_masks.items() if not v[i]],
                    "donor":rows[donors[i]] if matched[i] else None})
            report["workspaces"][ws]["populations"][pop] = entry
    upper = []
    for ws in (1,2):
        stats = report["workspaces"][ws]["populations"]["primary"]["prespecified"]["matched"]
        interval = stats["moving8"]["interval"]
        if interval is not None:
            upper.extend(v[1] for v in interval[-2:])
    report["primary_incremental_success"] = None if len(upper) != 4 else all(v<0 for v in upper)
    return report, per_row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--fits", type=Path, default=HERE/"fits.json")
    parser.add_argument("--blocks", type=Path, nargs=2, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--rows", type=Path, required=True)
    args = parser.parse_args()
    require(not args.result.exists() and not args.rows.exists(), "Use new output paths")
    fit = sealed_json(args.fits,FIT_HASH)
    mapping = contact_map()
    roster, windows, schemas = [sealed_json(args.metadata / k,h) for k,h in META_HASH.items()]
    packs = [load(p) for p in args.blocks]
    for p,s in zip(packs,schemas,strict=True):
        validate_test(p,s,windows,roster)
    result, arrays = evaluate(packs,roster,fit,mapping)
    result["inputs"] = {"fits_sha256":FIT_HASH, "metadata_sha256":META_HASH,
                        "npz_sha256_in_block_order":[digest(p) for p in args.blocks]}
    result["row_expected_method_order"] = list(MAIN + REFERENCES)
    with args.rows.open("xb") as stream:
        np.savez_compressed(stream,**arrays)
    result["row_output_sha256"] = digest(args.rows)
    write_json(args.result,result)


if __name__ == "__main__":
    main()
