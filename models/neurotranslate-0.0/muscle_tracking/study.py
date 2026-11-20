"""Fit or score the fixed shared movement model and 2D geometry comparisons."""
from pathlib import Path
import argparse,hashlib,json,math,sys
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent));from predict import linear,encode,read_checkpoint
from forecast import LEARNED,MODES,tokens,design,batch
PARENT="6a05e06ecbf0eadb4524369d9089847813763d0d2a3c1a49bdd1e4bf295e4864"
TRAIN=(1,2,3,4);ASSESS=(5,6,7,8)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(fp,d):fp.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')


def intervals(length,angle,row,clock,segment):
    n=len(length)
    if n==0 or any(v.shape!=(n,) for v in (length,angle,row,clock,segment)):
        raise ValueError('Native tracking columns do not agree')
    if np.any(np.diff(row)<=0):raise ValueError('Invalid native row order')
    i=np.arange(20,n-10,10,dtype=int)
    frames=i[:,None]+np.arange(-20,11)
    contiguous=np.all(np.diff(row[frames],axis=1)==1,axis=1)&np.all(segment[frames]==segment[frames][:,:1],axis=1)
    time_ok=np.all(np.isfinite(clock[frames]),axis=1)&np.all(np.diff(clock[frames],axis=1)>0,axis=1)
    past=frames[:,:21];l=length[past];a=angle[past];end=length[i+10]
    measurements=np.isfinite(l).all(axis=1)&(l>0).all(axis=1)&np.isfinite(a).all(axis=1)&np.isfinite(end)&(end>0)
    keep=contiguous&time_ok&measurements
    return (l[keep],a[keep],(end-l[:,-1])[keep],i[keep]),dict(rows=n,candidate=len(i),eligible=int(keep.sum()),
        noncontiguous_or_bad_clock=int((~(contiguous&time_ok)).sum()),bad_values=int((~measurements).sum()))


def load(cache,ids):
    parts=[];qualified=[];sources={}
    for p in ids:
        for trial in (1,2):
            prefix=cache/f'A{p:02d}'/f'trial-{trial}'
            f=prefix.with_suffix('.knots.npz')
            src=prefix.with_suffix('.source.json')
            evidence=json.loads(src.read_bytes())
            checksum=sha(f)
            if (evidence.get('qualified') is not True or evidence.get('npz_sha256')!=checksum or
                    evidence.get('dataset')!='10.6019/S-BIAD1482' or evidence.get('person')!=f'A{p:02d}'
                    or evidence.get('trial')!=trial or not {'length_mm','angle_deg'}.issubset(evidence.get('units',{}))):
                raise ValueError('Knot source identity, numeric checksum or paired tracking rows failed')
            with np.load(f,allow_pickle=False) as z:
                length,angle,row,clock,seg=[np.asarray(z[key],dtype=float) for key in ('length_mm','angle_deg','tracking_row','tracker_time','segment_id')]
            (l,a,y,c),q=intervals(length,angle,row,clock,seg)
            if not len(c):raise ValueError(f'No usable windows in A{p:02d} trial {trial}')
            groups=np.column_stack([np.full(len(c),p),np.full(len(c),trial),c]).astype(int)
            parts.append((l,a,y,groups));qualified.append(dict(person=p,trial=trial,**q));sources[str(f.relative_to(cache))]=checksum
    return tuple(np.concatenate(col) for col in zip(*parts)),qualified,sources


def weights(g):
    w=np.zeros(len(g));people=np.unique(g[:,0])
    for p in people:
        for q in (1,2):
            m=(g[:,0]==p)&(g[:,1]==q)
            if not m.any():raise ValueError('Missing required trial')
            w[m]=1/(2*len(people)*m.sum())
    return w


