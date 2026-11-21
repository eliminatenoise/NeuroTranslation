"""Run the shipped invented example and test role remapping, missing histories and control isolation."""
from copy import deepcopy
import json

import numpy as np

from .forecast import DEFAULT_FIT, TEMPORAL, predict
from .weights import validate


def verify():
    here = DEFAULT_FIT.parent
    load = lambda name: json.loads((here/name).read_bytes())
    example = load("example.json")
    state = validate(load("synthetic-fit.json"))
    run = lambda case: predict(case, state)
    actual, expected = run(example), load("expected.json")
    methods = actual["methods"]
    for label in methods:
        np.testing.assert_allclose(methods[label]["endpoint_native_px"],
                                   expected["methods"][label]["endpoint_native_px"], atol=1e-9, rtol=0)
        for k, row in enumerate(methods[label]["endpoint_shoulder_widths"]):
            native = (np.array(row) @ np.array(actual["reference"]["basis"]) * actual["reference"]["width_px"]
                      + actual["reference"]["origin_px"])
            np.testing.assert_allclose(native, methods[label]["endpoint_native_px"][k], atol=1e-9, rtol=0)

    reflected = deepcopy(example)
    reflected.update(implant_side="L", annotated_wrist="r_wrist")
    for entry in (reflected, reflected["earlier_donor"]):
        entry["prior_by_name"] = {("L" if n[0]=="R" else "R")+n[1:]: [[700-x,y] for x,y in points]
                                  for n,points in entry["prior_by_name"].items()}
    transformed = run(reflected)
    assert transformed["role_wrist"]["contralateral"] == "R_Wrist"
    for name, method in transformed["methods"].items():
        native = np.asarray(methods[name]["endpoint_native_px"]).copy()
        native[...,0] = 700 - native[...,0]
        np.testing.assert_allclose(method["endpoint_native_px"], native, atol=1e-9, rtol=0)

    changed = deepcopy(example)
    changed["prior_by_name"]["R_Wrist"][4][0] += 40
    perturbed = run(changed)["methods"]
    contra = lambda data: np.asarray(data["endpoint_native_px"])[:,0]
    for name in ("blocked","matched_blocked","ridge","intact_swapped","trained_swap"):
        np.testing.assert_allclose(contra(perturbed[name]),contra(methods[name]),atol=1e-10,rtol=0)
    assert np.max(abs(contra(perturbed["intact"])-contra(methods["intact"]))) > 1e-6
    del changed["prior_by_name"]["R_Elbow"]
    gaps = run(changed)
    assert gaps["methods"]["ridge"]["reason"] == ["available","missing_role_landmark"]
    assert gaps["methods"]["intact"]["reason"] == ["incomplete_bilateral_prior"]*2
    assert all(row[1] is None for row in gaps["methods"]["ridge"]["endpoint_native_px"])
    changed["prior_by_name"]["R_Shoulder"][5][1] = None
    assert run(changed)["reference"] is None
    changed = deepcopy(example)
    changed["frame_indices"][2] += 1
    assert run(changed)["methods"]["intact"]["reason"] == ["nonconsecutive_prior_frames"]*2
    changed = deepcopy(example)
    del changed["earlier_donor"]
    assert run(changed)["methods"]["intact_swapped"]["reason"] == ["missing_earlier_donor"]*2
    changed = deepcopy(example)
    changed["earlier_donor"]["prior_by_name"]["L_Shoulder"][3][0] = None
    assert run(changed)["methods"]["trained_swap"]["reason"] == ["donor_missing_prior_shoulder"]*2

    def rejects(case):
        try:
            run(case)
        except ValueError:
            return
        raise AssertionError("Invalid input was accepted")
    for field, value in (("implant_side","L"), ("future_by_name",{}), ("frame_indices",[True]*15)):
        rejects(dict(example, **{field:value}))
    altered = deepcopy(example)
    altered["prior_by_name"]["L_Wrist"][1][0] = "5"
    rejects(altered)
    altered = deepcopy(example)
    altered["earlier_donor"]["frame_indices"] = example["frame_indices"]
    rejects(altered)
    assert len(TEMPORAL) == 12
    return {"methods":len(methods),"example_native_pixel_tolerance":1e-9,
            "checks":"Native and normalized endpoints, reflection, other-arm isolation, missing roles and donor, clock and schema"}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
