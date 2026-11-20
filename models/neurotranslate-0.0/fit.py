"""Fit fixed person-fold wrist adapters without changing any source-domain weights."""
import argparse
import hashlib
import json
import os
import platform
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from network import SharedMotion
from predict import MODES, angular_tokens

HERE = Path(__file__).resolve().parent
BASE_HASH = "9a3649cb8f2119984e7f9f0b96a07bdc95e1833c7068f0e9caef2680f22e3179"
TABLE_MANIFEST_HASH = "beaf658491c6d402a63876cdf883b563ce65cad028383ce6bcdba485a844c7f9"
PROTOCOL_HASH = "049f4ccb5d6fbdb447262e66501e108e96f5a59df949ecd95f12c8c5a8acc910"
SEED = 20261120
BATCH = 128
EPOCHS = 4


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read_table(data_path, manifest_path):
    if digest(manifest_path) != TABLE_MANIFEST_HASH:
        raise ValueError("Source table manifest differs")
    manifest = json.loads(manifest_path.read_text())
    with np.load(data_path, allow_pickle=False) as f:
        if set(f.files) != set(manifest):
            raise ValueError("Unexpected source array set")
        table = dict(f)
    for name, a in table.items():
        item = manifest[name]
        if (list(a.shape) != item["shape"] or a.dtype.str != item["dtype"]
                or hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() != item["sha256"]):
            raise ValueError(f"Study array changed: {name}")
    return table


def save_json(path, result):
    with path.open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")


