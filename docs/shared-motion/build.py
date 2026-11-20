"""Rebuild the self-contained viewer. Python standard library only."""
import argparse
import hashlib
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime",type=Path,default=HERE.parents[1]/"models/shared-motion-browser",
                        help="Folder containing the released browser scorer and accompanying licences")
    parser.add_argument("--out",type=Path,default=HERE/"index.html")
    args = parser.parse_args()
    src = HERE/"src"
    hashes = json.loads((src/"sources.json").read_bytes())["buildInputsSha256"]

    def verified(folder, name):
        raw = (folder/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != hashes[name]:
            raise ValueError("Input differs from this edition: "+name)
        return raw.decode()

    runtime = verified(args.runtime,"shared-motion.js")
    if "</script" in runtime.lower():
        raise ValueError("Runtime is unsuitable for inline embedding")
    data = json.loads(verified(src,"inputs.json"))
    template = (src/"panel.html").read_text(encoding="utf-8")
    replacements = {"@@STYLE@@":(src/"panel.css").read_text(encoding="utf-8"),
                    "@@APP@@":(src/"panel.js").read_text(encoding="utf-8"),"@@RUNTIME@@":runtime,
                    "@@PAYLOAD@@":json.dumps(data,separators=(",",":"),allow_nan=False).replace("<","\\u003c"),
                    "@@CDLA@@":html.escape(verified(args.runtime,"CDLA-Permissive-2.0.txt"),quote=False),
                    "@@CC0@@":html.escape(verified(args.runtime,"CC0-1.0.txt"),quote=False)}
    for marker, value in replacements.items():
        if template.count(marker) != 1:
            raise ValueError("Missing or repeated template marker "+marker)
        template = template.replace(marker,value)
    content = template.encode("utf-8")
    args.out.write_bytes(content)
    print(args.out, len(content), hashlib.sha256(content).hexdigest())


if __name__ == "__main__":
    main()
