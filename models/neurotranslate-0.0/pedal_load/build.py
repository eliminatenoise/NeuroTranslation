"""Build a single offline page for the load response and shared-encoder forecasts."""
from pathlib import Path
import hashlib,json,re
import numpy as np
HERE=Path(__file__).resolve().parent
LABELS={'hold':'No load change','recent':'Repeat the recent load change','setting_median':'Typical change for the setting',
        'relaxation_setting':'Response model · setting','relaxation_emg':'Response model · setting and EMG',
        'linear_load':'Linear model · load and setting','linear_both':'Linear model · load, setting and EMG',
        'shared_load_no_setting':'Shared encoder · load only','shared_load':'Shared encoder · load and setting',
        'shared_both':'Shared encoder · load, setting and EMG','random_both':'Untrained encoder · fitted output','wrong_both':'Shared encoder · other trial’s EMG'}
def read(p):return json.loads(p.read_bytes())
if __name__=='__main__':
    model=read(HERE/'model.json');dev=read(HERE/'fit-summary.json');test=read(HERE/'assess-summary.json')
    parent=HERE.parent/'movement-weights.npz';prior=HERE.parent/'back_rotation'
    assert hashlib.sha256(parent.read_bytes()).hexdigest()==model['parent_sha256']
    with np.load(parent,allow_pickle=False) as w:shared={k:w[k].ravel().tolist() for k in w if k.startswith(('project.','position','blocks.','last_norm.'))}
    random={k:np.asarray(v).ravel().tolist() for k,v in read(prior/'random-encoder.json').items()}
    scope=(f"The two fitting participants supplied {dev['windows']} forecasts. Each development fold left one person out. The planned two-person assessment remains incomplete. "
           "In one neutral-pedal recording the right-load field has two columns, and its analysis clock could not be verified. "
           "The other seven recordings support three separate descriptions. One person supplied two trials at each setting. The other supplied both angle5 trials and a single neutral trial with no matching other-trial control. "
           "The latter person's qualified 1 kHz arrays are the author's exact every-tenth-row selections from the raw 10 kHz records.")
    finding="The registered two-person test for the added muscle signal remains unanswered. Each table selection describes one person’s available trials."
    payload=json.dumps(dict(model=model,dev=dev,test=test,shared=shared,random=random,labels=LABELS,scope=scope,finding=finding),ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('<','\\u003c')
    style=re.search(r'<style>(.*?)</style>',(prior/'reader.html.in').read_text(),re.S)[1]
    text=(HERE/'reader.html.in').read_text().replace('@@STYLE@@',style).replace('@@ENCODER@@',(prior/'encoder.js').read_text()).replace('@@DATA@@',payload)
    (HERE/'index.html').write_text(text)
