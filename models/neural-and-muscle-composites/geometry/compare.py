"""Is the prior simulated muscle–tendon geometry useful for a measured handle forecast?"""
from pathlib import Path
import argparse
import hashlib,json
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path, help="Folder with the three reconstructed reach NPZ files")
parser.add_argument("lengths", type=Path, help="Folder with three *-lengths.npz files from read_lengths.py")
parser.add_argument("output", type=Path, help="New file for aggregate scores")
args = parser.parse_args()
if args.output.exists():
    parser.error("Choose a new output file")
CONTACTS = json.loads((Path(__file__).resolve().parents[1] / "reach/protocol.json").read_bytes())["contacts"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(split,names=None):
    with np.load(args.source/(split+".npz")) as s,np.load(args.lengths/(split+"-lengths.npz")) as m:
        for key in ("block","original","workspace","ordinal","k"):np.testing.assert_array_equal(s[key],m[key])
        ids=list(m["names"].astype(str))
        if names is None:names=ids
        assert set(names)==set(ids) and len(names)==len(ids)==39
        pos=s["pose"]; guide=s["all_guide"]; spikes=s["all_history"]
        pop=np.stack([spikes[:,:,guide[:,0]==contact].sum(axis=2) for contact in CONTACTS],axis=-1)
        features=np.concatenate([pos[:,-1],*[pos[:,-1]-pos[:,-1-lag] for lag in (4,9,19)]],axis=-1)
        x={"pose":features,"neural":pop.reshape(-1,4,5,len(CONTACTS)).sum(axis=2).reshape(len(pos),-1),"anchor":m["anchor_m"][:,[ids.index(k) for k in names]],"target":s["movement"][:,-1,6:8]*10}
        x.update({k:s[k] for k in ('original','workspace','block','ordinal','k')})
    return x,names

def weights(a,keys):
    mat=np.stack([a[k] for k in keys],axis=1)
    _,inv,cnt=np.unique(mat,axis=0,return_inverse=True,return_counts=True)
    w=1/cnt[inv]
    for group in np.unique(a["workspace"]):
        ix=a["workspace"]==group;w[ix]/=w[ix].sum()
    return w/w.sum()

def fit(x,y,w):
    mu=w@x;sig=np.sqrt(w@((x-mu)**2));sig[sig<1e-8]=1
    X=(x-mu)/sig; bias=w@y
    # Solve the penalized regression directly and check against augmented least squares.
    coef=np.linalg.solve((X*w[:,None]).T@X+np.eye(X.shape[1]),(X*w[:,None]).T@(y-bias))
    augmented=np.vstack([X*np.sqrt(w)[:,None],np.eye(X.shape[1])])
    response=np.vstack([(y-bias)*np.sqrt(w)[:,None],np.zeros_like(coef)])
    ref=np.linalg.lstsq(augmented,response,rcond=None)[0]
    np.testing.assert_allclose(coef,ref,rtol=0,atol=1e-9)
    return mu,sig,coef,bias

def predict(x,model):
    mu,sig,coef,bias=model
    return ((x-mu)/sig)@coef+bias

def join(a,neural,anchor):
    chunks=[a["pose"]]
    if neural:chunks.append(a["neural"])
    chunks.append(anchor)
    return np.concatenate(chunks,axis=1)

def eligible(a):
    return np.logical_and.reduce([np.isfinite(a[k]).all(axis=1) for k in ('pose','neural','anchor','target')])

def subset(a,ix):return {k:v[ix] for k,v in a.items()}

def earlier(a):
    n=len(a["original"]);donor=np.full(n,-1)
    for i in range(n):
        j=np.flatnonzero((np.arange(n)<i)&(a["workspace"]==a["workspace"][i])&(a["block"]==a["block"][i])&(a["original"]<a["original"][i]))
        if len(j):donor[i]=j[-1]
    return donor

train,names=load("train");train=subset(train,eligible(train));w=weights(train,['workspace','block','original'])
models={}
for family in ('pose','pose_and_cortex'):
    neural=family=='pose_and_cortex'
    for method,anchor in [('zero_geometry',np.zeros_like(train["anchor"])),('true_geometry',train["anchor"])]:
        models[family,method]=fit(join(train,neural,anchor),train['target'],w)
records=[]
for split in ("block1","block2"):
    a,_=load(split,names);records.append(subset(a,eligible(a)))
held={k:np.concatenate([r[k] for r in records]) for k in records[0]}
d=earlier(held);mask=d>=0
scores={}
control_grids={}
for family in ('pose','pose_and_cortex'):
    neural=family=='pose_and_cortex';zeros=np.zeros_like(held["anchor"])
    preds={"persistence":np.zeros_like(held['target'])}
    for method,A in [('zero_geometry',zeros),('true_geometry',held['anchor']),('earlier_geometry',held['anchor'][np.maximum(d,0)])]:
        preds[method]=predict(join(held,neural,A),models[family,'true_geometry' if method=='earlier_geometry' else method])
    control_grids[family]={}
    for group in np.unique(held['workspace']):
        result={}
        for condition,m in [('all',held['workspace']==group),('paired',(held['workspace']==group)&mask)]:
            pick=subset(held,m);w=weights(pick,['block','original'])
            vals={name:float(w@np.linalg.norm(x[m]-pick['target'],axis=1)) for name,x in preds.items() if condition=='paired' or name!='earlier_geometry'}
            result[condition]={'rows':int(m.sum()),'trials':len(set(zip(pick['block'].tolist(),pick['original'].tolist()))),'endpoint_error_mm':vals}
        control_grids[family][str(group)]=result
summary={'target':'Measured handle planar endpoint displacement, millimetres, 100 ms after last earlier observation','training_windows':len(train['original']),
         'registered_test_windows':[len(r['original']) for r in records],'original_evaluation_unit':'Workspace with equal original trial weight; unique trial identity includes acquisition block.',
         'comparisons':control_grids,'case_selection':'Retrospective new predeclared comparison on the prior qualified days. No outcome enters earlier features. One macaque.',
         'evaluation_files':{q:sha((args.source if q.startswith('source/') else args.lengths)/Path(q).name) for q in ['source/train.npz','source/block1.npz','source/block2.npz','mechanics/train-lengths.npz','mechanics/block1-lengths.npz','mechanics/block2-lengths.npz']}}
main=control_grids['pose_and_cortex']
summary['incremental_geometry_pass']=all(z['paired']['endpoint_error_mm']['true_geometry']<min(z['paired']['endpoint_error_mm'][m] for m in ('earlier_geometry','zero_geometry')) for z in main.values())
args.output.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
print(len(train['original']),[(k,v['paired']) for k,v in main.items()],summary['incremental_geometry_pass'])
