"""Rank the frozen local gallery for one new description, without evaluating a new target."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch

from retrieval import Retrieval, TextMap, check_rows, digest


@torch.no_grad()
def rank(sentence,manifest_path,data,fitted,n):
    manifest=json.loads(manifest_path.read_text())
    check_rows(manifest["rows"])
    seal=json.loads((fitted/"seal.json").read_text())
    if seal["identity"]["manifest"]!=digest(manifest_path):
        raise ValueError("The gallery belongs to another corpus")
    for name,sha in seal["outputs"].items():
        if digest(fitted/name)!=sha:
            raise ValueError("Fitted artifact differs from its seal")
    rows=[r for r in manifest["rows"] if r["part"]=="assessment"]
    assessment_seal=json.loads((fitted.parent/"assessment"/"seal.json").read_text())
    if assessment_seal["identity"]!=seal["identity"]:
        raise ValueError("Assessment and fit used different sources")
    paths=[data/(r["key"]+".npy") for r in rows]
    if any(digest(path)!=assessment_seal["arrays_and_text"][r["key"]]["array"] for r,path in zip(rows,paths)):
        raise ValueError("Gallery arrays differ from their assessment seal")
    meta=json.loads((fitted/"fit.json").read_text())
    p=meta["policy"]
    with np.load(fitted/"linear.npz",allow_pickle=False) as z:
        seq=(np.stack([np.load(path,allow_pickle=False) for path in paths])-z["center"])/z["scale"]
        vocab=TextMap(meta["vocabulary"],z["idf"],p["text_tokens"])
    ids,_=vocab.encode([sentence])
    if not (ids>1).any():
        raise ValueError("The training vocabulary contains none of these words")
    model=Retrieval(len(vocab.idf),meta["channels"],p)
    with np.load(fitted/"attention.npz",allow_pickle=False) as z:
        model.load_state_dict({k:torch.from_numpy(z[k].copy()) for k in z.files})
    model.eval()
    m=torch.cat([model.from_motion(x) for x in torch.from_numpy(seq).split(p["batch"])])
    cos=(model.from_words(ids)@m.T).numpy().ravel()
    # Include every candidate tied across the display cutoff.
    cutoff=np.sort(cos)[-min(max(n,1),len(rows))]
    return [{"recording":rows[i]["key"],"cosine_similarity":float(cos[i]),
             "position_shared_if_tied":int(1+(cos>cos[i]).sum())}
            for i in np.argsort(-cos,kind="stable") if cos[i]>=cutoff]


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("sentence")
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--data",required=True,type=Path)
    p.add_argument("--fit",required=True,type=Path)
    p.add_argument("--top",type=int,default=5)
    a=p.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    print(json.dumps(rank(a.sentence,a.manifest,a.data,a.fit,a.top),indent=2))
