"""Check sampling, masks, independent scalar inference, held example and optional exact re-fit."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import torch

from predict import predict_count
from train_afferent import group_trials, source_windows
from train import CountTransformer, FOLDS, MODES, SEEDS, draw_plan, earlier_rows, load_data, normalizer, save_json, sha256, training_groups

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--refit",type=Path,required=True)
    p.add_argument("--split",choices=("prefix","afferent"),default="prefix")
    args=p.parse_args()
    out=args.out
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    aff_split=args.split=="afferent"
    raw,info=(source_windows if aff_split else load_data)(args.data)
    splits=np.unique(info[args.split]).tolist()
    selected_held="aff015" if aff_split else 0
    split_name=lambda value: str(value) if aff_split else "prefix"+str(value)
    with np.load(args.data,allow_pickle=False) as d:
        cutoff=d["cutoff_s"]
    acceptable_error=.00003
    modes=list(MODES)
    arch=CountTransformer().eval()
    rng=np.random.default_rng(47813)
    synthetic=[]
    for j in range(8):
        a=rng.normal(0,1+10*j,size=(5,5))
        a[:,4]=rng.integers(0,10,size=5)
        synthetic.append(a.tolist())
    synthetic.extend([np.zeros((5,5)).tolist(),[[1e12,-1e12,1e12,-1e12,20] for _ in range(5)]])
    fixtures=[]
    cases=[]
    errors=[]
    selected_name=split_name(selected_held)+"-seed1641-all.json"
    with np.load(out/"oof.npz",allow_pickle=False) as oo, np.load(out/"train-row-samples.npz",allow_pickle=False) as plans:
        assert all(np.array_equal(info[k],oo[k]) for k in info)
        lag=earlier_rows(info)
        assert np.array_equal(oo["earlier_row"],lag)
        ok=lag>=0
        assert all(np.array_equal(info[k][ok],info[k][lag[ok]]) for k in ("afferent","trial","prefix"))
        assert np.all(info["bin_index"][ok]-info["bin_index"][lag[ok]]==5)
        assert np.allclose(cutoff[ok]-cutoff[lag[ok]],.1,rtol=0,atol=1e-8)
        rates=oo["rate"]; wrong=oo["wrong_mechanics"]
        assert np.isfinite(rates).all() and np.all(rates>0)
        assert np.all(np.isfinite(wrong[ok])) and np.all(wrong[ok]>0) and np.isnan(wrong[~ok]).all()
        for fold_ix, fold in enumerate(splits):
            held=np.flatnonzero(info[args.split]==fold)
            groups=(group_trials if aff_split else training_groups)(info,fold); mean,sd=normalizer(raw,groups)
            probe=held[np.linspace(0,len(held)-1,6,dtype=int)]
            for seed in SEEDS:
                si=SEEDS.index(seed)
                plan=plans[f"{split_name(fold)}-seed{seed}"]
                assert np.array_equal(draw_plan(groups,seed,fold_ix if aff_split else fold),plan)
                assert np.all(info[args.split][plan]!=fold)
                for mode in modes:
                    key=f"{split_name(fold)}-seed{seed}-{mode}.json"
                    weights=json.loads((out/"checkpoints"/key).read_text())
                    assert np.array_equal(weights['normalizer']['mean'],mean) and np.array_equal(weights['normalizer']['sd'],sd)
                    assert weights["active"]==list(MODES[mode]) and weights["held_"+args.split]==fold
                    for row in probe:
                        cases.append({"file":key,"history":raw[row].tolist(),"target":float(rates[row,modes.index(mode),si])})
                    if mode=="all":
                        shifted=held[ok[held]]
                        for row in shifted[np.linspace(0,len(shifted)-1,5,dtype=int)]:
                            m=raw[row].copy(); m[:,:4]=raw[lag[row],:,:4]
                            cases.append({"file":key,"history":m.tolist(),"target":float(wrong[row,si])})
                    if key==selected_name:
                        arch.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in weights["weights"].items()})
                        hist=np.asarray(synthetic,dtype=np.float64)
                        with torch.no_grad():
                            expected=arch(torch.tensor(np.clip((hist-mean)/sd,-10,10),dtype=torch.float32)).numpy()
                        for n,(trial_history,target) in enumerate(zip(synthetic,expected)):
                            item={"history":trial_history,"target":float(target)}
                            fixtures.append({"name":"synthetic-"+str(n),"origin":"synthetic","expected_spikes_next_20ms":float(target),"history":trial_history})
                            cases.append({"file":key,**item})
        mask=(info["afferent"]=="aff015")&(info["trial"]==1)
        example=np.flatnonzero(mask)
        assert len(example)>0 and np.all(info["prefix"][example]==0)
        checkpoint=out/"checkpoints"/selected_name
        assert sha256(checkpoint)==sha256(args.refit/selected_name)
        selected=rates[info[args.split]==selected_held,modes.index("all"),0]
        rebuilt=np.load(args.refit/"refit.npy",allow_pickle=False)
        assert np.array_equal(selected,rebuilt)
        with (out/"aff015-trial1.csv").open("w",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(["target_bin","cutoff_s","observed_count",*modes,"wrong_mechanics"])
            for row in example:
                writer.writerow([int(info["bin_index"][row]),float(cutoff[row]),int(info["y_count"][row]),*map(float,rates[row,:,0]),
                                 float(wrong[row,0]) if ok[row] else ""])
        for row in example[np.linspace(0,len(example)-1,5,dtype=int)]:
            fixtures.append({"name":"aff015-trial1-bin-"+str(int(info["bin_index"][row])),"origin":"recorded held example",
                            "expected_spikes_next_20ms":float(rates[row,modes.index("all"),0]),"history":raw[row].tolist()})
        by_prefix={str(p):{"rows":int(np.sum(info["prefix"]==p)),"matched_rows":int(np.sum(ok & (info["prefix"]==p))),
                           "members":np.unique(info["afferent"][info["prefix"]==p]).tolist()} for p in np.unique(info["prefix"])}
        by_aff={str(a):{"rows":int(np.sum(info["afferent"]==a)),"matched_rows":int(np.sum(ok & (info["afferent"]==a)))} for a in np.unique(info["afferent"])}
    models={}
    for case in cases:
        key=case["file"]
        if key not in models:
            models[key]=json.loads((out/"checkpoints"/key).read_text())
        errors.append(abs(predict_count(models[key],case["history"])-case["target"]))
    invalid=[
      None,[],[[0]*5]*4,[[0]*4]*5,[[0,0,0,0,-1]]*5,[[0,0,0,0,.5]]*5,[[0,0,0,0,2**53]]*5,
      [[0,0,"1",0,0]]*5,[[True,0,0,0,0]]*5,[[0,0,None,0,0]]*5]
    for hist in invalid+[[[float("nan"),0,0,0,0]]*5,[[float("inf"),0,0,0,0]]*5]:
        try:
            predict_count(models[selected_name],hist)
        except ValueError:
            continue
        raise RuntimeError("invalid input accepted in Python")
    js=Path(__file__).resolve().with_name("predict.mjs").as_uri()
    script="""
