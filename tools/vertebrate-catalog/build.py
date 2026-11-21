"""Build the static corpus index from the public register and scored studies."""
import argparse
import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ROOT / "models" / "vertebrate-neural-data"
OUTPUT = ROOT / "docs" / "vertebrate-neural-data" / "index.html"

# The badges refer to the specific product in each register entry.
# Some source deposits provide more than one kind of signal.
SIGNALS = {
    "salamander-timed-retina": "Spike times",
    "salamander-binned-movies": "Binned spikes",
    "xenopus-tectal-current-steps": "Cell voltage or current",
    "cane-toad-mesh": "Extracellular voltage",
    "slider-turtle-dorsal-cortex": "Spike times and field potentials",
    "zebra-finch-song": "Threshold crossings",
    "pigeon-visual-entopallium": "Visual response summaries",
    "knifefish-electrosensory": "Electrophysiology",
    "zebrafish-forebrain-heat": "Fluorescence imaging",
    "rat-w-track": "Spike times and field potentials",
    "mouse-visual-neuropixels": "Spike times and field potentials",
    "macaque-area2-reach": "Spike times",
    "human-ajile12": "Cortical surface voltage",
    "human-medial-temporal-units": "Spike times",
    "human-scalp-motor": "Scalp voltage",
}
GROUPS = [
    ("Actinopterygii", "Ray-finned fishes", "fish"),
    ("Lissamphibia", "Amphibians", "amphibians"),
    ("Testudines", "Turtles", "turtles"),
    ("Aves", "Birds", "birds"),
    ("Mammalia", "Mammals", "mammals"),
]
GH = "https://github.com/eliminatenoise/NeuroTranslation"
MODEL = GH + "/tree/main/models/vertebrate-neural-data"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def entry(row):
    source = row["source"]
    label = escape(row["species"])
    signal = escape(SIGNALS[row["id"]])
    check = escape(row["evidence"]["level"].rstrip("."))
    links = [f'<a href="{escape(source["landing"])}">Data deposit</a>']
    # Some entries use the deposit itself as the study reference.
    same_deposit = (row["primary_study"] == source["landing"] or
                    row["primary_study"] == f'https://doi.org/{source.get("doi", "")}')
    if not same_deposit:
        links.append(f'<a href="{escape(row["primary_study"])}">Original study</a>')
    if "next_spike_evaluation" in row:
        links.append(f'<a href="{escape(row["next_spike_evaluation"])}">Spike forecast results</a>')
    return f'''<article class="entry" id="{escape(row['id'])}">
      <h4>{label}</h4>
      <p class="signal">{signal}</p>
      <p>{escape(row['recording_site'])} {escape(row['measurement'])}</p>
      <p class="checked">Source check · {check}.</p>
      {' · '.join(links)}
      <details><summary>Recording conditions and reuse</summary>
      <p>{escape(row['experiment_and_clock'])}</p>
      <p>{escape(row['unit_identity'])} {escape(row['independence'])}</p>
      <p>{escape(source['access'])}</p>
      <p>{escape(source['citation'])} · <a href="{escape(source['license_url'])}">{escape(source['license'])}</a></p></details>
    </article>'''


def render():
    catalog = read(MODELS / "datasets.json")
    rows = catalog["datasets"]
    if len({row["id"] for row in rows}) != len(rows) or set(SIGNALS) != {r["id"] for r in rows}:
        raise ValueError("Review the signal labels against the current register.")
    grouped = defaultdict(list)
    for row in rows:
        components = row["lineage"].split(" / ")
        matches = [name for token, name, slug in GROUPS if token in components]
        if len(matches) != 1:
            raise ValueError(f"Review lineage for {row['id']}")
        grouped[matches[0]].append(row)
    groups, jumps = [], []
    for token, name, slug in GROUPS:
        collection = grouped[name]
        n = len(collection)
        jumps.append(f'<a href="#{slug}">{name} ({n})</a>')
        count = f"{n} deposit" if n == 1 else f"{n} deposits"
        groups.append(f'<section id="{slug}" aria-labelledby="{slug}-title"><h3 id="{slug}-title">{name} <small>{count}</small></h3>' +
                      "".join(entry(row) for row in collection) + "</section>")
    tally = Counter(SIGNALS[row["id"]] for row in rows)
    signal_counts = "".join(f"<li>{escape(label)} <b>{n}</b></li>"
                            for label, n in sorted(tally.items(), key=lambda item: (-item[1], item[0])))
    turtle = read(MODELS / "turtle" / "results.json")["results"]["methods"]
    salamander = read(MODELS / "amphibian" / "results.json")
    salamander_means = salamander["equal_experiment_of_equal_repeat_means"]
    rat = read(ROOT / "models/next-neuron-prediction/er1-results.json")
    return Template((HERE / "index.tmpl.html").read_text(encoding="utf-8")).substitute(
        model=MODEL, github=GH, count=len(rows), edition=escape(catalog["edition"]),
        groups="\n".join(groups), jumps="\n".join(jumps), signals=signal_counts,
        rat_units=rat["candidate_units"],
        turtle_n=f"{turtle['shared_model']['pooled']['rows']:,}",
        turtle_model=f"{turtle['shared_model']['pooled']['log_loss']:.3f}",
        turtle_count=f"{turtle['online_rate']['pooled']['log_loss']:.3f}",
        salamander_n=f"{sum(e['methods']['shared_model']['pooled']['rows'] for e in salamander['experiments'].values()):,}",
        sal_model=f"{salamander_means['shared_model']['log_loss']:.3f}",
        sal_recency=f"{salamander_means['recency']['log_loss']:.3f}",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the published HTML against its inputs")
    args = parser.parse_args()
    page = render()
    source = (MODELS / "datasets.json").read_bytes()
    download = OUTPUT.with_name("datasets.json")
    if args.check:
        if not download.exists() or download.read_bytes() != source:
            raise SystemExit("The downloadable register differs from the source.")
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != page:
            raise SystemExit("The vertebrate corpus index needs rebuilding.")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(page, encoding="utf-8")
        download.write_bytes(source)
