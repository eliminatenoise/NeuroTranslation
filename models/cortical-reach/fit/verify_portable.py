"""Check archived native forecasts against the Python and offline JS reader."""
import argparse, copy, json, subprocess, tempfile
from pathlib import Path
import numpy as np
from predict import BLOCKS, MODES, SEEDS, SESSION, SHAPES, UNITS, predict
from train import load, sha, weight_path

def run(data,out,stage,report):
    raw,_,ids=load(data,stage,False)
    # Prespecified coverage: every window of the first eligible original, first and last
    # eligible row in each epoch, first source row with and without an earlier donor.
    selected=set(np.flatnonzero(ids['trial']==ids['trial'][0]))
    for epoch in (0,1):
        rows=np.flatnonzero(ids['epoch']==epoch)
        if len(rows): selected.update([rows[0],rows[-1]])
    for donor_status in [ids['donor']<0,ids['donor']>=0]:
        rows=np.flatnonzero(donor_status)
        if len(rows): selected.add(rows[0])
    selected=sorted(selected)
    def history(x):
        return dict(session=SESSION,unit_ids=UNITS,**{k:x[:,index].tolist() for k,index in BLOCKS.items()})
    # The synthetic case has no observed cue and zero counts on every channel.
    histories=[history(np.zeros((5,41)))]+[history(raw[i]) for i in selected]
    expected={}
    worst=0.
    with np.load(out/(stage+'-predictions.npz'),allow_pickle=False) as src:
        if str(src['source_sha256'])!=sha(data) or list(src['seeds'])!=list(SEEDS):
            raise ValueError('wrong source or seed lock')
        for mode in MODES:
            for si,seed in enumerate(SEEDS):
                path=weight_path(out,mode,seed)
                w=json.loads(path.read_text())
                predictions=[predict(w,h) for h in histories]
                native=src[mode][si,selected]
                worst=max(worst,float(np.max(np.abs(native-predictions[1:]))))
                expected[path.name]=[predictions[0]]+native.tolist()
    if worst>=1e-4: raise ValueError('Python/native mismatch')
    w=json.loads(weight_path(out,'all',17).read_text())
    rejected=0
    for bad in ['missing_cue','session','units','absent_units','fractional','negative','masked_angle',
                'bad_availability','nan','short','boolean','weight_shape','weight_nan','scale','weight_units']:
        h=copy.deepcopy(histories[0])
        weights=copy.deepcopy(w)
        if bad=='missing_cue': del h['cue']
        if bad=='session': h['session']='other'
        if bad=='units': h['unit_ids'].reverse()
        if bad=='absent_units': del h['unit_ids']
        if bad=='fractional': h['neural'][0][0]=.25
        if bad=='negative': h['neural'][0][0]=-1
        if bad=='masked_angle': h['cue'][0][1]=1
        if bad=='bad_availability': h['cue'][0][6]=2
        if bad=='nan': h['movement'][0][1]=float('nan')
        if bad=='short': h['movement'].pop()
        if bad=='boolean': h['movement'][0][0]=True
        if bad=='weight_shape': weights['parameters']['position'].pop()
        if bad=='weight_nan': weights['parameters']['position'][0][1]=float('nan')
        if bad=='scale': weights['x_scale'][0]=0
        if bad=='weight_units': weights['unit_ids'].reverse()
        try: predict(weights,h)
        except (ValueError,KeyError): rejected+=1
        else: raise AssertionError('invalid case accepted: '+bad)
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'fixture.json'
        path.write_text(json.dumps(dict(histories=histories,expected=expected),allow_nan=False))
        js=json.loads(subprocess.check_output(['node',str(Path(__file__).with_name('verify-runtime.mjs')),str(path),str(out)],text=True))
    report.write_text(json.dumps(dict(stage=stage,source_sha256=sha(data),native_archive_sha256=sha(out/(stage+'-predictions.npz')),
        python_max_absolute_error_cm=worst,python_invalid_rejected=rejected,js=js,
        reference_rows=[int(v) for v in selected],synthetic='five zero movement/spike bins and unavailable cues; NumPy/JS',
        native_reference='Stored native float32 outputs for six modes and three seeds'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['validation','test'])
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    a=p.parse_args()
    run(a.data,a.out,a.stage,a.report)
