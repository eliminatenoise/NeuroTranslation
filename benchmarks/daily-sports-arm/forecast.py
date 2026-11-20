"""Offline right-arm accelerometer forecasts for the UCI Daily and Sports Activities study."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "protocol.json"
PLAN = json.loads(PROTOCOL.read_text())
ARCHIVE_SHA256 = "f42ad7744ecf14151c9fa3a86dfb5b24de9d7cb7ffe956ef5de242983459c77e"
SEED = 20261120


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_windows(archive, partition):
    if digest(archive) != ARCHIVE_SHA256:
        raise ValueError("Dataset release differs from the study archive")
    if partition not in {"train", "assessment"}:
        raise ValueError("Unknown data partition")
    histories, targets, identities = [], [], []
    with ZipFile(archive) as source:
        for activity in PLAN["activities"]:
            for person in PLAN[partition]:
                for segment in range(1, PLAN["segments_per_person_activity"] + 1):
                    name = f"data/{activity}/{person}/s{segment:02}.txt"
                    with source.open(name) as file:
                        raw = np.loadtxt(file, delimiter=",", dtype=np.float64)
                    if list(raw.shape) != PLAN["expected_segment_shape"]:
                        raise ValueError(f"Unexpected shape in {name}: {raw.shape}")
                    xyz = raw[:, PLAN["zero_based_axes"]]
                    if not np.isfinite(xyz).all():
                        raise ValueError(f"Missing or nonfinite accelerometer values in {name}")
                    for cutoff in PLAN["zero_based_cutoffs"]:
                        start = cutoff + 1 - PLAN["history_samples"]
                        histories.append(xyz[start:cutoff + 1])
                        targets.append(xyz[cutoff + PLAN["lead_samples"]])
                        identities.append((activity, person, segment, cutoff))
    return np.stack(histories), np.stack(targets), identities


class ArmForecast(nn.Module):
    def __init__(self):
        super().__init__()
        self.input = nn.Linear(3, 32)
        self.positions = nn.Parameter(torch.empty(16, 32))
        nn.init.normal_(self.positions, std=0.02)
        self.blocks = nn.Sequential(*[
            nn.TransformerEncoderLayer(32, 4, 64, dropout=0.0, activation="gelu",
                                       batch_first=True, norm_first=True)
            for _ in range(2)
        ])
        self.norm = nn.LayerNorm(32)
        self.correction = nn.Linear(32, 3)
        nn.init.zeros_(self.correction.weight)
        nn.init.zeros_(self.correction.bias)

    def forward(self, history):
        if history.ndim != 3 or history.shape[1:] != (16, 3):
            raise ValueError("Expected [batch, 16 consecutive samples, 3 right-arm axes]")
        encoded = self.blocks(self.input(history) + self.positions)
        return history[:, -1] + self.correction(self.norm(encoded[:, -1]))


def fit_ridge(history, target):
    flat = history.reshape(len(history), -1)
    residual = target - history[:, -1]
    average = flat.mean(0)
    design = flat - average
    penalty = len(flat) * 0.001 * np.eye(flat.shape[1])
    coef = np.linalg.solve(design.T @ design + penalty, design.T @ (residual - residual.mean(0)))
    return coef, residual.mean(0) - average @ coef


def network_predictions(model, normalized):
    model.eval()
    with torch.inference_mode():
        chunks = torch.from_numpy(normalized.astype(np.float32)).split(64)
        return torch.cat([model(x) for x in chunks]).numpy().astype(np.float64)


def fit(archive, out):
    if (out / "model.pt").exists():
        raise FileExistsError("Use the stored checkpoint or a fresh output directory for another fit")
    start = time.perf_counter()
    x, y, rows = read_windows(archive, "train")
    center = x.mean(axis=(0, 1))
    scale = x.std(axis=(0, 1))
    if not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError("Unusable training scale")
    x = (x - center) / scale
    y = (y - center) / scale
    coef, intercept = fit_ridge(x, y)
    torch.manual_seed(SEED)
    model = ArmForecast()
    data = torch.from_numpy(x.astype(np.float32))
    target = torch.from_numpy(y.astype(np.float32))
    with torch.no_grad():
        if not torch.equal(model(data[:16]), data[:16, -1]):
            raise ValueError("Initial residual head differs from persistence")
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    shuffle = torch.Generator().manual_seed(SEED)
    losses = []
    for _ in range(12):
        squared_error = 0.0
        for indices in torch.randperm(len(data), generator=shuffle).split(64):
            optimizer.zero_grad(set_to_none=True)
            predictions = model(data[indices])
            loss = nn.functional.mse_loss(predictions, target[indices])
            loss.backward()
            optimizer.step()
            squared_error += loss.item() * len(indices)
        losses.append(squared_error / len(data))
    if not np.isfinite(losses).all():
        raise ValueError("Nonfinite training loss")
    state = {"model": model.state_dict(), "center": torch.from_numpy(center),
             "scale": torch.from_numpy(scale), "ridge": torch.from_numpy(coef),
             "intercept": torch.from_numpy(intercept), "protocol": digest(PROTOCOL),
             "source": ARCHIVE_SHA256, "implementation": digest(Path(__file__))}
    temp = out / "model.tmp"
    torch.save(state, temp)
    restored, _ = load(temp)
    before, after = network_predictions(model, x[:128]), network_predictions(restored, x[:128])
    if not np.array_equal(before, after):
        raise ValueError("Saved checkpoint changed training predictions")
    temp.rename(out / "model.pt")
    return {"train_windows": len(rows), "train_members": len(set(r[:3] for r in rows)),
            "participants": PLAN["train"], "parameters": sum(p.numel() for p in model.parameters()),
            "loss_per_epoch": losses, "save_reload_max_abs_difference": float(abs(before - after).max()),
            "checkpoint_sha256": digest(out / "model.pt"), "seconds": time.perf_counter() - start}


def load(path):
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state["protocol"] != digest(PROTOCOL) or state["source"] != ARCHIVE_SHA256:
        raise ValueError("Checkpoint and study release disagree")
    model = ArmForecast()
    model.load_state_dict(state["model"], strict=True)
    return model.eval(), state


def predict_all(model, state, x):
    center, scale = state["center"].numpy(), state["scale"].numpy()
    norm = (x - center) / scale
    residual = norm.reshape(len(x), -1) @ state["ridge"].numpy() + state["intercept"].numpy()
    return {"persistence": x[:, -1], "ridge": x[:, -1] + residual * scale,
            "transformer": network_predictions(model, norm) * scale + center}


def summarize(predictions, y, rows):
    groups = {"all": np.ones(len(y), dtype=bool)}
    for act in PLAN["activities"]:
        groups[act] = np.array([r[0] == act for r in rows])
    for person in PLAN["assessment"]:
        groups[person] = np.array([r[1] == person for r in rows])
        for act in PLAN["activities"]:
            groups[f"{person}/{act}"] = groups[person] & groups[act]
    errors = {model: abs(values - y) for model, values in predictions.items()}
    scores = {}
    for group, mask in groups.items():
        result = {"windows": int(mask.sum())}
        for model, error in errors.items():
            per_axis = error[mask].mean(axis=0)
            result[model] = {"mae": float(per_axis.mean()), "mae_xyz": per_axis.tolist()}
        result["transformer_minus_baseline_mae"] = {
            k: float((errors["transformer"][mask] - errors[k][mask]).mean())
            for k in ("persistence", "ridge")}
        scores[group] = result
    return scores


def assess(archive, out):
    start = time.perf_counter()
    model, state = load(out / "model.pt")
    if state["implementation"] != digest(Path(__file__)):
        raise ValueError("Evaluation implementation differs from the frozen fit")
    x, y, rows = read_windows(archive, "assessment")
    original = predict_all(model, state, x)
    shuffled = x.copy()
    rng = np.random.default_rng(34117)
    for i in range(len(x)):
        shuffled[i, :-1] = x[i, rng.permutation(15)]
    control = predict_all(model, state, shuffled)
    ordered = summarize(original, y, rows)
    np.savez_compressed(out / "assessment-arrays.npz", ids=np.array(rows), target=y,
                        **original, **{"shuffled_" + k: v for k, v in control.items()})
    return {"checkpoint_sha256": digest(out / "model.pt"), "participants": PLAN["assessment"],
            "assessment_members": len(set(r[:3] for r in rows)), "ordered": ordered,
            "shuffled": summarize(control, y, rows),
            "passes_primary_rule": all(
                delta < 0 for p in PLAN["assessment"]
                for delta in ordered[p]["transformer_minus_baseline_mae"].values()),
            "seconds": time.perf_counter() - start}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["fit", "assess"])
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--threads", type=int, choices=[1, 2, 4], default=1)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = args.output / (args.stage + ".json")
    if report.exists():
        parser.error(f"{report} already exists")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    procedure = fit if args.stage == "fit" else assess
    result = procedure(args.archive, args.output)
    result.update(torch=str(torch.__version__), numpy=np.__version__, cpu_threads=torch.get_num_threads(),
                  interop_threads=torch.get_num_interop_threads(), protocol_sha256=digest(PROTOCOL),
                  code_sha256=digest(Path(__file__)), archive_sha256=ARCHIVE_SHA256)
    report.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(report)


if __name__ == "__main__":
    main()
