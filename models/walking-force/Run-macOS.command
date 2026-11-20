#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import numpy' >/dev/null 2>&1; then
    echo 'This model needs Python 3 with NumPy. See REPRODUCE.md.'
    exit 1
fi
python3 predict.py
if [ -t 0 ]; then
    printf 'Press Enter to close. '
    read -r answer || true
fi
