"""Fit the shared-encoder and first-order load-response study; apply frozen readouts."""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from predict import linear,encode,read_checkpoint
from forecast import METHODS,READOUT,FRACTION,summaries,features,batch
PARENT='6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864'
TRAIN=(1,2);TEST=(3,4)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')


def windows(clock,emg,load):
    if clock.ndim!=1 or load.shape!=clock.shape or emg.shape!=clock.shape:
        raise ValueError('Raw vectors must share source sample rows')
    cut=np.arange(200,len(load)-100,100)
    all_rows=cut[:,None]+np.arange(-200,101)
    time=clock[all_rows]
    clock_ok=np.all(np.isfinite(time),axis=1)&np.all(np.abs(np.diff(time,axis=1)-.001)<=1e-8,axis=1)
    history=all_rows[:,:201];l=load[history];e=emg[history];future=load[cut+100]
    finite=np.isfinite(l).all(axis=1)&np.isfinite(e).all(axis=1)&np.isfinite(future)
    keep=clock_ok&finite
    return (l[keep],e[keep],(future-load[cut])[keep],cut[keep]),{'samples':len(clock),'candidates':len(cut),'eligible':int(keep.sum()),'bad_clock_windows':int((~clock_ok).sum()),'nonfinite_windows':int((~finite).sum())}


def collect(cache,people,manifest):
    reference=json.loads(Path(manifest).read_bytes())
    if reference['accession']!='S-BIAD1482' or reference['dataset_doi']!='10.6019/S-BIAD1482':
        raise ValueError('Wrong dataset release')
    expected={(row['person'],row['condition'],row['trial']):row for row in reference['records']}
    records=[];sources={};coverage=[]
    for p in people:
        for pos,name in enumerate(('angle0','angle5')):
            for trial in (1,2):
                stem=cache/f'A{p:02d}'/f'{name}-trial-{trial}'
                f=stem.with_suffix('.npz');receipt=json.loads(stem.with_suffix('.source.json').read_bytes());digest=sha(f)
                original=expected[(f'A{p:02d}',name,trial)]
                for field in ('member','sha256','rows','time_origin','array_f64le_sha256'):
                    if receipt.get(field)!=original.get(field):
                        raise ValueError('Raw source or array identity differs from published manifest')
                origin=receipt.get('time_origin')
                fields=receipt.get('source_fields',{})
                if (receipt.get('person')!=f'A{p:02d}' or receipt.get('condition')!=name or receipt.get('trial')!=trial
                    or fields.get('emg')!='emg_1' or fields.get('load')!='loadcell_right'
                    or origin not in ('stored_regular_vector','sample_index_at_published_1000_hz')):
                    raise ValueError('Original recording or channel identity differs: '+str(stem))
                with np.load(f,allow_pickle=False) as z:
                    args=[np.asarray(z[k],dtype=float) for k in ('time_s','emg','load')]
                for key,values in zip(('time_s','emg','load'),args):
                    array_sha=hashlib.sha256(np.ascontiguousarray(values,dtype='<f8').tobytes()).hexdigest()
                    if array_sha!=receipt['array_f64le_sha256'][key] or values.shape!=(receipt['rows'],):
                        raise ValueError('Original data fingerprint or row count differs: '+str(stem))
                (hist,emg,y,cut),info=windows(*args)
                if not len(cut):raise ValueError('No source-qualified windows: '+str(stem))
                groups=np.column_stack([np.full(len(y),p),np.full(len(y),pos),np.full(len(y),trial),cut]).astype(int)
                coverage.append(dict(person=p,setting=name,trial=trial,time_origin=origin,**info));sources[str(f.relative_to(cache))]=digest
                records.append((hist,emg,y,groups))
    return tuple(np.concatenate(col) for col in zip(*records)),coverage,sources


def weights(g):
    w=np.zeros(len(g));people=np.unique(g[:,0])
    for p in people:
        for c in (0,1):
            for t in (1,2):
                use=(g[:,0]==p)&(g[:,1]==c)&(g[:,2]==t)
                if not use.any():raise ValueError('Missing participant / setting / trial group')
                w[use]=1/(len(people)*4*np.count_nonzero(use))
    return w


