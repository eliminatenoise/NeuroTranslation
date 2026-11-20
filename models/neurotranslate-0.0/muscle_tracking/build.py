"""Build the portable HTML using the existing shared movement encoder and new readouts."""
from pathlib import Path
import hashlib,json,re
import numpy as np

HERE=Path(__file__).resolve().parent
LABEL={'hold':'Hold the last length','recent':'Repeat the recent length change','typical':'Typical change in training',
       'geometry':'Keep transverse span fixed','linear_length':'Linear model · length','shared_length':'Shared encoder · length',
       'linear_both':'Linear model · length and angle','shared_both':'Shared encoder · length and angle',
       'random_both':'Untrained encoder · fitted output','wrong_both':'Same shared model · wrong-trial angle'}
def read(p):return json.loads(p.read_bytes())
if __name__=='__main__':
    model=read(HERE/'model.json');parent=HERE.parent/'movement-weights.npz';prev=HERE.parent/'back_rotation'
    assert hashlib.sha256(parent.read_bytes()).hexdigest()==model['parent_sha256']
    with np.load(parent,allow_pickle=False) as w:
        shared={k:w[k].ravel().tolist() for k in w if k.startswith(('project.','position','blocks.','last_norm.'))}
    random={k:np.asarray(a).ravel().tolist() for k,a in read(prev/'random-encoder.json').items()}
    dev=read(HERE/'fit-summary.json');held=read(HERE/'assess-summary.json')
    scope=f"Four people provided the fitting recordings. Development errors are from one person at a time with that person left out of the fit. The separate evaluation covers {held['windows']:,} forecasts in {held['people']} people after the models were fixed."
    outcome=held['paired_angle_criterion']
    finding=('The paired-angle advantage met its prespecified test.' if outcome is True else 'The paired-angle advantage fell short of its prespecified test.' if outcome is False else 'The planned four-person test remains incomplete.')
    data={'model':model,'dev':dev,'held':held,'shared':shared,'random':random,'labels':LABEL,'example':read(HERE/'example.json'),'scope':scope,'finding':finding}
    css=re.search(r'<style>(.*?)</style>',(prev/'reader.html.in').read_text(),re.S)[1]
    template=(HERE/'reader.html.in').read_text().replace('@@STYLE@@',css).replace('@@ENCODER@@',(prev/'encoder.js').read_text())
    (HERE/'index.html').write_text(template.replace('@@DATA@@',json.dumps(data,separators=(',',':'),ensure_ascii=False,allow_nan=False).replace('<','\\u003c')))
