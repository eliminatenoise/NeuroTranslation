#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
exec "${NEUROTRANSLATE_PYTHON:-python3}" -B predict.py EXAMPLE.npz
