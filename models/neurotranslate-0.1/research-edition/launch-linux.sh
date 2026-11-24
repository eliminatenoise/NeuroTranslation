#!/bin/sh
folder=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
if [ -x "$folder/.venv/bin/python" ]; then
    exec "$folder/.venv/bin/python" "$folder/launch.py" "$@"
fi
exec python3 "$folder/launch.py" "$@"
