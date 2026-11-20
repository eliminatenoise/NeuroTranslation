"""Rebuild the offline browser model from the fitted readout and original movement checkpoint."""
import hashlib,json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
def load(name):return json.loads((HERE/name).read_bytes())

def invented():
    # Analytic synthetic inputs. No participant record or human action is embedded.
    t=(np.arange(160)-159)/256
    motion=np.stack((np.column_stack((9*np.sin(6*t),4*np.sin(8*t),3*np.cos(7*t)-3)),
                     np.column_stack((12*np.sin(5*t),5*np.sin(9*t),6*np.cos(5*t)-6))),axis=1)
    u=np.arange(8)[:,None];n=np.arange(13)[None,:];cap=np.arange(128)[None,:]
    nm=2*np.sin(.7*u+.2*n)
    n_rms=np.abs(nm)+5+2*np.cos(.4*u+.25*n)**2
    em=3*np.sin(.75*u+.10*cap)
    e_rms=np.abs(em)+5+np.cos(.25*u+.05*cap)**2
    return dict(domain="visual_balance",mode="shared_full",direction="counterclockwise",motion_mm=motion.tolist(),
        eeg_good=[True]*128,nuisance_good=[True]*13,eeg_mean_uv=em.tolist(),eeg_rms_uv=e_rms.tolist(),
        nuisance_mean_uv=nm.tolist(),nuisance_rms_uv=n_rms.tolist())

def main():
    checkpoint=HERE.parent/'movement-weights.npz';s=load('model.json')
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=s['parent_sha256']:raise ValueError('Parent checksum mismatch.')
    with np.load(checkpoint,allow_pickle=False) as npz:enc={k:npz[k].ravel().tolist() for k in npz if k.startswith(('project.','position','blocks.','last_norm.'))}
    example=invented();(HERE/'example.json').write_text(json.dumps(example,separators=(',',':'),allow_nan=False)+'\n')
    def brief(name):
        j=load(name+'.json')
        q=j['donors']['cycle']
        return {'people':q['people'],'events':q['events'],'methods':{k:v['endpoint_mm'] for k,v in q['methods'].items()},'test':q['scalp_tests']['shared_full']}
    payload={'state':s,'encoder':enc,'example':example,'development':brief('development'),'assessment':brief('historical')}
    html=(HERE/'reader.html.in').read_text().replace('@@DATA@@',json.dumps(payload,separators=(',',':'),allow_nan=False))
    html=html.replace('@@ENCODER@@',(HERE.parent/'back_rotation/encoder.js').read_text())
    (HERE/'index.html').write_text(html)
if __name__=='__main__':main()
