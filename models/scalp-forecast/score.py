"""Score frozen models on identical paired rows; no fitting or PyTorch dependency."""
import numpy as np
from predict import METHODS,batch

CONTRASTS = {
    "scalp_over_history":("scalp","history"),"scalp_over_wrong_pair":("scalp","scalp_shift"),
    "scalp_over_wrong_fit":("scalp","mispaired_fit_shift"),"scalp_over_eye":("scalp","eye"),
    "equal_width_scalp_over_eye":("bilateral","eye"),
    "combined_over_eye_history":("scalp_eye","eye"),
    "combined_over_wrong_scalp":("scalp_eye","scalp_eye_shift"),
    "attention_over_ridge":("scalp","ridge"),"scalp_over_history_ridge":("scalp","history_ridge"),
    "scalp_over_cue_median":("scalp","cue_median"),"scalp_over_cue_mean":("scalp","cue_mean"),
    "scalp_over_still":("scalp","still"),"scalp_only_over_eye_only":("scalp_only","eye_only")}
PRACTICAL = ("scalp_over_history","scalp_over_history_ridge","scalp_over_cue_median","scalp_over_cue_mean",
             "scalp_over_still","scalp_over_wrong_pair","scalp_over_wrong_fit")
BEYOND_EYE = ("scalp_over_eye","combined_over_eye_history","combined_over_wrong_scalp")


def people_results(model,rows):
    h,s,e,y,g = rows
    cue,flat = g[:,2],y.reshape(-1,9)
    errors = {m:np.abs(batch(model,h,s,e,cue,m)-flat) for m in METHODS}
    groups = np.unique(g[:,:3],axis=0)
    eligible = not any(model["constant_targets"])
    # Scoring constructs its own donor sets from source keys and onset order.
    for m in ("scalp","scalp_eye","mispaired_fit"):
        wrong = np.full_like(flat,np.nan)
        for key in groups:
            mask = np.flatnonzero((g[:,:3]==key).all(axis=1))
            ix = mask[np.argsort(g[mask,3])]
            if len(ix)<2:
                eligible = False
                continue
            losses = [np.abs(batch(model,h[ix],s[np.roll(ix,-offset)],e[ix],cue[ix],m)-flat[ix])
                      for offset in range(1,len(ix))]
            wrong[ix] = np.mean(losses,axis=0)
        errors[m+"_shift"] = wrong
    result = []
    for person in np.unique(g[:,0]):
        sel = g[:,0]==person
        runs = np.unique(g[sel,1])
        expected_runs = (1,2,3) if person<=7 else (4,)
        complete = eligible and tuple(runs)==expected_runs
        scores = {}
        for m,error in errors.items():
            run_maes = []
            for run in runs:
                cells = []
                for code in range(7):
                    mask = sel & (g[:,1]==run) & (cue==code)
                    if mask.sum()!=6:
                        complete=False
                    if mask.any() and np.isfinite(error[mask]).all():
                        cells.append(error[mask].mean(axis=0))
                if cells:
                    run_maes.append(np.mean(cells,axis=0))
            if not run_maes:
                raise ValueError("No paired score for this participant")
            native = np.mean(run_maes,axis=0)
            scores[m] = {"normalized_mae":float(np.mean(native/model["target_sd"])),
                         "native_mae":native.reshape(3,3).tolist()}
        result.append({"person":int(person),"n_trials":int(sel.sum()),"complete":bool(complete),"methods":scores})
    return result


def summarize(people,assessment):
    expected = list(range(8,13)) if assessment else list(range(1,8))
    if sorted(p["person"] for p in people)!=expected:
        raise ValueError("Missing or duplicate participant")
    size = len(people)
    complete = all(p["complete"] for p in people)
    names = people[0]["methods"]
    errors = {m:np.array([p["methods"][m]["normalized_mae"] for p in people]) for m in names}
    methods = {m:{"normalized_mae":float(v.mean()),"native_mae":np.mean(
        [p["methods"][m]["native_mae"] for p in people],axis=0).tolist()} for m,v in errors.items()}
    idx = np.random.default_rng(71293).integers(0,size,size=(10000,size))
    contrasts = {}
    for name,(a,b) in CONTRASTS.items():
        delta = errors[a]-errors[b]
        rel = float(1-errors[a].mean()/errors[b].mean()) if errors[b].mean()>0 else None
        passes = assessment and complete and rel is not None and rel>=0.05 and np.all(delta<0)
        contrasts[name] = {"candidate":a,"comparator":b,"mean_difference":float(delta.mean()),
                           "paired_95pct":np.quantile(delta[idx].mean(axis=1),[0.025,0.975]).tolist(),
                           "fraction_lower":rel,"people_lower":int((delta<0).sum()),
                           "paired_differences":delta.tolist(),"gate":bool(passes) if assessment and complete else None}
    gates = {}
    for name,keys in (("engineering_advantage",PRACTICAL),("increment_beyond_measured_eyes",BEYOND_EYE)):
        keys = tuple(dict.fromkeys(PRACTICAL+keys)) if name.startswith("increment") else keys
        gates[name] = all(contrasts[k]["gate"] for k in keys) if assessment and complete else None
    # Only participant-level scalar errors/differences; no individual target profiles or trial arrays.
    return {"format":"early-scalp-comparison-v1","stage":"fourth_run" if assessment else "leave_one_person_out",
            "n_people":size,"n_trials":sum(p["n_trials"] for p in people),"complete":complete,
            "participant_order":expected,"methods":methods,"contrasts":contrasts,"gates":gates,
            "person_errors":{m:v.tolist() for m,v in errors.items()}}
