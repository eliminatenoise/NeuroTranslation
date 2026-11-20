"""Rebuild the self-contained movement viewer using the Python standard library."""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=HERE.parents[1] / "models/neurotranslate-browser",
                        help="Directory containing the unified browser scorer, invented examples and licences")
    parser.add_argument("--out", type=Path, default=HERE / "index.html")
    args = parser.parse_args()
    src = HERE / "src"
    hashes = json.loads((src / "sources.json").read_bytes())["buildInputsSha256"]

    def verified(folder, name):
        raw = (folder / name).read_bytes()
        if digest(raw) != hashes[name]:
            raise ValueError("Input differs from this edition: " + name)
        return raw.decode("utf-8")

    runtime = verified(args.runtime, "shared-motion.js")
    if "</script" in runtime.lower():
        raise ValueError("Runtime is unsuitable for inline embedding")
    data = json.loads(verified(src, "inputs.json"))
    spatial = json.loads(verified(args.runtime, "examples.json"))
    rat = spatial["domain"].index("rat")
    data["inventedRat"] = spatial["x"][rat]
    data["pointExample"] = json.loads(verified(args.runtime, "point-example.json"))
    data["plateExample"] = json.loads(verified(args.runtime, "right-plate-example.json"))
    data["momentExample"] = json.loads(verified(args.runtime, "knee-moment-example.json"))
    data["kneeExample"] = json.loads(verified(args.runtime, "knee-example.json"))
    data["angleExample"] = json.loads(verified(args.runtime, "angular-example.json"))["input"]
    data["forearmExample"] = json.loads(verified(args.runtime, "forearm-example.json"))
    data["angleScores"] = json.loads(verified(src, "angular-scores.json"))
    payload = json.dumps(data, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    app = (src / "panel.js").read_text(encoding="utf-8")
    if app.count("__DATA_DIGEST__") != 1:
        raise ValueError("Missing or repeated data digest")
    app = app.replace("__DATA_DIGEST__", digest(payload.encode("utf-8")))
    replacements = {
        "@@PLATE_LICENCE@@": base64.b64encode(verified(args.runtime, "RIGHT-PLATE-DATA-LICENCE.txt").encode("utf-8")).decode("ascii"),
        "@@STYLE@@": (src / "panel.css").read_text(encoding="utf-8"),
        "@@APP@@": app,
        "@@RUNTIME@@": runtime,
        "@@PAYLOAD@@": payload,
        "@@CDLA@@": html.escape(verified(args.runtime, "CDLA-Permissive-2.0.txt"), quote=False),
        "@@CC0@@": html.escape(verified(args.runtime, "CC0-1.0.txt"), quote=False),
    }
    template = (src / "panel.html").read_text(encoding="utf-8")
    for marker, value in replacements.items():
        if template.count(marker) != 1:
            raise ValueError("Missing or repeated template marker " + marker)
        template = template.replace(marker, value)
    # A newline after </html> becomes body content when a browser saves the offline copy.
    content = template.rstrip("\n").encode("utf-8")
    args.out.write_bytes(content)
    print(args.out, len(content), digest(content))


if __name__ == "__main__":
    main()
