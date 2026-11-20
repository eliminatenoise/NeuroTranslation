"""Rebuild the illustrated HTML and its linked four-page PDF from local sources."""

import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

BASE = Path(__file__).resolve().parent


def phase_chart(ref, names, limit, ticks, digits=0):
    """Plot published means at 101 phases; gaps split paths and stay visible."""
    shades = ['#174f55', '#79513c', '#5b4475']
    styles = ['', 'stroke-dasharray="5 3"', 'stroke-dasharray="2 3"']
    lo, hi, top, bottom = 40, 626, 8, 65
    def tx(phase):
        return lo + (hi - lo) * phase / 100
    def ty(v):
        return bottom - (bottom - top) * v / limit
    out = ['<svg class="plot" viewBox="0 0 646 83" role="img">']
    out += ['<title>' + html.escape(', '.join(ref['figure_series'][n]['label'] for n in names)) + ' by stride phase</title>']
    for t in ticks:
        y = ty(t)
        out.append(f'<path d="M{lo} {y}H{hi}" stroke="#e1e4df"/><text x="{lo-7}" y="{y+4}" text-anchor="end">{t:.{digits}f}</text>')
    for phase, lab in [(0,'0'),(25,'25'),(50,'50'),(75,'75'),(100,'100%')]:
        x = tx(phase)
        out.append(f'<text x="{x}" y="81" text-anchor="middle">{lab}</text>')
    x_off = tx(ref['summary']['right_foot_off_pct']['mean'])
    out.append(f'<path d="M{x_off:.2f} {top}V{bottom}" stroke="#555" stroke-dasharray="2 3"/>')
    for i, name in enumerate(names):
        path = []
        start = True
        for phase, value in zip(ref['phase_percent'], ref['figure_series'][name]['mean']):
            if value is None:
                start = True
                continue
            path.append(f'{"M" if start else "L"}{tx(phase):.2f},{ty(value):.2f}')
            start = False
        out.append(f'<path d="{" ".join(path)}" fill="none" stroke="{shades[i]}" {styles[i]} stroke-width="2.5" stroke-linejoin="round"/>')
    return ''.join(out) + '</svg>'


def compile_html(licence):
    numbers = json.loads((BASE / 'numbers.json').read_text(encoding='utf-8'))
    ref = numbers['stride_reference']
    page = (BASE / 'paper.html.in').read_text(encoding='utf-8')
    for label, ids, lim, ticks, dec in [
            ('HEEL_CHART', ['R_FCC'], 0.20, [0, 0.10, 0.20], 2),
            ('EMG_CHART', ['R_tibialis_anterior'], 120, [0,60,120], 0),
            ('FORCE_CHART', ['plate1_up','plate2_up','right_contact_up'], 700, [0,350,700], 0)]:
        page = page.replace('{{' + label + '}}', phase_chart(ref, ids, lim, ticks, dec))
    rows = [
        ('Earlier two-plate load, carried forward','current-plate-persistence'),
        ('Marker Transformer','transformer-markers'),
        ('Marker + EMG Transformer','transformer-combined'),
        ('Nonlinear marker ridge','marker-kernel'),
        ('Marker + EMG linear ridge','ridge-combined'),
        ('Marker linear ridge','ridge-markers'),
        ('EMG Transformer','transformer-emg'),
        ('EMG linear ridge','ridge-emg'),
        ('Training mean','training-mean'),
        ('Always zero','constant-zero')]
    scores = numbers['two_plate_forecast']['metrics']
    table = []
    for name, key in rows:
        score = scores[key]
        vals = ''.join(f'<td>{score[k]:.2f}</td>' for k in ('MAE_N','RMSE_N'))
        table.append(f'<tr><th scope="row">{name}</th>{vals}</tr>')
    page = page.replace('{{PRIMARY_TABLE}}', '\n'.join(table))
    right = numbers['right_plate_forecast']['privileged_past_force']['mean_absolute_error_N']
    order = [('Earlier right-plate load, carried forward','current_plate'),
             ('Markers + EMG, simple ridge','combined_ridge'),
             ('Markers + EMG, frozen shared encoder and ridge','combined_shared'),
             ('Markers + EMG, scrambled encoder and ridge','scrambled_combined'),
             ('Average for the elapsed time after strike','phase'),
             ('Markers, simple ridge','marker_ridge'),
             ('Markers, frozen shared encoder and ridge','marker_shared')]
    table = [f'<tr><th scope="row">{label}</th><td>{right[key]:.2f}</td></tr>' for label, key in order]
    page = page.replace('{{RIGHT_TABLE}}', '\n'.join(table))
    page = page.replace('{{DATA_LICENCE_BASE64}}', base64.b64encode(licence).decode('ascii'))
    if '{{' in page:
        raise ValueError('An unresolved field remains in the HTML template')
    (BASE / 'index.html').write_text(page, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html-only', action='store_true')
    parser.add_argument('--browser', help='Path to Chrome or Chromium')
    args = parser.parse_args()
    licence = (BASE/'DATA-LICENCE.txt').read_bytes()
    if hashlib.sha256(licence).hexdigest() != '953500b054b9312498aca780ffc8af13ef226f7328f4088bfb5a9f237bf29e73':
        raise ValueError('DATA-LICENCE.txt must contain the original LICENCE member of the authors’ version 8 archive.')
    compile_html(licence)
    if args.html_only:
        return
    from pypdf import PdfReader, PdfWriter
    browser = args.browser or shutil.which('chromium') or shutil.which('google-chrome')
    if not browser:
        parser.error('Supply a Chrome or Chromium executable with --browser.')
    with tempfile.TemporaryDirectory() as temp:
        profile = Path(temp)
        raw = profile/'print.pdf'
        subprocess.run([browser,'--headless','--disable-gpu','--disable-background-networking',
                        '--no-first-run','--no-default-browser-check','--no-pdf-header-footer',
                        f'--user-data-dir={profile/"profile"}', f'--print-to-pdf={raw}',
                        (BASE/'index.html').as_uri()],check=True,capture_output=True,timeout=90)
        reader = PdfReader(raw)
        if len(reader.pages) != 4:
            raise ValueError(f'Expected four pages, got {len(reader.pages)}')
        writer = PdfWriter(clone_from=reader)
        writer.metadata = {'/Title':'One stride, two force plates', '/Subject':'Measuring and forecasting overground walking loads'}
        writer.add_attachment('DATA-LICENCE.txt', licence)
        writer.write(BASE/'muscle-and-floor.pdf')


if __name__ == '__main__':
    main()
