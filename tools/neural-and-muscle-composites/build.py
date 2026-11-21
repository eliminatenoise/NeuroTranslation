"""Generate the study reader from the released, group-level scores."""
import argparse
import json
import subprocess
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SITE = REPO / "docs/neural-and-muscle-composites"
MODELS = REPO / "models/neural-and-muscle-composites"
ARTICLES = [("representation-context-grounding","Choosing a model for the quantity it must predict"),
            ("muscle-signals-and-force","What can tell us how hard a muscle pulls?"),
            ("dataset-gaps","Which recordings could close the gaps?")]

def read(folder, file):
    return json.loads((MODELS / folder / file).read_text())

def table(caption, headings, rows):
    head = "".join(f'<th scope="col">{escape(col)}</th>' for col in headings)
    body = []
    for label, values in rows:
        cells = "".join(f"<td>{escape(str(x))}</td>" for x in values)
        body.append(f'<tr><th scope="row">{escape(label)}</th>{cells}</tr>')
    return f'<div class="table"><table><caption>{caption}</caption><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'

def metrics():
    experiments = [read("reach","results.json"), read("reach","optical-results.json")]
    timings = read("reach","runtime.json")
    systems = [("ar","Autoregressive"), ("diffusion","Diffusion"), ("hybrid","Hybrid"),
               ("ridge","Ridge regression"), ("persistence","Persistence"), ("velocity","Continue velocity"), ("mean","Training mean")]
    rows = []
    for system, label in systems:
        scores = []
        for summary in experiments:
            for task in ("movement","neural"):
                method = summary["tasks"][task]["systems"].get(system)
                scores.append(f'{method["primary"]["all"]["mean"]:.3f}' if method else "—")
        rows.append((label,scores))
    reach = table("Later-day forecasts, lower error is better",
        ["Method", "Handle (cm)", "Counts with handle", "Hand marker (cm)", "Counts with hand"], rows)
    perf = timings["sensors"]["handle"]
    pace = [f'{perf["systems"]["movement-"+key]["mean_batched_16_draw_ms_per_window"]:.3f}' for key in ("ar","diffusion","hybrid")]
    seconds = perf["score"]["command_wall_seconds"]
    time_note = (f'<p class="note">Handle forecasts used 2, 8 and 16 sequential decoder calls for autoregression, diffusion and the hybrid. '
                 f'On a two-thread CPU these took {pace[0]}, {pace[1]} and {pace[2]} ms per window with 16 draws, in batches of up to 32. '
                 f'The times cover model computation. The complete handle scoring process took {seconds:.2f} s including evaluation of both targets and all controls.</p>')
    pairs = read("balance","results.json")
    groups = [("paired","Electrical + movement pairs"),("early","Early mixing"),("crossed","Crossed pairing"),
        ("without_scalp","Paired, omit scalp values"),("without_physics","Paired, omit projections"),
        ("stationary","Repeat EMG, hold position"),("velocity32","Repeat EMG, continue velocity")]
    human = table("Six people on the beam, lower error is better",["Method","Muscle RMS error (µV)","Mean path error (mm)","Final point (mm)"],
        [(label,[f'{pairs["scores"][key]["both"][metric]:.3f}' for metric in pairs["outcomes"]]) for key,label in groups])
    mechanics = read("geometry","results.json")
    geom_rows = []
    for index in ["1","2"]:
        sample = mechanics["comparisons"]["pose_and_cortex"][index]["paired"]
        scores = sample["endpoint_error_mm"]
        geom_rows.append((f'Workspace {index}',[sample["trials"]]+[f'{scores[key]:.3f}' for key in ("persistence","zero_geometry","true_geometry","earlier_geometry")]))
    geo = table("Handle error at 100 ms, in millimetres",["Workspace","Trials","Stationary","No lengths","Correct lengths","Borrowed lengths"],geom_rows)
    return {"ARCH_TABLE":reach, "ARCH_TIME":time_note,"PAIR_TABLE":human,"GEOMETRY_TABLE":geo,
            "REFERENCE_LINKS":"".join(f'<li><a href="{slug}.html">{escape(label)}</a></li>' for slug,label in ARTICLES[:2])}

def build(check):
    template = (HERE/"index.tmpl.html").read_text()
    outputs = {}
    page = template
    for token,value in metrics().items():
        if page.count("{{"+token+"}}")!=1:
            raise ValueError(f"Missing or repeated substitution {token}")
        page = page.replace("{{"+token+"}}",value)
    outputs["index.html"] = page
    style = template[template.index("<style>"):template.index("</style>")+8]
    for slug,title in ARTICLES:
        content = subprocess.check_output(["md2html","--gfm",REPO/"docs"/(slug+".md")],text=True)
        if slug == "dataset-gaps":
            if not (REPO / "docs/dataset-gaps-sources.json").is_file():
                raise FileNotFoundError("Missing recording source inventory")
            outputs["dataset-gaps-sources.json"] = (REPO / "docs/dataset-gaps-sources.json").read_text()
        outputs[slug+".html"] = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)} · NeuroTranslation</title>{style}<main><header><a href="index.html">Neural signals, muscle and movement</a></header>'
            f'<section class="article">{content}</section><footer><a href="index.html">Return to study</a></footer></main></html>\n')
    for name,data in outputs.items():
        target = SITE / name
        if check:
            if not target.is_file() or target.read_text()!=data:
                raise SystemExit(f"Regenerate {name}")
        else:
            target.write_text(data)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    build(parser.parse_args().check)
