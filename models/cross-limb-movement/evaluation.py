"""Frozen scoring and wrong-trial controls. Read only the explicitly supplied cohort."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from network import load_model,predict_arrays,save_json,fingerprint,INPUT_KEYS
from donors import match
from scoring import aggregate,event_errors,compare
from training import read_data

DOMAINS=('lower','upper')
MODES=('joint','specialist','specialist-total','adapt','foreign-frozen','shuffled','paired-source')
UNITS=('µV','WAY exported amplitude units')


def actual_name(mode,d):
    label=DOMAINS[d]
    return {'joint':'joint','specialist':label,'specialist-total':label+'-total',
            'adapt':'adapt-'+label,'foreign-frozen':DOMAINS[1-d],
            'paired-source':'paired-source-'+label,'shuffled':'shuffled-'+label}[mode]


def basic(data,ids):
    past=data['past_rms'][ids]
    path=data['patch_xyz_mm'][ids]
    age=data['age_s'][ids]
    vel=(path[:,-1]-path[:,-2])/(1/32+age[:,-2,None]-age[:,-1,None])
    clock=np.arange(1,33)/256
    return {'persistence-stationary':(past,np.zeros((len(ids),32,3))),
            'persistence-repeat':(past,data['repeat_path_mm'][ids]),
            'persistence-linear':(past,clock[None,:,None]*vel[:,None,:])}


def summarize_predictions(data,predictions,all_ids,include_donors=False):
    output={}
    priv={}
    for d,label in enumerate(DOMAINS):
        ids=all_ids[data['domain'][all_ids]==d]
        preds={mode:tuple(v[ids] for v in predictions[actual_name(mode,d)]) for mode in MODES}
        preds.update(basic(data,ids))
        by_role={}
        paired={}
        for mode,(r,p) in preds.items():
            errors=event_errors(data,ids,r,p)
            if not np.isfinite(errors[:,:3]).all(): raise ValueError('Invalid native prediction '+mode)
            by_role[mode],paired[mode]=aggregate(data,ids,errors,d)
            priv[f'{label}_{mode}_errors']=errors
        differences={}
        for a,b in [('joint','specialist'),('joint','specialist-total'),('adapt','specialist'),
                    ('adapt','specialist-total'),('adapt','foreign-frozen'),('shuffled','paired-source'),
                    ('joint','persistence-stationary'),('joint','persistence-repeat'),('joint','persistence-linear')]:
            differences[a+' minus '+b]=compare(paired[a],paired[b])
        complete=np.asarray(data['complete'][ids],dtype=bool)
        strict={}
        for mode,(r,p) in preds.items():
            ci=ids[complete]
            strict[mode]=aggregate(data,ci,event_errors(data,ci,r[complete],p[complete]),d)[0]
        output[label]=dict(unit=UNITS[d],frame='ML / SI / AP' if d==0 else 'WAY Polhemus X / Y / Z',
                           methods=by_role,contrasts=differences,strict_complete=strict,
                           strict_complete_input_count=int(complete.sum()),named_usable_input_count=len(ids))
    output['joint_advantage']={}
    for c in ('specialist','specialist-total'):
        test=[output[label]['contrasts']['joint minus '+c]['differences'].get(metric,{}) for label in DOMAINS for metric in ('muscle_mae','path_mean_distance_mm')]
        output['joint_advantage'][c]=all(t and t['mean']<0 and t['upper98_75']<0 for t in test)
    return output,priv


def donor_control(data,all_ids,models):
    out={}
    private={}
    for d,label in enumerate(DOMAINS):
        ids=all_ids[data['domain'][all_ids]==d]
        recipient,donor=match(data,ids)
        mask=data['muscle_mask'][recipient]&data['muscle_mask'][donor]
        n=len(recipient)
        private.update({f'{label}_donor_{k}':v for k,v in dict(recipient=recipient,source=donor,mask=mask).items()})
        reports={}
        for mode in MODES:
            net,sc=models[actual_name(mode,d)]
            runs={}
            rows={}
            for cond in ('intact','wrong','wrong-correct-persistence','intact-all-own','wrong-all-donor'):
                origin=recipient if cond in ('intact','intact-all-own') else donor
                x={k:v[recipient].copy() for k,v in data.items() if k in INPUT_KEYS}
                usemask=data['muscle_mask'][origin] if cond in ('intact-all-own','wrong-all-donor') else mask
                x['muscle_mask']=usemask
                x['patch_rms']=np.where(usemask[:,None,:],data['patch_rms'][origin],0.)
                base=recipient if cond=='wrong-correct-persistence' else origin
                x['past_rms']=np.where(usemask,data['past_rms'][base],0.)
                if n:
                    r,p=predict_arrays(net,x,sc)
                else: r,p=np.empty((0,13)),np.empty((0,32,3))
                e=event_errors(data,recipient,r,p,mask)
                runs[cond],rows[cond]=aggregate(data,recipient,e,d,session_detail=False)
                if mode=='joint':
                    for name,arr in (('rms',r),('path',p),('errors',e)):
                        private[f'{label}_{mode}_{cond}_{name}']=arr
            contrasts={a+' minus '+b:compare(rows[a],rows[b]) for a,b in [('wrong','intact'),('wrong-correct-persistence','intact'),('wrong-all-donor','intact-all-own')]}
            reports[mode]=dict(runs=runs,contrasts=contrasts)
        controls={}
        for mode,(r,p) in basic(data,recipient).items():
            controls[mode]=aggregate(data,recipient,event_errors(data,recipient,r,p,mask),d,session_detail=False)[0]
        out[label]=dict(eligible_recipient_rows=n,input_rows=len(ids),methods=reports,persistence_controls=controls)
    return out,private


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,nargs='+',required=True)
    parser.add_argument('--models',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--private',type=Path,required=True)
    args=parser.parse_args()
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    data=read_data(args.data)
    ids=np.arange(len(data['domain']))
    names=sorted({actual_name(mode,d) for mode in MODES for d in (0,1)})
    models={name:load_model(args.models/f'model-{name}.json') for name in names}
    preds={}
    private={}
    for name,(net,scale) in models.items():
        preds[name]=predict_arrays(net,data,scale)
        private[name+'_rms'],private[name+'_path']=preds[name]
    results,details=summarize_predictions(data,preds,ids)
    controls,donor=donor_control(data,ids,models)
    results['donor_controls']=controls
    results['data_sha256']=[fingerprint(path) for path in args.data]
    results['model_sha256']={name:fingerprint(args.models/f'model-{name}.json') for name in names}
    save_json(args.out,results)
    np.savez_compressed(args.private,**private,**details,**donor)

if __name__=='__main__': main()
