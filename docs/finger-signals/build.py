# SPDX-License-Identifier: CC0-1.0
"""Rebuild the offline browser from the published study files. Requires NumPy."""
import argparse
import hashlib
import html
import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
MODELS = ("persistence", "motion_cue", "aligned")
LABELS = ("Hold last", "Glove + cue", "Glove + cue + brain")
PRIVACY = ("User agrees that, where applicable, content will not be used to identify or to "
           "otherwise infringe the privacy or confidentiality rights of individuals. Content "
           "distributed via the Stanford Digital Repository may be subject to additional license "
           "and use restrictions applied by the depositor.")


def build(folder):
    hashes = json.loads((SRC / "inputs.sha256.json").read_text())
    for member, expected in hashes.items():
        if hashlib.sha256((folder / member).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Study file differs from the published version: {member}")
    for member in ("RIGHTS.md", "licenses/CC0-1.0.txt", "licenses/CC-BY-SA-4.0.txt"):
        if (HERE / member).read_bytes() != (folder / member).read_bytes():
            raise ValueError(f"Local rights file differs from the study: {member}")

    spec = importlib.util.spec_from_file_location("finger_study", folder / "model.py")
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    example = json.loads((folder / "invented-case.json").read_text())
    glove = example["four_glove_readings_counts"]
    tokens = model.tokens_from_history(example["ecog_counts"], glove, example["digit_code"],
                                       example["phase"], example["elapsed_phase_ms"])
    # Round only invented band powers for reproducible export across FFT implementations.
    powers = np.expm1(tokens[:, model.BRAIN]).round(13).tolist()
    payload = {"glove": glove, "age": example["elapsed_phase_ms"], "powers": powers}
    for key in MODELS[1:]:
        with np.load(folder / "weights" / f"{key}.npz", allow_pickle=False) as weights:
            payload[key] = {name: weights[name].tolist() for name in ("mean","sd","weights","intercept")}
    result = json.loads((folder / "study-results.json").read_text())
    contrasts = {x["baseline"]: x for x in result["contrasts"] if x["candidate"] == "aligned"}
    scores, raw = [], []
    for key, name in zip(MODELS, LABELS):
        val = result["scores"][key]["macro_normalized_mae"]
        scores.append(f'<div class="score-row"><span>{name}</span><div class="score-track" aria-hidden="true">'
                      f'<div class="score-bar" style="width:{val / .30 * 100:.4f}%"></div></div><strong>{val:.4f}</strong></div>')
    for i, name in enumerate(result["digits"]):
        cells = "".join(f'<td>{result["scores"][key]["per_digit_mae_glove_units"][i]:.2f}</td>' for key in MODELS)
        raw.append(f'<tr><th scope="row">{name.title()}</th>{cells}</tr>')
    def number(v):
        return f"{v:.5f}".replace("-", "−")
    def interval(key):
        return " to ".join(number(v) for v in contrasts[key]["macro_interval"])

    ethics = (folder / "RIGHTS.md").read_text().split("\nEthics statement: ", 1)[1].strip()
    replacements = {
        "STYLE": (SRC / "style.css").read_text(),
        "PAYLOAD": json.dumps(payload, separators=(",",":"), allow_nan=False).replace("<", r"\u003c"),
        "SCRIPT":"\n".join((SRC / script).read_text() for script in ("model.js","graphics.js","view.js")),
        "FIT":str(result["train"]["scored_trials"]), "LATER":str(result["development_evaluation"]["scored_trials"]),
        "SCORES":"\n".join(scores), "ERRORS":"\n".join(raw),
        "GAIN":number(contrasts["motion_cue"]["macro_normalized_gain"]),
        "INTERVAL":interval("motion_cue"),
        "DONOR":number(contrasts["earlier_substitute"]["macro_normalized_gain"]),
        "DONOR_INTERVAL":interval("earlier_substitute"),
        "RIGHTS":html.escape("Ethics statement: " + ethics + "\n\nStanford catalogue terms\n" + PRIVACY),
        "LEGAL":html.escape("\n\n".join((folder / "licenses" / n).read_text() for n in ("CC-BY-SA-4.0.txt","CC0-1.0.txt"))),
    }
    page = (SRC / "page.html").read_text()
    for key, value in replacements.items():
        marker = f"__{key}__"
        if page.count(marker) != 1:
            raise ValueError(f"Expected one placeholder for {key}")
        page = page.replace(marker, value)
    return page


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=HERE.parent.parent / "models/cortical-glove")
    parser.add_argument("--out", type=Path, default=HERE / "index.html")
    args = parser.parse_args()
    args.out.write_text(build(args.model), encoding="utf-8")
