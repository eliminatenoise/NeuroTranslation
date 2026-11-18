"""Regenerate or check the offline grip-force browser from public materials."""

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


HERE = Path(__file__).resolve().parent
BENCHMARK = HERE.parent
REPO = HERE.parents[2]
BROWSER = REPO / "docs/grip-force"
PACKAGE = BENCHMARK / "WAY-EEG-GAL-grip-force-experimental-preview.zip"
PORTABLE = BENCHMARK / "WAY-EEG-GAL-grip-force-browser.zip"
PACKAGE_SHA256 = "d0d04f87bcbfedb487e68e36d558c021e91af96bce8d5e35434908caa37d913b"
MEMBERS = {
    "models.json": "6fb95883e35ad0e9da56a9d52961a4f21e86463b8b2930bb30848c52fb07de0f",
    "channel-order.json": "9c6703205c9f9e0b58fd7bd820808cc08af507ae3d7d6d5c96ae05b39a124e4b",
    "aggregate-dev-summary.json": "1f831ffa7cfe943b100487e7fdddeb980628d9827b5d4c05fbf54dc2931e7021",
}
BRANCHES = ("strong", "eeg", "emg", "emg_eeg")
BROWSER_FILES = ("app.js", "forecast.js", "index.html", "study.js", "style.css")
LAUNCHERS = ("Run-Linux.sh", "Run-Windows.cmd", "Run-macOS.command")


def checked(data, digest, label):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"SHA-256 differs from the accepted public source: {label}")
    return data


def study_script():
    source = checked(PACKAGE.read_bytes(), PACKAGE_SHA256, PACKAGE.name)
    with ZipFile(BytesIO(source)) as archive:
        files = {
            name: checked(archive.read(f"WAY-EEG-GAL-grip-force/{name}"), digest, name)
            for name, digest in MEMBERS.items()
        }
    model = files["models.json"].decode("utf-8").strip()
    channels = json.loads(files["channel-order.json"])
    dev = json.loads(files["aggregate-dev-summary.json"])
    matched = dev["dev_matched_phase"]
    higher_force = dev["dev_target_force_strata"]["target_force_above_0p5_n"]
    metadata = {
        "packageSha256": PACKAGE_SHA256,
        "modelSha256": MEMBERS["models.json"],
        "developmentSha256": MEMBERS["aggregate-dev-summary.json"],
        "glossaryRevision": dev["glossary_revision"],
        "glossarySha256": dev["glossary_sha256"],
        "eegChannels": channels["eeg"],
        "emgChannels": channels["emg"],
        "development": {
            "participants": dev["participants"],
            "pairedRows": dev["paired_rows"],
            "phaseRows": dev["phase_rows"],
            "aboveHalfNewtonRows": higher_force["strong"]["rows"],
            "gatePassed": dev["preregistered_comparisons_all_passed"],
            "matchedRmse": {key: value["rmse_n"] for key, value in matched.items()},
            "wholeRmse": {key: dev["dev_full"][key]["rmse_n"] for key in BRANCHES},
            "aboveHalfNewtonRmse": {key: higher_force[key]["rmse_n"] for key in BRANCHES},
        },
    }
    # Keep the accepted generator's provenance line for byte-identical reproduction.
    text = ('/* Generated from the exact accepted archive by tests/bind_study.py. */\n'
            f'"use strict";\nconst WayStudy = {{ models: {model},\n'
            f'  metadata: {json.dumps(metadata, ensure_ascii=True, indent=2)}\n}};\n')
    return text.encode("utf-8")


def offline_zip(study):
    files = {name: (BROWSER / name).read_bytes() for name in BROWSER_FILES if name != "study.js"}
    files["study.js"] = study
    files.update({name: (HERE / name).read_bytes() for name in (*LAUNCHERS, "README.md")})
    files["LICENSE"] = (REPO / "LICENSE").read_bytes().replace(b"\r\n", b"\n")

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            entry = ZipInfo(f"{PORTABLE.stem}/{name}", date_time=(2026, 11, 19, 0, 0, 0))
            entry.create_system = 3
            mode = 0o100755 if name.endswith((".sh", ".command")) else 0o100644
            entry.external_attr = mode << 16
            archive.writestr(entry, data)
    return output.getvalue()


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--write", action="store_true", help="Write the study binding and offline ZIP.")
    options = args.parse_args()
    study = study_script()
    archive = offline_zip(study)
    for path, expected in ((BROWSER / "study.js", study), (PORTABLE, archive)):
        if options.write:
            path.write_bytes(expected)
        elif path.read_bytes() != expected:
            raise SystemExit(f"Local bytes differ from the reproducible build: {path.name}")
        print(f"{hashlib.sha256(expected).hexdigest()}  {path.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
