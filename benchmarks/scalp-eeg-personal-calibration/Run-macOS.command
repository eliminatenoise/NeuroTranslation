#!/bin/sh
set -eu
directory=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -eq 0 ]; then set -- --help; fi
exec "${PYTHON:-python3}" "$directory/run.py" "$@"
