"""Embed the unchanged public development archive pins and trial commitments."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
RELEASE = HERE.parent / "WristMotion-Forearm-Recorded-Trial.zip"
RELEASE_SHA = "f752a2bb44dad136281d19cc0bcef37e9dd8422bb568b722e40e86823d1092a6"
CONVERTER = "WristMotion-Forearm-Recorded-Trial/wrist-recorded-trial-converter-v1/"
PINS = (
    ("RECIPE_TEXT", "DEVELOPMENT-ARCHIVE-PINS.json", "a0b4db26cd12926aa57a2797f766d0d7da27976cfa773168c56b6516755e1725"),
    ("CATALOGUE_TEXT", "wrist-recorded-development-sha256.txt", "2f6422705881398013b3245fb0d5fb4b0c5bb0528160c2325be8bdbc0286ff30"),
)


def require_sha(data, expected):
    if sha256(data).hexdigest() != expected:
        raise ValueError("The pinned public source changed")


def main():
    released = RELEASE.read_bytes()
    require_sha(released, RELEASE_SHA)
    chunks = ["/* WristMotion browser archive reader. See the companion documentation for sources. */\n",
              "(() => {\n  \"use strict\";\n\n"]
    with ZipFile(BytesIO(released)) as archive:
        for symbol, name, digest in PINS:
            data = archive.read(CONVERTER + name)
            require_sha(data, digest)
            source = data.decode("ascii")
            if "`" in source or "${" in source or "\r" in source:
                raise ValueError("This source cannot be embedded verbatim")
            chunks.append(f"  const {symbol} = String.raw`{source}`;\n\n")
    chunks.append((HERE / "archive-core.js").read_text())
    chunks.append("})();\n")
    (HERE / "wrist-archive.js").write_bytes("".join(chunks).encode("utf-8"))


if __name__ == "__main__":
    main()
