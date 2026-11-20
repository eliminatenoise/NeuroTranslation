#!/bin/sh
set -eu
if [ "$#" -eq 0 ]; then
    request=example.json
else
    case "$1" in
        /*) request=$1 ;;
        *) request=$PWD/$1 ;;
    esac
fi
cd "$(dirname "$0")"
if command -v node >/dev/null 2>&1; then
    exec node run-example.cjs "$request"
fi
exec python3 predict.py "$request"
