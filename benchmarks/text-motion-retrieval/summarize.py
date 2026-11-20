"""Publish aggregate metrics without sharing raw clips, caption text, score vectors or fitted weights."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics

import numpy as np
from retrieval import metric_dict, rows_mean_per_motion, tied_scores


def summary(work, manifest_path):
    read = lambda path: json.loads(path.read_text())
    manifest = read(manifest_path)
    out = read(work/"assessment"/"results.json")
    receipt = read(work/"assessment"/"seal.json")
    train = read(work/"fit"/"fit.json")
    counts = {}
    for part in ("train","assessment","reserve"):
        rows = [r for r in manifest["rows"] if r["part"]==part]
        counts[part]={"recordings":len(rows),"subject_ids":len({r["group"] for r in rows}),
                      "caption_count_from_metadata":sum(r["n_annotations"] for r in rows)}
    methods = {name:{k:v for k,v in result.items() if k!="by_motion"} for name,result in out["methods"].items()}
    attention = methods["attention"]
    # Descriptive breakdown of the saved scores. No refitting or reranking outside
    # the complete predeclared gallery and corresponding within-class galleries.
    actions = np.array(out["actions"])
    with np.load(work/"assessment"/"scores.npz",allow_pickle=False) as z:
        owners = z["owners"]
        categories = {}
        for action in sorted(set(actions)):
            clips = np.flatnonzero(actions==action)
            query_rows = np.flatnonzero(np.isin(owners,clips))
            local_owners = np.searchsorted(clips,owners[query_rows])
            by_method = {}
            for name in methods:
                score = z[name][query_rows]
                exact = rows_mean_per_motion(tied_scores(score,owners[query_rows]),local_owners,len(clips)).mean(0)
                within = rows_mean_per_motion(tied_scores(score[:,clips],local_owners),local_owners,len(clips)).mean(0)
                by_method[name] = {"exact_in_full_gallery":metric_dict(exact),
                                   "exact_within_action":metric_dict(within) if len(clips)>1 else None}
            categories[action] = {"recordings":len(clips),"captions":len(query_rows),
                                  "catalogue_subject_ids":len(set(out["groups"][i] for i in clips)),
                                  "methods":by_method}
    differences = {}
    for rival in ["ridge","wrong_pair","chance","caption_to_action"]:
        if rival not in methods:
            continue
        other = methods[rival]
        differences[rival] = {}
        for metric in ["recall1","mrr"]:
            by_group = {g:vals[metric]-other["by_group"][g][metric] for g,vals in attention["by_group"].items()}
            differences[rival][metric] = {
                "motion_macro_difference":attention["motion_macro"][metric]-other["motion_macro"][metric],
                "subject_id_macro_difference":statistics.mean(by_group.values()),
                "range_across_subject_ids":[min(by_group.values()),max(by_group.values())],
                "per_subject_id":by_group}
    passed = all(d["motion_macro_difference"]>0 for diff in differences.values() for d in diff.values())
    return {"task":"Local text-to-motion retrieval on recorded KIT subjects",
            "distribution":"Aggregate scores and study source only. Raw representations, descriptions, training vocabulary, score vectors and weights remain local.",
            "split":counts, "assessment_queries":out["coverage"],"ambiguity":receipt["ambiguity"],
            "assessment_cue_recording_counts":dict(Counter(out["actions"])),
            "assessment_cues_unseen_in_train":sorted(set(out["actions"])-set(train["cue_classes"])),
            "metrics":methods,"by_catalogue_action":categories,"attention_minus_comparator":differences,
            "prespecified_descriptive_comparison_passed":passed,"identity":receipt["identity"],
            "archive_sha256":manifest["archive_sha256"]}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    args.out.write_text(json.dumps(summary(args.work,args.manifest),indent=2,sort_keys=True,allow_nan=False)+"\n")
