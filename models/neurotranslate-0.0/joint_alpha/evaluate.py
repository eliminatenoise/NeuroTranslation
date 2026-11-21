"""Evaluate a previously frozen joint fit and matched controls by held group."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
from inference import JointModel
from network import Joint
from train import Cases, file_hash


def metrics(t, kind, y, pred):
    if kind=='categorical':
        ii = np.arange(len(y))
        actual = pred[ii,y]
        best = pred.max(axis=1)
        return dict(log_loss_nats=-np.log(np.maximum(actual,1e-30)),top1=(actual==best)/(pred==best[:,None]).sum(axis=1),midrank=1+(pred>actual[:,None]).sum(axis=1)+((pred==actual[:,None]).sum(axis=1)-1)/2)
    d = pred-y
    mae = np.nanmean(abs(d),axis=1)
    if kind=='count':
        # Persistence can give zero expected counts even where the source has a spike.
        # Declare the floor for the log score and keep the unaltered means for MAE.
        lam = np.maximum(pred,1e-8)
        ceiling = int(np.nanmax(y))
        logfac = np.array([math.lgamma(i+1) for i in range(ceiling+1)])
        nll = lam-y*np.log(lam)+logfac[np.nan_to_num(y).astype(int)]
        return dict(poisson_nll_nats=np.nanmean(nll,axis=1),count_mae=mae)
    if t=='human_sacrum_path':
        dist = np.linalg.norm(d.reshape(len(y),-1,3),axis=-1)
        return dict(mean_knot_distance_mm=np.nanmean(dist,axis=1),endpoint_distance_mm=dist[:,-1],coordinate_mae=mae)
    return dict(mae=mae)


def group_means(values,buckets):
    return np.array([np.nanmean(values[i]) if np.isfinite(values[i]).any() else np.nan for i in buckets])


def contrast(a,b):
    pair = a-b
    pair = pair[np.isfinite(pair)]
    if not len(pair):
        return None
    lohi = None
    if len(pair)>1:
        rng = np.random.default_rng(431)
        boot = np.mean(pair[rng.integers(0,len(pair),size=(2000,len(pair)))],axis=1)
        lohi = np.percentile(boot,[2.5,97.5]).tolist()
    return dict(mean=float(pair.mean()),observed_group_bootstrap95=lohi,groups=len(pair))


def native_prediction(model, key, data, rows, portable):
    arrays = portable.arrays
    stats = {f:arrays[key+'.'+f] for f in ['xmean','xscale','ymean','yscale']}
    x,_,valid = data.tensors(rows,stats)
    with torch.no_grad():
        raw = model(key,x,valid).numpy()
    if data.kind=='categorical':
        ex = np.exp(raw-raw.max(1,keepdims=True))
        return ex/ex.sum(1,keepdims=True)
    if data.kind=='count':
        return stats['ymean']*np.exp(np.clip(raw,-10.,10.))
    p = stats['ymean']+stats['yscale']*raw
    return np.maximum(p,0.) if portable.tasks[key].get('output_bound')=='nonnegative' else p


def decoded_batches(model,t,data):
    blocks=[]
    chunk=64 if data.kind=='categorical' else 256
    for i in range(0,len(data.x),chunk):
        part=slice(i,i+chunk)
        blocks.append(model.predict(t,data.x[part],None if data.valid is None else data.valid[part]))
    return np.concatenate(blocks)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path)
    p.add_argument('checkpoint',type=Path)
    p.add_argument('evidence',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    schema=json.loads(args.manifest.read_text())['tasks']
    joint=JointModel.load(args.checkpoint)
    native=Joint(joint.tasks,joint.architecture)
    native.load_state_dict({k:torch.tensor(joint.arrays[k]) for k in native.state_dict()})
    result={'checkpoint_sha256':file_hash(args.checkpoint),'evaluation':'retrospective previously observed held groups; no reserved recording opened','methods':'Equal group means on each listed split. All deltas are joint minus comparator. Lower is better except top1. The count log score floors expected counts at 1e-8. Intervals resample groups within the listed split; animals and people are distinguished in each source description.','tasks':{}}
    for t,s in joint.tasks.items():
        control=JointModel.load(args.evidence/(t+'-control.npz'))
        report={}
        for k in schema[t]['splits']:
            if k=='train':
                continue
            d=Cases(args.manifest.parent,schema[t],k)
            preds={'joint':decoded_batches(joint,t,d),'single_task':decoded_batches(control,t,d)}
            if d.baseline is not None:
                preds['source_baseline']=d.baseline
            if d.strong_reference is not None:
                preds['historical_specialist']=d.strong_reference
            if d.kind=='count' and d.baseline is not None:
                preds['half_persistence_half_training_rate']=.5*d.baseline+.5*joint.arrays[t+'.ymean']
            if d.kind=='categorical':
                # No training-unit marginal transfers to independently sorted rosters.
                valid=np.isfinite(d.x).any(axis=(-1,-2)) if d.valid is None else d.valid
                prior=valid/valid.sum(axis=1,keepdims=True)
            else:
                prior=np.broadcast_to(joint.arrays[t+'.ymean'],d.y.shape)
            preds['training_mean_or_uniform']=prior
            scores={mode:metrics(t,d.kind,d.y,v) for mode,v in preds.items()}
            primary=next(iter(scores['joint']))
            entry={'rows':len(d.y),'groups':len(d.groups),'group_definition':schema[t].get('group_definition'),'source_baseline':schema[t].get('baseline_description'),'primary_metric':primary,'mean_scores':{},'paired_primary_joint_minus':{}}
            for mode,ms in scores.items():
                entry['mean_scores'][mode]={name:float(np.nanmean(group_means(vals,d.buckets))) for name,vals in ms.items()}
                if mode!='joint':
                    if d.kind=='categorical':
                        left,right=scores['joint'][primary],ms[primary]
                    else:
                        available=np.isfinite(preds[mode])&np.isfinite(preds['joint'])&np.isfinite(d.y)
                        aligned_y=np.where(available,d.y,np.nan)
                        left=metrics(t,d.kind,aligned_y,preds['joint'])[primary]
                        right=metrics(t,d.kind,aligned_y,preds[mode])[primary]
                    mask=np.isfinite(left)&np.isfinite(right)
                    a=group_means(np.where(mask,left,np.nan),d.buckets)
                    b=group_means(np.where(mask,right,np.nan),d.buckets)
                    entry['paired_primary_joint_minus'][mode]=contrast(a,b)
            # Mask a complete input modality on the same held histories without refitting.
            modality_masks={}
            if t.startswith('macaque_'):
                modality_masks={'hide_motion':np.arange(8),'hide_cortex':np.arange(8,45)}
            elif t.startswith('human_'):
                modality_masks={'hide_scalp':np.arange(6),'hide_muscle':np.arange(6,14),'hide_sacrum':np.arange(14,26)}
            if modality_masks:
                entry['masked_modality_change_in_primary_error']={}
                for label,columns in modality_masks.items():
                    x=d.x.copy()
                    x[...,columns]=np.nan
                    masked=np.concatenate([joint.predict(t,x[i:i+256]) for i in range(0,len(x),256)])
                    change=metrics(t,d.kind,d.y,masked)[primary]-scores['joint'][primary]
                    vals=group_means(change,d.buckets)
                    entry['masked_modality_change_in_primary_error'][label]=float(np.nanmean(vals))
            if d.kind!='categorical':
                errors=np.abs(preds['joint']-d.y)
                entry['joint_mean_absolute_error_by_output']={}
                for j,name in enumerate(s['outputs']):
                    averages=group_means(errors[:,j],d.buckets)
                    observed=averages[np.isfinite(averages)]
                    entry['joint_mean_absolute_error_by_output'][name]=float(np.mean(observed)) if len(observed) else None
            if d.strong_reference is not None:
                entry['historical_specialist']=schema[t].get('support',{}).get(k,{}).get('strong_reference_description')
            entry['joint_vs_single_task_direction']=('higher_error' if entry['paired_primary_joint_minus']['single_task']['mean']>0 else 'lower_or_equal_error')
            rows=np.arange(min(16,len(d.y)))
            reference=native_prediction(native,t,d,rows,joint)
            actual=preds['joint'][rows]
            delta=float(np.abs(reference-actual).max())
            if not np.isfinite(actual).all() or not np.allclose(reference,actual,atol=2e-4,rtol=2e-5):
                raise RuntimeError(f'Training runtime and portable inference disagree for {t}/{k}: {delta}')
            entry['held_numpy_torch_parity']={'rows':len(rows),'max_abs':delta}
            if d.kind=='categorical':
                entry['candidates_per_row']=d.x.shape[1]
                if not np.allclose(preds['joint'].sum(axis=1),1.,atol=1e-6):
                    raise ValueError('Unnormalized probabilities')
            report[k]=entry
            print(t,k,entry['mean_scores']['joint'][primary],flush=True)
        if not report:
            raise ValueError('Missing held evaluation for '+t)
        result['tasks'][t]=report
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
