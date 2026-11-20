"""Build the self-contained browser comparison from the released model files."""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent


def read(p):
    return json.loads(p.read_bytes())


def main():
    model = read(HERE / "model.json")
    checkpoint = PARENT / "movement-weights.npz"
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != model["parent_sha256"]:
        raise ValueError("The parent checkpoint has changed.")
    raw = read(PARENT / "back_rotation/random-encoder.json")
    with np.load(checkpoint, allow_pickle=False) as saved:
        shared = {k:saved[k].ravel().tolist() for k in raw}
    payload = {"state":model,"trained":shared,"random":{k:np.ravel(v).tolist() for k,v in raw.items()},
               "dev":read(HERE/"development.json"),"historical":read(HERE/"historical.json")}
    text=(HERE/"reader.html.in").read_text().replace("@@DATA@@",json.dumps(payload,separators=(",",":"),allow_nan=False))
    text=text.replace("@@ENCODER@@",(PARENT/"back_rotation/encoder.js").read_text())
    (HERE/"index.html").write_text(text)


if __name__=="__main__":
    main()
