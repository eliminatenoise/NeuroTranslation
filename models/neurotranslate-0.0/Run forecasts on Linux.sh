#!/bin/sh
set -eu
root=$(CDPATH='' cd -P -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
    interpreter=python3
else
    interpreter=python
fi
if [ "$#" -gt 0 ]; then
    exec "$interpreter" "$root/predict.py" "$@"
fi
"$interpreter" "$root/predict.py"
if [ -t 0 ]; then
    printf '\nPress Return to close.'
    read -r reply
fi
