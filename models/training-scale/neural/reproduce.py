"""Rebuild the seven source groups and all curves in a new directory."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('data',type=Path,help='Directory populated by get_inputs.py')
    cli.add_argument('destination',type=Path,help='New working directory')
    cli.add_argument('--jobs',type=int,default=1,help='Independent single-thread CPU fits to run concurrently')
    args=cli.parse_args()
    if args.jobs<1:
        cli.error('--jobs must be positive')
    data=args.data.resolve(); dest=args.destination.resolve()
    dest.mkdir(parents=True,exist_ok=False)
    cache=dest/'cache'; out=dest/'runs'; report=dest/'report'
    environment={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    def launch(*command):
        subprocess.run([sys.executable,'-B',*map(str,command)],env=environment,check=True)
    launch(HERE/'prepare.py','--js14',data/'js14/train','--er1',data/'er1','--retina',data/'error_robust_mode_data.zip',
           '--turtle',data/'spikes.mat','--cache',cache)
    protocol=json.loads((HERE/'protocol.json').read_bytes())['training']
    sizes,seeds=protocol['sizes'],protocol['sample_seeds']
    for n in sizes:
        if n==sizes[-1]:
            launch(HERE/'analyze.py','forecast','--out',out)
        tasks=[(arm,seed) for arm in ('rat','mixed') for seed in seeds
               if not(n==sizes[-1] and arm=='rat' and seed!=seeds[0])]
        def train(task):
            arm,seed=task
            launch(HERE/'study.py','fit','--n',n,'--arm',arm,'--seed',seed,'--cache',cache,'--out',out)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(train,tasks))
        launch(HERE/'study.py','score','--n',n,'--cache',cache,'--out',out)
    launch(HERE/'analyze.py','report','--out',out,'--cache',cache,'--public',report)


if __name__=='__main__':
    main()
