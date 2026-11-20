"""Rebuild only one predeclared partition using eligible, hash-checked local sources."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
from features import AGE, EPS, TAPS, history_tokens

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONTRACT_SHA = '48d3dc03e05fce2b1c95e10aeca45ef934e3cd0108b7a53036b1616b29fc40a2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class Observations:
    native: np.ndarray
    grid: np.ndarray
    cm: np.ndarray
    rows: np.ndarray
    end: float
    inventory: dict


def load(entry, root):
    path = root / entry['path']
    if not path.is_file() and entry['domain'] == 'rat':
        path = root/'study-release/benchmarks/wtrack-neural-motion/recording'/Path(entry['path']).relative_to('wtrack-source')
    if sha(path) != entry['sha256']:
        raise ValueError(f"Unpinned sample file {path}")
    with np.load(path,allow_pickle=False) as f:
        if entry['domain'] == 'wrist':
            ticks = f['ticks']
            grid = f['t']
            if ticks.dtype != np.int64 or ticks.shape!=grid.shape or not np.all(np.diff(ticks)>=0) or not np.all(np.diff(grid)>0) or not np.isfinite(grid).all():
                raise ValueError('Invalid hand clocks')
            positive = np.flatnonzero(ticks>0)
            if not len(positive):
                raise ValueError('No originating ticks')
            # Subtract integers before conversion; absolute UTC ticks exceed double precision.
            native = (ticks-ticks[positive[0]])/10_000_000.
            first = (ticks>0) & np.r_[True,np.diff(ticks)>0]
            cm = f['xyz'][:,1,:].astype(np.float64)*100
            flags = f['active'] & f['valid'][:,1] & f['tracked'][:,1] & np.isfinite(cm).all(axis=1)
            use = first & flags
            rows = np.arange(len(ticks))
            end = float(native[-1])
            cnt = dict(source_rows=len(ticks),invalid_or_unusable=int((~flags).sum()),positive=int((ticks>0).sum()),distinct_positive=int(first.sum()))
        else:
            i = int(entry['recording'].split('-')[1])
            a,b = float(f['start_s']),float(f['stop_s'])
            if int(f['trial_id'])!=i or [a,b]!=[entry['start_s'],entry['stop_s']]:
                raise ValueError('Mismatched trip/time')
            raw = f['tracking_time_s']
            cm = f['xy_cm'].astype(np.float64)
            rows = f['camera_row']
            if cm.shape!=(len(raw),2) or not np.all((a<raw)&(raw<b)) or not np.all(np.diff(raw)>0) or not np.array_equal(rows,np.arange(*entry['camera_bounds'])):
                raise ValueError('Outside source bounds, invalid frame sequence or wrong coordinate dimensions')
            native = grid = raw-a
            use = np.isfinite(cm).all(axis=1)
            end = b-a
            cnt = dict(source_rows=len(raw),invalid_or_unusable=int((~use).sum()),distinct_positive=len(raw))
        cnt['admitted_unique'] = int(use.sum())
        return Observations(native[use],grid[use],cm[use],rows[use],end,cnt)


def history(obs,cut):
    q = cut + TAPS
    ids = np.searchsorted(obs.native,q,side='right')-1
    if np.any(ids<0):
        return None,'missing_history'
    if np.any(q-obs.native[ids]>AGE+EPS):
        return None,'stale_history'
    if np.any(np.diff(ids)<=0):
        return None,'reused_or_reversed_history'
    if np.any(np.diff(obs.native[ids[0]:ids[-1]+1])>.100+EPS):
        return None,'gap_history'
    if np.ptp(obs.grid[ids]-obs.native[ids])>.050+EPS:
        return None,'clock_disagreement_history'
    return ids,None


def future(obs, ids,cut):
    q = cut+.25
    if q > obs.end:
        return None,'right_censored'
    idx = np.searchsorted(obs.native,q,side='right')-1
    if idx <= ids[-1] or obs.native[idx] <= cut:
        return None,'missing_future'
    if q-obs.native[idx]>AGE+EPS:
        return None,'stale_future'
    if np.any(np.diff(obs.native[ids[-1]:idx+1])>.100+EPS):
        return None,'gap_future'
    all_ids=np.r_[ids,idx]
    if np.ptp(obs.grid[all_ids]-obs.native[all_ids])>.050+EPS:
        return None,'clock_disagreement_future'
    return idx,None


def build_record(entry,root):
    obs=load(entry,root)
    rows=[]
    reasons=Counter()
    planned=0
    eligible_history=0
    for cutoff in np.arange(2.,obs.end,2.):
        planned += 1
        ids,reason=history(obs,cutoff)
        if reason:
            reasons[reason] += 1
            continue
        eligible_history += 1
        if entry['domain']=='rat' and cutoff+.25+.05>obs.end-.25:
            reasons['prior_trial_end_buffer'] += 1
            continue
        idx,reason=future(obs,ids,cutoff)
        if reason:
            reasons[reason] += 1
            continue
        x=history_tokens(obs.cm[ids],obs.native[ids],cutoff)
        y=np.linalg.norm(obs.cm[idx]-obs.cm[ids[-1]])
        lead=obs.native[idx]-obs.native[ids[-1]]
        if not (.200-EPS<=lead<=.300+EPS):
            raise ValueError('Future physical duration outside the freeze')
        rows.append(dict(domain=entry['domain'],group=entry['group'],recording=entry['recording'],cutoff_s=cutoff,history_s=obs.native[ids],history_grid_s=obs.grid[ids],history_rows=obs.rows[ids],history_native_dt_s=np.diff(obs.native[ids]),target_s=obs.native[idx],target_grid_s=obs.grid[idx],target_row=obs.rows[idx],future_native_dt_s=lead,x=x,y=y))
        reasons['retained'] += 1
    assert sum(reasons.values())==planned
    return rows,dict(recording=entry['recording'],group=entry['group'],domain=entry['domain'],**obs.inventory,planned=planned,eligible_history=eligible_history,disposition=dict(reasons))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=['train','assessment'])
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--out',type=Path,default=HERE)
    parser.add_argument('--workers',type=int,default=1)
    args=parser.parse_args()
    if not 1<=args.workers<=4:
        parser.error('Choose 1 to 4 independent decompression threads')
    if sha(HERE/'contract.json')!=CONTRACT_SHA:
        raise ValueError('Changed data contract')
    entries=[e for e in json.loads((HERE/'contract.json').read_bytes())['records'] if e['role']==args.role]
    if args.workers==1:
        output=[build_record(e,args.root) for e in entries]
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            output=list(pool.map(lambda e:build_record(e,args.root),entries))
    rows=[r for rs,_ in output for r in rs]
    arrays={k:np.stack([r[k] for r in rows]) for k in rows[0]}
    args.out.mkdir(parents=True,exist_ok=True)
    dest=args.out/f'{args.role}.npz'
    np.savez_compressed(dest,**arrays)
    counts=[c for _,c in output]
    report=dict(contract_sha256=CONTRACT_SHA,packet_sha256=sha(dest),records=counts)
    (args.out/f'{args.role}-counts.json').write_text(json.dumps(report,indent=2)+'\n')
    print(args.role, len(rows), sha(dest))

if __name__=='__main__':
    main()
