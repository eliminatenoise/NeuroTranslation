"""Run the stand-and-sit force forecasts from ten 20 ms bins."""

import json
from pathlib import Path
import sys

import numpy as np
import torch
from safetensors import safe_open
from safetensors.torch import load_file

from fusion import ForceMotionForecast
from network import DEFAULT, TemporalAttention


HERE = Path(__file__).resolve().parent


class Forecaster:
    def __init__(self):
        torch.set_num_threads(1)
        torch.set_float32_matmul_precision("highest")
        self.models = []
        for seed in (2731, 4119):
            path = HERE / f"force-residual-{seed}.safetensors"
            with safe_open(path, framework="pt", device="cpu") as reader:
                metadata = reader.metadata()
            self.center = np.asarray(json.loads(metadata["force_center_n"]))
            self.scale = np.asarray(json.loads(metadata["force_scale_n"]))
            self.residual_ns = float(metadata["residual_scale_ns"])
            model = ForceMotionForecast(TemporalAttention, DEFAULT, 6)
            model.load_state_dict(load_file(path, device="cpu"), strict=True)
            model.eval()
            self.models.append(model)

    def predict(self, histories):
        force = np.asarray(histories, dtype=np.float64)
        if force.ndim != 3 or force.shape[1:] != (10, 2) or not np.isfinite(force).all():
            raise ValueError("Supply ten finite force pairs per history.")
        current = force[:, -1] * 0.1
        time = np.arange(-90, 0, 20) / 1000.
        centred = time - time.mean()
        slope = np.sum(force[:, -5:] * centred[None, :, None], axis=1) / (centred @ centred)
        ahead = (np.arange(100) + 0.5) / 1000.
        mean_growth = (-0.05 * np.expm1(-(ahead - time[-1]) / 0.05)).mean()
        trend = current + slope * mean_growth * 0.1
        change = force[:, -2:].mean(axis=1).sum(axis=1) - force[:, :2].mean(axis=1).sum(axis=1)
        rising = change > 50.
        corrected = trend.copy()
        if rising.any():
            samples = torch.tensor((force[rising] - self.center) / self.scale, dtype=torch.float32)
            missing = torch.zeros((len(samples), 10, 24), dtype=torch.float32)
            with torch.inference_mode():
                average = np.mean([model(samples, missing).numpy().astype(np.float64) for model in self.models], axis=0)
            corrected[rising] += self.residual_ns * average
        if not all(np.isfinite(values).all() for values in (current, trend, corrected, change)):
            raise ValueError("These force readings are outside the numeric range.")
        return {"persistence": current, "dampedTrend": trend, "attention": corrected, "rising": rising, "loadChangeN": change}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Pass a JSON file containing ten [plate 2, plate 3] pairs in newtons.")
    history = np.asarray(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), dtype=np.float64)
    result = Forecaster().predict(history[None])
    print(json.dumps({key: value[0].tolist() for key, value in result.items()}, indent=2))


if __name__ == "__main__":
    main()
