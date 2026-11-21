"""Reconstruct 10 ms area-2 reach windows from a checksum-verified native MAT."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from scipy.io import loadmat

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / 'selection.json').read_bytes())
LABELS = [f'{marker}_{axis}' for marker in ('Marker_1', 'Pronation_Pt1') for axis in 'xyz']
KEYS = PLAN['key_fields']
ROWS = {'history_rows': (-20, 0), 'movement_rows': (0, 10), 'delayed_rows': (10, 20)}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic(path, writer):
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        tmp = Path(stream.name)
    try:
        with tmp.open("wb") as stream:
            writer(stream)
        try:
            os.link(tmp, path)
        except FileExistsError:
            require(digest(tmp) == digest(path), f'Existing {path.name} differs')
    finally:
        tmp.unlink(missing_ok=True)


def json_write(path, value):
    atomic(path, lambda f: f.write((json.dumps(value, indent=2, allow_nan=False) + '\n').encode()))


def session(path, plan):
    require(path.stat().st_size == plan['bytes'] and digest(path) == plan['sha256'], 'Wrong source member')
    td = loadmat(path, variable_names=['trial_data'], squeeze_me=True, struct_as_record=False)
    blocks = np.atleast_1d(td['trial_data']).ravel()
    require(len(blocks) == len(plan['blocks']), 'Wrong physical block count')
    return blocks


def native_roster(td):
    go, target = (np.asarray(getattr(td, k)) for k in ('idx_goCueTime','idx_targetStartTime'))
    require(np.all(go[1:] > go[:-1]) and np.all(target[1:] > target[:-1]), 'Event order')
    result = {}
    prev_end = 0
    for oid, st, en, ws, outcome in zip(td.trialID, td.idx_startTime, td.idx_endTime, td.spaceNum, td.result, strict=True):
        oid, st, en = map(int, (oid, st, en))
        require(oid not in result and prev_end < st <= en <= len(td.pos), 'Original boundaries')
        prev_end = en
        spaces = None if not np.isfinite(ws) else float(ws)
        result[oid] = [oid, st, en, spaces, str(outcome), go[(st<=go)&(go<=en)].astype(int).tolist(),
                       target[(st<=target)&(target<=en)].astype(int).tolist()]
    return result


def cue_rows(rows, events):
    go = np.asarray(events, dtype=np.int64)
    prior = np.searchsorted(go, rows, side='left')
    elapsed = np.zeros(prior.shape, dtype='float64')
    has_go = prior > 0
    elapsed[has_go] = (rows[has_go] - go[prior[has_go]-1]) * 0.01
    return np.column_stack((prior, elapsed, has_go))


def extract(td, spec, stage):
    b = spec['block']
    require((td.monkey, td.task, td.date_time, td.bin_size) == ('C', 'TRT', spec['date'], 0.01), 'Source task/clock/date')
    roster = native_roster(td)
    if stage == 'train':
        expected = [r[:3] for r in spec['roster']]
        all_rewarded = [r for r in roster.values() if r[3] == 1 and r[4] == 'R']
        require(expected == [r[:3] for r in all_rewarded[:len(all_rewarded)*7//10]], 'Training originals')
        selected = all_rewarded[:len(all_rewarded)*7//10]
    else:
        require(list(roster.values()) == spec['roster'], 'Held native go/target streams or roster differ')
        selected = list(roster.values())
    native_keys = []
    for oid, st, en, ws, outcome, go, target in selected:
        if ws not in (1,2) or outcome != 'R' or not go or target != [go[0]]:
            continue
        for ordinal, event in enumerate(go[1:4], 2):
            k = event + 5
            if k-20 >= st and k+20 <= en and (ordinal == len(go) or go[ordinal] > k+20):
                native_keys.append([b, int(ws), oid, ordinal, k])
    require(native_keys == spec['keys'], 'Candidate identity, chronology, boundary or next-go exclusion differs')
    result = {key: x for key, x in zip(KEYS, np.asarray(native_keys, dtype=np.int64).T, strict=True)}
    guide = np.asarray(td.S1_unit_guide, dtype=np.int64)
    require(np.array_equal(guide, spec['guide']), 'Native acquisition-contact or sort column order differs')
    n = len(td.pos)
    names = list(td.marker_names)
    require(all(names.count(s) == 1 for s in LABELS), 'Missing/duplicate optical label')
    require(td.pos.shape == (n, 2) and td.markers.shape == (n,len(names)) and td.S1_spikes.shape == (n,len(guide)), 'Native clock/array size')
    marker = [names.index(s) for s in LABELS]
    pos_cols = np.flatnonzero(guide[:,1] > 0)
    result.update(all_guide=guide, all_columns=np.arange(1,len(guide)+1), unit_guide=guide[pos_cols],
                  sorted_columns=1+pos_cols, source_member_sha256=np.asarray(PLAN[stage]['sha256']),
                  pose_labels=np.asarray(LABELS + ['handle_x','handle_y']))
    for name, (lo,hi) in ROWS.items():
        result[name] = result['k'][:,None] + np.arange(lo,hi)
    all_pose = []
    for row_name, count_name, positive_name in (
        ('history_rows', 'all_history', 'spikes'), ('movement_rows', 'all_concurrent', 'concurrent'),
        ('delayed_rows', 'all_delayed', 'delayed')):
        rows = result[row_name] - 1
        counts = td.S1_spikes[rows]
        result[count_name] = counts
        result[positive_name] = counts[:,:,pos_cols]
        if row_name != 'delayed_rows':
            optical = td.markers[rows[:,:,None], marker]
            all_pose.append(np.concatenate((optical, td.pos[rows]), axis=2).astype(np.float64))
    result['pose'] = all_pose[0]
    result['movement'] = all_pose[1] - all_pose[0][:,-1:,:]
    cues = np.asarray([cue_rows(np.arange(k-20,k+1),roster[oid][5]) for oid,k in zip(result['original'],result['k'],strict=True)])
    result['cue'] = cues[:,:20]
    result['cue_at_k'] = cues[:,20,:2]
    if stage == 'train':
        fold_for_trial = {}
        for fold, group in enumerate(np.array_split(np.arange(len(selected)), 5)):
            fold_for_trial.update((selected[i][0], fold) for i in group)
        result['fold'] = np.array([fold_for_trial[oid] for oid in result['original']], dtype=np.int64)
        previous = {}
        donors = []
        for i, (block, space, oid, ordinal, _) in enumerate(native_keys):
            group = (block, space, ordinal)
            earlier = previous.get(group, -1)
            if earlier >= 0:
                older_id = native_keys[earlier][2]
                require(older_id != oid and roster[older_id][2] < roster[oid][1], 'Earlier-trial boundary')
            donors.append(earlier)
            previous[group] = i
        result['donor'] = np.array(donors, dtype=np.int64)
        roster_fields = [r[:3] + [fold_for_trial[r[0]]] for r in selected]
        require(roster_fields == spec['roster'] and result['fold'].tolist() == spec['fold'] and donors == spec['donor'],
                'September 7 folds or earlier-trial identities differ')
        for key, axis in zip(('original','start','end','fold'), np.asarray(roster_fields, dtype=np.int64).T,strict=True):
            result['roster_'+key] = axis
        result['roster_block'] = np.full(len(spec['roster']), b, dtype=np.int64)
    return result


def verify_training(reference, arrays):
    require(digest(reference) == PLAN['training_reference_npz'], 'Frozen training reference changed')
    with np.load(reference,allow_pickle=False) as saved:
        for field in saved.files:
            require(np.array_equal(arrays[field],saved[field],equal_nan=True), 'Frozen training mismatch: '+field)
        return saved.files


def write_npz(target, arrays):
    atomic(target, lambda f: np.savez_compressed(f, **arrays))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('train','held'))
    parser.add_argument('--mat',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--reference-train',type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    plan=PLAN[args.stage]
    for td, spec in zip(session(args.mat,plan),plan['blocks'],strict=True):
        arrays=extract(td,spec,args.stage)
        if args.stage=='train' and args.reference_train:
            verify_training(args.reference_train,arrays)
        name='train' if args.stage=='train' else f"block{spec['block']}"
        target=args.output/(name+'.npz')
        write_npz(target,arrays)
        print(name,len(arrays['k']),len(arrays['all_guide']),digest(target),flush=True)


if __name__=='__main__':
    main()
