"""Run a frozen study or a small deliberately artificial software test."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
try:
    import resource
except ImportError:
    resource = None
import time

import numpy as np
import torch

from retrieval import Clip, check_rows, digest, dump, evaluate, fit, unpack, words


def load(rows, part, data_root, policy):
    if part not in ("train", "assessment"):
        raise ValueError("Only training and assessment payloads are accessible")
    clips, payload_hashes = [], {}
    for row in rows:
        if row["part"] != part:
            continue
        prefix = data_root / row["key"]
        text_path = prefix.with_suffix(".json")
        data_path = prefix.with_suffix(".npy")
        captions = json.loads(text_path.read_text())
        if not isinstance(captions, list):
            raise ValueError("Expected caption list")
        x = np.load(data_path, allow_pickle=False)
        if x.ndim != 2 or x.shape[0] != policy["motion_steps"] or not np.isfinite(x).all():
            raise ValueError(f"Invalid fixed-phase measured trajectory for {row['key']}")
        payload_hashes[row["key"]] = {"array":digest(data_path), "text":digest(text_path)}
        clips.append(Clip(row["key"], row["group"], row.get("action"), captions, x))
    if len({c.sequence.shape for c in clips}) != 1:
        raise ValueError("Inconsistent motion shapes")
    unpack(clips)
    return clips, payload_hashes


def check_preparation(manifest, phase, sources, data):
    if "archive_sha256" not in manifest:  # Developer-owned fixtures may supply phase rows directly.
        return None
    receipt = data/(phase+"-records.json")
    rows = json.loads(receipt.read_text())
    if {r["key"]:{k:r[k] for k in ("array","text")} for r in rows} != sources:
        raise ValueError("Prepared files differ from the selected release pull")
    return digest(receipt)


def fit_files(out):
    return {p.name:digest(p) for p in out.iterdir() if p.suffix in (".npz",".json") and p.name != "seal.json"}


def evidence(args, start):
    return {"elapsed_s":time.perf_counter() - start, "python":platform.python_version(),
            "torch":str(torch.__version__), "numpy":np.__version__,
            "intra_op":torch.get_num_threads(), "inter_op":torch.get_num_interop_threads(),
            "affinity":sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None,
            "peak_rss_platform_units":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None,
            "device":"cpu","loader_workers":0,
            "environment":{k:os.getenv(k) for k in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS")}}
    

def diagnostics(train_receipt, current):
    seen = set(train_receipt["caption_token_hashes"])
    counted = Counter(tuple(words(s)) for c in current for s in c.captions)
    cross = {}
    for c in current:
        for tokens in {tuple(words(s)) for s in c.captions}:
            cross.setdefault(tokens,set()).add(c.key)
    n = sum(counted.values())
    return {"assessment_queries":n,
            "queries_verbatim_after_tokenization_seen_in_training":sum(
                count for tok,count in counted.items() if text_hash(tok) in seen),
            "assessment_queries_matching_descriptions_of_multiple_assessment_clips":sum(
                count for tok,count in counted.items() if len(cross[tok])>1),
            "assessment_recordings_with_same_action_peer":sum(
                1 for c in current if c.action and sum(k.action==c.action for k in current)>1),
            "semantic_equivalence_annotation":"unknown except where source action classes are supplied"}


def text_hash(tokens):
    return hashlib.sha256(" ".join(tokens).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=["fit","assess"])
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--work",type=Path,required=True)
    parser.add_argument("--policy",type=Path,default=Path(__file__).with_name("policy.json"))
    parser.add_argument("--threads",type=int,default=1)
    args = parser.parse_args()
    start = time.perf_counter()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    manifest = json.loads(args.manifest.read_text())
    rows = manifest["rows"]
    if any(not r["key"].isalnum() for r in rows):
        raise ValueError("Expected a plain alphanumeric clip ID")
    check_rows(rows)
    policy = json.loads(args.policy.read_text())
    identity = {"manifest":digest(args.manifest),"policy":digest(args.policy),
                "study.py":digest(__file__),"retrieval.py":digest(Path(__file__).with_name("retrieval.py"))}
    if "archive_sha256" in manifest:
        identity["preprocessing"] = digest(Path(__file__).with_name("kit_data.py"))
        if identity["preprocessing"] != manifest["preprocessing_sha256"]:
            raise ValueError("The preprocessing code differs from the archive manifest")
    fitted = args.work / "fit"
    if args.phase=="fit":
        train, sources = load(rows,"train",args.data,policy)
        prepared = check_preparation(manifest,"train",sources,args.data)
        if len({v["array"] for v in sources.values()}) != len(train):
            raise ValueError("Numerically identical motion files in TRAIN; require source-group audit")
        fit(train,policy,fitted)
        dump({"identity":identity, "prepared_receipt_sha256":prepared, "arrays_and_text":sources, "outputs":fit_files(fitted),
              "caption_token_hashes": sorted({text_hash(words(s)) for c in train for s in c.captions}),
              "runtime":evidence(args,start)}, fitted/"seal.json")
    else:
        seal = json.loads((fitted/"seal.json").read_text())
        if seal["identity"] != identity or fit_files(fitted) != seal["outputs"]:
            raise ValueError("Data manifest, protocol, code or fitted parameters changed")
        clips,sources = load(rows,"assessment",args.data,policy)
        prepared = check_preparation(manifest,"assessment",sources,args.data)
        previous = {v["array"] for v in seal["arrays_and_text"].values()}
        current = [v["array"] for v in sources.values()]
        if previous.intersection(current) or len(set(current)) != len(current):
            raise ValueError("Duplicated motion bytes in assessment or across split")
        out = args.work/"assessment"
        evaluate(clips,fitted,out)
        dump({"identity":identity, "prepared_receipt_sha256":prepared, "arrays_and_text":sources, "outputs":fit_files(out),
              "ambiguity":diagnostics(seal,clips), "runtime":evidence(args,start)},out/"seal.json")


if __name__=="__main__":
    main()
