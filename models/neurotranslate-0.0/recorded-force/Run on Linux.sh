#!/bin/sh
set -eu
cd -P -- "$(dirname -- "$0")"
exec "${PYTHON:-python3}" -B forecast.py "$@"
