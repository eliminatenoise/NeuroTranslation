"""Build a self-contained browser model using its sibling movement checkpoint."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
LABELS={"zero":"No rotation","recent":"Repeat the last rotation","task_median":"Typical rotation for the instruction",
        "linear_motion":"Straight-line model · motion","shared_motion":"Shared encoder · motion",
        "shared_upper":"Shared encoder · motion and upper back","shared_lower":"Shared encoder · motion and lower back",
        "linear_full":"Straight-line model · all readings","shared_full":"Shared encoder · all readings",
        "random_full":"Untrained encoder · fitted output","wrong_full":"Shared encoder · wrong-trial electrodes"}


def read(name):return json.loads((HERE/name).read_bytes())
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=HERE/'index.html');args=p.parse_args()
    model=read('model.json')
    weights=HERE.parent/'movement-weights.npz'
    if hashlib.sha256(weights.read_bytes()).hexdigest()!=model['parent_sha256']:
        raise ValueError('Mismatched movement checkpoint.')
    with np.load(weights,allow_pickle=False) as archive:
        shared={k:archive[k].ravel().tolist() for k in archive if k.startswith(('project.','position','blocks.','last_norm.'))}
    random={k:np.asarray(v).ravel().tolist() for k,v in read('random-encoder.json').items()}
    if {k:len(v) for k,v in shared.items()}!={k:len(v) for k,v in random.items()}:raise ValueError('Incompatible comparison encoder.')
    held=read('assess-summary.json');s=held['balanced']
    finding=(f"Across {held['windows']:,} windows from three people with verified orientation measurements, mean error was {s['shared_motion']['mae_deg']:.3f}° "
             f"using motion alone, {s['shared_full']['mae_deg']:.3f}° with both electrode regions, and {s['wrong_full']['mae_deg']:.3f}° with the other trial’s voltage. "
             "The planned four-person test remains incomplete.")
    data=dict(model=model,shared=shared,random=random,dev=read('fit-summary.json'),test=held,example=read('example.json'),labels=LABELS,finding=finding)
    raw=json.dumps(data,separators=(',',':'),ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    template=(HERE/'reader.html.in').read_text();assert template.count('@@ENCODER@@')==template.count('@@DATA@@')==1
    args.output.write_text(template.replace('@@ENCODER@@',(HERE/'encoder.js').read_text()).replace('@@DATA@@',raw))
if __name__=='__main__':main()
