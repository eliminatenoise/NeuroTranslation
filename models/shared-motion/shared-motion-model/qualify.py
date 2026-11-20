"""Bounded comparison of one and two CPU threads on the first 24 training updates."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
out = []
for threads in (1, 2, 2, 1):
    start = time.perf_counter()
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS=str(threads),
               OMP_NUM_THREADS=str(threads), PYTHONDONTWRITEBYTECODE='1')
    run = subprocess.run([sys.executable, str(here/'train.py'), '--probe', '--threads', str(threads)],
                         check=True, env=env, text=True, capture_output=True)
    row = json.loads(run.stdout)
    row['complete_invocation_seconds'] = time.perf_counter()-start
    out.append(row)
diff = max(v['last_loss'] for v in out) - min(v['last_loss'] for v in out)
if diff > 1e-5:
    raise ValueError('Thread route changed loss above tolerance')
median = {n:statistics.median(r['train_seconds'] for r in out if r['threads']==n) for n in (1,2)}
result = {'runs':out, 'median_train_seconds':median, 'selected':min(median,key=median.get),
          'metric':'Median optimization-loop seconds on a repeated real 24-update prefix; loading costs are measured separately.',
          'last_loss_span':diff}
(here/'route.json').write_text(json.dumps(result, indent=2))
print(json.dumps({key:value for key,value in result.items() if key!='runs'}))
