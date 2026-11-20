"""Build the self-contained walking landmark supplement from public group summaries."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

BASE = Path(__file__).resolve().parent
DATA_LICENCE_SHA256 = "953500b054b9312498aca780ffc8af13ef226f7328f4088bfb5a9f237bf29e73"
TEAL, RUST, GREY, PURPLE = "#155b59", "#a74831", "#59686a", "#605682"


def fixed(value):
    return f"{value:.2f}".replace("-", "−")


def interval_plot(series):
    """Draw paired differences on one shared millimetre scale, centred on zero."""
    x_left, width, low, high = 260, 250, -5, 3
    def x(value):
        return x_left + (value - low) * width / (high - low)
    parts = ['<svg class="differences" viewBox="0 0 680 170" role="img" aria-labelledby="contrast-title contrast-desc">',
             '<title id="contrast-title">Difference in mean endpoint error, in millimetres</title>',
             '<desc id="contrast-desc">Dots mark means. Horizontal lines span 95% paired walker intervals. Negative values favour the combined Transformer.</desc>',
             '<text x="0" y="14" class="ax">Comparator</text><text x="675" y="14" text-anchor="end" class="ax">Mean [95% interval], mm</text>']
    for tick in (-4,-2,0,2):
        coord = x(tick)
        parts.append(f'<path d="M{coord:.2f} 24V135" stroke="{GREY if tick == 0 else "#d8e1df"}" stroke-dasharray="{"" if tick == 0 else "2 3"}"/>')
        parts.append(f'<text x="{coord:.2f}" y="155" text-anchor="middle" class="ax">{tick}</text>')
    for i, (label, row) in enumerate(series):
        y = 40 + 28*i
        mean, (lo, hi) = row["mean_mm"], row["ci95_mm"]
        paint = RUST if i == len(series)-1 else TEAL
        parts.extend([f'<text y="{y+4}" x="0">{label}</text>',
            f'<path d="M{x(lo):.2f} {y}H{x(hi):.2f}M{x(lo):.2f} {y-4}v8M{x(hi):.2f} {y-4}v8" stroke="{paint}" stroke-width="2" fill="none"/>',
            f'<circle cx="{x(mean):.2f}" cy="{y}" r="4" fill="{paint}"/>',
            f'<text x="675" y="{y+4}" text-anchor="end">{fixed(mean)} [{fixed(lo)}, {fixed(hi)}]</text>'])
    return "".join(parts) + "</svg>"


def travel_plot(data):
    """Show signed directions and the mean length, retaining unsupported phases as gaps."""
    left, right, top, bottom = 42, 650, 21, 162
    def x(phase):
        return left + phase / 100 * (right - left)
    def y(value):
        return bottom - (value + 100) / 550 * (bottom - top)
    parts = ['<svg class="travel" viewBox="0 0 670 195" role="img" aria-labelledby="ankle-title ankle-desc">',
             '<title id="ankle-title">Observed right ankle movement over 200 milliseconds</title>',
             '<desc id="ankle-desc">Signed forward, left and up components and average straight-line endpoint distance by stride phase. During swing, forward movement and distance both exceed 400 mm. Values stop when fewer than three walkers contribute.</desc>',
             '<text x="4" y="12" class="ax">mm</text>']
    for tick in (-100,0,100,200,300,400):
        coord = y(tick)
        parts.append(f'<path d="M{left} {coord:.2f}H{right}" stroke="{GREY if tick == 0 else "#dde4e2"}"/><text x="{left-7}" y="{coord+4:.2f}" text-anchor="end" class="ax">{tick}</text>')
    parts.append(f'<path d="M{x(50)} {top}V{bottom}" stroke="#73807e" stroke-dasharray="2 3"/>')
    for label, values, color, dash in [
        ("Distance",data["mean_endpoint_distance_mm"],TEAL,""),
        ("Forward",[v[0] if v is not None else None for v in data["delta_mm"]],RUST,"7 3"),
        ("Left",[v[1] if v is not None else None for v in data["delta_mm"]],GREY,"2 2"),
        ("Up",[v[2] if v is not None else None for v in data["delta_mm"]],PURPLE,"9 3 2 3")]:
        points, move = [], True
        for phase, value in zip(data["phases"], values):
            if value is None:
                move = True
            else:
                points.append(f'{"M" if move else "L"}{x(phase):.2f},{y(value):.2f}')
                move = False
        parts.append(f'<path d="{" ".join(points)}" stroke="{color}" stroke-dasharray="{dash}" fill="none" stroke-width="2.5"><title>{label}</title></path>')
    for tick in (0,25,50,75,100):
        parts.append(f'<text x="{x(tick)}" y="181" text-anchor="middle" class="ax">{tick}%</text>')
    return "".join(parts) + "</svg>"


def render_html(licence):
    data = json.loads((BASE/"numbers.json").read_text())
    template = (BASE/"paper.html.in").read_text()
    six = data["six_points"]
    rows = []
    for key, label in [("ridge_markers","Marker positions · linear ridge"),("ridge_combined","Markers and EMG · linear ridge"),
                       ("transformer_markers","Marker positions · Transformer"),("transformer_combined","Markers and EMG · Transformer"),
                       ("velocity","Continue recent marker velocity"),("phase","Mean for gait event and elapsed time"),("persistence","Hold each marker still")]:
        stat = six["means"][key]
        rows.append(f'<tr><th scope="row">{label}</th><td>{fixed(stat["mean_mm"])}</td><td>{fixed(stat["ci95_mm"][0])}–{fixed(stat["ci95_mm"][1])}</td></tr>')
    template = template.replace("{{SIX_ROWS}}", "".join(rows))
    contrasts = [("Marker-only Transformer",six["paired"]["transformer_markers"]),("Prior-repeat EMG",six["paired"]["wrong_emg"]),
                 ("Marker-only ridge",six["paired"]["ridge_markers"]),("Aligned personal template",data["direction_followup"]["paired"])]
    template = template.replace("{{CONTRAST_CHART}}",interval_plot(contrasts))
    rows = []
    for key, label in [("stationary","Hold the marker still"),("velocity","Continue recent velocity"),("previous","Repeat the last 200 ms"),
                       ("linear","Linear ridge"),("radial","Radial basis ridge"),("shared","Trained encoder + ridge"),("shuffled","Shuffled encoder + ridge")]:
        vals = [data["one_point"][group]["means_mm"][key] for group in ("other_46","fit_6")]
        rows.append(f'<tr><th scope="row">{label}</th><td>{fixed(vals[0])}</td><td>{fixed(vals[1])}</td></tr>')
    template = template.replace("{{POINT_ROWS}}", "".join(rows))
    template = template.replace("{{TRAVEL_CHART}}", travel_plot(data["observed_travel"]))
    template = template.replace("{{LICENCE}}", base64.b64encode(licence).decode("ascii"))
    if "{{" in template:
        raise ValueError("Unresolved template field")
    (BASE/"index.html").write_text(template,encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-only",action="store_true")
    parser.add_argument("--browser",help="Path to a Chrome or Chromium executable")
    args = parser.parse_args()
    licence = (BASE/"DATA-LICENCE.txt").read_bytes()
    if hashlib.sha256(licence).hexdigest() != DATA_LICENCE_SHA256:
        raise ValueError("The authors’ original version 8 LICENCE must be present.")
    render_html(licence)
    if args.html_only:
        return
    from pypdf import PdfReader, PdfWriter
    browser = args.browser or shutil.which("chromium") or shutil.which("google-chrome")
    if not browser:
        parser.error("Supply a Chrome or Chromium executable with --browser.")
    with tempfile.TemporaryDirectory() as name:
        temp = Path(name)
        raw = temp / "print.pdf"
        subprocess.run([browser,"--headless","--disable-gpu","--disable-background-networking","--no-first-run","--no-default-browser-check",
                        "--no-pdf-header-footer",f"--user-data-dir={temp / 'profile'}",f"--print-to-pdf={raw}",(BASE/"index.html").as_uri()],
                       check=True,capture_output=True,timeout=90)
        reader = PdfReader(raw)
        if len(reader.pages) != 4:
            raise ValueError(f"Expected four pages, found {len(reader.pages)}")
        writer = PdfWriter(clone_from=reader)
        writer.metadata = {"/Title":"Where will the wrist be in a fifth of a second?", "/Subject":"Two walking landmark forecasts and a measured stride reference"}
        writer.add_attachment("DATA-LICENCE.txt",licence)
        writer.write(BASE/"walking-landmarks.pdf")


if __name__ == "__main__":
    main()
