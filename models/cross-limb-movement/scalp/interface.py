"""Public anatomical vocabulary, physical clocks and reproducible synthetic examples."""
import json
import math
from pathlib import Path

MUSCLES = [f'{side} {m}' for side in ('left','right') for m in
           ('tibialis anterior','soleus','medial gastrocnemius','peroneus longus')] + [
           f'right {m}' for m in ('anterior deltoid','brachioradialis','flexor digitorum',
                                   'common extensor digitorum','first dorsal interosseous')]

def fixture(domain):
    active = range(8) if domain == 0 else (8,9,11,12)
    mask = [j in active for j in range(13)]
    rms = [[(10 if domain == 0 else 300) * (1 + .03*j + .15*math.cos(.2*i + j)) if mask[j] else 0
            for j in range(13)] for i in range(20)]
    xyz = [[(i-19)*(.18 if domain == 0 else .55), 0.1*math.sin(i/5)-0.1*math.sin(19/5), (19-i)*.04] for i in range(20)]
    return dict(domain=domain,session=1,direction=-1 if domain==0 else 0,muscle_mask=mask,patch_rms=rms,
                patch_xyz_mm=xyz,age_s=[0 if domain==0 else ((i-19)*.03125)%0.002 for i in range(19)]+[0],
                past_rms=[math.sqrt(sum(row[j]**2 for row in rms[-4:])/4) for j in range(13)])

if __name__ == '__main__':
    for domain,name in enumerate(('lower','upper')):
        Path(__file__).with_name(f'synthetic-{name}.json').write_text(json.dumps(fixture(domain),indent=1)+'\n')
