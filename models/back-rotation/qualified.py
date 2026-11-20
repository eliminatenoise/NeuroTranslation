"""Reproduce descriptive scores only for the three held people with documented quaternion channels."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.io import loadmat

EXPECTED=[f"Quaternion ({i})[A.U]" for i in range(1,5)]
CONFLICT=EXPECTED[1:]+["BufferChannel[A.U.]"]


def inspect_labels(cache):
    audit={}
    for n in (10,12,13,14):
        for trial in (2,3):
            path=cache/f"S{n:02d}"/f"trial-{trial:02d}.mat"
            receipt=json.loads(path.with_suffix('.source.json').read_bytes())
            if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['member_sha256']:
                raise ValueError('Source digest changed')
            doc=loadmat(path,variable_names=['data_estructure'],simplify_cells=True)['data_estructure']
            labels=[str(x).strip() for x in doc['quaternions']['labels']]
            if labels!=(CONFLICT if n==10 else EXPECTED):
                raise ValueError('Source mapping differs from this fixed qualification report')
            audit[str(path.relative_to(cache))]=labels
    return audit


def execute(cache,specialist,shared,weights,model_path,out):
    sys.path.insert(0,str(specialist))
    from assess import verify
    from extract import read_trial
    from score import predictions as specialist_predictions, person_scores as specialist_person
    seal=verify(specialist);model=json.loads((specialist/'model.json').read_bytes())
    labels=inspect_labels(cache)
    rows=[]
    for n in (12,13,14):
        trials=[read_trial(cache/f'S{n:02d}'/f'trial-{t:02d}.mat') for t in (2,3)]
        rows.append(specialist_person(trials,[specialist_predictions(model,t) for t in trials]))
    spec={'stage':'Descriptive subset of three new people with verified orientation labels','n_people':3,'n_trials':6,
          'n':{k:sum(r['n'][k] for r in rows) for k in ('611','621')},
          'model_sha256':seal['sha256']['model.json'],
          'mae_deg':{m:{k:float(np.mean([r['mae_deg'][m][k] for r in rows])) for k in ('611','621','balanced')} for m in rows[0]['mae_deg']},
          'incremental_gate_passes':None,'regional_gates':None}
    # The shared folder is the actual CPU package so its original encoder and checkpoint can be loaded.
    sys.path.insert(0,str(shared));sys.path.insert(0,str(shared.parent))
    from study import load, predictions as shared_predictions, person_scores as shared_person,summary
    from predict import read_checkpoint
    from project import for_release
    m=json.loads(model_path.read_bytes())
    if hashlib.sha256(weights.read_bytes()).hexdigest()!=m['parent_sha256']:raise ValueError('Wrong shared parent checkpoint')
    m['random_encoder']=json.loads((shared/'random-encoder.json').read_bytes());cfg,w=read_checkpoint(weights)
    cohort,quality,_=load(cache,(12,13,14))
    raw=summary(shared_person(cohort,shared_predictions(cohort,m,cfg,w)))
    assert raw['practical_criterion'] is None
    # Publish counts and descriptive means. The preregistered four-person decision is unavailable.
    public=for_release(raw)
    for section in public['contrasts'].values():section.pop('sign_p',None)
    reason=('Both recordings from one prespecified person list quaternion components 2, 3 and 4 followed by BufferChannel. '
            'The first component could not be verified. The four-person assessment is incomplete for both models. '
            'Scores below describe three other people with four documented orientation components. No replacement or refit.')
    for d in [spec,public]:d.update(planned_people=4,assessment_status='incomplete',physical_target_qualification=reason)
    out.mkdir(exist_ok=True,parents=True)
    for path,data in [('specialist.json',spec),('shared.json',public),('label-eligibility.json',{'labels':labels,'qualified_people':3,'planned_people':4,'reason':reason})]:
        (out/path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    return spec,public

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('cache','specialist','shared','weights','model','out'):p.add_argument(k,type=Path)
    a=p.parse_args();sp,co=execute(a.cache,a.specialist,a.shared,a.weights,a.model,a.out)
    print(sp['mae_deg']['full'],co['balanced']['shared_full'])
