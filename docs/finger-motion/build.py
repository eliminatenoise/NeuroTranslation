# SPDX-License-Identifier: CC0-1.0
"""Build a self-contained browser companion from the published movement decoder."""
import argparse
import base64
import hashlib
import html
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE / 'src'
sys.path.insert(0, str(SRC))
from invented_rhythm import AMPLITUDES, ELAPSED_MS, waveform

FAMILIES = ('ridge','transformer')
MODES = ('cue','cortex','aligned')
PRIVACY = ('User agrees that, where applicable, content will not be used to identify or to '
           'otherwise infringe the privacy or confidentiality rights of individuals. Content '
           'distributed via the Stanford Digital Repository may be subject to additional license '
           'and use restrictions applied by the depositor.')

def binary(a):
    if a.dtype.str not in ('<f4','<f8'):
        raise ValueError(f'Expected little-endian floating-point parameters, got {a.dtype}')
    return dict(width=a.dtype.itemsize, bytes=base64.b64encode(a.tobytes(order='C')).decode('ascii'))

def number(value):
    return f'{value:.4f}'.replace('-', '−')

def gain(contrast):
    lo,hi = contrast['macro_interval']
    return f'{number(contrast["macro_normalized_gain"])} <span class="ci">[{number(lo)}, {number(hi)}]</span>'

def evidence(result):
    score = result['scores']
    strongest = min(score, key=lambda k: score[k]['macro_normalized_mae'])
    gates = result['gated_within_cue_advantage']
    if strongest != 'ridge_cue' or any(gates.values()):
        raise ValueError('The recorded conclusion changed; review the page against this new model.')
    scores = []
    for mode,label in (('cue','Cue only'),('cortex','Cortex only'),('aligned','Cue + cortex'),('earlier','Earlier cortex + cue')):
        row = '<tr><th scope="row">'+label+'</th>'
        for family in FAMILIES:
            key = family+'_'+mode
            css = ' class="best"' if key==strongest else ''
            row += f'<td{css}>{number(score[key]["macro_normalized_mae"])}</td>'
        scores.append(row+'</tr>')
    def table(key,labels):
        rows=[]
        for suffix,label in labels:
            row = '<tr><th scope="row">'+label+'</th>'
            for family in FAMILIES:
                baseline = suffix if suffix=='zero_difference' else family+'_'+suffix
                found, = [c for c in result[key] if c['candidate']==family+'_aligned' and c['baseline']==baseline]
                row += '<td>'+gain(found)+'</td>'
            rows.append(row+'</tr>')
        return ''.join(rows)
    cross, = [c for c in result['primary_contrasts'] if (c['baseline'],c['candidate'])==('ridge_aligned','transformer_aligned')]
    cross_interval = ' to '.join(map(number,cross['macro_interval']))
    supp=result['conditional_support']; evaluation=result['evaluation']; train=result['train']
    if supp['pairs_by_cue']['little']!=0:
        raise ValueError('Check revised support by finger in the text')
    return dict(
        SCORES=''.join(scores),
        COMPARATORS=f"A ridge model with past glove readings alone scored {number(score['ridge_history']['macro_normalized_mae'])}. The training mean scored {number(score['training_mean']['macro_normalized_mae'])}. Only the glove-history comparison received past glove readings as inputs.",
        CONDITIONAL=f"Twenty trials formed {supp['pairs']} disjoint pairs of repeats across four cued fingers. Predicting zero difference between repeats beat the cue-plus-cortex guess for both families. Neither family passed the predeclared test for extra information about movement within a cue. There was no little-finger pair.",
        PRIMARY=table('primary_contrasts', [('cue','Cue only'),('earlier','Earlier cortex + cue'),('cortex','Cortex only')]),
        PAIRS=table('conditional_contrasts',[('zero_difference','Zero difference'),('cue','Cue only'),('earlier','Earlier cortex + cue')]),
        CROSS=f"With cue and cortex together, the Transformer reduced error by {number(cross['macro_normalized_gain'])} relative to ridge (paired 95% interval {cross_interval}). Cue-only ridge still had the lowest overall error.",
        SUPPORT=(f"All fits used {train['trials']} earlier trials. Evaluation used {evaluation['trials']} later trials from the same recording, "
                 f"with {evaluation['cutoffs_per_trial']} cutoffs per trial split equally between the cue and the following blank. "
                 "The first eligible trial of each cue in each split supplied an earlier signal. It contributed no scored target. "
                 "The repeat test formed disjoint pairs in chronological order within each cue and discarded unpaired trials. "
                 "Pairs by cue were "+', '.join(f"{finger} {count}" for finger,count in supp['pairs_by_cue'].items())+".")
    )

def build(folder):
    folder=folder.resolve()
    for name,digest in json.loads((SRC/'inputs.sha256.json').read_text()).items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Published decoder input changed: {name}')
    for name in ('CC0-1.0.txt','CC-BY-SA-4.0.txt'):
        if (HERE/'licenses'/name).read_bytes()!=(folder/'licenses'/name).read_bytes():
            raise ValueError(f'Licence differs from the published study: {name}')
    spec=importlib.util.spec_from_file_location('finger_features',folder/'features.py')
    features=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(features)
    # Precompute spectral summaries exclusively from the published mathematical wave generator.
    # Quantization at 10 decimals is below the tested inference tolerance across FFT versions.
    powers = [features.packet(waveform(a),1,0,ELAPSED_MS)[:,60:].round(10).tolist() for a in AMPLITUDES]
    models={}
    for family in FAMILIES:
        for mode in MODES:
            key=family+'_'+mode
            with np.load(folder/'weights'/(key+'.npz'),allow_pickle=False) as w:
                models[key]={name:binary(w[name]) for name in w.files}
    data=json.dumps(dict(models=models,powers=powers,age=ELAPSED_MS),separators=(',',':'),allow_nan=False)
    ethics = 'Ethics statement: '+(folder/'RIGHTS.md').read_text().split('\nEthics statement: ',1)[1].strip()
    if ethics not in (HERE/'RIGHTS.md').read_text():
        raise ValueError('Viewer source statement differs from the original')
    replacements=dict(STYLE=(SRC/'style.css').read_text(), DATA=data.replace('<',r'\u003c'),
                      SCRIPT='\n'.join((SRC/n).read_text() for n in ('network.js','view.js')),
                      ETHICS=html.escape(ethics), PRIVACY=html.escape(PRIVACY),
                      LEGAL=html.escape('\n\n'.join((HERE/'licenses'/n).read_text() for n in ('CC-BY-SA-4.0.txt','CC0-1.0.txt'))),
                      **evidence(json.loads((folder/'results.json').read_text())))
    page=(SRC/'page.html').read_text()
    for key,value in replacements.items():
        marker='__'+key+'__'
        if page.count(marker)!=1:
            raise ValueError('Expected one template slot for '+key)
        page=page.replace(marker,value)
    return page

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,default=HERE.parent.parent/'models/finger-motion')
    parser.add_argument('--out',type=Path,default=HERE/'index.html')
    args=parser.parse_args()
    args.out.write_text(build(args.model),encoding='utf-8')
