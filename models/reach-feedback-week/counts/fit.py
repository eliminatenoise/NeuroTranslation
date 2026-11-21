"""Fit two fixed Poisson forecasts for each of three cortical count endpoints."""
import argparse
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from forecast import POPULATIONS, build_design, channels, contact_map, group_columns, predict, totals, write_json
from inputs import TRAIN_KEYS, load, validate_train
from roster import digest, require


def original_weights(block, original):
    _, index, sizes = np.unique(np.column_stack((block,original)),axis=0,return_inverse=True,return_counts=True)
    return 1.0 / (len(sizes)*sizes[index])


def standardize(x, w):
    mean = np.average(x,axis=0,weights=w)
    constant = (np.max(x,axis=0) == np.min(x,axis=0))
    mean[constant] = x[0,constant]
    scale = np.sqrt(np.average((x-mean)**2,axis=0,weights=w))
    scale[constant] = 1.
    require(np.all(np.isfinite(scale) & (scale>0)), "Nonfinite feature scale")
    return (x-mean)/scale, mean, scale


def objective(beta, z, y, w):
    eta = beta[0] + z @ beta[1:]
    mu = np.exp(eta)
    resid = w * (mu-y)
    return (w @ (mu - y * eta) + .005 * (beta[1:] @ beta[1:]),
            np.r_[resid.sum(), z.T @ resid + .01 * beta[1:]])


def fit_head(z, y, w):
    require(w@y > 0, "Entire training response silent; finite unpenalized intercept unavailable")
    start = np.zeros(z.shape[1]+1)
    start[0] = np.log(w @ y)
    res = minimize(objective, start, args=(z,y,w), jac=True, method="L-BFGS-B",
                   options={"maxiter":1000, "ftol":1e-9, "gtol":1e-8, "maxls":50})
    require(res.success and np.isfinite(res.x).all() and np.isfinite(res.fun) and np.isfinite(res.jac).all(),
            f"Fit did not converge: {res.message}")
    return res.x, {"iterations":int(res.nit), "objective":float(res.fun),
                   "max_abs_gradient":float(abs(res.jac).max()), "termination":str(res.message)}


def fit_pack(p, mapping, qualification=False):
    validate_train(p,mapping)
    w = original_weights(p["block"],p["original"])
    primary = channels(mapping,"primary")
    h, valid = totals(p["all_history"],group_columns(p["all_guide"],primary,"primary"))
    require(valid.all(), "Missing registered training input")
    base, residual = build_design(p["pose"],p["cue_at_k"],h,p["movement"][:,-1])
    require(np.isfinite(base).all() and np.isfinite(residual).all(), "Missing registered training input")
    standardized = {a:standardize(x,w) for a,x in (("base",base),("update",np.column_stack((base,residual))))}
    fit = {"training_date":"2017-09-07", "training_keys_sha256":TRAIN_KEYS, "windows":len(w), "originals":198,
           "primary_input_contacts":primary, "populations":{}}
    diag = {}
    for pop in POPULATIONS:
        contacts = channels(mapping,pop)
        if qualification:
            contacts = contacts[:2]
        target, valid = totals(p["all_delayed"],group_columns(p["all_guide"],contacts,pop))
        require(valid.all(), "Missing registered training endpoint")
        model = {"contacts":contacts, "train_mean":(w@target).tolist()}
        diag[pop] = {}
        for arm,(z,mean,scale) in standardized.items():
            coeff,details = [], []
            for y in target.T:
                beta, diagnostics = fit_head(z,y,w)
                coeff.append(beta.tolist())
                details.append(diagnostics)
            model[arm] = {"mean":mean.tolist(),"scale":scale.tolist(),"coefficients":coeff}
            diag[pop][arm] = details
        fit["populations"][pop] = model
    return fit, diag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_npz",type=Path)
    parser.add_argument("fits",type=Path)
    parser.add_argument("diagnostics",type=Path)
    parser.add_argument("--qualification",action="store_true",help="Fit the first two contacts of each endpoint only")
    args = parser.parse_args()
    require(not args.fits.exists() and not args.diagnostics.exists(), "Use fresh output paths")
    p = load(args.training_npz)
    model, diagnostics = fit_pack(p,contact_map(),args.qualification)
    model["input_npz_sha256"] = digest(args.training_npz)
    write_json(args.fits,model)
    write_json(args.diagnostics,diagnostics)


if __name__ == "__main__":
    main()
