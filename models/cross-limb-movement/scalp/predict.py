"""Read a synthetic or measured event and write its native muscle and marker forecast."""
import argparse
import json
from pathlib import Path

from fusion_model import predict_event

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('weights', type=Path)
    parser.add_argument('event', type=Path)
    args = parser.parse_args()
    print(json.dumps(predict_event(args.weights, json.loads(args.event.read_text())), allow_nan=False))
