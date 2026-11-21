"""Refit the selected configuration on all admitted training groups."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('selection',type=Path)
    p.add_argument('manifest',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--threads',type=int,default=2)
    a=p.parse_args()
    record=json.loads(a.selection.read_text())
    v=record['selected']
    cmd=[sys.executable,'-B',str(HERE/'train.py'),str(a.manifest),'--out',str(a.out),'--evidence',str(a.evidence),'--controls','--seed',str(record['selected_full_refit_seed']),'--threads',str(a.threads),'--device',a.device]
    for k in ['width','heads','depth','ff_width','learning_rate','steps','schedule']:
        cmd+=['--'+k.replace('_','-'),str(v[k])]
    subprocess.run(cmd,check=True)


if __name__=='__main__':
    main()
