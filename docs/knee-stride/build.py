"""Build a self-contained reader. Every model and study input is hash-pinned."""
import argparse
from pathlib import Path
import hashlib
import json
import html

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assembled(model):
    pins = json.loads((SRC / "inputs.sha256.json").read_text())
    for name, expected in pins.items():
        path = (SRC if name.startswith("shared-knee.") else model) / name
        if sha(path) != expected:
            raise ValueError(f"Changed model or study input: {name}")
    load = lambda name: json.loads((model / name).read_text())
    fit, results, source = load("weights.json"), load("results.json"), load("source-members.json")
    if results["weights_sha256"] != pins["weights.json"] or results["protocol_sha256"] != pins["protocol.json"]:
        raise ValueError("Assessment and checkpoint disagree")
    people = [dict(id=p["participant"], cutoffs=p["cutoffs"], mae=p["mae_deg"]) for p in results["participants"]]
    members = []
    for p in results["participants"]:
        member = next(m for m in source["members"] if m["subject"] == p["participant"])
        if member["sha256"] != p["member_sha256"] or member["rows"] != p["source_rows"] or member["split"] != "test":
            raise ValueError("Held-out file identity changed")
        members.append(dict(**member,long_windows=p["cutoffs"]))
    if [p["id"] for p in people] != list(range(41,53)) or sum(p["cutoffs"] for p in people) != results["cutoffs"]:
        raise ValueError("Unexpected evaluation cohort or size")
    normalized = dict(people=people, cutoffs=results["cutoffs"],
          means={m: v["bilateral"] for m,v in results["mean_person_mae_deg"].items()}, comparisons=[])
    for pair, value in results["paired_person_differences_deg"].items():
        a,b=pair.split("_minus_")
        normalized["comparisons"].append(dict(a=a,b=b,mean=value["mean"],ci=value["ci95"],wins=value["wins"],ties=value["ties"],losses=value["losses"]))
    scored=results["paired_person_differences_deg"]
    if not all(scored["transformer_residual_minus_"+comp]["wins"] == 12 for comp in ["prior_stride","ridge_residual"]):
        raise ValueError("The comparative text must be reviewed for these results")
    normalized["outcome"]="The knee-trained Transformer gave smaller mean errors than both alternatives for every one of these 12 walkers. Fresh walkers would test whether that advantage carries over."

    shared = json.loads((SRC/"shared-knee.json").read_text())
    scores = shared["scores"]
    if scores["checkpoint_sha256"] != shared["checkpoint_sha256"] or scores["cutoffs"] != results["cutoffs"]:
        raise ValueError("Shared study identity mismatch")
    transfer_people = []
    for p in scores["per_person"]:
        mae={m: dict(right=v[0],left=v[1],bilateral=sum(v)/2) for m,v in p["mae_degrees"].items()}
        transfer_people.append(dict(id=p["person"],cutoffs=p["cutoffs"],mae=mae))
    if [(p["id"],p["cutoffs"]) for p in transfer_people] != [(p["id"],p["cutoffs"]) for p in people]:
        raise ValueError("Shared study and knee-trained participant windows differ")
    if scores["shared_advantage_criterion_met"] or scores["mae_degrees"]["shared"] <= min(scores["mae_degrees"][m] for m in ("raw","scrambled")):
        raise ValueError("Review the shared comparison interpretation")
    transfer=dict(people=transfer_people,cutoffs=scores["cutoffs"],means=scores["mae_degrees"],comparisons=[],
           outcome="The frozen encoder beat stride replay on average. Measurements alone gave a slightly smaller mean error, and the shuffled encoder gave the smallest. This comparison found no advantage from the encoder’s learned weights.")
    for b,v in scores["comparisons"].items():
        transfer["comparisons"].append(dict(a="shared",b=b,mean=v["shared_minus_comparator_deg"],ci=v["paired_ci95"],
              wins=v["shared_wins"],ties=v["ties"],losses=len(people)-v["shared_wins"]-v["ties"]))
    return dict(weights=fit,shared=shared,scores=dict(specialist=normalized,transfer=transfer),
        source=dict(columns=source["columns"],frame_column=source["frame_column"],members=members))

def build(model):
    study = json.dumps(assembled(model),separators=(",",":"),allow_nan=False).replace("<",r"\u003c")
    scripts="\n".join((SRC/name).read_text() for name in ["forecast.js","shared-knee.js","input.js","view.js"])
    return (SRC/"page.html").read_text().replace("__STYLE__",(SRC/"style.css").read_text()).replace("__CDLA__",html.escape((HERE/"CDLA-Permissive-2.0.txt").read_text())).replace("__STUDY__",study).replace("__SCRIPTS__",scripts)

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",type=Path,default=HERE.parents[1]/"models/knee-stride")
    p.add_argument("--out",type=Path,default=HERE/"index.html")
    args=p.parse_args()
    args.out.write_text(build(args.model),encoding="utf-8")