def configure(threads):
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    return {"numpy": np.__version__, "torch": str(torch.__version__), "cuda": torch.cuda.is_available(),
            "hip": torch.version.hip, "intra": torch.get_num_threads(), "interop": torch.get_num_interop_threads(),
            "blas": os.environ.get("OPENBLAS_NUM_THREADS"), "python": platform.python_version(),
            "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None}


def cores(spatial):
    if digest(spatial) != BASE_HASH:
        raise ValueError("Wrong spatial checkpoint")
    train_core = SharedMotion.load(spatial)
    torch.manual_seed(104927)
    random_core = SharedMotion()
    for net in (train_core, random_core):
        net.requires_grad_(False).eval()
    return {"pretrained": train_core, "random": random_core}


def normalization(table, rows):
    result = {}
    residual = table["target"][rows] - table["anchor"][rows]
    for key, a, axis in (("bins", table["bins"][rows], (0, 1)),
                         ("anchor", table["anchor"][rows], 0), ("residual", residual, 0)):
        result[key + "_center"] = a.mean(axis=axis)
        scale = a.std(axis=axis)
        result[key + "_scale"] = np.where(scale <= 1e-8, 1., scale)
    return result


def tensor_array(a):
    return torch.from_numpy(np.ascontiguousarray(a, dtype=np.float32))


class AngularAdapter(nn.Module):
    def __init__(self, core):
        super().__init__()
        self.core = core
        torch.manual_seed(SEED)
        self.project = nn.Linear(64, 24)
        self.readout = nn.Linear(24, 2)
        nn.init.zeros_(self.readout.weight)
        nn.init.zeros_(self.readout.bias)

    def forward(self, x):
        z = self.project(x) + self.core.position
        for block in self.core.blocks:
            z = block(z)
        return self.readout(self.core.last_norm(z[:, -1]))


def state(layer):
    return {k: v.detach().cpu().numpy().copy() for k, v in layer.state_dict().items()}


def adapter_state(adapter):
    return {k: v for layer in ("project", "readout")
            for k, v in ((layer + "." + name, a) for name, a in state(getattr(adapter, layer)).items())}


def fit_one(core, x, y, limit=None):
    adapter = AngularAdapter(core)
    params = [p for p in adapter.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=.001, weight_decay=.01)
    rng = np.random.default_rng(SEED)
    loss_values = []
    batches = hashlib.sha256()
    started = time.perf_counter()
    for epoch in range(EPOCHS):
        ordered = rng.permutation(len(y))
        for start in range(0, len(ordered), BATCH):
            indices = ordered[start:start+BATCH]
            batches.update(indices.astype("<i8").tobytes())
            take = torch.from_numpy(indices)
            optimizer.zero_grad(set_to_none=True)
            loss = (adapter(x[take]) - y[take]).square().mean()
            loss.backward()
            nn.utils.clip_grad_norm_(params, 1., error_if_nonfinite=True)
            optimizer.step()
            loss_values.append(loss.item())
            if limit and len(loss_values) == limit:
                break
        if limit and len(loss_values) == limit:
            break
    if not np.isfinite(loss_values).all() or any(p.grad is not None for p in core.parameters()):
        raise RuntimeError("Nonfinite loss or gradient on frozen source weights")
    return adapter_state(adapter), {
        "steps": len(loss_values), "batch_order_sha256": batches.hexdigest(), "loss_first": loss_values[0],
        "loss_last": loss_values[-1], "loss_sha256": hashlib.sha256(np.array(loss_values, "<f8").tobytes()).hexdigest(),
        "seconds": time.perf_counter() - started}


def synthetic(core):
    gen = np.random.default_rng(132)
    x = tensor_array(gen.normal(size=(1024, 4, 64)))
    y = tensor_array(gen.normal(size=(1024, 2)))
    return fit_one(core, x, y, limit=32)[1]


def write_state(path, arrays):
    with path.open("xb") as f:
        np.savez_compressed(f, **arrays)


def fit(args):
    started = time.perf_counter()
    route = configure(args.threads)
    models = cores(args.spatial)
    if args.command == "fixture":
        result = synthetic(models["pretrained"])
        print(json.dumps({"route": route, **result, "main_seconds": time.perf_counter() - started}))
        return
    if digest(HERE / "protocol.json") != PROTOCOL_HASH:
        raise ValueError("Frozen protocol changed")
    args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    table = read_table(args.data, args.manifest)
    if not np.array_equal(np.unique(table["person"]), np.arange(6)):
        raise ValueError("Subject split changed")
    report = {"route": route, "protocol_sha256": PROTOCOL_HASH, "spatial_sha256": BASE_HASH,
              "array_manifest_sha256": TABLE_MANIFEST_HASH, "fits": {}, "files": {}}
    for held in [0, 1, 2, 3, 4, 5, None]:
        label = "all-six" if held is None else f"held-{held}"
        rows = np.arange(len(table["slot"])) if held is None else np.flatnonzero(table["person"] != held)
        stats = normalization(table, rows)
        y = tensor_array(((table["target"][rows] - table["anchor"][rows]) - stats["residual_center"])
                         / stats["residual_scale"])
        weights = {"angular.stats." + k: v for k, v in stats.items()}
        receipt = {"fitting_people": np.unique(table["person"][rows]).tolist(), "rows": len(rows), "arms": {}}
        for mode, channels in MODES.items():
            x = tensor_array(angular_tokens(table["bins"][rows, :, :channels], table["anchor"][rows],
                                            table["slot"][rows], mode, stats))
            for condition in (["pretrained"] if held is None else models):
                trained, detail = fit_one(models[condition], x, y)
                weights.update({condition + "." + mode + "." + k: v for k, v in trained.items()})
                receipt["arms"][condition + "." + mode] = detail
        if len({v["batch_order_sha256"] for v in receipt["arms"].values()}) != 1:
            raise ValueError("Fit opportunities differ")
        path = args.out / (label + ".npz")
        write_state(path, weights)
        report["fits"][label] = receipt
        report["files"][path.name] = digest(path)
    # Keep private random control state for NumPy-only reproduction of all held-person scores.
    random_path = args.out / "random-core.npz"
    write_state(random_path, state(models["random"]))
    report["files"][random_path.name] = digest(random_path)
    path = args.out / "movement-weights.npz"
    with np.load(args.spatial, allow_pickle=False) as base:
        deployment = dict(base)
    config = json.loads(str(deployment["configuration"]))
    config["angular"] = {"format": 1, "domain": "wrist_angle", "units": "degrees", "axes": ["extension", "radial_deviation"],
                         "modes": list(MODES), "horizon_ticks": 128, "clock_hz": 512, "base_sha256": BASE_HASH,
                         "protocol_sha256": PROTOCOL_HASH, "array_manifest_sha256": TABLE_MANIFEST_HASH}
    deployment["configuration"] = np.array(json.dumps(config))
    for k, a in weights.items():
        key = "angular." + k.removeprefix("pretrained.") if k.startswith("pretrained.") else k
        deployment[key] = a
    write_state(path, deployment)
    report["files"][path.name] = digest(path)
    report["wall_seconds"] = time.perf_counter() - started
    save_json(args.out / "seal.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("fixture", "fit"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--spatial", type=Path, required=True)
        cmd.add_argument("--threads", type=int, choices=(1, 2), required=True)
        if name == "fit":
            cmd.add_argument("--data", type=Path, required=True)
            cmd.add_argument("--manifest", type=Path, required=True)
            cmd.add_argument("--out", type=Path, required=True)
    fit(parser.parse_args())
