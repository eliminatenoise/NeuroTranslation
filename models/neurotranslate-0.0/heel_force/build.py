"""Embed both original encoders, readouts and aggregate results in an offline page."""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent


def read(file):
    return json.loads(file.read_bytes())


def main():
    model = read(HERE / "model.json")
    path = PARENT / "movement-weights.npz"
    if hashlib.sha256(path.read_bytes()).hexdigest() != model["parent_sha256"]:
        raise ValueError("Mismatched movement encoder")
    random = read(PARENT / "back_rotation/random-encoder.json")
    with np.load(path, allow_pickle=False) as archive:
        trained = {k: archive[k].ravel().tolist() for k in random}
    data = dict(model=model, example=read(HERE / "example.json"), trained=trained,
                random={k: np.ravel(v).tolist() for k, v in random.items()},
                reports=[read(HERE / (s + "-summary.json")) for s in ("fit", "historic-assessment", "later-repeats")])
    template = (HERE / "reader.html.in").read_text()
    html = template.replace("@@DATA@@", json.dumps(data, separators=(",", ":"), allow_nan=False))
    html = html.replace("@@ENCODER@@", (PARENT / "back_rotation/encoder.js").read_text())
    (HERE / "index.html").write_text(html)


if __name__ == "__main__":
    main()