def other_trial(g):
    out=np.full(len(g),-1,int)
    for p in np.unique(g[:,0]):
        for c in (0,1):
            for t in (1,2):
                rows=np.flatnonzero((g[:,0]==p)&(g[:,1]==c)&(g[:,2]==t))
                other=np.flatnonzero((g[:,0]==p)&(g[:,1]==c)&(g[:,2]==3-t))
                if not len(rows) or not len(other):raise ValueError('Wrong-trial history unavailable')
                if np.any(np.diff(g[rows,3])<=0):raise ValueError('Cutoffs out of order')
                out[rows]=other[np.arange(len(rows))*len(other)//len(rows)]
    assert np.all(out>=0) and np.all(g[:,2]!=g[out,2]) and np.array_equal(g[:,:2],g[out,:2])
    return out


def center_scale(a,w):
    m=np.average(a,axis=0,weights=w);sd=np.sqrt(np.average((a-m)**2,axis=0,weights=w))
    return m,np.where(sd<1e-8,1.,sd)


def median(a,w):
    order=np.argsort(a,kind='stable');return float(a[order[np.searchsorted(np.cumsum(w[order]),w.sum()/2)]])


def fit(data,w,rand,cfg):
    load,emg,y,g=data;wt=weights(g);setting=g[:,1];t,d=summaries(load,emg)
    recent=load[:,-1]-load[:,-101];m,s=center_scale(t.reshape(-1,6),np.repeat(wt/4,4))
    state={'format':1,'parent_sha256':PARENT,'medians':{name:median(y[setting==c],wt[setting==c]) for c,name in enumerate(('angle0','angle5'))},'fits':{}}
    for mode in READOUT:
        f={'token_mean':m.tolist(),'token_sd':s.tolist()}
        v=features(mode,t,d,recent,setting,f,rand if mode=='random_both' else w,cfg,linear,encode)
        target=(load[:,-1]+y/FRACTION) if mode.startswith('relaxation') else (y-recent)
        n,sd=center_scale(v,wt);z=(v-n)/sd
        intercept=float(wt@target);coef=np.linalg.solve(z.T@(wt[:,None]*z)+.05*np.eye(z.shape[1]),z.T@(wt*(target-intercept)))
        f.update(mean=n.tolist(),sd=sd.tolist(),intercept=intercept,coef=coef.tolist());state['fits'][mode]=f
    return state


def predictions(data,state,w,rand,cfg):
    load,emg,y,g=data
    tok,dyn=summaries(load,emg)
    scores={m:batch(m,load,g[:,1],tok,dyn,state,w,rand,cfg,linear,encode) for m in METHODS}
    tok,dyn=summaries(load,emg[other_trial(g)])
    scores['wrong_both']=batch('shared_both',load,g[:,1],tok,dyn,state,w,rand,cfg,linear,encode)
    return scores


def by_person(data,pred):
    load,emg,y,g=data;rows=[]
    for p in np.unique(g[:,0]):
        use=g[:,0]==p;yy=y[use];wt=weights(g[use]);cells={}
        for name,c in [('balanced',None),('angle0',0),('angle5',1)]:
            mask=np.ones(len(yy),dtype=bool) if c is None else g[use,1]==c
            weights_here=wt[mask]/wt[mask].sum()
            cells[name]={}
            for model,vec in pred.items():
                error=vec[use][mask]-yy[mask]
                cells[name][model]={'mae':float(weights_here@np.abs(error)),'rmse':float(np.sqrt(weights_here@(error**2))),'bias':float(weights_here@error)}
        rows.append({'windows':int(use.sum()),'conditions':cells})
    return rows


def aggregate(rows,stage):
    cells={c:{m:{k:float(np.mean([r['conditions'][c][m][k] for r in rows])) for k in ('mae','rmse','bias')} for m in rows[0]['conditions'][c]} for c in ('balanced','angle0','angle5')}
    for c in cells:
        for m in cells[c]:
            cells[c][m]['rmse']=float(np.sqrt(np.mean([r['conditions'][c][m]['rmse']**2 for r in rows])))
    comps=('shared_load','wrong_both','linear_both','random_both','linear_load','relaxation_emg','recent','hold')
    ordered=sorted(rows,key=lambda r:tuple(r['conditions']['balanced'][m]['mae']-r['conditions']['balanced']['shared_both']['mae'] for m in comps))
    gains={m:[r['conditions']['balanced'][m]['mae']-r['conditions']['balanced']['shared_both']['mae'] for r in ordered] for m in comps}
    n=sum(a>0 and b>0 for a,b in zip(gains['shared_load'],gains['wrong_both']))
    avg=cells['balanced']
    passed=None if len(rows)!=2 else bool(n==2 and all(avg['shared_both']['mae']<=.95*avg[m]['mae'] for m in ('shared_load','wrong_both')))
    return {'stage':stage,'people':len(rows),'windows':sum(r['windows'] for r in rows),'units':'original right load-channel output','horizon_samples':100,'scores':cells,'paired_gain':gains,'joint_improvement':n,'paired_emg_criterion':passed,'paired_order':'anonymous order by matched-model gain, identical for every comparison'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['fit','assess']);p.add_argument('cache',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--model',type=Path,default=HERE/'model.json');p.add_argument('--parent',type=Path,default=HERE.parent/'movement-weights.npz');p.add_argument('--private-folds',type=Path);p.add_argument('--source-manifest',type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if sha(a.parent)!=PARENT:raise ValueError('Use the original shared checkpoint')
    cfg,w=read_checkpoint(a.parent)
    rand={k:np.asarray(v,float) for k,v in json.loads((HERE.parent/'back_rotation/random-encoder.json').read_bytes()).items()}
    manifest=a.source_manifest or HERE/('development-manifest.json' if a.phase=='fit' else 'assessment-manifest.json')
    data,info,source=collect(a.cache,TRAIN if a.phase=='fit' else TEST,manifest)
    if a.phase=='fit':
        rows=[]
        for person in TRAIN:
            mask=data[-1][:,0]==person;tr=tuple(x[~mask] for x in data);te=tuple(x[mask] for x in data)
            state=fit(tr,w,rand,cfg)
            if a.private_folds:
                a.private_folds.mkdir(exist_ok=True,parents=True);put(a.private_folds/f'held-A{person:02d}.json',state)
            rows.extend(by_person(te,predictions(te,state,w,rand,cfg)))
        state=fit(data,w,rand,cfg);put(a.out/'model.json',state)
    else:
        state=json.loads(a.model.read_bytes());rows=by_person(data,predictions(data,state,w,rand,cfg))
    result=aggregate(rows,a.phase);put(a.out/(a.phase+'-summary.json'),result);put(a.out/(a.phase+'-source.json'),{'coverage':info,'npz_sha256':source})
    print(a.phase,result['windows'],result['scores']['balanced']['shared_both'],result['paired_emg_criterion'])
if __name__=='__main__':main()
