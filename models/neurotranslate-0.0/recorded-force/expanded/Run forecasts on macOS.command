#!/bin/sh
set -eu
root=$(CDPATH='' cd -P -- "$(dirname -- "$0")" && pwd)
if [ -x "$root/.venv/bin/python" ]; then
    interpreter="$root/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    interpreter=python3
elif command -v python >/dev/null 2>&1; then
    interpreter=python
else
    printf '%s\n' 'Install Python 3 and set up the local environment. See README.md.' >&2
    exit 1
fi
if [ "$#" -gt 0 ]; then
    exec "$interpreter" "$root/predict.py" "$@"
fi
"$interpreter" "$root/predict.py"
if [ -t 0 ]; then
    printf '\nPress Return to close.'
    read -r reply
fi
