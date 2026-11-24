#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if [ "$#" -eq 0 ]; then
    set -- common-six
fi
exec "${PYTHON:-python3}" -B predict.py "$@"
