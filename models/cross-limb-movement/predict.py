"""Run a portable checkpoint on one source-frame event (native PyTorch)."""
import argparse
import json
from pathlib import Path
from network import predict_event

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('weights',type=Path)
    p.add_argument('input',type=Path)
    args=p.parse_args()
    print(json.dumps(predict_event(args.weights,json.loads(args.input.read_text())),indent=2))
