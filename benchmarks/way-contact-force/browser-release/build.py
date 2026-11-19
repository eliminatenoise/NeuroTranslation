"""Build a portable preview directly from the two accepted aggregate model archives."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import zipfile

HERE = Path(__file__).resolve().parent
NAME = "NeuroTranslation-Grip-After-Contact-Comparison"
RIDGE_SHA = "f4efbe7ca9c3c37ecb782b29846129e363e1910d104ae504262bb0b4f2e2d2d8"
CNN_SHA = "7aacd9a4cafbec773aebb0e663ce4c4f3139ab087427f60786e416ed0afd977b"
DEFAULT_RIDGE = HERE.parent / "neuro-contact-forecast-20261119" / "NeuroTranslation-Grip-After-Contact-Experimental-Preview.zip"
DEFAULT_CNN = HERE.parent / "neuro-contact-temporal-20261119" / "grip-contact-temporal-preview.zip"
ASSETS = ("index.html", "style.css", "forecast.js", "app.js", "README.md",
          "Run-Linux.sh", "Run-macOS.command", "Run-Windows.cmd")


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def selected(archive, expected_sha, names):
    if sha(archive.read_bytes()) != expected_sha:
        raise ValueError(f"Source archive failed SHA-256 verification: {archive.name}")
    with zipfile.ZipFile(archive) as zipped:
        matching = [name for name in zipped.namelist() if Path(name).name in names]
        if len(matching) != len(names) or {Path(name).name for name in matching} != set(names):
            raise ValueError("Expected exactly one member per selected source name.")
        return {Path(name).name: zipped.read(name) for name in matching}


def build(ridge_path, cnn_path):
    ridge = selected(ridge_path, RIDGE_SHA, ("parameters.json", "channel-order.json", "AGGREGATE-RESULTS.json"))
    cnn = selected(cnn_path, CNN_SHA, ("MODEL.json", "DEVELOPMENT.json"))
    ridge_parameters = json.loads(ridge["parameters.json"])
    cnn_parameters = json.loads(cnn["MODEL.json"])
    channels = json.loads(ridge["channel-order.json"])
    cnn_dev = json.loads(cnn["DEVELOPMENT.json"])
    ridge_dev = json.loads(ridge["AGGREGATE-RESULTS.json"])["development"]["populations"]
    if (channels["eeg"] != cnn_parameters["eeg_order"]
        or cnn_parameters["history_sample_rate_hz"] != 500
        or cnn_parameters["history_rows"] != 200 or cnn_parameters["forecast_sample_offset"] != 60
        or ridge_parameters["horizon_ms_on_recorded_clock"] != 120):
        raise ValueError("The shared forecast contract differs across the two archives.")
    matched = ridge_dev["matched"]["models"]
    ridge_rmse = {}
    for branch in ("mechanics", "aligned_eeg", "rotated_eeg"):
        group = ridge_dev["primary"]["models"][branch] if branch != "rotated_eeg" else matched[branch]
        count = (group["people"], group["trials"], group["rows"])
        result = group["equal_person_mean"]["rmse_n"]
        if count != (3, 882, 4410) or result != cnn_dev["companion_ridge_same_rows"][branch]["rmse_n"]:
            raise ValueError("Ridge and temporal evidence disagree on the common development comparison.")
        ridge_rmse[branch] = result
    cnn_rmse = {}
    for branch in ("mechanics", "aligned", "rotated"):
        section = "rotation" if branch == "rotated" else "primary"
        group = cnn_dev["scores"][section][branch]["full"]
        count = (group["participants"], group["trials"], group["rows"])
        if count != (3, 882, 4410):
            raise ValueError("A displayed temporal development score uses different row support.")
        cnn_rmse[branch] = group["rmse_n"]
    ridge_delta = ridge_dev["primary"]["paired"]["aligned_eeg_vs_mechanics"]
    cnn_delta = cnn_dev["primary_aligned_minus_mechanics"]
    assets = {
        "ridge": ridge_parameters["models"], "cnn": cnn_parameters["models"], "channels": channels,
        "development": {
            "participants": cnn_dev["participants"], "trials": cnn_dev["trials"], "rows": cnn_dev["rows"],
            "ridge": ridge_rmse, "cnn": cnn_rmse,
            "ridgeDelta": {"mean": ridge_delta["equal_person_mean_delta_n"],
                           "interval": ridge_delta["descriptive_t95_interval_n"]},
            "cnnDelta": {"mean": cnn_delta["mean_rmse_change_n"],
                         "interval": cnn_delta["descriptive_t_interval_95_n"]},
        },
    }
    manifest = {
        "model_edition": "2026-11-19 experimental preview",
        "study": "WAY-EEG-GAL force-confirmation grip forecast",
        "glossary": {"revision": cnn_dev["glossary_revision"], "sha256": cnn_dev["glossary_sha256"]},
        "sources": {
            "ridge": {"archive": ridge_path.name, "sha256": RIDGE_SHA,
                      "members": {name: sha(contents) for name, contents in ridge.items()}},
            "cnn": {"archive": cnn_path.name, "sha256": CNN_SHA,
                    "members": {name: sha(contents) for name, contents in cnn.items()}},
        },
        "contains": ["derived fitted parameters", "aggregate development scores", "invented sensor generator"],
        "file_sha256": {},
    }

    destination = HERE / "dist" / NAME
    destination.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        shutil.copy2(HERE / "web" / name, destination / name)
    data = json.dumps(assets, separators=(",", ":"), allow_nan=False, ensure_ascii=True)
    generated = f"/* Generated by build.py from checksum-bound model packages. */\n" \
                f"globalThis.ContactModelData = {data};\n"
    (destination / "model-data.js").write_text(generated, encoding="utf-8")
    files = (*ASSETS, "model-data.js")
    for name in files:
        manifest["file_sha256"][name] = sha((destination / name).read_bytes())
    (destination / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    archive = destination.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for name in sorted((*files, "MANIFEST.json")):
            info = zipfile.ZipInfo(f"{NAME}/{name}", (2026, 11, 19, 12, 0, 0))
            info.create_system = 3
            mode = 0o755 if name in ("Run-Linux.sh", "Run-macOS.command") else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            zipped.writestr(info, (destination / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                           compresslevel=9)
    print(sha(archive.read_bytes()), archive.relative_to(HERE))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ridge", type=Path, default=DEFAULT_RIDGE)
    parser.add_argument("--cnn", type=Path, default=DEFAULT_CNN)
    arguments = parser.parse_args()
    build(arguments.ridge, arguments.cnn)
