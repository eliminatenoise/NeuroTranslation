"""Build the self-contained JavaScript evaluator from its exact public release."""

from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
PUBLIC_ARCHIVE = HERE.parent / "WristMotion-Forearm-Correction.zip"
ZIP_PATH = "benchmarks/wrist-forearm-transfer/WristMotion-Forearm-Correction.zip"
REPO = "https://github.com/eliminatenoise/NeuroTranslation"
COMMIT = "51cb7a250c029af86c154b5c233c87fc69d1bc90"
ARCHIVE_SHA = "29c2ec08aac01d07f58d7a1cecd37a0868004e4d48b89d173e87e757b5cb3234"
UPSTREAM = {
    "MODEL.json": "b3b9efef1ebdad42f4545747e90c6dee3170d774340590167446b312aba17d72",
    "SYNTHETIC-CASES.json": "98660cb01b0ae3542ea32da999e782f3ed8a905a1a331edf2c8c8bde74052be2",
    "portable.py": "5285dde41bd3b23c4627824d69a25a8aa1c0343aae5902fb5417c306a5b78914",
    "DESIGN.json": "5c1e109fac72426b5a5eef052c6b08ff6429b0def78ec8f1f840aa19bd1e0b96",
    "AGGREGATE.json": "8dd5aa9c75e1e19f9ccd2238ea194b42e49ef37502a4f11d455277828eadea72",
}
GLOSSARY_VERSION = 36
GLOSSARY_SHA = "40b98695e6204bc9e305ecdea853756aec30f48a6ae67d29e92c8bb220b3e406"
OFFSETS = (384, 512, 640, 768, 896, 1024)


def check(payload, digest, label):
    if sha256(payload).hexdigest() != digest:
        raise ValueError(f"{label} does not match the pinned release")
    return payload


def upstream_members():
    archive = PUBLIC_ARCHIVE.read_bytes()
    check(archive, ARCHIVE_SHA, "Public model ZIP")
    with ZipFile(BytesIO(archive)) as bundle:
        return {name: check(bundle.read(f"WristMotion-Forearm-Correction/{name}"), digest, name)
                for name, digest in UPSTREAM.items()}


def illustrative_window(slot, variant):
    """Extend the public fixture's deterministic waveforms to new artificial inputs."""
    offset = OFFSETS[slot]
    motion = [[math.sin(i / (5 + slot)) + (0.15 + 0.07 * variant) * (i - 15),
               math.cos(i / (6 + slot)) - 0.11 * (i - 15)] for i in range(16)]

    def signed(sample, electrode):
        phase = sample / (1.4 + electrode / 1.5) + slot * 0.3 + variant
        return math.cos(phase) * (5 + electrode + variant * 6)

    emg = [[math.sqrt(math.fsum((signed(sample, 2 * pair) - signed(sample, 2 * pair + 1)) ** 2
                               for sample in range(start, start + 16)) / 16)
            for pair in range(4)] for start in range(0, 256, 16)]
    return {
        "target_offset_ticks": offset,
        "anchor_deg": [round((0.35 + 0.09 * variant) * offset / 30, 12), round(-0.19 * offset / 32, 12)],
        "motion_bins_deg_relative_to_anchor": [[round(value, 12) for value in row] for row in motion],
        "emg_differential_rms_uv": [[round(value, 12) for value in row] for row in emg],
    }


def main():
    members = upstream_members()
    model = json.loads(members["MODEL.json"])
    if model["design_sha256"] != UPSTREAM["DESIGN.json"]:
        raise ValueError("The model does not belong to the pinned study design")
    examples = [illustrative_window(slot, variant) for slot, variant in ((0, 0.25), (2, 0.50), (5, 0.75))]
    pins = {
        "sourceRepository": REPO,
        "sourceCommit": COMMIT,
        "sourceArchivePath": ZIP_PATH,
        "sourceArchiveSha256": ARCHIVE_SHA,
        "modelSha256": UPSTREAM["MODEL.json"],
        "pythonSha256": UPSTREAM["portable.py"],
        "syntheticSha256": UPSTREAM["SYNTHETIC-CASES.json"],
        "designSha256": UPSTREAM["DESIGN.json"],
        "aggregateSha256": UPSTREAM["AGGREGATE.json"],
        "parentMotionSealSha256": model["parent_motion_temporal_sha256"],
        "transferTrainSealSha256": model["transfer_train_sha256"],
        "glossaryRevision": GLOSSARY_VERSION,
        "glossarySha256": GLOSSARY_SHA,
    }
    source = (HERE / "model-runtime.js.in").read_text(encoding="utf-8")
    replacements = {
        "RELEASED_MODEL": members["MODEL.json"].decode().strip(),
        "RELEASED_SYNTHETIC": members["SYNTHETIC-CASES.json"].decode().strip(),
        "ILLUSTRATIVE_WINDOWS": json.dumps(examples, indent=2, allow_nan=False),
        "SOURCE_PINS": json.dumps(pins, indent=2, allow_nan=False),
    }
    for marker, payload in replacements.items():
        token = f"/* {marker} */"
        if source.count(token) != 1:
            raise ValueError(f"Expected one insertion point for {marker}")
        source = source.replace(token, payload)
    output = HERE / "forearm-model.js"
    output.write_bytes(source.encode("utf-8"))
    print(f"{sha256(output.read_bytes()).hexdigest()}  {output.name}")


if __name__ == "__main__":
    main()
