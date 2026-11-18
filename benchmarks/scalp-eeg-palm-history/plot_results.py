"""Render the development participants and the participant-balanced cohort result."""

import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator


HERE = Path(__file__).resolve().parent
INK = "#17242e"
QUIET = "#425464"
HISTORY = "#23475c"
EEG = "#9b440f"
GRID = "#e2e9ed"


def load_rows(result_file):
    payload = result_file.read_bytes()
    report = json.loads(payload)
    if report["status"] != "archival_development_scored":
        raise ValueError("A scored post-observation result is required")
    dev_ids = report["roles"]["DEV"]
    pairs = report["dev_comparisons"]["primary"]
    methods = ("time_palm", "time_palm_eeg")
    if (pairs["baseline"], pairs["candidate"]) != methods:
        raise ValueError("Unexpected primary methods")
    rows = []
    for subject in dev_ids:
        participant = report["individuals"][subject]
        values = tuple(participant["metrics"][key]["rmse_mm"] for key in methods)
        rows.append((subject, participant["eligible_trials"], values))
    cohort = report["cohorts"]["DEV"]
    values = tuple(cohort["participant_balanced"][key]["rmse_mm"] for key in methods)
    if not rows or len(rows) != cohort["participants"]:
        raise ValueError("Development participant count disagrees with results")
    if cohort["trials"] != sum(row[1] for row in rows):
        raise ValueError("Development trial count disagrees with results")
    for idx, value in enumerate(values):
        calculated = math.sqrt(sum(row[2][idx] ** 2 for row in rows) / len(rows))
        if not math.isclose(value, calculated, rel_tol=1e-12):
            raise ValueError("Participant-balanced cohort value disagrees with the individual values")
    rows.append(("Equal-weight cohort", cohort["trials"], values))
    return rows, cohort["frames"], hashlib.sha256(payload).hexdigest()


def render(rows, frames, input_sha, output_file):
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Liberation Sans"],
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": QUIET,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })
    fig, ax = plt.subplots(figsize=(8.85, 4.62))
    fig.subplots_adjust(left=0.258, right=0.836, bottom=0.254, top=0.665)
    fig.text(0.04, 0.91, "Palm-position error with and without scalp EEG", fontsize=20, weight="bold")
    fig.text(
        0.04, 0.848,
        f"{len(rows) - 1} development participants  ·  {rows[-1][1]:,} trials  ·  {frames:,} matched target frames",
        fontsize=11, color=QUIET,
    )
    legend = [
        Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor="white",
               markeredgecolor=HISTORY, markeredgewidth=1.7, label="Timing + past palm"),
        Line2D([], [], marker="s", linestyle="", markersize=7, markerfacecolor=EEG,
               markeredgecolor=EEG, label="Timing + past palm + EEG"),
    ]
    fig.legend(
        handles=legend, loc="upper left", bbox_to_anchor=(0.04, 0.793), ncol=2, frameon=False,
        borderaxespad=0, handlelength=1, handletextpad=0.55, columnspacing=1.4, fontsize=10,
    )
    y_positions = [*range(len(rows) - 1), len(rows) - 0.7]
    highlight_y = y_positions[-1]
    ax.axhspan(highlight_y - 0.37, highlight_y + 0.37, color="#f1f5f8", zorder=0)
    largest = max(max(values) for _, _, values in rows)
    tick = 0.25 if largest <= 1.75 else 10 ** math.floor(math.log10(largest)) / 2
    limit = math.ceil(largest * 1.08 / tick) * tick
    ax.set(xlim=(0, limit), ylim=(highlight_y + 0.53, -0.55))
    ax.xaxis.set_major_locator(MultipleLocator(tick))
    ax.xaxis.set_major_formatter(lambda value, _: f"{value:g}")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", which="both", length=0, pad=8, labelsize=10)
    for key in ("right", "top"):
        ax.spines[key].set_visible(False)
    for key in ("bottom", "left"):
        ax.spines[key].set_color("#a5b2bb")
    ax.set_yticks(y_positions, [
        f"{subject}  ·  {trials} trials" if idx < len(rows) - 1 else subject
        for idx, (subject, trials, _) in enumerate(rows)
    ])
    for tick_label in ax.get_yticklabels():
        tick_label.set_color(INK)
    ax.get_yticklabels()[-1].set_fontweight("bold")
    ax.set_xlabel("Root mean squared error (mm)", fontsize=11, labelpad=8)
    for idx, (y, (_, _, (baseline, augmented))) in enumerate(zip(y_positions, rows, strict=True)):
        ax.plot([baseline, augmented], [y, y], color="#63737f", linewidth=1.9, solid_capstyle="round")
        ax.scatter(baseline, y, s=43, marker="o", facecolors="white", edgecolors=HISTORY, linewidths=1.5, zorder=4)
        ax.scatter(augmented, y, s=36, marker="s", color=EEG, zorder=5)
        ax.text(
            1.055, y, f"{augmented - baseline:+.3f}", transform=ax.get_yaxis_transform(),
            fontsize=11, weight="bold" if idx == len(rows) - 1 else "normal", va="center", color=INK,
        )
    ax.text(
        1.055, 1.04, "Change\nwith EEG (mm)", transform=ax.transAxes,
        fontsize=9, va="bottom", color=QUIET,
    )
    fig.text(
        0.04, 0.097, "Cohort RMSE is the square root of the mean of the participants’ mean squared errors.",
        fontsize=9, color=QUIET,
    )
    fig.text(0.04, 0.055, "IACKD ds006840 v1.0.0 · Archived right-hand R1 trials · 100 ms stored-clock input lead", fontsize=9, color=QUIET)
    baseline, augmented = rows[-1][2]
    description = (
        f"Cohort root mean squared error was {baseline:.3f} mm with timing and past palm "
        f"and {augmented:.3f} mm with additional EEG. Change with EEG by participant: "
        + ", ".join(f"{subject} {with_eeg - without:+.3f} mm" for subject, _, (without, with_eeg) in rows[:-1])
        + ". The cohort gives equal weight to each development participant."
    )
    buffer = BytesIO()
    fig.savefig(buffer, dpi=300, format="png", metadata={
        "Title": "Palm-position error with and without scalp EEG",
        "Description": description,
        "Source": f"RESULT.json SHA-256 {input_sha}",
    })
    plt.close(fig)
    output_file.write_bytes(buffer.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE / "RESULT.json")
    parser.add_argument("--output", type=Path, default=HERE / "cohort-comparison.png")
    options = parser.parse_args()
    render(*load_rows(options.input), options.output)
