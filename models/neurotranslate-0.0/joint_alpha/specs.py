"""Measure checkpoint size and single-case latency on observed development input shapes."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import zipfile

import numpy as np
from inference import JointModel


def timing_child(path,task,case):
    model=JointModel.load(path)
    model.predict(task,np.load(case,allow_pickle=False))


def arithmetic(arch,t,features,outputs,candidates):
    d=arch['width'];h=arch['ff_width'];depth=arch['depth']
    # One MAC = 2 nominal operations; includes the learned empty memory position.
    linear=2*(t*2*features*d+d*outputs)
    layer=2*((2+2*(t+1))*d*d+2*d*h+2*(t+1)*d)
    return candidates*(linear+depth*layer)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('checkpoint',type=Path);p.add_argument('manifest',type=Path);p.add_argument('training',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    m=JointModel.load(a.checkpoint)
    tr=json.loads(a.training.read_text())
    desc=json.loads(a.manifest.read_text())['tasks']
    with zipfile.ZipFile(a.checkpoint) as archive:
        uncompressed=sum(i.file_size for i in archive.infolist())
    report=dict(model='NeuroTranslate 0.0',version=m.version,architecture=m.architecture,parameter_dtype='float32',
                checkpoint_compressed_bytes=a.checkpoint.stat().st_size,uncompressed_npz_member_bytes=uncompressed,
                trainable_parameter_count=tr['parameters_total'],shared_trunk_parameters=tr['parameters_shared'],
                trainable_parameter_bytes=4*tr['parameters_total'],sizing='Member bytes include parameters, train-only scales, schema and NumPy headers; parameter bytes count floats alone.',
                training_device=tr.get('training_device','cpu'),fit_seconds=tr['joint']['seconds'],process_peak_rss_through_fit_kib=tr.get('rss_peak_through_fit_kib'),
                gpu_peak_allocated_bytes=tr.get('gpu_peak_allocated_bytes'),gpu_peak_reserved_bytes=tr.get('gpu_peak_reserved_bytes'),
                memory_note='Peak RSS includes interpreter, optimizer, input caches and CPU allocator. GPU allocator counters cover framework tensors only; driver, other jobs and full machine memory are outside their scope.',
                optimization={'updates':tr['steps'],'batch_per_task':tr['batch_per_task'],'tasks_per_update':tr['task_count'],'seed':tr.get('seed',431),'learning_rate_schedule':tr.get('schedule','constant'),'learning_rate':tr.get('learning_rate',.0015),'optimizer':'AdamW, one global mean over task losses, clip global norm 2, weight decay 0.001. Gradients propagate through every task head and the shared temporal attention by reverse-mode automatic differentiation.'},
                runtime={'hardware':platform.machine(),'operating_system':platform.system(),'numpy':np.__version__,'cpu_affinity_count':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,'blas_threads':os.environ.get('OPENBLAS_NUM_THREADS'),'method':'Single observed development case on CPU per task. Cold end-to-end is median of three fresh processes including Python, NumPy, reading checkpoint and case, and first prediction. Warm median and p95 over 60 calls after 5 warmups, including model preprocessing and decoding. Excludes sensor capture, feature extraction, user interface and transport. Timing varies by machine.'},
                flops_note='Nominal FP multiply/add count for one input shape, counting one multiply-accumulate as two. Includes linear maps and attention score/value products. Excludes normalization, masking, exponentials, biases, activations, data movement and framework overhead. FLOPs per training update were not measured.',tasks={})
    with tempfile.TemporaryDirectory(dir=a.output.parent) as scratch:
        for t,s in m.tasks.items():
            with np.load(a.manifest.parent/desc[t]['splits']['train'],allow_pickle=False) as z:
                sample=z['X'][:1]
            scratch_case=Path(scratch)/(t+'.npy')
            np.save(scratch_case,sample)
            cold=[]
            for _ in range(3):
                start=time.perf_counter()
                subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--cold',str(a.checkpoint),t,str(scratch_case)],check=True)
                cold.append(time.perf_counter()-start)
            for _ in range(5):
                m.predict(t,sample)
            warm=[]
            for _ in range(60):
                start=time.perf_counter()
                m.predict(t,sample)
                warm.append((time.perf_counter()-start)*1000)
            counts={name:sum(v.size for k,v in m.arrays.items() if k.startswith(prefix+t+'.')) for name,prefix in [('input_adapter','adapters.'),('output_head','outputs.')]}
            T,F=sample.shape[-2:];C=sample.shape[1] if sample.ndim==4 else 1
            report['tasks'][t]=dict(parameter_count=counts,context_steps=T,input_channels=F,output_channels=len(s['outputs']),test_case_candidate_count=C if sample.ndim==4 else None,context=s.get('history'),output=s.get('target'),nominal_inference_flops=arithmetic(m.architecture,T,F,len(s['outputs']),C),cold_seconds_median=float(np.median(cold)),warm_ms_median=float(np.median(warm)),warm_ms_p95=float(np.percentile(warm,95)))
    a.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--cold':
        timing_child(Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4]))
    else:
        main()
