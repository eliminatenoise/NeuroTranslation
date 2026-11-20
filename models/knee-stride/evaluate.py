"""Score a frozen training checkpoint on the twelve previously studied people."""
import argparse
import json
from pathlib import Path

import numpy as np

from extract import TEST, TRAIN
from predict import MODELS, forecast, predictions
from trials import PROTOCOL_SHA256, digest, load_trial, save


PAIRS = (("ridge_residual","prior_stride"), ("transformer_residual","prior_stride"),
         ("transformer_residual","ridge_residual"))


def evaluate(cache, weights_path, fit_path):
    weights = json.loads(weights_path.read_text())
    fit = json.loads(fit_path.read_text())
    train_members = fit["trained_members"]
    weight_hash = digest(weights_path)
    if (fit["benchmark"] or fit["updates"] != 1600 or fit["weights_sha256"] != weight_hash or
            fit["protocol_sha256"] != PROTOCOL_SHA256 or [m["participant"] for m in train_members] != list(TRAIN)):
        raise ValueError("Expected the final frozen training checkpoint")
    previous = {m["knee_series_sha256_le_f8"] for m in train_members}
    rows, max_difference, controls = [], 0., 0
    for person in TEST:
        t = load_trial(cache, person)
        ident = t.join["knee_series_sha256_le_f8"]
        if ident in previous:
            raise ValueError("Duplicate knee trace. Stop for source review.")
        previous.add(ident)
        measures = {name: [] for name in MODELS}
        for start in range(0, len(t.cuts), 256):
            ix = slice(start, start+256)
            for name, pred in predictions(t.tokens[ix], t.stride[ix], weights).items():
                measures[name].append(np.abs(pred - t.target[ix]))
        mae = {}
        for name, chunks in measures.items():
            errors = np.concatenate(chunks).mean(axis=0)
            mae[name] = dict(bilateral=float(errors.mean()), right=float(errors[0]), left=float(errors[1]))
        for j in (0,len(t.cuts)//2,len(t.cuts)-1):
            cut = t.cuts[j]
            history = slice(cut-239,cut+1)
            original = forecast(t.frames[history],t.knees[history],weights)
            alternate = t.knees.copy()
            alternate[cut+1:] += 123
            changed = forecast(t.frames[history],alternate[history],weights)
            if original != changed or not np.allclose(alternate[cut+15]-t.target[j],123,rtol=0,atol=1e-10):
                raise ValueError("Prefix forecast changed or future-target control failed")
            scalar_period = min(range(45,181),key=lambda p:np.sum((t.knees[cut-59:cut+1]-t.knees[cut-p-59:cut-p+1])**2))
            if t.periods[j] != scalar_period or original["period_frames"] != scalar_period:
                raise ValueError("Direct and rolling period selection differ")
            fast = predictions(t.tokens[j:j+1],t.stride[j:j+1],weights)
            for name in MODELS:
                max_difference = max(max_difference, float(np.abs(fast[name][0]-original[name]).max()))
            controls += 1
        rows.append(dict(**t.join, mae_deg=mae, paired_differences_deg={a+"_minus_"+b:mae[a]["bilateral"]-mae[b]["bilateral"] for a,b in PAIRS}))
    avg = {m:{axis:float(np.mean([r["mae_deg"][m][axis] for r in rows])) for axis in ("bilateral","right","left")} for m in MODELS}
    idx = np.random.default_rng(21301).integers(0,len(rows),size=(10000,len(rows)))
    comparisons = {}
    for a,b in PAIRS:
        key = a+"_minus_"+b
        delta = np.array([r["paired_differences_deg"][key] for r in rows])
        lo,hi = np.quantile(delta[idx].mean(axis=1),[.025,.975])
        wins = int((delta<0).sum())
        comparisons[key] = dict(mean=float(delta.mean()),ci95=[float(lo),float(hi)],wins=wins,
                                ties=int((delta==0).sum()),losses=int((delta>0).sum()),
                                passed_registered_criterion=bool(delta.mean()<0 and hi<0 and wins>=8))
    total = sum(r["cutoffs"] for r in rows)
    if total != 40201 or abs(avg["prior_stride"]["bilateral"]-3.5352540464780127)>1e-8 or max_difference>.001:
        raise ValueError("Coverage, control replication or CLI parity failed")
    return dict(format="two-knee-stride-results-1",protocol_sha256=PROTOCOL_SHA256,weights_sha256=weight_hash,
                domain="Stored Xsens knee flexion/extension at 0.5 m/s, single treadmill recording per person. Reused descriptive evaluation cohort.",
                people=len(rows),cutoffs=total,train_people=len(train_members),train_cutoffs=fit["train_cutoffs"],
                mean_person_mae_deg=avg,paired_person_differences_deg=comparisons,participants=rows,
                controls=dict(future_target_shift_degrees=123, tested_cutoffs=controls,
                              future_change_max_prediction_difference_deg=0, maximum_fast_vs_scalar_forecast_difference_deg=max_difference),
                training_join=train_members)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for param in ("cache","weights","fit_receipt","results"):
        p.add_argument(param,type=Path)
    args=p.parse_args()
    if args.results.exists():
        p.error("Give the evaluation a fresh output path")
    save(args.results,evaluate(args.cache,args.weights,args.fit_receipt))
