"""Prepare locally supplied Delhaye recordings on their 1 kHz force/event grid."""
import argparse
import hashlib
from io import BytesIO
import json
import os
import shutil
from pathlib import Path
import tempfile

import numpy as np
from scipy.io import loadmat
from scipy.io.matlab._mio5 import varmats_from_mat

ROSTER = Path(__file__).with_name('touch-roster.json')
ROSTER_SHA256 = '616ff7a447cf84de013d3c47e88dc7552122b3aa77855a01b88c5d6b311f2593'
ROW_KEYS = ('recording', 'trial', 'cutoff_ms')
REQUIRED = {'ProtData': ('fxRaw', 'fyRaw', 'fzRaw', 'spk'),
            'AllUCL': ('Subj', 'Unit', 'FileNameUCL', 'UnitType', 'RFloc', 'isVoid', 'isInvalid',
                       'Material_str', 'Direction_str')}


def check_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def columns(directory, row, name):
    path = directory / row['file']
    raw = path.read_bytes()
    if len(raw) != row['bytes'] or 'md5:'+hashlib.md5(raw).hexdigest() != row['md5']:
        raise ValueError(f'Original deposit size/MD5 mismatch for {path.name}')
    if 'sha256' in row and hashlib.sha256(raw).hexdigest() != row['sha256']:
        raise ValueError(f'Original SHA256 mismatch for {path.name}')
    mat = loadmat(BytesIO(raw), variable_names=[name,'__function_workspace__'])
    if mat[name][0]['_Class'] != 'table':
        raise ValueError(f'{path.name}: expected deposited MATLAB table')
    workspace = mat['__function_workspace__'].tobytes()
    if workspace[:4] != b'\0\1IM':
        raise ValueError(f'{path.name}: incompatible nested MAT-v5 header')
    inner = BytesIO(raw[:116]+bytes(8)+workspace[:4]+workspace[8:])
    members = varmats_from_mat(inner)
    if len(members) != 2:
        raise ValueError(f'{path.name}: incompatible table workspace')
    wrapper = loadmat(members[0][1], struct_as_record=False)['__function_workspace__'].item()
    cells = wrapper.MCOS[0]['_ObjectMetadata'].ravel()
    names_idx, values_idx = (7,2) if name == 'AllUCL' else (4,5)
    names = [str(cell.item()) for cell in cells[names_idx].ravel()]
    values = dict(zip(names,cells[values_idx].ravel(),strict=True))
    if len(names) != len(values) or not set(REQUIRED[name]).issubset(values):
        raise ValueError(f'{path.name}: missing or duplicate table field')
    return {k:values[k] for k in REQUIRED[name]}


def native_inputs(row, table, events, axes, held):
    """Construct every feature exclusively from source rows at or before its own t."""
    if any(a.shape!=events.shape for a in axes) or events.ndim!=2:
        raise ValueError(f"{row['file']}: inconsistent force and spike grids")
    i, = [n for n,cell in enumerate(table['FileNameUCL'].ravel()) if cell.item()==Path(row['file']).stem]
    for key, desc in [('Subj','person'),('Unit','unit'),('UnitType','receptor_class'),('RFloc','field_vs_contact')]:
        if table[key][i,0].item()!=row[desc]:
            raise ValueError(f"Wrong {key} in {row['file']}")
    if len(table['isInvalid'][i]) != events.shape[1]:
        raise ValueError('Source trial flags and measurements disagree')
    if table['isVoid'][i,0]:
        return
    t=np.arange(200,len(events)-40,20,dtype=np.int32)
    past=t[:,None,None]-199+20*np.arange(10)[None,:,None]+np.arange(20)[None,None,:]
    for j in range(1, events.shape[1]):
        if table['isInvalid'][i,j-1] or table['isInvalid'][i,j]:
            continue
        def condition(col):
            return tuple(table[k][i,col].item() for k in ('Material_str','Direction_str'))
        material, direction=condition(j)
        if (material,direction)!=condition(j-1):
            continue
        history=events[:,j][past]
        # The in-process training transform uses float64 column stacks, then writes float32.
        current=np.column_stack([a[:,j] for a in axes])[past].mean(axis=2)
        previous=np.column_stack([a[:,j-1] for a in axes])[past].mean(axis=2)
        keep=(np.isfinite(current).all(axis=(1,2)) & np.isfinite(previous).all(axis=(1,2)) &
              np.isin(history,(0,1)).all(axis=(1,2)))
        if not keep.any():
            continue
        x=np.dstack([current,history.sum(axis=2),past[:,:,-1]/1000])[keep].astype('float32')
        n=len(x)
        result=dict(X=x,previous_repeat_force=previous[keep].astype('float32'),cutoff_ms=t[keep],
                    trial=np.full(n,j+1,dtype='int16'),previous_trial=np.full(n,j,dtype='int16'),
                    material=np.full(n,material),direction=np.full(n,direction),
                    baseline=x[:,-1,3:4].copy(),group=np.full(n,row['person']),
                    unit=np.full(n,row['unit']),receptor_class=np.full(n,row['receptor_class']),
                    field_vs_contact=np.full(n,row['field_vs_contact']),
                    recording=np.full(n,Path(row['file']).stem if held else row['file']))
        if held:
            result['person'] = result['group']
        yield result


