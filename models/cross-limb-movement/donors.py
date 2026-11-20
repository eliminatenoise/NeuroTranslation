"""Construct non-overlapping measured donor rotations, without crossing a study."""
import numpy as np


def match(data,ids,identical_mask=False):
    groups={}
    for i in ids:
        d=int(data['domain'][i])
        key=(d,str(data['person'][i]),int(data['session'][i]),int(data['direction'][i]),int(data['block'][i]) if d==0 else -1)
        if identical_mask: key+=tuple(data['muscle_mask'][i].tolist())
        groups.setdefault(key,[]).append(int(i))
    pairs=[]
    for group in groups.values():
        order=np.asarray(sorted(group,key=lambda i:(data['cutoff_s'][i],data['event'][i])))
        lower=data['domain'][order[0]]==0
        best=[]
        for offset in range(1,len(order)):
            other=np.roll(order,-offset)
            apart=(np.abs(data['cutoff'][order]-data['cutoff'][other])>207 if lower else
                   np.abs(data['cutoff_s'][order]-data['cutoff_s'][other])>.752)
            common=data['muscle_mask'][order]&data['muscle_mask'][other]
            valid=apart&(data['event'][order]!=data['event'][other])&(common.sum(1)>=(8 if lower else 3))
            if identical_mask and not valid.all(): continue
            candidate=list(zip(order[valid].tolist(),other[valid].tolist()))
            if len(candidate)>len(best): best=candidate
            if len(best)==len(order): break
        pairs.extend(best)
    return np.asarray(pairs,dtype=int).reshape(-1,2).T
