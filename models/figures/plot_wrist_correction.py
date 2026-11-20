"""Plot the person-balanced scores from the published six-person wrist comparison."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "neurotranslate-0.0" / "forearm" / "results.json"


def main():
    results = json.loads(RESULTS.read_bytes())
    scores = results["scores"]
    rows = [
        ("Shared model, direct forecast", "zero", "direct_shared_emg"),
        ("Shared model, corrected forecast", "motion", "emg"),
        ("Wrist specialist", "prior_motion_cnn", "prior_emg_corrected_cnn"),
    ]
    controls = [
        ("Aligned with the movement", "emg"),
        ("Held at its average over time", "time_constant"),
        ("Played backwards", "reversed"),
        ("Taken from a different trial", "wrong_trial"),
    ]
    ink = "#183539"
    teal = "#09686a"
    muted = "#566669"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5,
                         "pdf.fonttype": 42, "text.color": ink, "xtick.color": muted,
                         "ytick.color": ink, "axes.labelcolor": ink})
    fig, (left, right) = plt.subplots(2, 1, figsize=(9.0, 7.45))
    fig.subplots_adjust(left=.355, right=.92, top=.79, bottom=.18, hspace=1.06)
    fig.text(.055, .95, "What does the forearm add to a wrist forecast?", size=18, weight="bold")
    fig.text(.055, .908, "Two right-wrist angles, a quarter of a second ahead. Smaller errors are better.", size=11.5)
    for ax, title, labels in [(left, "Movement alone and with forearm electrodes", [r[0] for r in rows]),
                              (right, "Changing the forearm signal in the corrected shared model", [r[0] for r in controls])]:
        ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", pad=13)
        ax.spines[:].set_visible(False)
        ax.set_xlim(3.4, 4.66)
        ax.set_ylim(len(labels)-.55, -.55)
        ax.set_yticks(range(len(labels)), labels)
        ax.tick_params(axis="both", length=0, pad=8)
        ax.xaxis.set_major_locator(MultipleLocator(.25))
        ax.grid(axis="x", color="#dbe3e3", linewidth=.8)
        ax.set_axisbelow(True)
    def score(key):
        return scores[key]["equal_person_rmse_deg"]
    for y, (_, movement, added) in enumerate(rows):
        before, after = score(movement), score(added)
        left.plot([after, before], [y, y], color="#9faeb0", linewidth=2)
        left.scatter([before], [y], s=49, facecolor="white", edgecolor=muted, linewidth=1.6, zorder=3)
        left.scatter([after], [y], marker="D", s=35, color=teal, zorder=4)
        left.annotate(f"{before:.3f}°", (before, y), xytext=(8, -3.5), textcoords="offset points", color=muted)
        left.annotate(f"{after:.3f}°", (after, y), xytext=(-8, -3.5), textcoords="offset points", ha="right", color=teal)
    left.scatter([], [], s=40, facecolor="white", edgecolor=muted, label="Movement alone")
    left.scatter([], [], s=31, marker="D", color=teal, label="With forearm signal")
    left.legend(loc="upper right", bbox_to_anchor=(1, -.21), ncol=2, frameon=False, fontsize=9)
    for y, (_, key) in enumerate(controls):
        value = score(key)
        color = teal if key == "emg" else muted
        right.scatter(value, y, marker="D", s=35, color=color)
        right.annotate(f"{value:.3f}°", (value, y), xytext=(9, -3.5), textcoords="offset points", color=color)
    right.set_xlabel("Two-angle error in degrees (root mean square)", labelpad=10)
    fig.text(.055, .083, f"{results['people']} people • {results['trials']:,} trials • {results['overlapping_windows']:,} overlapping forecasts", fontsize=10.5, weight="bold")
    fig.text(.055, .048, "Each person counted equally. The six people had been studied before. Accuracy on a new person remains unknown.", fontsize=9)
    fig.savefig(HERE / "wrist-correction.png", dpi=155)
    fig.savefig(HERE / "wrist-correction.pdf", metadata={"CreationDate": None, "ModDate": None, "Title": "What does the forearm add to a wrist forecast?"})
    plt.close(fig)


if __name__ == "__main__":
    main()
