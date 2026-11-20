"""Build the offline page from pinned exported weights and aggregate study results."""
import argparse
import hashlib
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
INPUTS = {
    "weights.json": "b4062509f2cdf4cbe7e5ce968ebac54d9dcc47e9edf1978fdf9f3b51364c9884",
    "results.json": "98ecfe47355b3533c2e8f7aebd9542a4f78f9eb229b0125d7dd2359d59910f5d",
}

def credits():
    paragraphs = (HERE / "NOTICE.md").read_text().split("\n\n")[1:]
    def link(match):
        label, path = match.groups()
        if path == "CDLA-Permissive-2.0.txt":
            path = "#cdla-terms"
        if path == "LICENSE":
            path = "#code-terms"
        return f'<a href="{path}">{label}</a>'
    rendered = []
    for paragraph in paragraphs:
        escaped = html.escape(paragraph.strip()).replace("*HoloAssist*", "<i>HoloAssist</i>").replace("*Single Day W-Track Learning*", "<i>Single Day W-Track Learning</i>")
        rendered.append("<p>" + re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, escaped) + "</p>")
    for slug, heading, name in (("cdla-terms", "Community Data License Agreement", "CDLA-Permissive-2.0.txt"), ("code-terms", "CC0 code dedication", "LICENSE")):
        rendered.append(f'<details id="{slug}"><summary>{heading}</summary><pre>{html.escape((HERE / name).read_text())}</pre></details>')
    return "\n".join(rendered)

def build():
    packed = {}
    for name, expected in INPUTS.items():
        data = (SRC / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Recheck the model and assessment before changing {name}.")
        packed[name] = json.dumps(json.loads(data), separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    scripts = "\n".join((SRC / name).read_text() for name in ("knee-moment.js", "example.js", "view.js"))
    return ((SRC / "page.html").read_text().replace("__STYLE__", (SRC / "style.css").read_text())
            .replace("__WEIGHTS__", packed["weights.json"]).replace("__SCORES__", packed["results.json"])
            .replace("__NOTICE__", credits()).replace("__SCRIPTS__", scripts))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "index.html")
    args = parser.parse_args()
    args.output.write_text(build(), encoding="utf-8")
