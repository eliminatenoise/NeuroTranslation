"""Check the frozen September 7 coefficients and score chronological training holdbacks."""
from pathlib import Path
import hashlib
import json
import numpy as np
from fit import ARMS, RIDGE, features, fit_one, pool, predict

import argparse
cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument("source",type=Path)
cli.add_argument("weights",type=Path)
cli.add_argument("out",type=Path)
args=cli.parse_args()
path=args.source
weights=args.weights
fit=json.loads(weights.read_bytes())
assert fit["source_sha256"]==hashlib.sha256(path.read_bytes()).hexdigest()
with np.load(path,allow_pickle=False) as z:
    src={k:z[k] for k in z.files}
guide=src["unit_guide"]
contacts=np.unique(guide[:,0])
ids=src["original"]
def averaging(ids):
    group,inverse,counts=np.unique(ids,return_inverse=True,return_counts=True)
    return 1/(len(group)*counts[inverse])

def newton(z,y,w):
    x=np.column_stack((np.ones(len(z)),z))
    beta=np.zeros(x.shape[1]);beta[0]=np.log(w@y)
    penalty=np.r_[0.,np.full(z.shape[1],RIDGE)]
    def value(b):
        lin=x@b
        return w@(np.exp(lin)-y*lin)+0.5*penalty@(b*b)
    for _ in range(50):
        rate=np.exp(x@beta);grad=x.T@(w*(rate-y))+penalty*beta
        if np.linalg.norm(grad,np.inf)<3e-10:break
        step=np.linalg.solve(x.T@((w*rate)[:,None]*x)+np.diag(penalty),grad)
        scale=1.;obj=value(beta)
        while scale>1e-10 and value(beta-scale*step)>obj+1e-15:
            scale*=0.5
        beta-=scale*step
    assert np.linalg.norm(grad,np.inf)<2e-8
    return np.exp(x@beta)

def score(y,mu):
    if np.any(mu<=0) or not np.all(np.isfinite(mu)):raise ValueError("Poisson intensity")
    logterm=np.zeros_like(mu)
    good=y>0
    logterm[good]=y[good]*np.log(y[good]/mu[good])
    return 2*(mu-y+logterm)

def ci(diff):
    roster=src["roster_original"][src["roster_fold"]>0]
    per=np.array([np.mean(diff[ids==i]) for i in roster])
    rng=np.random.default_rng(20261125)
    starts=rng.integers(0,len(roster)-7,(5000,(len(roster)+7)//8))
    draw=(starts[:,:,None]+np.arange(8)).reshape(5000,-1)[:,:len(roster)]
    return {"mean":float(per.mean()),"block_of_eight_95":np.quantile(per[draw].mean(1),[.025,.975]).tolist()}

def run():
    supported=src["fold"]>0
    w=averaging(ids)
    errors={arm:np.full((len(ids),len(contacts)),np.nan) for arm in ARMS}
    worst=0.0
    for j,contact in enumerate(contacts):
        y=pool(src["delayed"],guide,contact).sum(1)
        for arm in ARMS:
            x=features(src,contact,arm)
            model=fit["arms"][arm][str(contact)]
            z=np.clip((x-w@x)/np.maximum(np.sqrt(w@((x-w@x)**2)),1e-8),-8,8)
            q=newton(z,y,w)
            worst=max(worst,float(np.max(np.abs(q-predict(x,model))/(q+1e-9))))
            for part in range(1,5):
                train=src["fold"]<part
                valid=src["fold"]==part
                assert not set(ids[train])&set(ids[valid])
                foldmodel=fit_one(x[train],y[train],averaging(ids[train]))
                errors[arm][valid,j]=score(y[valid],predict(x[valid],foldmodel))
    assert worst<3e-5,worst
    for arm in ARMS:
        assert np.isfinite(errors[arm][supported]).all() and np.isnan(errors[arm][~supported]).all()
    avg={arm:errors[arm].mean(1) for arm in ARMS}
    out={"training_day":"2017-09-07","other_day_numeric_reads":0,"forward_originals":len(np.unique(ids[supported])),
         "forward_windows":int(supported.sum()),"training_contacts":contacts.tolist(),"fold_fit_count":len(contacts)*len(ARMS)*4,
         "separately_recomputed_full_fit_count":len(contacts)*len(ARMS),"max_relative_rate_difference_independent_newton":worst,
         "weights_sha256":hashlib.sha256(weights.read_bytes()).hexdigest(),"source_sha256":fit["source_sha256"],
         "held_training_original_deviance":{arm:ci(loss) for arm,loss in avg.items()},
         "measured_minus_stale":ci(avg["measured_update"]-avg["stale_position"]),
         "scope":"Chronological holdbacks within the reserved training groups on September 7. The September 14 signals remain unseen. These internal checks do not estimate day transfer."}
    args.out.write_text(json.dumps(out,indent=2)+"\n")

if __name__=="__main__":
    run()
