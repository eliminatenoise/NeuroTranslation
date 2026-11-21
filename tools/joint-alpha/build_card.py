"""Build the joint alpha guide and model card from its shipped checkpoint and results."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODEL = REPO / "models/neurotranslate-0.0/joint_alpha"
SITE = REPO / "docs/joint-alpha"
SRC = "https://github.com/eliminatenoise/NeuroTranslation/blob/main/models/neurotranslate-0.0/joint_alpha"


def read(name):
    return json.loads((MODEL / name).read_text(encoding="utf-8"))


def fmt(value):
    return "—" if value is None else f"{value:,.4g}"


def table(caption, labels, rows):
    heads = "".join(f'<th scope="col">{escape(s)}</th>' for s in labels)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>" for row in rows)
    return f'<div class="scroll"><table><caption>{escape(caption)}</caption><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>'


def metric_label(task, key):
    known = {"poisson_nll_nats": "Poisson loss (nats/contact)", "log_loss_nats": "Log loss (nats)",
             "mean_knot_distance_mm": "Mean point error (mm)"}
    units = {"human_leg_emg": "µV RMS", "landmark_motion": "body radii", "macaque_cortex_to_motion": "mm",
             "optical_fluorescence": "assay development SD"}
    return known.get(key, "Mean absolute error (" + units.get(task, key) + ")")


def build():
    digest = hashlib.sha256((MODEL / "neurotranslate.npz").read_bytes()).hexdigest()
    specs = read("specifications.json")
    training = read("training-summary.json")
    capacity = read("capacity-results.json")
    runtime = read("product-runtime.json")
    scores = read("results.json")
    desc = read("tasks.json")
    assert scores["checkpoint_sha256"] == runtime["threads"]["1"]["checkpoint_sha256"] == digest
    with np.load(MODEL / "neurotranslate.npz", allow_pickle=False) as arrays:
        schemas = json.loads(str(arrays["schemas"]))
        params = {k: arrays[k].size for k in arrays.files if k.startswith(("adapters.", "trunk.", "outputs."))}
    n = int(sum(params.values()))
    common = int(sum(size for k, size in params.items() if k.startswith("trunk.")))
    assert set(schemas) == set(desc) == set(scores["tasks"])
    assert n == specs["trainable_parameter_count"] and common == specs["shared_trunk_parameters"]
    rows, io, task_sections = [], [], []
    for task, schema in schemas.items():
        ui = desc[task]
        rank = schema["kind"] == "categorical"
        channels = len(schema["channels"])
        input_shape = ("C × " if rank else "") + f'{schema["history_steps"]} × {channels}'
        output_shape = "C probabilities" if rank else str(len(schema["outputs"]))
        adapter = sum(v for k,v in params.items() if k.startswith("adapters."+task+"."))
        head = sum(v for k,v in params.items() if k.startswith("outputs."+task+"."))
        io.append([ui["title"],input_shape,output_shape,f"{adapter:,}",f"{head:,}",
                   f'{training["training_rows"][task]:,}',f'{training["training_groups"][task]:,}'])
        def fields(keys, units):
            return ", ".join(escape(k.replace("_"," ")) + " (" + escape(u) + ")" for k,u in zip(keys, units))
        out = "One probability per eligible candidate, normalized over the local roster." if rank else fields(schema["outputs"],schema["output_units"])
        task_sections.append(f'<details><summary>{escape(ui["title"])}</summary><p>{escape(ui["input"])} {escape(ui["horizon"])}.</p>'
                             f'<p><strong>Input order.</strong> {fields(schema["channels"],schema["input_units"])}</p>'
                             f'<p><strong>Output order.</strong> {out}</p><p>{escape(schema["limits"])}</p></details>')
        for split, detail in scores["tasks"][task].items():
            key = detail["primary_metric"]
            data = detail["mean_scores"]
            rows.append([ui["title"], split.replace("test_", "").replace("test","held").replace("_"," "), detail["groups"],metric_label(task,key),
                        *[fmt(data.get(method,{}).get(key)) for method in ("joint","single_task","source_baseline","half_persistence_half_training_rate","historical_specialist","training_mean_or_uniform")]])
    a = specs["architecture"]
    wins = sum(row["paired_primary_joint_minus"]["single_task"]["mean"] < 0 for groups in scores["tasks"].values() for row in groups.values())
    comparisons = sum(map(len, scores["tasks"].values()))
    summary = (f"The joint fit had lower primary error than its matched single-task fit on {wins} of {comparisons} held comparisons. "
               "The two human outcomes favored single-task fits. The cortical count and fluorescence tasks improved over single-task training, "
               "yet a smoothed rate and repeating the last fluorescence reading respectively gave lower errors.")
    lead = (f'<p>All {len(schemas)} tasks update one temporal-attention encoder during training. Each uses its own input layer and readout. '
            'The paired human and macaque tasks see earlier values of the quantities they predict, alongside other sensors. '
            'Unrelated experiments supply separate training examples.</p>'
            f'<p><a href="model-card.html">See every task, the measured errors, model sizes and runtime</a>. '
            f'The common encoder contains {common:,} of the {n:,} trainable parameters.</p><p>{summary}</p>')
    source = (HERE/"guide.html").read_text(encoding="utf-8")
    guide = source.replace("<!-- TASK_RESULTS -->", lead)
    page = source.split("<body>")[0].replace("<title>NeuroTranslate 0.0 joint alpha</title>", "<title>Model card · NeuroTranslate 0.0 joint alpha</title>")
    page = page.replace("</style>",".scroll{max-width:100%;overflow-x:auto;margin:1rem 0 1.5rem}.scroll th,.scroll td{min-width:4rem;font-variant-numeric:tabular-nums}.scroll td:first-child{min-width:9rem}details{margin:.6rem 0}summary{cursor:pointer;color:#075d52;font-weight:650}code{overflow-wrap:anywhere}caption{margin:.5rem 0}th,td{font-size:.9rem}\n</style>")
    page += ('<body><main><header><p><a href="./">NeuroTranslate 0.0 joint alpha</a></p><h1>What is inside the checkpoint?</h1>'
             f'<p>Every task updates the same {common:,} parameters. Changing a task changes the input layer and readout that fit its instruments and units. '
             'The shared weights still carry what the other tasks taught them.</p></header>')
    page += (f'<section><h2>Size and architecture</h2><p>{n:,} trainable parameters, all {escape(specs["parameter_dtype"])}. '
             f'Width {a["width"]}, {a["heads"]} attention heads, depth {a["depth"]}, and {a["ff_width"]} hidden units per feed-forward layer. '
             'The encoder reads the observed history and a missingness mask with a fixed time encoding. A learned empty-memory position participates in attention.</p>'
             f'<p>The compressed checkpoint occupies {specs["checkpoint_compressed_bytes"]:,} bytes, including schema, metadata and training-set normalizers. '
             f'Trainable parameters alone occupy {specs["trainable_parameter_bytes"]:,} bytes. SHA-256 <code>{digest}</code>.</p></section>')
    page += '<section><h2>Inputs, outputs and data</h2><p>The shapes below describe one history. C is the number of local recorded-unit candidates in that input. Human EMG and sacrum rows come from the same events, and the two macaque targets come from the same reaches. Adding these row or group counts across tasks would count those source windows twice. Groups mean people, trials, videos or recordings according to the task.</p>'
    exposures = sum(training["training_rows"][t] for t in schemas if t not in ("human_sacrum_path","macaque_motion_to_cortex"))
    page += (f'<p>The five input collections supply {exposures:,} distinct source windows when the two pairs of targets sharing a history are counted once. '
             f'Each of {training["steps"]:,} optimizer updates takes {training["batch_per_task"]} draws per task, or {training["training_draws_per_task"]:,} per task over the fit. '
             'Sampling with replacement can revisit a window.</p>')
    page += table("One checkpoint, seven tasks",["Task","Input steps × channels","Outputs","Input parameters","Readout parameters","Training rows","Training groups"],io)
    page += "".join(task_sections)+"</section>"
    chosen = capacity["selected"]
    ladder = [[c["width"],c["heads"],c["depth"],c["ff_width"],f'{c["learning_rate"]:g}',f'{c["parameters"]:,}',f'{c["aggregate"]:.5f}'] for c in capacity["candidates"]]
    page += (f'<section><h2>Which tested size earned its place?</h2><p>The development comparison held out whole source groups. Each candidate saw the same task mixtures and update count. '
             'The score divides each task’s error by its development reference, averages the paired outcomes within each domain, then gives five domains equal weight. Lower is better. '
             f'The selected candidate scored {chosen["aggregate"]:.5f}. The first width comparison used one seed. The refinement compared two seeds on the same inner split, then the selected configuration was refitted on all development data. Wider candidates included 256 and 512 channels.</p>')
    page += table("Development comparison before historical assessment",["Width","Heads","Depth","FF width","Learning rate","Parameters","Score"],ladder)
    refinement = [[c["width"],c["steps"],c["schedule"].replace("_"," "),", ".join(str(r["seed"]) for r in c["seed_scores"]),
                   ", ".join(f'{r["aggregate"]:.5f}' for r in c["seed_scores"]),f'{c["aggregate"]:.5f}'] for c in capacity["refinement_candidates"]]
    page += table("Longer training and a second seed",["Width","Updates","Schedule","Seeds","Seed scores","Mean score"], refinement)+"</section>"
    page += '<section><h2>What happened on the held recordings?</h2><p>Each score gives equal weight to groups within its split. Lower values are better. The matched single-task model used the same architecture and update count. The source reference uses each study’s comparison rule. For macaque counts, a second comparison halves the recent count and adds half the training-set mean. The trained specialist, where available, is a separate historical fit. The last column repeats a training mean or assigns every candidate equal probability. A dash means the comparison was unavailable. Group counts can include several trials from one animal. These recordings had already been studied.</p>'
    page += f"<p>{summary}</p>"
    page += table("Primary error by task and held split",["Task","Split","Groups","Error measure","Joint","Single-task","Source reference","Smoothed rate","Earlier specialist","Mean or uniform"],rows)
    page += f'<p>For uncertainty, missing-target support, paired differences and scores beyond the primary outcome, inspect <a href="{SRC}/results.json">the full results</a>.</p></section>'
    run = runtime["threads"]["1"]
    page += (f'<section><h2>How much memory and time?</h2><p>On a {escape(runtime["cpu"])} running {escape(runtime["os"])}, Python {escape(runtime["python"])} and NumPy {escape(run["numpy"])}, '
             f'the selected {escape(specs["training_device"])} training run took {fmt(specs["fit_seconds"])} s. Its process peaked at {fmt(specs["process_peak_rss_through_fit_kib"]/1024)} MiB, including data and optimizer state. '
             f'The median fresh-process default CLI forecast took {fmt(run["fresh_cli_median_ms"])} ms across five launches. '
             f'The warm product test peaked at {fmt(run["process_peak_RSS_MiB"])} MiB resident memory, including Python and NumPy. The launcher requests one mathematical-library thread.</p>')
    timings=[[desc[t]["title"],fmt(v["median_ms"]),fmt(v["p95_ms"])] for t,v in run["tasks"].items()]
    page += table("One fictional case, fifty cached calls per task",["Task","Median ms","95th percentile ms"],timings)
    page += f'<p>These are CPU measurements after inputs have been prepared. Sensor acquisition and browser rendering add their own time. <a href="{SRC}/specifications.json">Training hardware, resource costs and model timings</a> · <a href="{SRC}/product-runtime.json">Product timings for one and two threads</a>.</p></section></main></body></html>\n'
    return {"index.html":guide,"model-card.html":page}


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    for name,page in build().items():
        path=SITE/name
        if args.check:
            if path.read_text(encoding="utf-8")!=page: raise SystemExit(f"Regenerate {name}")
        else:
            path.write_text(page,encoding="utf-8")
