"""Generate artificial hand movements for tests of numerical behavior and provenance checks."""
import argparse
import json
from pathlib import Path

import numpy as np

from kit_components import dump


def generate(dest):
    dest.mkdir(parents=True,exist_ok=False)
    rows=[]
    for n in range(11):
        role='train' if n<6 else ('review' if n<10 else 'reserve')
        rec=f'fixture-{n:02}'
        row={'role':role,'group':f'group-{n}','recording':rec}
        rows.append(row)
        if role=='reserve':
            continue
        path=dest/role
        path.mkdir(exist_ok=True)
        t=np.arange(0,15,1/30.)
        rng=np.random.default_rng(400+n)
        xyz=rng.normal(0,.001,(len(t),26,3))
        xyz[:,1:,0]+=.018*np.arange(1,26)[None,:]
        events=[]
        for k,a in enumerate(range(0,15,3)):
            active=(t>=a)&(t<a+3)
            xyz[active,:,2]+=.035*np.sin((k+1)*t[active,None]+np.arange(26))
            word=['open','press','turn','lift','open'][k]
            events.append({'id':k,'start':a,'end':a+3,'text':f'{word} device','verb':word,'noun':'device'})
        events+= [dict(events[0],id=15,text='open the device'),dict(events[0],id=16,start=.1),dict(events[0],id=17,text='?')]
        valid=np.ones((len(t),26),dtype=bool)
        valid[::9]=False
        ticks=np.arange(len(t))
        ticks[::8]=np.maximum(0,ticks[::8]-1)
        np.savez_compressed(path/(rec+'.npz'),t=t,xyz=xyz.astype('f4'),valid=valid,tracked=valid,
                            active=valid.any(1),ticks=ticks)
        dump(dict(row,duration_s=15,events=events),path/(rec+'.json'))
    dump({'kind':'artificial_fixture','recordings':rows},dest/'SPLIT.json')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    generate(p.parse_args().directory)
