"""Evaluate the frozen PhysioNet knee-stride models on the frozen optical recording."""
import argparse
from pathlib import Path
import hashlib
import json
import sys
from time import perf_counter

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
sys.path.insert(0, str(PACKAGE))
from predict import MODELS, forecast, phase_tokens, predictions
from trials import select_periods
from select_segments import select

PAIRS = [('ridge_residual','prior_stride'),('transformer_residual','prior_stride'),
         ('transformer_residual','ridge_residual')]
MODEL_HASHES = {
    'predict.py':'a32a7ffd371b8512e322f57f0f35849dc11e31d4b54174bba91ee70a71cca4f1',
    'weights.json':'c866348ffd0b6e3fcefc5feb9ce6178d3c3e88c5f92d7a2474fa9176e379afbe',
    'protocol.json':'a96040d1cfd327d1170bb836137aa8abf622bf1bebdc18288f30a76880ecb890',
    'trials.py':'09e95a79067543396f9ed917cab0c54d98cca48bbd256e631584dbf6f32ae425',
    'results.json':'b695de7f97aa7bc0d8d6d1c7546e040ac651fec46c312eea9499103ae5038770',
}
FREEZES = {
    'preregistration.md':'f0b0b4c3ea5fe6b5491b736129aede492336b91342cb886e91e9fcd97a77392a',
    'clock-addendum.md':'3d1ffb783dec4290d6c3beb5e898acf0f017cafa5953dc025f69cd688dde222c',
    'selection.json':'a5fddd10358ae4f3d4dbeaa6d80442b3811749888ffad2a19e4dea92f1cb59f1',
    'select_segments.py':'2bb72655fc42815df6d4f9960455b18bd889a9220c991d0afbc19e99a6e14cd8',
}
DATA_SHA = 'df8b3e31d2fe6869b95b4776a8f77639da476685b4c0ccb86c985bee3f01b531'

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def array_hash(array, dtype='<f8'):
    return hashlib.sha256(np.asarray(array,dtype=dtype).tobytes(order='C')).hexdigest()

def resample(series, k):
    """Interpolate on an integer rational clock. Integer hits use the single observation."""
    lower, remainder = np.divmod(5*k,3)
    upper = lower + (remainder != 0)
    return series[lower] + (remainder[:,None] / 3) * (series[upper] - series[lower])

def valid_ranges(native, lower, upper):
    valid = (np.isfinite(native) & (native != 0)).all(axis=1)
    rejected = np.r_[0, np.cumsum(~valid)]
    return rejected[upper+1] == rejected[lower]

