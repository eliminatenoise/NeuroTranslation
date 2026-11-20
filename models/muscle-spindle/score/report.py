"""Derive the short, source-bound readout from saved hierarchical scores."""

import argparse
import csv
import gzip
import json
from pathlib import Path


def val(v):
    return "undefined" if v is None else f"{v:.5g}"


def write(folder):
    summary = json.loads((folder / "summary.json").read_text())
    sizes = summary["group_sizes_windows"]
    ps = summary["models"]["full"]
    p = summary["population"]
    held_level = summary["held_unit"]
    held_groups = list(sizes["full"][held_level])
    text = [
        "# Held recording-group forecast",
        "",
        f"**{p}**. {summary['interpretation'].rstrip('.')}.",
        f"The source contains {sizes['full']['macro']['all']:,} scored windows in "
        f"{len(sizes['full']['trial'])} trials and {len(sizes['full']['member'])} afferent members. "
        f"The nonoverlapping lag comparison retains {sizes['common_lag']['macro']['all']:,} windows. "
        "All counts refer to detected spikes per 20 ms.",
        "",
        "| Model | Held mean deviance | Held count MAE | Mean observed | Mean forecast | Observed / forecast |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, method in ps.items():
        st = method.get("mean", method.get("fixed"))["macro"]["all"]
        text.append(
            "| "
            + name
            + " | "
            + " | ".join(
                val(st[k])
                for k in (
                    "deviance",
                    "mae",
                    "observed",
                    "forecast",
                    "observed_over_forecast",
                )
            )
            + " |"
        )
    text.extend(
        [
            "",
            "## Exploratory held-afferent comparisons"
            if held_level == "member"
            else "## Frozen gates",
            "",
            "| Comparison | Passed | Unmet conditions |",
            "| --- | --- | --- |",
        ]
    )
    for name, gate in summary["gates"].items():
        unmet = [k.replace("_", " ") for k, v in gate["conditions"].items() if not v]
        text.append(
            f"| {name} | {'yes' if gate['pass_all'] else 'no'} | {', '.join(unmet) or 'none'} |"
        )
    text.extend(
        [
            "",
            "## Between-recording spread",
            "",
            "The entries below subtract the comparator loss from the combined model loss. "
            "Negative differences indicate a lower error for the combined model. "
            "These held groups describe archive records. Independent-animal identity is unverified.",
            "",
            "| Contrast | "
            + " | ".join(g + " Δ deviance" for g in held_groups)
            + " | Macro Δ MAE | Members with lower deviance |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    with gzip.open(folder / "paired-differences.csv.gz", "rt") as file:
        pairs = list(csv.DictReader(file))
    for tag in [
        "glm_combined_vs_history",
        "glm_combined_vs_mechanics",
        "glm_current_vs_stale_mechanics",
        "transformer_combined_vs_history",
        "transformer_combined_vs_mechanics",
        "transformer_current_vs_stale_mechanics",
        "transformer_vs_glm_joint",
        "transformer_vs_glm_afferent",
        "transformer_vs_glm_sampled",
    ]:
        selected = [
            r
            for r in pairs
            if r["comparison"] == tag and r["seed"] in ("mean", "fixed")
        ]
        px = {
            r["group"]: float(r["deviance"])
            for r in selected
            if r["level"] == held_level
        }
        mac = next(float(r["mae"]) for r in selected if r["level"] == "macro")
        members = [float(r["deviance"]) for r in selected if r["level"] == "member"]
        text.append(
            f"| {tag} | "
            + " | ".join(val(px[g]) for g in held_groups)
            + f" | {val(mac)} | {sum(v < 0 for v in members)} / {len(members)} |"
        )
    text.extend(
        [
            "",
            "## Calibration and replication",
            "",
            "The fixed calibration bins in calibration-bins.csv.gz report observed and predicted counts, absolute window counts and balanced mass. "
            "The largest errors can be inspected by afferent and trial in group-scores.csv.gz. "
            "The three Transformer seeds repeat the same source splits. Overlapping windows share spike history within trials. "
            "The reported ranges across held records and seeds describe these recordings and fits. "
            "The available archive groups cannot establish population uncertainty, cross-animal transfer or a biological feedback loop. "
            "The original prefix-5 reserve remains outside every fit and result.",
        ]
    )
    (folder / "READOUT.md").write_text("\n".join(text) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    write(args.folder)
