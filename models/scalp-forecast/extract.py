"""Build jointly eligible trials directly from clocks in the verified GDF files."""
from collections import Counter
import numpy as np
from ofner_early import ASSESSMENT, CUES, FITTING, Run

SCALP = (13, 17, 28, 32, 43, 47)
EYES = (62, 63, 64)
SENSORS = (93, 94, 68)
HORIZONS = (256, 512, 768)


def read(cache, partition):
    jobs = {"fit": FITTING, "assessment": ASSESSMENT}[partition]
    trials, audit = [], []
    for person, number in jobs:
        exclusions = Counter()
        with Run(cache, person, number) as run:
            cues = [(t, c) for t, c in run.events if c in CUES]
            if (Counter(c for _, c in cues) != {c: 6 for c in CUES} or
                    [t for t, _ in cues] != sorted({t for t, _ in cues})):
                raise ValueError("Unexpected cue roster or ordering")
            events = Counter(run.events)
            for i, (t, c) in enumerate(cues):
                limit = cues[i+1][0] if i+1 < len(cues) else run.records*512
                ends = [tt for tt, cc in run.events if t < tt <= limit and cc == c+0x8000]
                if ends != [t+1536] or any(events[t-1024, m] != 1 for m in (0x300,0x311,0x312)):
                    raise ValueError("Unexpected precursor or movement end")
                cutoff = t+128
                last = cutoff//8
                if t < 127 or last < 31 or (cutoff+768)//8 >= run.records*64:
                    exclusions["incomplete"] += 1
                    continue
                electric = np.column_stack([run.window(k,t-127,t+129) for k in SCALP+EYES])
                hist = np.column_stack([run.window(k,last-31,last+1) for k in SENSORS]).reshape(4,8,3)
                ends = [(cutoff+h)//8 for h in HORIZONS]
                future = np.array([np.column_stack([run.window(k,e-7,e+1) for k in SENSORS]) for e in ends])
                if not all(np.isfinite(a).all() for a in (electric,hist,future)):
                    exclusions["nonfinite"] += 1
                    continue
                levels = np.median(hist,axis=1)
                drift = np.median(hist[:,4:],axis=1) - np.median(hist[:,:4],axis=1)
                b = electric.reshape(4,64,9).mean(axis=1)
                trials.append((np.column_stack((levels,drift)), b[:,:6], b[:,6:],
                               np.median(future,axis=1)-levels[-1], (person,number,c-0x600,t)))
            audit.append({"person":person,"run":number,"source_sha256":run.sha256,
                          "cue_events":len(cues),"omissions":dict(exclusions)})
    if not trials:
        raise ValueError("No jointly eligible trials")
    return tuple(np.array(x) for x in zip(*trials)), audit
