"""Build the browser runtime from the approved, publicly released frozen checkpoint."""

import argparse
import base64
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ARCHIVE_SHA256 = "6ff18be033fb566606c22455746702b28a776a9f9e935cac9200072f57efd312"
FIT_SEAL_SHA256 = "e888a96ddfa14e5ee3ec8788bdedede89da3b9646ca201ea9e99e21542788e8a"
DESIGN_SHA256 = "69518d134127f762d7199f1fb64b28c471655f158d63bf8592199388af03ec35"
SEEDS = (17, 29, 43)
METHOD_CHANNELS = {"motion": 2, "combined": 10}
NORMALIZATION_WIDTHS = {
    "bins_center": 10, "bins_scale": 10, "anchor_center": 2, "anchor_scale": 2,
    "residual_center": 2, "residual_scale": 2,
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_npz(public_zip, filename, expected_digest):
    contents = public_zip.read(f"checkpoint/{filename}")
    if sha256(contents) != expected_digest:
        raise ValueError(f"Frozen checkpoint member changed: {filename}")
    with np.load(io.BytesIO(contents), allow_pickle=False) as bundle:
        return dict(bundle)


def parameter_shapes(channels):
    return {
        "encoder.0.weight": (16, channels, 3),
        "encoder.0.bias": (16,),
        "encoder.2.weight": (16, 16, 3),
        "encoder.2.bias": (16,),
        "predictor.0.weight": (32, 16 * 12 + 8),
        "predictor.0.bias": (32,),
        "predictor.2.weight": (2, 32),
        "predictor.2.bias": (2,),
    }


def as_model_bytes(arrays, channels):
    shapes = parameter_shapes(channels)
    if set(arrays) != set(shapes):
        raise ValueError("Frozen checkpoint parameter names disagree with the public architecture")
    chunks = []
    for name, shape in shapes.items():
        values = arrays[name]
        if values.shape != shape or values.dtype != np.float32 or not np.isfinite(values).all():
            raise ValueError(f"Invalid frozen float32 parameter: {name}")
        chunks.append(values.astype("<f4", copy=False).tobytes(order="C"))
    return b"".join(chunks)


def read_checkpoint(path):
    data = path.read_bytes()
    if sha256(data) != ARCHIVE_SHA256:
        raise ValueError("Input archive differs from the approved public R1 release")
    model_filenames = {f"{method}-{seed}.npz" for method in METHOD_CHANNELS for seed in SEEDS}
    with zipfile.ZipFile(io.BytesIO(data)) as public_zip:
        receipt = json.loads(public_zip.read("checkpoint/CHECKPOINT.json"))
        keys = receipt["weights_sha256"]
        if (set(keys) != model_filenames | {"fit-arrays.npz"}
                or receipt["original_train_seal_sha256"] != FIT_SEAL_SHA256
                or receipt["original_design_sha256"] != DESIGN_SHA256):
            raise ValueError("The approval, study or checkpoint inventory differs from R1")
        arrays = read_npz(public_zip, "fit-arrays.npz", keys["fit-arrays.npz"])
        normalization = {}
        for name, width in NORMALIZATION_WIDTHS.items():
            value = arrays[name]
            if (value.shape != (width,) or value.dtype != np.float64 or not np.isfinite(value).all()
                    or (name.endswith("_scale") and (value <= 0).any())):
                raise ValueError(f"Invalid frozen float64 normalization: {name}")
            normalization[name] = value.tolist()
        models = {}
        for method, channels in METHOD_CHANNELS.items():
            models[method] = {}
            for seed in SEEDS:
                filename = f"{method}-{seed}.npz"
                weights = read_npz(public_zip, filename, keys[filename])
                values = as_model_bytes(weights, channels)
                models[method][str(seed)] = base64.b64encode(values).decode("ascii")
    return {
        "fitSealSha256": FIT_SEAL_SHA256,
        "designSha256": DESIGN_SHA256,
        "publicArchiveSha256": ARCHIVE_SHA256,
        "checkpointFilesSha256": keys,
        "normalization": normalization,
        "models": models,
    }


def read_commitments(path, expected_digest):
    data = path.read_bytes()
    if len(data) != 960 * 65 or sha256(data) != expected_digest:
        raise ValueError("The commitment catalogue differs from its exact accepted source")
    if not re.fullmatch(rb"(?:[0-9a-f]{64}\n){960}", data):
        raise ValueError("Expected exactly 960 lowercase SHA-256 commitments with LF endings")
    digests = data.decode("ascii").splitlines()
    if digests != sorted(set(digests)):
        raise ValueError("Expected commitments in sorted order without duplicates")
    return {"fileSha256": expected_digest, "sha256": digests}


def js_data(name, value):
    return f"const {name} = {json.dumps(value, indent=2, allow_nan=False)};\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-release", type=Path, required=True)
    parser.add_argument("--catalogue", type=Path, required=True)
    parser.add_argument("--catalogue-sha256", required=True)
    args = parser.parse_args()
    weights = js_data("temporalCheckpoint", read_checkpoint(args.public_release))
    commitments = js_data("recordedCommitments", read_commitments(args.catalogue, args.catalogue_sha256))

    source = (HERE / "temporal-inference.mjs").read_text(encoding="utf-8")
    imports = ('import { recordedCommitments } from "./recorded-commitments.mjs";\n'
               'import { temporalCheckpoint } from "./temporal-weights.mjs";\n')
    export = "export async function forecastRecordedTrial(packet)"
    if not source.startswith(imports) or source.count(export) != 1:
        raise ValueError("The browser classic build needs the expected two imports and single export")
    runtime = source.removeprefix(imports).replace(export, "async function forecastRecordedTrial(packet)")
    outputs = {
        "temporal-weights.mjs": "export " + weights,
        "recorded-commitments.mjs": "export " + commitments,
        "wrist-recorded.js": (
            "// Generated by build_runtime.py from the released checkpoint and verified trial hashes.\n"
            '"use strict";\n\nwindow.WristRecorded = (() => {\n' + weights + commitments + runtime
            + "\nreturn Object.freeze({ forecastRecordedTrial });\n})();\n"
        ),
    }
    for filename, output in outputs.items():
        (HERE / filename).write_text(output, encoding="utf-8", newline="\n")
        print(filename, sha256(output.encode("utf-8")), len(output.encode("utf-8")))


if __name__ == "__main__":
    main()
