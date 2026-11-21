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
for sample in first_use_body next_neuron_prediction; do
    printf '\n%s\n' "$sample"
    "$interpreter" "$root/predict.py" "$root/$sample/example.json"
done
if [ -t 0 ]; then
    printf '\nPress Return to close.'
    read -r reply
fi