def swaps(g):
    d=np.full(len(g),-1,int)
    for p in np.unique(g[:,0]):
        for q in (1,2):
            i=np.flatnonzero((g[:,0]==p)&(g[:,1]==q));o=np.flatnonzero((g[:,0]==p)&(g[:,1]==3-q))
            if not len(o) or not len(i):raise ValueError('No independent-trial donor')
            if not np.all(np.diff(g[o,2])>0) or not np.all(np.diff(g[i,2])>0):raise ValueError('Wrong trial ordering')
            d[i]=o[np.arange(len(i))*len(o)//len(i)]
    if (d<0).any() or np.any(g[:,1]==g[d,1]) or np.any(g[:,0]!=g[d,0]):raise ValueError('Unsafe donor alignment')
    return d


def scale(a,w):
    m=np.average(a,axis=0,weights=w);s=np.sqrt(np.average((a-m)**2,axis=0,weights=w))
    return m,np.where(s<1e-8,1.,s)


def fit(data,encoder,random,cfg):
    l,a,y,g=data;w=weights(g);t=tokens(l,a)
    m,s=scale(t.reshape(-1,6),np.repeat(w/4,4))
    ix=np.argsort(y,kind='stable');median=float(y[ix[np.searchsorted(np.cumsum(w[ix]),w.sum()/2)]])
    state={'parent_sha256':PARENT,'format':1,'typical':median,'readouts':{}}
    residual=y-(l[:,-1]-l[:,-11]);intercept=float(np.average(residual,weights=w))
    for method in LEARNED:
        f={'token_mean':m.tolist(),'token_sd':s.tolist()}
        x=design(method,l,a,f,random if method=='random_both' else encoder,cfg,linear,encode)
        mu,sd=scale(x,w);z=(x-mu)/sd
        coef=np.linalg.solve(z.T@(w[:,None]*z)+.05*np.eye(z.shape[1]),z.T@(w*(residual-intercept)))
        f.update(mean=mu.tolist(),sd=sd.tolist(),coef=coef.tolist(),intercept=intercept);state['readouts'][method]=f
    return state


def predictions(data,state,encoder,random,cfg):
    l,a,y,g=data
    results={m:batch(m,l,a,state,encoder,random,cfg,linear,encode) for m in MODES}
    results['wrong_both']=batch('shared_both',l,a[swaps(g)],state,encoder,random,cfg,linear,encode)
    return results


def person_rows(data,pred):
    l,a,y,g=data;rows=[]
    for p in np.unique(g[:,0]):
        who=g[:,0]==p;w=weights(g[who]);scores={}
        for m,vec in pred.items():
            err=vec[who]-y[who];scores[m]={'mae_mm':float(w@np.abs(err)),'rmse_mm':float(np.sqrt(w@(err**2))),'bias_mm':float(w@err)}
        rows.append({'person':int(p),'windows':int(who.sum()),'scores':scores})
    return rows


def summarize(rows,stage,complete=True):
    methods=rows[0]['scores']
    avg={m:{k:float(np.mean([r['scores'][m][k] for r in rows])) for k in ('mae_mm','rmse_mm','bias_mm')} for m in methods}
    order=sorted(rows,key=lambda r:tuple(r['scores'][m]['mae_mm']-r['scores']['shared_both']['mae_mm'] for m in ('shared_length','wrong_both','linear_both','random_both','geometry')))
    contrasts={}
    for m in ('shared_length','wrong_both','linear_both','random_both','geometry','recent','hold','linear_length','typical'):
        gains=[r['scores'][m]['mae_mm']-r['scores']['shared_both']['mae_mm'] for r in order]
        n=sum(v!=0 for v in gains);plus=sum(v>0 for v in gains)
        rec={'paired_gain_mm':gains,'mean_gain_mm':float(np.mean(gains)),'people_improved':plus}
        if complete and len(rows)==4:rec['sign_p']=min(1.,2*sum(math.comb(n,i) for i in range(min(plus,n-plus)+1))/2**n)
        contrasts[m]=rec
    both=sum(x>0 and y>0 for x,y in zip(contrasts['shared_length']['paired_gain_mm'],contrasts['wrong_both']['paired_gain_mm']))
    gate=None if not complete or len(rows)!=4 else bool(both>=3 and all(avg['shared_both']['mae_mm']<=.95*avg[k]['mae_mm'] for k in ('shared_length','wrong_both')))
    return {'stage':stage,'people':len(rows),'windows':sum(r['windows'] for r in rows),'horizon_tracking_steps':10,'scores':avg,'contrasts':contrasts,
            'joint_improvements':both,'paired_angle_criterion':gate,'paired_order':'One anonymous outcome-sorted order is used across contrasts in this stage.'}


def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['fit','assess']);p.add_argument('cache',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--model',type=Path,default=HERE/'model.json');p.add_argument('--parent',type=Path,default=HERE.parent/'movement-weights.npz')
    args=p.parse_args();args.out.mkdir(exist_ok=True,parents=True)
    if sha(args.parent)!=PARENT:raise ValueError('Shared movement checkpoint identity changed')
    cfg,w=read_checkpoint(args.parent)
    rand={k:np.asarray(v,float) for k,v in json.loads((HERE.parent/'back_rotation/random-encoder.json').read_bytes()).items()}
    if args.stage=='fit':
        data,coverage,hashes=load(args.cache,TRAIN);rows=[]
        for person in TRAIN:
            test=data[3][:,0]==person
            train=tuple(a[~test] for a in data);held=tuple(a[test] for a in data)
            state=fit(train,w,rand,cfg);rows.extend(person_rows(held,predictions(held,state,w,rand,cfg)))
        state=fit(data,w,rand,cfg);write(args.out/'model.json',state)
    else:
        data,coverage,hashes=load(args.cache,ASSESS);state=json.loads(args.model.read_bytes())
        rows=person_rows(data,predictions(data,state,w,rand,cfg))
    result=summarize(rows,args.stage);write(args.out/(args.stage+'-summary.json'),result)
    write(args.out/(args.stage+'-source.json'),{'coverage':coverage,'input_sha256':hashes})
    print(args.stage,result['windows'],result['scores']['shared_both'],result['paired_angle_criterion'])
if __name__=='__main__':run()