import { readFileSync } from 'node:fs';
const { predictCount }=await import(process.argv[1]);
const d=JSON.parse(readFileSync(0, 'utf8'));
const err=d.cases.map(c=>Math.abs(predictCount(d.models[c.file],c.history)-c.target));
const model=d.models[d.selected];
for(const x of [...d.invalid,Array(5).fill(Array(5)),Array(5),Array(5).fill([NaN,0,0,0,0]),Array(5).fill([Infinity,0,0,0,0])]){
 let rejected=false;
 try{predictCount(model,x)}catch(e){rejected=true}
 if(!rejected)throw Error('invalid history accepted')
}
console.log(JSON.stringify({max_abs:Math.max(...err),n:err.length,invalid:d.invalid.length+4}));
"""
    jsrun=subprocess.run(["node","--input-type=module","-e",script,js],input=json.dumps(dict(cases=cases,models=models,selected=selected_name,invalid=invalid)),text=True,check=True,capture_output=True)
    jsresult=json.loads(jsrun.stdout)
    assert max(errors)<=acceptable_error and jsresult["max_abs"]<=acceptable_error
    save_json(out/"fixtures.json",{"checkpoint":selected_name,"cases":fixtures,"absolute_tolerance":acceptable_error})
    save_json(out/"history-example.json",fixtures[-1]["history"])
    save_json(out/"verification.json",{"fit_count":len(models),"split":args.split,"rows_by_native_filename_prefix":by_prefix,"rows_by_afferent":by_aff,"deployment_checkpoint":selected_name,
             "train_probe_plan":f"All full batch plans reproduced; zero held {args.split} training rows; train-only fold scales replayed.",
             "control":"Exactly five target bins / 100 ms apart, same afferent, trial and prefix on all matched rows. Missing predictions are NaN only on structurally unavailable control rows.",
             "full_refit_weights_byte_identical":True,"refit_held_group":selected_held,"full_refit_held_predictions_bit_identical":True,
             "selected_group_oof_count":len(selected),"held_aff015_trial1_rows":len(example),
             "max_abs_pytorch_vs_python":max(errors),"max_abs_pytorch_vs_js":jsresult['max_abs'],"inference_cases":len(cases),"runtimes_checked":["Python standard library","JavaScript Node ESM bridge"],
             "invalid_python_rejections":len(invalid)+2,"invalid_js_rejections":jsresult['invalid'],"absolute_tolerance":acceptable_error,
             "synthetic_fixture_count":len(synthetic),"recorded_fixture_count":len(fixtures)-len(synthetic)})
if __name__=="__main__":
    main()
