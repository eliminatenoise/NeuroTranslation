"""Build a self-contained interactive comparison of posture-specific fitted readouts."""
from pathlib import Path
import json
import numpy as np

HERE=Path(__file__).resolve().parent

def synthetic():
    t=(np.arange(160)-159)/256
    position=np.column_stack([7*np.sin(7*t),5*np.sin(5*t+.4)-5*np.sin(.4),3*np.sin(9*t)])
    j=np.arange(8)[None,:]
    amp=8+2*np.cos(4*t[:,None]+j*.5)
    volts=amp*np.sin(2*np.pi*(29+2*j)*t[:,None]+.34*j)
    return {"domain":"muscle_motion","mode":"pooled","posture":"standing","direction":"counterclockwise",
            "sacrum_mm":position.tolist(),"leg_uv":volts.tolist()}

def main():
    example=synthetic();(HERE/'example.json').write_text(json.dumps(example,separators=(',',':'))+'\n')
    def read(p):return json.loads((HERE/p).read_bytes())
    state=read('model.json')
    selected=("pooled","walk_only","stand_only","stand_limited","adapted_walk")
    state["fits"]={m:state["fits"][m] for m in selected}
    def selection(name):
        q=read(name+'.json')
        return {"summary":q["primary"],"standing":q["postures"]["standing"],
                "walking":q["postures"]["walking"]}
    blob={"state":state,"example":example,"development":selection("development"),"historical":selection("historical")}
    text=(HERE/'reader.html.in').read_text().replace('@@DATA@@',json.dumps(blob,separators=(',',':'),allow_nan=False))
    (HERE/'index.html').write_text(text)
if __name__=="__main__":main()