def score_person(source, row, weights):
    trial = source[row['trial_path']]
    lo,hi = row['zero_based_half_open']
    raw = np.column_stack([trial['jointAngles'][name][0, lo:hi] for name in row['angle_names']])
    # First two columns supply model data; the others determine original short-mask availability.
    grid = np.arange((len(raw)-1)*3//5+1)
    knees = resample(raw[:,:2],grid)
    cuts0 = np.arange(240,len(grid)-15,3)
    raw_cut, rem = np.divmod(5*cuts0,3)
    assert (rem == 0).all()
    target = raw_cut + 25
    mask_knee = valid_ranges(raw[:,:2],5*(cuts0-239)//3,target)
    mask_short = valid_ranges(raw,raw_cut-40,target)
    cuts = cuts0[mask_knee & mask_short]
    if not len(cuts):
        return dict(person=row['person'],available=False,all_windows=len(cuts0),n=0), None
    native_cuts = 5*cuts//3
    target = raw[native_cuts+25,:2]
    assert np.array_equal(target,knees[cuts+15])
    periods = select_periods(knees, cuts)
    tokens, anchors = phase_tokens(knees,cuts,periods)
    outputs = {name:[] for name in MODELS}
    for start in range(0,len(cuts),256):
        ix=slice(start,start+256)
        for name, value in predictions(tokens[ix],anchors[ix],weights).items():
            outputs[name].append(value)
    outputs = {name:np.concatenate(value) for name,value in outputs.items()}
    assert all(np.isfinite(a).all() for a in outputs.values())
    mae = {}
    for name,value in outputs.items():
        right,left=np.mean(np.abs(value-target),axis=0)
        mae[name]={'right':float(right),'left':float(left),'bilateral':float((right+left)/2)}
    delta={}
    for a,b in PAIRS:
        delta[f'{a}_minus_{b}']=mae[a]['bilateral']-mae[b]['bilateral']
    checks=[]
    for j in sorted({0,len(cuts)//2,len(cuts)-1}):
        cut=cuts[j]
        idx=np.arange(cut-239,cut+1)
        prefix=resample(raw[:native_cuts[j]+1,:2],idx)
        assert np.array_equal(knees[idx],prefix)
        changed=raw.copy()
        changed[native_cuts[j]+1:,:2]+=123.
        new_prefix=resample(changed[:,:2],idx)
        assert np.array_equal(prefix,new_prefix)
        assert np.allclose(changed[native_cuts[j]+25,:2]-target[j],123,atol=1e-12,rtol=0)
        direct=forecast(idx,prefix,weights)
        alt = forecast(idx,new_prefix,weights)
        assert direct==alt
        p0=min(range(45,181),key=lambda p:np.square(prefix[-60:]-prefix[-60-p:-p]).sum())
        assert p0==periods[j]==direct['period_frames']
        diffs=[np.max(np.abs(outputs[name][j]-direct[name])) for name in MODELS]
        assert max(diffs)<0.001
        checks.append({'model_cut':int(cut),'native_cut_0based':int(lo+native_cuts[j]),
                       'native_target_0based':int(lo+native_cuts[j]+25),'period':int(p0),
                       'max_batch_scalar_deg':float(max(diffs)),'future_change_forecast_deg':0.0})
    n=len(cuts)
    measured=dict(person=row['person'],available=True,all_windows=len(cuts0),n=n,
                  excluded=len(cuts0)-n,failing_bilateral_history=int((~mask_knee).sum()),
                  failing_short_six_joint=int((~mask_short).sum()),mae_deg=mae,
                  paired_differences_deg=delta,clock_controls=checks,
                  native_column_sha256_le_f8={name:array_hash(raw[:,i]) for i,name in enumerate(row['angle_names'])},
                  native_cut_index_sha256_le_i8=array_hash(lo+native_cuts,'<i8'),
                  native_target_pairs_sha256_le_f8=array_hash(target))
    return measured, array_hash(raw[:,:2])

def main(archive):
    # The distributed protocol omits two administrative sentences. The original
    # digest remains part of the pre-existing result record for reproducibility.
    public_protocols = {**FREEZES, 'preregistration.md': 'a8c425b5d722a9f98b1ab77d9abf1c465fa324b13ace0aace1e870b41bc9b0f7'}
    for folder,expected in ((HERE,public_protocols),(PACKAGE,MODEL_HASHES)):
        for file,sha in expected.items():
            assert digest(folder/file)==sha,file
    assert digest(archive)==DATA_SHA
    rows=json.loads((HERE/'selection.json').read_text())
    assert rows==select(archive)
    original=json.loads((PACKAGE/'results.json').read_text())
    assert original['cutoffs']==40201
    assert original['mean_person_mae_deg']['prior_stride']['bilateral']==3.5352540464780127
    assert original['weights_sha256']==MODEL_HASHES['weights.json']
    assert original['controls']['maximum_fast_vs_scalar_forecast_difference_deg']<0.001
    source_hashes={r['knee_series_sha256_le_f8'] for r in original['participants']+original['training_join']}
    weights=json.loads((PACKAGE/'weights.json').read_text())
    data=[]
    with h5py.File(archive) as h:
        for row in rows:
            person,knee_hash=score_person(h,row,weights)
            if knee_hash:
                assert knee_hash not in source_hashes
                source_hashes.add(knee_hash)
                person['native_selected_knees_sha256_le_f8']=knee_hash
            data.append(person)
    included=[p for p in data if p['available']]
    n=len(included)
    assert n
    scores={name:{axis:float(np.mean([p['mae_deg'][name][axis] for p in included]))
                  for axis in ('right','left','bilateral')} for name in MODELS}
    bootstrap=np.random.default_rng(21301).integers(0,n,size=(10000,n))
    comparisons={}
    for a,b in PAIRS:
        key=f'{a}_minus_{b}'
        d=np.array([p['paired_differences_deg'][key] for p in included])
        low,high=np.quantile(d[bootstrap].mean(axis=1),[.025,.975])
        wins,ties,losses=int((d<0).sum()),int((d==0).sum()),int((d>0).sum())
        comparisons[key]=dict(mean=float(d.mean()),CI95=[float(low),float(high)],wins=wins,ties=ties,
                              losses=losses,passed=bool(d.mean()<0 and high<0 and wins>=8))
    return dict(archive_sha256=DATA_SHA,protocol_hashes=FREEZES,model_hashes=MODEL_HASHES,
                domain='Reznick US study, offline optical knee estimates, level s0x8 task, 250 ms',
                participants_screened=len(data),participants_scored=n,cutoffs=sum(p['n'] for p in data),
                mean_person_mae_deg=scores,comparisons=comparisons,participants=data,
                archived_original_prior_stride_deg=original['mean_person_mae_deg']['prior_stride']['bilateral'],
                archived_original_cutoffs=original['cutoffs'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('result',type=Path)
    args=parser.parse_args()
    if args.result.exists(): parser.error('Use a fresh result path')
    t0=perf_counter()
    out=main(args.archive)
    with args.result.open('x') as f:
        json.dump(out,f,indent=2,allow_nan=False); f.write('\n')
    print(json.dumps({k:out[k] for k in ('participants_scored','cutoffs','mean_person_mae_deg','comparisons')}))
    print('Full checks and score in seconds',perf_counter()-t0)
