"""Reproduce the locked width and duration comparisons using inner development folds."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def candidate(folder):
    r=read(folder/'training.json')
    s=read(folder/'score.json')
    return dict(**s['architecture'],learning_rate=r.get('learning_rate',.0015),steps=r['steps'],seed=r.get('seed',431),schedule=r.get('schedule','constant'),aggregate=s['aggregate'],task_scores=s['task_scores'],domain_scores=s['domain_scores'],median_latency_seconds=s['median_latency_seconds'],parameters=r['parameters_total'],fit_seconds=r['joint']['seconds'],training_device=r.get('training_device','cpu'),peak_rss_kib=r.get('rss_peak_through_fit_kib'),gpu_peak_allocated_bytes=r.get('gpu_peak_allocated_bytes'),checkpoint_sha256=r['checkpoint_sha256'])


def fit_score(folds,out,config,device):
    out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
    if device=='cuda':
        for k in ['TMPDIR','XDG_CACHE_HOME','MIOPEN_USER_DB_PATH','TRITON_CACHE_DIR']:
            path=out.parent/'gpu-cache'/k
            path.mkdir(parents=True,exist_ok=True)
            env[k]=str(path.resolve())
    cmd=[sys.executable,'-B',str(HERE/'train.py'),str(folds),'--out',str(out/'checkpoint.npz'),'--evidence',str(out),'--threads','2','--device',device]
    for k in ['width','heads','depth','ff_width','learning_rate','steps','seed','schedule']:
        cmd+=['--'+k.replace('_','-'),str(config[k])]
    with (out/'log').open('w') as log:
        subprocess.run(cmd,check=True,env=env,stdout=log,stderr=subprocess.STDOUT)
        subprocess.run([sys.executable,'-B',str(HERE/'capacity.py'),'score',str(folds),str(out/'checkpoint.npz'),str(out/'score.json')],check=True,env=env,stdout=log,stderr=subprocess.STDOUT)
    return candidate(out)


def stage_one(folds,out,device):
    plan=read(HERE/'capacity-plan.json')
    for w,h,d,ff in plan['architectures']:
        backend='cpu' if w<128 else device
        for lr in ([.0015,.0005] if w>=128 else [.0015]):
            folder=out/(f'w{w}-480-{backend}2'+('' if lr==.0015 else '-lr'+str(lr)))
            cfg=dict(width=w,heads=h,depth=d,ff_width=ff,learning_rate=lr,steps=480,seed=431,schedule='constant')
            fit_score(folds,folder,cfg,backend)


def stage_two(folds,out,device):
    one=sorted([candidate(p.parent) for p in out.glob('w*-480-*/score.json')],key=lambda v:(v['width'],v['learning_rate']))
    if len(one)!=8 or len(set((v['width'],v['learning_rate']) for v in one))!=8:
        raise ValueError('All eight fixed-budget candidates must finish before refinement')
    first=min(one,key=lambda v:v['aggregate'])
    (out/'stage-one-seal.json').write_text(json.dumps({'candidates':one,'selected':first},indent=2)+'\n')
    best_wide=min((v for v in one if v['width']>=256),key=lambda v:v['aggregate'])
    base=next(v for v in one if v['width']==32)
    finalist={(v['width'],v['learning_rate']):v for v in (base,first,best_wide)}
    trials=[dict(first,seed=827)]
    for v in finalist.values():
        for seed in (431,827):
            trials.append(dict(v,seed=seed,steps=1920,schedule='warmup_cosine'))
    def lane(configs,backend):
        rows=[]
        for v in configs:
            folder=out/f"refine-w{v['width']}-s{v['steps']}-seed{v['seed']}-lr{v['learning_rate']}"
            rows.append(fit_score(folds,folder,v,backend))
        return rows
    groups=[([v for v in trials if v['width']<128],'cpu'),([v for v in trials if v['width']>=128],device)]
    with ThreadPoolExecutor(max_workers=2 if device=='cuda' else 1) as pool:
        jobs=[pool.submit(lane,configs,backend) for configs,backend in groups if configs]
        all_rows=[first]+[r for job in jobs for r in job.result()]
    by={}
    for v in all_rows:
        by.setdefault((v['width'],v['learning_rate'],v['steps'],v['schedule']),[]).append(v)
    comparisons=[]
    for (width,lr,steps,schedule),pair in by.items():
        assert sorted(v['seed'] for v in pair)==[431,827]
        comparisons.append(dict(width=width,heads=pair[0]['heads'],depth=pair[0]['depth'],ff_width=pair[0]['ff_width'],learning_rate=lr,steps=steps,schedule=schedule,aggregate=sum(v['aggregate'] for v in pair)/2,median_latency_seconds=sum(v['median_latency_seconds'] for v in pair)/2,seed_scores=sorted(pair,key=lambda v:v['seed'])))
    best=min(v['aggregate'] for v in comparisons)
    selected=min([v for v in comparisons if v['aggregate']<=best+1e-8],key=lambda v:v['median_latency_seconds'])
    public_selection={k:v for k,v in selected.items() if k!='seed_scores'}
    result={'metric':read(HERE/'capacity-plan.json')['metric'],'selected':public_selection,'candidates':one,'refinement_candidates':comparisons,'selected_full_refit_seed':431,'evaluation_scope':'Training-internal grouped validation only. Comparison spans the enumerated widths, learning rates, durations and seeds.'}
    (out/'capacity-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(public_selection),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['one','two']);p.add_argument('fold_manifest',type=Path);p.add_argument('output',type=Path);p.add_argument('--large-device',choices=['cpu','cuda'],default='cpu')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    if a.stage=='one':
        stage_one(a.fold_manifest,a.output,a.large_device)
    else:
        stage_two(a.fold_manifest,a.output,a.large_device)
