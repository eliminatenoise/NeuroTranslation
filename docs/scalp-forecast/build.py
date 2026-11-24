"""Rebuild the static reader and its optional offline ZIP using Python 3.10+."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent
APP = ["index.html", "build.py", "README.md", "NOTICE.md", "CC0.txt", "CC-BY-4.0.txt",
       "Open on Windows.cmd", "Open on Linux.sh", "Open on macOS.command",
       "src/page.html", "src/style.css", "src/charts.js", "src/app.js", "src/predict.js"]
METHOD = ["model.json", "example.json", "predict.py", "development.json", "assessment.json",
          "PROTOCOL.md", "provenance.json"]
FILES = sorted(APP + ["method/" + path for path in METHOD])
LABELS = {"scalp_shift": "Cue + motion + shuffled scalp", "scalp_eye_shift": "Cue + motion + eye + shuffled scalp",
          "mispaired_fit_shift": "Mismatched fit + shuffled scalp"}


def read(name):
    return json.loads((ROOT / name).read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload():
    seals = read("method/provenance.json")["files"]
    needed = {"src/predict.js", *("method/" + name for name in METHOD if name != "provenance.json")}
    if set(seals) != needed:
        raise ValueError("Incomplete scientific inventory")
    for name in needed:
        if seals[name] != sha(ROOT / name):
            raise ValueError("Scientific file has changed: " + name)
    model = read("method/model.json")
    if model["format"] != "early-scalp-arm-v1":
        raise ValueError("Unsupported fitted model format")
    cohorts = {}
    for name, label, description in [
        ("assessment", "Five people · fourth run", "Each of five people supplied their fourth execution run."),
        ("development", "Seven people · leave one out", "Each development fold withheld one of seven people and tested their three execution runs."),
    ]:
        group = read("method/" + name + ".json")
        if group["projection_format"] != "early-scalp-cohort-v1":
            raise ValueError("Expected a cohort-only projection")
        cohorts[name] = {**group, "label": label, "description": description}
        cohorts[name]["contrasts"] = {k: {"a": v["candidate"], "b": v["comparator"], "wins": v["people_lower"],
                                          "delta": v["mean_difference"], "interval": v["paired_95pct"], "pass": v["gate"]}
                                       for k, v in group["contrasts"].items()}
    ass = cohorts["assessment"]
    primary = ass["contrasts"]["scalp_over_history"]
    s, h = (ass["methods"][key]["normalized_mae"] for key in ["scalp", "history"])
    sentence = (f"Across {ass['n_people']} people outside the fit, adding scalp signals to the cue and early motion gave "
                f"an overall error of {s:.6f}. Cue and motion alone scored {h:.6f}. "
                f"The scalp model had lower error in {primary['wins']} of {ass['n_people']} people.")
    engineering = ass["gates"]["engineering_advantage"]
    if engineering is True:
        sentence += " The scalp fit cleared the study’s practical and pairing comparisons."
    elif engineering is False:
        sentence += " It fell short of the study’s combined practical and pairing criterion."
    else:
        sentence += " Coverage was insufficient for the study’s formal decision."
    gate = ass["gates"]["increment_beyond_measured_eyes"]
    gate_text = {True: "The assessment met the study’s full comparison for an incremental forecast advantage beyond the measured eye signals.",
                 False: "The assessment fell short of the study’s full criterion for an incremental forecast advantage beyond the measured eye signals.",
                 None: "The study could not decide whether scalp inputs added a forecast advantage beyond the measured eye signals."}[gate]
    eye_text = ("In the seven-person development signal check, simultaneous central scalp and eye-channel 63 recordings had a "
                "median absolute correlation of 0.327 in the first quarter-second after the cue. Pairing the central scalp signal "
                "with the next same-cue trial’s eye recording gave 0.195. The central signal averaged C3 and C4. "
                "These correlations cannot apportion the signal among eye movement, shared reference, cue responses and other sources. "
                + gate_text)
    return {"model": model, "example": read("method/example.json"),
            "reports": {"cohorts": cohorts, "labels": LABELS, "eye_observation": eye_text, "assessment_result": sentence}}


def build(archive=None):
    page = (ROOT / "src/page.html").read_text(encoding="utf-8")
    if page.count("__EMBEDDED_PAYLOAD__") != 1:
        raise ValueError("Missing or repeated data marker")
    data = json.dumps(payload(), ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    (ROOT / "index.html").write_bytes(page.replace("__EMBEDDED_PAYLOAD__", data).encode("utf-8"))
    sums = "".join(sha(ROOT / name) + "  " + name + "\n" for name in FILES)
    (ROOT / "SHA256SUMS").write_bytes(sums.encode("utf-8"))
    if archive:
        members = sorted([*FILES, "SHA256SUMS"])
        if archive.resolve() in {(ROOT / name).resolve() for name in members}:
            raise ValueError("Choose a separate destination for the ZIP")
        with ZipFile(archive, "w") as out:
            for name in members:
                info = ZipInfo("scalp-forecast/" + name, (2026, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100755 if name.endswith((".sh", ".command")) else 0o100644) << 16
                out.writestr(info, (ROOT / name).read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, help="Write a portable ZIP to this path")
    build(parser.parse_args().zip)
