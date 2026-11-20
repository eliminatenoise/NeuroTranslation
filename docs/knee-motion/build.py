"""Build the portable knee-angle viewer from the pinned released model and study."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
METHODS = ("persistence", "slope", "knee_ridge", "all_ridge", "transformer")


def load_inputs(folder):
    result = {}
    for key, expected in json.loads((SRC / "inputs.sha256.json").read_text()).items():
        content = (folder / key).read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"Model/study source has changed: {key}")
        if key.endswith(".json"):
            result[key] = json.loads(content)
    return result


def build(folder):
    inputs = load_inputs(folder)
    w, ex, scores, sources, phase = (inputs[name] for name in
        ("weights.json", "example.json", "results.json", "sources.json", "phase-results.json"))
    members = sorted((row for row in sources["members"] if row["split"] == "test"), key=lambda r: r["subject"])
    if len(members) != scores["test_people"] or not members or sum(r["eligible_windows"] for r in members) != scores["test_windows"]:
        raise ValueError("Source membership differs from the held-person assessment")
    ci = phase["paired_person_bootstrap_ci95"]
    extended = (
        f"A longer look changed the result. On the {phase['eligible_cutoffs']:,} windows with four seconds "
        f"of knee history, replaying a similar point in an earlier stride gave {phase['prior_stride_mean_mae_degrees']:.2f}° "
        f"error. The transformer, with 0.4 seconds of history, gave {phase['transformer_mean_mae_degrees']:.2f}°. "
        f"Stride replay had the smaller error in {phase['prior_stride_wins']} of {phase['test_people']} walkers. "
        f"Its mean advantage was {phase['transformer_minus_stride_mae_degrees']:.2f}° "
        f"(95% participant-bootstrap interval {ci[0]:.2f}° to {ci[1]:.2f}°)."
    )
    study = dict(weights=w, example=ex, errors={name: scores["error_summary"][name]["equal_person_mean_mae_degrees"]
        for name in METHODS}, trainPeople=scores["train_people"], testPeople=scores["test_people"],
        testWindows=scores["test_windows"], extended=extended, source=dict(columns=sources["columns"],
        frame_column=sources["frame_column"], members=members))
    payload = json.dumps(study, separators=(",", ":"), allow_nan=False).replace("<", r"\u003c")
    scripts = "\n".join((SRC / name).read_text() for name in ("forecast.js", "input.js", "view.js"))
    return (SRC / "page.html").read_text().replace("__STYLE__", (SRC / "style.css").read_text()).replace(
        "__STUDY__", payload).replace("__SCRIPTS__", scripts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=HERE.parent.parent / "models/knee-motion")
    parser.add_argument("--out", type=Path, default=HERE / "index.html")
    args = parser.parse_args()
    args.out.write_text(build(args.model), encoding="utf-8")
