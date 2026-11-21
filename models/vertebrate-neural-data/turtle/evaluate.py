"""Apply the fixed rat-trained scoring rule to the published turtle spike-cluster recording."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
from scipy.io import loadmat

MAT_SHA256="e5a609e6dc28c05a88d51e71cdfd74cc6f6107958aed7592dee3a88fe3ba7881"
MODEL_SOURCE="3514e7925fd9c833ab5f939513991eadb04b246cab3d63ee320e807410251f61"
MODEL_WEIGHTS="25f9d22ee284b794c1a4f7019587b6e4b92631ab04ff9664266045aa4718ecad"

def main(mat, scorer, declared_roster=False):
    if hashlib.sha256(mat.read_bytes()).hexdigest()!=MAT_SHA256:raise ValueError("Unexpected turtle figure source")
    if hashlib.sha256((scorer/"benchmark.py").read_bytes()).hexdigest()!=MODEL_SOURCE:raise ValueError("Unexpected rat scorer")
    if hashlib.sha256((scorer/"weights.json").read_bytes()).hexdigest()!=MODEL_WEIGHTS:raise ValueError("Unexpected rat-trained weights")
    sys.path.insert(0,str(scorer))
    from benchmark import evaluate,read_trial
    spikes=loadmat(mat,simplify_cells=True)["spikes"]
    def native_ticks(milliseconds):
        value=np.asarray(milliseconds,dtype=float)*20
        if not np.isfinite(value).all() or np.max(np.abs(value-np.rint(value)))>1e-6:
            raise ValueError("Time outside the author-reported 20 kHz acquisition clock")
        return np.rint(value).astype(np.int64)
    times=native_ticks(spikes["spiketime"])
    ids=np.asarray(spikes["cluster"],int)
    declarations=np.asarray(spikes["clusterIdentity"],int)
    assert len(ids)==len(times) and np.isfinite(times).all() and len(np.unique(declarations))==len(declarations)
    assert np.isin(ids,declarations).all()
    onsets=native_ticks(spikes["onStim_sorted"])
    windows=[]
    # All indices saved by the figure script share one recording clock. Restore chronological order.
    for row in np.argsort(onsets,kind="stable"):
        start,stop=onsets[row]-10000,onsets[row]+50000
        if start<times.min() or stop>times.max() or (windows and start<windows[-1][2]):continue
        windows.append((int(row),int(start),int(stop)))
        if len(windows)==40:break
    if len(windows)<=20:raise ValueError("Insufficient nonoverlapping test windows")
    seen=set()
    for _,start,stop in windows[:20]:
        seen.update(ids[(times>start)&(times<stop)].tolist())
    candidates=np.array(sorted(declarations if declared_roster else seen))
    if len(candidates)<2:raise ValueError("No eligible population")
    model=json.loads((scorer/"weights.json").read_bytes())
    trials=[];cut=0;dropped=0
    with tempfile.TemporaryDirectory() as scratch:
        for row,start,stop in windows[20:]:
            select=(times>start)&(times<stop)
            novel=select&~np.isin(ids,candidates)
            if np.any(novel):
                stop=int(times[novel].min());cut+=1
                select&=times<stop
            if stop<=start: dropped+=1;continue
            arrays=[np.sort(times[select&(ids==c)])/20000.0 for c in candidates]
            p=Path(scratch)/"trial.npz"
            np.savez(p,trial_id=np.int64(row),start_s=start/20000.0,stop_s=stop/20000.0,unit_id=candidates,spike_end=np.cumsum([len(a) for a in arrays]),spike_time_s=np.concatenate(arrays))
            trials.append(read_trial(p,row))
    results=evaluate(trials,model,False)
    return {"study":"Frozen sorted-unit forecaster on a turtle cortical spike-cluster recording",
            "archive":"10.5061/dryad.k98sf7mm6","recording":str(spikes["recname"]),"published_figure_source":"https://github.com/EvolutionaryNeuralCodingLab/SpatiallySelectiveViewInvariance/blob/b421ce0a62140a812e964cb027b97f979e98f049/plot_Fig1h.m",
            "animals":1,"recordings":1,"declared_cluster_count":len(declarations),"candidate_clusters_seen_in_initial_windows":len(seen),"candidate_count":len(candidates),
            "analysis":"supplementary native declared roster" if declared_roster else "registered earlier observed roster",
            "source_stimulus_onsets":len(onsets),"roster_windows":20,"selected_test_windows":len(windows)-20,
            "test_windows_truncated_for_new_cluster":cut,"windows_unavailable_after_truncation":dropped,"scored_trial_windows":len(trials),
            "fitted_on_target":False,"unit_quality":"Original spike-cluster identities. The authors describe the illustrated unit as putative. Cluster-specific isolation, refractory-violation and continuous detectability data are unavailable here. A screened subset named sig_units was not used.",
            "results":results}

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mat",type=Path);cli.add_argument("scorer",type=Path,help="Path to the released next-neuron-prediction model directory");cli.add_argument("out",type=Path)
    cli.add_argument("--declared-roster",action="store_true",help="Supplementary comparison using all originally declared cluster IDs, including those unobserved on initialization trials.")
    args=cli.parse_args()
    args.out.write_text(json.dumps(main(args.mat,args.scorer.resolve(),args.declared_roster),indent=2,allow_nan=False)+"\n")
