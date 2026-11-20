"""Use the frozen geometry checks with a selective-header fallback for one archive member.

Run alongside acquire.py. A07 trial 1 includes opaque MATLAB graphics that some
SciPy versions cannot inventory. The four selected geometry variables are readable.
"""
from pathlib import Path

import acquire
from scipy.io import loadmat, whosmat

ORIGINAL = "859408d298064351767ca181e9483378b74c082350478b95875401f359776f00"
NAMES = ("A", "B", "fascicle_length1", "PA1")
frozen_qualify = acquire.qualify


def read_inventory(path):
    try:
        return whosmat(path)
    except TypeError:
        if acquire.sha(path) != ORIGINAL:
            raise
    # Read only the four geometry variables in this exact source member. The
    # ordinary extraction below will verify all fields, labels and numeric values.
    arrays = loadmat(path, variable_names=list(NAMES), squeeze_me=False)
    return [(name, arrays[name].shape, "struct" if arrays[name].dtype.names else "double")
            for name in NAMES]


def qualify_with_header_receipt(path):
    out, detail = frozen_qualify(path)
    if path.parent.name == "A07" and path.name == "trial-1.mat":
        detail["header_compatibility"] = {
            "adapter_sha256": acquire.sha(Path(__file__)),
            "scope": "A07 trial 1 only. Four unrelated opaque MATLAB graphics objects have no dimensions for a full SciPy variable listing.",
            "permitted_selective_fields": list(NAMES),
            "scientific_checks": "Frozen source tracker and numerical checks in acquire.py."
        }
    return out, detail


if __name__ == "__main__":
    acquire.whosmat = read_inventory
    acquire.qualify = qualify_with_header_receipt
    raise SystemExit(acquire.main())
