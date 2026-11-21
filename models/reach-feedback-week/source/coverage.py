"""Report primitive numerical support without changing an original, count or column."""
from pathlib import Path
import argparse

import numpy as np
from reconstruct import HERE, PLAN, digest, json_write


def summary(rows, mask):
    chosen = rows[mask]
    return dict(windows=len(chosen),originals=len(set(map(int,chosen))))


def report(stage, output):
    guides = [np.asarray(b['guide']) for d in ('train','held') for b in PLAN[d]['blocks']]
    zero = sorted(set.intersection(*[set(g[g[:,1]==0,0]) for g in guides]))
    positive = sorted(set.intersection(*[set(g[g[:,1]>0,0]) for g in guides]))
    coverage=[]
    for spec in PLAN[stage]['blocks']:
        b = spec['block']
        name = 'train' if stage=='train' else f'block{b}'
        path = output/(name+'.npz')
        with np.load(path,allow_pickle=False) as saved:
            a = {key:saved[key] for key in saved}
        guide = a['all_guide']
        good_counts = {}
        bad_by_column = {}
        for key in ('all_history','all_concurrent','all_delayed'):
            x = a[key]
            good_counts[key] = (np.isfinite(x) & (x>=0) & (np.floor(x)==x)).all(axis=1)
            rr,cc = np.where(~good_counts[key])
            bad_by_column[key] = [{'row_zero_based':int(i),'column_one_based':int(j+1)} for i,j in zip(rr,cc,strict=True)]
        good_pose=np.isfinite(a['pose']).all(axis=(1,2))
        good_move=np.isfinite(a['movement']).all(axis=(1,2))
        good_cue=np.isfinite(a['cue']).all(axis=(1,2)) & np.isfinite(a['cue_at_k']).all(axis=1)
        populations = {
            'all_common_with_sort_zero':(zero,np.ones(len(guide),bool)),
            'sort_zero_only_on_same_contacts':(zero,guide[:,1]==0),
            'positive_sorts_only_common_contacts':(positive,guide[:,1]>0)}
        primary_indices = np.flatnonzero(np.isin(guide[:,0],zero))
        primary_history=good_counts['all_history'][:,primary_indices].all(axis=1)
        blocks_by_workspace={}
        for ws in np.unique(a['workspace']):
            in_ws=a['workspace']==ws
            ids=a['original']
            roster=spec['roster']
            assigned=roster if stage=='train' else [r for r in roster if r[3]==int(ws)]
            rewarded=assigned if stage=='train' else [r for r in assigned if r[4]=='R']
            groups = {}
            for p,(contacts,kind) in populations.items():
                cols = np.flatnonzero(np.isin(guide[:,0],contacts) & kind)
                by_contact={}
                for c in contacts:
                    idx = np.flatnonzero((guide[:,0]==c)&kind)
                    fields={key:summary(ids,in_ws & valid[:,idx].all(axis=1)) for key,valid in good_counts.items()}
                    own_response = good_counts['all_delayed'][:,idx].all(axis=1)
                    fields['primary_inputs_motion_and_own_response']=summary(ids,in_ws & good_pose & good_move & good_cue & primary_history & own_response)
                    by_contact[str(c)]=dict(columns_one_based=(idx+1).tolist(),observable=fields)
                mask=good_pose & good_move & good_cue & primary_history & good_counts['all_delayed'][:,cols].all(axis=1)
                groups[p]=dict(contacts=list(map(int,contacts)),columns_one_based=(cols+1).tolist(),joint_current_and_delayed=summary(ids,in_ws & mask),per_head=by_contact)
            regions={}
            for region,slc in [('hand',slice(0,3)),('elbow',slice(3,6)),('handle',slice(6,8))]:
                regions[region]={}
                for key in ('pose','movement'):
                    valid=np.isfinite(a[key][:,:,slc]).all(axis=(1,2))
                    regions[region][key]=summary(ids,in_ws & valid)
            blocks_by_workspace[str(ws)] = dict(assigned_originals=len(assigned),rewarded_originals=len(rewarded),
                raw_candidates=summary(ids,in_ws),by_ordinal={str(j):summary(ids,in_ws & (a['ordinal']==j)) for j in (2,3,4)},
                cue_at_k_and_history=summary(ids,in_ws & good_cue),position_history=summary(ids,in_ws & good_pose),
                intervening_trajectory=summary(ids,in_ws & good_move),movement_regions=regions,contact_groups=groups)
        invalid_pose={}
        for key in ('pose','movement','cue','cue_at_k'):
            invalid_pose[key]=np.argwhere(~np.isfinite(a[key])).tolist()
        coverage.append(dict(block=b,file_sha256=digest(path),raw_columns=len(guide),unit_guide=guide.tolist(),
            numerator_note='Numerical availability before donor matching. Per-field counts can overlap. See fitted scorer for actual paired donor and loss support.',
            bad_count_window_and_native_column=bad_by_column,nonfinite_entries_zero_based=invalid_pose,by_workspace=blocks_by_workspace))
    return dict(stage=stage,member_sha256=PLAN[stage]['sha256'],blocks=coverage)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('train','held'))
    parser.add_argument('--out',type=Path,default=HERE)
    args=parser.parse_args()
    json_write(args.out/(args.stage+'-coverage.json'),report(args.stage,args.out))
