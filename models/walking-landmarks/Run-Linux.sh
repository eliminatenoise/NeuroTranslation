#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import numpy' >/dev/null 2>&1; then
    echo 'Install Python 3 with NumPy to run the walking forecast. See REPRODUCE.md.'
    exit 1
fi
python3 predict.py "$@"
if [ -t 0 ] && [ "$#" -eq 0 ]; then
    printf 'Press Enter to close. '
    read -r answer || true
fi