def outcomes(events, trials, cutoffs):
    """Direct later counts and their binary-observation support, separate from feature extraction."""
    observed=events[cutoffs[:,None]+np.arange(21,41),trials[:,None]-1]
    valid=np.isin(observed,(0,1)).all(axis=1)
    return np.where(valid,observed.sum(axis=1),np.nan).astype('float32')[:,None],valid


def rows_for_split(roster, split):
    rows=[r for r in roster['recordings'] if r['split']==split]
    if {r['person'] for r in rows} != set(roster['partitions'][split]):
        raise ValueError('Participant partition mismatch')
    return rows


def assemble(args, roster):
    held=args.mode=='test-features'
    split='test' if held else args.mode
    summary=columns(args.mat_dir,roster['summary'],'AllUCL')
    blocks=[]
    for row in rows_for_split(roster,split):
        data=columns(args.mat_dir,row,'ProtData')
        events=data['spk']
        axes=[data[key] for key in ('fxRaw','fyRaw','fzRaw')]
        for block in native_inputs(row,summary,events,axes,held):
            if not held:
                y,observed=outcomes(events, block['trial'], block['cutoff_ms'])
                block['y']=y
                block={key:arr[observed] for key,arr in block.items()}
            if len(block['X']):
                blocks.append(block)
    if not blocks:
        raise ValueError('No eligible rows in partition')
    return {key:np.concatenate([b[key] for b in blocks]) for key in blocks[0]}


def test_labels(args, roster):
    if not args.features or not args.predictions or not args.prediction_sha256:
        raise ValueError('Supply frozen held features, keyed predictions and their independently recorded SHA256')
    prediction_bytes=args.predictions.read_bytes()
    if hashlib.sha256(prediction_bytes).hexdigest()!=args.prediction_sha256:
        raise ValueError('Predictions differ from their supplied pre-label digest')
    # Rebuild features without reading future outcomes, so keys cannot be substituted to select test rows.
    held_args=argparse.Namespace(mode='test-features',mat_dir=args.mat_dir)
    expected=assemble(held_args,roster)
    with np.load(args.features,allow_pickle=False) as features, np.load(BytesIO(prediction_bytes),allow_pickle=False) as pred:
        if set(expected)!=set(features.files) or any(not np.array_equal(v,features[k]) for k,v in expected.items()):
            raise ValueError('Frozen features differ from the source reconstruction')
        for k in ROW_KEYS:
            if not np.array_equal(features[k],pred[k]):
                raise ValueError(f'Frozen predictions misaligned on {k}')
        rates=pred['predicted_rate']
        if rates.ndim not in (1,2) or rates.shape[0]!=len(expected['trial']) or rates.size==0:
            raise ValueError('Predicted-rate row count mismatch')
        if not np.isfinite(rates).all() or np.any(rates<0):
            raise ValueError('Frozen predictions contain invalid count rates')
    result={k:expected[k] for k in ROW_KEYS}
    y=np.full((len(result['trial']),1),np.nan,dtype='float32')
    for row in rows_for_split(roster,'test'):
        take=result['recording']==Path(row['file']).stem
        if take.any():
            events=columns(args.mat_dir,row,'ProtData')['spk']
            y[take],_=outcomes(events,result['trial'][take],result['cutoff_ms'][take])
    result.update(y=y,observed=np.isfinite(y[:,0]),prediction_sha256=np.array(args.prediction_sha256))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['train','development_validation','test-features','test-labels'])
    parser.add_argument('mat_dir',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--features',type=Path)
    parser.add_argument('--predictions',type=Path)
    parser.add_argument('--prediction-sha256')
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output path to preserve earlier reads and seals')
    if check_digest(ROSTER)!=ROSTER_SHA256:
        raise ValueError('The frozen public source roster or its original file checksums have changed')
    roster=json.loads(ROSTER.read_bytes())
    result=test_labels(args,roster) if args.mode=='test-labels' else assemble(args,roster)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=args.output.parent)
    try:
        with os.fdopen(fd,'wb') as out:
            np.savez_compressed(out,**result)
            out.flush()
            os.fsync(out.fileno())
        with args.output.open('xb') as destination:
            try:
                with open(name,'rb') as staged:
                    shutil.copyfileobj(staged,destination,1024*1024)
                destination.flush()
                os.fsync(destination.fileno())
            except BaseException:
                destination.close()
                args.output.unlink(missing_ok=True)
                raise
    finally:
        Path(name).unlink(missing_ok=True)
    print(f"{len(result['trial'])} rows, SHA256 {check_digest(args.output)}")


if __name__=='__main__':
    main()
