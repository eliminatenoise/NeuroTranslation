#!/bin/sh
set -eu
cd -P -- "$(dirname -- "$0")"
if command -v python3 >/dev/null 2>&1; then python=python3; else python=python; fi
if ! "$python" -c 'import numpy' 2>/dev/null; then
    echo "This demo needs Python 3.10 or later and NumPy. See README.md for setup."
    if [ -t 0 ]; then printf 'Press Return to close.'; read -r answer; fi
    exit 1
fi
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 exec "$python" joint_demo.py "$@"
