#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Install Python 3 with NumPy, then run this launcher again.' >&2
    exit 1
fi
exec python3 forecast.py "$@"
