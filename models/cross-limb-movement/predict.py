"""Run a portable checkpoint on one source-frame event (native PyTorch)."""
import argparse
import json
from pathlib import Path
import sys

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('weights',type=Path)
    p.add_argument('input',type=Path)
    args=p.parse_args()
    weights = json.loads(args.weights.read_text())
    if weights['format'] == 'cross-limb-path-map-v1':
        from decoder_model import predict_event as predict_path_map
        result = predict_path_map(weights, json.loads(args.input.read_text()))
    elif weights['format'] == 'scalp-muscle-motion-v1':
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'scalp'))
        from fusion_model import predict_event as predict_scalp
        result = predict_scalp(weights, json.loads(args.input.read_text()))
    else:
        from network import predict_event
        result = predict_event(weights, json.loads(args.input.read_text()))
    print(json.dumps(result, indent=2))
