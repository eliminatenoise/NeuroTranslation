"""Named contact count windows. Row arguments are one-based MATLAB indices."""
from __future__ import annotations
import numpy as np


COMPASS = {0: (1,0), 90: (0,1), 180: (-1,0), 270: (0,-1)}
OFFSETS = (0,5,10,15)


class Ineligible(ValueError):
    """Window was excluded by a frozen eligibility or numerical quality rule."""


def zero_columns(guide, contacts):
    """Find exactly one sort-zero column per named contact, retaining contact order."""
    pairs = [tuple(map(int,pair)) for pair in guide]
    if len(set(pairs)) != len(pairs) or len(set(contacts)) != len(contacts):
        raise ValueError("Ambiguous source contact/sort identity")
    lookup = {channel:i for i,(channel,code) in enumerate(pairs) if code==0}
    if any(c not in lookup for c in contacts):
        raise ValueError("Required sort-zero contact is absent")
    return np.array([lookup[c] for c in contacts], dtype=int)


def bump_anchors(original):
    """Select perturbation phase from original-record metadata, before numeric reads."""
    if original["result"]!="R" or original["flag"]!=1:
        raise Ineligible("ineligible_result_or_center_hold_bump_flag")
    if original["bump_direction"] not in COMPASS:
        raise Ineligible("missing_or_noncardinal_bump_direction")
    events = original["events"]
    if len(events["bump"]) != 1 or any(len(events[name])>1 for name in ("target","go")):
        raise Ineligible("ambiguous_or_missing_anchor")
    later = events["target"]+events["go"]
    anchors=[]
    for offset in OFFSETS:
        k=events["bump"][0]+offset
        if k-20 < original["start"] or k+10 > original["end"]:
            continue
        if any(stamp<=k+10 for stamp in later):
            continue
        anchors.append((offset,k))
    return anchors


def observed_cues(edges, events, angles):
    # Columns bump flag, cos/sin; target flag, cos/sin; go flag.
    cues=np.zeros((len(edges),7),dtype=np.float64)
    elapsed=np.zeros((len(edges),3),dtype=np.float64)
    for j,name in enumerate(("bump","target","go")):
        if not events[name]:
            continue
        if len(events[name])!=1:
            raise Ineligible("ambiguous_event")
        stamp=events[name][0]
        seen=stamp<edges
        if not seen.any():
            continue
        cues[seen,j*3]=1
        elapsed[seen,j]=(edges[seen]-stamp)*.01
        if name!="go":
            if angles[name] not in COMPASS:
                raise Ineligible("missing_visible_direction")
            cues[seen,j*3+1:j*3+3]=COMPASS[angles[name]]
    return cues,elapsed


def count_cells(array):
    if not np.isfinite(array).all() or np.any(array<0) or not np.all(array==np.floor(array)):
        raise Ineligible("invalid_source_count")
    return array.astype(np.int64,copy=False)


def sample_window(counts, pos, columns, original, k):
    """Extract one window. The history stops just before target row k."""
    if not (original["start"] <= k-20 and k+10 <= original["end"]):
        raise Ineligible("original_bounds")
    if original["start"]<1 or original["end"]>len(counts) or len(pos)!=len(counts):
        raise ValueError("Invalid original interval on stored data grid")
    history=slice(k-21,k-1)
    future=slice(k-1,k+9)
    prior=count_cells(counts[history,columns])
    label=count_cells(counts[future,columns]).sum(axis=0)
    position=np.asarray(pos[history],dtype=np.float64)
    if position.shape!=(20,2) or not np.isfinite(position).all():
        raise Ineligible("missing_prior_encoder_position")
    token_pos=position.reshape(5,4,2)
    movement=np.concatenate((token_pos[:,-1,:],token_pos[:,-1,:]-token_pos[:,0,:]),axis=1)
    token_edges=np.arange(k-16,k+1,4)
    angles={"bump":original["bump_direction"],"target":original["target_direction"]}
    cues,elapsed=observed_cues(token_edges,original["events"],angles)
    return dict(position_history_cm=position, count_history=prior,
                count_tokens_40ms=prior.reshape(5,4,len(columns)).sum(axis=1),
                movement_tokens_cm=movement,cues=cues,cue_elapsed_s=elapsed,
                prior_count_100ms=prior[-10:].sum(axis=0), target_count_100ms=label)
