"""Rebuild the two browser assets from the published predictor and recorded-trial ZIPs."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def build(destination):
    with tempfile.TemporaryDirectory() as temporary:
        parent = Path(temporary)
        source = parent / 'browser-source'
        source.mkdir()
        for name in ['build_archive.py','archive-core.js','build_model.py','model-runtime.js.in']:
            shutil.copyfile(HERE/name, source/name)
        for name in ['WristMotion-Forearm-Correction.zip','WristMotion-Forearm-Recorded-Trial.zip']:
            shutil.copyfile(HERE.parent/name, parent/name)
        for builder in ['build_archive.py','build_model.py']:
            subprocess.run([sys.executable, '-I', '-B', str(source/builder)],check=True)
        worker = (source/'wrist-archive.js').read_text(encoding='utf-8') + '\n' + (HERE/'worker-entry.js').read_text(encoding='utf-8')
        outputs = {'archive-worker.js': ('"use strict";\nglobalThis.WristArchiveWorkerSource = ' + json.dumps(worker,ensure_ascii=True) + ';\n').encode(),
                   'forearm-model.js': (source/'forearm-model.js').read_bytes()}
        destination.mkdir(parents=True,exist_ok=True)
        for name, data in outputs.items():
            path=destination/name
            if path.exists() and path.read_bytes()!=data:
                raise ValueError(f'Choose an output directory without a different {name}')
        for name,data in outputs.items():
            (destination/name).write_bytes(data)
            print(sha256(data).hexdigest(), name)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path,help='Directory for the rebuilt JavaScript assets')
    build(parser.parse_args().destination)
