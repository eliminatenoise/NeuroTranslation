"""Re-create the fixed untrained encoder control with the original PyTorch initializer."""
from pathlib import Path
import json,sys
import torch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from network import SharedMotion
if __name__=="__main__":
    torch.manual_seed(20261121)
    model=SharedMotion()
    arrays={k:v.detach().numpy().tolist() for k,v in model.state_dict().items()
            if k.startswith(("project.","position","blocks.","last_norm."))}
    (HERE/"random-encoder.json").write_text(json.dumps(arrays,separators=(",",":"),allow_nan=False)+"\n")
