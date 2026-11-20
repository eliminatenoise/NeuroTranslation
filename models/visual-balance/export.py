"""Write the browser weight asset, preserving JSON numbers from the fit."""
import argparse
import json
from pathlib import Path


def export(weights, destination):
    bundle = json.dumps(json.loads(weights.read_text()), allow_nan=False, separators=(",", ":"))
    source = """(function(root,value){
  if(typeof module==='object' && module.exports) module.exports=value;
  else root.VisualWalkWeights=value;
})(globalThis,""" + bundle + ");\n"
    destination.write_text(source)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("weights", type=Path)
    p.add_argument("destination", type=Path)
    args = p.parse_args()
    export(args.weights, args.destination)
