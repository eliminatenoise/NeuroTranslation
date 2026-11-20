"""Local zero-shot comparison on independent univariate axes; no decoding remote code."""
from pathlib import Path
import hashlib
import numpy as np
import torch
from chronos import ChronosBoltPipeline

HERE = Path(__file__).resolve().parent
CONFIG = "278f0086733031635fb1c861cb01c1bad6477420c7fcb19381a2993e335785e0"
WEIGHTS = "75068728d376d2bec670379eeef4bfb4d24c0cfe24d957451f8d19b447030a32"
HORIZONS = (1, 3, 6, 12)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_bolt():
    local = HERE / ".bolt"
    if digest(local / "model.safetensors") != WEIGHTS or digest(local / "config.json") != CONFIG:
        raise ValueError("Local Chronos checkpoint differs")
    model = ChronosBoltPipeline.from_pretrained(str(local), local_files_only=True, dtype=torch.float32)
    if list(model.quantiles) != [i / 10 for i in range(1, 10)]:
        raise ValueError("Unexpected quantile grid")
    model.inner_model.eval()
    return model


def quantiles(model, x):
    if x.ndim != 3 or x.shape[1:] != (16, 3) or not np.isfinite(x).all():
        raise ValueError("Expected finite [batch,16,XYZ] histories")
    # Fold XYZ into the batch. Bolt is univariate. It never mixes axes or people.
    data = torch.from_numpy(np.ascontiguousarray(x.transpose(0, 2, 1), dtype=np.float32))
    with torch.inference_mode():
        raw = model.predict(data.reshape(-1, 16), prediction_length=12, limit_prediction_length=True)
    raw = raw.reshape(len(x), 3, 9, 12).permute(0, 3, 1, 2).numpy()
    return raw[:, np.array(HORIZONS) - 1].astype(np.float64)
