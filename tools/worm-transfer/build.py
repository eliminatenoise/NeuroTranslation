"""Render the worm-to-zebrafish study from its sealed, aggregate outputs."""
import argparse
import hashlib
import json
import math
from html import escape
from pathlib import Path
from string import Template


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODEL = ROOT / "models/vertebrate-neural-data/worm-transfer"
OUTPUT = ROOT / "docs/worm-to-vertebrate/index.html"
SOURCE = "https://github.com/eliminatenoise/NeuroTranslation/tree/main/models/vertebrate-neural-data/worm-transfer"
ARMS = {
    "fish": "Fish only · same regions and early period",
    "worm": "Fish and eight worms",
    "fish_new_roi": "Fish only · other regions",
    "fish_late_time": "Fish only · later period",
    "persistence": "Carry the last observation forward",
}


def read(name):
    return json.loads((MODEL / name).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value(n):
    if not math.isfinite(n):
        raise ValueError("Missing or non-finite aggregate")
    return f"{n:.5f}"


def signed(n):
    return f"{n:+.5f}".replace("-", "−")


def row(label, cells):
    return "<tr><th scope=\"row\">" + escape(label) + "</th>" + "".join(
        f"<td>{escape(cell)}</td>" for cell in cells
    ) + "</tr>"


def render():
    split = read("split.json")
    protocol = read("protocol.json")
    fit = read("fit.json")
    results = read("results.json")
    if results["fit_sha256"] != digest(MODEL / "fit.json"):
        raise ValueError("Score file and fitted coefficients disagree")
    if not all(digest(MODEL / name) == mark for name, mark in fit["frozen_sources"].items()):
        raise ValueError("Study inputs differ from those used for fitting")
    held = results["held_animals"]
    roster = split["held_fish"]
    if set(roster) != set(held) or roster != protocol["evaluation_vertebrates"]:
        raise ValueError("The reported and scored fish differ")
    if len(roster) != 7 or len(split["train_worms"]) != 8:
        raise ValueError("The report describes seven held fish and eight worms")
    if any(a["rows"] != 1024 for a in fit["arms"].values()) or fit["shared_core"]["rows"] != 768:
        raise ValueError("The reported training budget differs from the fit")
    independent = read("independent-check.json")
    summary = results["equal_animal_scores"]
    mse = summary["all"]["mse"]
    delta = results["primary"]["worm_minus_fish_mse"]
    diff = [held[name]["worm_minus_fish_mse"] for name in roster]
    n = len(roster)
    wins = sum(d < 0 for d in diff)
    losses = sum(d > 0 for d in diff)
    relative = results["primary"]["relative_change_percent_vs_fish"]
    if not math.isclose(sum(diff) / n, delta, abs_tol=1e-12) or wins != results["primary"]["animals_improved"]:
        raise ValueError("Per-animal differences disagree with the primary result")
    if delta == 0:
        outcome = "The two training sets gave the same average squared error."
    else:
        direction = "reduced" if delta < 0 else "increased"
        outcome = f"Replacing a quarter of the fish examples with worm recordings {direction} average squared error by {abs(relative):.2f}%."
    controls = [("fish_new_roi", "other regions of the training fish"),
                ("fish_late_time", "a later period in the training fish")]
    controls_text = []
    for key, description in controls:
        comp = "lower than" if mse[key] < mse["worm"] else "higher than" if mse[key] > mse["worm"] else "the same as"
        controls_text.append(f"The fit using {description} had {value(mse[key])} squared error, {comp} the mixed fit.")
    score_table = []
    for arm, label in ARMS.items():
        beats = sum(held[f]["scores"]["all"]["mse"][arm] < held[f]["scores"]["all"]["mse"]["persistence"] for f in roster)
        victories = "—" if arm == "persistence" else f"{beats} / {n}"
        score_table.append(row(label, [value(mse[arm]), value(summary["all"]["mae"][arm]), victories]))
    animal_table = []
    for animal, d in zip(roster, diff):
        all_scores = held[animal]["scores"]["all"]
        animal_table.append(row(animal, [str(all_scores["rois"]), f"{all_scores['cases']:,}",
                                          value(all_scores["mse"]["fish"]), value(all_scores["mse"]["worm"]), signed(d)]))
    sensitivity = results["primary"]["omit_one_animal_mean_differences"].values()
    recordings = [held[f]["recording"] for f in roster]
    min_horizon = min(r["observed_offsets_s"][-1]["minimum"] for r in recordings)
    max_horizon = max(r["observed_offsets_s"][-1]["maximum"] for r in recordings)
    low, high = independent["primary_difference_descriptive_t95"]
    first_target = min(r["first_forecast_target_s"] for r in recordings)
    region_count = sum(r["eligible_rois"] for r in recordings)
    crop_count = sum(r["raw_roi_count_in_crop"] for r in recordings)
    bands = []
    for key, label in (("early", "30 to <60 seconds"), ("middle", "60 to <120 seconds"),
                       ("late", "120 to <180 seconds"), ("low_prior_change", "Smaller preceding change"),
                       ("high_prior_change", "Larger preceding change")):
        group = summary[key]
        if group["animals"]:
            cells = [str(group["animals"]), f"{group['cases']:,}", value(group["mse"]["fish"]), value(group["mse"]["worm"])]
        else:
            cells = ["0", "0", "—", "—"]
        bands.append(row(label, cells))
    time_direction = []
    for band in ("early", "middle", "late"):
        a = summary[band]["mse"]
        time_direction.append("lower" if a["worm"] < a["fish"] else "higher" if a["worm"] > a["fish"] else "equal")
    time_result = (f"In the first scored period (30 to 60 seconds), the mixed fit had {time_direction[0]} error than the fish-only fit. "
                   f"Its error was {time_direction[1]} from 60 to 120 seconds and {time_direction[2]} for the rest of the recording.")
    persistence_wins = sum(r["scores"]["all"]["mse"]["worm"] < r["scores"]["all"]["mse"]["persistence"] for r in held.values())
    ties = n - wins - losses
    return Template((HERE / "index.tmpl.html").read_text(encoding="utf-8")).substitute(
        source=SOURCE, blob=SOURCE.replace("/tree/", "/blob/"), outcome=outcome, delta=signed(delta), wins=wins, losses=losses, ties_text=f" The models tied in {ties}." if ties else "",
        time_result=time_result, persistence_wins=persistence_wins,
        fish=value(mse["fish"]), worm=value(mse["worm"]), controls=" ".join(controls_text),
        cases=f"{summary['all']['cases']:,}", region_count=region_count, crop_count=crop_count,
        horizon=(f"{min_horizon:.3f}" if abs(max_horizon-min_horizon)<1e-7 else f"{min_horizon:.3f}–{max_horizon:.3f}"),
        first_target=f"{first_target:.3f}", lower=signed(low), upper=signed(high),
        high_fish=value(summary["high_prior_change"]["mae"]["fish"]), high_worm=value(summary["high_prior_change"]["mae"]["worm"]), loo=f"{signed(min(sensitivity))} to {signed(max(sensitivity))}",
        score_rows="\n".join(score_table), animal_rows="\n".join(animal_table), band_rows="\n".join(bands),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    check = parser.parse_args().check
    output = render()
    if check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != output:
            raise SystemExit("Study page differs from the model results or page template.")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(output, encoding="utf-8")
