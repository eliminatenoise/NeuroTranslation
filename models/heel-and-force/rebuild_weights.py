"""Rebuild the four selected final weight files from the public extractor's train NPZ."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
import torch
from records import MUSCLES, sha, stats, write
from network import encode_state, train

DEVELOPMENT_SHA256 = "fb2ea815357a523192f08bd8d04c33ac3226c7bc9e746ecd3b034db6ffe78852"
EPOCH = {"joint":12, "heel":12, "force":12, "marker":36}
EXPECTED = {
    "joint":"5c7052d187358abd8c24d081c23d2e72ef90cc0603fc8f981e2fd502c37107cb",
    "heel":"4ac3c7e90b8b49717dda997adfbd19cbd84bca341273f2b9ae854cd16b94bd09",
    "force":"36cbd0efe9272cac00bc17d502187f72f2ac59513dcf3cccacb165f07a1c7365",
    "marker":"21b27370f7231594b4b47bfc60636e43aa17eea76a36b46f69c92e078e7f4358",
}


def rebuild(source, output):
    if sha(source) != DEVELOPMENT_SHA256:
        raise ValueError("Input differs from the sealed development NPZ")
    if output.exists():
        raise FileExistsError("Choose an unused output directory")
    with np.load(source, allow_pickle=False) as f:
        d = {k:f[k] for k in ("marker_mm","emg_uv","offset","person","repeat","heel_delta_mm","force_n")}
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    norm = stats(d)
    hashes = {}
    with tempfile.TemporaryDirectory(dir=output.parent) as folder:
        work = Path(folder) / "rebuild"
        work.mkdir()
        for kind, epoch in EPOCH.items():
            snapshots, _ = train(d, norm, kind, "cpu", epochs=(epoch,))
            model = {"schema":"gait-pair-temporal-v1","kind":kind,"epoch":epoch,"norm":norm,
                     "state":encode_state(snapshots[epoch],kind),"supported_offsets":sorted(set(map(int,d["offset"]))),
                     "marker_order":["R_FCC","R_FM2"],"emg_order":MUSCLES,"axes":["lab_X","lab_Y","lab_Z_up"]}
            destination = work / (kind+"-model.json")
            write(destination,model)
            hashes[kind] = sha(destination)
        work.rename(output)
    return {"weights":hashes,"exact_reference_bytes":hashes == EXPECTED,"torch":str(torch.__version__),
            "numpy":np.__version__,"device":"cpu","intra_threads":1,"inter_threads":1}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("development_npz", type=Path)
    parser.add_argument("unused_output_directory", type=Path)
    arg = parser.parse_args()
    result = rebuild(arg.development_npz, arg.unused_output_directory)
    print(json.dumps(result))
    sys.exit(0 if result["exact_reference_bytes"] else 1)
