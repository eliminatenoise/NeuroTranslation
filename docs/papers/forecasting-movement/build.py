"""Build the self-contained HTML note and, optionally, print it with Chromium."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def svg(name):
    raw = (HERE/name).read_text()
    return raw[raw.index('<svg'):]


def row(label, numbers, digits):
    return '<tr><th scope="row">'+label+'</th>'+''.join(f'<td>{v:.{digits}f}</td>' for v in numbers)+'</tr>'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium',help='Chromium executable to use for PDF export')
    args=parser.parse_args()
    evidence=json.loads((HERE/'evidence.json').read_bytes())
    scores=evidence['stride']['overall']
    stride_rows=''.join(row(label,[scores[key]['bodyMeanMm'],scores[key]['pelvisMeanMm']],2) for key,label in [
        ('conditional','Movement and word'),('history-only','Movement alone'),('retrieval','Recorded stride match'),('ridge','Linear model')])
    rats=evidence['track']['rat']
    rat_rows=''.join(row(r['rat'],[r[k] for k in ('constant_speed','motion','combined','earlier_trip')],3) for r in rats)
    overall=evidence['track']['equal_rat']
    rat_rows+=row('Equal-rat mean',[overall[k] for k in ('constant_speed','motion','combined','earlier_trip')],3)
    values={'stride':svg('stride-curves.svg'),'rat':svg('rat-comparisons.svg'),'stride_rows':stride_rows,'rat_rows':rat_rows,
            'tag_gain':f"{scores['history-only']['bodyMeanMm']-scores['conditional']['bodyMeanMm']:.2f}",
            'run_error':f"{next(g['tagged'] for g in evidence['stride']['groups'] if g['group']=='127'):.2f}"}
    page=(HERE/'note.html.in').read_text()
    for key,val in values.items():page=page.replace('{{'+key+'}}',val)
    if '{{' in page:raise ValueError('Unresolved template marker')
    target=HERE/'index.html';target.write_text(page)
    if args.chromium:
        with tempfile.TemporaryDirectory() as profile:
            subprocess.run([args.chromium,'--headless','--no-sandbox','--disable-gpu','--no-pdf-header-footer','--user-data-dir='+profile,
                            '--print-to-pdf='+str(HERE/'movement-forecast.pdf'),target.as_uri()],check=True)

if __name__=='__main__':main()
