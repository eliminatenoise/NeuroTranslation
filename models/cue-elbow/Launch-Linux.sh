#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -B infer.py "$@"
if [ "$#" -eq 0 ] && [ -t 0 ]; then
    printf '\nPress Enter to close. '
    read -r answer || true
fi
