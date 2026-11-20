"""Make the public aggregate reports from the original local study outputs."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from ofner_transfer import FILES, filename

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")) + "\n")


def aggregate(report, original_hash, freeze_hash):
    people = report["people"]
    s = report["summary"]
    methods = {
        k: {"score": v["score"], "native_mae": v["native_mae"]}
        for k, v in s["methods"].items()
    }
    contrasts = {}
    for k, c in s["contrasts"].items():
        parts = {
            a: c[a]
            for a in (
                "defined",
                "pass",
                "mean_difference",
                "relative_change",
                "paired_percentile_95",
                "people_with_lower_error",
            )
            if a in c
        }
        if c["defined"]:
            parts["sorted_paired_differences"] = sorted(
                c["differences_in_people_order"]
            )
        contrasts[k] = parts
    by_cue = {}
    for cue in report["cues"]:
        entries = [
            p["methods"] for p in people if cue in p["methods"]["transformer"]["by_cue"]
        ]
        if not entries:
            continue
        vals = {}
        for method in methods:
            local = [p[method]["by_cue"][cue] for p in entries]
            scores = [v["score"] for v in local]
            vals[method] = {
                "score": float(np.mean(scores)) if None not in scores else None,
                "native_mae": np.mean(
                    [v["native_mae"] for v in local], axis=0
                ).tolist(),
            }
        by_cue[cue] = {
            "n": sum(p["transformer"]["by_cue"][cue]["n"] for p in entries),
            "n_people": len(entries),
            "methods": vals,
        }
    runs = report["source_runs"]
    flat = [
        r["flat_target_coordinates"]
        for r in runs
        if r["flat_target_coordinates"] is not None
    ]
    return {
        "projection_format": "cued-arm-cohort-v1",
        "source_report_sha256": original_hash,
        "freeze_sha256": freeze_hash,
        "cohort": report["cohort"],
        "n": report["n"],
        "n_people": len(people),
        "n_runs": sum(len(p["runs"]) for p in people),
        "n_scheduled_runs": len(runs),
        "n_outside_fit_range": sum(p["outside_fit_range"] for p in people),
        "runs_with_constant_target_by_horizon_and_instrument": np.sum(
            flat, axis=0
        ).tolist()
        if flat
        else None,
        "n_runs_with_constant_glove_target_all_horizons": sum(
            all(v[2] for v in r) for r in flat
        ),
        "channels": report["channels"],
        "horizons_s": report["horizons_s"],
        "cues": report["cues"],
        "summary": {
            "methods": methods,
            "contrasts": contrasts,
            "criteria": s["criteria"],
            "overall_advantage": s["overall_advantage"],
            "complete_people_cues_runs": s["complete_people_cues_runs"],
        },
        "by_cue": by_cue,
    }


def project(frozen_dir, output, assessment=None):
    output.mkdir(parents=True, exist_ok=True)
    seal = read(frozen_dir / "freeze.json")
    freeze_hash = sha(frozen_dir / "freeze.json")
    projection_sums = {}
    for name in ("development.json", "training-source.json", "fit-diagnostics.json"):
        if sha(frozen_dir / name) != seal["products"][name]:
            raise ValueError(
                "An original fitting product differs from the frozen digest."
            )

    def add(name, original, data):
        write(output / name, data)
        projection_sums[name] = {
            "sha256": sha(output / name),
            "source_report_sha256": sha(original),
        }

    original = frozen_dir / "development.json"
    add(
        "development-summary.json",
        original,
        aggregate(read(original), sha(original), freeze_hash),
    )
    original = frozen_dir / "training-source.json"
    records = []
    for r in read(original):
        person, run = r["person"], r["run"]
        size, publisher_md5 = FILES[person][run - 1]
        records.append(
            {
                "source_filename": filename(person, run),
                "bytes": size,
                "publisher_md5": publisher_md5,
                "source_sha256": r["source_sha256"],
            }
        )
    add(
        "training-inventory.json",
        original,
        {
            "format": "source-file-inventory-v1",
            "source_report_sha256": sha(original),
            "freeze_sha256": freeze_hash,
            "files": records,
        },
    )
    original = frozen_dir / "fit-diagnostics.json"
    add(
        "training-diagnostics.json",
        original,
        {
            "format": "pooled-final-fit-v1",
            "source_report_sha256": sha(original),
            "freeze_sha256": freeze_hash,
            "all_seven": read(original)["all_seven"],
        },
    )
    if assessment is not None:
        report = read(assessment)
        if (
            report["freeze_sha256"] != freeze_hash
            or report["model_sha256"] != seal["products"]["model.json"]
        ):
            raise ValueError("Assessment report belongs to a different frozen fit.")
        add(
            "assessment-summary.json",
            assessment,
            aggregate(report, sha(assessment), freeze_hash),
        )
    write(
        output / "projection-manifest.json",
        {
            "format": "cued-arm-public-projections-v1",
            "freeze_sha256": freeze_hash,
            "model_sha256": seal["products"]["model.json"],
            "projection_source_sha256": sha(HERE / "project_reports.py"),
            "origin": "Study outputs are summarized across people. Each contrast sorts its paired differences independently.",
            "public_reports": projection_sums,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_fit_directory", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--assessment-original", type=Path)
    args = parser.parse_args()
    project(
        args.original_fit_directory, args.output_directory, args.assessment_original
    )
