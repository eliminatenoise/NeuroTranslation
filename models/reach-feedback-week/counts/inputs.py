"""Verify recording identity, native axis labels, column placement and bin alignment."""
import hashlib

import numpy as np

from forecast import LABELS, TEST_MEMBER, TRAIN_KEYS, TRAIN_MEMBER
from roster import KEY, keyed_rows, native_cue, require

META_HASH = {
    "held-roster.json":"2e7578114bda89b18f5e2e0bbf6079dd52e4fb477c63405461b2cdf1ff2dccc6",
    "held-windows.json":"308cfb92f66c627cda88babe818c5b4431c8dcfda9629d58f0123693b95e4f6b",
    "held-schema.json":"0050b332d90a3d42f4fa00c7a83d296e8b60b54e861b1dce07760a0ab8e6a8ba",
}


def validate(pack, native_guide, member):
    n, u = len(pack["k"]), len(native_guide)
    require(pack["source_member_sha256"].item() == member, "Unexpected recording")
    require(pack["pose_labels"].tolist() == LABELS, "Unexpected coordinate labels")
    require(np.array_equal(pack["all_guide"], native_guide), "Unexpected guide")
    require(np.array_equal(pack["all_columns"], np.arange(1, u+1)), "All columns must be in native order")
    for key in KEY:
        require(pack[key].dtype.kind in "iu" and pack[key].shape == (n,), f"Invalid key {key}")
    for name, length, start in (("history_rows",20,-20), ("movement_rows",10,0), ("delayed_rows",10,10)):
        require(np.array_equal(pack[name], pack["k"][:,None] + np.arange(start,start+length)), f"Wrong {name}")
    for name, shape in (("all_history",(20,u)), ("all_concurrent",(10,u)), ("all_delayed",(10,u)),
                        ("pose",(20,8)), ("movement",(10,8)), ("cue_at_k",(2,))):
        require(pack[name].shape == (n,*shape) and pack[name].dtype.kind in "iuf", f"Invalid {name}")
    pos = np.flatnonzero(np.asarray(native_guide)[:,1] > 0)
    require(np.array_equal(pack["sorted_columns"],pos+1) and np.array_equal(pack["unit_guide"],np.asarray(native_guide)[pos]),
            "Positive columns do not match native guide")
    for k, positive in (("all_history","spikes"),("all_concurrent","concurrent"),("all_delayed","delayed")):
        require(np.array_equal(pack[k][:,:,pos],pack[positive],equal_nan=True), f"{positive} mismatch")


def verify_cue(actual, expected):
    finite = np.isfinite(actual)
    require(np.allclose(actual[finite], expected[finite], rtol=0, atol=1e-12), "Incorrect finite go covariate")


def validate_train(pack, mapping):
    validate(pack,mapping["blocks"][0]["guide"],TRAIN_MEMBER)
    keys = np.stack([pack[k] for k in KEY], axis=1).astype("<i8")
    require(hashlib.sha256(keys.tobytes()).hexdigest() == TRAIN_KEYS, "Not the 519 prespecified train keys")
    require(len(keys) == 519 and len(np.unique(keys[:,[0,2]],axis=0)) == 198, "Unexpected training population")
    verify_cue(pack["cue_at_k"],np.column_stack((pack["ordinal"], np.full(len(keys), .05))))


def validate_test(pack, schema, windows, roster):
    validate(pack,schema["guide"],TEST_MEMBER)
    keys = [tuple(w[k] for k in KEY) for w in windows if w["block"] == schema["block"]]
    require(keyed_rows(pack) == keys, "All frozen candidate keys are required in original order")
    owned = {(r["block"],r["original"]):r for r in roster}
    expected = np.array([native_cue(np.array([k]), owned[b,oid]["go"])[0,:2] for b,_,oid,_,k in keys])
    verify_cue(pack["cue_at_k"], expected)


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {k:data[k] for k in data.files}
