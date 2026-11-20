"""Run an invented-input check and verify that incomplete or mistyped histories fail."""
import copy
import json
from pathlib import Path
import sys
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from predict import predict_record

def main():
    sample=json.loads((HERE/'example.json').read_bytes())
    truth=json.loads((HERE/'example-results.json').read_bytes())
    for mode,expected in truth.items():
        actual=predict_record(dict(sample,mode=mode))
        assert actual['period_frames']==expected['period_frames']
        np.testing.assert_allclose(actual['internal_knee_moment_Nm_per_kg'],expected['internal_knee_moment_Nm_per_kg'],atol=1e-10,rtol=0)
    for kind in ['zero','mixed_boolean','frame_gap','future_field','axes','unknown_mode']:
        case=copy.deepcopy(sample)
        if kind=='zero':case['angles_deg'][99][3]=0
        elif kind=='mixed_boolean':case['angles_deg'][99][3]=True
        elif kind=='frame_gap':case['frames'][76]+=1
        elif kind=='future_field':case['future_moment']=[0.2,0.1]
        elif kind=='axes':case['angles_deg'][106].pop()
        else:case['mode']='missing'
        try:predict_record(case)
        except (ValueError,TypeError):continue
        raise AssertionError(f'Accepted an invalid history: {kind}')
    print('Five forecast methods matched the invented example. Six invalid inputs were rejected.')

if __name__=='__main__':main()
