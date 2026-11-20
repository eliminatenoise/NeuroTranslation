"""Reproduce the separately qualified evaluation groups, without inventing a missing donor."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from forecast import METHODS,batch,summaries
from study import windows,read_checkpoint,linear,encode
HERE=Path(__file__).resolve().parent
GROUPS=(
    ('complete','One participant, both settings, both repetitions','A04',('angle0','angle5'),(1,2)),
    ('other_angle5','Other participant, angle5, both repetitions','A03',('angle5',),(1,2)),
    ('other_angle0','Other participant, angle0, second repetition only','A03',('angle0',),(2,)),
)


def window_file(cache,row,decimated):
    person=row['person']; setting=row['condition'];trial=row['trial']
    stem=cache/person/f'{setting}-trial-{trial}'
    note=json.loads(stem.with_suffix('.source.json').read_bytes())
    for field in ('person','condition','trial','member','sha256','rows','array_f64le_sha256'):
        if note[field]!=row[field]:raise ValueError('Source identity changed: '+field)
    fields={'time_s':'time_new','emg':'emg_1_new','load':'loadcell_right_new'} if decimated else {'time_s':'time','emg':'emg_1','load':'loadcell_right'}
    if note['source_fields']!=fields:raise ValueError('Unexpected voltage or time source')
    with np.load(stem.with_suffix('.npz'),allow_pickle=False) as f:
        arrays=[]
        for key in ('time_s','emg','load'):
            a=np.ascontiguousarray(f[key],dtype='<f8')
            if a.shape!=(row['rows'],) or hashlib.sha256(a.tobytes()).hexdigest()!=row['array_f64le_sha256'][key]:
                raise ValueError('Source channel failed hash or sample check')
            arrays.append(a)
    return windows(*arrays)[0]


def describe(cache,model,weights,manifest):
    state=json.loads(model.read_bytes())
    if hashlib.sha256(weights.read_bytes()).hexdigest()!=state['parent_sha256']:raise ValueError('Wrong shared movement checkpoint')
    cfg,w=read_checkpoint(weights)
    random={k:np.asarray(v,dtype=float) for k,v in json.loads((HERE.parent/'back_rotation/random-encoder.json').read_bytes()).items()}
    roster=json.loads(manifest.read_bytes())
    if roster['accession']!='S-BIAD1482' or roster['dataset_doi']!='10.6019/S-BIAD1482':raise ValueError('Invalid dataset')
    bad=roster['unsupported_records']
    if [(r['person'],r['condition'],r['trial']) for r in bad]!=[('A03','angle0',1)]:raise ValueError('Unsupported-source list changed')
    records={}
    for group,selected in [('records',False),('author_grid_records',True)]:
        for r in roster[group]:
            key=(r['person'],r['condition'],r['trial'])
            if key in records:raise ValueError('Duplicate source recording')
            records[key]=window_file(cache,r,selected)
    expected={(p,s,t) for _,_,p,settings,trials in GROUPS for s in settings for t in trials}
    if set(records)!=expected:raise ValueError('Incomplete source support for these descriptions')
    groups={}
    for label,text,person,settings,trials in GROUPS:
        by_trial={};counts={}
        for s in settings:
            counts[s]=0
            for t in trials:
                l,e,y,cut=records[person,s,t];counts[s]+=len(y)
                pos=np.full(len(l),int(s=='angle5'));tok,dyn=summaries(l,e)
                preds={m:batch(m,l,pos,tok,dyn,state,w,random,cfg,linear,encode) for m in METHODS}
                if (person,s,3-t) in records:
                    donor=records[person,s,3-t][1]
                    swap=donor[np.arange(len(e))*len(donor)//len(e)]
                    st,sd=summaries(l,swap);preds['wrong_both']=batch('shared_both',l,pos,st,sd,state,w,random,cfg,linear,encode)
                errors={m:pr-y for m,pr in preds.items()}
                by_trial[s,t]={m:{'mae':float(np.abs(er).mean()),'mse':float((er**2).mean()),'bias':float(er.mean())} for m,er in errors.items()}
        summary={}
        for scope in ('balanced',*settings):
            values=[v for (s,t),v in by_trial.items() if scope=='balanced' or s==scope]
            summary[scope]={m:{'mae':float(np.mean([v[m]['mae'] for v in values])),
                                 'rmse':float(np.sqrt(np.mean([v[m]['mse'] for v in values]))),
                                 'bias':float(np.mean([v[m]['bias'] for v in values]))} for m in values[0]}
        groups[label]={'description':text,'people':1,'trials':len(by_trial),'windows':sum(counts.values()),'windows_by_setting':counts,'has_wrong_trial':len(trials)==2,'scores':summary}
    return {'assessment_status':'incomplete','original_planned_people':2,'full_roster_gates':None,'qualified_trials':len(records),
            'qualified_windows':sum(g['windows'] for g in groups.values()),'wrong_comparable_windows':sum(g['windows'] for g in groups.values() if g['has_wrong_trial']),
            'horizon':'100 source-grid sample positions; 1 kHz nominal','unit':'right load channel, native units','groups':groups}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('cache',type=Path);p.add_argument('out',type=Path);p.add_argument('--model',type=Path,default=HERE/'model.json')
    p.add_argument('--parent',type=Path,default=HERE.parent/'movement-weights.npz');p.add_argument('--manifest',type=Path,default=HERE/'assessment-manifest.json')
    args=p.parse_args();result=describe(args.cache,args.model,args.parent,args.manifest);args.out.mkdir(exist_ok=True,parents=True)
    (args.out/'assess-summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
