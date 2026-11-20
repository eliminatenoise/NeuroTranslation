"""Make a public copy without reporting channel errors derived from a single person."""
import argparse
import json
from pathlib import Path

def publishable(result):
    if isinstance(result,dict):
        people=result.get("per_channel_people")
        if isinstance(people,list) and isinstance(result.get("methods"),dict):
            for values in result["methods"].values():
                for field in ("channel_mae_native","channel_bias_native"):
                    if field in values:
                        values[field]=[v if count>=2 else None for count,v in zip(people,values[field],strict=True)]
        for child in result.values():publishable(child)
    elif isinstance(result,list):
        for child in result:publishable(child)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("input",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args()
    j=publishable(json.loads(a.input.read_bytes()))
    j["public_channel_reporting"]="Channel-level amplitude error and bias are withheld wherever fewer than two participants contributed. Counts and the registered overall cohort scores are retained."
    a.output.write_text(json.dumps(j,indent=2,allow_nan=False)+"\n")
