"""Build the self-contained rhythm viewer from the pinned public study."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "src"
PINS = {
    "fit.json": "57e989090a461f3f4903c8ebc9d05bc6cf22bd60c6e731b007ade0f4d8110ac9",
    "protocol.json": "67b33f3a79fb013cb71f7a59e1dca0fd34a4b2bbafbfe1437b719df4c584b34c",
    "results.json": "e17f74ee9dc2c09b0843111ecb8c5783920f6a5dfc4245ab5c1f978031ab0c21",
    "source-clarification.json": "dfcbfca1e194c0afdefacd37a0fff9234fdd16ffe73caa08f2b1b36e44166be0",
}
FIELDS = ["person", "emg_cycles_min", "angle_cycles_min", "emg_rows", "angle_rows",
          "emg_sha256", "angles_sha256", "wrong_person_source", "estimate_cycles_min"]


def build(model):
    inputs = {}
    for name, pin in PINS.items():
        raw = (model / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError(f"Study version mismatch in {name}")
        inputs[name] = json.loads(raw)
    score = inputs["results.json"]
    study = {"people": [{k: row[k] for k in FIELDS} for row in score["people"]], "scores": score["scores"]}
    payload = json.dumps(study, ensure_ascii=True, allow_nan=False, separators=(",", ":")).replace("<", r"\u003c")
    tokens = {
        "/*__CSS__*/": (SOURCE / "style.css").read_text(encoding="utf-8"),
        "/*__WORKER__*/": (SOURCE / "spectrum.js").read_text(encoding="utf-8"),
        "/*__APP__*/": (SOURCE / "app.js").read_text(encoding="utf-8"),
        "__STUDY__": payload,
    }
    page = (SOURCE / "page.html").read_text(encoding="utf-8")
    for marker, text in tokens.items():
        if page.count(marker) != 1:
            raise ValueError(f"Expected one placeholder for {marker}")
        page = page.replace(marker, text)
    return page.encode("utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=HERE.parent.parent / "models" / "gait-rhythm")
    parser.add_argument("--out", type=Path, default=HERE / "index.html")
    args = parser.parse_args()
    args.out.write_bytes(build(args.model))
