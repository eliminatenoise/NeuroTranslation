"""Score the exact released model on the five prespecified originals without retraining."""
import argparse
import json
from pathlib import Path
import tempfile
from extract import read
from project_report import project
from score import people_results,summarize
from study import HERE,SOURCE,PRODUCT,digest,save

FROZEN = "619c8bef297757cebe5acfbe47647d6c017f56a8a56b14bdcd42db3bd724cf33"


def assess_published(cache,output):
    if output.exists():
        raise FileExistsError("Choose a new cohort report path")
    seal_path = HERE/"freeze.json"
    if digest(seal_path)!=FROZEN:
        raise ValueError("Unexpected scientific freeze fingerprint")
    seal = json.loads(seal_path.read_bytes())
    if set(seal["source"])!=set(SOURCE) or set(seal["product"])!=set(PRODUCT):
        raise ValueError("Incomplete scientific freeze")
    for name in SOURCE:
        if digest(HERE/name)!=seal["source"][name]:
            raise ValueError("Original fitting or scoring program differs: "+name)
    for name in ("model.json","example.json"):
        if digest(HERE/name)!=seal["product"][name]:
            raise ValueError("Released product differs: "+name)
    weights=json.loads((HERE/"model.json").read_bytes())
    rows,source=read(cache,"assessment")
    result=summarize(people_results(weights,rows),True)
    result.update({"freeze_sha256":FROZEN,"model_sha256":seal["product"]["model.json"],"source":source})
    # The full, linked scores exist only in this private temporary directory.
    with tempfile.TemporaryDirectory() as tmp:
        raw=Path(tmp)/"assessment.json"
        save(raw,result)
        project(raw,output,seal_path)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    assess_published(args.cache,args.output)
