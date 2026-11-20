"""Export the pure-browser linear comparison and two invented source-specific fixtures."""
from pathlib import Path
import json
import numpy as np
from forecast import ARM,LEG
HERE=Path(__file__).resolve().parent

def invented(arm):
    names=list(ARM if arm else LEG)
    end=np.arange(-19,1)/32
    rate=500 if arm else 256
    ticks=np.floor(end*rate+1e-9)/rate
    def xyz(t):
        if arm:return np.column_stack((125*t+9*np.sin(5*t),27*t+8*np.sin(9*t),40*t+2*np.sin(8*t)))
        return np.column_stack((8*np.sin(6*t),4*np.sin(8*t),2*np.cos(5*t)-2))
    j=np.arange(len(names))[None,:];k=np.arange(20)[:,None]
    rms=(.04 if arm else 14)*(1+.32*np.cos(.4*k+.45*j)+.2*np.sin(.13*k+.31*j))
    times=np.arange(1,33)/256-.125
    return {"domain":"cross_limb","study":"grasp_lift" if arm else "balance","mode":"pooled",
            "context":"led_grasp_lift" if arm else "walking_ccw","channel_names":names,
            "patch_rms":rms.tolist(),"patch_xyz_mm":xyz(ticks).tolist(),"age_s":(end-ticks).tolist(),
            "repeat_path_mm":(xyz(times)-xyz(np.array([-.125]))).tolist()}

def main():
    examples={k:invented(k=='grasp_lift') for k in ('balance','grasp_lift')}
    for k,v in examples.items():(HERE/(k+'-example.json')).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
    def read(p):return json.loads((HERE/p).read_bytes())
    def small(name):
        out={}
        for k,d in read(name+'.json')['domains'].items():
            out[k]={'people':d['people'],'events':d['events'],'unit':d['unit'],'strict':d['strict_complete']['events'],
                    'errors':{m:[s['emg_mae_native'],s['mean_path_mm'],s['endpoint_mm']] for m,s in d['methods'].items()},
                    'transfer_pass':d['calibrated_pass_amplitude_path']}
        return out
    payload={'examples':examples,'state':read('model.json'),'development':small('development'),'assessment':small('historical')}
    (HERE/'index.html').write_text((HERE/'reader.html.in').read_text().replace('@@PAYLOAD@@',json.dumps(payload,separators=(',',':'),allow_nan=False)))
if __name__=='__main__':main()
