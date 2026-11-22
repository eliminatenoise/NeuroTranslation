#!/usr/bin/env sh
set -eu
cd -- "$(dirname -- "$0")"
if command -v python3 >/dev/null 2>&1; then
    exec python3 -B paired_plates.py "$@"
fi
printf '%s\n' 'Python 3 is needed. Install it or run paired_plates.py with your Python interpreter.' >&2
exit 1
