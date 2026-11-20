"""Build the offline HTML from pinned scientific inputs and readable viewer sources."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"


def build(model, out):
    hashes = json.loads((SRC / "inputs.sha256.json").read_bytes())

    def verified(filename):
        raw = (model / filename).read_bytes()
        if hashlib.sha256(raw).hexdigest() != hashes[filename]:
            raise ValueError("Model file changed: " + filename)
        return raw.decode("utf-8")

    for name in hashes:
        verified(name)
    reader = lambda name: json.loads(verified(name))
    refs = {action: reader("reference-" + action + ".json") for action in ["walk", "run"]}
    payload = {"schema": reader("schema.json"), "weights": reader("weights.json"),
               "refs": refs, "study": json.loads((SRC / "study.json").read_bytes())}
    data = json.dumps(payload, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    runtime = verified("inference.mjs").replace("export function ", "function ")
    slots = {"STYLE": "view.css", "CAMERA": "scene.js", "VIEWER": "view.js"}
    replacements = {key: (SRC/file).read_text() for key,file in slots.items()}
    replacements.update(DATA=data, INFERENCE=runtime)
    page = (SRC / "page.html").read_text()
    for key,value in replacements.items():
        if key in ("CAMERA", "INFERENCE", "VIEWER") and "</script" in value.lower():
            raise ValueError("Unsafe inline script end")
        tag = "/* " + key + " */"
        if page.count(tag) != 1:
            raise ValueError("Template marker changed: " + key)
        page = page.replace(tag, value)
    out.write_text(page,encoding="utf-8")
    print(hashlib.sha256(page.encode()).hexdigest(), out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, default=HERE/"index.html")
    args=p.parse_args()
    build(args.model, args.out)
