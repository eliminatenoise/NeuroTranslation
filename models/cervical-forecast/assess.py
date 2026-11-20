"""Apply frozen fits to new people. No fit, participant normalization or model selection."""
import argparse
import json
import math
from pathlib import Path
import sys
import numpy as np


def sign_p(gains):
    positive, negative = sum(x > 0 for x in gains), sum(x < 0 for x in gains)
    n = positive + negative
    return min(1, 2 * sum(math.comb(n, i) for i in range(min(positive, negative) + 1)) / 2**n)


def report(rows, full, controls, min_people, margin):
    macro = {method: {name: float(np.mean([r[method][name] for r in rows])) for name in metrics}
             for method, metrics in rows[0].items()}
    gains = {m: [r[m]["mae_uV"] - r[full]["mae_uV"] for r in rows] for m in controls}
    ordered = sorted(zip(*gains.values()))
    paired = {m: [v[i] for v in ordered] for i, m in enumerate(controls)}
    both = sum(all(v > 0 for v in pair) for pair in zip(*gains.values()))
    return {"macro": macro, "people_improved_on_both": both,
            "criterion_met": both >= min_people and all(
                macro[full]["mae_uV"] <= (1 - margin) * macro[m]["mae_uV"] if margin
                else macro[full]["mae_uV"] < macro[m]["mae_uV"] for m in controls),
            "contrasts": {m: {"mean_gain_uV": float(np.mean(v)), "range_uV": [min(v), max(v)],
                              "people_improved": sum(g>0 for g in v), "exact_two_sided_sign_p": sign_p(v), "paired_gains_uV": paired[m]} for m,v in gains.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="Directory containing the six assessment NPZ files and acquisition receipts.")
    parser.add_argument("out", type=Path, help="A new JSON file for the cohort results.")
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    sys.path.insert(0, str(base / "robust"))
    if args.out.exists():
        parser.error("Choose a new JSON output path.")
    from evaluation import errors, sealed_predictions, load_npz
    from forward import predict
    from study import load
    from forecast import INPUTS, with_anchor
    def read(p): return json.loads(p.read_bytes())
    def save(p, obj): p.write_text(json.dumps(obj, indent=2, allow_nan=False)+"\n")
    weights=read(base/"export"/"weights.json")
    controls=read(base/"export"/"controls.json")
    model=read(base/"robust"/"model.json")
    transformer_rows=[]; robust_rows=[]
    for index in range(5,11):
        sid=f"sub-{index:03d}"
        file=args.data/("assessment-"+sid+".npz")
        receipt=args.data/(sid+"-receipt.json")
        if read(receipt)["subject"]!=sid: raise ValueError("Wrong assessment subject")
        raw,baseline,target=load_npz(file,receipt)
        z,y=load(file, receipt)
        np.testing.assert_allclose(target,y,atol=1e-10,rtol=0)
        order=np.arange(len(y)); people=np.zeros(len(y),int)
        tp=sealed_predictions(raw,baseline,order,people,weights,controls)
        # The target's early axillary bins come from the event 37 places ahead.
        wrong=raw.copy()
        wrong[:,10:,0]=np.roll(raw[:,10:,0],-37,axis=0)
        tp["transformer_same_fit_wrong"]=predict(wrong,order,weights,"eng")
        tp["neck_persistence"]=z[:,-1,1]
        transformer_rows.append(errors(y,tp))
        anchor=z[:,-1,1]
        rp={m:with_anchor(m,model,z,anchor) for m in INPUTS}
        other=z.copy()
        other[:,:,0]=np.roll(z[:,:,0],-37,axis=0)
        rp["wrong_event"]=with_anchor("with_axilla",model,other,anchor)
        robust_rows.append(errors(y,rp))
    save(args.out,{"scope":"six new people within the original study", "participants":6,"events":480,
        "transformer":report(transformer_rows,"transformer_eng",["transformer_noneng","transformer_same_fit_wrong"],5,0),
        "robust":report(robust_rows,"with_axilla",["other_sites","wrong_event"],6,.05)})
if __name__=="__main__": main()
