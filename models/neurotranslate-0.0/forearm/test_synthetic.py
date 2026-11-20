"""Invented cohorts only. Check estimator, control routing and two exclusions."""
from pathlib import Path
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import study
from forearm.residual import apply, estimate, features


def cohort():
    rng = np.random.default_rng(3227)
    n = 6 * 36
    person = np.repeat(np.arange(6), 36)
    anchor = rng.normal(size=(n, 2))
    bins = rng.normal(size=(n, 16, 14))
    bins[:, :, 2:6] = abs(bins[:, :, 2:6])
    return {"person": person, "slot": np.tile(np.arange(6), 36), "block": np.zeros(n, int),
            "trial": np.tile(np.repeat(np.arange(6), 6), 6), "donor": np.concatenate(
                [np.r_[np.arange(p*36+6,p*36+36),np.arange(p*36,p*36+6)] for p in range(6)]),
            "bins": bins, "anchor": anchor, "target": anchor + rng.normal(size=(n, 2))}


def main():
    t = cohort()
    study.donor_check(t)
    for arm, c in study.ARMS.items():
        preds = t["target"] + .3
        inp = [t["bins"][:, :, :c], t["anchor"], preds, t["slot"]]
        fit = estimate(*inp, preds, t["person"], arm)
        np.testing.assert_array_equal(apply(*inp, arm, fit), preds)
        offsets = np.arange(6)[t["slot"],None] + np.array([[1.2, -2.1]])
        fitted = estimate(*inp, preds + offsets, t["person"], arm)
        np.testing.assert_allclose(apply(*inp, arm, fitted), preds + offsets, atol=1e-11)
        f = features(*inp[:3], arm)
        np.testing.assert_array_equal(f[:, 34:36], preds - t["anchor"])
    # Contaminate both held people with extreme but finite values. Fitting a four-person state must be invariant.
    study.original.configure(2)
    spatial = HERE.parent / "spatial-seed.npz"
    core = study.original.cores(spatial)["pretrained"]
    cfg, w = study.read_checkpoint(spatial)
    mutated = {k: v.copy() for k, v in t.items()}
    affected = np.isin(t["person"], [3, 5])
    for k in ("bins", "anchor", "target"):
        mutated[k][affected] += 1000
    group = study.subset_without(3, 5)
    before, rb = study.inner_state(t, group, core)
    after, ra = study.inner_state(mutated, group, core)
    for key in before:
        np.testing.assert_array_equal(before[key], after[key])
    assert ra["fitting_rows"] == rb["fitting_rows"] == 144
    # Nested-row builder must index each inner state by the four legal people and predict only a fifth.
    outer = study.subset_without(5)
    inner = {tuple(j for j in outer if j!=i): before for i in outer}
    rows, out, parents = study.nested_rows(t, outer, inner, cfg, w)
    assert 5 not in np.unique(t["person"][rows]) and np.isfinite(out).all()
    for i, parent in parents.items():
        assert set(parent["training_people"]) == set(range(6)) - {int(i),5}
    # Deliberately corrupt donor identity; it must be rejected.
    t["donor"][0] = 0
    try:
        study.donor_check(t)
    except AssertionError:
        pass
    else:
        raise AssertionError("self donor accepted")
    print(json.dumps({"all_inputs": "invented", "zero_residual_exact": True,
                      "unpenalized_slot_offsets_exact_within": 1e-11, "forecast_change_columns": [34,35],
                      "excluded_input_and_target_mutation": "all four-person scales and weights bit-identical",
                      "self_donor_rejected": True, "nested_parents": parents}, indent=2))


if __name__ == "__main__":
    main()
