"""Fit and assess the right-plate readout using the original source and the frozen source split."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
import zlib
import ezc3d
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import predict
import right_plate as rp
from right_contact import right_contact_geometry, right_emg_slice

PARENT='7a0c17c66049fba7812d0acf1392af21829c3c6528ace3667202c8091f97f8b4'
METHOD='ae34d05c9d01dd005dc24d85465c682b9992cc79e1edf2cc93f24dadb3ffc82e'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trials(directory,partition):
    pins=json.loads((HERE/'source-checks.json').read_bytes())[partition]
    if sha(directory/'contact-codes.json')!=pins['source_contact_table_sha256']:
        raise ValueError('Contact metadata does not match the selected source edition and partition.')

    codes=json.loads((directory/'contact-codes.json').read_bytes())
    paths=sorted(directory.glob('*.c3d')); rows=[];ex=Counter()
    summary=[[p.name,p.stat().st_size,f'{zlib.crc32(p.read_bytes()):08x}'] for p in paths]
    if hashlib.sha256(json.dumps(summary,separators=(',',':')).encode()).hexdigest()!=pins['roster_and_source_crc_sha256']:
        raise ValueError('The source files or participant partition changed.')
    labels={k:f'{partition}-{i+1:02}' for i,k in enumerate(sorted({p.stem.split('_')[0] for p in paths}))}
    if len(paths)!=len(codes) or set(p.name for p in paths)!=set(codes):raise ValueError('Missing or unexpected C3Ds')
    for p in paths:
        contact=codes[p.name]
        if contact['code'] not in ('12','21'):
            ex['trial_without_two_source_assigned_distinct_plates']+=1;continue
        raw=ezc3d.c3d(str(p),extract_forceplat_data=True)
        par,data=raw['parameters'],raw['data'];plate=contact['right_plate']
        geom=right_contact_geometry(raw,plate)
        if not geom['both_on_plate']:
            ex['right_strike1_marker_pair_not_inside_assigned_plate']+=1;continue
        t0=geom['point_index'];n=data['points'].shape[-1]
        if (par['POINT']['UNITS']['value']!=['mm'] or par['ANALOG']['RATE']['value'][0]!=1500 or
                par['POINT']['RATE']['value'][0]!=100 or data['analogs'].shape[-1]!=15*n):
            raise ValueError('Unexpected source unit/clock')
        labs=par['POINT']['LABELS']['value'];a_labs=par['ANALOG']['LABELS']['value']
        ids=[labs.index(k) for k in ('R_FCC','R_FM2')]
        q=a_labs.index('Fz'+str(plate))
        if par['ANALOG']['UNITS']['value'][q]!='N':raise ValueError('Expected a force channel in N')
        signed=-data['analogs'][0,q]
        calibrated=data['platform'][plate-1]['force'][2]
        if not np.allclose(signed,calibrated,rtol=1e-6,atol=1e-4,equal_nan=True):raise ValueError('Unexpected plate axis/sign')
        if not (np.isfinite(signed)&(signed!=0)).any():
            ex['all_zero_or_missing_plate_channel']+=1;continue
        f=signed.reshape(n,15).mean(axis=1)
        ctr=par['FORCE_PLATFORM']['CORNERS']['value'][:,:,plate-1].mean(axis=1)
        pp=np.transpose(data['points'][:3,ids,:],(2,1,0))
        residual=data['meta_points']['residuals'][0,ids,:].T
        usable=0
        for off_id,off in enumerate(rp.OFFSETS):
            t=t0+off;at=t+np.array([-18,-12,-6,0])
            if t-23<0 or t+10>=n:
                ex['window_outside_record']+=1;continue
            if not (np.isfinite(pp[at]).all() and (residual[at]>=0).all()):
                ex['window_missing_marker']+=1;continue
            if not np.isfinite(f[t+10]):
                ex['nonfinite_target_block']+=1;continue
            xyz=((pp[at]-ctr)/1000).reshape(4,6)
            v,good=right_emg_slice(raw,15*(t-23),15*(t+1))
            v=v.reshape(4,90,8);mask=good.reshape(4,90,8).all(axis=1)
            rms=np.sqrt(np.mean(np.where(mask[:,None,:],v,0)**2,axis=1))*1e6
            rows.append((labels[p.stem.split('_')[0]],p.stem,off_id,xyz,rms,mask.astype(float),f[t+10],f[t]))
            usable+=1
        if not usable:ex['qualified_trial_but_no_complete_window']+=1
    if not rows:raise ValueError('No qualifying right-platform observations.')
    people,rep,off,x,e,v,y,prior=map(np.asarray,zip(*rows))
    return dict(people=people,rep=rep,offset=off.astype(int),markers=x,emg=e,valid=v,y=y,prior=prior,
                counts={'selected_people':len({p.name.split('_')[0] for p in paths}),'selected_trials':len(paths),'people':len(set(people)),
                        'trials':len(set(rep)),'windows':len(y),'offset_windows':[int(sum(off==i)) for i in range(4)],'excluded':dict(ex)})


def weighted(data):
    p=data['people'];trial=data['rep'];out=np.zeros(len(p))
    for who in np.unique(p):
        person=p==who;rs=np.unique(trial[person])
        for r in rs:
            use=person&(trial==r)
            out[use]=1/(len(np.unique(p))*len(rs)*use.sum())
    return out


def scales(x,wt):
    mean=np.average(x,axis=0,weights=wt);sd=np.sqrt(np.average((x-mean)**2,axis=0,weights=wt))
    return mean,np.where(sd<1e-8,1.,sd)


def fit(directory,parent,out):
    if sha(parent)!=PARENT:raise ValueError('Need the verified previous model')
    d=trials(directory,'train');wt=weighted(d);config,w=predict.read_checkpoint(parent)
    with np.load(parent,allow_pickle=False) as source:packed={k:source[k] for k in source.files}
    zmean,zsd=scales(d['markers'].reshape(-1,6),np.repeat(wt/4,4))
    w['right_plate.marker_mean']=zmean;w['right_plate.marker_sd']=zsd
    y=d['y'];center=np.average(y,weights=wt)
    phase=[]
    for i in range(4):
        keep=d['offset']==i
        if not keep.any():phase.append(center);continue
        source={k:d[k][keep] for k in ('people','rep')}
        phase.append(np.average(y[keep],weights=weighted(source)))
    w['right_plate.phase']=np.asarray(phase)
    for mode in rp.MODES[1:]:
        x=rp.design(w,mode,d['offset'],d['markers'],d['emg'],d['valid'],config,predict.linear,predict.encode)
        m,s=scales(x,wt);z=(x-m)/s;zt=z.T*wt
        coef=np.linalg.solve(zt@z+.05*np.eye(z.shape[1]),zt@(y-center))
        for name,v in [('mean',m),('sd',s),('coef',coef),('bias',np.asarray(center))]:
            w['right_plate.'+mode+'.'+name]=v
    packed.update({k:v for k,v in w.items() if k.startswith('right_plate.')})
    config['right_plate_force']={'format':1,'input_bin_ms':60,'bins':4,'elapsed_since_annotated_strike_frames':rp.OFFSETS,
                                 'horizon_frames':10,'unit':'N','measurement':'upward external load on the source-assigned platform'}
    packed['configuration']=np.array(json.dumps(config))
    np.savez_compressed(out,**packed)
    print(json.dumps({'fit':d['counts'],'weights_sha256':sha(out),'method_sha256':METHOD}))


def scores(d,preds,mask):
    people={}
    for p in np.unique(d['people'][mask]):
        trials=np.unique(d['rep'][(d['people']==p)&mask]);person={}
        for k,pred in preds.items():
            person[k]=float(np.mean([np.mean(np.abs(pred[(d['rep']==r)&mask]-d['y'][(d['rep']==r)&mask])) for r in trials]))
        people[str(p)]=person
    return {'people':len(people),'trials':len(np.unique(d['rep'][mask])),'windows':int(mask.sum()),
            'mean_absolute_error_N':{k:float(np.mean([v[k] for v in people.values()])) for k in preds} if people else {},
            'per_person':people}


def contrast(result,other):
    diffs=[v['combined_shared']-v[other] for v in result['per_person'].values()]
    if not diffs:return None
    a=np.asarray(diffs);draw=np.random.default_rng(71864).integers(len(a),size=(10000,len(a)))
    return {'other':other,'shared_combined_minus_other_mean_N':float(a.mean()),'wins':int(np.sum(a<0)),
            'within_1e_minus_10_N':int(np.sum(np.abs(a)<=1e-10)),'wins_beyond_1e_minus_10_N':int(np.sum(a < -1e-10)),
            'people':len(a),'paired_person_bootstrap_95_N':np.quantile(a[draw].mean(axis=1),[.025,.975]).tolist()}


def score(directory,checkpoint,out):
    cfg,w=predict.read_checkpoint(checkpoint)
    d=trials(directory,'assessment');pred={k:rp.batch(w,k,d['offset'],d['markers'],d['emg'],d['valid'],cfg,predict.linear,predict.encode) for k in rp.MODES}
    donors=np.full(len(d['y']),-1)
    for i in range(len(donors)):
        cand=np.flatnonzero((d['people']==d['people'][i]) & (d['rep']!=d['rep'][i]) & (d['offset']==d['offset'][i]))
        if len(cand):
            later=cand[d['rep'][cand]>d['rep'][i]]
            donors[i]=later[0] if len(later) else cand[0]
    ok=donors>=0
    wrong_pred=rp.batch(w,'combined_shared',d['offset'],d['markers'],d['emg'][np.maximum(donors,0)],d['valid'][np.maximum(donors,0)],cfg,predict.linear,predict.encode)
    full=scores(d,pred,np.ones(len(d['y']),bool))
    wrong=scores(d,{**pred,'wrong_repeat':wrong_pred},ok)
    past=scores(d,{**pred,'current_plate':d['prior']},np.isfinite(d['prior']))
    contrasts=[contrast(full,k) for k in ('phase','marker_shared','combined_ridge','scrambled_combined')]
    contrasts.append(contrast(wrong,'wrong_repeat'))
    def lower(c):return c is not None and c['shared_combined_minus_other_mean_N']<0 and c['wins']>c['people']/2
    selected=[contrasts[0],contrasts[1],contrasts[2],contrasts[4]]
    gate=all(lower(c) for c in selected) and contrasts[1]['paired_person_bootstrap_95_N'][1]<0 and contrasts[4]['paired_person_bootstrap_95_N'][1]<0
    summary={'method_sha256':METHOD,'checkpoint_sha256':sha(checkpoint),'test_coverage':d['counts'],'full':full,'paired_wrong_repeat':wrong,
             'privileged_past_force':past,'paired_contrasts_N':contrasts,'incremental_emg_gate':bool(gate),'frozen_representation_gate':lower(contrasts[3])}
    # Public scores require group and person means, never individual source windows.
    out.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'full':full['mean_absolute_error_N'],'people':full['people'],'trials':full['trials'],'windows':full['windows'],'gate':gate}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['fit','score']);parser.add_argument('source_dir',type=Path)
    parser.add_argument('checkpoint',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if sha(HERE/'METHOD.md')!=METHOD or args.checkpoint.resolve()==args.output.resolve():parser.error('Use the frozen study and a separate output')
    (fit if args.action=='fit' else score)(args.source_dir,args.checkpoint,args.output)
