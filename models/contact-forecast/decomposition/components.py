"""Decompose Poisson deviance additively into total-count and contact-allocation errors."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.special import xlogy

PHASES=('bump','post_bump_go','unbumped_go')

def components(y, predicted):
    y=np.asarray(y,dtype=np.float64)
    mu=np.maximum(np.asarray(predicted,dtype=np.float64),1e-6)
    if mu.shape!=y.shape or np.any(y<0) or not (np.isfinite(y).all() and np.isfinite(mu).all()): raise ValueError('invalid counts or means')
    count=y.sum(-1)
    total=mu.sum(-1)
    direct=2*(xlogy(y,y/mu)-y+mu).mean(-1)
    number=2*(xlogy(count,count/total)-count+total)/y.shape[-1]
    fraction=y/np.where(count[:,None]>0,count[:,None],1)
    allocation=2*xlogy(y,fraction/(mu/total[:,None])).mean(-1)
    np.testing.assert_allclose(direct,number+allocation,rtol=1e-10,atol=1e-10)
    assert (number>=-1e-10).all() and (allocation>=-1e-10).all()
    return np.stack((direct,number,allocation,count,total),axis=-1)

def original_mean(values,idx):
    return np.mean([values[idx==trial].mean(0) for trial in np.unique(idx)],axis=0)

def analyze(data,transformer,linear):
    results={}
    for code,phase in enumerate(PHASES):
        for support,mask in [('eligible',data['phase']==code),('matched',(data['phase']==code)&(data['donor']>=0))]:
            if not mask.any():continue
            rows=data['trial'][mask]
            y=data['target_count_100ms'][mask]
            group={}
            for family,archive in [('transformer',transformer),('poisson',linear)]:
                for arm in ('count_cue','all','wrong_movement','movement','cue','count','movement_cue'):
                    if arm=='wrong_movement' and support!='matched':continue
                    forecast=archive[arm]
                    if forecast.ndim==2:forecast=forecast[None,...]
                    metrics=[original_mean(components(y,seed[mask]),rows).tolist() for seed in forecast]
                    group[family+'_'+arm]={'by_fit':metrics,'mean':np.mean(metrics,0).tolist()}
            results[phase+'_'+support]={'windows':int(mask.sum()),'originals':len(np.unique(rows)),'models':group}
    return {'fields':['mean deviance per contact','total-count deviance divided by contact count','allocation deviance per contact','observed events across contacts per 100 ms','expected events across contacts per 100 ms'],'groups':results}

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('source','transformer','poisson','out'):cli.add_argument(name,type=Path)
    args=cli.parse_args()
    with np.load(args.source) as src, np.load(args.transformer) as tf, np.load(args.poisson) as gl:
        for p in (tf,gl):
            for key in ('trial','offset','phase','k','donor'):
                np.testing.assert_array_equal(p[key],src[key])
        output=analyze(src,tf,gl)
    args.out.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
